"""resq: a fair queue for one scarce shared resource (a GPU, a device, a build machine...). Python stdlib only, no console windows.

Every user of the resource joins the queue instead of polling a lock:

  python resq.py run "<what>" --owner NAME [--task ID] [--short] [--timeout H] -- <command ...>
        enqueue, wait for your turn, take the lock, run the command, release, exit with its code
  python resq.py acquire "<what>" --owner NAME [--task ID] [--short] [--pid PID] [--timeout H]
        enqueue, wait, take the lock, print the owner line, exit 0 (the lock stays held until `release`; PID = the process
        that holds it, default: the caller)
  python resq.py release --owner NAME [--pid PID]
        remove the lock if it is yours (same owner, and the same pid when given); never touches another owner's lock
  python resq.py status        the lock, the running turn and the waiting tickets in serving order (exit 3 = someone waiting)
  python resq.py hold [--by "..."] [--wait]      the user's hold: take the lock as "<hold_line> ..." when it is free
  python resq.py unhold        remove the user's hold (only a lock whose line starts with hold_line)

Serving order: priority owners (queue.priority_owners, e.g. "build*") > tickets for an open P1 board task > the running turn's
owner (until its turn tail) > board priority of the ticket's --task (P2 < P3 = untagged < P4) > the owner served least recently
> the oldest ticket. Running jobs are never cut.
Turns: an owner keeps the resource for its consecutive tickets, with queue.grace_s between them, for at most queue.turn_max_min;
in the last queue.turn_tail_min its long tickets rank like everyone else's. A --short ticket (releases within
queue.short_max_min) may run in another owner's grace gap; an overrun bans that owner from gaps for queue.gap_ban_min.
Gate: queue.gate_cmd (optional shell command, exit 0 = OK) must pass before a long, non-priority ticket takes a free lock.
A lock whose holder pid is dead is removed by any waiter (holds excepted). The user's hold is removed only by the user (board
button / `unhold`) or by the manager.
Config: --config, else env STUDIO_BOARD_CONFIG, else ../board/board.config.json; state lives in the config's paths.queue.
Env: RESQ_OWNER, RESQ_TASK as defaults for --owner / --task.
"""
import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
POLL = 1.0

S = {"turn_max_min": 20, "grace_s": 60, "turn_tail_min": 3, "short_max_min": 3, "gap_ban_min": 60,
     "priority_owners": ["build*", "nightly*"], "hold_line": "USER HOLD", "gate_cmd": "", "on_hold_url": ""}
P = {"dir": HERE, "register": None, "words": {}, "default_prio": 3}
CLOSED_KEYS = ("ACCEPTED", "HANDOFF", "LIVE", "REJECTED", "CLOSED", "BACKLOG")


def configure(config=None):
    """read the board config (queue settings, queue folder, register for task priorities). Missing config = defaults here."""
    p = Path(config or os.environ.get("STUDIO_BOARD_CONFIG") or (HERE.parent / "board" / "board.config.json"))
    c = {}
    if p.is_file():
        with open(p, encoding="utf-8-sig") as f:
            c = json.load(f)
        base = p.resolve().parent
        paths = c.get("paths") or {}
        P["dir"] = (base / paths.get("queue", "../queue")).resolve()
        P["register"] = (base / paths.get("register", "../data/PROPOSALS.md")).resolve()
    S.update({k: v for k, v in (c.get("queue") or {}).items() if k in S})
    P["words"] = {k: str((v or {}).get("word") or k).upper() for k, v in (c.get("statuses") or {}).items()}
    pr = (c.get("priority") or {}).get("default", 3)
    P["default_prio"] = int(pr) if str(pr).isdigit() else 3
    return P["dir"]


def _paths():
    d = Path(P["dir"])
    return d / "lock", d / "lock" / "owner.txt", d / "tickets", d / "turn.json", d / "events.log", d / "gaps.log"


# ---------------------------------------------------------------- small helpers

def now():
    return time.time()


def iso(t=None):
    return dt.datetime.fromtimestamp(t or now()).isoformat(timespec="seconds")


def alive(pid):
    try:
        pid = int(pid)
    except Exception:  # noqa
        return False
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259          # STILL_ACTIVE


def is_priority(owner):
    return any(fnmatch.fnmatch(str(owner or "").lower(), pat.lower()) for pat in S["priority_owners"])


