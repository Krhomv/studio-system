# Relay message formats (reference for the manager)

Every relay names the card, quotes the user's words exactly (or says "no comment"), gives the time from the decision line, and
states the card's status now. The recipient can act on it without opening the board. One message per {{TERM_STUDIO}} per batch: group
several lines for the same {{TERM_STUDIO}}. Never upgrade the user's words ("looks fine" is not "ship it"). After relaying, run
`python {{HUB}}/board/tick.py --relayed`.

`<HH:MM>` is the decision's `ts`; `<words>` is its `comment`.

| Action | Message |
|---|---|
| approve | `<ID> APPROVED by the user (board, <HH:MM>): "<words>". Now APPROVED, priority P<n>. Start in priority order (prio.py).` |
| reject | `<ID> REJECTED by the user (board, <HH:MM>): "<words>". Don't re-propose it.` |
| backlog | `<ID> moved to the BACKLOG by the user (board, <HH:MM>): "not now". Don't work on it or re-propose it; no queue time.` |
| approve_backlog | `<ID> APPROVED from the backlog by the user (board, <HH:MM>): "<words>".` |
| reject_backlog | `<ID> REJECTED from the backlog by the user (board, <HH:MM>): "<words>".` |
| accept | `<ID> result ACCEPTED by the user (board, <HH:MM>): "<words>"<; pick: <option>>. Put it in your {{TERM_READY}} (with these words) and set HANDOFF once it is all in.` |
| reject_result | `<ID> result sent back by the user (board, <HH:MM>): "<words>". Now APPROVED, IN WORK (rework). Rework, then set RESULT again.` |
| close | `<ID> CLOSED by the user (board, <HH:MM>): "<reason>". Stop any work on it.` |
| reopen | `<ID> REOPENED by the user (board, <HH:MM>). Now APPROVED (reopened by user).` |
| priority | `<ID> priority <from> -> <to> (user, board, <HH:MM>). Re-check your order (prio.py --studio <key>).` |
| new_request | `New user request <ID> "<title>" (board, <HH:MM>), APPROVED, P<n>: "<what>"<; picture <path>>. Register nothing else: the card exists.` |
| question | `The user asks on <ID> (board, <HH:MM>): "<words>". Answer with note.py <ID> "..." --answer [--img ...].` |
| answer | `The user answered your ask on <ID> (board, <HH:MM>): "<words>" (your ask: "<first 80 chars>"). Act on it.` |
| merge | `The user requested the merge of bundle <name> (board, <HH:MM>): "<words>". This is the user's say-so for this one merge. Merge, update bundle.json, open a new bundle for the next changes, note each card carried.` |
| hold | `The user holds the shared resource (board, <HH:MM>). Stop your chained runners now; a running job may finish and release. Queue nothing long until "release".` |
| release | `The user released the shared resource (board, <HH:MM>). The queue runs again; re-queue what you paused.` |
| revert (after a build) | `<ID> was reverted in <label>: <reason>. Now APPROVED, IN WORK. Fix it and post a new result.` |

Messages the {{TERM_MANAGER}} sends on its own:

| When | Message |
|---|---|
| halt | `HALT (usage <N> %, the user's account switch): start nothing new. Don't launch new queue jobs; a job already running may finish and release the queue on its own. Write your resume notes (NOTES / HANDOFF / RESUME_BUILD.md) now, then end your turn.` |
| resume | `Resume: the halt is lifted (<reason>). Read your NOTES.md / HANDOFF.md and continue with your approved cards in priority order.` |
| handover call | see `manager/prompts/handover_call.txt` |
| build done | `<label> (<round>) is built. Your items: <ID> LIVE, <ID> reverted (<why>). Faults for you: <list with pictures>. The shared resource is yours again. Re-copy any lab taken from the old product before judging.` |
| idle nudge | `You've been idle <N> min with no ticket. Your approved cards: <IDs in priority order>. If none are left, propose a batch with pictures.` |
| stale card | `<ID> has had no note for <N> h. Post a status note, or set it to "waiting for X" / close it if it is overtaken.` |
| new rule | `New rule from the user (<date> "<words>"): TASKS_GUIDE §<n> updated. Read it now.` |
