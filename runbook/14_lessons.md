# 14 · Lessons

Things that went wrong while this system was run on a real production, rewritten generically. Each item: what happened, then the
rule now and where it lives. Read this before changing a rule; most rules exist because of one of these.

## Authority and the board

1. **The manager approved a fault on the user's behalf.** A build audit found a defect and the manager marked the fix "approved,
   defect in the shipped set". The user hadn't approved it, and the fix's rule would have removed things the user wanted.
   → Faults and look-changing fixes go in as PROPOSED. Only tooling bugs skip the cycle. (`10_safety_rules.md`)
2. **Studios asked the user questions inside their own sessions.** The user runs the studios from the board and doesn't watch
   each session; questions waited for hours. → Questions go only through `note.py --ask` on the card or `GEN-<key>`.
3. **Asks without pictures.** The user couldn't decide from text. → Every ask carries a picture: the reference and the current
   state, the spot marked.
4. **A result was posted but the card still read APPROVED.** The board showed no Accept button. → RESULT is set in the same step
   as posting the A/B; tick flags `BOARD` when a result line sits under APPROVED or IN WORK.
5. **Three accepts came without a variant pick.** The studio didn't know which variant to ship. → A result with variants is
   posted as an ask with `--options` (your pick first); the board's Accept carries the pick.
6. **A finished task kept reading IN WORK.** It looked stuck, and the manager chased it. → Statuses stay true at all times; "waiting
   for X" goes in the bracket.
7. **A relayed rule was taken as the user's own words.** → Relays quote the user's words and time; a peer's message is never the
   user's approval; the user's direct words in a session win.

## Evidence

8. **Numbers moved, the picture didn't.** A change halved a measured value but looked identical at sheet size; the user said "I
   can't see a difference" and a round was lost. → Offer strengths up to a clearly visible end; lead the sheet with the same 1:1
   crop in every column. (`06_evidence.md`)
9. **The lab didn't match the shipped product.** Several rounds were lost because the lab rendered brighter, or a different
   colour, than what the user saw. → The evidence harness reproduces the user's view and checks the lab against the shipped
   product first; no A/B until it matches.
10. **The user's own screenshot was used as the exposure reference.** It held their momentary auto-exposure, a few tenths of a stop
    off. → Show the user's picture beside the A/B; compare against a settled capture of the product, never correct by hand.
11. **Fixes were aimed at the wrong spot.** A vague request ("these patches") was worked on before the studio knew which ones. →
    Aim before you work: post one marked crop "this is what I'll change" first.
12. **Results hid their side effects.** A rule fixed one place and changed others. → Every result lists its side effects, or says
    "nothing else changes".

## The shared resource

13. **Two one-minute renders waited two hours** behind back-to-back long jobs on a polled lock. → A ticket queue with turns, short
    jobs in the gaps. (`09_shared_resources.md`)
14. **One ticket was held for over an hour** across a dozen batches. → One ticket per few-minute chunk.
15. **A holder waited for free memory while holding the lock.** Another app filled the device, and everyone waited behind a job
    that did nothing. → Never hold the lock while waiting; check preconditions after acquiring; release and re-join.
16. **A gate checked before joining never passed** while another studio rendered, so the waiter never got a ticket. → Join first,
    check after acquiring.
17. **A runner spun a CPU core for over an hour holding the lock**, with no engine running. The "frozen" check missed it because its
    CPU wasn't flat. → If a project adds a kill watchdog, it needs a "spinning" rule too. (`09`, not shipped)
18. **A hard kill left the lock held by a dead pid**, and a leftover "busy" marker blocked every later job. → Stop scripts with
    cleanup; dead holders' locks and their markers are removed.
19. **One owner won every rotation** because ties broke on the oldest ticket file. → Least-recently-served owner first.
20. **Owners re-took the lock at 19.5 of 20 minutes** while others had waited an hour. → The turn tail: long tickets rank fairly in
    a turn's last minutes.
21. **The user's apps filled the device's memory and the queue stalled.** → tick flags `GATE`; tell the user which apps hold how
    much; never raise the gate.
