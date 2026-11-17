# 07. The manager's routine

The manager keeps the work moving without being asked. Why: the studios run unattended for hours; a stuck job, an idle
studio or an unrelayed decision can waste half a day before anyone looks.

All commands run from the project root. The full prompt texts are in `templates/manager/prompts/`; the deployed copies
live in `studio-hub/manager/prompts/`, filled for the project.

## At session start (and after a resume or compaction)

1. Read the top entries of `studio-hub/manager/NEXT.md`.
2. `mcp__ccd_session_mgmt__list_sessions {"linked": true}`: which studios exist, which are working.
3. Board up? `python studio-hub/board/start.py` (it does nothing if the board already answers).
4. Scheduled prompts: list them (CronList). Re-create any that are missing from `manager/prompts/`. Record their ids in
   `NEXT.md`.
5. Arm the decisions watcher (below).
6. Read usage once (`mcp__ccd_session_mgmt__get_usage`).
7. Run `python studio-hub/board/tick.py` and act on its flags.
8. One short line to the user: what runs, what waits for them.

## The scheduled prompts

Scheduled prompts (CronCreate) belong to the session that made them: they die with it and expire after 7 days.
Re-create them after an app restart, a session switch, and before day 7; `NEXT.md` holds their ids and creation dates.
The scheduler may fire a few minutes (or a fixed offset) away from the minute given: check the first firing and note the
real time in `NEXT.md`. Times below are examples for a 02:45 deadline and a ~03:00 build.

| Prompt | Cron (example) | Template | Purpose |
|---|---|---|---|
| Tick | `7,27,47 * * * *` | `tick.txt` | health check every 20 min, act only on flags |
| Decisions watcher | Monitor, not cron; re-armed every 30 min | `decisions_watch.txt` | relay each user action within a minute |
| Usage check | `19,49 * * * *`; every 10 min at 95 % or more | `usage_check.txt` | halt at the threshold |
| Handover call | ~1 h before the deadline, e.g. `43 1 * * *` | `handover_call.txt` | every studio fills its ready file |
| Build trigger | build time, e.g. `3 3 * * *` | `build_trigger.txt` | start the build as a subagent |
| Morning report | when the build agent reports (backstop cron e.g. `30 8 * * *`) | `morning_report.txt` | LIVE marking, report, resume studios |
| Halt stragglers | one-shot, 10 min after a halt | `halt_stragglers.txt` | stop the manager's own sessions still working |
| Resume | by hand, after the user lifts a halt | `resume.txt` | re-create crons, re-arm, tell studios to resume |

**Tick.** Run `tick.py`, then list linked sessions. Act only on what needs it, per the flag table below. While
`studio-hub/BUILD_RUNNING` exists, skip everything except a HOLD by a studio owner. If all is OK, end the turn with one
short line and no wrap-up box.

**Decisions watcher.** A Monitor runs `python studio-hub/board/watch.py --minutes 30`. It prints each new line of
`decisions.jsonl` past the cursor as it arrives and exits after 30 minutes on its own (no orphan loops). On each line:
relay it to the studio in the format below; after relaying, run `python studio-hub/board/tick.py --relayed`. When the
Monitor ends, arm it again. `live` / `revert` lines are the manager's own and need no relay.

**Usage check.** Read `get_usage`. At the halt threshold (default 98 % of the weekly window), follow
`studio-hub/manager/USAGE_HALT.md`: HALT to every studio and subagent, delete the crons, full handover in `NEXT.md`, one
message to the user, stop. At 95 % or more, check every 10 minutes. Below 95 %, one line. Details in
`11_continuity_and_budget.md`.

**Handover call.** Message each studio that ships into the build: put everything finished, checked and user-accepted
into `ready/<owner>.md` by the deadline, including anything labelled "for tomorrow"; only unaccepted or unchecked work
stays "not ready"; one line back with what's in; no long jobs on the shared resource that would still run at build time.
Then, at the deadline, check the stamps and note them in `NEXT.md` for the build brief. See `08_build_and_publish.md`.

**Build trigger.** Follow `studio-hub/PUBLISH.md`, "Manager at the trigger": backup, skip check, label, brief from the
ready files plus `NEXT.md` notes, frozen ready copies, `BUILD_RUNNING`, spawn the build subagent (cron turns cannot start
sessions, so the build is always a subagent), arm a hang watchdog.

**Morning report.** When the build agent reports: `mark_live.py` for every shipped card, `--revert-to-work` for reverted
ones, `applied.json` stamps, tell each studio the build is done and the shared resource is theirs again with its own
items' results, then one short report to the user with one or two pictures.

**Halt stragglers.** Ten minutes after a halt: stop any session the manager started that is still working. Never stop
a session the manager did not start (message only). Never kill a running job on the shared resource: it finishes and
releases by itself.

## Tick flags and what to do

