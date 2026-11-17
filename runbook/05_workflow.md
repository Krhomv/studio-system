# 05. The workflow, end to end

The user's rule, in one sentence: studios tell the user what they want to change, with pictures; if the user approves,
they do the work and show the result; if the user accepts, it is scheduled for the next build.

## The steps

| # | Step | Who | How | Status after |
|---|---|---|---|---|
| 1 | Propose | studio | append a block to the register (temp + `os.replace`), picture on `visual:`; tell the manager in one line | PROPOSED |
| 2 | Present | manager | batch new proposals for the user with their pictures (when a few are up, or one is urgent) | PROPOSED |
| 3 | Decide | user | board: Approve / Reject / Backlog, optional comment and priority | APPROVED / REJECTED / BACKLOG |
| 4 | Relay | manager | message the studio quoting the user's words and time; `tick.py --relayed` | unchanged |
| 5 | Aim | studio | if the card is not pinned to an exact spot: one marked picture "this is what I'll change" as a note | APPROVED |
| 6 | Work | studio | set IN WORK; work in its lab; notes at milestones and at least every `stale_hours` | IN WORK |
| 7 | Ask (when needed) | studio | `note.py <ID> "..." --ask --img ... [--options ...]`; carries on with other work | IN WORK |
| 8 | Answer | user | board: answer the ask (one click on an option or free text) | unchanged |
| 9 | Result | studio | evidence picture on `result:`, a note with the picture, status RESULT, all in one step | RESULT |
| 10 | Judge | user | board: Accept (with a pick if variants) or Rework (with words) | ACCEPTED / back to IN WORK |
| 11 | Hand off | studio | write the item into `ready/<owner>.md` with install, dry run, revert, checks; set HANDOFF with the stamp | HANDOFF |
| 12 | Build | manager + build agent | handover call, freeze, build, gates (`08_build_and_publish.md`) | HANDOFF |
| 13 | Live | manager | `mark_live.py <label> --round <R> <IDs>`; reverted items back to work with the reason | LIVE |
| 14 | Report | manager | one short morning report to the user; each studio gets its own items' results | LIVE |

## What counts as approved

| Source | Enters as | Result needs accept? |
|---|---|---|
| A studio's idea, an audit finding, a fix that changes how shipped work looks | PROPOSED | yes |
| The user's board "New request" | APPROVED (user request, web tool) | yes |
| The user's direct words in a studio's or the manager's session | APPROVED, source and words on `decision:` | yes |
| The user's own review pass (notes taken while using the product) | APPROVED, default priority P2, source on `decision:` | yes |
| A pipeline or tooling bug (broken build step, stuck queue, crashing script, stale copy of the product) | no card needed; say on the board what was fixed (a note on `GEN-<key>`) | no |

Read-only work (a survey, an audit, a measurement) still needs approval when it is proposed as a card. Its result is
a list or sheet the user picks from.

## Review passes become cards

When the user reviews the product and leaves notes (screenshots with marks, a list of issues):
1. The manager copies `templates/hub/REVIEW_NOTES.md` to `studio-hub/reviews/REVIEW_<YYYYMMDD>.md` and lists each note:
   the user's words, the picture, the spot.
2. Each note becomes an APPROVED card for the studio that owns it, priority P2 unless the user set one, with
   `decision: user review <date> (approved by the workflow rule)` and the picture on `visual:`.
3. A note that spans two studios becomes one card per studio, each saying `see AUD-09` for the other part.
4. The manager tells each studio its new cards in one message.

## Rework

The user presses Rework, optionally with words. The card becomes `APPROVED, IN WORK (result rejected: rework)`. The
manager relays the words. The studio reworks, keeps the old `result:` line until the new evidence replaces it, and sets
RESULT again. Common reasons: "I can't see a difference" (go further: `06_evidence.md`), "wrong spot", "side effect".

## Variants and picks

A result with options A / B / C is posted as an ask with `--options`, the studio's pick first. The user's Accept carries
the pick ("Accept: B"). The studio ships only the picked variant. Never ship a variant the user didn't pick.

## Partial approval

The user approves part of a card ("yes to A, skip B"). The studio does only the approved part and writes the scope into
the card: `APPROVED, IN WORK (A + C only, user 20:49 "skip B")`.

## Side effects

If a fix is a rule that changes other things too, the result lists them, or says "nothing else changes". Why: the user
accepts the full effect, not just the spot in the picture.

## Accept in principle

When an item needs a final pass that can only happen close to the deadline (for example re-placing hand edits on the
latest data), the studio posts the result early and asks for an accept in principle ("yes, tonight, after the final
pass"). The final pass then runs at the handover; the studio posts the final picture on the card before the deadline.

## Waiting on something

A card blocked on another card, a merge or the user says so in its bracket: `APPROVED (waiting for LVL-02)`. It is not
stale and the tick won't chase it. A pending merge never blocks a RESULT: build the change on a scratch copy, post the
evidence for accept, and put the accepted change into the next bundle after the merge.

## Closing and moving

- No longer needed (superseded, its premise gone): CLOSED with the reason. A studio may close its own card; the manager
  closes cards overtaken by events and asks the user only when relevance is unclear.
- Withdrawn by the studio before approval: `CLOSED (withdrawn: why)`.
- Moved to another studio or merged into another card: `CLOSED (moved to LVL-07)`; the new card says `was AUD-03`.

## Reverted by the build

A shipped item that fails its gate or makes its checks worse is reverted by the build agent with the item's own revert
command. The manager then runs `mark_live.py <label> --revert-to-work <ID> --reason "<what failed>"`. The card returns
to `APPROVED, IN WORK (reverted in <label>: <why>)`; the studio fixes it and sets RESULT again (a new accept is needed
if the look changes).

## Things the user already decided

`TASKS_GUIDE.md` has a list "Decisions already taken". Each line: what was decided, the user's words, the date, the
card. Studios read it before proposing and never re-flag those things. The manager adds a line whenever the user
settles a recurring question, and whenever the user rejects something a studio might propose again.

## Example: one card's history

```
## AUD-04  audio-studio  Wind loop clicks at the loop point  — LIVE (v041a, r12 03-15)
what:    remove the click where the wind ambience loops.
why:     audible tick in quiet areas.
visual:  studios/audio/cards/AUD-04_proposal.png (waveform at the loop point, marked)
scope:   3 wind loops; crossfade rule in the loop exporter.
cost:    CPU only; low risk.
decision: user, 2026-03-14 10:02, "Approve." (web tool)
priority: P2 (user, 2026-03-14 10:03, web tool)
result:  studios/audio/cards/AUD-04_result.png (before | 40 ms | 80 ms crossfade, spectrograms + clips)
accept:  user, 2026-03-14 16:40, "Accept. pick: 80 ms" (web tool)
handoff: live in v041a (r12, 2026-03-15 07:10, mark_live)
```
Progress thread (from `note.py AUD-04 --show`), oldest first:
```
10:31 audio-studio: aim: these three loop points (picture)
11:50 audio-studio 40%: rule in the exporter; loop 1 clean
13:05 audio-studio ASKS USER: keep the gust layer under the crossfade? (picture) [keep it | drop it]
13:40 USER REPLIED: keep it
15:12 audio-studio ASKS USER (the RESULT): before | 40 ms | 80 ms, all three loops (picture) [80 ms | 40 ms]
16:40 user: "Accept: 80 ms" (answer + accept in one click)
17:05 audio-studio: in ready/audio-studio.md item 2, stamp 17:05 -> HANDOFF
07:10 build: live in v041a (r12)
```
