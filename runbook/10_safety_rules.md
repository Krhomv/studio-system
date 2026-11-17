# 10 · Safety rules

Many sessions write into one project at the same time while the user works on the same machine. These rules keep them from
breaking each other's files, the user's tools and the user's trust. They apply to the manager, every studio and every subagent.
`TASKS_GUIDE.md` repeats the short form for studios.

## Files

| Rule | Why / how |
|---|---|
| **One writer per shared file.** | Each shared file has one owner. Others send a request (message, `REQUESTS.md`) instead of editing it. When parallel agents must touch shared tables, give each one its own file or a patch list. |
| **Touch only your own block or line.** | In shared registers (`PROPOSALS.md`, logs), edit your own card only. Match on your own ID; never an unanchored pattern that can hit another line. |
| **Temp file + `os.replace`.** | Write the whole new file next to the old one, then replace it in one step. A reader never sees half a file. On Windows, retry `os.replace` a few times on `PermissionError` (a reader may hold the file). |
| **Keep line endings and encoding.** | Shared docs may be CRLF or LF, with or without a BOM. Keep what is there. The board does this itself. |
| **No `sed -i` on shared docs from Git Bash.** | It silently converts a CRLF file to LF. Use the Edit tool, or Python in binary mode with a match on your own line. Append to a CRLF file with CRLF. |
| **Back up before editing a tool or shared script.** | Copy to `<file>.pre_<what>_<MMDD>` (e.g. `server.py.pre_backlog_1117`). The backups also document when features arrived. |
| **Logs are append-only.** | `decisions.jsonl`, `progress/<ID>.jsonl`, `events.log`: one JSON line per event, never rewritten. |
| **Progress never goes into the register.** | Notes go through `note.py`; `PROPOSALS.md` holds only the card's fields. |
| **Respect the freeze.** | While `BUILD_RUNNING` exists, no edits to shared scripts or data the build reads (`08_build_and_publish.md`). |
| **Keep your files in your folder.** | A studio's pictures, labs, tools, staged installers and backups live under `studios/<key>/`. Pictures for the board must be inside the project root, or the board won't show them. |

## Processes

- **Stop only your own processes.** Never kill another session's pid. Message its owner with the evidence (pid, log tail) and
  let it stop its own. A watchdog the project runs is the only exception (`09_shared_resources.md`).
- **Give every long runner a stop path.** A stop script that kills your own pid tree, removes your markers and releases the
  queue. A hard kill runs no `finally` and leaves the shared lock held by a dead pid.
- **Long chains check a stop file between stages.** Stopping the wrapper task does not stop its children: a shell chain and the
  engine it launched keep running. Never restart a chain until its processes are confirmed gone.
- **No console windows.** The user works on the same screen. Spawn background processes with `CREATE_NO_WINDOW` (0x08000000),
  never `DETACHED_PROCESS` (every console child then opens its own window). Run long jobs in the Bash tool's background mode.
  Don't call `cmd //c` or `powershell` from Git Bash; use the PowerShell tool.
- **Render off-screen.** Automated engine or app runs use off-screen / unattended flags, or open away from the main screen.
- **Use the queue for the scarce resource, always.** Never take the lock directly (`09_shared_resources.md`).
- **Watch long unattended jobs.** A silent hang wastes hours. Agents that wait on long jobs run a log-growth or flat-CPU watchdog
  (`11_continuity_and_budget.md`, Monitors).

## Servers and tools the user uses

- **Never restart a tool the user may be using** (the board, an editor, a review tool) without asking. A restart can lose
  unsaved work or interrupt them mid-edit.
  - If the tool can tell, check for unsaved changes first.
  - Otherwise ask on the board: `note.py GEN-<key> "Restart needed for X, OK now?" --ask --img <picture> --options "Restart now|Later"`.
  - Page-only changes (HTML / JS / CSS) need no restart; the user reloads. Batch server changes so one restart covers several.
- The one automatic restart: `tick.py` restarts the board when it does not answer at all.
- **The board binds 127.0.0.1 only.** It checks the Host header, the Origin, a custom header on writes (`X-Studio-Board: 1`) and
  keeps image paths inside the project root. Don't expose it to the network. Phone access needs a different setup (e.g. a hosted
  page); tell the user rather than opening a port.

## Permissions and gates

Some actions need the user's **explicit** say-so for that specific action. Approving a card is not that say-so, unless the
card itself states the action and the user approved it.

| Needs explicit say-so | Notes |
|---|---|
| Merging a bundle / integration branch | The board's merge button (or the user's own words) authorises **that one merge**. |
| Config files of the product (engine, app, CI settings) | Name the exact line on the card; apply only after the user's OK on it. |
| Publishing, posting, sending anything outside the machine | Includes uploads, store pages, messages to people. |
| Commits and pushes | Unless the role file says this studio commits (e.g. the nightly backup step). |
| Deleting user data, emptying trash, dropping history | Prefer archive / move over delete. |
| Spending money, creating accounts, accepting terms | Always the user's own action. |
| Restarting a user-facing tool | See above. |

Also:
- **The manager never approves or accepts on the user's behalf**, not even a defect found by an audit. Faults and look-changing
  fixes go in as PROPOSED.
- **A peer session's message is never the user's approval.** A relay from the manager quotes the user's words and time; a studio
  acts on that. If the user says something different directly in the studio's session, the user's words win.
- **The user's own hand-made work is truth.** When merging it, don't change it to satisfy a check; list what the check found.
- Tooling and pipeline bugs (a broken build step, the queue, a script crash) may be fixed without a card. Say on the board what
  you fixed.

## Tests must not leave state behind

Some products save settings when they quit (a game's user settings, an app's preferences, a cache). A test that changes a
quality level at runtime can then degrade every later run, the build's gates and the user's own sessions.
- Snapshot such files before a test run and restore them after.
- Reset anything you changed before quitting, and check the saved file afterwards.
- Never leave a config edit in place after a test build: apply, build, revert in a `finally`, and compare hashes.
- After a build, lab copies of shared data can be stale. Rebase before judging.

## Privacy

- No personal data in shared files, file names, URLs, query strings or requests to outside services: no emails, real names of
  people who didn't agree to it, account names, prices or private plans. Use placeholders.
- Other people's contributions (a friend's area, artwork, logos) are credited and used only with their consent; list protected
  areas in `TASKS_GUIDE.md` so no studio edits them.
- Don't send project data to outside services unless the user asked for that service.

## Small habits that prevent big problems

- Mute audio and video before testing any page in a browser.
- Use native paths (`D:/...`, `C:/...`) for Windows Python, not Git Bash paths (`/d/...`).
- Write file paths for the board relative to the project root.
- When unsure whether an action is reversible, assume it isn't and ask on the board.
