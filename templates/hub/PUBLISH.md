# How a {{TERM_BUILD}} is made ({{PROJECT}})

One {{TERM_BUILD}} per night picks up what the {{TERM_STUDIO}}s marked ready, plus <describe any other input, e.g. the newest merged
bundle>. The {{TERM_STUDIO}}s keep iterating by day; the {{TERM_BUILD}} folds their accepted work into the product without blocking them.
<describe what the build produces and where it lands, e.g. "a packaged game in builds/<label>/">.

Cadence (local time): handover call ~{{HANDOVER}} · {{TERM_READY}} deadline {{DEADLINE}} · {{TERM_BUILD}} trigger ~{{BUILD_TIME}} ·
morning report when the {{TERM_BUILD}} agent reports. <describe a different cadence here if the project builds weekly / on demand>.

## Studio side: the {{TERM_READY}}
Each {{TERM_STUDIO}} keeps `{{HUB}}/ready/<owner>.md` current whenever something accepted is stable. Format (`templates/hub/READY_FILE.md`):
```
stamp: <YYYY-MM-DDTHH:MM>        # bump on every change; the build skips stamps it already applied (applied.json)
accepted: <ID> user <date time> "<the user's words>" (sheet <path>)   # one line per item
already live: <what is installed in the shared files already, so the build only rebuilds>
apply tonight:
  1. <ID>: python <installer> (dry run) / python <installer> --apply / revert: python <installer> --revert <stamp>
build-script changes: <edits to this round's own copies of the build scripts, if any>
check: <where to look, the expected numbers, and what "worse" looks like>
not ready: <work in progress the build must NOT take>
```
- Only user-ACCEPTED items. A {{TERM_READY}} written in the evening is never final.
- **Handover call (~{{HANDOVER}}):** the {{TERM_MANAGER}} tells every {{TERM_STUDIO}} to put EVERYTHING finished, checked and accepted into
  tonight's file by {{DEADLINE}}, including work labelled "for tomorrow". Only unchecked or unaccepted work stays "not ready".
  The {{TERM_MANAGER}} never defers finished, accepted work to the next night. No other cutoffs exist.
- **Freeze:** while `{{HUB}}/BUILD_RUNNING` exists, {{TERM_STUDIO}}s don't change shared scripts, data or anything the {{TERM_BUILD}} reads:
  <describe the shared paths>. Lab copies and their own files are fine. Stage changes for the next night instead.
- **During the {{TERM_BUILD}}** {{TERM_STUDIO}}s keep working: CPU work, analysis, lab-only data. Their queue jobs wait behind the
  {{TERM_BUILD}}'s (the {{TERM_BUILD}} owner has priority) and run in its idle phases. A job already running is never cut.

## {{TERM_MANAGER}} at the trigger (~{{BUILD_TIME}})
0. **Backup, every night (built or skipped):** <describe the backup command, e.g. a commit + push of small hand-made files>.
   Run it in the background. Never commit large files by hand; list them for the morning. One-line result in the morning report.
1. **Skip check.** Skip, and say so in the morning, if all of these hold:
   - no {{TERM_READY}} has a stamp newer than `applied.json`;
   - <describe other inputs: no newer merged bundle>;
   - nothing was installed live since the last {{TERM_BUILD}}.
   Also don't start while `BUILD_RUNNING` exists, while usage is at the halt threshold, or while a "USER HOLD" lock is held.
   In that case re-check every 30 min until <describe the latest start time>.
2. **Label.** Next round `rNN`, {{TERM_BUILD}} label <describe the naming rule>. Folder `{{HUB}}/builds/rNN/`.
3. **Brief.** Write `builds/rNN/BUILD_BRIEF.md` (template `BUILD_BRIEF.md`) from this file plus tonight's items: each {{TERM_READY}}'s apply
   list, the other inputs, the gates. Start from the previous round's brief for procedure and gates.
   Copy the {{TERM_READY}}s into `builds/rNN/ready/` so the {{TERM_BUILD}} reads a frozen copy.
4. Write `BUILD_RUNNING` (round, label, start time). Spawn the {{TERM_BUILD}} **subagent** (Agent tool, model <describe>, effort
   <describe>). A scheduled turn cannot start sessions, so the {{TERM_BUILD}} is always a subagent of the {{TERM_MANAGER}}.
5. Arm the hang watchdog (Monitor on the {{TERM_BUILD}}'s logs; the watch loop must expire on its own and be re-armed).

## The {{TERM_BUILD}} (subagent)
1. **Apply:** for each item, dry run, then `--apply`. Log every backup / revert stamp in `builds/rNN/RESUME_BUILD.md`.
2. **Build:** <describe the build steps>. Then delete `BUILD_RUNNING` as soon as the shared files are no longer read.
3. **Gates:** the standing gates plus each {{TERM_READY}}'s own checks. Judge the SHIPPED artefact, never a dev copy.
   For items whose output depends on other inputs, compare against a baseline with the same inputs (run the pre-change version on
   tonight's inputs), not against last night's {{TERM_BUILD}}.
4. **A failing item:** revert it with its revert command and rebuild from the earliest step it touches, if the night allows
   (finish by <describe>). Otherwise list it for the morning, unreverted. Never patch around a failing item.
5. **Evidence:** <describe the captures / audits> → `builds/rNN/RESULT.md` (template `BUILD_RESULT.md`).
6. **Usage:** check before each step. At the halt threshold, stop at the next safe point: finish or cleanly end the step, release the
   queue, make `RESUME_BUILD.md` complete, report "HALTED at <step>".
7. **Rules:** queue only through `resq.py`, owner `build-rNN` (priority owner). Off-screen, no console windows. Stop only own pids.
   No config changes, no merges. Temp file + `os.replace`. Keep `RESUME_BUILD.md` current. Stop at the first hang.

## Morning ({{TERM_MANAGER}}, when the {{TERM_BUILD}} agent reports)
- **LIVE:** `python {{HUB}}/board/mark_live.py <label> --round rNN <ID> ...` for every shipped card.
  Each reverted item: `python {{HUB}}/board/mark_live.py <label> --revert-to-work <ID> --reason "..."`.
- Update `applied.json` with the stamps applied.
- **Resume the {{TERM_STUDIO}}s:** tell each the {{TERM_BUILD}} is done, the shared resource is theirs again, and its own items' results and
  faults. Lab copies made from the old product are now stale: re-copy before judging.
- **One short report to the user:** where the {{TERM_BUILD}} is, what went in (per {{TERM_STUDIO}}), gates, top faults, anything reverted,
  the backup's one-line result, and one or two existing sheets.
- If an upstream input (a merge) missed the night, say so and why. A fallback decision ("build on the previous base if the merge
  isn't published by X") is written into NEXT.md the evening before.
