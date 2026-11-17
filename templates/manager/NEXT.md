# {{PROJECT}}: {{TERM_MANAGER}} log and handover

Newest entry first. One entry per event that a successor would need: a decision, a state change, a problem, a snapshot.
Every entry starts `## <MM-DD HH:MM> <TOPIC IN CAPS>` and says what is true now and what is next. Write "FOR THE <round> BRIEF:"
on anything the next {{TERM_BUILD}} must know. Before a likely context compaction or an account switch, write a SNAPSHOT entry.

Keep this file short enough to read at a session start: when it passes ~60 KB, move entries older than a week to
`NEXT_archive_<YYYYMM>.md` (temp file + `os.replace`) and leave a pointer.

## Standing state (rewrite in place when it changes)
- Scheduled jobs (session-only; re-create after an app restart, a session switch, or before day 7):
  | Job | Cron | Id | Created | Expires |
  |---|---|---|---|---|
  | tick | `7,27,47 * * * *` | <id> | <date> | <date + 7 d> |
  | usage check | `19,49 * * * *` | <id> | <date> | <date + 7 d> |
  | handover call | <cron for ~{{HANDOVER}}> | <id> | <date> | <date + 7 d> |
  | {{TERM_BUILD}} trigger | <cron for ~{{BUILD_TIME}}> | <id> | <date> | <date + 7 d> |
- Decisions watcher: Monitor `python {{HUB}}/board/watch.py --minutes 30`, re-armed every 30 min; cursor at <N>.
- {{TERM_STUDIO}} sessions: <key>: <session name / id>, <working folder>, <model / effort>, <state: active / parked by the user>.
- Open for the user: <asks / results waiting, oldest first>.
- Last {{TERM_BUILD}}: <label>, <round>, <date>; next: <what it will take>.

---

## <MM-DD HH:MM> SNAPSHOT (before compaction)
- Jobs: <ids>. Watcher cursor <N>. Queue: <holder / waiting>.
- {{TERM_STUDIO}}s: <one line each: working on, waiting for>.
- Tonight: <ready stamps so far, what is pending>.
- Open for the user: <list>.

## <MM-DD HH:MM> SET UP ({{DATE}})
- Studio system deployed. Board {{BOARD_URL}}. {{TERM_STUDIO}}s: <keys>.