| Flag | Meaning | Action |
|---|---|---|
| DECISION | a user action not yet relayed | relay it now (format below), then `tick.py --relayed` |
| BOARD ... has a result but reads APPROVED / IN WORK | evidence posted, no Accept button | ask the studio to set RESULT |
| BOARD ... no studio note for N h | stale card | ask the studio for a status note; if the card is overtaken by events, close it with a reason or mark "waiting for X" |
| BOARD ... IN WORK with no progress note | started silently | ask for a first note |
| BOARD DOWN (restarted) | the board did not answer; tick restarted it | check `board/server.log` if it repeats |
| READY | a studio's ready file is old near the deadline | nudge that studio to write or refresh it by the deadline |
| HOLD | the queue lock is held too long, or by a dead process | read the holder's log tail; if stuck, message the owner studio with the evidence (pid, last log line) and ask it to stop its own process and release; never kill another session's process |
| WAIT | a ticket has waited a long time | recheck after 1 minute, then find out why (turn order, a gate, a long holder) and message the right studio |
| STUCK | lock free, tickets waiting, no grace running | recheck after 1 minute; if still stuck, find the waiter that never takes it and message its studio |
| GATE | the resource's gate is shut by something outside the queue | tell the user in one line which of their apps hold how much; never loosen the gate yourself |
| (project flags) | from `tick_local.py` | as documented in that file |

Beyond the flags, each tick also looks at:
- **Idle studios.** A studio idle for more than 60 minutes with no queued job: point it to its user-approved cards
  (`prio.py --studio <key>`), or ask it to propose a batch with pictures. Never suggest self-chosen work. Skip studios
  the user parked.
- **New PROPOSED / RESULT cards** (the tick prints counts and IDs): batch them for the user when a few have piled up or
  one is urgent, with their pictures.
- **Open asks** waiting for the user: mention them when they pile up or block work.

## Relay message formats

Full formats in `templates/relay_messages.md` (scaffold.py copies it, filled, to `studio-hub/manager/relay_messages.md`). The shape is always the same: card, what the user did, the user's words in
quotes, the time, what the studio should do next.

| Action | Message to the studio |
|---|---|
| approve | `AUD-04 APPROVED by the user (board 10:02, "Approve. keep the gust layer"). Priority P2. Start when it's your top card.` |
| reject / backlog | `AUD-05 REJECTED by the user (board 10:04, no comment). Don't re-propose it.` / `... BACKLOG: don't work on it or re-propose it.` |
| accept | `AUD-04 ACCEPTED (board 16:40, "Accept: 80 ms"). Ship only the 80 ms variant: ready file + HANDOFF.` |
| reject_result | `AUD-04 sent back for rework (board 16:41, "<words>"). Rework, then RESULT again.` |
| priority | `AUD-04 priority P3 -> P1 (board 11:00). Re-check prio.py.` |
| question | `The user asks on AUD-04 (board 12:10): "<question>". Answer with note.py AUD-04 "..." --answer.` |
| answer | `The user answered your ask on AUD-04 (board 13:40): "<answer>".` |
| new_request | `New request for you: AUD-09 "<title>", APPROVED P2 (board 09:15): "<what>".` |
| merge | `The user requested the merge of bundle <name> (board 14:40). This is the user's say-so for that one merge.` |
| hold / release | to every studio using the resource: `The user holds the GPU from the board (14:05): stop chained runners, queue nothing long.` / `... released: queue as usual.` |

Relays carry the user's words because a studio must be able to tell the user's decision from the manager's opinion.
After relaying, run `tick.py --relayed`. The board then shows "passed to the studio".

## Board hygiene review (a few times a day)

- **Priority order.** Compare `prio.py` with what each studio is actually doing and queuing. Move a studio onto its
  highest-priority approved card.
- **Stale.** Cards with no note for more than `stale_hours`: ask for a note. Cards overtaken by events: close with a
  reason, or mark "waiting for X". Ask the user only when relevance is unclear.
- **True statuses.** Evidence posted = RESULT. Shipped = LIVE. Moved = CLOSED with a link. Partially approved = scope in
  the bracket.
- **Parser warnings.** The board header shows them; ask the owning studio to fix its block.
- **The base guide.** When the user set a new rule today, it is in `TASKS_GUIDE.md` with their words and date, and every
  studio was told.

## Process improvements

When work is slow, measure before proposing: time per job on the shared resource, how much of it is overhead, rounds lost
to mismatched labs or misaimed fixes, accepts that came without a pick. Propose a short list of changes with the numbers
to the user. The user decides; then write the accepted ones into `TASKS_GUIDE.md` and tell the studios. Never change a
queue or process setting on a hunch: measure it first (the queue's `events.log` exists for that).

## NEXT.md: the manager's log and handover

- Newest entry at the top. Each entry starts with the date and time and a short title in capitals.
- Write an entry for: every user decision that changes the plan, every build (start, result), every new or retired
  studio, every halt and resume, every cron re-creation (with ids), anything the next build brief must know
  ("FOR THE BUILD BRIEF: ...").
- Before a context compaction (or when the context is getting long), write a state snapshot entry: crons and their ids,
  the watcher, tonight's build plan, each ready file's state, what waits for the user, anything unusual.
- Keep each entry to a few lines; details belong in studio notes and build folders.

## Staying free

- Dispatch long work (builds, audits, research) to subagents. Keep the manager's own turns short; end them once work
  is dispatched; let notifications bring results back.
- Don't relay through long messages. A long brief goes into a file; the message points to it.
- Messages to sessions are capped per user turn (about 10). For a fan-out to many studios, write one brief file and send
  short pointers; tell the user how many still need a message.
- A cron or watcher turn cannot start sessions. Night work runs as subagents of the manager
  (`11_continuity_and_budget.md`, "App limits").
