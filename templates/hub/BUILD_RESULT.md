# Round <rNN> result (<date>): <label>

<One paragraph: built or not, where it is (<path / launcher / URL>), how long it took, the headline (better / same / worse, why).>

## What went in
### <owner> (stamp <stamp>)
- <ID> <title>: applied <backup stamp>; gate <PASS / FAIL>; <one line on what it does in the product>
### Other inputs
- <bundle / base>: <version, what it carried>

Not in tonight: <IDs and why>.

## Gates
| Gate | Expected | Measured | Verdict |
|---|---|---|---|
| <name> | <value> | <value> | PASS / FAIL / NOTE |

## Evidence
- Sheets: <paths inside the project>
- Scores / measurements vs <baseline>: <table or one line per set>

## Reverted
- <ID>: why (<gate, numbers>), revert stamp <stamp>, state now (rebuilt without it / listed for the morning).

## Top faults (owner → what)
- <owner>: <fault, where, picture>

## For the morning
- LIVE: `python {{HUB}}/board/mark_live.py <label> --round <rNN> <IDs>`
- Back to work: `python {{HUB}}/board/mark_live.py <label> --revert-to-work <ID> --reason "..."`
- Per {{TERM_STUDIO}}: <what to tell each one>
- Backup step: <one-line result>
