# {{PROJECT}}: studio hub

The shared home of the studio system in this project. Set up {{DATE}}.
Only shared things live here. Everything a {{TERM_STUDIO}} makes stays in `studios/<key>/`.

| Path | What | Who writes it |
|---|---|---|
| `TASKS_GUIDE.md` | the rules every {{TERM_STUDIO}} follows (wins over any other file) | {{TERM_MANAGER}}, when the user sets a rule |
| `PUBLISH.md` | how a {{TERM_BUILD}} is made, checked and published | {{TERM_MANAGER}} |
| `manager/` | the {{TERM_MANAGER}}'s role, running log (`NEXT.md`), halt procedure, scheduled prompts | {{TERM_MANAGER}} |
| `board/` | the task board tool and `board.config.json` ({{BOARD_URL}}) | {{TERM_MANAGER}} (tool changes need a `.pre_<what>_<MMDD>` backup) |
| `data/PROPOSALS.md` | every card, one block each | each {{TERM_STUDIO}} its own blocks; the board writes decisions |
| `data/decisions.jsonl` | every user action on the board, append-only | the board, `mark_live.py` |
| `data/relayed.cursor` | how many decision lines the {{TERM_MANAGER}} has relayed | `board/tick.py --relayed` |
| `data/progress/<ID>.jsonl` | notes, asks, answers per card, append-only | `board/note.py`, the board |
| `data/bundle.json` | the open bundle of changes waiting for the user's merge button (optional) | the bundle's owner {{TERM_STUDIO}} |
| `ready/<owner>.md` | each {{TERM_STUDIO}}'s {{TERM_READY}}: accepted items for the next {{TERM_BUILD}} | that {{TERM_STUDIO}} |
| `applied.json` | which {{TERM_READY}} stamps the last {{TERM_BUILD}} applied | the {{TERM_BUILD}} |
| `builds/<round>/` | brief, frozen {{TERM_READY}} copies, resume file, result of each {{TERM_BUILD}} | {{TERM_MANAGER}}, {{TERM_BUILD}} agent |
| `BUILD_RUNNING` | exists only while a {{TERM_BUILD}} runs: shared files are frozen | {{TERM_BUILD}} |
| `requests/REQUESTS.md` | requests from one {{TERM_STUDIO}} to the owner of a shared domain | any {{TERM_STUDIO}} (own items) |
| `reviews/REVIEW_<YYYYMMDD>.md` | the user's own review passes, turned into cards | {{TERM_MANAGER}} |
| `queue/` | the shared-resource queue (`resq.py`) and its state | `resq.py` only |

Start the board: `python {{HUB}}/board/start.py`. Stop it: `python {{HUB}}/board/stop.py`.
The full runbook (how the whole system works, how to change it) is kept outside the project: `{{RUNBOOK}}`.

## This project's choices
Filled by the deploying agent from the interview (runbook `12_deploy_new_project.md`). Keep it current when the user changes one.

| Choice | This project |
|---|---|
| What a {{TERM_STUDIO}} / the {{TERM_MANAGER}} / a {{TERM_BUILD}} / a {{TERM_RESULT}} / a {{TERM_READY}} is called | <describe> |
| Who decides (approves, accepts, merges) | <describe> |
| Evidence a {{TERM_RESULT}} needs | <describe> |
| Shared scarce resource and its gate | <describe> |
| Cadence: review times, handover {{HANDOVER}}, deadline {{DEADLINE}}, {{TERM_BUILD}} {{BUILD_TIME}} | <describe> |
| Usage halt threshold, model and effort per role | <describe> |
| Things that need the user's explicit say-so | <describe> |
| Protected areas, privacy rules | <describe> |
