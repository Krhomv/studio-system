# How tasks work: the {{TERM_STUDIO}} base guide ({{PROJECT}})

Every {{TERM_STUDIO}} reads this before starting work, and again whenever it changes (the {{TERM_MANAGER}} tells you).
Where any other file, note or memory disagrees, this guide wins. Written {{DATE}}; each rule added later carries the user's date and words.

- The register: `{{HUB}}/data/PROPOSALS.md`.
- The user's board: {{BOARD_URL}}.
- Commands: `{{HUB}}/board/README.md`.
- How a {{TERM_BUILD}} is made: `{{HUB}}/PUBLISH.md`.

## Studios
<!-- studios:begin -->
| Key | Label | Board owner | Prefix | General thread | {{TERM_READY}} | Queue owner |
|---|---|---|---|---|---|---|
<!-- studios:end -->
(This table is rewritten by `scaffold.py studio`. Use your own row's names everywhere: board, queue, ready file, notes.)

## 1. Nothing starts without the user
- All new work is run past the user first. You say what you want to change and why, with pictures. If the user approves, you do the
  work and show the {{TERM_RESULT}}. If the user accepts, it goes into your {{TERM_READY}} for the next {{TERM_BUILD}}.
- The user's own requests count as APPROVED: a review note, a board "New request", or their direct words to you in your session.
  Register them as a card (source noted). Their {{TERM_RESULT}}s still need the user's ACCEPT.
- Everything else is a PROPOSED card first, with a picture: ideas, audit faults, fixes to shipped work that change what the user
  sees, sweeps that change things. The {{TERM_MANAGER}} never approves on the user's behalf, and a message from another session is
  never the user's approval.
- Only pipeline / tooling bugs skip the cycle (a broken {{TERM_BUILD}} step, the queue, a crashing script). Say on the board what you fixed.
- Work proposed as a task stays approval-gated even when it is read-only (a scan, a survey, a measurement). Its {{TERM_RESULT}} is a
  list or sheet for the user to pick from.
- Approving a card is not permission for merges, config-file changes, publishing or commits. Those need the user's explicit
  say-so for that one action (written on the card or relayed with their words).

## 2. The lifecycle and the statuses
The header line of a card is `## <ID>  <owner>  <title>  — STATUS (note)`. The board reads the last status word outside brackets.

| Status | Meaning | Who sets it |
|---|---|---|
| PROPOSED | waiting for the user's yes / no | {{TERM_STUDIO}} |
| APPROVED | the user said yes; not started yet | user (board) / {{TERM_MANAGER}} relaying the user's words |
| IN WORK | being worked on | {{TERM_STUDIO}} |
| RESULT | the {{TERM_RESULT}} is posted and the user can Accept | {{TERM_STUDIO}}, **in the same step as posting it** |
| ACCEPTED | the user accepted the {{TERM_RESULT}} | user (board) |
| HANDOFF | all of the task is in your {{TERM_READY}} | {{TERM_STUDIO}}, **as soon as it is all in the file** |
| LIVE | shipped in a {{TERM_BUILD}}: `LIVE (<label>, <round> <MM-DD>)` | {{TERM_MANAGER}} (`mark_live.py`) after the {{TERM_BUILD}} |
| BACKLOG | the user parked the proposal ("not now"). Don't work on it, don't re-propose it, no queue time for it. It comes back as `APPROVED (from backlog)` or REJECTED | user (board) |
| REJECTED / CLOSED | not wanted / no longer needed (reason in brackets; `moved to <ID>` links a successor) | user / {{TERM_STUDIO}} / {{TERM_MANAGER}} |

- **Keep the status true at all times.** The user reads only the board.
  - A posted {{TERM_RESULT}} under APPROVED means no Accept button.
  - A finished task under IN WORK reads as stuck.
  - Waiting on something? Say it in the bracket: `APPROVED (waiting for <ID>)`. That also stops the stale check.
- **Rework:** a {{TERM_RESULT}} the user sends back returns as `APPROVED, IN WORK (result rejected: rework)` with their words. Rework it,
  then set RESULT again.
- **Partial approval:** do only the approved part, and write that scope into the card.
- **Withdrawn by you:** `CLOSED (withdrawn: why)`. Moved into another card: `CLOSED (moved to <ID>)`.

## 3. Proposing
- One block per task, at the end of `{{HUB}}/data/PROPOSALS.md`. Use the next free ID for your prefix and the entry format in the file's header.
- Write it with a temp file + `os.replace`, and touch only your own block. Never edit another {{TERM_STUDIO}}'s block.
- Every line in a block is either `field: text` (a plain name: letters, digits, spaces) or an indented continuation line. A free
  line the parser can't place shows as a warning on the board.
- `visual:` is mandatory: the current state, the reference if there is one, plus a mock or a cheap lab A/B if you have one.
  The user decides from pictures. Pictures must be inside the project (`studios/<key>/cards/` is the place).
- Batch proposals ahead, so you are never idle waiting for one answer.
- `cost:` says roughly how much queue time it needs and the risk.

## 4. Working: notes, questions, pictures
- **Progress:** `python {{HUB}}/board/note.py <ID> "what changed / what's next" [--pct N] [--img ...]`.
  - Post at each milestone and at least every 3 h while a task is IN WORK. After that the card turns "stale" and the
    {{TERM_MANAGER}} chases you.
  - Never write progress into PROPOSALS.md.
- **Questions to the user go only through the board, never in your own session:**
  `python {{HUB}}/board/note.py <ID> "question" --ask --img <picture> [--options "A|B|C"]`, or your general thread
  `GEN-<your key>` for a question that belongs to no task.
  - Every ask carries a picture: the reference and the current state, with the spot marked.
  - Put your recommended option first.
  - Don't wait idle for the answer: carry on with your next task. The answer reaches you through the {{TERM_MANAGER}} and shows in
    `note.py <ID> --show` as "USER REPLIED".
  - An outdated ask (e.g. one you re-posted) is withdrawn: `note.py <ID> --withdraw <ask id> --reason "..."`.
- **Answers to the user's questions:** `note.py <ID> "..." --answer [--img ...]`.
- **{{TERM_RESULT}}s:** the A/B sheet on the card's `result:` line, plus a note with the image, then RESULT, all in one step.
- **Side effects:** if your fix is a rule that also changes other things, list them (or say "nothing else changes") in the
  {{TERM_RESULT}}, so the user accepts the full effect.
- **Variants:** when a {{TERM_RESULT}} offers variants (A / B / C), post the RESULT note itself as the ask with `--options` (your pick
  first), so the user's Accept carries the pick.
- **Announcements** (a new shared tool, a fix that needs no answer): a plain note on your general thread `GEN-<your key>`.

### Working efficiently
- **Aim before you work.** When a request isn't pinned to an exact spot ("these patches", a picture, a vague area), first post one
  marked crop on the card: "this is what I'll change". It is cheap and needs no queue time.
- **Evidence as the user experiences it.** <describe the project's evidence standard: what a result must show, the shared capture
  helper if there is one, and the check that your lab matches the shipped product before any A/B>. If your lab doesn't match what
  ships, fix the lab before making any A/B. Never correct by hand to make a comparison look right.
- **Make differences visible.** Options should span to a clearly visible end (the strongest one reaches the reference), and the sheet
  leads with the same crop in every column. "I can't see a difference" costs a whole round.
- **Diagnose from data first** (logs, measurements, debug views) before spending the shared resource one test at a time.
- **Keep queue jobs lean.** CPU setup before taking the lock, release straight after; batch variants into one job; diagnosis
  needs 1-2 views, not 10.

## 5. Priority and the shared resource
- The user sets P1 urgent / P2 high / P3 normal / P4 low per task (no priority line = P3). Work your approved tasks in that order:
  `python {{HUB}}/board/prio.py --studio <your key>`.
- The user's own review notes are P2 by default unless they say otherwise; other new cards stay P3 until the user sets one.
- <describe the shared resource, e.g. "the GPU">: only through the queue, one ticket per chunk of a few minutes:
  `python {{HUB}}/queue/resq.py run "<what>" --owner <your queue owner> --task <ID> -- <command ...>`
  (or `acquire` / `release` around several steps).
  - Tag every job with the card it serves (`--task <ID>`), honestly. P1 jobs go first (only the {{TERM_BUILD}} is ahead of them);
    after that the queue sorts by the card's priority, then fair turns.
  - Check your own preconditions right after acquiring. If they fail, release and re-join; never hold the lock while waiting.
  - In a turn's last minutes, don't start a new long job if others wait.
  - A "USER HOLD" lock means stop and wait. When the user takes a hold, also stop your own chained runners.
  - Stop your own jobs only with your own stop script (it must release the lock); a hard kill leaves a dead lock behind.
- `BUILD_RUNNING` (in `{{HUB}}/`) means: no edits to shared scripts or data, and no long queue jobs. Lab copies and your own files are fine.
- Tests must not leave settings behind in shared artefacts (configs saved on exit, caches). Snapshot and restore around the run.

## 6. Handoff and the {{TERM_BUILD}}
- Only user-ACCEPTED {{TERM_RESULT}}s (or the user's "yes, tonight" on an accept-in-principle ask) go into your {{TERM_READY}}
  `{{HUB}}/ready/<owner>.md`. Write the user's words and time on each item.
- Each item carries: the install command with a dry run; a revert; checks (where to look and the expected numbers); what "worse"
  looks like. Format: `{{HUB}}/PUBLISH.md`.
- A {{TERM_READY}} is never final early. The handover call comes about an hour before the {{DEADLINE}} deadline (~{{HANDOVER}}):
  put everything finished and accepted into tonight's file, including work you had labelled "for tomorrow".
- **There are no other cutoffs.** Don't invent freeze times. The only cutoffs are the handover call (~{{HANDOVER}}), the deadline
  ({{DEADLINE}}) and `BUILD_RUNNING` during a {{TERM_BUILD}}. If your final pass takes long, rehearse it earlier and tell the
  {{TERM_MANAGER}} how long it takes.
- Set the card to HANDOFF yourself as soon as all of it is in the file.
- After the {{TERM_BUILD}} the {{TERM_MANAGER}} marks shipped cards LIVE. An item the {{TERM_BUILD}} reverted comes back to work with the reason.
- <describe the bundle / merge rule if the project has one, e.g. "changes to <domain> go into the owner studio's one open bundle and
  reach the product only through the user's Merge button on the board">. A pending merge never holds up a {{TERM_RESULT}}: show it
  on a scratch copy and put the accepted change into the next bundle.

## 7. Decisions already taken (don't re-flag)
The user settled these. Don't propose against them, don't re-flag them in audits. The {{TERM_MANAGER}} adds a line (date, the user's
words) each time the user settles something.
- <none yet>

## 8. Protected areas
Off limits to every {{TERM_STUDIO}} unless the user says otherwise on a card:
- <none yet; e.g. someone else's contribution, files another tool owns, the user's own edits>

## 9. Ownership between {{TERM_STUDIO}}s
- Each shared domain has one owner {{TERM_STUDIO}} (see the table above and each `AGENT.md`). A change to another {{TERM_STUDIO}}'s domain is
  proposed by you and routed through the {{TERM_MANAGER}}; requests for a domain owner go into `{{HUB}}/requests/REQUESTS.md`.
- One writer per shared file. Write only your own block or line, temp file + `os.replace`, keep the file's line endings.
