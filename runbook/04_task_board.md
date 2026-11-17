# 04. The task board

The board is a small local web tool (Python standard library only) over the register `studio-hub/data/PROPOSALS.md`.
The user decides there; studios post there through `note.py`; the manager relays from its decision log.
URL: `http://127.0.0.1:<port>/` (port from `board.config.json`, localhost only).

## Files

| File | Written by | Read by |
|---|---|---|
| `data/PROPOSALS.md` | studios (their blocks), the board (decision / priority / accept lines, status), `mark_live.py`, the manager (hygiene) | board, `note.py`, `prio.py`, `tick.py`, `resq.py` (task priority) |
| `data/decisions.jsonl` | the board, `mark_live.py` | the manager (`watch.py`, `tick.py`), the board (delivery state) |
| `data/relayed.cursor` | `tick.py --relayed` | the board, `tick.py`, `watch.py` |
| `data/progress/<ID>.jsonl` | `note.py`, the board (the user's questions and replies) | board, `note.py --show`, `tick.py` |
| `data/bundle.json` | the bundle's owning studio | the board (bundle panel) |
| `requests/REQUESTS.md` | studios | the board (requests panel, read-only) |

## The register: one block per card

```
## AUD-04  audio-studio  Wind loop clicks at the loop point  — APPROVED, IN WORK (waiting for LVL-02)
what:    remove the click where the wind ambience loops (every 42 s).
why:     audible tick in quiet areas; the reference recording has none.
visual:  studios/audio/cards/AUD-04_proposal.png
scope:   the 3 wind loops; a rule in the loop exporter (crossfade 80 ms), not per file.
cost:    CPU only; low risk.
decision: user, 2026-03-14 10:02, "Approve." (web tool)
priority: P2 (user, 2026-03-14 10:03, web tool)
result:
accept:
handoff:
```

Rules the parser enforces:
- The header is `## <ID>  <owner>  <title>  — STATUS (note)`. The dash before the status is an em dash (`—`).
- The board reads the **last status word outside brackets**. `APPROVED, IN WORK (result rejected: rework)` reads as
  IN WORK. Text in brackets is a note for humans: `(waiting for LVL-02)`, `(moved to AUD-07)`.
- Every line is `field: text` (field name: letters, digits, spaces, up to 25 characters) or an indented continuation
  line. A blank line ends a field.
- Anything else is a **parser warning**: the board shows a warning count in its header and lists the lines. Duplicate
  IDs, a header without a status, and a status that does not start with a status word are warnings too.
- Cards come after the first line that is exactly `---`. Everything above it is the header (format, rules).
- IDs are `<PREFIX>-NN`, the next free number for the prefix. The board's "New request" picks it itself.
- Field order: `what why visual scope cost decision priority result accept handoff` (`fields` in the config). Pictures
  are read from the `visual` and `result` fields (`image_fields`): any path ending in .jpg / .jpeg / .png / .webp that
  exists inside the project root.

How to write a block: a studio appends its own block at the end with a temp file + `os.replace`, and never touches
anyone else's block. The board writes one block at a time, refuses if that block changed since the page loaded (409
"edited since this page loaded"), keeps the file's line endings and encoding, and writes with temp + `os.replace`.

## GEN threads

`GEN-<key>` is a studio's general thread. It has no register block, only `data/progress/GEN-<key>.jsonl`. Use it for:
- questions that belong to no card (`note.py GEN-audio "..." --ask --img ...`);
- announcements the user should see (a new shared tool, a measurement): plain notes, shown under "Studio notes" in the
  Questions tab.

## Statuses

| Status | Meaning | Set by |
|---|---|---|
| PROPOSED | waiting for the user's yes / no | studio |
| APPROVED | the user said yes; not started yet | the board, or the manager quoting the user's words |
| IN WORK | being worked on | studio |
| RESULT | evidence posted; the user can accept | studio, **in the same step as posting the evidence** |
| ACCEPTED | the user accepted the result | the board |
| HANDOFF | all of it is in the ready file | studio, as soon as it is all in |
| LIVE | shipped: `LIVE (<label>, <round> <MM-DD>)` | `mark_live.py` (manager) after the build |
| BACKLOG | the user parked it: "not now" | the board |
| REJECTED | not wanted | the board |
| CLOSED | no longer needed (reason in brackets) | user, studio or manager |

HANDOFF, LIVE and BACKLOG can be switched off (`"statuses": {"HANDOFF": {"enabled": false}}`); with no build, ACCEPTED
is final. Each status may get a `label` (what the board shows) and, rarely, a `word` (what is written in the register).
Change labels freely; change words only before the first card exists.

**Keep statuses true.** The user reads only the board:
- evidence posted under APPROVED means no Accept button;
- a finished card under IN WORK reads as stuck;
- a card waiting on something says so in the bracket: `APPROVED (waiting for AUD-02)`. `tick.py` does not call such a
  card stale.

