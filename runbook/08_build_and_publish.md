# 08 · Build and publish

How accepted work gets from a studio's lab into the product the user actually uses, and how the board learns that it shipped.
Default terms: **build** (one publish run), **round** (`r01`, `r02`, ...), **label** (the build's name), **ready file** (a studio's
list of what goes into the next build), **LIVE** (shipped). Each project renames these in `board.config.json` → `terms` and in
`studio-hub/PUBLISH.md`.

The procedure for one project lives in `studio-hub/PUBLISH.md` (template: `templates/hub/PUBLISH.md`). This page explains the
parts every project shares.

## The rhythm (default: one build per night)

| When (config `schedule`) | Who | What |
|---|---|---|
| All day | studios | Work approved cards in labs and copies. Post results. Keep the ready file current as items are accepted. |
| `handover` (e.g. 01:45) | manager | Handover call: every studio puts everything finished, checked and accepted into tonight's ready file. |
| `deadline` (e.g. 02:45) | studios | Ready files final. The manager notes each stamp in `NEXT.md`. |
| `build` (e.g. 03:03) | manager → build subagent | Backup, skip check, brief, freeze, build, gates. |
| Morning | manager | Mark LIVE, send each studio its results, resume the studios, one short report to the user. |

Other cadences are fine (see "Projects without a nightly build" below). Pick them in the interview (`12_deploy_new_project.md`).

## Ready files: `studio-hub/ready/<owner>.md`

Template: `templates/hub/READY_FILE.md`. One file per studio that ships into the build (`"ready": true` in its config entry).

Each file carries:
- `stamp:` the time of the last change. **Bump it on every change.** The build skips files whose stamp it already applied
  (`studio-hub/applied.json`).
- One block per item, and for each item:
  - the card ID and the user's acceptance, **with their words and time** (`accepted: user 11-17 20:02 "Accept. pick: S"`);
  - the install command **with a dry run**, then the real run;
  - the **revert** command (byte for byte, with the backup stamp it creates);
  - **checks**: which views, spots or numbers prove it, and the expected values;
  - **what "worse" looks like**, so the build agent can tell a failure without asking.
- `already live:` anything installed into shared data already, so the build only rebuilds.
- `not ready:` work in progress the build must NOT take.

Rules:
- Only **user-ACCEPTED** results go in. The one exception is the user's explicit "yes, tonight" on an accept-in-principle ask
  (for an item whose final pass can only run late). A studio's own judgement never puts an item in.
- Items are **commands, not instructions**. An installer with dry run / apply / revert and its own backups. The build agent
  should never have to interpret prose.
- As soon as every part of a card is in the ready file, the studio sets the card to `HANDOFF` (`handoff:` = the stamp).
- A ready file is **never final early**. A file written at 17:00 is a draft until the handover call.

## The handover call

About an hour before the deadline the manager messages every studio that ships (prompt: `templates/manager/prompts/handover_call.txt`):
- Put **everything** finished, checked and accepted into tonight's file, including work labelled "for tomorrow".
- Only unchecked or unaccepted work stays under `not ready`.
- Reply in one line with what is in.
- Don't start long jobs on the shared resource that would still run when the build starts, unless they are short.

There are **no other cutoffs**. Studios don't invent freezes ("freeze at 23:00"). The only cutoffs are the handover call, the
deadline and the freeze marker during the build. "Staged for the night after" is not a reason to wait: anything checked and
revertable by the deadline goes in tonight. A studio whose final pass is long rehearses it earlier and tells the manager how long
it takes, so the manager can give it priority on the shared resource at the call.

## The freeze: `studio-hub/BUILD_RUNNING`

While this file exists (config `paths.build_marker`):
- No edits to shared scripts, shared data or anything the build reads. Stage the change for the next build instead.
- Lab work, own copies and CPU work continue. Studios don't stop for the build.
- Shared-resource tickets queue behind the build (build owners have priority in `resq.py`). A studio job already running is
  never cut.
- Don't trust lab captures that read shared data mid-build: the build may be rewriting it.
- The manager's tick skips its routine nudges, except a stuck holder.

The build agent writes the marker first and removes it once the product is built (before the long checks, if the project
allows it). The board shows it in the resource panel.

## The trigger (manager, at `schedule.build`)

Prompt: `templates/manager/prompts/build_trigger.txt`. Steps:

0. **Backup, every night, built or skipped.** Run the project's backup (e.g. a git commit + push of the day's small hand-made
   files) in the background. Never commit large files by hand; list them for the morning.
1. **Skip check.** Skip the build, and say so in the morning, when all of these hold:
   - no ready file has a new stamp since `applied.json`;
   - no merged bundle is newer than the last build's base;
   - nothing was installed live since the last build.
   Also don't start while a build runs, while the user holds the shared resource, or at the usage halt line. Re-check every
   30 min until a cutoff time set in PUBLISH.md.
