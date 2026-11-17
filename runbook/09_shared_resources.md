# 09 · Shared scarce resources

Studios run in parallel; some things can only serve one job at a time. A GPU, a test device, a build machine, a licence seat,
an API with a tight rate limit, a recording booth. Without a queue, jobs poll a lock, the strictest poller never gets a turn,
and a two-minute job waits two hours behind a stream of long ones. This page describes the generic queue shipped as
`studio-hub/queue/resq.py` (config section `queue` in `board.config.json`) and the rules every studio follows around it.

Skip the queue (`scaffold.py init --no-queue`, `panels.queue.enabled: false`) when nothing is scarce.

## The model

- **The lock** is a folder `queue/lock/` with an `owner.txt` line: owner name, what, pid, time. Whoever holds the lock may use
  the resource. Nobody else touches it.
- **Tickets** are files in `queue/tickets/`, one per waiting job (owner, what, pid, task, short, created). A waiter takes the lock
  only when its ticket is first in the serving order and the lock is free. A ticket whose pid is dead is removed by any waiter.
- **State:** `queue/turn.json` (whose turn, since when, grace), `queue/events.log` (one JSON line per take / release).

Commands (from the project root):

| Need | Command |
|---|---|
| One job | `python studio-hub/queue/resq.py run "<what>" --owner <owner> [--task <ID>] [--short] -- <command ...>` |
| Hold across several steps | `resq.py acquire "<what>" --owner <owner> [--task <ID>] [--pid PID]`, your steps, then `resq.py release --owner <owner> [--pid PID]` |
| See the queue | `resq.py status` (exit 3 = someone is waiting) |
| The user's hold | `resq.py hold` / `resq.py unhold` (the board's Hold / Release button runs the same code) |

`acquire` and `release` default `--pid` to the caller's pid, so the holder stays alive for the whole hold. Pass `--pid`
explicitly when you call from a wrapper.

## Serving order

1. **Priority owners** (config `queue.priority_owners`, e.g. `build*`, `nightly*`): the build goes first. A job already running
   is never cut; the build takes the resource right after it.
2. **Tickets for an open P1 card** (`--task <ID>`, priority read from the register). They may also take a free lock during
   another owner's grace.
3. **Board priority** of the ticket's task: P2 before P3 and untagged, before P4.
4. **Least-recently-served owner**, so one owner with an old ticket always queued can't win every rotation.
5. **Oldest ticket.**

Tag every job with its card: `--task <ID>`. Tag honestly; the manager checks that tags match the work.

## Turns

- When an owner gets the resource its **turn** starts. Its further tickets run back to back.
- After each release the owner keeps the resource for `queue.grace_s` seconds (default 60), so CPU work between two of its jobs
  doesn't lose the turn.
- A turn ends when the owner queues nothing within the grace, or after `queue.turn_max_min` (default 20) of consecutive jobs.
  A single long job is never cut, which is why long work must be split (see "One ticket per chunk").
- In the last `queue.turn_tail_min` minutes of a turn, the owner's **long** tickets rank fairly instead of first whenever
  someone else waits. This stops an owner re-taking the resource at 19.5 minutes while others have waited an hour.
- Inside its turn, an owner's own tickets also run in board-priority order.

## Short jobs in the gaps

`--short` means "this job always releases within `queue.short_max_min` minutes". A short ticket may run inside another owner's
grace gap when that owner has nothing queued. The gap pauses the owner's grace and turn clock. A gap job that overruns is logged
and its owner gets no gaps for `queue.gap_ban_min` minutes. Decide `--short` per call, not per job type: the same step can take
twenty seconds or half an hour depending on its input.

## The user's hold

The user may need the resource themselves (to play, to render, to record). The board's Hold button (or `resq.py hold`):
- takes the lock with an owner line starting with `queue.hold_line` (default `USER HOLD`) **as soon as it is free**; a running
  job finishes first and the button shows "holding..." meanwhile;
- then calls `queue.on_hold_url` if set (e.g. ask a shared model server to unload its models);
- logs `hold` / `release` in `decisions.jsonl`, so the manager tells the studios.

Rules:
- Nobody takes a held lock. Only the user (Release button, `resq.py unhold`) or the manager on the user's word removes it.
- Before taking a hold for the user, the manager asks the current holder's studio to stop its chained runners and drop its
  queued tickets. Otherwise a runner can start its next job inside its own turn before the hold lands.
- "Hold" means stop: studios stop their own multi-job runners at once, not only "after this job".

