# Memory rules: format and where each kind of rule belongs

## Where a rule goes
| Kind of rule | Where | Why |
|---|---|---|
| How every {{TERM_STUDIO}} works (statuses, asks, queue, handoff) | `{{HUB}}/TASKS_GUIDE.md` | one place all {{TERM_STUDIO}}s read; it wins over everything else |
| A decision the user took about the product ("keep the dark floor") | TASKS_GUIDE §7 "Decisions already taken" | stops every {{TERM_STUDIO}} re-flagging it |
| One {{TERM_STUDIO}}'s role, domain, limits | `studios/<key>/AGENT.md` | loaded at every session start in that folder |
| What a {{TERM_STUDIO}} learned about its craft (methods, pitfalls, numbers) | `studios/<key>/NOTES.md` (Lessons) | lasting knowledge travels with the {{TERM_STUDIO}}, not the session |
| How the user wants this session to behave (feedback, preferences) | the session's memory folder | memory is per working folder: a {{TERM_STUDIO}} in `studios/<key>/` has its own |
| The {{TERM_MANAGER}}'s state (jobs, ids, what is open) | `{{HUB}}/manager/NEXT.md` | state, not a rule; it changes hourly |
| A fact the project's files or history already record | nowhere new | don't duplicate; point to it |

When the user sets a rule for everyone, the {{TERM_MANAGER}} writes it into TASKS_GUIDE (date + their words) and tells the {{TERM_STUDIO}}s; a
memory alone would reach only the session that wrote it.

## Memory file format (one fact per file)
```markdown
---
name: <short-kebab-case-slug>
description: <one line: what the rule is, specific enough to decide relevance at recall>
metadata:
  type: feedback        # user | feedback | project | reference
---

**User <date> ~<time>:** "<the user's exact words>" (context: <what had just happened, in one line>).

**Why:** <the reason the user gave, or the cost the rule prevents; one or two lines>.

**How to apply:**
- <the concrete behaviour, when it triggers, what to do instead>
- <the exception, if any>

Related: [[other-memory-name]], [[another]].
```
Then add one line to the memory index (`MEMORY.md`): `- [Title](file.md) — hook`.

## Rules for rules
- Quote the user's words and date; a rule without its source gets misapplied later.
- Write the why: it decides the edge cases the rule's text doesn't cover.
- Update the existing file when a rule changes ("replaces the <date> rule"); delete a rule that turned out wrong.
- A rule relayed by another session is the {{TERM_MANAGER}}'s reading of the user, not the user's own words: say so in the file, and let
  the user's direct words win.
- No personal data, names of people or secrets in memory files.
