# 03. Studio lifecycle: create, run, hand over, park, fold, retire

## When to create a studio

A subject deserves its own studio when it has its own stream of work, its own tools or lab, and changes the user wants
to judge separately. Examples: art, audio, levels, lighting, performance, packaging, marketing.
A one-off job is not a studio: it is a subagent of the manager or of an existing studio.

The user decides that a studio exists. The manager proposes one when a subject keeps coming up and nobody owns it.

## Create: the checklist

Decide these with the user first:

| Item | Example | Where it goes |
|---|---|---|
| key | `audio` | folder, GEN thread, filters |
| prefix | `AUD` | card IDs |
| owner name | `audio-studio` | card headers, ready file, queue |
| label | `Audio` | board |
| icon, colour | `music`, `#6fc3c9` | board (`04_task_board.md` lists the icon names) |
| ships into the build? | yes / no | `ready: true/false`; a planning-only studio has no ready file |
| queue owner | `audio-studio` | `resq.py --owner` |
| role in one paragraph | "owns all sound: ambience, effects, mix; not music licensing" | `AGENT.md`, brief |
| domain it owns, what it may not touch | "owns the mix bus; never edits level files" | `AGENT.md`, `TASKS_GUIDE.md` domains list |
| model and effort | strongest model, high | `AGENT.md`, start_session |
| first deliverable | state audit + 3-6 proposals | brief |

Then:

1. **Register it.** From the project root:
   `python studio-hub/board/scaffold.py studio audio --prefix AUD --label "Audio" --owner audio-studio --icon music --color "#6fc3c9"`
   (add `--no-ready` for a planning-only studio). This:
   - adds the studio to `board.config.json` (studio list, prefix, icon, colour, queue owner);
   - creates `studios/audio/` from `templates/studio/` (`CLAUDE.md`, `AGENT.md`, `NOTES.md`, `BRIEF.md`) and the empty
     sub-folders `cards/ lab/ tools/ staged/ backup/ logs/`;
   - rewrites the studio list in `TASKS_GUIDE.md` (between `<!-- studios:begin -->` and `<!-- studios:end -->`).
2. **Fill the role.** Edit `studios/audio/AGENT.md`: replace every `<describe ...>` with the user's answers (role,
   domain, off-limits, tools, evidence it must show, first deliverable).
3. **Restart the board** so it shows the new studio: `stop.py` then `start.py`. Only when the user is not mid-action on
   the board (`10_safety_rules.md`, "Servers"). A restart loses nothing on disk; it can lose a half-typed comment.
4. **Start the session.** The manager calls `start_session` with:
   - the brief from `studios/audio/BRIEF.md` (filled), as the prompt;
   - working folder `studios/audio/` (so `CLAUDE.md` and `AGENT.md` load automatically), no worktree;
   - the model and effort from the checklist;
   - initiation "user_asked" only in the user's own turn (or the side-session event right after it). A cron turn or a
     turn started by another session's message cannot start sessions; there, propose the start as a card the user clicks
     (`11_continuity_and_budget.md`, "App limits").
5. **Wire it into the routine.** Add the studio to the handover call prompt if it ships into the build
   (`templates/manager/prompts/handover_call.txt`), and to the build trigger's list of ready files. Note the new studio
   and its session id in `manager/NEXT.md`.
6. **First deliverable.** The brief asks for: a state note on `GEN-<key>` with a picture (what exists, what is wrong,
   what could improve), then 3-6 PROPOSED cards with pictures, ranked by gain against cost. The studio tells the manager
   in one line when they are up. The manager batches them for the user.

## The brief

`templates/studio/BRIEF.md` is the start prompt. It says, in order:
- who you are (one paragraph), owner name, prefix, folder;
- read first: `TASKS_GUIDE.md`, your `AGENT.md`, `PUBLISH.md`, the top of `manager/NEXT.md`, the queue's README;
- your job and your first deliverable;
- the hard rules that matter most for this studio (nothing starts without approval; asks only on the board; the queue;
  the freeze; files you may not touch; no commits or merges);
