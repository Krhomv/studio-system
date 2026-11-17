# Studio system: one manager, many studios, one user who decides

A way of running a long creative or technical project with several AI sessions at once.

- **Studios** are separate sessions. Each one owns one subject (for example art, audio, levels, performance).
  A studio proposes work with pictures, does the work once approved, and shows the result.
- **The user** decides everything that changes the product: what starts, what is accepted, what is merged or published.
  The user decides on a local web **task board**, not by chatting with each studio.
- **The manager** is one more session. It keeps the work moving: it relays the user's board decisions to the studios,
  watches a shared scarce resource (often a GPU), runs a health check every 20 minutes, calls the studios to hand over
  before each build, runs the build, marks shipped work as LIVE, and halts everything near the usage limit.

This folder holds the runbook, the templates, and a generic copy of the task board and the resource queue.
Copy them into a project with `board/scaffold.py`, then fill them in after interviewing the user
(`runbook/12_deploy_new_project.md`).

## Quick start

```
python C:/AI/studio-system/tests/smoke_test.py
```
Builds a throw-away project in a temp folder, runs every board route and command against it, and stops only its own server.

```
python C:/AI/studio-system/sample/make_sample.py --config
python C:/AI/studio-system/board/start.py --config C:/AI/studio-system/sample/studio-hub/board/board.config.json
```
Opens the sample board on http://127.0.0.1:8790/ (stop it with `stop.py` and the same `--config`). Rerun `make_sample.py` to reset it.

To set up a real project, ask a session to follow `runbook/12_deploy_new_project.md` (new project) or
`runbook/13_adapt_existing_project.md` (a project that already runs sessions). It interviews you first.

## The loop

```
   studio                         user (board)                  manager
   ------                         ------------                  -------
   PROPOSED card + picture  --->  Approve / Reject / Backlog --> relays the user's words
        |                                                        to the studio
        v
   APPROVED -> IN WORK  (progress notes, asks with pictures) <-- user answers on the board
        |
        v
   RESULT (A/B picture)     --->  Accept / Rework  ---------->  relays
        |
        v
   ACCEPTED -> item written into ready/<owner>.md
        |                                                   handover call (~1 h before the deadline)
        v                                                   build (BUILD_RUNNING freeze)
   HANDOFF                                                  mark_live.py -> LIVE
                                                            morning report to the user
```

Nothing starts without the user's approval. Nothing ships without the user's accept.
The board is the only place the user has to look.

## Reading order

| Reader | Start with | Then |
|---|---|---|
| The user | this file, `runbook/00_overview.md`, `runbook/05_workflow.md` | `runbook/04_task_board.md` (what the buttons do) |
| The manager | `runbook/01_roles.md`, `runbook/07_manager_routine.md` | 04, 05, `08_build_and_publish.md`, `09_shared_resources.md`, `10_safety_rules.md`, `11_continuity_and_budget.md` |
| A studio | the project's `studio-hub/TASKS_GUIDE.md` and its own `studios/<key>/AGENT.md` | `runbook/05_workflow.md`, `runbook/06_evidence.md` |
| The deploying agent | `runbook/12_deploy_new_project.md` or `runbook/13_adapt_existing_project.md` | everything else, then `templates/` |

A studio in a deployed project never reads this folder directly. It reads the filled-in copies in the project
(`studio-hub/TASKS_GUIDE.md`, its `AGENT.md`). This folder is the source those copies are made from.

## Folder map

