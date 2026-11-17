"""Studio board: a small local web tool over the studios' task register (Python stdlib only).

Serves index.html and a JSON API over the register (PROPOSALS.md: read / write, one block per write), the studios' progress notes,
the user's decision log, and optional panels: a requests inbox (read-only), an integration bundle with a "merge" button, and a
read-only view of the shared-resource queue (queue/resq.py) with the user's Hold / Release button.
Bound to 127.0.0.1. Everything project-specific comes from board.config.json.

  python server.py [--config PATH] [--port N]

Config: --config, else env STUDIO_BOARD_CONFIG, else board.config.json next to this file.
"""
import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
GEN_RE = re.compile(r"^GEN-([A-Za-z0-9_-]{1,40})$")   # a studio's general thread (no register block)

# Fixed stages. A project may rename the word written in the register ("word") and the text shown ("label"),
# and switch off the optional ones (no build -> no HANDOFF / LIVE).
STATUS_KEYS = ["PROPOSED", "APPROVED", "IN WORK", "RESULT", "ACCEPTED", "HANDOFF", "LIVE", "BACKLOG", "REJECTED", "CLOSED"]
OPTIONAL_STATUSES = ("HANDOFF", "LIVE", "BACKLOG")
STAGE_COLUMN = {"PROPOSED": "proposed", "APPROVED": "work", "IN WORK": "work", "RESULT": "result", "ACCEPTED": "done",
                "HANDOFF": "done", "LIVE": "live", "BACKLOG": "backlog", "REJECTED": "rejected", "CLOSED": "closed"}

DEFAULTS = {
    "project": "Project",
    "app_id": "studio-board",
    "port": 8790,
    "root": "../..",
    "paths": {"register": "../data/PROPOSALS.md", "decisions": "../data/decisions.jsonl", "progress": "../data/progress",
              "bundle": "../data/bundle.json", "requests": "../requests/REQUESTS.md", "ready": "../ready",
              "build_marker": "../BUILD_RUNNING", "queue": "../queue"},
    "image_bases": ["", "studio-hub", "studios"],
    "terms": {"studio": "studio", "studios": "studios", "manager": "manager", "user": "you", "result": "result",
              "build": "build", "ready_file": "ready file"},
    "studios": [],
    "statuses": {},
    "fields": ["what", "why", "visual", "scope", "cost", "decision", "priority", "result", "accept", "handoff"],
    "image_fields": ["visual", "result"],
    "priority": {"default": 3, "names": {"1": "urgent", "2": "high", "3": "normal", "4": "low"}},
    "stale_hours": 3,
    "schedule": {"handover": "", "deadline": "", "build": ""},
    "panels": {"requests": {"enabled": False, "title": "Requests inbox"},
               "bundle": {"enabled": False, "owner": "", "title": "Bundle", "button": "Merge this bundle"},
               "queue": {"enabled": False, "title": "Queue"},
               "system": {"enabled": True, "gpu": ""}},
    "queue": {"turn_max_min": 20, "grace_s": 60, "turn_tail_min": 3, "short_max_min": 3, "gap_ban_min": 60,
              "priority_owners": ["build*", "nightly*"], "hold_line": "USER HOLD", "gate_cmd": "", "on_hold_url": ""},
}

CFG = {}            # resolved config (absolute paths) - filled by load_config()
WRITE_LOCK = threading.Lock()
WORD = {}           # status key -> word written in the register
KEY_OF = {}         # word -> status key
STATUS_START = None
PRIO_RE = re.compile(r"^\s*P([1-4])\b", re.I)


# ---------------------------------------------------------------- config

def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def config_path(arg=None):
    return os.path.abspath(arg or os.environ.get("STUDIO_BOARD_CONFIG") or os.path.join(HERE, "board.config.json"))


def load_config(path=None, port=None):
    """read board.config.json, merge it over DEFAULTS, resolve paths, build the status tables. Returns CFG."""
    global STATUS_START
    p = config_path(path)
    with open(p, encoding="utf-8-sig") as f:
        raw = json.load(f)
    c = _merge(DEFAULTS, raw)
    base = os.path.dirname(p)
    c["config_file"] = p
    c["root"] = os.path.abspath(os.path.join(base, c["root"]))
    c["paths"] = {k: os.path.abspath(os.path.join(base, v)) if v else "" for k, v in c["paths"].items()}
    c["cursor"] = os.path.join(os.path.dirname(c["paths"]["decisions"]), "relayed.cursor")
    if port:
        c["port"] = int(port)
    # studios
    seen = set()
    studios = []
    for s in c.get("studios") or []:
        key = str(s.get("key", "")).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        studios.append({"key": key, "prefix": str(s.get("prefix") or key.upper()).strip(),
                        "owner": str(s.get("owner") or key + "-studio").strip(), "label": str(s.get("label") or key),
                        "icon": str(s.get("icon") or ""), "color": str(s.get("color") or "#7c8590"),
                        "ready": bool(s.get("ready", True)), "queue_owner": str(s.get("queue_owner") or s.get("owner") or key)})
    c["studios"] = studios
    # statuses
    WORD.clear()
    KEY_OF.clear()
    st = {}
    for k in STATUS_KEYS:
        o = (c.get("statuses") or {}).get(k) or {}
        w = re.sub(r"\s+", " ", str(o.get("word") or k).strip().upper())
        if not re.match(r"^[A-Z][A-Z ]{1,30}$", w) or w in KEY_OF:
            raise ValueError("status %s: bad or duplicate word %r" % (k, w))
        WORD[k] = w
        KEY_OF[w] = k
        st[k] = {"word": w, "label": str(o.get("label") or k.title().replace("In Work", "In work")),
                 "enabled": bool(o.get("enabled", True)) if k in OPTIONAL_STATUSES else True}
    c["statuses"] = st
    words = sorted(KEY_OF, key=len, reverse=True)
    STATUS_START = re.compile(r"^(" + "|".join(re.escape(w) for w in words) + r")\b")
    pr = c.get("priority") or {}
    c["priority"] = {"default": int(pr.get("default", 3)) if str(pr.get("default", 3)).isdigit() else 3,
                     "names": {int(k): str(v) for k, v in (pr.get("names") or {}).items() if str(k).isdigit()}}
    CFG.clear()
    CFG.update(c)
    return CFG


def W(key):
    return WORD.get(key, key)


def enabled(key):
    return CFG["statuses"].get(key, {}).get("enabled", True)


def studio_by(key=None, owner=None, prefix=None):
    for s in CFG["studios"]:
        if key and s["key"] == str(key).lower():
            return s
        if owner and s["owner"].lower() == str(owner).lower():
            return s
        if prefix and s["prefix"].lower() == str(prefix).lower():
            return s
    return None


def studio_of(name, bid=""):
    """the configured studio for a header owner name / thread name / task id (None if unknown)"""
    n = str(name or "").strip().lower()
    s = studio_by(key=n) or studio_by(owner=n)
    if s:
        return s
    m = re.match(r"^([A-Za-z][A-Za-z0-9]*)-\d+$", bid or "")
    return studio_by(prefix=m.group(1)) if m else None


