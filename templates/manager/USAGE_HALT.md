# Usage halt ({{PROJECT}})

The user's rule: <describe, e.g. "at 98 % of the weekly usage window, halt everything while I switch accounts">.
Threshold: <N> % of <describe which window(s) count>. Read it with `mcp__ccd_session_mgmt__get_usage`.
If the user suspends the rule ("ignore the limit this time"), write that in NEXT.md with their words; the rule comes back after
the reset unless they say otherwise.

## Watching
- The {{TERM_MANAGER}} checks usage on every side-session event and every scheduled turn.
- Backstop: a scheduled check every 30 min (`prompts/usage_check.txt`). At <N - 3> % or more, a check every 10 min.
- {{TERM_STUDIO}}s and subagents check it themselves at the start of each turn or step. At the threshold they stop at the next safe
  point without waiting for the {{TERM_MANAGER}}.
- Below the threshold, keep working and dispatching normally, even work that won't finish before it (it resumes after).

## Halt (at the threshold)
1. **Send HALT** to every working session: the {{TERM_STUDIO}}s, any other linked session (message only if you didn't start it), and any
   {{TERM_BUILD}} subagent. Text:
   "HALT (usage <N> %, the user's account switch): start nothing new. Don't launch new queue jobs; a job already running may
   finish and release the queue on its own. Write your resume notes (NOTES / HANDOFF / RESUME_BUILD.md) now, then end your turn."
2. **Stop the stragglers.** If a session you started is still working 10 minutes later, stop it with `stop_session`
   (`prompts/halt_stragglers.txt`). Don't kill running jobs or engines: they finish and release the queue themselves.
3. **Delete the scheduled jobs** (tick, usage, handover call, {{TERM_BUILD}} trigger). The next account's session re-creates them.
4. **Handover in `NEXT.md`**, top entry `HALTED <time>`:
   - each session and its last state; each subagent and its resume file;
   - the queue holder and waiters (`python {{HUB}}/queue/resq.py status`);
   - the jobs to re-create, with their crons and prompt files;
   - the open user decisions.
5. **Tell the user** in one short message: halted at <N> % (<window>), what was mid-way, ready to switch. Then stop: from then on,
   side-session events get one line at most and no new work.

## Resume (after the switch)
- The user resumes this session (`prompts/resume.txt`).
- Re-create the scheduled jobs and the decisions watcher; write the new ids in NEXT.md.
- Check the queue (`resq.py status`); if the user held it, ask whether they are done before releasing.
- Tell each {{TERM_STUDIO}} "resume" with a pointer to its notes (staggered if more than ~8). The user may prefer to resume them directly.