## Preconditions and gates

Many jobs need more than the lock: free memory on the device, no other engine instance, an idle shared service.
- **Check preconditions after you acquire, never before joining.** A gate checked before joining never passes while another
  studio's job is running, so the waiter never gets a ticket.
- **Never hold the lock while waiting on a precondition.** If it fails after acquiring, release and re-join after a few minutes.
- The optional `queue.gate_cmd` (exit 0 = OK) is run by resq when a ticket reaches the front of a free lock. It keeps long jobs
  off a device that something outside the queue already fills.
- When the gate stays shut because of **the user's own apps**, tick.py flags `GATE`. The manager tells the user, in one line,
  which apps hold how much, so they can close some. **Never loosen the gate** and never touch the user's apps.

## One ticket per chunk

The turn cap only acts between tickets. A script that takes one ticket for an hour of batches blocks everyone for an hour. Take
one ticket per few-minute chunk (one engine launch, one capture batch, one render): acquire before, release straight after.

## Lean jobs

The lock is usually the project's bottleneck. Measured on a busy day, most of a typical lab job was overhead.
- Do CPU setup **before** acquiring; release straight after the capture.
- Skip warm-ups when only parameters changed.
- Batch variants into one job; diagnosis needs one or two views, not ten.
- Find causes from data (logs, masks, debug views) before switching things off one resource run at a time.

## Stopping and dead holders

- A hard kill runs no cleanup, so the lock stays held by a dead pid. Each studio keeps a **stop script** for its own runners
  that kills its own pid tree, removes its own markers and releases the lock.
- resq removes a lock whose holder pid is dead (after a re-check), and its tickets.
- Marker files that name a pid ("busy" flags some tools write) must be cleaned with the lock, or they block every later job.
- After an edit to `resq.py`, waiters that started earlier keep running the old code until they re-queue. Tell the studios to
  re-queue still-waiting jobs.

## Shared local services

A service several studios use (a local image-model server, a database, a dev server) is a shared resource too.
- Run **one** instance. Never start a second one, even if the first seems slow.
- Free its memory only when its own queue is empty.
- Don't restart it while its queue has jobs: other sessions may be using it.
- An idle service that keeps a model loaded can shut the gate for everyone. The manager (or `on_hold_url`) frees it when idle.

## Measure before changing a knob

`queue/events.log` records every take and release. Before changing `grace_s`, `turn_max_min` or the order, measure: time lost
(owner never came back while others waited), grace used for the owner's next job, gap fills, jobs per turn. Show the user the
numbers and a recommendation; change nothing without their yes. Back up `resq.py` first (`resq.py.pre_<what>_<MMDD>`).

## The manager's queue checks (tick.py flags)

| Flag | Meaning | Action |
|---|---|---|
| `HOLD` | a non-priority owner held the lock more than `turn_max_min + 5`, or the holder is dead | Read the holder's log tail. If stuck, message the owner studio with the evidence (pid, last log line) and ask it to stop its own pid. Never kill another session's process. |
| `WAIT` | a ticket waited more than 45 min | Re-check after 1 min, then find out why (turn order, gate) and message the right studio. Waiting behind the build or a user hold is by design. |
| `STUCK` | lock free, tickets waiting, nobody in grace | Re-check after 1 min; a waiter that never takes it is usually stuck on its own precondition. |
| `GATE` | gate shut while tickets wait | Tell the user which apps to close. |

## A kill watchdog (described, NOT shipped)

A long-running project can add a watchdog that frees the lock from a frozen holder. It is not shipped because it kills
processes and must be tuned to the project's engines. If you add one:
- **Stale:** holder pid dead or unknown, and no resource or engine activity for ~20 min → remove the lock (no kill).
- **Frozen:** holder alive, but its process tree's CPU flat and the resource idle for ~30 min → kill the holder's tree **by pid**
  (never by name), remove the lock, log it.
- **Spinning:** holder alive and busy, but no engine in its tree and the resource nearly idle for ~30 min → same as frozen.
- Never touch the user's hold (alert after a few hours instead). Skip priority owners. Require all engine processes to be quiet:
  engines launched through another shell may sit outside the holder's process tree.
- Remove marker files that name the killed pid. Log every action with evidence.
- Run it as a supervised, self-expiring process (see `11_continuity_and_budget.md`, Monitors) and record where it runs in `NEXT.md`.

Add it when the project runs long unattended jobs at night and has seen holders freeze. Until then, tick.py's `HOLD` flag plus a
message to the owner is enough.
