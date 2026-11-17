# Shared-resource queue (resq)

One fair queue for one scarce shared resource: a GPU, a test device, a build machine, a licence seat. Every user of the resource
joins the queue instead of polling a lock. Python standard library only, no console windows. Rules and reasons:
`runbook/09_shared_resources.md`.

| Need | Command (from the project root) |
|---|---|
| One job | `python studio-hub/queue/resq.py run "<what>" --owner <owner> --task <ID> -- <command ...>` |
| Hold the lock across several steps | `... resq.py acquire "<what>" --owner <owner> --task <ID> [--pid <your pid>]`, your steps, then `... resq.py release --owner <owner> [--pid <your pid>]` |
| A job that always ends within short_max_min | add `--short` (it may use another owner's grace gap) |
| See the queue | `... resq.py status` (exit 3 = someone waiting) |
| The user's hold | the board's Hold / Release button, or `resq.py hold [--wait]` / `resq.py unhold` |

## Rules
- Use one stable `--owner` per studio (the `queue_owner` in board.config.json). The build uses an owner that matches
  `priority_owners` (e.g. `build-r12`).
- Tag every job with the board task it serves (`--task <ID>` or env `RESQ_TASK`). Honest tags: an open P1 task jumps the queue.
- One ticket per chunk of a few minutes. A running job is never cut, so one long ticket blocks everyone.
- Do CPU setup before you take the lock; release straight after the GPU part.
- Never hold the lock while you wait for a precondition (another app's memory, a service). Check after `acquire`; if it fails,
  release and join again.
- Never remove another owner's lock. A lock whose holder pid is dead is cleared by the next waiter; the user's hold never is.
- A hard kill skips `release`: stop your own jobs with a script that releases in its cleanup.
- The gate (`gate_cmd`) keeps long jobs off a resource that other programs already fill. When it stays shut, the manager tells the
  user which of their apps to close; nobody loosens the gate on their own.

## Files (state, in this folder)
`lock/owner.txt` (the holder's line: owner, what, task, since, pid), `tickets/*.json` (one per waiter), `turn.json` (the running
turn, least-recently-served record, gap bans), `events.log` (one JSON line per take / release / hold: measure before changing
settings), `gaps.log` (short jobs that overran).

## Settings (board.config.json "queue")
`turn_max_min` (20), `grace_s` (60), `turn_tail_min` (3), `short_max_min` (3), `gap_ban_min` (60), `priority_owners`
(["build*", "nightly*"]), `hold_line` ("USER HOLD"), `gate_cmd` ("" = none; a shell command, exit 0 = OK), `on_hold_url` (POSTed
once the user's hold is taken, e.g. to make a local service unload its models; "" = none).

Not shipped on purpose: a watchdog that kills frozen holders. See `runbook/09_shared_resources.md` for when a project adds one.
