# {{LABEL}} {{TERM_STUDIO}} ({{OWNER}}): working notes

Owner `{{OWNER}}`, board prefix `{{PREFIX}}-`, general thread `GEN-{{KEY}}`, queue owner `{{QUEUE_OWNER}}`. Base rules:
`{{HUB}}/TASKS_GUIDE.md` (wins over this file).
This file holds lasting working knowledge, not a diary. Progress goes on the board (`note.py`); session hand-over notes go in
`HANDOFF.md`. Keep it under ~30 KB: when the log grows, fold what lasts into the sections above it and move old log entries to
`logs/notes_archive_<YYYYMM>.md`.

## Current state (rewrite in place, 5 lines max)
- Working on: <card, step>
- Waiting for: <the user's answer on X / another studio's Y>
- Queue: <ticket waiting / none>
- Next: <the next card in priority order>

## Where things live (all under studios/{{KEY}}/)
| Path | What |
|---|---|
| `cards/` | pictures for cards, asks and {{TERM_RESULT}}s (`<ID>_*.jpg`) |
| `lab/` | scratch copies and experiments (never shared data) |
| `tools/` | my scripts |
| `staged/` | installers for accepted items (dry run / `--apply` / `--revert <stamp>`) |
| `backup/` | backups my installers made, and anything of others' I had to restore |
| `logs/` | job logs, archived notes |

## Scripts
| Script | Does |
|---|---|
| `tools/<name>.py` | <what it does, its main flags> |

## Method
- <how I make a {{TERM_RESULT}}: the lab, the evidence, the check that the lab matches what ships>
- <how I size queue jobs>

## Lessons
- <a thing that went wrong or surprised me, and the rule that follows; one or two lines each>

## Service for other {{TERM_STUDIO}}s
- <what I do for others, how they ask, what they get>

## Open cards (one line each, keep current)
- <ID> <short title>: <state, next step>

## Log (short, dated, newest last; fold into the sections above when it lasts)
- {{DATE}}: {{TERM_STUDIO}} created.