2. **Label.** Next round `rNN`; the label scheme is in PUBLISH.md (e.g. base version + letter).
3. **Brief.** Write `studio-hub/builds/<round>/BUILD_BRIEF.md` (template `templates/hub/BUILD_BRIEF.md`) from PUBLISH.md, the
   ready files, the bundle state and the "FOR THE BUILD BRIEF" notes in `manager/NEXT.md`. Copy every ready file into
   `builds/<round>/ready/` so the build reads a fixed copy.
4. **Freeze and start.** Write `BUILD_RUNNING` (round, label, start time). Spawn the build as a **manager subagent**: a cron
   turn cannot start sessions (see `11_continuity_and_budget.md`). Arm a hang watchdog Monitor on the build's logs.

## The build agent's rules

- Dry-run each ready item, then apply it. Log every backup or revert stamp in `builds/<round>/RESUME_BUILD.md`
  (template `templates/hub/RESUME_BUILD.md`). Keep that file current after each step, so a stop or a quota halt resumes cleanly.
- Use the shared resource only through `resq.py`, with a priority owner name (`build-<round>`; config
  `queue.priority_owners`).
- **Gates:** the project's standard gates plus each ready file's own checks.
- **A failing item is reverted, never patched around.** Run its revert command and rebuild from the earliest step it touches,
  if the time allows (a cutoff in PUBLISH.md). Otherwise leave it in, unreverted, and list it for the morning.
- **Compare against a baseline with the same inputs.** When the base changed the same night (a merged bundle, another item),
  outputs shift by several percent. A check against last night's build then blames the wrong item. Run the pre-change step on
  the new base, or set tolerances that allow the night's other changes.
- **Judge the shipped artefact**, never a dev copy. If the publish step copies or packages something, check that the copy is
  complete (counts, hashes). A check made in the editor or workspace does not count as shipped.
- Tests must not leave settings behind in the shipped product (see `10_safety_rules.md`).
- Off-screen, no console windows, stop only own pids, no config or bundle changes, temp file + `os.replace`.
- Check usage before each step; at the halt line, stop at the next safe point with RESUME_BUILD.md complete.
- Stop at the first hang and report; the watchdog Monitor tells the manager.
- Write `builds/<round>/RESULT.md` (template `templates/hub/BUILD_RESULT.md`): what went in per studio, gates, scores, top
  faults, anything reverted.

## The bundle (an integration branch, optional)

Some changes are too large for a ready file: a model, a schema, a content pack. One studio owns them and keeps **one open
bundle** at a time, described in `studio-hub/data/bundle.json` (config `panels.bundle`). The board shows it with a merge button.
- The bundle owner merges **only** on the user's button (decision action `merge`, relayed by the manager as "user requested a
  merge of <name> (board, <time>)") or the user's own words. That is the say-so for **that one merge**. Then it opens a new bundle.
- The build never takes an unmerged bundle.
- A pending merge never holds up a RESULT. Build the fix on a scratch copy, post the A/B for accept, and put the accepted change
  into the next bundle after the merge.
- The user's own hand-made work in a bundle is **truth**. Don't alter it to satisfy a check; list the check's findings for the user.
- If the build waits on a merge that isn't published by a set time, build on the previous base and say why in the morning.

## After the build (manager)

1. **Mark LIVE:** `python studio-hub/board/mark_live.py <label> --round <R> <ID> [<ID> ...]` for every card that shipped
   (ACCEPTED or HANDOFF). The board's Live section groups them by build.
2. **Reverted items** go back to work with the reason:
   `python studio-hub/board/mark_live.py <label> --revert-to-work <ID> --reason "gate X failed: ..."`.
3. **Record the applied stamps** in `studio-hub/applied.json`.
4. **Resume the studios:** tell each one the build is done, the shared resource is theirs again, and its own items' results
   and faults. Any studio idle with work left gets a clear "resume" with a pointer to its notes.
5. **Morning report to the user,** short: the build path, what went in (per studio, plus the bundle), gates, scores, top
   faults, anything reverted, the backup's one-line result, and one or two sheets
   (prompt: `templates/manager/prompts/morning_report.txt`).
6. **Lab copies may now be stale.** Studios that copy shared data into a lab rebase their copies on the new build before
   judging anything.

## Projects without a nightly build

| Cadence | How it changes the flow |
|---|---|
| On demand | Same steps; the user (or the manager, when N accepted items wait) triggers the build. No handover call; a short "ready files now" call instead. |
| Weekly / per milestone | Handover call and deadline move to the release day. Ready files collect accepted items over the week. |
| Continuous (no build) | The studio installs each accepted item itself, with backup and revert, outside any freeze. Disable `HANDOFF` in config; mark LIVE with a date label (`mark_live.py 2026-11-18 <ID>`). |
| Nothing ships (planning, research) | Disable `HANDOFF` and `LIVE` (`"enabled": false`). ACCEPTED is the end of a card. Such studios keep no ready file (`"ready": false`). |

Whatever the cadence, keep three things: only accepted work ships, every shipped item has a revert, and the board says LIVE
only after the shipped artefact was checked.