def evlog(event, owner="", **kw):
    try:
        ev = _paths()[4]
        ev.parent.mkdir(parents=True, exist_ok=True)
        with open(ev, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(dict({"ts": iso(), "event": event, "owner": owner}, **kw)) + "\n")
    except Exception:  # noqa
        pass


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".%d.tmp" % os.getpid())
    tmp.write_text(json.dumps(data), encoding="utf-8")
    for i in range(10):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.1)
    tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------- task priority from the board register

_PRIO = {"mtime": None, "map": {}}


def task_priority(task):
    """-> (priority 1..4, open?) for a board task id; untagged / unknown = (default, False)"""
    if not task or not P["register"]:
        return P["default_prio"], False
    reg = Path(P["register"])
    try:
        mt = reg.stat().st_mtime
    except OSError:
        return P["default_prio"], False
    if _PRIO["mtime"] != mt:
        closed = {P["words"].get(k, k) for k in CLOSED_KEYS}
        allw = sorted(set(P["words"].values()) | closed | {"PROPOSED", "APPROVED", "IN WORK", "RESULT"}, key=len, reverse=True)
        m_, cur = {}, None
        for ln in reg.read_text(encoding="utf-8", errors="replace").splitlines():
            h = re.match(r"^## (\S+)\s.*?(?:\u2014|--)\s*(.*)$", ln)
            if h:
                st = re.sub(r"\([^)]*\)", " ", h.group(2)).upper()
                found = []
                for w in allw:
                    for m in re.finditer(r"(?<![A-Z])" + re.escape(w) + r"(?![A-Z])", st):
                        found.append((m.start(), w))
                    st = re.sub(r"(?<![A-Z])" + re.escape(w) + r"(?![A-Z])", lambda x: "#" * len(x.group(0)), st)
                last = max(found)[1] if found else ""
                cur = h.group(1)
                m_[cur] = [P["default_prio"], last not in closed]
                continue
            if cur and re.match(r"^priority:\s*P([1-4])\b", ln, re.I):
                m_[cur][0] = int(re.match(r"^priority:\s*P([1-4])", ln, re.I).group(1))
        _PRIO.update(mtime=mt, map=m_)
    v = _PRIO["map"].get(task)
    return (v[0], v[1]) if v else (P["default_prio"], False)


# ---------------------------------------------------------------- state

def lock_owner():
    """the lock's owner line ('' when free); never raises"""
    _, ow, *_ = _paths()
    try:
        return ow.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "?" if _paths()[0].exists() else ""


def lock_pid(line=None):
    m = re.search(r"\bpid (\d+)", line if line is not None else lock_owner())
    return int(m.group(1)) if m else None


def holder_name(line=None):
    line = lock_owner() if line is None else line
    return line.split(" ")[0] if line else ""


def held_by_user():
    return _paths()[0].exists() and lock_owner().upper().startswith(S["hold_line"].upper())


def turn_state():
    try:
        return json.loads(_paths()[3].read_text(encoding="utf-8"))
    except Exception:  # noqa
        return {}


def turn_active(st=None, t=None):
    """the owner whose turn is running (holding, or inside its grace after a release), else None"""
    st = turn_state() if st is None else st
    t = now() if t is None else t
    o = st.get("owner")
    if not o:
        return None
    if t - st.get("started", 0) > S["turn_max_min"] * 60 and holder_name() != o:
        return None
    if holder_name() == o:
        return o
    gap = st.get("gap") or {}
    if gap and holder_name() == gap.get("owner"):
        return o
    return o if t - st.get("last_release", 0) < S["grace_s"] else None


