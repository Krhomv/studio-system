"""End-to-end smoke test of the studio system, on a throw-away copy. Touches nothing outside a temp folder and stops only the
board process it started.

  python smoke_test.py [--port N] [--keep]

Steps: scaffold.py init + 3 x scaffold.py studio into a temp project -> sample data on top (make_sample.py) -> register switched
to CRLF line endings -> start.py on a free port (8800-8899, or --port) -> every GET route, the security checks, every POST action
(with stale-hash conflicts) -> note.py / prio.py / mark_live.py / watch.py / tick.py / resq.py against the copy -> stop.py ->
the port is free again. Prints PASS / FAIL per check; exit 1 if anything failed. --keep leaves the temp project for a look.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SYS = os.path.dirname(HERE)
PY = sys.executable
NW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
RES = {"pass": 0, "fail": []}


def check(name, ok, info=""):
    if ok:
        RES["pass"] += 1
        print("PASS  " + name)
    else:
        RES["fail"].append(name)
        print("FAIL  %s  %s" % (name, str(info)[:400]))
    return ok


def run(args, cwd=None, env=None, timeout=120):
    r = subprocess.run([PY, "-B"] + args, capture_output=True, text=True, cwd=cwd, env=env, timeout=timeout, creationflags=NW)
    return r.returncode, r.stdout + r.stderr


def free_port():
    for p in range(8800, 8900):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise SystemExit("no free port in 8800-8899")


class Board:
    def __init__(self, port):
        self.base = "http://127.0.0.1:%d" % port
        self.port = port

    def req(self, path, body=None, headers=None, raw=False):
        h = {} if body is None else {"Content-Type": "application/json", "X-Studio-Board": "1"}
        h.update(headers or {})
        data = None if body is None else json.dumps(body).encode()
        r = urllib.request.Request(self.base + path, data=data, headers=h, method="POST" if body is not None else "GET")
        try:
            with urllib.request.urlopen(r, timeout=15) as resp:
                b = resp.read()
                return resp.status, (b if raw else json.loads(b.decode() or "{}"))
        except urllib.error.HTTPError as e:
            b = e.read()
            try:
                return e.code, json.loads(b.decode())
            except ValueError:
                return e.code, {"raw": b[:200]}

    def tasks(self):
        return self.req("/api/tasks")[1]

    def block(self, bid):
        return next((b for b in self.tasks()["blocks"] if b["id"] == bid), None)

    def decide(self, bid, action, comment="", h=None):
        b = self.block(bid)
        return self.req("/api/decide", {"id": bid, "action": action, "hash": h or b["hash"], "comment": comment})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    port = a.port or free_port()
    tmp = tempfile.mkdtemp(prefix="studio_smoke_")
    proj = os.path.join(tmp, "example")
    os.makedirs(proj)
    hub = os.path.join(proj, "studio-hub")
    cfgp = os.path.join(hub, "board", "board.config.json")
    env = dict(os.environ, STUDIO_BOARD_CONFIG=cfgp)
    started = False
    print("temp project: %s   port %d" % (proj, port))
    try:
        # ---------------------------------------------------------- scaffold
        rc, out = run([os.path.join(SYS, "board", "scaffold.py"), "init", proj, "--name", "Example Game", "--port", str(port)])
        check("scaffold init", rc == 0 and os.path.isfile(cfgp), out)
        for f in ("CLAUDE.md", "studio-hub/TASKS_GUIDE.md", "studio-hub/PUBLISH.md", "studio-hub/data/PROPOSALS.md",
                  "studio-hub/manager/AGENT.md", "studio-hub/manager/prompts/tick.txt", "studio-hub/manager/relay_messages.md",
                  "studio-hub/queue/resq.py", "studio-hub/board/server.py", "studio-hub/templates/studio/AGENT.md"):
            check("init made " + f, os.path.isfile(os.path.join(proj, f)))
        guide = open(os.path.join(hub, "TASKS_GUIDE.md"), encoding="utf-8").read()
        check("init filled {{HUB}} / {{PROJECT}}", "{{HUB}}" not in guide and "{{PROJECT}}" not in guide and "Example Game" in guide)
        rc2, out2 = run([os.path.join(SYS, "board", "scaffold.py"), "init", proj, "--name", "Example Game"])
        check("scaffold init twice keeps existing files", rc2 == 0 and "kept" in out2 and
              open(os.path.join(proj, "CLAUDE.md"), encoding="utf-8").read().count("<!-- studio-system -->") == 1, out2)
        for key, pre, lab, icon, owner in (("art", "ART", "Art", "brush", ""), ("audio", "AUD", "Audio", "music", ""),
                                           ("levels", "LVL", "Levels", "map", "")):
            rc, out = run([os.path.join(hub, "board", "scaffold.py"), "studio", key, "--prefix", pre, "--label", lab, "--icon", icon])
            check("scaffold studio " + key, rc == 0 and os.path.isfile(os.path.join(proj, "studios", key, "AGENT.md")), out)
        rc, out = run([os.path.join(hub, "board", "scaffold.py"), "studio", "art2", "--prefix", "ART", "--label", "Dup"])
        check("scaffold refuses a duplicate prefix", rc != 0, out)
        cfg = json.load(open(cfgp, encoding="utf-8"))
        check("config has the 3 studios", [s["key"] for s in cfg["studios"]] == ["art", "audio", "levels"], cfg["studios"])
        guide = open(os.path.join(hub, "TASKS_GUIDE.md"), encoding="utf-8").read()
        check("guide studio table rewritten", "| levels | Levels | levels-studio | LVL- | GEN-levels |" in guide)
        agent = open(os.path.join(proj, "studios", "art", "AGENT.md"), encoding="utf-8").read()
        check("studio AGENT.md filled", "{{OWNER}}" not in agent and "art-studio" in agent)

        # ---------------------------------------------------------- sample data on top, CRLF register, sample panels
        rc, out = run([os.path.join(SYS, "sample", "make_sample.py"), "--out", proj])
        check("sample data written", rc == 0, out)
        sample_cfg = json.load(open(os.path.join(SYS, "sample", "studio-hub", "board", "board.config.json"), encoding="utf-8"))
        for k in ("schedule", "panels"):
            cfg[k] = sample_cfg[k]
        cfg["panels"]["system"]["gpu"] = ""          # no external program needed for the test
        with open(cfgp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        regp = os.path.join(hub, "data", "PROPOSALS.md")
        raw = open(regp, "rb").read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        open(regp, "wb").write(raw)

        # ---------------------------------------------------------- start
        rc, out = run([os.path.join(hub, "board", "start.py")], env=env)
        started = rc == 0
        check("start.py", started, out)
        if not started:
            return 1
        rc, out = run([os.path.join(hub, "board", "start.py")], env=env)
        check("start.py again is idempotent", rc == 0 and "already running" in out, out)
        B = Board(port)

        # ---------------------------------------------------------- GET routes
        st, h = B.req("/api/health")
        check("GET /api/health", st == 200 and h.get("app") == "board-example-game", h)
        st, c = B.req("/api/config")
        check("GET /api/config", st == 200 and len(c.get("studios", [])) == 3 and c["statuses"]["IN WORK"]["word"] == "IN WORK", c)
        st, page = B.req("/", raw=True)
        check("GET / (index.html)", st == 200 and b"/api/config" in page)
        t = B.tasks()
        cols = {}
        for b in t["blocks"]:
            cols[b["column"]] = cols.get(b["column"], 0) + 1
        check("GET /api/tasks: 14 cards in every column",
              len(t["blocks"]) == 14 and cols == {"live": 1, "done": 2, "result": 1, "work": 4, "proposed": 3, "backlog": 1,
                                                  "rejected": 1, "closed": 1}, cols)
        check("parser warning for the malformed card", any("LVL-04" in i for i in t["issues"]), t["issues"])
        check("3 open asks (one on a GEN thread)", len(t["open_asks"]) == 3 and any(q["general"] for q in t["open_asks"]), t["open_asks"])
        check("moved-to link LVL-03 -> LVL-02", B.block("LVL-03")["moved_to"]["id"] == "LVL-02")
        check("images resolved", all(i["rel"] for b in t["blocks"] for i in b["images"]["visual"]))
        st, r = B.req("/api/requests")
        check("GET /api/requests", st == 200 and r["items"] and r["items"][0]["id"] == "REQ-01", r)
        st, mb = B.req("/api/bundle")
        check("GET /api/bundle", st == 200 and mb["exists"] and mb["can_merge"], mb)
        st, q = B.req("/api/queue")
        check("GET /api/queue", st == 200 and "queue" in q and q["queue"]["lock"] is None and q["tonight"]["deadline"], q)
        st, _ = B.req("/img?p=studios/art/cards/ART-01_rocks_ab.png", raw=True)
        check("GET /img inside the project", st == 200)
        st, _ = B.req("/img?p=../../windows/win.ini", raw=True)
        check("GET /img refuses ..", st == 403)
        st, _ = B.req("/api/tasks", headers={"Host": "evil.example:%d" % port})
        check("bad Host header refused", st == 403)
        st, _ = B.req("/api/decide", {"id": "ART-05"}, headers={"X-Studio-Board": "0"})
        check("POST without the board header refused", st == 403)
        st, _ = B.req("/api/decide", {"id": "ART-05"}, headers={"Origin": "http://evil.example"})
        check("POST from another origin refused", st == 403)

        # ---------------------------------------------------------- POST actions
        old = B.block("ART-05")["hash"]
        st, r = B.decide("ART-05", "approve", "yes, start with the potions")
        check("approve ART-05", st == 200 and r["status"] == "APPROVED", r)
        st, r = B.decide("ART-05", "approve", h=old)
        check("stale hash -> 409 conflict", st == 409 and r.get("conflict"), r)
        st, r = B.decide("AUD-03", "backlog")
        check("backlog AUD-03", st == 200 and r["status"].startswith("BACKLOG"), r)
        st, r = B.decide("AUD-03", "approve_backlog", "ok now")
        check("approve from backlog", st == 200 and "from backlog" in r["status"], r)
        st, r = B.decide("ART-06", "reject_backlog")
        check("reject from backlog", st == 200 and r["status"] == "REJECTED", r)
        st, r = B.decide("LVL-04", "reject", "not needed")
        check("reject LVL-04", st == 200 and r["status"] == "REJECTED", r)
        st, r = B.decide("ART-03", "approve")
        check("wrong stage -> 409", st == 409, r)
        ask = next(q for q in B.tasks()["open_asks"] if q["id"] == "ART-03")
        st, r = B.req("/api/answer", {"id": "ART-03", "reply_to": ask["nid"], "text": "B (medium)"})
        check("answer the ART-03 ask (pick)", st == 200 and r["ok"], r)
        st, r = B.req("/api/answer", {"id": "ART-03", "reply_to": ask["nid"], "text": "again"})
        check("second answer to the same ask -> 409", st == 409, r)
        st, r = B.decide("ART-03", "accept", "pick: B (medium)")
        check("accept ART-03", st == 200 and r["status"] == "ACCEPTED", r)
        st, r = B.decide("LVL-02", "close")
        check("close without a reason -> 400", st == 400, r)
        st, r = B.decide("LVL-02", "close", "superseded (by LVL-05)")
        check("close LVL-02 with a reason", st == 200 and r["status"].startswith("CLOSED (user: superseded [by LVL-05]"), r)
        st, r = B.decide("LVL-02", "reopen")
        check("reopen LVL-02", st == 200 and r["status"].startswith("APPROVED (reopened"), r)
        b = B.block("ART-04")
        st, r = B.req("/api/priority", {"id": "ART-04", "hash": b["hash"], "level": "P1"})
        check("priority P1 on ART-04", st == 200 and B.block("ART-04")["priority"] == 1, r)
        st, r = B.req("/api/new", {"studio": "levels", "priority": "P2", "title": "Fence clips through the barn", "what": "move the fence 30 cm",
                                   "visual": "studios/levels/cards/LVL-01_railing.png"})
        check("new request -> LVL-05 APPROVED", st == 200 and r["id"] == "LVL-05" and B.block("LVL-05")["priority"] == 2, r)
        st, r = B.req("/api/question", {"id": "AUD-01", "question": "Is the bridge done too?"})
        check("question to AUD-01", st == 200, r)
        st, r = B.req("/api/question", {"id": "GEN-audio", "question": "Any plan for the rain sounds?"})
        check("question on a GEN thread", st == 200, r)
        st, r = B.req("/api/merge", {"name": "bundle-0004", "comment": "merge LVL-01"})
        check("merge request for the bundle", st == 200, r)
        st, r = B.req("/api/merge", {"name": "bundle-0004"})
        check("second merge request -> 409", st == 409, r)
        st, r = B.req("/api/new", {"studio": "nope", "title": "x", "what": "y"})
        check("new request for an unknown studio -> 400", st == 400, r)
        rb = open(regp, "rb").read()
        check("register keeps CRLF after writes", rb.count(b"\r\n") > 50 and rb.count(b"\n") == rb.count(b"\r\n"))
        txt = rb.decode("utf-8")
        check("decision lines carry the user's words", 'user, ' in txt and '"Approve. yes, start with the potions" (board)' in txt)

        # ---------------------------------------------------------- studio commands
        N = os.path.join(hub, "board", "note.py")
        rc, out = run([N, "ART-04", "Text redrawn, far view checked.", "--pct", "70", "--img", "studios/art/cards/ART-04_sign_wip.png"], cwd=proj, env=env)
        check("note.py progress note with picture", rc == 0 and "noted ART-04" in out, out)
        rc, out = run([N, "ART-04", "--img", "studios/../../outside.png"], cwd=proj, env=env)
        check("note.py refuses a picture outside the project", rc != 0, out)
        rc, out = run([N, "LVL-05", "Which side of the barn?", "--ask", "--img", "studios/levels/cards/LVL-01_railing.png",
                       "--options", "north|south"], cwd=proj, env=env)
        check("note.py --ask with options", rc == 0 and "asked the user" in out, out)
        ask_id = out.split("[id ")[-1].split("]")[0]
        rc, out = run([N, "LVL-05", "--withdraw", ask_id, "--reason", "found it in the request"], cwd=proj, env=env)
        check("note.py --withdraw own ask", rc == 0 and "withdrew" in out, out)
        rc, out = run([N, "GEN-art", "New brush set in studios/art/tools."], cwd=proj, env=env)
        check("note.py plain note on GEN-art", rc == 0, out)
        rc, out = run([N, "GEN-nobody", "x"], cwd=proj, env=env)
        check("note.py refuses an unknown GEN thread", rc != 0, out)
        rc, out = run([N, "AUD-01", "--show"], cwd=proj, env=env)
        check("note.py --show prints the user's question", rc == 0 and "USER ASKED" in out, out)
        rc, out = run([N, "--open-asks"], cwd=proj, env=env)
        check("note.py --open-asks", rc == 0 and "open ask(s)" in out and "ART-04" in out, out)
        rc, out = run([os.path.join(hub, "board", "prio.py"), "--studio", "art"], cwd=proj, env=env)
        check("prio.py --studio art (P1 first)", rc == 0 and out.strip().splitlines()[1].strip().startswith("P1"), out)
        ML = os.path.join(hub, "board", "mark_live.py")
        rc, out = run([ML, "v4", "--round", "r4", "ART-02", "ART-03", "AUD-02"], cwd=proj, env=env)
        check("mark_live.py v4 r4 (3 items)", rc == 0 and out.count("-> LIVE (v4, r4") == 3, out)
        rc, out = run([ML, "v4", "ART-04"], cwd=proj, env=env)
        check("mark_live.py refuses an IN WORK item", rc != 0 and "SKIPPED" in out, out)
        rc, out = run([ML, "v4", "--revert-to-work", "AUD-02", "--reason", "click came back"], cwd=proj, env=env)
        check("mark_live.py --revert-to-work", rc == 0 and "reverted in v4" in out, out)
        t = B.tasks()
        live = [b for b in t["blocks"] if b["column"] == "live"]
        check("board shows the new LIVE group", any(b["live_label"] == "v4" for b in live), [b["live_label"] for b in live])

        # ---------------------------------------------------------- tick / watch
        TK = os.path.join(hub, "board", "tick.py")
        rc, out = run([TK], cwd=proj, env=env)
        check("tick.py flags unrelayed decisions", rc == 0 and "FLAG DECISION" in out and "BOARD DOWN" not in out, out)
        rc, out = run([TK, "--relayed"], cwd=proj, env=env)
        check("tick.py --relayed", rc == 0 and "relayed cursor" in out, out)
        rc, out = run([TK], cwd=proj, env=env)
        check("tick.py after relay: no DECISION flags", rc == 0 and "FLAG DECISION" not in out, out)
        got = {}
        th = threading.Thread(target=lambda: got.update(r=run([os.path.join(hub, "board", "watch.py"), "--minutes", "0.12", "--interval", "1"],
                                                                cwd=proj, env=env)))
        th.start()
        time.sleep(2.5)
        B.req("/api/question", {"id": "ART-05", "question": "Can you show two icons first?"})
        th.join(30)
        out = got.get("r", (1, ""))[1]
        check("watch.py prints a new decision live, then ends", "DECISION" in out and "ART-05 question" in out and "re-arm" in out, out)

        # ---------------------------------------------------------- queue
        RQ = os.path.join(hub, "queue", "resq.py")
        rc, out = run([RQ, "status"], cwd=proj, env=env)
        check("resq status (empty)", rc == 0 and "lock: free" in out, out)
        rc, out = run([RQ, "run", "test job", "--owner", "art-studio", "--task", "ART-04", "--", PY, "-c", "print('job ran')"], cwd=proj, env=env)
        check("resq run (takes, runs, releases)", rc == 0 and "job ran" in out, out)
        rc, out = run([RQ, "acquire", "hold for checks", "--owner", "audio-studio", "--pid", str(os.getpid())], cwd=proj, env=env)
        check("resq acquire", rc == 0 and "audio-studio" in out, out)
        st, q = B.req("/api/queue")
        check("board queue panel shows the holder", q["queue"]["lock"] and q["queue"]["lock"]["owner"] == "audio-studio", q.get("queue"))
        rc, out = run([RQ, "release", "--owner", "art-studio"], cwd=proj, env=env)
        check("resq release refuses another owner's lock", rc != 0, out)
        rc, out = run([RQ, "release", "--owner", "audio-studio", "--pid", str(os.getpid())], cwd=proj, env=env)
        check("resq release own lock", rc == 0 and "released" in out, out)
        st, r = B.req("/api/hold", {"action": "hold"})
        time.sleep(0.8)
        st, q = B.req("/api/queue")
        check("board Hold button takes the user hold", q["queue"]["lock"] and q["queue"]["lock"]["hold"], q.get("queue"))
        rc, out = run([TK], cwd=proj, env=env)
        check("tick.py does not flag the user's hold", "FLAG HOLD" not in out, out)
        st, r = B.req("/api/hold", {"action": "release"})
        st2, q = B.req("/api/queue")
        check("board Release button removes the hold", st == 200 and q["queue"]["lock"] is None, r)
        dec = open(os.path.join(hub, "data", "decisions.jsonl"), encoding="utf-8").read()
        check("hold / release logged for the manager", '"action": "hold"' in dec and '"action": "release"' in dec)
        ev = open(os.path.join(hub, "queue", "events.log"), encoding="utf-8").read()
        check("queue events log written", '"event": "take"' in ev and '"event": "release"' in ev)

        # ---------------------------------------------------------- stop
        rc, out = run([os.path.join(hub, "board", "stop.py")], env=env)
        check("stop.py stops our board", rc == 0 and "stopped" in out, out)
        started = False
        time.sleep(0.5)
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port))
            check("port free again", True)
        except OSError as e:
            check("port free again", False, e)
        finally:
            s.close()
    finally:
        if started:
            run([os.path.join(hub, "board", "stop.py")], env=env)
        if a.keep:
            print("kept: " + proj)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed%s" % (RES["pass"], len(RES["fail"]), (": " + ", ".join(RES["fail"])) if RES["fail"] else ""))
    return 1 if RES["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
