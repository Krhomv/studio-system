# 11 · Continuity and budget

Sessions get compacted, restarted, switched to another account and halted at usage limits. Scheduled jobs expire. This page
covers how the system keeps its memory and its routine through all of that, and how it spends its budget.

## Where knowledge lives

| Kind of knowledge | File | Written by |
|---|---|---|
| Rules every studio follows (wins over any other file) | `studio-hub/TASKS_GUIDE.md` | manager, when the user sets a rule |
| Decisions the user already took ("don't re-flag") | `TASKS_GUIDE.md`, last section | manager |
| A studio's role, domain, boundaries | `studios/<key>/AGENT.md` | manager at creation; updated on the user's word |
| A studio's lasting working knowledge | `studios/<key>/NOTES.md` | the studio |
| A studio's state for a session swap | `studios/<key>/HANDOFF.md` | the studio, when handing over |
| The manager's running state and log | `studio-hub/manager/NEXT.md` | manager |
| Card progress, questions, answers | `studio-hub/data/progress/<ID>.jsonl` via `note.py` | studios, the board |
| The user's preferences and corrections for one working folder | Claude Code memory | the session that heard them |
| How to publish | `studio-hub/PUBLISH.md` | manager |

Memory is stored **per working folder**. Studio sessions run in `studios/<key>/`, so each studio has its own memory, and the
manager (at the project root) has another. Put rules that apply to everyone in `TASKS_GUIDE.md`, not in one session's memory.
When the user sets a new rule, the manager updates the guide and tells the studios.