```
C:/AI/studio-system/
  README.md                  this file
  runbook/
    00_overview.md           the model, the loop, default terms
    01_roles.md              user, manager, studios, subagents; who may decide what
    02_project_layout.md     the folder tree a deployed project gets
    03_studio_lifecycle.md   create, run, hand over, park, fold, retire a studio
    04_task_board.md         the register, statuses, actions, logs, asks, panels, API
    05_workflow.md           propose -> approve -> work -> result -> accept -> ship, step by step
    06_evidence.md           what a proposal, an ask and a result must show
    07_manager_routine.md    the manager's scheduled prompts, tick flags, relays, hygiene
    08_build_and_publish.md  ready files, handover call, freeze, the build, LIVE, morning report
    09_shared_resources.md   the queue for a scarce shared resource (GPU, device, licence)
    10_safety_rules.md       files, processes, servers, permissions, privacy
    11_continuity_and_budget.md  handover logs, compaction, crons, usage halt, model and effort
    12_deploy_new_project.md the deploying agent's interview and setup steps
    13_adapt_existing_project.md  retrofitting a project that already has sessions and folders
    14_lessons.md            pitfalls seen in practice, each with its fix
  templates/                 files scaffold.py copies into a project ({{...}} filled, <...> by hand)
    project/ hub/ manager/ manager/prompts/ studio/  relay_messages.md  memory_rule.md
  board/                     the task board (stdlib Python): server.py, index.html, note.py, prio.py,
                             mark_live.py, start.py, stop.py, watch.py, tick.py, tick_local.py,
                             scaffold.py, README.md (board.config.json is written per project by scaffold.py)
  queue/                     resq.py + README.md: the generic queue for a shared resource
  sample/                    a fictional project with three studios and cards in every status (make_sample.py rebuilds it)
  tests/                     smoke_test.py: starts the board on a spare port and exercises every route
  skill/SKILL.md             an optional Claude Code skill ("deploy the studio system"), not installed
```

## Glossary (default terms)

Every term below can be renamed for a project. The board shows the names from `board.config.json`:
`"terms"` renames the words in the page, `"statuses"` renames the status labels (and, if really needed, the
words written in the register). The meaning of each stage never changes.

| Term | Meaning | Renamed with |
|---|---|---|
| studio | a session that owns one subject and its folder `studios/<key>/` | `terms.studio`, `terms.studios` |
| manager | the session that relays, watches, builds and halts | `terms.manager` |
| user | the person who decides; the board says "you" | `terms.user` |
| card / task | one block in `studio-hub/data/PROPOSALS.md`, ID `<PREFIX>-NN` | - |
| register | `PROPOSALS.md`, the list of all cards | - |
| result | the evidence a studio posts for accept, usually an A/B picture | `terms.result` |
| build | the step that turns accepted work into the shipped product | `terms.build` |
| ready file | `studio-hub/ready/<owner>.md`: what a studio hands to tonight's build | `terms.ready_file` |
| handover call | the manager's message, about an hour before the deadline, asking every studio to fill its ready file | - |
| LIVE | a card whose work shipped in a build | `statuses.LIVE.label` |
| ask | a studio's question to the user, posted on the board with a picture | - |
| GEN thread | `GEN-<key>`: a studio's general thread for questions that belong to no card | - |
| decision log | `studio-hub/data/decisions.jsonl`: every user action, one JSON line each | - |
| relay | the manager passing a decision to the studio, quoting the user's words and time | - |
| owner name | a studio's stable name in cards, ready files and the queue (`art-studio`) | `studios[].owner` |
| queue | `resq.py`: turns on a shared scarce resource | `panels.queue.title` |
| hold | the user's reservation of the shared resource from the board | `queue.hold_line` |
| bundle | one open set of changes (for example a merge branch) that only the user's button merges | `panels.bundle` |
| freeze | `studio-hub/BUILD_RUNNING` exists: nobody edits what the build reads | - |

Status words, in order: PROPOSED, APPROVED, IN WORK, RESULT, ACCEPTED, HANDOFF, LIVE, plus BACKLOG, REJECTED, CLOSED.
HANDOFF, LIVE and BACKLOG can be switched off for projects that do not need them (see `runbook/04_task_board.md`).

## Requirements

- Python 3.9 or newer, standard library only. The board binds to 127.0.0.1 only.
- Claude Code with linked sessions (the manager starts the studios), scheduled prompts (CronCreate) and Monitor.
- Windows-first (no console windows, process checks via Windows APIs); the code also runs on macOS and Linux.
