# {{PROJECT}}: studio system

This project runs the studio system: one {{TERM_MANAGER}} session and several {{TERM_STUDIO}} sessions, steered by the user on a
task board ({{BOARD_URL}}).

- Every {{TERM_STUDIO}} follows `{{HUB}}/TASKS_GUIDE.md`. Where another file disagrees, that guide wins.
- A {{TERM_STUDIO}}'s own role is in `studios/<key>/AGENT.md`; the {{TERM_MANAGER}}'s is in `{{HUB}}/manager/AGENT.md`.
- Nothing new starts without the user's approval on the board, and nothing ships without the user's accept.
- Questions to the user go through the board (`python {{HUB}}/board/note.py <ID> "..." --ask --img <picture>`), not in a session.