A feedback memory follows `templates/memory_rule.md`: the rule, then **Why:** (what happened, the user's words) and **How to
apply:** (what to do differently). Save corrections and confirmed approaches; don't save what the files already record.

## The manager's `NEXT.md`

Template: `templates/manager/NEXT.md`. Newest entry at the top, one heading per entry: `## MM-DD HH:MM <TOPIC>`.
An entry holds what the next manager (or the same one after compaction) needs:
- the cron ids and when they were created (they expire, see below), the watcher's cursor;
- what each studio is on, what is waiting for the user;
- tonight's build plan and every "FOR THE BUILD BRIEF" note (labels, baselines, known side effects);
- incidents: what broke, what was done, what is still open.

Write a **snapshot entry before a context compaction** and after any halt or resume. Keep entries short; details belong in the
files they point to.

## Studio notes: knowledge, not a diary

Template: `templates/studio/NOTES.md`. On long projects, studio notes that grow as a diary reach hundreds of kilobytes and nobody
can read them after a compaction. Keep this shape:
1. **Open cards**, one line each, kept current.
2. **Where things live** (a table of the studio's folders and files).
3. **Scripts** (what each does, how to run it).
4. **Method** (how this studio measures and decides).
5. **Lessons** (what went wrong and the rule now).
6. A **short log** of the last few days. Move older entries to `logs/notes_archive_<YYYYMM>.md`.

Progress goes on the board with `note.py`, not in NOTES.md.

## Handovers between sessions

When a studio's session is replaced (after many compactions, an account switch, a fold into another studio), the outgoing
session writes `studios/<key>/HANDOFF.md` (template `templates/studio/HANDOFF.md`): what is on the board, where the work stands,
tools and how to run them, the user's decisions in force, open questions, what it was about to do next, and what not to touch.
The incoming session reads AGENT.md, HANDOFF.md, NOTES.md, then `note.py --open-asks` and `prio.py --studio <key>`.
For folding an old session into a new studio, see `13_adapt_existing_project.md`.

The app's shared notes folder for linked sessions is a good place for one-off hand-over notes and large findings that don't
belong in a studio's files.

## Context compaction

- After a compaction a studio re-reads its AGENT.md (loaded automatically when its working folder is `studios/<key>/`), the
  top of NOTES.md and TASKS_GUIDE.md if it changed.
- The manager re-reads `manager/AGENT.md`, the top of NEXT.md, and checks its crons and the watcher are still armed.
- Long investigations write a resume point into the studio's files before they get long.

## Scheduled jobs (crons)

The manager's routine runs on session cron jobs (prompts in `templates/manager/prompts/`, filled into `studio-hub/manager/prompts/`).
- Session crons **live only in that session** and **expire after 7 days**. An app restart or a session switch also loses them.
- Record each job's id, schedule and creation date in NEXT.md. Re-create them after a restart, a switch, or before day 7.
- The scheduler may fire a few minutes off the written time. Check the first firing and note the real time.
- Use odd minutes (`7,27,47 * * * *`) so jobs don't all fire on the hour.
- A cron turn **cannot start sessions** (next section). Work that must start at night runs as a manager **subagent**.
- Quiet turns end with one short line and no wrap-up box.

## Monitors and watcher loops

- The decisions watcher (`python studio-hub/board/watch.py --minutes 30`) runs under Monitor and exits after 30 minutes on its
  own. Re-arm it when it ends (prompt `templates/manager/prompts/decisions_watch.txt`).
- Hang watchdogs (log growth, flat CPU of an engine) also run under Monitor. **Every loop must expire on its own** (a `t_end`
  check). A Monitor timeout does not kill a shell loop on Windows: re-arming every 30 minutes once left dozens of orphan loops
  running. Check for orphans by command line now and then.

## App limits that shape the routine

| Limit | Consequence |
|---|---|
| A session can start other sessions only in the user's own turn, or in the side-session-event chain right after it. A turn started by a cron, a heartbeat, a scheduled task or another session's message breaks the chain. | Start studios from the user's message. Night work (the build, an audit) runs as a manager subagent (Agent tool). If the chain breaks, propose the next session as a card and tell the user one message from them restarts it. |
| About 10 messages to other sessions per user turn; then sends pause until the user writes again. | For fan-outs (handover call, halt, a new rule), put the text in a shared file and send short pointers. Stagger large batches ("send them as others finish") and tell the user how many still need a message. |
| Side-session events reach the manager when a session it started ends a turn. | Studios don't need to message the manager when done; their turn-end note arrives on its own. |

## The manager stays free to talk

The user wants to talk to the manager while work runs. Keep the manager's turns short: dispatch long work to studios or
background subagents, end the turn, and let notifications bring results back. No long foreground work in the manager.

## Usage budget

The user's plan has usage windows (read with `mcp__ccd_session_mgmt__get_usage`). The project sets thresholds in the interview;
defaults:

| Level | Action |
|---|---|
| below 95 % | one line, carry on |
| 95 % or more | check every 10 minutes (prompt `usage_check.txt`) |
| 98 % or more | **halt**: follow `studio-hub/manager/USAGE_HALT.md` |

Halt protocol (template `templates/manager/USAGE_HALT.md`):
1. Send HALT to every working studio and subagent: start nothing new, no new jobs on the shared resource (a running one may finish
   and release), write your resume notes, end your turn. Message sessions the manager didn't start; don't stop them.
2. After ~10 minutes, stop any of the manager's own sessions still working (prompt `halt_stragglers.txt`). Don't kill running
   engine jobs; they finish and release the queue.
3. Delete the crons.
4. Write a full "HALTED <time>" entry in NEXT.md: each session's state, each subagent's resume file, the queue state, the crons to
   re-create (with their prompts), open user decisions.
5. Tell the user in one short message, then stop. Later events get one line at most.

Resume (prompt `resume.txt`): re-create the crons and the watcher, check the queue, tell each studio "resume" with a pointer to
its notes.

Also:
- Studios and subagents check usage themselves at each turn or step and stop at the next safe point at the halt line.
- The user may suspend the rule for a cycle ("ignore the limit this time"). Note it in NEXT.md and in USAGE_HALT.md; it comes
  back after the reset unless the user says otherwise.
- **Don't impose your own budget caps.** Only the user sets them. Keep resume points current so a quota stop resumes cleanly.
- Below the halt line, keep dispatching normally, even work that won't finish before a reset.

## Model and effort per role

Defaults; the user decides in the interview, and running sessions keep their model unless the user asks.

| Role | Default |
|---|---|
| Manager | the user's choice for the main session |
| Studios | a strong model at high effort |
| Build subagent, auditors, design and fix subagents | the same as studios; tell build agents to spawn their auditors the same way |
| Quick look-ups, file sweeps | a lighter model or medium effort |

Don't lower effort to save budget. Near the limit, stop starting new work and keep resume points instead. Respect the user's cap
on concurrent subagents; prefer short, bounded tasks when a limit is near, so little work is cut off mid-task.