def prio_of(fields):
    m = PRIO_RE.match(fields.get("priority", "") or "")
    return int(m.group(1)) if m else CFG["priority"]["default"]


# ---------------------------------------------------------------- file io

def read_file(path):
    """-> (text, meta); text keeps the original line endings."""
    with open(path, "rb") as f:
        raw = f.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    body = raw[3:] if bom else raw
    try:
        text, enc = body.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, enc = body.decode("cp1252"), "cp1252"
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return text, {"raw": raw, "bom": bom, "enc": enc, "eol": "\r\n" if crlf > lf else "\n"}


class Conflict(Exception):
    pass


class BadRequest(Exception):
    pass


def write_file(path, text, meta):
    """temp file + os.replace; refuses if the file changed on disk since it was read"""
    data = text.encode(meta["enc"])
    if meta["bom"]:
        data = b"\xef\xbb\xbf" + data
    fd, tmp = tempfile.mkstemp(prefix=".board_", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        with open(path, "rb") as f:
            if f.read() != meta["raw"]:
                raise Conflict("The register changed on disk while saving. Reloaded; please try again.")
        for i in range(10):
            try:
                os.replace(tmp, path)
                tmp = None
                break
            except PermissionError:
                if i == 9:
                    raise
                time.sleep(0.15)
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------- images

def _inside_root(p):
    try:
        rr = os.path.normcase(os.path.realpath(CFG["root"]))
        pp = os.path.normcase(os.path.realpath(p))
        return os.path.commonpath([rr, pp]) == rr
    except ValueError:
        return False


def resolve_image(token, prev_dir=None):
    """token as written -> path relative to the project root (forward slashes) if it is an existing image inside it"""
    t = str(token or "").strip().strip("`'\"").replace("\\", "/")
    if not t or os.path.splitext(t)[1].lower() not in IMG_EXT or ".." in t.split("/"):
        return None
    root = CFG["root"]
    cands = []
    if re.match(r"^[A-Za-z]:/", t) or t.startswith("/"):
        cands.append(t)
    else:
        if "/" not in t and prev_dir:
            cands.append(os.path.join(root, prev_dir, t))
        for b in CFG["image_bases"]:
            cands.append(os.path.join(root, b, t))
    for c in cands:
        c = os.path.abspath(c)
        if os.path.isfile(c) and _inside_root(c):
            return os.path.relpath(c, root).replace("\\", "/")
    return None


IMG_TOKEN = re.compile(r"[A-Za-z0-9_.:/\\\-]+\.(?:jpg|jpeg|png|webp|gif)\b", re.I)


def extract_images(text):
    out, prev = [], None
    for m in IMG_TOKEN.finditer(text or ""):
        rel = resolve_image(m.group(0), prev)
        if rel:
            prev = os.path.dirname(rel)
        out.append({"raw": m.group(0), "rel": rel})
    return out


# ---------------------------------------------------------------- register parsing

HEADER_RE = re.compile(r"^##\s+(\S+)\s+(\S+)\s+(.*)$")
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_ /-]{0,24}):(?:[ \t]|$)")
SEP_RE = re.compile(r"\u2014|--")      # the em dash (or two hyphens) before the status


def block_hash(block_text):
    return hashlib.sha1(block_text.replace("\r\n", "\n").rstrip().encode("utf-8")).hexdigest()[:16]


def stage_of(status):
    """the LAST status word outside brackets -> status key (None if there is none)"""
    s = re.sub(r"\([^)]*\)", " ", status or "").upper()
    found = []
    for w in sorted(KEY_OF, key=len, reverse=True):     # longest words first, so 'NOT DONE' never also counts as 'DONE'
        for m in re.finditer(r"(?<![A-Z])" + re.escape(w) + r"(?![A-Z])", s):
            found.append((m.start(), KEY_OF[w]))
        s = re.sub(r"(?<![A-Z])" + re.escape(w) + r"(?![A-Z])", lambda m: "#" * len(m.group(0)), s)
    return max(found)[1] if found else None


def split_header(line):
    """'## ID  owner  title  — STATUS' -> dict with the status position (relative to the line)"""
    body = line.rstrip("\r\n")
    m = HEADER_RE.match(body)
    if not m:
        return None
    rest_start, rest = m.start(3), m.group(3)
    seps = [(x.start(), x.end()) for x in SEP_RE.finditer(rest)]
    pick = None
    for a, b in seps:   # first separator followed by a status word
        if STATUS_START.match(rest[b:].lstrip()):
            pick = (a, b)
            break
    if pick is None and seps:
        pick = seps[-1]
    if pick is None:
        return {"id": m.group(1), "owner": m.group(2), "title": rest.strip(), "status": "", "status_pos": None}
    after = rest[pick[1]:]
    lead = len(after) - len(after.lstrip())
    return {"id": m.group(1), "owner": m.group(2), "title": rest[:pick[0]].strip(), "status": after.strip(),
            "status_pos": rest_start + pick[1] + lead}


def parse_fields(lines):
    """lines without the header -> (fields, order, extras)"""
    fields, order, extras, cur = {}, [], [], None
    for ln in lines:
        if not ln.strip():
            cur = None
            continue
        if ln[:1] in (" ", "\t"):
            if cur is not None:
                fields[cur] = (fields[cur] + " " + ln.strip()).strip()
            else:
                extras.append(ln.strip())
            continue
        m = FIELD_RE.match(ln)
        if m:
            key = m.group(1).strip().lower()
            val = ln[m.end():].strip()
            if key in fields:
                extras.append("duplicate field " + key + ": " + val)
                cur = None
                continue
            fields[key] = val
            order.append(key)
            cur = key
        else:
            extras.append(ln.strip())
            cur = None
    return fields, order, extras


def parse_register(text):
    """-> {blocks, issues}. Cards start after the first '---' line. Each block carries start / end offsets into text."""
    lines = text.splitlines(keepends=True)
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln)
    offs.append(pos)
    first = 0
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            first = i + 1
            break
    starts = [i for i in range(first, len(lines)) if lines[i].startswith("## ")]
    blocks, issues, seen = [], [], {}
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(lines)
        btxt = "".join(lines[s:e])
        h = split_header(lines[s])
        if not h:
            issues.append("line %d: header not parsed: %s" % (s + 1, lines[s].strip()))
            continue
        fields, order, extras = parse_fields([ln.rstrip("\r\n") for ln in lines[s + 1:e]])
        st = stage_of(h["status"])
        sd = studio_of(h["owner"], h["id"])
        b = {"id": h["id"], "studio": h["owner"], "skey": sd["key"] if sd else "", "title": h["title"],
             "status": h["status"], "stage": st, "column": STAGE_COLUMN.get(st, "proposed"),
             "fields": fields, "order": order, "extras": extras, "line": s + 1, "hash": block_hash(btxt),
             "start": offs[s], "end": offs[e],
             "images": {f: extract_images(fields.get(f, "")) for f in CFG["image_fields"]}}
        b["priority"] = prio_of(fields)
        if not h["status"]:
            issues.append("%s (line %d): no '\u2014 STATUS' in the header" % (h["id"], s + 1))
        elif not STATUS_START.match(h["status"]):
            issues.append("%s (line %d): status does not start with a status word: %s" % (h["id"], s + 1, h["status"]))
        if st is None:
            issues.append("%s: no status word found; shown under %s" % (h["id"], CFG["statuses"]["PROPOSED"]["label"]))
        if extras:
            issues.append("%s: %d line(s) outside the field format" % (h["id"], len(extras)))
        if not sd:
            issues.append("%s: owner '%s' is not a configured studio" % (h["id"], h["owner"]))
        if h["id"] in seen:
            issues.append("%s: duplicate id (lines %d and %d)" % (h["id"], seen[h["id"]], s + 1))
        seen[h["id"]] = s + 1
        blocks.append(b)
    for b in blocks:
        if sum(1 for x in blocks if x["id"] == b["id"]) > 1:
            b["duplicate"] = True
    return {"blocks": blocks, "issues": issues}