def tickets(clean=True):
    """live tickets [(path, data)]; dead waiters' tickets are removed (clean=False: only skipped, for read-only views)"""
    tdir = _paths()[2]
    out = []
    if not tdir.is_dir():
        return out
    for f in sorted(tdir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa
            d = {}
        pid = d.get("pid") or (re.findall(r"_(\d+)\.json$", f.name) or [0])[0]
        if alive(pid):
            out.append((f, d))
        elif clean:
            f.unlink(missing_ok=True)
    return out


def ranked(live, st=None, t=None):
    """live tickets in serving order -> [(rank tuple, path, data)]"""
    st = turn_state() if st is None else st
    t = now() if t is None else t
    cur = turn_active(st, t)
    served = st.get("served") or {}
    in_tail = cur and (t - st.get("started", t)) > (S["turn_max_min"] - S["turn_tail_min"]) * 60
    others_wait = any(d.get("owner") != cur for _, d in live)
    out = []
    for f, d in live:
        o = d.get("owner", "?")
        pr, open_ = task_priority(d.get("task"))
        created = d.get("created_t", 0)
        if is_priority(o):
            r = (-3, 0, created)
        elif pr == 1 and open_:
            r = (-2, 0, created)
        elif cur and o == cur and not (in_tail and others_wait and not d.get("short")):
            r = (-1, pr, created)
        else:
            r = (pr, served.get(o, 0), created)
        out.append((r, f, d))
    out.sort(key=lambda x: (x[0], x[1].name))
    return out


def snapshot():
    """read-only view for the board panel"""
    t = now()
    lk = None
    if _paths()[0].exists():
        line = lock_owner()
        m = re.search(r"since (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)", line)
        t0 = dt.datetime.fromisoformat(m.group(1)).timestamp() if m else None
        pid = lock_pid(line)
        name = holder_name(line)
        hold = line.upper().startswith(S["hold_line"].upper())
        lk = {"line": line, "owner": "user hold" if hold else name, "what": re.sub(r",? ?since .*$", "", line[len(name):]).strip(),
              "pid": pid, "alive": bool(pid) and alive(pid), "held_min": round((t - t0) / 60, 1) if t0 else None,
              "hold": hold, "priority": is_priority(name)}
    st = turn_state()
    cur = turn_active(st, t)
    turn = None
    if cur:
        gap = st.get("gap") or {}
        h = holder_name()
        mode = "gap" if (gap and h == gap.get("owner")) else ("holding" if h == cur else "grace")
        turn = {"owner": cur, "jobs": st.get("jobs", 1), "used_min": round((t - st.get("started", t)) / 60, 1),
                "left_min": round(max(0, S["turn_max_min"] * 60 - (t - st.get("started", t))) / 60, 1), "max_min": S["turn_max_min"],
                "mode": mode, "grace_s": max(0, int(S["grace_s"] - (t - st.get("last_release", 0)))) if mode == "grace" else None,
                "gap_owner": gap.get("owner") if mode == "gap" else None, "priority": is_priority(cur)}
    tk = []
    for r, f, d in ranked(tickets(clean=False), st, t):
        pr, open_ = task_priority(d.get("task"))
        tk.append({"owner": d.get("owner"), "what": d.get("what", ""), "pid": d.get("pid"), "short": bool(d.get("short")),
                   "task": d.get("task") or "", "prio": pr, "p1": pr == 1 and open_, "priority": is_priority(d.get("owner")),
                   "created": d.get("created"), "wait_min": round((t - d.get("created_t", t)) / 60, 1)})
    bans = {o: dt.datetime.fromtimestamp(u).strftime("%H:%M") for o, u in (st.get("gap_ban") or {}).items() if u > t}
    return {"lock": lk, "turn": turn, "tickets": tk, "bans": bans, "gate": bool(S["gate_cmd"]), "hold_line": S["hold_line"],
            "settings": {k: S[k] for k in ("turn_max_min", "grace_s", "short_max_min")}}


# ---------------------------------------------------------------- taking / releasing

def _take(line):
    lock, ow, *_ = _paths()
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        return False
    except OSError:
        return False
    ow.write_text(line, encoding="utf-8")
    return True


def owner_line(owner, what, pid, task=""):
    return "%s %s%s, since %s, pid %d" % (owner, (what or "").replace("\n", " ")[:120], (" [%s]" % task) if task else "", iso(), pid)


_GATE = {"t": 0, "ok": True}


def gate_ok():
    if not S["gate_cmd"]:
        return True
    if now() - _GATE["t"] < 30:
        return _GATE["ok"]
    try:
        r = subprocess.run(S["gate_cmd"], shell=True, capture_output=True, timeout=60, creationflags=NW)
        ok = r.returncode == 0
    except Exception:  # noqa
        ok = True   # a broken gate command must not stop the queue for ever
    _GATE.update(t=now(), ok=ok)
    return ok


def clear_dead_lock():
    """remove a lock whose holder pid is dead (never a hold)"""
    if not _paths()[0].exists() or held_by_user():
        return False
    line = lock_owner()
    pid = lock_pid(line)
    if pid and not alive(pid):
        time.sleep(1.0)   # re-check: a release may be under way
        if lock_owner() == line and not alive(pid):
            shutil.rmtree(_paths()[0], ignore_errors=True)
            evlog("stale_release", holder_name(line), pid=pid)
            return True
    return False


def enqueue(what, owner, pid, short=False, task=""):
    tdir = _paths()[2]
    tdir.mkdir(parents=True, exist_ok=True)
    t = now()
    f = tdir / ("%d_%s_%d.json" % (int(t * 1000), re.sub(r"[^A-Za-z0-9_.-]", "-", owner)[:40], pid))
    _write_json(f, {"owner": owner, "what": what, "pid": pid, "created": iso(t), "created_t": t, "short": bool(short), "task": task or ""})
    return f


def wait_take(what, owner, holder_pid, timeout_h=12.0, short=False, task=""):
    """block until this ticket may take the lock; returns the owner line written"""
    me = os.getpid()
    ticket = enqueue(what, owner, me, short, task)
    deadline = now() + timeout_h * 3600
    try:
        while now() < deadline:
            if _paths()[0].exists():
                clear_dead_lock()
                time.sleep(POLL)
                continue
            live = tickets()
            order = ranked(live)
            if not order or order[0][1].name != ticket.name:
                # a --short ticket may use another owner's grace gap when that owner has nothing waiting
                if not (short and _gap_ok(owner, live)):
                    time.sleep(POLL)
                    continue
            st = turn_state()
            cur = turn_active(st)
            gap = False
            if cur and cur != owner and not is_priority(owner):
                pr, open_ = task_priority(task)
                if not (pr == 1 and open_):
                    if short and _gap_ok(owner, live):
                        gap = True
                    else:
                        time.sleep(POLL)
                        continue
            if not short and not is_priority(owner) and not gate_ok():
                time.sleep(POLL * 5)
                continue
            line = owner_line(owner, what, holder_pid, task)
            if not _take(line):
                time.sleep(POLL)
                continue
            ticket.unlink(missing_ok=True)
            st = turn_state()
            t = now()
            if gap:
                st["gap"] = {"owner": owner, "started": t}
                evlog("take_gap", owner, what=what, task=task)
            elif st.get("owner") == owner and turn_active(st, t) == owner:
                st["jobs"] = st.get("jobs", 1) + 1
                st.pop("gap", None)
                evlog("take", owner, what=what, task=task, turn_job=st["jobs"])
            else:
                served = st.get("served") or {}
                served[owner] = t
                st = {"owner": owner, "started": t, "jobs": 1, "last_release": 0, "served": served,
                      "gap_ban": st.get("gap_ban") or {}}
                evlog("take", owner, what=what, task=task, turn_job=1)
            _write_json(_paths()[3], st)
            return line
        raise TimeoutError("waited %.1f h without getting the lock" % timeout_h)
    finally:
        ticket.unlink(missing_ok=True)


def _gap_ok(owner, live):
    st = turn_state()
    cur = turn_active(st)
    if not cur or cur == owner or is_priority(cur) or holder_name():
        return False
    if (st.get("gap_ban") or {}).get(owner, 0) > now():
        return False
    return not any(d.get("owner") == cur for _, d in live)


def release(owner, pid=None):
    lock = _paths()[0]
    if not lock.exists():
        return False
    line = lock_owner()
    if holder_name(line) != owner or (pid and lock_pid(line) not in (None, int(pid))):
        return False
    shutil.rmtree(lock, ignore_errors=True)
    st = turn_state()
    t = now()
    gap = st.get("gap") or {}
    if gap.get("owner") == owner:
        took = t - gap.get("started", t)
        if took > S["short_max_min"] * 60:
            st.setdefault("gap_ban", {})[owner] = t + S["gap_ban_min"] * 60
            try:
                with open(_paths()[5], "a", encoding="utf-8") as f:
                    f.write("%s %s gap job overran: %.1f min, no gaps for %d min\n" % (iso(t), owner, took / 60, S["gap_ban_min"]))
            except OSError:
                pass
        st.pop("gap", None)
        evlog("release_gap", owner, held_min=round(took / 60, 1))
    elif st.get("owner") == owner:
        st["last_release"] = t
        evlog("release", owner)
    _write_json(_paths()[3], st)
    return True


def hold(by="the user"):
    line = "%s (%s, since %s). Only the user or the manager removes it." % (S["hold_line"], by, iso())
    ok = _take(line)
    if ok:
        evlog("hold", "user", by=by)
    return ok


def unhold():
    if not held_by_user():
        return False
    shutil.rmtree(_paths()[0], ignore_errors=True)
    evlog("unhold", "user")
    return True


# ---------------------------------------------------------------- cli

def print_status():
    s = snapshot()
    lk = s["lock"]
    if lk:
        print("lock: %s | held %s min | holder %s" % (lk["line"][:110], lk["held_min"], "alive" if lk["alive"] or lk["hold"] else "DEAD"))
    else:
        print("lock: free")
    tu = s["turn"]
    if tu:
        print("turn: %s job %d, %.1f / %d min (%s%s)" % (tu["owner"], tu["jobs"], tu["used_min"], tu["max_min"], tu["mode"],
                                                    (", grace %d s" % tu["grace_s"]) if tu["grace_s"] is not None else ""))
    for o, u in s["bans"].items():
        print("gap ban: %s until %s" % (o, u))
    for i, t in enumerate(s["tickets"], 1):
        print("  %d. %s | %s%s%s | P%d | waiting %.0f min" % (i, t["owner"], t["what"][:60], " [%s]" % t["task"] if t["task"] else "",
                                                          " short" if t["short"] else "", t["prio"], t["wait_min"]))
    if S["gate_cmd"]:
        print("gate: %s" % ("open" if gate_ok() else "SHUT (%s fails)" % S["gate_cmd"]))
    return 3 if s["tickets"] else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "acquire"):
        p = sub.add_parser(name)
        p.add_argument("what")
        p.add_argument("--owner", default=os.environ.get("RESQ_OWNER", ""))
        p.add_argument("--task", default=os.environ.get("RESQ_TASK", ""))
        p.add_argument("--short", action="store_true")
        p.add_argument("--timeout", type=float, default=12.0, help="hours")
        if name == "acquire":
            p.add_argument("--pid", type=int, default=None)
    p = sub.add_parser("release")
    p.add_argument("--owner", default=os.environ.get("RESQ_OWNER", ""))
    p.add_argument("--pid", type=int, default=None)
    sub.add_parser("status")
    p = sub.add_parser("hold")
    p.add_argument("--by", default="the user")
    p.add_argument("--wait", action="store_true")
    sub.add_parser("unhold")
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:                       # run "<what>" [options] -- <command ...>
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    a = ap.parse_args(argv)
    configure(a.config)

    if a.cmd == "status":
        return print_status()
    if a.cmd == "hold":
        while True:
            if held_by_user():
                print("already held")
                return 0
            if hold(a.by):
                print("held: " + lock_owner())
                return 0
            if not a.wait:
                print("busy: " + lock_owner() + " (use --wait to take it when free)")
                return 1
            time.sleep(0.25)
    if a.cmd == "unhold":
        print("released" if unhold() else "no hold to release")
        return 0
    if not a.owner:
        print("--owner (or env RESQ_OWNER) is needed", file=sys.stderr)
        return 2
    if a.cmd == "release":
        ok = release(a.owner, a.pid)
        print("released" if ok else "not released (free, or not yours: %s)" % (lock_owner() or "free"))
        return 0 if ok else 1
    if a.cmd == "acquire":
        holder = a.pid or os.getppid()
        print(wait_take(a.what, a.owner, holder, a.timeout, a.short, a.task))
        return 0
    cmd = command
    if not cmd:
        print("give the command after --", file=sys.stderr)
        return 2
    wait_take(a.what, a.owner, os.getpid(), a.timeout, a.short, a.task)
    try:
        try:   # pass the std handles explicitly: a child without a console window would otherwise lose its output
            io = {"stdin": sys.stdin.fileno(), "stdout": sys.stdout.fileno(), "stderr": sys.stderr.fileno()}
        except (AttributeError, OSError, ValueError):
            io = {}
        sys.stdout.flush()
        return subprocess.call(cmd, creationflags=NW, **io)
    finally:
        release(a.owner, os.getpid())


if __name__ == "__main__":
    sys.exit(main())