- how to reach the manager (SendMessage, for cross-studio matters only).

Keep the brief short: everything lasting lives in `AGENT.md` and `TASKS_GUIDE.md`, which survive compaction; the
brief does not.

## AGENT.md and NOTES.md

| File | Holds | Changes |
|---|---|---|
| `AGENT.md` | the role: subject, domain, off-limits, tools, evidence standard, model / effort, how to report | rarely; when the user changes the role |
| `NOTES.md` | lasting knowledge: a "current state" section at the top, where things live, scripts, method, lessons, open cards (one line each) | at every milestone |
| board progress notes | what changed, what's next, per card | at every milestone and at least every `stale_hours` |
| `HANDOFF.md` | a map for the next session: what is where, what is mid-way, decisions in force, open questions | only at a hand-over |

`NOTES.md` is not a diary. Why: diaries grow to hundreds of kilobytes, a resumed session can't find the current state
in them, and the user's view of progress is the board anyway. Keep the top section current; move old log entries to
`logs/notes_archive_<YYYYMM>.md` when the file passes ~40 KB.

## Run: a studio's daily duties

- At session start and after every compaction: read `AGENT.md` (auto-loaded when running in its folder), the top of
  `NOTES.md`, `prio.py --studio <key>`, `note.py <ID> --show` for the cards in work.
- Work the highest-priority APPROVED card. Keep a stock of proposals ahead.
- Note on the board at each milestone and at least every `stale_hours` (default 3 h) while a card is IN WORK.
- Write `NOTES.md` at each milestone.
- Keep the ready file current; answer the handover call.
- Check usage at the start of each turn; at the halt threshold, stop at the next safe point (`11_continuity_and_budget.md`).

## Hand over to a new session

When a session gets long, crashes, or moves to another account:
1. The old session writes `studios/<key>/HANDOFF.md` from `templates/studio/HANDOFF.md`: where things are, what is
   mid-way (with resume commands), decisions in force, open asks, what it was about to do next.
2. It ends its turn. It stops only its own processes; a running queue job may finish and release by itself.
3. The new session starts in the same folder, reads `AGENT.md`, `HANDOFF.md`, `NOTES.md`, and carries on.
   Nothing on the board changes: the cards belong to the owner name, not to a session.
4. The manager notes the new session id in `NEXT.md`.

## Park

The user may park a studio ("not now"). Its cards stay; its proposals go to BACKLOG. The manager notes "parked by the
user" in `NEXT.md` and the tick does not nudge it to propose while it is idle. Only the user unparks it.

## Fold one session or studio into another

Example: an older session that already did marketing work becomes the new marketing studio, or two studios merge.
1. The old session writes a `HANDOFF.md` into the target studio's folder: map of its files (they may stay where they
   are), cards it posted, user decisions in force, open questions, next steps.
2. The new (or target) studio adopts the old cards: same IDs if the prefix stays; otherwise CLOSED `(moved to AUD-07)`
   on the old card and a new card that says `was MKT-03` (the board links both).
3. The old session is renamed ("... (handed over to <studio>)") and stops. It is archived only on the user's yes.
   If the manager did not start that session, it only messages it; it never stops it.
4. Update `board.config.json` (owner, prefix), the handover prompt and `NEXT.md`.

## Retire

1. The user agrees. Every open card gets a final state: CLOSED with a reason, moved to another studio, or BACKLOG.
2. The ready file is removed after the last build that took it.
3. The studio is removed from `board.config.json` (its LIVE cards still show; their owner stays in the header) and from
   the handover and build prompts.
4. The folder stays (it holds the installers and backups of shipped work). Add a line at the top of `NOTES.md`:
   `RETIRED <date>: <why>; <who owns the domain now>`.
5. The session is archived on the user's yes.
