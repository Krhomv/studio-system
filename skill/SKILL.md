---
name: studio-system
description: Deploy, set up or adapt the "studio system" on a project — one manager session plus many subject studio sessions, a local task board where the user approves proposals and accepts results, a shared-resource queue and a scheduled build/publish routine. Use when the user asks to set up studios, a manager/coordinator session, the task board / approval board, or to bring this way of working to a new or existing project; also to add, park, fold or retire a studio in a project that already runs it. Not for one-off task lists.
---

# Studio system

The runbook, templates and tools live in `C:/AI/studio-system/`. Read `C:/AI/studio-system/README.md` first.

## Pick the path

| The user wants | Follow |
|---|---|
| The system on a **new** project | `runbook/12_deploy_new_project.md` |
| The system on a project that already has sessions, folders and habits | `runbook/12_deploy_new_project.md` (interview) + `runbook/13_adapt_existing_project.md` |
| A new studio in a project that runs the system | `runbook/03_studio_lifecycle.md` (create) |
| Park, fold or retire a studio | `runbook/03_studio_lifecycle.md` |
| The manager's routine (tick, relay, handover, build, usage) | `runbook/07_manager_routine.md`, `runbook/08_build_and_publish.md`, `runbook/11_continuity_and_budget.md` |

## Rules while deploying

- **Interview first.** Never fill the config from assumptions. Ask in small batches, defaults first, then show the mapping table
  and wait for the user's yes (`runbook/12`, "The interview").
- Scaffold with `python C:/AI/studio-system/board/scaffold.py init <project root> --name "<Project>"`; add studios with
  `python <root>/studio-hub/board/scaffold.py studio <key> --prefix <PREFIX> --label "<Label>"`.
- The tool is **copied** into the project; never edit the template copy in `C:/AI/studio-system/` for one project's needs.
- Don't move existing project folders; point to them (`runbook/13`).
- Start studio sessions only in the user's own turn, with the brief from `studios/<key>/BRIEF.md`, working folder
  `studios/<key>/`, and the model and effort the user chose.
- Use a free local port for the board; never take over a port another tool uses; never restart a tool the user may be using.
- Keep personal data, secrets and other people's names out of every shared file.
- Don't commit, publish or merge anything without the user's explicit say-so.

## Done means

The board runs on the project's port with the user's words and studios, `tick.py` prints `OK`, each studio has posted its first
state note and proposals, the manager's crons and decisions watcher are armed and recorded in `studio-hub/manager/NEXT.md`, and
the user has been told the board URL, the schedule and how to halt.
