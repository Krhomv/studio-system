"""tick.py: the manager's compact health check of the board, the studios and the shared queue. Prints one short status block and
FLAG lines for anything that needs action. It changes nothing, except restarting the board when it does not answer.

  python tick.py [--config PATH]
  python tick.py --relayed          mark every decision line as relayed (after you relayed them)

FLAGS (what to do on each: runbook/07_manager_routine.md):
- DECISION   a user action on the board not yet relayed to its studio (relay it, quoting the user's words, then --relayed)
- BOARD      hygiene: a result posted while the card still reads APPROVED / IN WORK; no studio note for more than stale_hours on
             an APPROVED / IN WORK card (parked cards with "waiting for" / "held" in the bracket are skipped); IN WORK with no note
- READY      within 2 h of the deadline, a ready file not written for 6 h
- HOLD       the queue lock held longer than turn_max_min + 5 by a normal owner, or held by a dead pid (holds and priority owners
             excepted: the build's long holds are by design)
- WAIT       a ticket waiting more than 45 min (not while a hold or a priority owner has the lock)
- STUCK      lock free, tickets waiting, no turn running (check again in 1 min before acting)
- GATE       the gate command says no while tickets wait: tell the user what to close; never loosen the gate yourself
- BOARD DOWN the board did not answer; tick restarted it with start.py
Project-specific checks: tick_local.py next to this file, `def checks(ctx): return ["FLAG text", ...]`.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import server as S  # noqa: E402
NW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def decision_lines():
    try:
        with open(S.CFG["paths"]["decisions"], encoding="utf-8", errors="replace") as f:
            return [x for x in f.read().splitlines() if x.strip()]
    except OSError:
        return []


def set_cursor(n):
    p = S.CFG["cursor"]
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(str(n))
    os.replace(tmp, p)


def hours_to(hhmm):
    na = S.next_at(hhmm)
    return None if na is None else na["in_min"] / 60.0


def load_resq():
    p = os.path.join(S.CFG["paths"]["queue"], "resq.py")
    if not os.path.isfile(p):
        p = os.path.join(os.path.dirname(HERE), "queue", "resq.py")
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location("resq_tick", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.configure(S.CFG["config_file"])
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--relayed", action="store_true")
    a = ap.parse_args()
    c = S.load_config(a.config)
    if a.relayed:
        n = len(decision_lines())
        set_cursor(n)
        print("relayed cursor = %d" % n)
        return 0

    now = time.time()
    flags, out = [], []
    out.append("%s %s" % (time.strftime("%H:%M"), c["project"]))
    building = os.path.exists(c["paths"]["build_marker"])

    # ---- register
    text, _ = S.read_file(c["paths"]["register"])
    reg = S.parse_register(text)
    blocks = reg["blocks"]
    cnt = {}
    for b in blocks:
        cnt.setdefault(b["stage"] or "?", []).append(b["id"])
    line = "tasks: " + ", ".join("%s %d" % (k, len(v)) for k, v in cnt.items())
    if cnt.get("PROPOSED"):
        line += " | to approve: " + " ".join(cnt["PROPOSED"])
    if cnt.get("RESULT"):
        line += " | to accept: " + " ".join(cnt["RESULT"])
    out.append(line)
    if reg["issues"]:
        out.append("parser: %d warning(s): %s" % (len(reg["issues"]), " ; ".join(reg["issues"][:3])))

    # ---- open asks
    dec, cur = S.read_decisions(), S.relayed_cursor()
    summ = {b["id"]: S.progress_summary(b["id"], dec, cur) for b in blocks}
    gens = [dict(id=g, title="general", general=True, progress=S.progress_summary(g, dec, cur)) for g in S.gen_threads()]
    asks = S.collect_open_asks([dict(b, progress=summ[b["id"]]) for b in blocks], gens)
    if asks:
        oldest = (now - dt.datetime.fromisoformat(asks[0]["ts"][:19]).timestamp()) / 3600
        out.append("asks for the user: %d (oldest %.1f h): %s" % (len(asks), oldest, " ; ".join("%s %s" % (q["id"], q["note"][:50]) for q in asks[:4])))

    # ---- hygiene
    stale_h = float(c.get("stale_hours") or 3)
    for b in blocks:
        if b["stage"] not in ("APPROVED", "IN WORK"):
            continue
        st = b["status"].lower()
        if b["fields"].get("result", "").strip() and "rework" not in st and "reverted" not in st:
            flags.append("BOARD %s has a %s but reads %s (set %s so the user can accept)" % (
                b["id"], c["terms"]["result"], S.W(b["stage"]), S.W("RESULT")))
        if re.search(r"waiting for|waits for|\bheld\b", st):
            continue
        last = summ[b["id"]]["last_studio"]
        if last:
            age = (now - dt.datetime.fromisoformat(last[:19]).timestamp()) / 3600
            if age > stale_h:
                flags.append("BOARD %s %s: no %s note for %.1f h (stale?)" % (b["id"], S.W(b["stage"]), c["terms"]["studio"], age))
        elif b["stage"] == "IN WORK":
            flags.append("BOARD %s %s with no progress note" % (b["id"], S.W("IN WORK")))

    # ---- ready files
    rd = c["paths"]["ready"]
    stamps = []
    h_dead = hours_to(c["schedule"].get("deadline"))
    if rd and os.path.isdir(rd):
        for f in sorted(os.listdir(rd)):
            if not f.endswith(".md"):
                continue
            mt = os.path.getmtime(os.path.join(rd, f))
            stamps.append("%s %s" % (f[:-3], time.strftime("%H:%M", time.localtime(mt))))
            if h_dead is not None and 0 <= h_dead <= 2 and (now - mt) / 3600 > 6:
                flags.append("READY %s last written %.1f h ago (deadline %s)" % (f[:-3], (now - mt) / 3600, c["schedule"]["deadline"]))
    out.append("%ss: %s%s" % (c["terms"]["ready_file"], ", ".join(stamps) or "none", " | BUILD_RUNNING" if building else ""))

    # ---- queue
    q = None
    if c["panels"]["queue"].get("enabled"):
        try:
            q = load_resq()
        except Exception as e:  # noqa
            out.append("queue: not readable (%s)" % e)
    if q is not None:
        snap = q.snapshot()
        lk, tk, tu = snap["lock"], snap["tickets"], snap["turn"]
        if lk:
            out.append("lock: %s | held %s min | holder %s" % (lk["line"][:90], lk["held_min"], "alive" if lk["alive"] or lk["hold"] else "DEAD"))
            if not lk["hold"] and not lk["priority"]:
                if not lk["alive"]:
                    flags.append("HOLD dead holder (pid %s): %s" % (lk["pid"], lk["line"][:70]))
                elif lk["held_min"] and lk["held_min"] > q.S["turn_max_min"] + 5:
                    flags.append("HOLD %.0f min: %s" % (lk["held_min"], lk["line"][:70]))
        else:
            out.append("lock: free")
        for t in tk:
            out.append("  q %s | %s%s | waiting %.0f min" % (t["owner"], t["what"][:60], " [%s]" % t["task"] if t["task"] else "", t["wait_min"]))
            if t["wait_min"] > 45 and not (lk and (lk["hold"] or lk["priority"])):
                flags.append("WAIT %.0f min: %s %s" % (t["wait_min"], t["owner"], t["what"][:50]))
        if not lk and tk:
            if tu:
                out.append("  (lock free: %s is in its grace between jobs)" % tu["owner"])
            else:
                flags.append("STUCK lock free with %d waiting (check again in 1 min before acting)" % len(tk))
            if snap.get("gate") and not q.gate_ok():
                flags.append("GATE shut (%s fails) while %d wait: tell the user what to close; never loosen the gate" % (q.S["gate_cmd"], len(tk)))

    # ---- unrelayed decisions
    lines = decision_lines()
    for x in lines[S.relayed_cursor():]:
        if '"action": "live"' in x or '"action": "revert"' in x:
            continue
        try:
            d = json.loads(x)
            words = str(d.get("comment") or "").strip()
            flags.append('DECISION %s %s %s -> %s%s' % (d.get("id", "?"), d.get("studio", "?"), d.get("action", "?"), d.get("status", ""),
                                                      (' | words: "%s"' % words[:120]) if words else ""))
        except ValueError:
            flags.append("DECISION (unparsed) %s" % x[:90])

    # ---- the board itself
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/api/health" % c["port"], timeout=3).read()
    except Exception:  # noqa
        subprocess.run([sys.executable, os.path.join(HERE, "start.py"), "--config", c["config_file"]],
                       capture_output=True, timeout=60, creationflags=NW)
        flags.append("BOARD DOWN: the board did not answer; restarted it with start.py")

    # ---- project checks
    lp = os.path.join(HERE, "tick_local.py")
    if os.path.isfile(lp):
        try:
            spec = importlib.util.spec_from_file_location("tick_local", lp)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            ctx = {"cfg": c, "now": now, "server": S, "queue": q, "blocks": blocks, "building": building, "flags": list(flags)}
            flags += [str(f) for f in (m.checks(ctx) or [])]
        except Exception as e:  # noqa
            flags.append("LOCAL tick_local.py failed: %s" % e)

    if building:
        out.append("BUILD_RUNNING: act only on HOLD flags by studios and on DECISION relays")
    for ln in out:
        print(ln)
    for fl in flags:
        print("FLAG " + fl)
    if not flags:
        print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
