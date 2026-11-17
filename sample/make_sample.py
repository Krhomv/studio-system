"""Write the sample project's data: a fictional small game ("Example Game") run by three studios (art, audio, levels), with cards in
every status, progress notes, open asks (one with options on a RESULT), a general thread, a partly relayed decision log, a
bundle waiting for the merge button, a requests inbox, ready files, a review pass and placeholder pictures. Times are relative to
now, so stale / fresh states look the same whenever you run it.

  python make_sample.py [--out <project root>] [--config]      (default --out: this folder)

--config also writes studio-hub/board/board.config.json (the sample's own). Existing data files are replaced; nothing else is
touched. View it: python ../board/start.py --config <out>/studio-hub/board/board.config.json   (then stop.py with the same --config)
"""
import argparse
import datetime as dt
import json
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
NOW = dt.datetime.now().replace(microsecond=0)


def t(hours_ago, minutes=0):
    return (NOW - dt.timedelta(hours=hours_ago, minutes=minutes)).isoformat()


def stamp(hours_ago):
    return (NOW - dt.timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M")


CONFIG = {
    "project": "Example Game",
    "app_id": "board-example-game",
    "port": 8790,
    "root": "../..",
    "paths": {"register": "../data/PROPOSALS.md", "decisions": "../data/decisions.jsonl", "progress": "../data/progress",
              "bundle": "../data/bundle.json", "requests": "../requests/REQUESTS.md", "ready": "../ready",
              "build_marker": "../BUILD_RUNNING", "queue": "../queue"},
    "image_bases": ["", "studio-hub", "studios"],
    "terms": {"studio": "studio", "studios": "studios", "manager": "manager", "user": "you", "result": "result",
              "build": "build", "ready_file": "ready file"},
    "studios": [
        {"key": "art", "prefix": "ART", "owner": "art-studio", "label": "Art", "icon": "brush", "color": "#d58fb8", "ready": True,
         "queue_owner": "art-studio"},
        {"key": "audio", "prefix": "AUD", "owner": "audio-studio", "label": "Audio", "icon": "music", "color": "#6fc3c9", "ready": True,
         "queue_owner": "audio-studio"},
        {"key": "levels", "prefix": "LVL", "owner": "levels-studio", "label": "Levels", "icon": "map", "color": "#92a6dc", "ready": True,
         "queue_owner": "levels-studio"}],
    "statuses": {"HANDOFF": {"enabled": True}, "LIVE": {"enabled": True}, "BACKLOG": {"enabled": True}},
    "fields": ["what", "why", "visual", "scope", "cost", "decision", "priority", "result", "accept", "handoff"],
    "image_fields": ["visual", "result"],
    "priority": {"default": 3, "names": {"1": "urgent", "2": "high", "3": "normal", "4": "low"}},
    "stale_hours": 3,
    "schedule": {"handover": "01:45", "deadline": "02:45", "build": "03:00"},
    "panels": {"requests": {"enabled": True, "title": "Requests inbox"},
               "bundle": {"enabled": True, "owner": "levels-studio", "title": "Level bundle", "button": "Merge this bundle"},
               "queue": {"enabled": True, "title": "GPU"},
               "system": {"enabled": True, "gpu": "nvidia-smi"}},
    "queue": {"turn_max_min": 20, "grace_s": 60, "turn_tail_min": 3, "short_max_min": 3, "gap_ban_min": 60,
              "priority_owners": ["build*", "nightly*"], "hold_line": "USER HOLD", "gate_cmd": "", "on_hold_url": ""},
}

# ---------------------------------------------------------------- pictures (stdlib PNG; labels when Pillow is installed)

PICS = {
    "art/cards/ART-01_rocks_ab.png": ("rocks: before | after", (92, 88, 84), (140, 128, 112)),
    "art/cards/ART-02_torch_ab.png": ("torch glow: before | after", (180, 110, 40), (200, 160, 90)),
    "art/cards/ART-03_grass_now.png": ("north hill grass, now (marked)", (110, 150, 60), (110, 150, 60)),
    "art/cards/ART-03_grass_abc.png": ("grass tint: A | B | C", (120, 160, 70), (95, 130, 80)),
    "art/cards/ART-04_sign_aim.png": ("aim: this sign (marked)", (70, 60, 50), (230, 220, 200)),
    "art/cards/ART-04_sign_wip.png": ("sign text, work in progress", (70, 60, 50), (240, 235, 220)),
    "art/cards/ART-05_icons_mock.png": ("icon set mock", (40, 44, 60), (200, 180, 120)),
    "art/cards/ART-06_water.png": ("water now | darker mock", (40, 90, 120), (20, 50, 75)),
    "audio/cards/AUD-01_steps.png": ("footsteps: wood floor zones", (90, 70, 50), (130, 100, 70)),
    "audio/cards/AUD-02_wind_loop.png": ("wind loop: click at loop point", (50, 60, 70), (90, 110, 130)),
    "audio/cards/AUD-03_ducking.png": ("music level during dialogue", (60, 50, 80), (120, 100, 160)),
    "levels/cards/LVL-01_railing.png": ("bridge railing gap (marked)", (100, 100, 110), (160, 160, 170)),
    "levels/cards/LVL-02_cave.png": ("cave entrance: camera clips", (50, 45, 40), (90, 80, 70)),
    "levels/cards/LVL-04_ledge.png": ("ledge too high to climb", (120, 115, 100), (150, 145, 130)),
    "levels/cards/GEN_levels_state.png": ("levels state: 12 zones checked", (60, 70, 90), (90, 110, 140)),
}


def png_bytes(w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)  # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def make_pic(path, label, c1, c2, w=480, h=270):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (w, h), c1)
        d = ImageDraw.Draw(im)
        d.rectangle([w // 2, 0, w, h], fill=c2)
        d.line([w // 2, 0, w // 2, h], fill=(20, 20, 20), width=2)
        d.ellipse([w // 2 - 50, h // 2 - 35, w // 2 + 50, h // 2 + 35], outline=(240, 70, 60), width=4)
        d.rectangle([0, h - 30, w, h], fill=(16, 16, 18))
        d.text((10, h - 22), label, fill=(235, 235, 235))
        im.save(path, optimize=True)
    except ImportError:
        rows = []
        for y in range(h):
            row = []
            for x in range(w):
                c = (16, 16, 18) if y >= h - 30 else (c1 if x < w // 2 else c2)
                row += list(c)
            rows.append(row)
        with open(path, "wb") as f:
            f.write(png_bytes(w, h, rows))


# ---------------------------------------------------------------- register

def register():
    S = stamp
    return f"""# Proposals register: Example Game

Studios: read `studio-hub/TASKS_GUIDE.md` first. One block per task; write it with a temp file + os.replace and touch only your own
block. Progress goes through `note.py`, never into this file.

Entry format:
```
## <ID>  <owner>  <short title>  — STATUS (note)
what:    <the change, in one or two lines>
why:     <what looks wrong / what improves>
visual:  <picture path(s): current state, a marked crop, a mock>
scope:   <where / how many; rule or one-off>
cost:    <time, resource tickets, risk>
decision: <user, date, words>          (the board writes it)
priority: <P1..P4 (user, date)>        (the board writes it; none = P3)
result:  <A/B picture path>            (the studio, when done)
accept:  <user, date, words>           (the board writes it)
handoff: <ready-file stamp>            (the studio) / live in <label> (mark_live.py)
```

---

## ART-01  art-studio  Rock textures read flat at mid distance  — LIVE (v3, r3 {(NOW - dt.timedelta(hours=30)).strftime('%m-%d')})
what:    add a mid-distance detail layer to the cliff rock material so the rocks keep their shape from 20-60 m.
why:     from the main path the cliffs read as flat grey walls; up close they are fine.
visual:  studios/art/cards/ART-01_rocks_ab.png
scope:   all cliff rock instances (one material rule, not per object).
cost:    2 short GPU tickets; low risk.
decision: user, {S(52)}, "Approve." (board)
result:  studios/art/cards/ART-01_rocks_ab.png
accept:  user, {S(40)}, "Accept." (board)
handoff: live in v3 (r3, {S(30)}, mark_live)

## ART-02  art-studio  Torch glow too orange in the cave  — ACCEPTED
what:    move the cave torch light from orange to a warmer white and lower its radius by a fifth.
why:     the cave reads like it is on fire; the torches should read as small warm lights.
visual:  studios/art/cards/ART-02_torch_ab.png
scope:   the 14 cave torches (one light preset).
cost:    1 short ticket.
decision: user, {S(26)}, "Approve." (board)
result:  studios/art/cards/ART-02_torch_ab.png
accept:  user, {S(3)}, "Accept." (board)
handoff:

## ART-03  art-studio  Grass tint on the north hill  — RESULT (variants A / B / C, pick in the ask)
what:    tone the north hill grass down from lime to a dry green; three strengths.
why:     the hill reads neon next to the forest edge.
visual:  studios/art/cards/ART-03_grass_now.png
scope:   north hill grass only (a region mask), not site-wide.
cost:    1 ticket per variant set.
decision: user, {S(20)}, "Approve." (board)
priority: P2 (user, {S(20)}, board)
result:  studios/art/cards/ART-03_grass_abc.png
accept:
handoff:

## ART-04  art-studio  Signboard text unreadable at the market  — IN WORK
what:    redraw the market signboard text at twice the texel density, same style.
why:     user: "I can't read any of the shop signs".
visual:  studios/art/cards/ART-04_sign_aim.png
scope:   the 6 market signs (one atlas).
cost:    CPU work, 1 ticket for the A/B.
decision: user, {S(9)}, "Approve." (board)
priority: P2 (user, {S(8)}, board)
result:
accept:
handoff:

## ART-05  art-studio  New icon set for the inventory  — PROPOSED
what:    replace the 40 placeholder inventory icons with one consistent drawn set (mock attached: 6 of them).
why:     the placeholders mix three styles; players mix up potions and food.
visual:  studios/art/cards/ART-05_icons_mock.png
scope:   inventory icons only.
cost:    about a day of CPU work; no GPU.
decision:
result:
accept:
handoff:

## ART-06  art-studio  Darker lake water  — BACKLOG (user: not now)
what:    darken the lake water and add a little murk near the shore.
why:     the lake reads like a swimming pool.
visual:  studios/art/cards/ART-06_water.png
scope:   the lake material.
cost:    2 tickets.
decision: user, {S(48)}, "Backlog." (board)
result:
accept:
handoff:

## AUD-01  audio-studio  Footsteps on wood sound like stone  — APPROVED, IN WORK (result rejected: rework)
what:    tag the wooden floors with the wood surface type so the footstep set switches.
why:     every wooden floor plays the stone steps.
visual:  studios/audio/cards/AUD-01_steps.png
scope:   all wooden floor meshes (a surface-type rule).
cost:    CPU only.
decision: user, {S(30)}, "Approve." (board)
result:  studios/audio/cards/AUD-01_steps.png
accept:  user, {S(6)}, "Rework. the bridge still sounds like stone" (board)
handoff:

## AUD-02  audio-studio  Ambient wind loop clicks at the loop point  — HANDOFF
what:    re-cut the wind loop on a zero crossing and cross-fade 200 ms.
why:     a click every 41 s in the open areas.
visual:  studios/audio/cards/AUD-02_wind_loop.png
scope:   one sound file.
cost:    minutes.
decision: user, {S(28)}, "Approve." (board)
result:  studios/audio/cards/AUD-02_wind_loop.png
accept:  user, {S(5)}, "Accept." (board)
handoff: studio-hub/ready/audio-studio.md stamp {S(4)}

## AUD-03  audio-studio  Lower the music under dialogue  — PROPOSED
what:    duck the music by 6 dB while a character speaks, with a 300 ms fade.
why:     the music covers quiet lines in two scenes.
visual:  studios/audio/cards/AUD-03_ducking.png
scope:   the music bus (one rule).
cost:    CPU only.
decision:
result:
accept:
handoff:

## AUD-04  audio-studio  New menu click sound  — REJECTED
what:    a softer click for the menu buttons.
why:     the current click is sharp.
visual:
scope:   menu only.
cost:    minutes.
decision: user, {S(70)}, "Reject. the click is fine" (board)
result:
accept:
handoff:

## LVL-01  levels-studio  Gap in the bridge railing  — APPROVED (waiting for LVL-02)
what:    close the gap in the east bridge railing.
why:     the player can walk off the bridge there.
visual:  studios/levels/cards/LVL-01_railing.png
scope:   one railing segment (in the level bundle).
cost:    minutes; goes in the open bundle.
decision: user, {S(12)}, "User request." (board)
priority: P1 (user, {S(12)}, board)
result:
accept:
handoff:

## LVL-02  levels-studio  Cave entrance too narrow for the camera  — IN WORK
what:    widen the cave entrance by 1 m so the follow camera stops clipping into the rock.
why:     the camera jumps inside the wall for a second on the way in.
visual:  studios/levels/cards/LVL-02_cave.png
scope:   the cave entrance only.
cost:    one bundle change, 2 tickets for the A/B.
decision: user, {S(24)}, "Approve." (board)
result:
accept:
handoff:

## LVL-03  levels-studio  Old spawn area clean-up  — CLOSED (moved to LVL-02: same rock edit)
what:    clean up the old spawn area rocks.
why:     overlapping rocks.
visual:
scope:   spawn area.
cost:    small.
decision: user, {S(60)}, "Approve." (board)
result:
accept:
handoff:

## LVL-04  levels-studio  Ledge too high to climb near the mill  — PROPOSED
what:    lower the mill ledge by 40 cm.
why:     players expect to climb it.
this line has no field name, so the board shows a parser warning for this card
visual:  studios/levels/cards/LVL-04_ledge.png
scope:   one ledge.
cost:    minutes.
decision:
result:
accept:
handoff:
"""


def note(ts, by, text, pct=None, images=None, **kw):
    nid = dt.datetime.fromisoformat(ts).strftime("%Y%m%dT%H%M%S.%f") + "-" + format(abs(hash((ts, by, text))) % 65536, "04x")
    r = {"ts": ts + ".000000", "nid": nid, "by": by, "pct": pct, "note": text, "images": images or []}
    r.update(kw)
    return r


def progress():
    A = "studios/art/cards/"
    ask3 = note(t(1, 10), "art-studio", "Three strengths of the dry-green tint. Which one? A is closest to the forest edge.",
                images=[A + "ART-03_grass_abc.png"], kind="ask", options=["A (strong)", "B (medium)", "C (light)"])
    ask4 = note(t(2), "art-studio", "Keep the hand-painted letter style, or switch to a clean print style for readability?",
                images=[A + "ART-04_sign_aim.png"], kind="ask", options=["keep hand-painted", "clean print"])
    old_ask = note(t(5), "art-studio", "Same sign question, first version (re-posted with a picture).", kind="ask")
    gen_ask = note(t(0, 40), "levels-studio", "The bundle has LVL-01 ready; LVL-02 is not accepted yet. Merge LVL-01 alone now, or wait for LVL-02?",
                   images=["studios/levels/cards/GEN_levels_state.png"], kind="ask", options=["wait for LVL-02", "merge LVL-01 now"])
    return {
        "ART-01": [note(t(50), "art-studio", "Detail layer in, testing at 3 distances.", 50, [A + "ART-01_rocks_ab.png"]),
                   note(t(44), "art-studio", "A/B posted for accept.", 100, [A + "ART-01_rocks_ab.png"])],
        "ART-03": [note(t(19), "art-studio", "Region mask done; making three strengths.", 40),
                   note(t(1, 15), "art-studio", "A/B with three strengths posted.", 100, [A + "ART-03_grass_abc.png"]), ask3],
        "ART-04": [note(t(8), "art-studio", "Aim: this is the sign I'll change (marked).", 10, [A + "ART-04_sign_aim.png"]),
                   old_ask,
                   note(t(4, 59), "art-studio", "", kind="withdraw", reply_to=old_ask["nid"]),
                   ask4,
                   note(t(1), "art-studio", "Atlas redrawn at 2x, now checking the far view.", 40, [A + "ART-04_sign_wip.png"])],
        "AUD-01": [note(t(20), "audio-studio", "Wood tag added to 212 floor meshes.", 80, ["studios/audio/cards/AUD-01_steps.png"]),
                   note(t(5, 30), "user", "Does the rule also cover the bridge planks?", kind="question"),
                   note(t(5), "audio-studio", "Not yet: the bridge planks use the stone surface. Adding them now.", 85, answer=True)],
        "LVL-02": [note(t(6), "levels-studio", "Entrance widened in the bundle copy; camera test queued.", 30,
                        ["studios/levels/cards/LVL-02_cave.png"]),
                   note(t(0, 30), "user", "Will the wider entrance change the light inside?", kind="question")],
        "GEN-levels": [note(t(3), "levels-studio", "State note: 12 zones checked for walkable gaps, 2 found (LVL-01, LVL-04).",
                            images=["studios/levels/cards/GEN_levels_state.png"]), gen_ask],
    }, ask3, ask4


def decisions(ask3):
    D = lambda h, i, s, a, st, title, c="", **kw: dict({"ts": t(h)[:19], "id": i, "studio": s, "action": a, "comment": c,  # noqa: E731
                                                         "status": st, "title": title}, **kw)
    rows = [
        D(70, "AUD-04", "audio-studio", "reject", "REJECTED", "New menu click sound", "the click is fine"),
        D(52, "ART-01", "art-studio", "approve", "APPROVED", "Rock textures read flat at mid distance"),
        D(48, "ART-06", "art-studio", "backlog", "BACKLOG (user: not now)", "Darker lake water"),
        D(40, "ART-01", "art-studio", "accept", "ACCEPTED", "Rock textures read flat at mid distance"),
        D(30, "ART-01", "art-studio", "live", "LIVE (v3, r3)", "Rock textures read flat at mid distance", build="v3"),
        D(30, "AUD-01", "audio-studio", "approve", "APPROVED", "Footsteps on wood sound like stone"),
        D(28, "AUD-02", "audio-studio", "approve", "APPROVED", "Ambient wind loop clicks at the loop point"),
        D(26, "ART-02", "art-studio", "approve", "APPROVED", "Torch glow too orange in the cave"),
        D(24, "LVL-02", "levels-studio", "approve", "APPROVED", "Cave entrance too narrow for the camera"),
        D(20, "ART-03", "art-studio", "approve", "APPROVED", "Grass tint on the north hill"),
        D(20, "ART-03", "art-studio", "priority", "APPROVED", "Grass tint on the north hill", **{"from": "P3", "to": "P2"}),
        D(12, "LVL-01", "levels-studio", "new_request", "APPROVED (user request, board)", "Gap in the bridge railing",
          "close the gap in the east bridge railing", visual="studios/levels/cards/LVL-01_railing.png", priority="P1"),
        D(9, "ART-04", "art-studio", "approve", "APPROVED", "Signboard text unreadable at the market"),
        D(8, "ART-04", "art-studio", "priority", "APPROVED", "Signboard text unreadable at the market", **{"from": "P3", "to": "P2"}),
        D(6, "AUD-01", "audio-studio", "reject_result", "APPROVED, IN WORK (result rejected: rework)", "Footsteps on wood sound like stone",
          "the bridge still sounds like stone"),
        D(5.5, "AUD-01", "audio-studio", "question", "APPROVED, IN WORK (result rejected: rework)", "Footsteps on wood sound like stone",
          "Does the rule also cover the bridge planks?"),
        D(5, "AUD-02", "audio-studio", "accept", "ACCEPTED", "Ambient wind loop clicks at the loop point"),
        # the two below are not relayed yet (after the cursor): tick.py flags them as DECISION
        D(3, "ART-02", "art-studio", "accept", "ACCEPTED", "Torch glow too orange in the cave"),
        D(0.5, "LVL-02", "levels-studio", "question", "IN WORK", "Cave entrance too narrow for the camera", "Will the wider entrance change the light inside?"),
    ]
    for r in rows:   # the board writes a user question as a note AND a decision with the same time stamp
        if r["action"] == "question":
            r["ts"] += ".000000"
    return rows, len(rows) - 2


NOTES = """# {label} studio ({owner}): working notes

Owner `{owner}`, card prefix `{prefix}-`, general thread `GEN-{key}`. Base rules: `studio-hub/TASKS_GUIDE.md` (wins over this file).
This file holds lasting working knowledge, not a diary. Progress goes on the board (`note.py`).

## Where things live
| Path | What |
|---|---|
| `cards/` | pictures for cards, asks and results |
| `lab/` | scratch copies and experiments |
| `staged/` | installers for accepted items (dry run / --apply / --revert) |

## Lessons
- (sample) Show the strongest option clearly: small safe steps read as "no change" at sheet size.

## Open cards (one line each, kept current)
- (sample) see the board
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--config", action="store_true", help="also write studio-hub/board/board.config.json")
    a = ap.parse_args()
    root = os.path.abspath(a.out)
    hub = os.path.join(root, "studio-hub")
    if a.config:
        write(os.path.join(hub, "board", "board.config.json"), json.dumps(CONFIG, indent=2) + "\n")
    for rel, (label, c1, c2) in PICS.items():
        make_pic(os.path.join(root, "studios", rel), label, c1, c2)
    write(os.path.join(hub, "data", "PROPOSALS.md"), register())
    pdir = os.path.join(hub, "data", "progress")
    os.makedirs(pdir, exist_ok=True)
    for f in os.listdir(pdir):
        if f.endswith(".jsonl"):
            os.remove(os.path.join(pdir, f))
    notes, ask3, ask4 = progress()
    for bid, rows in notes.items():
        write(os.path.join(pdir, bid + ".jsonl"), "".join(json.dumps(r) + "\n" for r in rows))
    rows, cursor = decisions(ask3)
    write(os.path.join(hub, "data", "decisions.jsonl"), "".join(json.dumps(r) + "\n" for r in rows))
    write(os.path.join(hub, "data", "relayed.cursor"), str(cursor))
    write(os.path.join(hub, "data", "bundle.json"), json.dumps({
        "name": "bundle-0004", "title": "Level fixes, batch 4", "opened": t(26)[:19], "base": "v3",
        "changes": [{"id": "LVL-01", "what": "east bridge railing gap closed", "accepted": True},
                    {"id": "LVL-02", "what": "cave entrance widened by 1 m (camera test pending)", "accepted": False}],
        "state": "open", "state_ts": t(26)[:19], "merged_as": "", "merge_log": "", "note": "LVL-02 waits for its A/B"}, indent=2) + "\n")
    write(os.path.join(hub, "requests", "REQUESTS.md"), """# Requests inbox (levels)

Requests from other studios to the levels studio (owner of the level geometry). One item per request; the levels studio answers on
its own items. New work for a studio goes on the board as a card, not here.

## Open

### REQ-01 Footstep surface tags on the new bridge — open
- from: audio-studio
- where: east bridge planks
- evidence: studios/audio/cards/AUD-01_steps.png
- status: open, the levels studio adds the wood tag in the next bundle

## Closed

### REQ-00 Ledge collision near the mill — CLOSED
- from: art-studio
- status: closed, became LVL-04
""")
    write(os.path.join(hub, "ready", "audio-studio.md"), f"""stamp: {(NOW - dt.timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M')}   (NOT final: the handover call decides)
accepted: AUD-02 wind loop = user ACCEPTED on the board {stamp(5)} ("Accept.")
already live: nothing
apply tonight:
 1. AUD-02: python studios/audio/staged/aud02/install.py            (dry run: 1 file would change)
    python studios/audio/staged/aud02/install.py --apply            (backup in studios/audio/backup/<stamp>/)
    revert: python studios/audio/staged/aud02/install.py --revert <stamp>
check: play the open field for 2 min: no click at the loop point; the loop length is unchanged (41.0 s).
worse looks like: a gap of silence, or the wind louder than before.
not ready: AUD-01 (rework, not accepted)
""")
    write(os.path.join(hub, "ready", "art-studio.md"), f"""stamp: {(NOW - dt.timedelta(hours=9)).strftime('%Y-%m-%dT%H:%M')}
accepted: (none new yet; ART-02 accepted {stamp(3)} must be added at the handover call)
already live: ART-01 rock detail layer (v3)
apply tonight: nothing yet
not ready: ART-03 (result waits for the user's pick), ART-04 (in work)
""")
    write(os.path.join(hub, "reviews", "REVIEW_" + NOW.strftime("%Y%m%d") + ".md"), f"""# User review pass {NOW.strftime('%Y-%m-%d')}

The user's own notes from playing v3, turned into cards (APPROVED, P2 by default):
- "the shop signs are unreadable" -> ART-04
- "you can fall off the east bridge" -> LVL-01 (the user set P1)
""")
    for st in CONFIG["studios"]:
        write(os.path.join(root, "studios", st["key"], "NOTES.md"),
              NOTES.format(label=st["label"], owner=st["owner"], prefix=st["prefix"], key=st["key"]))
    ncards = register().split("\n---\n", 1)[1].count("\n## ")
    print("sample written to %s (%d cards, %d note files, %d decisions, cursor %d)" % (root, ncards, len(notes), len(rows), cursor))
    return 0


if __name__ == "__main__":
    main()
