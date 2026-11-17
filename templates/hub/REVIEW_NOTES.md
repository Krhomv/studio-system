# Review pass <YYYY-MM-DD> on <label of the build the user reviewed>

The user's own review notes (<describe how the user marks things: in-app markers, screenshots, a list>) turned into cards by the
{{TERM_MANAGER}}. The user's own notes count as APPROVED; default priority P2 unless the user said otherwise. Their {{TERM_RESULT}}s
still need the user's accept.

Copy this file to `{{HUB}}/reviews/REVIEW_<YYYYMMDD>.md` for each pass. One row per note; nothing is dropped. A note that is a
question (not a request) goes to the owner as an ask, not a card.

| # | The user's words (verbatim) | Picture / marker | Where | Owner | Card | Priority |
|---|---|---|---|---|---|---|
| 1 | "<quote>" | <path inside the project> | <location> | <owner> | <ID> | P2 |

Registered <date time> by the {{TERM_MANAGER}}. Each card's `decision:` line reads `user review <YYYY-MM-DD> note #N (approved by the workflow rule)`.
