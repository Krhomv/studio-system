# <round> {{TERM_BUILD}} (<label>): <one line: base / inputs> + the {{TERM_STUDIO}}s' user-accepted items

Written by the {{TERM_MANAGER}} at <date time> from `{{HUB}}/PUBLISH.md`, the frozen {{TERM_READY}} copies in `ready/` and `{{HUB}}/manager/NEXT.md`.
You are the {{TERM_BUILD}} agent. Follow this brief top to bottom. Keep `RESUME_BUILD.md` (same folder) current after every step, so a
fresh agent can resume from it.

## Labels
- Round: <rNN>. Label: <label>. Previous: <label of the last build> (its brief: `{{HUB}}/builds/<prev round>/BUILD_BRIEF.md`).
- Base / other inputs: <describe, e.g. the merged bundle name and version, or "unchanged">.
- Queue owner: `build-<rNN>` (priority owner in resq).

## What goes in
| Owner | Stamp | Items (card IDs) | Notes |
|---|---|---|---|
| <owner> | <stamp> | <IDs> | <order constraints, stacking, "already live"> |

Not taken tonight (and why): <IDs / unmerged bundles / items marked not ready>.

## Steps
1. Check that `{{HUB}}/BUILD_RUNNING` exists (the {{TERM_MANAGER}} wrote it at the trigger).
2. Apply, in this order (dry run, then `--apply`; log each backup / revert stamp in RESUME_BUILD.md):
   - <owner>: <commands copied from the frozen ready copy>
3. Build: <describe the build steps and their logs>.
4. Delete `{{HUB}}/BUILD_RUNNING` once the shared files are no longer read: <describe the point>.
5. Gates (on the SHIPPED artefact): <standing gates> + each {{TERM_READY}}'s own checks (listed below).
   - <owner> <ID>: <check, expected numbers, what worse looks like>
6. Evidence: <captures / audits / measurements>, against <baseline>. For items whose output depends on other inputs, compare
   against a same-inputs baseline (the pre-change version run on tonight's inputs), not against last night's {{TERM_BUILD}}.
7. Write `RESULT.md` (template `BUILD_RESULT.md`) and report to the {{TERM_MANAGER}}.

## Rules
- A failing item: revert it with its own revert command and rebuild from the earliest step it touches, if there is time (finish by
  <time>). Otherwise list it for the morning, unreverted. Never patch around it, never edit a {{TERM_STUDIO}}'s installer.
- Queue only through `python {{HUB}}/queue/resq.py`, owner `build-<rNN>`. Release between long phases if nothing needs the resource.
- Off-screen, no console windows (CREATE_NO_WINDOW). Stop only your own pids. No config changes, no merges, no commits
  (except the backup step if the brief lists it).
- Temp file + `os.replace` for every write to a shared file.
- Usage: check before each step; at <threshold> % stop at the next safe point, release the queue, complete RESUME_BUILD.md,
  report "HALTED at <step>".
- Stop at the first hang and report it with the log tail; don't retry blindly.
- Subagents you start (auditors): model <describe>, effort <describe>.