## Board actions

| Button (card status) | New status | `action` in the log |
|---|---|---|
| Approve (PROPOSED) | APPROVED | `approve` |
| Reject (PROPOSED) | REJECTED | `reject` |
| Backlog (PROPOSED) | BACKLOG (user: not now) | `backlog` |
| Approve (BACKLOG) | APPROVED (from backlog) | `approve_backlog` |
| Reject (BACKLOG) | REJECTED | `reject_backlog` |
| Accept (RESULT) | ACCEPTED | `accept` |
| Rework (RESULT) | APPROVED, IN WORK (result rejected: rework) | `reject_result` |
| Close (any open card; reason required) | CLOSED (user: reason) | `close` |
| Reopen (CLOSED) | APPROVED (reopened by user) | `reopen` |
| P1 / P2 / P3 / P4 | unchanged; `priority:` line rewritten | `priority` (with `from`, `to`) |
| New request | new card, APPROVED (user request, web tool) | `new_request` |
| Ask the studio (any card) | unchanged | `question` |
| Answer (a studio's open ask) | unchanged | `answer` (`reply_to` = the ask's id) |
| Merge this bundle (bundle panel) | unchanged | `merge` |
| Hold / Release (queue panel) | unchanged | `hold` / `release` |
| (none: `mark_live.py`) | LIVE / back to work | `live` / `revert` |

Batch actions: tick several PROPOSED cards, then "Approve selected" or "Backlog selected".
Decision lines carry the user's words: `decision: user, <date time>, "Approve. <comment>" (web tool)`.

## The decision log

`data/decisions.jsonl`, one JSON object per line, append-only, never edited:
```
{"ts": "2026-03-14T10:02:11", "id": "AUD-04", "studio": "audio-studio", "action": "approve",
 "comment": "keep the gust layer", "status": "APPROVED", "title": "Wind loop clicks at the loop point"}
```
Extra keys by action: `from` / `to` (priority), `reply_to` / `question` (answer), `build` (live / revert),
`visual` / `priority` (new_request).

`data/relayed.cursor` holds the number of lines the manager has relayed. Lines past it are "waiting for the manager"
on the board; lines before it are "passed to the studio"; a question the studio has answered shows "answered".
The manager relays and then runs `tick.py --relayed` (`07_manager_routine.md`).

## Progress notes, asks and answers

`data/progress/<ID>.jsonl`, append-only, one JSON object per line:
```
{"ts": "...", "nid": "<unique note id>", "by": "audio-studio", "pct": 40, "note": "crossfade rule in; 2 of 3 loops clean",
 "images": ["studios/audio/cards/AUD-04_wip.png"]}
```
Optional keys: `"answer": true` (a studio's answer to the user's question), `"kind"`: `ask` (a question to the user),
`withdraw` (a studio closing its own ask), `reply` (the user's answer), `question` (the user's question),
`"options": [...]`, `"reply_to": "<nid>"`.

| Command | Does |
|---|---|
| `note.py <ID> "text" [--pct N] [--img p ...]` | progress note; the card shows the latest `--pct` as a bar |
| `note.py <ID> "text" --answer` | marks the note as the studio's answer to the user's question |
| `note.py <ID> "question" --ask --img <picture> [--options "A\|B\|C"]` | asks the user in the card's thread; the card shows "waiting for your answer"; it lands in the Questions tab |
| `note.py GEN-<key> "question" --ask --img <picture>` | a question that belongs to no card |
| `note.py <ID> --withdraw <ask id> --reason "..."` | closes the studio's own outdated ask |
| `note.py <ID> --show` | the card's notes, asks, the user's questions and replies ("USER REPLIED") |
| `note.py --open-asks` | every unanswered ask: id, studio, age, text |

Rules:
- Every ask carries a picture. The user decides from pictures.
- `--options` gives one-click answers; free text stays possible. Put the studio's own pick first.
- **Accept with a pick.** When a RESULT offers variants, post the RESULT note itself as an ask with `--options`
  ("A: subtle | B: strong | C: reference level"). The board then shows "Accept: A", "Accept: B" ... buttons that send the
  answer and the accept in one click, so the accept always carries the pick.
- A studio does not wait idle for an answer; it carries on with its next card.
- Never write progress into the register.
- Images: jpg / png / webp inside the project, given relative to the project root (or to an `image_bases` entry), or
  absolute inside the root.

## Priority

`priority: P1..P4` in the block, written by the board. No line = the default (P3).
P1 urgent, P2 high, P3 normal, P4 low (`priority.names`). Studios work their APPROVED / IN WORK cards in that order:
`prio.py --studio <key>` (ties: older card first). The queue reads the same priority from the register to order
tickets tagged `--task <ID>` (`09_shared_resources.md`).

## Backlog, new requests, close, reopen, moves

- **Backlog:** the user's "not now". Studios don't work on it, don't re-propose it, and use no shared resource for it.
  It comes back only as "APPROVED (from backlog)" or goes to REJECTED.
