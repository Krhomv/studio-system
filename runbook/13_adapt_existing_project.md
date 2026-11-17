# 13 · Adapting an existing project

For a project that already has working sessions, folders, scripts and habits. The aim: put the board and the rules in place
without breaking anything that works, then move the rest over gradually. Do the interview of `12_deploy_new_project.md` first;
this page adds what is different.

## 1. Take stock (read only)

Before changing anything, list:
- **Sessions:** `mcp__ccd_session_mgmt__list_sessions` (linked and not). For each: title, working folder, what it does, model,
  whether it is running now. Which one becomes the manager?
- **Folders per subject:** where each session keeps its work, scripts, pictures and notes.
- **Work in flight:** to-do lists, issue trackers, notes with "next" sections, half-finished branches, jobs running right now.
- **Publish path:** the scripts that build or ship the product today, and what they read.
- **Shared resources:** locks, queues or "busy" flags already in use; services several sessions use.
- **Existing rules:** `CLAUDE.md` files, memory folders, rule documents. What the user already decided.

Write the inventory into `studio-hub/manager/NEXT.md` (first entry) once the hub exists, or keep it in the session until then.

## 2. Map to studios

| Existing | Becomes | Notes |
|---|---|---|
| A session that works on one subject | that subject's studio | keeps running; gets a role file and the rules |
| A subject with no session | a new studio, or parked | ask the user |
| A session that coordinates | the manager | or start a fresh manager session |
| An old session whose subject merged into another | folded (section 6) | its work moves to the new studio |

Show the map to the user with the interview's mapping table.

## 3. Folders: point first, move later

- Run `scaffold.py init` and `scaffold.py studio` as for a new project. Each studio gets `studios/<key>/` with its AGENT.md and
  NOTES.md.
- **Leave existing work folders where they are.** Scripts, logs and other sessions refer to their paths; moving them breaks
  things silently. AGENT.md's "Where things live" table points to them.
- New work goes into the studio folder from now on.
- Move an old folder only when its studio is idle, every script that names it is updated, and a backup exists. One studio at a time.
- Pictures the board must show have to be inside the project root (config `root`). If an old folder is outside, copy the card
  pictures into `studios/<key>/cards/`.

## 4. Shared resources

- If a lock already exists, put `resq.py` in front of it: set `paths.queue` and make every job go through `resq.py`.
- Old scripts that take the lock directly must switch. Until they do, they must not take it while `resq.py status` exits 3
  (someone waiting).
- Map existing "busy" markers into a `tick_local.py` check so the manager sees stale ones.
- Agree the owner names (one stable name per session) and the priority owners (the build).

## 5. Turn existing work into cards

Write the blocks into `studio-hub/data/PROPOSALS.md` (one block per task, temp file + `os.replace`), then check the board shows
no parser warnings.

| Existing item | Card |
|---|---|
| Something the user asked for, not started | `APPROVED` with the source and the user's words on `decision:` |
| Something the user asked for, in progress | `APPROVED, IN WORK` with a first progress note |
| A studio's own idea | `PROPOSED` with a picture, for the user to decide |
| Finished but not shipped, not yet seen by the user | `RESULT` with the A/B on `result:`, for the user to accept |
| Accepted but not shipped | `ACCEPTED`, then into the ready file → `HANDOFF` |
| Already shipped | not registered (or `LIVE` with the build label, if the user wants history) |
| Doubtful relevance | ask the user in the first batch; close what they drop |

`decisions.jsonl` starts empty and `relayed.cursor` at 0. Don't invent decision lines for history; the register's `decision:`
fields hold it.

## 6. Fold an old session into a studio

1. Ask the old session to write a handover (template `templates/studio/HANDOFF.md`): what is on the board, where the work stands,
   tools, the user's decisions, open questions, what it was about to do, what not to touch.
2. The new studio adopts the old session's cards. No duplicates: it edits or closes them.
3. Rename the old session ("… (handed over to <studio>)"). Archive it **only on the user's yes**.
4. A session the manager didn't start is messaged, never stopped.

## 7. Brief the running sessions

- Write the rules once (`TASKS_GUIDE.md`) and send each running session a short message with pointers: its AGENT.md, the guide,
  the board URL, its prefix and owner name, and "from <time> all new work is proposed on the board first".
- The message cap (about 10 messages to sessions per user turn) applies: stagger, or ask the user to send a one-line go.
- A studio treats a rule relayed by the manager as the manager's relay of the user's words. If the user tells it something
  different directly, the user's words win.
- Running sessions stay at the project root. That's fine: they read their AGENT.md now and after each compaction. New
  sessions start in `studios/<key>/`.

## 8. Memory and existing rules

- Existing memory belongs to the folder it was written in (usually the project root, shared by every old session). Studios that
  later run in their own folder start with an empty memory.
- Move rules that matter to every studio into `TASKS_GUIDE.md` (§1 authority, §4 evidence, §7 decisions taken), and a studio's
  own rules into its AGENT.md. Keep the memory files; don't delete them.
- Decisions the user already took go in the guide's "decided, don't re-flag" list with the user's words and date.

## 9. The switch-over

- Pick a time with the user ("from tonight's build on"). Work started before it may finish as it is; everything new goes through
  the board.
- At the switch: in-flight work is on the board as `IN WORK`, studios post progress with `note.py`, questions go to the board only.
- The first build after the switch takes only user-accepted items. Studio judgement no longer puts work into a ready file.

## 10. The first week

Watch for:
- studios still asking in their own sessions instead of the board;
- cards whose status lies (a result under IN WORK, nothing posted for hours);
- jobs on the shared resource outside `resq.py`, or untagged;
- ready files treated as final in the evening;
- old notes files that keep growing as diaries (move them to the NOTES.md shape of `11_continuity_and_budget.md`).

Fix each with a one-line rule in `TASKS_GUIDE.md` and a message to the studios, not by doing their work.