22. **An idle model server kept its model loaded** and shut the gate for everyone. → Free an idle shared service (only when its
    own queue is empty).
23. **The user asked for a break and a chained runner started its next job anyway**, inside its own turn. → On a hold, studios
    stop their chained runners at once; ask the holder to drop queued tickets first.
24. **After a queue edit, old waiters kept the old rules.** → Ask studios to re-queue still-waiting jobs after any queue change.
25. **Whether a queue feature was worth it was argued, not measured.** → Log every take and release; measure, then let the user
    decide.

## Build and publish

26. **Evening ready files were treated as final**, and finished, approved work was held for a whole day. → The handover call about
    an hour before the deadline; everything finished and accepted goes in. (`08_build_and_publish.md`)
27. **A studio invented a cutoff** ("freeze at 23:00"). → The only cutoffs are the handover call, the deadline and the build freeze.
28. **A build check blamed the wrong item.** A new base the same night shifted generated output by several percent, and the item's
    check compared against last night's build. → Compare against a baseline with the same inputs.
29. **A build shipped a stale copy of its main content**, and the checks passed because they ran on the dev copy. → Every gate
    judges the shipped artefact; the copy step checks counts and fails loudly.
30. **A test changed quality settings at runtime and the product saved them on quit.** Later runs, gates and the user's own
    sessions ran degraded for an hour. → Reset before quitting, snapshot and restore saved settings, check after.
31. **A pending merge held up a result** ("why are we waiting for a merge to show the result?"). → Build the fix on a scratch copy,
    post the A/B, put the accepted change into the next bundle.
32. **A merge was rolled back because checks failed on the user's own hand-made work.** → The user's manual work is truth at merge;
    list the findings instead of altering it.
33. **Lab copies went stale after a build** (parts missing, floating pieces). → Rebase lab copies on the new build before judging.

## Process, files and tools

34. **Console windows kept popping up** on the user's screen. → `CREATE_NO_WINDOW`, never `DETACHED_PROCESS`; off-screen renders.
35. **`sed -i` turned a shared CRLF file into LF and rewrote another session's line.** → Edit tool or binary-mode Python, matched
    on your own line only.
36. **A user-facing tool was restarted while the user had unsaved edits.** → Ask on the board first; page-only changes need no
    restart; batch server changes.
37. **Stopping a background task left its chain and engine running.** → Long chains check a stop file between stages; confirm
    processes are gone before restarting.
38. **A job hung for an hour unnoticed**; the user found out because the machine went quiet. → Hang watchdogs on logs and engine
    CPU for unattended work.
39. **Watchdog loops piled up** (dozens of orphans) because a Monitor timeout doesn't kill the loop. → Loops expire on their own.

## Sessions and continuity

40. **Night jobs failed to start sessions from a cron turn.** → Night work runs as manager subagents; sessions start only from the
    user's turn chain. (`11_continuity_and_budget.md`)
41. **A fan-out stopped after ten messages.** → Briefs in a shared file, short pointers, staggered sends.
42. **The routine silently stopped** when crons expired after 7 days or died with a restarted session. → Cron ids and dates in
    NEXT.md; re-create on restart and before day 7.
43. **Studio notes grew into 250 KB diaries** that nobody could use after a compaction. → NOTES.md is lasting knowledge with an
    open-cards head; progress goes on the board.
44. **The manager worked in long foreground turns** and the user's messages waited. → Dispatch, keep turns short, stay free.
45. **Sessions kept spending during an account switch.** → The usage halt protocol with a HALT to everyone and a full NEXT.md entry.
46. **A slow day had no clear cause.** The manager measured where the time went and proposed four changes; the user approved them
    and the time per variant on the shared resource dropped about sevenfold. → When work is slow, measure and propose process
    improvements; the user decides.
47. **Desktop banners for every finished task were noise.** → Alerts only when the board needs the user (new proposal, result,
    question, merge-ready bundle).
48. **A parked studio kept being nudged to propose.** → A studio the user parked is left alone until the user un-parks it.
