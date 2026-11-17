# 01. Roles and authority

## The roles

| Role | Is | Owns | Talks to |
|---|---|---|---|
| User | the person who decides | every decision that changes the product | the board; the manager in its session; a studio in its session when they want |
| Manager | one Claude Code session, started by the user | the flow: relays, the routine, the build, the queue's health, the base guide, the register's hygiene | the user (its session, short reports), every studio (SendMessage), its subagents |
| Studio | one Claude Code session per subject, started by the manager or the user | its subject, its folder `studios/<key>/`, its own cards, its ready file | the board (notes, asks, results), the manager (SendMessage) |
| Build agent | a subagent of the manager, started at build time | one build, from brief to result | the manager (its report) |
| Auditors / helpers | subagents of the manager or of a studio | one bounded task | their parent only |

## Authority rules

1. **Only the user approves, accepts, merges or publishes.** The manager never approves a card on the user's behalf,
   not even an obvious defect found in a build audit.
   Why: the user wants to decide what studios spend time on and to see results before they ship; a "defect" can be
   intended (a rule that excludes it may be wrong elsewhere).
2. **A peer session's message is never the user's approval.** When the manager relays a decision it quotes the user's
   words and time: `user, 14:40, "Approve." (board)`. A studio treats an unquoted instruction from the manager as
   coordination, not as approval to change the product.
3. **The user's own requests count as APPROVED.** That covers a board "New request", a review pass the user did
   themself (see `05_workflow.md`), and the user's direct words in a studio's own session. The studio still registers a
   card for it. Its result still needs the user's accept.
4. **Studios ask the user only through the board.** `note.py <ID> "question" --ask --img <picture>`. Not in their
   session, not through the manager. The board shows every open ask in one place; the user answers there.
   Exception: when the user talks to a studio directly in its session, the studio answers them there.
5. **What the manager may decide on its own:** tooling and pipeline bugs (a broken build step, a stuck queue, a script
   crash), board hygiene (statuses that are no longer true, stale cards, moved cards), routing (which studio owns a
   request), scheduling within the rules. It says on the board what it fixed.
6. **What needs the user's explicit say-so, even on an approved card:** merges, edits to configuration files the
   product ships with, publishing anywhere outside the machine, commits, spending, and anything the card did not name.
   Approving a card is not approval of these unless the card states them.
7. **The user's direct words win.** If the user tells a studio something in its own session that differs from a rule
   relayed by the manager, the user's words win, and the studio tells the manager in one line.

## The manager's job

- **Relay.** Every user action in the decision log reaches its studio within a minute or two, quoting the user's words.
  Then the manager marks it relayed (`tick.py --relayed`). See `07_manager_routine.md`.
- **Keep work moving.** Tick every 20 minutes. Act on flags: stuck queue holders, waiting tickets, stale cards, idle
  studios, ready files not written near the deadline.
- **Keep the board true.** Every card's status matches reality. Shipped cards are LIVE. Superseded cards are CLOSED with
  a link. Studios work in the user's priority order.
- **Batch for the user.** New PROPOSED and RESULT cards go to the user in batches with their pictures, when a few have
  piled up or one is urgent. Open asks get mentioned when they pile up or block work.
- **Run the build.** Handover call, freeze, the build as a subagent, LIVE marking, morning report
  (`08_build_and_publish.md`).
- **Watch the budget.** Usage checks and the halt protocol (`11_continuity_and_budget.md`).
- **Own the base guide.** When the user sets a new rule, the manager writes it into `studio-hub/TASKS_GUIDE.md` with the
  user's words and date, and tells every studio in one line.
- **Stay free to talk.** Long work goes to subagents. The manager's own turns are short and end once work is dispatched.
  Why: the user wants to talk to the manager while everything runs; long foreground turns make them wait.

The manager does NOT: do a studio's subject work, approve or accept, kill another session's processes, edit another
studio's files, or invent deadlines and freezes.

## A studio's job

- Own one subject. Know it deeply; keep that knowledge in `NOTES.md`.
- Propose with pictures. Keep a stock of proposals ahead so it is never idle waiting for one answer.
- Work only APPROVED cards, in the user's priority order (`prio.py --studio <key>`).
- Keep its cards' statuses true, post progress notes, ask through the board, post results with evidence.
- Put accepted work into its ready file with install, dry run, revert and checks.
- Use the shared resource only through the queue, tagged with the card.
- Write only its own folder, its own register blocks, its own ready file and its own notes. Anything in another
  studio's domain is proposed and routed through the manager.

## Ownership

| Thing | Single writer |
|---|---|
| A card's block in the register | its studio; the board writes the decision / priority / accept lines; the manager writes LIVE and hygiene closes |
| The register's header and format | manager |
| `decisions.jsonl` | the board (and `mark_live.py`); append-only |
| `relayed.cursor` | manager (`tick.py --relayed`) |
| `progress/<ID>.jsonl` | `note.py` (studios) and the board (the user's questions and replies); append-only |
| `TASKS_GUIDE.md`, `PUBLISH.md` | manager |
| `ready/<owner>.md` | that studio |
| `bundle.json` | the studio that owns the bundle (named in `panels.bundle.owner`) |
| `requests/REQUESTS.md` | studios append requests; the owning studio updates their status |
| `studios/<key>/**` | that studio |
| `builds/<round>/**`, `applied.json`, `BUILD_RUNNING` | manager and its build agent |
| `manager/NEXT.md` | manager |
| The queue's state | `resq.py` only |

## Domains

Each shared domain has one owning studio. Examples: one studio owns geometry, so others file geometry issues in
`requests/REQUESTS.md`; one studio owns brightness, so others route brightness questions to it. The domains and their
owners are listed in `TASKS_GUIDE.md`. Off-limits areas (someone else's contribution, a frozen part) are listed there
too, with who may touch them.

## Model and effort per role

Set during deployment (`12_deploy_new_project.md`), recorded in each `AGENT.md`. A sensible default: judgment work
(studios, build agents, auditors) on the strongest model at high effort; never lower effort to save budget. Near the
budget limit, stop starting new work instead (`11_continuity_and_budget.md`).