- **New request:** the user picks a studio, a priority, a title, what, and an optional picture path. The card enters
  as APPROVED with the next free ID.
- **Close** needs a reason; ACCEPTED, HANDOFF, LIVE, REJECTED and CLOSED cards cannot be closed. **Reopen** brings a
  CLOSED card back as APPROVED.
- **Moves:** a status like `CLOSED (moved to AUD-07)` links the two cards; a card whose title or decision says
  `was AUD-03` / `moved from AUD-03` links back. The board shows both links.

## Panels

All optional (`panels` in the config):

| Panel | Shows | Writes |
|---|---|---|
| Requests inbox | `requests/REQUESTS.md`, read-only: `## Open` / `## Closed` sections, `### <ID> <title> — <tag>` items, `- field: value` lines | nothing |
| Bundle | the open bundle from `data/bundle.json`: `name`, `title`, `opened`, `base`, `changes` [{id, what, accepted}], `state` (open / merging / merged / failed), `state_ts`, `merged_as`, `merge_log`, `note`; the tail of the merge log | the "Merge this bundle" button logs a `merge` action. The board never merges: the owning studio does, on the relayed request. |
| Queue | lock holder, the current turn, waiting tickets in serving order, the schedule (handover, deadline, build) with minutes to go, ready-file stamps, the freeze marker | Hold / Release: the user's own reservation of the resource (`09_shared_resources.md`) |
| System | CPU, RAM and (with `gpu: "nvidia-smi"`) GPU use and memory | nothing |

The bundle exists because some changes must land together and only on the user's button (a merge of one branch of
model edits, for example). One bundle open at a time; every change of that kind goes in it; after a merge the owner
opens a new one. A pending merge never holds up a RESULT: the studio shows the change on a scratch copy and asks for
accept.

## Alerts

The bell button turns on desktop notifications: one alert per new PROPOSED card, new RESULT, new studio ask, or bundle
ready to merge. The board polls in the background while the bell is on. Why: the user only wants to be called when the
board needs them; routine "task done" banners from the sessions stay off.

Cards IN WORK with no studio note for `stale_hours` show a "stale" tint.

## API

GET (no side effects): `/` (the page), `/api/health`, `/api/config`, `/api/tasks`, `/api/requests`, `/api/bundle`,
`/api/queue`, `/img?p=<path relative to the root>`.
POST (JSON body, `Content-Type: application/json`, header `X-Studio-Board: 1`): `/api/decide` (action, id, hash, comment),
`/api/priority` (id, hash, level), `/api/new`, `/api/question`, `/api/answer` (id, reply_to, text), `/api/merge`,
`/api/hold` (action hold / release). Conflicts return 409 with a message; the page reloads the card.

## Security model

- Binds 127.0.0.1 only; checks the Host header and, on POST, the Origin and the custom header (no cross-site writes).
- Body limit 64 KB; JSON only; strict Content-Security-Policy; frames denied.
- Images served only from inside the project root, only image extensions, no `..`.
- The server runs no commands except an optional fixed GPU query, cached.
- Phone access is not supported (localhost only). If the user wants the board on a phone, that is a separate,
  explicit project.

## Running it

- `python studio-hub/board/start.py`: starts it in the background with no console window; prints the URL; does
  nothing if it already runs. `stop.py` stops only the pid in `server.pid`, and only if that pid is this board.
- Log: `studio-hub/board/server.log`. `tick.py` restarts the board when it does not answer.
- Never restart it while the user may be acting on it. Page-only changes (index.html) need no restart: the user
  reloads. Batch server changes so one restart covers several.

## Config reference (`board.config.json`)

| Key | Meaning |
|---|---|
| `project`, `app_id`, `port` | page title, the id `start.py` / `stop.py` check, the port |
| `root` | the project root (images must be inside it) |
| `paths.*` | register, decisions, progress, bundle, requests, ready, build_marker, queue |
| `image_bases` | folders (relative to the root) tried when a picture path is relative |
| `terms.*` | studio, studios, manager, user, result, build, ready_file: the page's words |
| `studios[]` | key, prefix, owner, label, icon, color, ready, queue_owner |
| `statuses.<KEY>` | label, word, enabled (HANDOFF / LIVE / BACKLOG only) |
| `fields`, `image_fields` | field order for inserts; fields scanned for pictures |
| `priority` | default and names |
| `stale_hours` | stale tint and the tick's stale flag |
| `schedule` | handover, deadline, build times (HH:MM) |
| `panels.*` | requests, bundle (owner, title, button), queue (title), system (gpu) |
| `queue.*` | the queue's settings (`09_shared_resources.md`) |

Icon names: brush, leaf, sun, cube, gauge, parcel, megaphone, spray, tiles, music, film, code, bug, book, pen, chart,
map, wrench, globe, star. An unknown name shows a dot.
