# Studio board

A small local web tool over the studios' task register (Python 3.8+ standard library only, no install). The user approves,
rejects, accepts, sends back, parks, closes, prioritises and requests work here, answers the studios' questions, asks questions of
their own, presses the bundle's merge button and holds the shared resource. Everything the user does is one line in the decision
log, which the manager relays to the studios.

How the system around it works: `../runbook/04_task_board.md` (in the runbook folder) or the project's `studio-hub/README.md`.

## Files
| File | What |
|---|---|
| `server.py` | the HTTP server (127.0.0.1 only) and the shared parser / writer used by every other script |
| `index.html` | the page (dark theme; tabs Tasks / Requests / Questions / Queue; desktop alerts on request) |
| `board.config.json` | everything project-specific: project name, port, paths, terms, studios, status words and labels, panels |
| `note.py` | studios: progress notes, answers, questions to the user (`--ask`), `--withdraw`, `--show`, `--open-asks` |
| `prio.py` | approved / in-work tasks per studio in the user's priority order |
| `mark_live.py` | manager, after a build: shipped items to LIVE, reverted ones back to work |
| `start.py` / `stop.py` | start in the background without a console window (idempotent) / stop only this board's own pid |
| `watch.py` | manager: Monitor command that prints new decision lines, ends by itself after N minutes |
| `tick.py` | manager: health check with FLAG lines; `--relayed` moves the cursor; `tick_local.py` = project checks |
| `scaffold.py` | `init` a project, add a `studio` |
| `server.log`, `server.pid` | written at run time next to the config |

## Run
```
python studio-hub/board/start.py            # http://127.0.0.1:<port>/
python studio-hub/board/stop.py
```
Every script takes `--config <path to board.config.json>`; without it, env `STUDIO_BOARD_CONFIG`, else the config next to the
script. The sample project: `python board/start.py --config sample/studio-hub/board/board.config.json` from the runbook folder
(stop it with `stop.py` and the same `--config`).

## Config keys (board.config.json; paths are relative to the config file's folder)
| Key | Meaning |
|---|---|
| `project`, `app_id`, `port` | page title, the id the start / stop scripts check, the port (127.0.0.1 only) |
| `root` | the project root: every picture must be inside it |
| `paths` | register, decisions, progress, bundle, requests, ready, build_marker, queue |
| `image_bases` | folders (relative to the root) that short picture paths are looked up in |
| `terms` | the project's words for studio(s), manager, user, result, build, ready file (shown on the page) |
| `studios[]` | `key`, `prefix` (card ids), `owner` (name in card headers, notes, ready file), `label`, `icon`, `color`, `ready` (has a ready file), `queue_owner` |
| `statuses` | per status key: `word` (written in the register), `label` (shown), `enabled` (HANDOFF / LIVE / BACKLOG only) |
| `fields`, `image_fields` | card field order; fields whose pictures are shown |
| `priority` | `default` (1-4) and `names` |
| `stale_hours` | an IN WORK card with no studio note for this long is tinted stale (and flagged by tick.py) |
| `schedule` | `handover`, `deadline`, `build` times (HH:MM), shown on the page and used by tick.py |
| `panels` | `requests`, `bundle` (`owner`, `title`, `button`), `queue` (`title`), `system` (`gpu`: "nvidia-smi" or "") on / off |
| `queue` | resq settings: turn_max_min, grace_s, turn_tail_min, short_max_min, gap_ban_min, priority_owners, hold_line, gate_cmd, on_hold_url |

Icons: brush, leaf, sun, cube, gauge, parcel, megaphone, spray, tiles, music, film, code, bug, book, pen, chart, map, wrench, globe,
star. A studio or a status added in the config shows after a board restart (ask the user first: never restart while they use it).

## API (JSON)
GET `/api/health`, `/api/config`, `/api/tasks`, `/api/requests`, `/api/bundle`, `/api/queue`, `/img?p=<path inside the root>`.
POST (header `X-Studio-Board: 1`, `Content-Type: application/json`): `/api/decide` {id, action, hash, comment},
`/api/priority` {id, hash, level}, `/api/new` {studio, priority, title, what, visual}, `/api/question` {id, question},
`/api/answer` {id, reply_to, text}, `/api/merge` {name, comment}, `/api/hold` {action: hold | release}.
Decide actions: approve, reject, backlog, approve_backlog, reject_backlog, accept, reject_result, close (reason required), reopen.

## Safety
- Bound to 127.0.0.1; the Host header must be 127.0.0.1 / localhost with the port; POSTs need the custom header and a same-origin
  Origin; bodies up to 64 KB; a strict Content-Security-Policy; pictures only from inside the project root.
- Every register write changes one block, refuses if the block changed since the page loaded (hash check, 409 conflict), keeps the
  file's line endings / BOM / encoding, and goes through a temp file + `os.replace`.
- The decision log and the progress notes are append-only. The board runs no commands (except an optional `nvidia-smi` read and
  the optional `on_hold_url` call after the user's hold).
- The page is reachable only on this PC. For phone access you need something else (e.g. a hosted page that reads a copy).

## Tests
`python ../tests/smoke_test.py` (from the runbook folder) builds a throw-away project, runs every route and command against it on a
free port (8800-8899) and stops only its own server.
