# 12 · Deploying the system on a new project

For the agent that sets the system up (usually the session that will become the manager). For an existing project with sessions
and folders already in use, read `13_adapt_existing_project.md` too.

**Never deploy from assumptions.** The defaults come from one production; the right terms, cadence and evidence differ per
project. Interview the user first, show them the mapping, then build.

## Steps

0. **Read** `README.md` and `runbook/00` to `11`. Look at `sample/` and the board running on it if you need to see it.
1. **Interview the user** (below). Ask in small batches (up to four questions at a time); offer the default as the first option.
2. **Write the mapping table** (below) and show it to the user. Change it until they say yes.
3. **Scaffold the hub** from the template folder:
   `python C:/AI/studio-system/board/scaffold.py init <project root> --name "<Project>" [--hub studio-hub] [--port 8790] [--no-queue]`
   It copies the board, the queue (unless `--no-queue`) and the templates into the layout of `02_project_layout.md`, fills the
   `{{...}}` placeholders it knows and lists the ones left.
4. **Fill the config and templates** with the interview's answers:
   - `studio-hub/board/board.config.json`: `terms`, `statuses` (labels, words, enabled), `fields`, `priority`, `stale_hours`,
     `schedule`, `panels`, `queue`. Studios are added in step 6.
   - `studio-hub/TASKS_GUIDE.md`: every `<describe ...>` part (evidence standard, protected areas, permissions, decisions taken).
   - `studio-hub/PUBLISH.md`: the project's real build steps, gates, labels, revert, backup, cutoffs.
   - `studio-hub/manager/AGENT.md`, `USAGE_HALT.md`, `prompts/*.txt`: thresholds, times, model and effort.
   - Record the mapping table in `studio-hub/README.md` under "This project's choices".
5. **Start and check the board.**
   - `python C:/AI/studio-system/tests/smoke_test.py` once: it checks the template tool on its sample data, on a spare port, and
     stops only its own server.
   - `python studio-hub/board/start.py`, then open the URL. Check: the page loads, the terms read right, the parser shows no
     warnings, the panels you enabled show data.
   - `python studio-hub/board/tick.py` prints a status block and `OK`.
6. **Create the studios**, one at a time (`03_studio_lifecycle.md`):
   - `python studio-hub/board/scaffold.py studio <key> --prefix <PREFIX> --label "<Label>" [--owner <owner>] [--icon <name>] [--color "#rrggbb"] [--no-ready]`
     adds the studio to the config, the guide's studio list and `studios/<key>/` from the templates.
   - Fill its `AGENT.md` (role, domain, boundaries, first deliverable) and `BRIEF.md`.
   - Restart the board once after adding studios (ask the user first if they are using it).
   - Start each studio session in the **user's turn**: `start_session` with the brief as prompt, fresh context, working folder
     `studios/<key>/` (the app may ask the user to trust the folder), the model and effort from the interview. If the folder
     can't be used, start it at the project root and tell it to read `studios/<key>/AGENT.md` first.
7. **Arm the manager routine** from `studio-hub/manager/prompts/` (`07_manager_routine.md`): the tick cron, the usage check,
   the handover call and build trigger if the project builds, and the decisions watcher (`watch.py --minutes 30` under Monitor).
   Record every id in `NEXT.md`.
8. **Day 1** (checklist below).
9. **Tell the user** (end of this page).

## The interview

Each group says why it matters and where the answers go.

### A. The project and its product
1. What is the project, in two lines? Where is its root folder?
2. What does the user actually experience at the end: a game build, a website, a video, a document, a dataset?
3. Where and how is that product made today (a build script, an export, a render)?
4. Platform: OS, shell, Python version (3.10 or newer), a free local port for the board.

Why: the evidence and the build depend on what "the shipped product" is. → `project`, `root`, `port` in the config;
`PUBLISH.md`; `TASKS_GUIDE.md` §4.

### B. Who decides
1. Is the user the only one who approves, accepts and merges? Anyone else?
2. What may studios fix without a card? (Default: tooling and pipeline bugs only, with a board note.)
3. Are there protected areas, other people's work, or things nobody may touch?

Why: authority is the core rule of the system. → `TASKS_GUIDE.md` §1 and §7; `manager/AGENT.md`.

### C. The subjects (studios)
1. Which subjects need their own studio? For each: a short key, a card prefix, an owner name, a label, an icon and a colour.
2. What may each one touch, and what belongs to another studio? Who owns shared domains (brightness, geometry, shared data)?
3. Which studios ship into the build (keep a ready file) and which only plan or advise?
4. Does one studio own a bundle that the user merges by button (`panels.bundle`)? Does one keep an inbox of requests from the
   others (`panels.requests`)?
5. What should each studio deliver first?

Why: clean boundaries prevent two writers on one file. → `studios[]` (via `scaffold.py studio`), `panels`, each `AGENT.md`.

### D. Words
1. What do you call a studio, the manager, a build, a result, a ready file? (Defaults: studio, manager, build, result, ready file.)
2. Status names: keep PROPOSED / APPROVED / IN WORK / RESULT / ACCEPTED / HANDOFF / LIVE / BACKLOG / REJECTED / CLOSED, or rename
   their labels? Do you want a backlog?