def public_block(b):
    return {k: v for k, v in b.items() if k not in ("start", "end")}


# ---------------------------------------------------------------- requests inbox (read-only)

def parse_inbox(text):
    """'## Section' then '### ID title — tag' items with '- key: value' lines"""
    lines = text.splitlines()
    section, items, cur, curkey, fence = None, [], None, None, False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if ln.startswith("## "):
            section, cur = ln[3:].strip().lower(), None
            continue
        if ln.startswith("### ") and section is not None:
            parts = ln[4:].strip().split(None, 1)
            title = parts[1] if len(parts) > 1 else ""
            tag = ""
            if "\u2014" in title:
                title, tag = [x.strip() for x in title.rsplit("\u2014", 1)]
            cur = {"id": parts[0] if parts else "?", "title": title, "tag": tag, "section": section, "line": i + 1, "fields": []}
            items.append(cur)
            curkey = None
            continue
        if cur is None:
            continue
        m = re.match(r"^-\s+([^:]{1,40}):\s?(.*)$", ln)
        if m:
            cur["fields"].append([m.group(1).strip(), m.group(2).strip()])
            curkey = len(cur["fields"]) - 1
        elif ln[:1] in (" ", "\t") and ln.strip() and curkey is not None:
            cur["fields"][curkey][1] = (cur["fields"][curkey][1] + " " + ln.strip()).strip()
        elif ln.strip():
            cur["fields"].append(["note", ln.strip()])
            curkey = len(cur["fields"]) - 1
    for it in items:
        fd = {k.lower(): v for k, v in it["fields"]}
        it["status"] = fd.get("status", "")
        it["closed"] = bool((it["section"] or "").startswith("closed") or it["tag"].upper().startswith("CLOSED")
                            or it["status"].lower().startswith("closed"))
        it["images"] = extract_images(" ".join(v for _, v in it["fields"]))
    return items


# ---------------------------------------------------------------- writing helpers

def now_stamp():
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def now_iso():
    return _dt.datetime.now().isoformat(timespec="seconds")


def clean_words(s, limit=2000):
    s = (s or "").replace("\r", " ").replace("\n", " ").replace('"', "'").strip()
    return re.sub(r"\s+", " ", s)[:limit]


def field_prefix(key):
    return (key + ":").ljust(8) + " "


def set_field(lines, eol, key, value):
    """lines with their own endings (index 0 = header): replace or insert one field (one line)"""
    order = CFG["fields"]
    idx = None
    for i in range(1, len(lines)):
        m = FIELD_RE.match(lines[i].rstrip("\r\n"))
        if m and m.group(1).strip().lower() == key:
            idx = i
            break
    if idx is not None:
        old = lines[idx]
        ending = old[len(old.rstrip("\r\n")):] or eol
        m = re.match(r"^([^:]+:)([ \t]*)(.*)$", old.rstrip("\r\n"))
        pre = (m.group(1) + m.group(2)) if (m and m.group(3).strip() and m.group(2)) else field_prefix(m.group(1)[:-1] if m else key)
        j = idx + 1
        while j < len(lines) and lines[j][:1] in (" ", "\t") and lines[j].strip():
            j += 1
        lines[idx:j] = [pre + value + ending]
        return
    rank = order.index(key) if key in order else len(order)
    ins = 1
    for i in range(1, len(lines)):
        m = FIELD_RE.match(lines[i].rstrip("\r\n"))
        if m:
            k = m.group(1).strip().lower()
            if k in order and order.index(k) < rank:
                j = i + 1
                while j < len(lines) and lines[j][:1] in (" ", "\t") and lines[j].strip():
                    j += 1
                ins = j
    if ins == len(lines) and lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += eol
    lines.insert(ins, field_prefix(key) + value + eol)


def set_status(lines, new_status):
    hd = split_header(lines[0])
    hl = lines[0]
    ending = hl[len(hl.rstrip("\r\n")):]
    if hd["status_pos"] is None:
        lines[0] = hl.rstrip("\r\n") + "  \u2014 " + new_status + ending
    else:
        lines[0] = hl[:hd["status_pos"]] + new_status + ending


