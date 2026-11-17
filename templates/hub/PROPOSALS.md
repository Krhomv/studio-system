# {{PROJECT}}: proposals register

**{{TERM_STUDIO}}s: read `{{HUB}}/TASKS_GUIDE.md` first.** It is the base guide for statuses, notes, questions, priorities and handoff.

Lifecycle: PROPOSED → APPROVED / REJECTED / BACKLOG (user) → IN WORK → RESULT ({{TERM_RESULT}} posted) → ACCEPTED / rework (user) →
HANDOFF (in the {{TERM_READY}}) → LIVE (shipped in a {{TERM_BUILD}}).
- The user's own requests enter as APPROVED with their source noted. Their {{TERM_RESULT}}s still need ACCEPTED.
- Each {{TERM_STUDIO}} adds its own blocks at the end of this file (temp file + `os.replace`; one block per task; never touch another's block).
- The user decides on the board ({{BOARD_URL}}); the board writes the `decision:`, `priority:` and `accept:` lines itself.
- Progress goes through `python {{HUB}}/board/note.py <ID> "text" [--pct N] [--img path]`, never into this file.

Entry format (every line is `field: text` or an indented continuation line):
```
## <ID>  <owner>  <short title>  — STATUS
what:    <the change, in one or two lines>
why:     <what looks wrong / what improves; the reference as a guide>
visual:  <picture path(s) inside the project: current state + reference, and a mock / lab A/B if there is one>
scope:   <where / how many instances; a rule or a one-off>
cost:    <rough time / queue tickets; risk>
decision: <user, date, words>          (the board, or the manager relaying the user's words)
priority: <P1..P4 (user, date)>        (the board; no line = P3)
result:  <A/B sheet path>              (the studio, when done)
accept:  <user, date, words>           (the board)
handoff: <ready-file stamp>            (the studio) / live in <label> (mark_live.py)
```

---
