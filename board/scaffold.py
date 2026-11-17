"""scaffold.py: set up the studio system in a project, and add studios to it. It never overwrites an existing file (unless --force)
and never deletes anything.

  python scaffold.py init <project root> --name "<Project>" [--hub studio-hub] [--port 8790] [--no-queue] [--force]
        creates <root>/<hub>/ (board, queue, data, ready, builds, requests, reviews, manager, templates), <root>/studios/,
        <root>/CLAUDE.md (or appends a section to an existing one), board.config.json, and the filled templates.
        Run it from the runbook folder (C:/AI/studio-system/board/scaffold.py).
  python scaffold.py studio <key> --prefix ART --label "Art" [--owner art-studio] [--icon brush] [--color "#d58fb8"]
                            [--queue-owner NAME] [--no-ready] [--config <hub>/board/board.config.json] [--force]
        adds the studio to board.config.json, creates studios/<key>/ (CLAUDE.md, AGENT.md, NOTES.md, BRIEF.md and the
        cards / lab / tools / staged / backup / logs folders) and rewrites the studio table in TASKS_GUIDE.md.
        Run it from the project's copy (<hub>/board/scaffold.py) or pass --config.

Placeholders: {{NAME}} are filled here; <describe ...> parts are for the deploying agent / the user. After init, read the list
of files with <describe ...> left and fill them (runbook/12_deploy_new_project.md).
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)                         # the runbook folder (or the project's hub, for a deployed copy)
BOARD_FILES = ["server.py", "index.html", "note.py", "prio.py", "mark_live.py", "start.py", "stop.py", "watch.py", "tick.py",
               "scaffold.py", "README.md"]
KEEP_FILES = ["tick_local.py"]                      # copied once, then the project's own
ICONS = ["brush", "leaf", "sun", "cube", "gauge", "parcel", "megaphone", "spray", "tiles", "music", "film", "code", "bug", "book",
         "pen", "chart", "map", "wrench", "globe", "star"]
COLORS = ["#d58fb8", "#82be8f", "#c99a73", "#d9b95e", "#92a6dc", "#6fc3c9", "#b49ad6", "#e08a6a", "#9fc46a", "#e6a0a0"]
report = {"made": [], "skipped": []}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "project"


def write_new(path, text, force=False):
    if os.path.exists(path) and not force:
        report["skipped"].append(path)
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)
    report["made"].append(path)
    return True


def copy_new(src, dst, force=False):
    if os.path.exists(dst) and not force:
        report["skipped"].append(dst)
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    report["made"].append(dst)
    return True


def fill(text, vals):
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: str(vals.get(m.group(1), m.group(0))), text)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def values(cfg, root, hub_rel, runbook):
    t = cfg.get("terms", {})
    sc = cfg.get("schedule", {})
    return {"PROJECT": cfg.get("project", "Project"), "ROOT": root.replace("\\", "/"), "HUB": hub_rel,
            "BOARD_URL": "http://127.0.0.1:%d/" % cfg.get("port", 8790), "PORT": cfg.get("port", 8790),
            "HANDOVER": sc.get("handover") or "<handover time>", "DEADLINE": sc.get("deadline") or "<deadline>",
            "BUILD_TIME": sc.get("build") or "<build time>", "DATE": dt.date.today().isoformat(),
            "TERM_STUDIO": t.get("studio", "studio"), "TERM_MANAGER": t.get("manager", "manager"), "TERM_BUILD": t.get("build", "build"),
            "TERM_RESULT": t.get("result", "result"), "TERM_READY": t.get("ready_file", "ready file"),
            "RUNBOOK": runbook.replace("\\", "/")}


def default_config(name, port, queue):
    return {
        "project": name, "app_id": "board-" + slug(name), "port": port, "root": "../..", "runbook": SRC.replace("\\", "/"),
        "paths": {"register": "../data/PROPOSALS.md", "decisions": "../data/decisions.jsonl", "progress": "../data/progress",
                  "bundle": "../data/bundle.json", "requests": "../requests/REQUESTS.md", "ready": "../ready",
                  "build_marker": "../BUILD_RUNNING", "queue": "../queue"},
        "image_bases": ["", "studio-hub", "studios"],
        "terms": {"studio": "studio", "studios": "studios", "manager": "manager", "user": "you", "result": "result",
                  "build": "build", "ready_file": "ready file"},
        "studios": [],
        "statuses": {"HANDOFF": {"enabled": True}, "LIVE": {"enabled": True}, "BACKLOG": {"enabled": True}},
        "fields": ["what", "why", "visual", "scope", "cost", "decision", "priority", "result", "accept", "handoff"],
        "image_fields": ["visual", "result"],
        "priority": {"default": 3, "names": {"1": "urgent", "2": "high", "3": "normal", "4": "low"}},
        "stale_hours": 3,
        "schedule": {"handover": "", "deadline": "", "build": ""},
        "panels": {"requests": {"enabled": True, "title": "Requests inbox"},
                   "bundle": {"enabled": False, "owner": "", "title": "Bundle", "button": "Merge this bundle"},
                   "queue": {"enabled": bool(queue), "title": "Queue"},
                   "system": {"enabled": True, "gpu": "nvidia-smi" if shutil.which("nvidia-smi") else ""}},
        "queue": {"turn_max_min": 20, "grace_s": 60, "turn_tail_min": 3, "short_max_min": 3, "gap_ban_min": 60,
                  "priority_owners": ["build*", "nightly*"], "hold_line": "USER HOLD", "gate_cmd": "", "on_hold_url": ""},
    }


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- init

def cmd_init(a):
    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        print("project root not found: %s" % root, file=sys.stderr)
        return 2
    tsrc = os.path.join(SRC, "templates")
    if not os.path.isdir(tsrc) or not os.path.isfile(os.path.join(SRC, "queue", "resq.py")):
        print("run init from the runbook folder (templates/ and queue/ next to board/); not found under %s" % SRC, file=sys.stderr)
        return 2
    hub_rel = a.hub.strip("/\\") or "studio-hub"
    hub = os.path.join(root, hub_rel)
    board = os.path.join(hub, "board")
    for d in ("board", "data/progress", "ready", "builds", "requests", "reviews", "manager/prompts", "queue", "templates"):
        os.makedirs(os.path.join(hub, d), exist_ok=True)
    os.makedirs(os.path.join(root, "studios"), exist_ok=True)
    for f in BOARD_FILES:
        copy_new(os.path.join(HERE, f), os.path.join(board, f), force=True)   # the tool's own code is always refreshed
    for f in KEEP_FILES:
        copy_new(os.path.join(HERE, f), os.path.join(board, f), force=a.force)
    if not a.no_queue:
        for f in ("resq.py", "README.md"):
            copy_new(os.path.join(SRC, "queue", f), os.path.join(hub, "queue", f), force=True)
    cfgp = os.path.join(board, "board.config.json")
    if os.path.exists(cfgp) and not a.force:
        cfg = json.load(open(cfgp, encoding="utf-8-sig"))
        report["skipped"].append(cfgp)
    else:
        cfg = default_config(a.name, a.port, not a.no_queue)
        cfg["image_bases"] = ["", hub_rel, "studios"]
        save_json(cfgp, cfg)
        report["made"].append(cfgp)
    vals = values(cfg, root, hub_rel, cfg.get("runbook") or SRC)
    # reference copy of every template (unfilled), so a deployed project can add studios and fill per-use files
    for dp, _, files in os.walk(tsrc):
        for f in files:
            s = os.path.join(dp, f)
            copy_new(s, os.path.join(hub, "templates", os.path.relpath(s, tsrc)), force=a.force)
    T = lambda *p: read(os.path.join(tsrc, *p))  # noqa: E731
    write_new(os.path.join(hub, "README.md"), fill(T("hub", "README.md"), vals), a.force)
    write_new(os.path.join(hub, "TASKS_GUIDE.md"), fill(T("hub", "TASKS_GUIDE.md"), vals), a.force)
    write_new(os.path.join(hub, "PUBLISH.md"), fill(T("hub", "PUBLISH.md"), vals), a.force)
    write_new(os.path.join(hub, "data", "PROPOSALS.md"), fill(T("hub", "PROPOSALS.md"), vals), a.force)
    write_new(os.path.join(hub, "requests", "REQUESTS.md"), fill(T("hub", "REQUESTS.md"), vals), a.force)
    for f in ("AGENT.md", "NEXT.md", "USAGE_HALT.md"):
        write_new(os.path.join(hub, "manager", f), fill(T("manager", f), vals), a.force)
    for f in sorted(os.listdir(os.path.join(tsrc, "manager", "prompts"))):
        write_new(os.path.join(hub, "manager", "prompts", f), fill(T("manager", "prompts", f), vals), a.force)
    write_new(os.path.join(hub, "manager", "relay_messages.md"), fill(T("relay_messages.md"), vals), a.force)
    write_new(os.path.join(hub, "manager", "memory_rule.md"), fill(T("memory_rule.md"), vals), a.force)
    write_new(os.path.join(hub, "data", "decisions.jsonl"), "", False)
    write_new(os.path.join(hub, "data", "relayed.cursor"), "0", False)
    write_new(os.path.join(hub, "applied.json"), "{}\n", False)
    # project CLAUDE.md: new file, or one appended section (marked, so a second init does not add it twice)
    pc = os.path.join(root, "CLAUDE.md")
    section = fill(T("project", "CLAUDE.md"), vals)
    if not os.path.exists(pc):
        write_new(pc, "<!-- studio-system -->\n" + section)
    else:
        cur = read(pc)
        if "<!-- studio-system -->" in cur:
            report["skipped"].append(pc)
        else:
            with open(pc, "a", encoding="utf-8", newline="") as f:
                f.write(("\n" if not cur.endswith("\n") else "") + "\n<!-- studio-system -->\n" + section)
            report["made"].append(pc + " (section appended)")
    rewrite_guide_table(cfg, hub)
    summary(root)
    print("\nnext: fill board.config.json (terms, schedule, panels) and every <describe ...>, then add studios:")
    print("  python %s/board/scaffold.py studio <key> --prefix XX --label \"Name\"" % hub_rel)
    print("  python %s/board/start.py        -> http://127.0.0.1:%d/" % (hub_rel, cfg.get("port", 8790)))
    return 0


# ---------------------------------------------------------------- studio

def rewrite_guide_table(cfg, hub):
    p = os.path.join(hub, "TASKS_GUIDE.md")
    if not os.path.isfile(p):
        return False
    txt = read(p)
    m = re.search(r"(<!-- studios:begin -->\r?\n)(.*?)(<!-- studios:end -->)", txt, re.S)
    if not m:
        return False
    eol = "\r\n" if "\r\n" in m.group(1) else "\n"
    head = [ln for ln in m.group(2).splitlines() if ln.strip()][:2]
    if len(head) < 2:
        head = ["| Key | Label | Board owner | Prefix | General thread | Ready file | Queue owner |", "|---|---|---|---|---|---|---|"]
    hub_rel = os.path.relpath(hub, cfg.get("_root", os.path.dirname(hub))).replace("\\", "/")
    rows = ["| %s | %s | %s | %s- | GEN-%s | %s | %s |" % (s["key"], s.get("label", s["key"]), s["owner"], s["prefix"], s["key"],
            ("`%s/ready/%s.md`" % (hub_rel, s["owner"])) if s.get("ready", True) else "none", s.get("queue_owner") or s["owner"])
            for s in cfg.get("studios", [])]
    new = txt[:m.start(2)] + eol.join(head + rows) + eol + txt[m.end(2):]
    if new != txt:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        os.replace(tmp, p)
        report["made"].append(p + " (studio table)")
    return True


def cmd_studio(a):
    cfgp = os.path.abspath(a.config or os.environ.get("STUDIO_BOARD_CONFIG") or os.path.join(HERE, "board.config.json"))
    if not os.path.isfile(cfgp):
        print("no board.config.json at %s: run this from the project's <hub>/board/ copy, or pass --config" % cfgp, file=sys.stderr)
        return 2
    cfg = json.load(open(cfgp, encoding="utf-8-sig"))
    board = os.path.dirname(cfgp)
    hub = os.path.dirname(board)
    root = os.path.abspath(os.path.join(board, cfg.get("root", "../..")))
    cfg["_root"] = root
    key = a.key.strip().lower()
    if not re.match(r"^[a-z][a-z0-9_-]{0,30}$", key):
        print("key: lower-case letters, digits, - or _ (e.g. art, audio, level-design)", file=sys.stderr)
        return 2
    prefix = a.prefix.strip().upper()
    if not re.match(r"^[A-Z][A-Z0-9]{0,9}$", prefix):
        print("prefix: 1-10 upper-case letters / digits, starting with a letter (e.g. ART)", file=sys.stderr)
        return 2
    owner = (a.owner or key + "-studio").strip()
    studios = cfg.setdefault("studios", [])
    for s in studios:
        if s["key"] == key and not a.force:
            print("studio %s is already in the config (use --force to refresh its files)" % key, file=sys.stderr)
            return 2
        if s["key"] != key and (s["prefix"].upper() == prefix or s["owner"].lower() == owner.lower()):
            print("prefix %s or owner %s is already used by %s" % (prefix, owner, s["key"]), file=sys.stderr)
            return 2
    n = len(studios)
    entry = {"key": key, "prefix": prefix, "owner": owner, "label": a.label or key.title(),
             "icon": a.icon if a.icon in ICONS else (a.icon or ICONS[n % len(ICONS)]),
             "color": a.color or COLORS[n % len(COLORS)], "ready": not a.no_ready, "queue_owner": a.queue_owner or owner}
    if a.icon and a.icon not in ICONS:
        print("note: icon '%s' is not built in (%s); the board shows a dot" % (a.icon, ", ".join(ICONS)))
    studios[:] = [s for s in studios if s["key"] != key] + [entry]
    save_json(cfgp, {k: v for k, v in cfg.items() if not k.startswith("_")})
    report["made"].append(cfgp + " (studio %s)" % key)
    tdir = os.path.join(SRC, "templates", "studio")
    if not os.path.isdir(tdir):
        tdir = os.path.join(hub, "templates", "studio")
    if not os.path.isdir(tdir):
        print("studio templates not found (templates/studio next to board/, or <hub>/templates/studio)", file=sys.stderr)
        return 2
    hub_rel = os.path.relpath(hub, root).replace("\\", "/")
    vals = values(cfg, root, hub_rel, cfg.get("runbook") or SRC)
    vals.update(KEY=key, LABEL=entry["label"], PREFIX=prefix, OWNER=owner, QUEUE_OWNER=entry["queue_owner"])
    sd = os.path.join(root, "studios", key)
    for d in ("cards", "lab", "tools", "staged", "backup", "logs"):
        os.makedirs(os.path.join(sd, d), exist_ok=True)
    for f in ("CLAUDE.md", "AGENT.md", "NOTES.md", "BRIEF.md"):
        write_new(os.path.join(sd, f), fill(read(os.path.join(tdir, f)), vals), a.force)
    rewrite_guide_table(cfg, hub)
    summary(root)
    print("\nnext: fill studios/%s/AGENT.md and BRIEF.md (<describe ...>), restart the board when the user is not using it" % key)
    print("(the new studio shows after a restart), then start the session from the user's turn with BRIEF.md.")
    return 0


def summary(root):
    for p in report["made"]:
        print("made     " + os.path.relpath(p.split(" (")[0], root).replace("\\", "/") + (" (" + p.split(" (", 1)[1] if " (" in p else ""))
    for p in report["skipped"]:
        print("kept     " + os.path.relpath(p, root).replace("\\", "/") + "  (exists; --force to replace)")
    left = []
    for p in report["made"]:
        p = p.split(" (")[0]
        if p.endswith((".md", ".txt")) and os.path.isfile(p):
            k = read(p).count("<describe")
            if k:
                left.append("%s (%d)" % (os.path.relpath(p, root).replace("\\", "/"), k))
    if left:
        print("\n<describe ...> left to fill: " + ", ".join(left))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("root")
    p.add_argument("--name", required=True)
    p.add_argument("--hub", default="studio-hub")
    p.add_argument("--port", type=int, default=8790)
    p.add_argument("--no-queue", action="store_true")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("studio")
    p.add_argument("key")
    p.add_argument("--prefix", required=True)
    p.add_argument("--label", default="")
    p.add_argument("--owner", default="")
    p.add_argument("--icon", default="")
    p.add_argument("--color", default="")
    p.add_argument("--queue-owner", default="")
    p.add_argument("--no-ready", action="store_true")
    p.add_argument("--config", default=None)
    p.add_argument("--force", action="store_true")
    a = ap.parse_args()
    return cmd_init(a) if a.cmd == "init" else cmd_studio(a)


if __name__ == "__main__":
    sys.exit(main())