def log_decision(rec):
    path = CFG["paths"]["decisions"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def one_block(text, bid):
    reg = parse_register(text)
    matches = [b for b in reg["blocks"] if b["id"] == bid]
    if not matches:
        raise Conflict("Task %s is not in the register any more. Reloaded." % bid)
    if len(matches) > 1:
        raise Conflict("Task id %s appears twice in the register; not writing. Ask the %s to fix it." % (bid, CFG["terms"]["manager"]))
    return matches[0], reg


# ---------------------------------------------------------------- progress notes (append-only, one jsonl per task)

def progress_path(bid):
    if not ID_RE.match(bid or ""):
        raise BadRequest("bad task id")
    return os.path.join(CFG["paths"]["progress"], bid + ".jsonl")


def append_note(bid, by, pct, note, images, answer=False, kind=None, options=None, reply_to=None):
    path = progress_path(bid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = _dt.datetime.now()
    rec = {"ts": now.isoformat(timespec="microseconds"),
           "nid": "%s-%s" % (now.strftime("%Y%m%dT%H%M%S.%f"), os.urandom(2).hex()),
           "by": by, "pct": pct, "note": note, "images": list(images or [])}
    if answer:
        rec["answer"] = True
    if kind:
        rec["kind"] = kind
    if options:
        rec["options"] = list(options)
    if reply_to:
        rec["reply_to"] = reply_to
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read_notes(bid):
    """-> notes oldest first; bad lines skipped"""
    try:
        path = progress_path(bid)
    except BadRequest:
        return []
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for lineno, ln in enumerate(f, 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            pct = r.get("pct")
            pct = None if (not isinstance(pct, (int, float)) or isinstance(pct, bool)) else max(0, min(100, int(round(pct))))
            imgs = [{"raw": p, "rel": resolve_image(p)} for p in (r.get("images") or [])[:20] if isinstance(p, str)]
            out.append({"ts": str(r.get("ts", "")), "by": str(r.get("by", "")), "pct": pct, "note": str(r.get("note", "")),
                        "images": imgs, "answer": bool(r.get("answer")), "kind": str(r.get("kind", "") or ""),
                        "reply_to": str(r.get("reply_to", "") or ""), "nid": str(r.get("nid", "") or ("%s#%d" % (r.get("ts", ""), lineno))),
                        "options": [str(o)[:120] for o in (r.get("options") or []) if isinstance(o, (str, int, float))][:8]})
    return out


def relayed_cursor():
    try:
        with open(CFG["cursor"], encoding="utf-8") as f:
            return max(0, int(f.read().strip() or 0))
    except (OSError, ValueError):
        return 0


def read_decisions():
    """-> {id: [records, each with 'line' = 0-based index among the non-empty lines]}"""
    out = {}
    try:
        with open(CFG["paths"]["decisions"], encoding="utf-8", errors="replace") as f:
            i = -1
            for ln in f:
                if not ln.strip():
                    continue          # line numbers count non-empty lines, like relayed.cursor
                i += 1
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("id"):
                    r["line"] = i
                    out.setdefault(str(r["id"]), []).append(r)
    except OSError:
        pass
    return out


QUESTION_ACTIONS = ("question",)
BUILD_ACTIONS = ("live", "revert")   # written by mark_live.py, not by the user


def progress_summary(bid, decisions=None, cursor=0):
    notes = read_notes(bid)
    studio = [n for n in notes if n["by"] != "user"]
    user_dec = (decisions or {}).get(bid, [])
    seen = {(d.get("ts"), d.get("comment", "")) for d in user_dec}
    answers = [d for d in user_dec if d.get("action") == "answer"]
    withdrawn = {n["reply_to"]: n for n in studio if n["kind"] == "withdraw"}
    tl = []
    for n in studio:
        if n["kind"] == "withdraw":
            continue
        if n["kind"] == "ask":
            rep = [d for d in answers if str(d.get("reply_to", "")) == n["nid"]]
            wd = withdrawn.get(n["nid"]) if withdrawn.get(n["nid"], {}).get("by") == n["by"] else None
            st = ("answered" if rep[-1]["line"] >= cursor else "passed") if rep else ("withdrawn" if wd else "open")
            tl.append(dict(n, kind="ask", ask_state=st, reply=str(rep[-1].get("comment", "")) if rep else "",
                           withdraw_reason=wd["note"] if wd else "", withdraw_ts=wd["ts"] if wd else ""))
        else:
            tl.append(dict(n, kind="answer" if n["answer"] else "note"))
    for n in notes:   # user notes the decision log does not hold (log rotated): shown without a delivery state
        if n["by"] == "user" and (n["ts"], n["note"]) not in seen and n["kind"] != "reply":
            tl.append(dict(n, kind="question", action="question", delivery=None, line=None))
    for d in user_dec:
        act, ts = str(d.get("action", "")), str(d.get("ts", ""))
        if act == "answer":
            continue   # shown on its ask
        delivery = "waiting" if d["line"] >= cursor else "passed"
        if act in QUESTION_ACTIONS and any(n["ts"] > ts for n in studio):
            delivery = "answered"
        if act in BUILD_ACTIONS:
            tl.append({"kind": "build", "action": act, "ts": ts, "by": "build", "note": str(d.get("comment", "")),
                       "status": str(d.get("status", "")), "build": str(d.get("build", "")), "pct": None, "images": [],
                       "delivery": None, "line": d["line"]})
            continue
        tl.append({"kind": "question" if act in QUESTION_ACTIONS else "decision", "action": act, "ts": ts, "by": "user",
                   "note": str(d.get("comment", "")), "status": str(d.get("status", "")), "pct": None, "images": [],
                   "delivery": delivery, "line": d["line"], "to": str(d.get("to", "")), "from": str(d.get("from", ""))})
    tl.sort(key=lambda x: (x["ts"], 0 if x["by"] in ("user", "build") else 1))
    pct = next((n["pct"] for n in reversed(studio) if n["pct"] is not None), None)
    qs = [x for x in tl if x["kind"] == "question"]
    open_q = bool(qs) and not any(n["ts"] > qs[-1]["ts"] for n in studio)
    open_asks = [x for x in tl if x["kind"] == "ask" and x["ask_state"] == "open"]
    return {"notes": list(reversed(tl)), "pct": pct, "last": tl[-1]["ts"] if tl else None,
            "last_studio": studio[-1]["ts"] if studio else None, "open_question": open_q,
            "open_asks": len(open_asks), "cursor": cursor}


def gen_threads():
    try:
        names = os.listdir(CFG["paths"]["progress"])
    except OSError:
        return []
    return sorted(n[:-6] for n in names if n.endswith(".jsonl") and GEN_RE.match(n[:-6]))


def gen_studio(gid):
    g = GEN_RE.match(gid or "")
    if not g:
        return None
    return studio_of(g.group(1))


def collect_open_asks(blocks, gens):
    out = []
    for b in blocks + gens:
        for n in b["progress"]["notes"]:
            if n.get("kind") == "ask" and n.get("ask_state") == "open":
                out.append({"id": b["id"], "studio": n["by"], "skey": b.get("skey", ""), "title": b.get("title", ""),
                            "general": b.get("general", False), "ts": n["ts"], "nid": n["nid"], "note": n["note"],
                            "images": n["images"], "options": n.get("options", [])})
    out.sort(key=lambda x: x["ts"])
    return out


# ---------------------------------------------------------------- user actions

def do_answer(req):
    """the user's reply to a studio ask: a progress note (by user) + decision 'answer'"""
    bid = str(req.get("id", "")).strip()
    reply_to = str(req.get("reply_to", "")).strip()
    text = clean_words(req.get("text", ""), 4000)
    if not text:
        raise BadRequest("write an answer first")
    title, status = "", ""
    if not GEN_RE.match(bid):
        rtext, _ = read_file(CFG["paths"]["register"])
        b, _ = one_block(rtext, bid)
        title, status = b["title"], b["status"]
    with WRITE_LOCK:
        notes = read_notes(bid)
        asks = [n for n in notes if n["kind"] == "ask" and n["by"] != "user" and n["nid"] == reply_to]
        if not asks:
            raise Conflict("That question is not in the %s thread any more. Reloaded." % bid)
        ask = asks[0]
        if any(n["kind"] == "withdraw" and n["reply_to"] == ask["nid"] and n["by"] == ask["by"] for n in notes):
            raise Conflict("%s withdrew this question. Reloaded." % ask["by"])
        if any(d.get("action") == "answer" and d.get("reply_to") == ask["nid"] for d in read_decisions().get(bid, [])):
            raise Conflict("You already answered this question. Reloaded.")
        rec = append_note(bid, "user", None, text, [], kind="reply", reply_to=ask["nid"])
        log_decision({"ts": rec["ts"], "id": bid, "studio": ask["by"], "action": "answer", "comment": text,
                      "reply_to": ask["nid"], "question": ask["note"][:300], "status": status or "general thread",
                      "title": title or ("general question from %s" % ask["by"])})
    return {"ok": True, "id": bid, "ts": rec["ts"]}


def do_question(req):
    """the user's question / note to the studio of a card"""
    bid = str(req.get("id", "")).strip()
    note = clean_words(req.get("question", "") or req.get("comment", ""), 4000)
    if not note:
        raise BadRequest("write your question first")
    if GEN_RE.match(bid):
        s = gen_studio(bid)
        owner, status, title = (s["owner"] if s else bid[4:]), "general thread", "general thread"
    else:
        text, _ = read_file(CFG["paths"]["register"])
        b, _ = one_block(text, bid)
        owner, status, title = b["studio"], b["status"], b["title"]
    with WRITE_LOCK:
        rec = append_note(bid, "user", None, note, [], kind="question")
        log_decision({"ts": rec["ts"], "id": bid, "studio": owner, "action": "question", "comment": note,
                      "status": status, "title": title})
    return {"ok": True, "id": bid, "ts": rec["ts"]}


# action: (required stage, field written, word, new status key or literal builder)
def _actions():
    return {
        "approve": ("PROPOSED", "decision", "Approve.", W("APPROVED")),
        "reject": ("PROPOSED", "decision", "Reject.", W("REJECTED")),
        "accept": ("RESULT", "accept", "Accept.", W("ACCEPTED")),
        "reject_result": ("RESULT", "accept", "Rework.", "%s, %s (result rejected: rework)" % (W("APPROVED"), W("IN WORK"))),
        "close": (None, None, "Close.", None),
        "reopen": ("CLOSED", None, None, "%s (reopened by user)" % W("APPROVED")),
        "backlog": ("PROPOSED", "decision", "Backlog.", "%s (user: not now)" % W("BACKLOG")),
        "approve_backlog": ("BACKLOG", "decision", "Approve (from backlog).", "%s (from backlog)" % W("APPROVED")),
        "reject_backlog": ("BACKLOG", "decision", "Reject (from backlog).", W("REJECTED")),
    }


KEEP_OLD_FIELD = ("close", "approve_backlog", "reject_backlog")   # append to the field instead of replacing it
NOT_CLOSABLE = ("CLOSED", "REJECTED", "ACCEPTED", "HANDOFF", "LIVE")


def do_decide(req):
    bid = str(req.get("id", "")).strip()
    action = str(req.get("action", "")).strip()
    h = str(req.get("hash", "")).strip()
    comment = clean_words(req.get("comment", ""))
    acts = _actions()
    if action not in acts:
        raise BadRequest("unknown action: " + action)
    if "backlog" in action and not enabled("BACKLOG"):
        raise BadRequest("the backlog is switched off in board.config.json")
    need, field, word, new_status = acts[action]
    if action == "close":
        reason = comment.replace("(", "[").replace(")", "]").replace("\u2014", "-")[:200].strip()
        if not reason:
            raise BadRequest("give a reason for closing")
        new_status = "%s (user: %s)" % (W("CLOSED"), reason)
    path = CFG["paths"]["register"]
    with WRITE_LOCK:
        text, meta = read_file(path)
        b, _ = one_block(text, bid)
        if b["hash"] != h:
            raise Conflict("%s was edited since this page loaded (a %s or the %s changed it). Reloaded: please read it again "
                           "and redo your decision." % (bid, CFG["terms"]["studio"], CFG["terms"]["manager"]))
        if action == "close":
            if b["stage"] in NOT_CLOSABLE:
                raise Conflict("%s is %s; it cannot be closed. Nothing written." % (bid, b["status"] or "?"))
            field = "accept" if b["fields"].get("decision", "").strip() else "decision"
        elif b["stage"] != need:
            raise Conflict("%s is %s now, not %s; nothing written." % (bid, b["status"] or "?", W(need)))
        lines = text[b["start"]:b["end"]].splitlines(keepends=True)
        set_status(lines, new_status)
        stamp = now_stamp()
        if field:
            value = 'user, %s, "%s" (board)' % (stamp, (word + " " + comment).strip())
            old = b["fields"].get(field, "").strip() if action in KEEP_OLD_FIELD else ""
            set_field(lines, meta["eol"], field, (old + " | " + value) if old else value)
        write_file(path, text[:b["start"]] + "".join(lines) + text[b["end"]:], meta)
        log_decision({"ts": now_iso(), "id": bid, "studio": b["studio"], "action": action, "comment": comment,
                      "status": new_status, "title": b["title"]})
    return {"ok": True, "id": bid, "status": new_status, "stamp": stamp}


def do_priority(req):
    bid = str(req.get("id", "")).strip()
    h = str(req.get("hash", "")).strip()
    m = PRIO_RE.match(str(req.get("level", "")))
    if not m:
        raise BadRequest("priority must be P1, P2, P3 or P4")
    new = int(m.group(1))
    path = CFG["paths"]["register"]
    with WRITE_LOCK:
        text, meta = read_file(path)
        b, _ = one_block(text, bid)
        if b["hash"] != h:
            raise Conflict("%s was edited since this page loaded. Reloaded: please set the priority again." % bid)
        old = b["priority"]
        if old == new and b["fields"].get("priority"):
            raise Conflict("%s is already P%d." % (bid, new))
        lines = text[b["start"]:b["end"]].splitlines(keepends=True)
        stamp = now_stamp()
        set_field(lines, meta["eol"], "priority", "P%d (user, %s, board)" % (new, stamp))
        write_file(path, text[:b["start"]] + "".join(lines) + text[b["end"]:], meta)
        log_decision({"ts": now_iso(), "id": bid, "studio": b["studio"], "action": "priority", "from": "P%d" % old,
                      "to": "P%d" % new, "comment": "", "status": b["status"], "title": b["title"]})
    return {"ok": True, "id": bid, "priority": new, "stamp": stamp}


def next_id(blocks, prefix):
    best, width = 0, 2
    for b in blocks:
        m = re.match(r"^" + re.escape(prefix) + r"-(\d+)$", b["id"], re.I)
        if m and int(m.group(1)) >= best:
            best, width = int(m.group(1)), len(m.group(1))
    return "%s-%0*d" % (prefix, width, best + 1)


def clean_path(p):
    p = re.sub(r"\s+", " ", (p or "").strip().strip("`'\"").replace("\\", "/"))
    rootf = CFG["root"].replace("\\", "/").rstrip("/") + "/"
    if p.lower().startswith(rootf.lower()):
        p = p[len(rootf):]
    return p[:400]


def wrap(s, width):
    lines, cur = [], ""
    for w in s.split(" "):
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w) if cur else w
    lines.append(cur)
    return lines


def do_new(req):
    s = studio_by(key=str(req.get("studio", "")).strip())
    if not s:
        raise BadRequest("pick a %s" % CFG["terms"]["studio"])
    title = clean_words(req.get("title", ""), 160).replace("\u2014", "-").replace("--", "-")
    what = clean_words(req.get("what", ""), 4000)
    visual = clean_path(req.get("visual", ""))
    if not title:
        raise BadRequest("a title is needed")
    if not what:
        raise BadRequest("'what' is needed")
    pm = PRIO_RE.match(str(req.get("priority", "") or ("P%d" % CFG["priority"]["default"])))
    if not pm:
        raise BadRequest("priority must be P1, P2, P3 or P4")
    prio = int(pm.group(1))
    path = CFG["paths"]["register"]
    with WRITE_LOCK:
        text, meta = read_file(path)
        reg = parse_register(text)
        nid = next_id(reg["blocks"], s["prefix"])
        status = "%s (user request, board)" % W("APPROVED")
        stamp = now_stamp()
        eol = meta["eol"]
        wl = wrap(what, 140)
        out = ["## %s  %s  %s  \u2014 %s" % (nid, s["owner"], title, status), field_prefix("what") + wl[0]]
        out += ["         " + x for x in wl[1:]]
        out += [field_prefix("why") + "user request (board)", (field_prefix("visual") + visual) if visual else "visual:",
                "scope:", "cost:", 'decision: user, %s, "User request." (board)' % stamp,
                field_prefix("priority") + "P%d (user, %s, board)" % (prio, stamp), "result:", "accept:"]
        if enabled("HANDOFF"):
            out.append("handoff:")
        t = text
        if t and not t.endswith(("\n", "\r")):
            t += eol
        if t and not t.endswith(eol + eol) and not t.endswith("\n\n"):
            t += eol
        t += eol.join(out) + eol
        write_file(path, t, meta)
        log_decision({"ts": now_iso(), "id": nid, "studio": s["owner"], "action": "new_request", "comment": what,
                      "status": status, "title": title, "visual": visual, "priority": "P%d" % prio})
    return {"ok": True, "id": nid, "status": status, "priority": prio}


# ---------------------------------------------------------------- tasks api

MOVED_TO_RE = re.compile(r"(?:(?i:\bas|\bmoved to|\binto|\bsee)|->|\u2192)\s+([A-Z][A-Z0-9]*-\d+)\b")
MOVED_FROM_RE = re.compile(r"(?i:\bwas|\bmoved from|\bfrom)\s+([A-Z][A-Z0-9]*-\d+)\b")


def live_label(status):
    m = re.search(r"\b" + re.escape(W("LIVE")) + r"\s*\(\s*([^,)]+)", status or "")
    return m.group(1).strip() if m else ""


def link_moves(blocks):
    ids = {b["id"] for b in blocks}
    for b in blocks:
        b["live_label"] = live_label(b.get("status", "")) if b.get("stage") == "LIVE" else ""
        lv = [n["ts"] for n in (b.get("progress") or {}).get("notes", []) if n.get("action") == "live"]
        b["live_ts"] = max(lv) if lv else ""
        b["moved_to"] = None
        for m in MOVED_TO_RE.finditer(b.get("status", "")):
            if m.group(1) != b["id"]:
                b["moved_to"] = {"id": m.group(1), "registered": m.group(1) in ids}
                break
    for b in blocks:
        src = [x["id"] for x in blocks if x is not b and x["moved_to"] and x["moved_to"]["id"] == b["id"]]
        own = " ".join([b.get("title", ""), b.get("status", ""), b["fields"].get("decision", "")])
        for m in MOVED_FROM_RE.finditer(own):
            if m.group(1) != b["id"] and m.group(1) in ids and m.group(1) not in src:
                src.append(m.group(1))
        b["moved_from"] = src
    return blocks


def api_tasks():
    text, meta = read_file(CFG["paths"]["register"])
    reg = parse_register(text)
    dec, cur = read_decisions(), relayed_cursor()
    blocks = link_moves([dict(public_block(b), progress=progress_summary(b["id"], dec, cur)) for b in reg["blocks"]])
    gens = []
    for g in gen_threads():
        s = gen_studio(g)
        gens.append({"id": g, "studio": s["owner"] if s else g[4:], "skey": s["key"] if s else "",
                     "title": "general thread of " + (s["label"] if s else g[4:]), "general": True,
                     "progress": progress_summary(g, dec, cur)})
    return {"register": CFG["paths"]["register"], "eol": "CRLF" if meta["eol"] == "\r\n" else "LF",
            "blocks": blocks, "general": gens, "open_asks": collect_open_asks(blocks, gens), "issues": reg["issues"],
            "time": now_stamp()}


def api_config():
    c = CFG
    return {"project": c["project"], "app_id": c["app_id"], "terms": c["terms"], "studios": c["studios"],
            "statuses": c["statuses"], "fields": c["fields"], "image_fields": c["image_fields"],
            "priority": {"default": c["priority"]["default"], "names": {str(k): v for k, v in c["priority"]["names"].items()}},
            "stale_hours": c["stale_hours"], "schedule": c["schedule"],
            "panels": {k: dict(v, enabled=bool(v.get("enabled"))) for k, v in c["panels"].items()},
            "hold": bool(c["panels"]["queue"].get("enabled"))}


def api_requests():
    if not CFG["panels"]["requests"].get("enabled"):
        return {"enabled": False, "items": []}
    p = CFG["paths"]["requests"]
    if not os.path.isfile(p):
        return {"enabled": True, "items": [], "error": "requests file not found: %s" % os.path.basename(p)}
    text, _ = read_file(p)
    return {"enabled": True, "inbox": p, "items": parse_inbox(text), "time": now_stamp()}


# ---------------------------------------------------------------- integration bundle (read + merge request)
# bundle.json belongs to the bundle's owner studio; the board only reads it. A merge request is one decision line.

def read_bundle():
    path = CFG["paths"]["bundle"]
    if not path or not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8-sig") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError("not an object")
        return d, None
    except Exception as e:  # noqa
        return None, "bundle.json not readable: %s" % e


def resolve_log(p):
    t = str(p or "").strip().strip("`'\"").replace("\\", "/")
    if not t or ".." in t.split("/") or os.path.splitext(t)[1].lower() not in (".log", ".txt"):
        return None
    cands = [t] if (re.match(r"^[A-Za-z]:/", t) or t.startswith("/")) else [os.path.join(CFG["root"], b, t) for b in CFG["image_bases"]]
    for c in cands:
        c = os.path.abspath(c)
        if os.path.isfile(c) and _inside_root(c):
            return c
    return None


def tail_lines(path, n=15):
    with open(path, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 65536))
        return f.read().decode("utf-8", errors="replace").splitlines()[-n:]


def bundle_name(d):
    return str(d.get("name") or d.get("branch") or "")


def api_bundle():
    pc = CFG["panels"]["bundle"]
    out = {"enabled": bool(pc.get("enabled")), "exists": False, "error": None, "name": None}
    if not pc.get("enabled"):
        return out
    d, err = read_bundle()
    out.update(exists=d is not None, error=err)
    if d is None:
        return out
    name = bundle_name(d)
    changes = [{"id": str(c.get("id", "")), "what": str(c.get("what", "")), "accepted": c.get("accepted") is not False}
               for c in d.get("changes") or [] if isinstance(c, dict)]
    state = str(d.get("state") or "open").lower()
    st_ts = str(d.get("state_ts") or "")
    reqs = [r for r in read_decisions().get(name, []) if r.get("action") == "merge"] if name else []
    last = reqs[-1] if reqs else None
    pending = bool(last) and state == "open" and str(last.get("ts", "")) >= st_ts
    req = None
    if last:
        req = {"ts": last.get("ts"), "comment": last.get("comment", ""), "line": last["line"],
               "delivery": "waiting" if last["line"] >= relayed_cursor() else "passed"}
    log_tail, log_note = None, None
    if d.get("merge_log"):
        lp = resolve_log(d.get("merge_log"))
        if lp:
            try:
                log_tail = tail_lines(lp, 15)
            except OSError as e:
                log_note = "merge_log not readable: %s" % e
        else:
            log_note = "merge_log not shown (missing, outside the project, or not .log / .txt)"
    out.update(name=name, title=str(d.get("title") or ""), opened=str(d.get("opened") or ""), base=str(d.get("base") or ""),
               changes=changes, state=state, state_ts=st_ts, merged_as=str(d.get("merged_as") or ""),
               merge_log=str(d.get("merge_log") or ""), note=str(d.get("note") or ""), log_tail=log_tail, log_note=log_note,
               merge_request=req, pending=pending, owner=pc.get("owner", ""),
               can_merge=state == "open" and bool(changes) and not pending and bool(name))
    return out


def do_merge(req):
    pc = CFG["panels"]["bundle"]
    if not pc.get("enabled"):
        raise BadRequest("the bundle panel is switched off")
    name = str(req.get("name", "") or req.get("branch", "")).strip()
    comment = clean_words(req.get("comment", ""))
    with WRITE_LOCK:
        d, err = read_bundle()
        if d is None:
            raise Conflict(err or "There is no open bundle. Reloaded.")
        cur = bundle_name(d)
        if not name or name != cur:
            raise Conflict("The bundle changed (now %s). Reloaded: check it and try again." % (cur or "none"))
        if str(d.get("state") or "open").lower() != "open":
            raise Conflict("%s is %s, not open; no merge request sent." % (cur, d.get("state")))
        if not [c for c in (d.get("changes") or []) if isinstance(c, dict)]:
            raise Conflict("%s has no changes yet; nothing to merge." % cur)
        st_ts = str(d.get("state_ts") or "")
        if any(r.get("action") == "merge" and str(r.get("ts", "")) >= st_ts for r in read_decisions().get(cur, [])):
            raise Conflict("A merge of %s is already requested and waiting for %s." % (cur, pc.get("owner") or "its owner"))
        rec = {"ts": now_iso(), "id": cur, "studio": pc.get("owner", ""), "action": "merge", "comment": comment,
               "status": "MERGE REQUESTED", "title": "merge %s" % cur}
        log_decision(rec)
    return {"ok": True, "name": cur, "ts": rec["ts"]}


# ---------------------------------------------------------------- shared-resource queue (read-only view + the user's hold)

_resq = {"mod": None, "err": None}


def resq_mod():
    """queue/resq.py, loaded from the configured queue folder; only its read functions and hold / unhold are used"""
    if _resq["mod"] is None and _resq["err"] is None:
        try:
            import importlib.util
            p = os.path.join(CFG["paths"]["queue"], "resq.py")
            if not os.path.isfile(p):   # the runbook layout: ../queue/resq.py next to board/ (state still goes to paths.queue)
                p = os.path.join(os.path.dirname(HERE), "queue", "resq.py")
            spec = importlib.util.spec_from_file_location("resq_board", p)
            m = importlib.util.module_from_spec(spec)
            sys.dont_write_bytecode = True
            spec.loader.exec_module(m)
            m.configure(CFG["config_file"])
            _resq["mod"] = m
        except Exception as e:  # noqa
            _resq["err"] = "queue not readable: %s" % e
    return _resq["mod"]


_smi = {"t": 0, "v": None}
_smi_lock = threading.Lock()


def nvidia_smi():
    with _smi_lock:
        if time.time() - _smi["t"] < 10:
            return _smi["v"]
        v = None
        try:
            import subprocess
            r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            parts = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
            v = {"util": int(parts[0]), "mem_used": int(parts[1]), "mem_total": int(parts[2])}
        except Exception as e:  # noqa
            v = {"error": str(e)[:120]}
        _smi.update(t=time.time(), v=v)
        return v


_sys = {"cpu": None, "t": 0}


def cpu_sampler(interval=2.0):
    """background thread (Windows): CPU % from GetSystemTimes deltas"""
    import ctypes
    from ctypes import wintypes
    k = ctypes.windll.kernel32
    ft = lambda f: (f.dwHighDateTime << 32) | f.dwLowDateTime  # noqa: E731
    last = None
    while True:
        try:
            i, kk, u = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
            if k.GetSystemTimes(ctypes.byref(i), ctypes.byref(kk), ctypes.byref(u)):
                cur = (ft(i), ft(kk), ft(u))
                if last:
                    di, tot = cur[0] - last[0], (cur[1] - last[1]) + (cur[2] - last[2])
                    if tot > 0:
                        _sys["cpu"] = round(max(0.0, min(100.0, 100.0 * (1 - di / tot))), 1)
                        _sys["t"] = time.time()
                last = cur
        except Exception:  # noqa
            pass
        time.sleep(interval)


def ram_status():
    if os.name != "nt":
        return None
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MEMORYSTATUSEX()
        m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return None
        mb = 1024 * 1024
        return {"total_mb": m.ullTotalPhys // mb, "used_mb": (m.ullTotalPhys - m.ullAvailPhys) // mb}
    except Exception:  # noqa
        return None


def next_at(hhmm):
    if not re.match(r"^\d{1,2}:\d\d$", hhmm or ""):
        return None
    now = _dt.datetime.now()
    h, m = map(int, hhmm.split(":"))
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if t < now - _dt.timedelta(hours=6):
        t += _dt.timedelta(days=1)
    return {"at": hhmm, "in_min": round((t - now).total_seconds() / 60)}


_HOLD = {"pending": False, "since": None}
HOLD_LOCK = threading.Lock()


def _hold_worker(q):
    """take the hold the moment the lock is free (a running job is never cut), then call the optional on_hold_url"""
    while True:
        with HOLD_LOCK:
            if not _HOLD["pending"]:
                return
            try:
                took = q.hold(by="the user, from the board")
            except Exception:  # noqa
                took = False
            if took:
                _HOLD["pending"] = False
                log_decision({"ts": now_iso(), "id": "QUEUE", "studio": CFG["terms"]["manager"], "action": "hold", "comment": "",
                              "status": "%s (held from the board)" % CFG["queue"]["hold_line"], "title": "the user holds the queue"})
                break
        time.sleep(0.25)
    url = CFG["queue"].get("on_hold_url")
    if url:
        try:
            import urllib.request
            urllib.request.urlopen(urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"},
                                                          method="POST"), timeout=10).read()
        except Exception:  # noqa
            pass


def do_hold(req):
    if not CFG["panels"]["queue"].get("enabled"):
        raise BadRequest("the queue panel is switched off")
    action = str(req.get("action", "")).strip()
    q = resq_mod()
    if q is None:
        raise Conflict(_resq["err"] or "queue not available")
    held = q.held_by_user()
    if action == "hold":
        with HOLD_LOCK:
            if held:
                return {"ok": True, "state": "held"}
            if _HOLD["pending"]:
                return {"ok": True, "state": "pending"}
            _HOLD["pending"], _HOLD["since"] = True, now_stamp()
        threading.Thread(target=_hold_worker, args=(q,), daemon=True).start()
        time.sleep(0.6)
        return {"ok": True, "state": "pending" if _HOLD["pending"] else "held"}
    if action == "release":
        with HOLD_LOCK:
            if _HOLD["pending"]:
                _HOLD["pending"] = False
                return {"ok": True, "state": "cancelled"}
            if not held:
                raise Conflict("The queue isn't held by you (a job holds it, or it's free). Nothing released.")
            q.unhold()
            log_decision({"ts": now_iso(), "id": "QUEUE", "studio": CFG["terms"]["manager"], "action": "release", "comment": "",
                          "status": "released from the board", "title": "the user released the queue"})
        return {"ok": True, "state": "released"}
    raise BadRequest("action must be hold or release")


def api_queue():
    now = time.time()
    out = {"time": now_stamp(), "hold": {"pending": _HOLD["pending"], "since": _HOLD["since"]}}
    sp = CFG["panels"]["system"]
    if sp.get("enabled"):
        out["sys"] = {"cpu": _sys["cpu"] if now - _sys["t"] < 30 else None, "ram": ram_status()}
        if sp.get("gpu") == "nvidia-smi":
            out["smi"] = nvidia_smi()
    if CFG["panels"]["queue"].get("enabled"):
        q = resq_mod()
        if q is None:
            out["error"] = _resq["err"]
        else:
            try:
                out["queue"] = q.snapshot()
            except Exception as e:  # noqa
                out["error"] = "queue snapshot failed: %s" % e
    ready = []
    rd = CFG["paths"]["ready"]
    if rd and os.path.isdir(rd):
        for f in sorted(os.listdir(rd)):
            if f.endswith(".md"):
                mt = os.path.getmtime(os.path.join(rd, f))
                ready.append({"studio": f[:-3], "stamp": _dt.datetime.fromtimestamp(mt).strftime("%m-%d %H:%M"),
                              "age_min": round((now - mt) / 60)})
    build = None
    br = CFG["paths"]["build_marker"]
    if br and os.path.exists(br):
        mt = os.path.getmtime(br)
        try:
            txt = open(br, encoding="utf-8", errors="replace").read().strip()[:200] if os.path.isfile(br) else ""
        except OSError:
            txt = ""
        build = {"since": _dt.datetime.fromtimestamp(mt).strftime("%H:%M"), "min": round((now - mt) / 60), "text": txt}
    sc = CFG["schedule"]
    out["tonight"] = {"ready": ready, "build": build, "handover": next_at(sc.get("handover")),
                      "deadline": next_at(sc.get("deadline")), "build_start": next_at(sc.get("build"))}
    return out


# ---------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    server_version = "StudioBoard/1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if self.command == "POST" or (len(args) > 1 and str(args[1])[:1] in "45"):
            sys.stderr.write("%s %s\n" % (_dt.datetime.now().strftime("%m-%d %H:%M:%S"), fmt % args))
            sys.stderr.flush()

    def _host_ok(self):
        host = (self.headers.get("Host") or "").strip().lower()
        return host in ("127.0.0.1:%d" % CFG["port"], "localhost:%d" % CFG["port"])

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _err(self, code, msg):
        self._send(code, {"ok": False, "error": msg})

    def do_GET(self):
        if not self._host_ok():
            return self._err(403, "bad Host header")
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8", {
                        "Content-Security-Policy": "default-src 'self'; img-src 'self'; style-src 'unsafe-inline'; "
                                                   "script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
                        "X-Frame-Options": "DENY"})
            if u.path == "/api/health":
                return self._send(200, {"ok": True, "app": CFG["app_id"], "pid": os.getpid(), "port": CFG["port"],
                                        "project": CFG["project"], "config": CFG["config_file"],
                                        "register": CFG["paths"]["register"], "decisions": CFG["paths"]["decisions"]})
            if u.path == "/api/config":
                return self._send(200, api_config())
            if u.path == "/api/tasks":
                return self._send(200, api_tasks())
            if u.path == "/api/requests":
                return self._send(200, api_requests())
            if u.path == "/api/bundle":
                return self._send(200, api_bundle())
            if u.path == "/api/queue":
                return self._send(200, api_queue())
            if u.path == "/img":
                return self._img(parse_qs(u.query).get("p", [""])[0])
            return self._err(404, "not found")
        except Exception as e:  # noqa
            sys.stderr.write("GET %s failed: %r\n" % (self.path, e))
            return self._err(500, "server error: %s" % e)

    do_HEAD = do_GET

    def _img(self, p):
        p = (p or "").replace("\\", "/")
        if not p or ".." in p.split("/") or re.match(r"^[A-Za-z]:", p) or p.startswith("/"):
            return self._err(403, "refused")
        ext = os.path.splitext(p)[1].lower()
        if ext not in IMG_EXT:
            return self._err(403, "refused")
        full = os.path.abspath(os.path.join(CFG["root"], p))
        if not _inside_root(full) or not os.path.isfile(full):
            return self._err(404, "no such image")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", IMG_EXT[ext])
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=30")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_POST(self):
        if not self._host_ok():
            return self._err(403, "bad Host header")
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            return self._err(415, "Content-Type must be application/json")
        if self.headers.get("X-Studio-Board") != "1":
            return self._err(403, "missing X-Studio-Board header")
        origin = self.headers.get("Origin")
        if origin and origin.lower() not in ("http://127.0.0.1:%d" % CFG["port"], "http://localhost:%d" % CFG["port"]):
            return self._err(403, "bad Origin")
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0 or n > 64 * 1024:
            return self._err(400, "bad body size")
        try:
            req = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(req, dict):
                raise ValueError("not an object")
        except Exception:  # noqa
            return self._err(400, "bad JSON")
        routes = {"/api/decide": do_decide, "/api/new": do_new, "/api/question": do_question, "/api/priority": do_priority,
                  "/api/answer": do_answer, "/api/merge": do_merge, "/api/hold": do_hold}
        fn = routes.get(urlparse(self.path).path)
        if not fn:
            return self._err(404, "not found")
        try:
            return self._send(200, fn(req))
        except Conflict as e:
            return self._send(409, {"ok": False, "conflict": True, "error": str(e)})
        except BadRequest as e:
            return self._err(400, str(e))
        except Exception as e:  # noqa
            sys.stderr.write("POST %s failed: %r\n" % (self.path, e))
            return self._err(500, "write failed: %s" % e)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None, help="board.config.json (default: env STUDIO_BOARD_CONFIG, else next to server.py)")
    ap.add_argument("--port", type=int, default=None, help="override the config's port")
    a = ap.parse_args()
    load_config(a.config, a.port)
    if not os.path.isfile(CFG["paths"]["register"]):
        sys.stderr.write("register not found: %s\n" % CFG["paths"]["register"])
        return 2
    if os.name == "nt" and CFG["panels"]["system"].get("enabled"):
        threading.Thread(target=cpu_sampler, name="cpu-sampler", daemon=True).start()
    httpd = ThreadingHTTPServer(("127.0.0.1", CFG["port"]), Handler)
    httpd.daemon_threads = True
    sys.stderr.write("%s %s serving http://127.0.0.1:%d/  project=%s config=%s pid=%d\n" % (
        _dt.datetime.now().strftime("%m-%d %H:%M:%S"), CFG["app_id"], CFG["port"], CFG["project"], CFG["config_file"], os.getpid()))
    sys.stderr.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