Why: the user reads the board all day; it should use their words. → `terms`, `statuses` (`label`, optionally `word`, `enabled`).

### E. Evidence
1. What must a proposal show before you decide? What must a result show before you accept?
2. Is there a reference truth (footage, a spec, a design, a recording, metrics) that results are judged against?
3. How do you see the product (in play, in a browser, on a phone, printed)? Can a studio reproduce exactly that view?
4. Numbers, pictures, or both? How big must a difference be to count?

Why: this sets what a studio does before you see anything. → `TASKS_GUIDE.md` §4, `fields`, `image_fields`, `06_evidence.md`.

### F. Scarce shared resources
1. What can only one job use at a time (GPU, device, build machine, licence, API)? How long are typical jobs?
2. Is there a gate (free memory, no other instance) and who may hold the resource first (the build)?
3. Do you want a Hold button to take the resource for yourself?
4. Shared local services (a model server, a database) that sessions must not start twice or restart?

Why: without a queue, jobs starve and stall each other. → `queue` section, `panels.queue`, `panels.system`, `--no-queue`.

### G. Cadence
1. When do you review the board? Do you want batches or single items?
2. Is there a build, and when (nightly, weekly, on demand, never)? Handover call and deadline times?
3. Tick interval (default 20 min), stale threshold (default 3 h), quiet hours?

Why: the routine and the cutoffs come from this. → `schedule`, `stale_hours`, `prompts/*.txt` cron lines, `PUBLISH.md`.

### H. Publishing
1. The build steps, from inputs to the shipped artefact. How long they take.
2. The gates that prove a build is good. What "worse" looks like.
3. How to revert one item. Where builds land. How they are labelled.
4. Backup every night? Skip the build when nothing changed?

Why: the build agent must run unattended. → `PUBLISH.md`, `build_trigger.txt`, `templates/hub/BUILD_BRIEF.md`.

### I. Budget
1. Usage halt line and watch line (defaults 98 % / 95 %)? Which usage windows count?
2. Model and effort for the manager, studios, build agent, auditors?
3. A cap on concurrent subagents?

Why: a halt mid-switch wastes work; effort is the user's call. → `USAGE_HALT.md`, `usage_check.txt`, `manager/AGENT.md`, `BRIEF.md`.

### J. Permissions
1. What needs your explicit say-so beyond approving a card: merges, config files, publishing, commits, deletes, spending?

→ `TASKS_GUIDE.md` §1, `10_safety_rules.md` table, each `AGENT.md`.

### K. Your attention
1. How should the board alert you (the bell, desktop notifications)? Should task-complete banners stay off?
2. Do you need the board on your phone? (It is localhost only; that needs another setup.)

→ `manager/AGENT.md` ("route everything through the board").

### L. Existing material
1. Existing sessions, notes, to-do lists, folders, scripts to migrate? → `13_adapt_existing_project.md`.

### M. Privacy
1. Names, secrets, prices or plans that must never be written into shared files?

→ `TASKS_GUIDE.md` §7, `manager/AGENT.md`.

## The mapping table

Show it to the user before step 3. One row per decision:

| Item | Default | This project |
|---|---|---|
| Studio / manager / build / result / ready file | studio / manager / build / result / ready file | |
| Statuses kept / renamed | all ten, default labels | |
| Studios (key, prefix, owner, ships?) | — | |
| Evidence for a proposal / a result | picture of current state + reference / same-view A/B | |
| Shared resource, gate, priority owners | none | |
| Build cadence, handover, deadline, build time | nightly 01:45 / 02:45 / 03:03 | |
| Tick, stale, usage watch / halt | 20 min, 3 h, 95 % / 98 % | |
| Explicit say-so list | merges, config, publishing, commits | |
| Model and effort per role | strong model, high effort | |
| Board port | 8790 | |

## Day-1 checklist

- [ ] Each studio posted a state note on `GEN-<key>` with a picture and 3-6 PROPOSED cards with visuals.
- [ ] The board shows them with no parser warnings; the manager batched them for the user.
- [ ] The user approved a first batch; the relay worked end to end: decision → `watch.py` line → message to the studio quoting the
      user's words → `tick.py --relayed`.
- [ ] A studio ran one job through `resq.py` with `--task`, and `resq.py status` looked right.
- [ ] A studio posted an ask with options and a picture; the user answered on the board; the answer reached the studio.
- [ ] Before the first build: each shipping studio dry-ran its ready file; the manager rehearsed the trigger with the skip check.
- [ ] The first build ran while someone could watch it; the morning report and LIVE marking happened.
- [ ] NEXT.md lists every cron id with its creation date.

## What to tell the user when done

In a few lines:
- the board URL and what needs them there (Proposed and Result columns, the Questions tab, the bell);
- the studios and what each does;
- the schedule: ticks, handover call, deadline, build, morning report;
- where things are (`studio-hub/`, `studios/`), and that `TASKS_GUIDE.md` is the rulebook;
- how to stop everything (tell the manager "halt"), and that crons expire after 7 days unless re-created.
