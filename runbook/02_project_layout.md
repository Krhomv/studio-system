# 02. Project layout

Everything a studio makes lives under its own folder. Everything shared lives in one hub folder. Nothing else in the
project changes shape.

Why: when studio folders are scattered (one under a texture tree, one under a lab tree, one next to the release files),
nobody can find a studio's notes, pictures or installers, and cleanup after retiring a studio is guesswork.

## The tree

```
<project>/
  CLAUDE.md                     3 lines: this project runs the studio system; studios read studio-hub/TASKS_GUIDE.md
  studio-hub/                   the system's home (name set at deploy; default studio-hub)
    README.md                   what this folder is, the board URL, where things are
    TASKS_GUIDE.md              the rules every studio follows (wins over any other file)
    PUBLISH.md                  the build / publish procedure
    applied.json                which ready-file stamps the last build applied
    BUILD_RUNNING               exists only while a build runs (the freeze)
    manager/
      AGENT.md                  the manager's role
      NEXT.md                   running log and handover, newest entry first
      USAGE_HALT.md             the halt and resume procedure
      prompts/*.txt             the scheduled prompts, filled for this project
    board/                      the task board (copied from C:/AI/studio-system/board)
      server.py index.html note.py prio.py mark_live.py start.py stop.py watch.py
      tick.py tick_local.py scaffold.py board.config.json README.md
      server.log server.pid     (run time)
    data/
      PROPOSALS.md              the register
      decisions.jsonl           every user action, append-only
      relayed.cursor            how many decision lines the manager has relayed
      progress/<ID>.jsonl       notes, asks and replies per card (and per GEN-<key> thread)
      bundle.json               the open bundle (only if the bundle panel is on)
    ready/<owner>.md            one ready file per studio that ships into the build
    builds/<round>/             BUILD_BRIEF.md, ready/ (frozen copies), RESUME_BUILD.md, RESULT.md
    requests/REQUESTS.md        requests from one studio to the studio that owns a domain (optional)
    reviews/REVIEW_<YYYYMMDD>.md  the user's own review passes, turned into cards
    queue/                      resq.py and README.md; state: lock/owner.txt, tickets/*.json, turn.json, events.log
  studios/
    <key>/
      CLAUDE.md                 one line: @AGENT.md (auto-loads the role when the session runs here)
      AGENT.md                  the studio's role
      NOTES.md                  lasting knowledge: current state, where things live, lessons
      HANDOFF.md                only when handing over to another session or studio
      cards/                    pictures for proposals, asks and results (the board serves them)
      lab/                      scratch copies and experiments
      tools/                    the studio's own scripts
      staged/                   installers for accepted items (dry run / apply / revert)
      backup/                   backups the installers write
      logs/                     job logs
```

## Rules for the tree

- **Pictures live inside the project root.** The board serves images only from inside the root (and from the
  `image_bases` in `board.config.json`). A picture outside the root shows as "not found" on the card.
- **Card pictures go in `studios/<key>/cards/`.** Name them after the card: `ART-07_proposal.jpg`, `ART-07_result.jpg`.
- **Lab work stays in `lab/`.** Studios iterate on copies, never on the shared data the build reads.
  Lab copies go stale after a build that changes their inputs: re-copy them before judging new work against them.
- **Installers go in `staged/`.** Every accepted item ships through a script with a dry run, an apply and a revert.
  Backups go in `backup/<stamp>/`, one folder per install.
- **The hub is shared; a studio writes only its own lines there:** its register blocks, its ready file, its notes
  through `note.py`, its requests.
- **The project's own folders stay where they are.** The system adds `studio-hub/`, `studios/` and a short `CLAUDE.md`.
  When adapting an existing project, old folders stay in place and studio files point to them
  (`13_adapt_existing_project.md`).

## Where each session runs

| Session | Working folder | Loads automatically |
|---|---|---|
| Manager | `<project>/` | `<project>/CLAUDE.md` |
| Studio `<key>` | `<project>/studios/<key>/` | `studios/<key>/CLAUDE.md` (imports `AGENT.md`) and `<project>/CLAUDE.md` |

Claude Code loads `CLAUDE.md` from the working folder and every parent folder. So a studio session that runs in its own
folder gets its role and the project rules at every start and after every context compaction, without being told.

Side effect: memory is stored per working folder, so each studio gets its own memory. That is fine: rules for all
studios live in `TASKS_GUIDE.md`, a studio's role in `AGENT.md`, its knowledge in `NOTES.md`
(`11_continuity_and_budget.md`, "Memory").

Fallback: if a studio session must run at the project root (for example the app would not start it in a subfolder),
its brief tells it to read `studios/<key>/AGENT.md` first and again after each compaction.

## Names

| Name | Form | Example | Used in |
|---|---|---|---|
| studio key | short, lower case | `art` | folder `studios/art/`, `GEN-art`, `prio.py --studio art` |
| prefix | upper case | `ART` | card IDs `ART-01`, `ART-02` |
| owner name | `<key>-studio` | `art-studio` | card headers, ready file `ready/art-studio.md`, `note.py --by` |
| queue owner | usually the owner name | `art-studio` | `resq.py --owner art-studio` |
| build round | `r` + number | `r12` | `builds/r12/`, `mark_live.py <label> --round r12` |
| build label | project-defined | `v041a` | `LIVE (v041a, r12 03-14)` |

One stable owner name per studio, everywhere. Why: the queue's fairness, the board's filters and the ready files all
key on it; a studio that uses two names gets two turns and loses its cards.

## The tool is copied, not shared

`scaffold.py init` copies `board/` and `queue/` from `C:/AI/studio-system/` into the project's hub. Each project runs its
own copy on its own port. Why: projects add features to their board over time; a shared copy would let one project's
change break another's running board. Improvements worth keeping go back into `C:/AI/studio-system/` by hand.

## Config

`studio-hub/board/board.config.json` holds everything project-specific: project name, port, paths, studios (key,
prefix, owner, label, icon, colour, ready file yes/no, queue owner), status labels, terms, priorities, the stale
threshold, the schedule, which panels show, and the queue's settings. All paths in it are relative to the config
file's folder. `04_task_board.md` lists every key.
