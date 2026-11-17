# 00. Overview: the model in one page

## The idea

A project too big for one session is split by subject. Each subject gets a **studio**: a separate session with its own
folder, its own role file and its own notes. Studios iterate fast on their subject in their own lab copies.

One **manager** session coordinates. It does not do the studios' work. It keeps their work moving, carries the user's
decisions to them, shares the scarce resource fairly, and turns accepted work into a shipped product on a fixed cadence.

The **user** decides. Every new piece of work, every result that ships, every merge and every config change waits for
the user's own yes. The user gives that yes on a local web **task board**, with pictures in front of them.

Why this shape:
- Short loops per subject (minutes, not hours) let the user steer each subject separately.
- A fixed build cadence folds many small accepted changes into one playable / usable product without blocking the day.
- One decision surface (the board) means the user never has to read eight session transcripts.
- The manager's routine catches stuck jobs, idle studios and stale cards before they cost hours.

## The loop

```
 PROPOSED  -- user approves -->  APPROVED  -- studio starts -->  IN WORK
    |  \-- user rejects --> REJECTED                               |
    |  \-- user parks  ---> BACKLOG                                |  progress notes, asks to the user
    v                                                              v
                                                                RESULT  (A/B picture on the card)
                                                                   |
                         user sends it back (rework) <-------------+-------- user accepts
                         APPROVED, IN WORK (result rejected)                     |
                                                                                 v
                                                                             ACCEPTED
                                                                                 |  studio writes it into ready/<owner>.md
                                                                                 v
                                                                             HANDOFF
                                                                                 |  the build ships it
                                                                                 v
                                                                               LIVE
```

Side exits: CLOSED (no longer needed, reason in brackets, may link to a successor card); reverted by the build
(back to APPROVED, IN WORK with the reason).

## A day in the system

| When | What happens |
|---|---|
| Day | Studios work their APPROVED cards in the user's priority order. They post progress notes, ask questions on the board, post results. They batch new proposals ahead so they are never idle waiting for one answer. |
| Any time | The user opens the board, approves, rejects, parks, accepts, answers, sets priorities, files new requests. Each click is one line in the decision log. |
| Within a minute | The manager sees the new decision line, relays it to the studio, quoting the user's words, and marks it relayed. |
| Every 20 min | The manager's tick: queue health, stale cards, idle studios, unrelayed decisions, board up. Quiet ticks end in one line. |
| ~1 h before the deadline | Handover call: every studio puts everything finished and accepted into its ready file. |
| Deadline | Ready files are read. |
| Build time | The manager writes the freeze marker and runs the build as a subagent. Studios keep working on what doesn't touch the frozen files. |
| Morning | Shipped cards are marked LIVE, reverted ones go back to work with the reason, the user gets one short report, each studio gets its own results. |

The times are a project setting (`schedule` in `board.config.json`). A project with no nightly build uses an
on-demand or weekly publish instead (`08_build_and_publish.md`).

## What each part is

| Part | Where | Purpose |
|---|---|---|
| Task board | `studio-hub/board/` | The user's only decision surface. Reads and writes the register, logs every decision. |
| Register | `studio-hub/data/PROPOSALS.md` | One block per card. Studios write their own blocks; the board writes decisions into them. |
| Decision log | `studio-hub/data/decisions.jsonl` | Append-only record of every user action. The manager relays from it. |
| Progress notes | `studio-hub/data/progress/<ID>.jsonl` | Studio notes, asks, withdrawals and the user's replies, per card. |
| Base guide | `studio-hub/TASKS_GUIDE.md` | The rules every studio follows. Wins over any other file. |
| Studio folder | `studios/<key>/` | Role (`AGENT.md`), knowledge (`NOTES.md`), pictures, lab, tools, installers. |
| Manager folder | `studio-hub/manager/` | Role, running log (`NEXT.md`), halt procedure, scheduled prompts. |
| Ready files | `studio-hub/ready/<owner>.md` | What each studio hands to the next build: install, dry run, revert, checks. |
| Build folder | `studio-hub/builds/<round>/` | Brief, frozen ready copies, resume file, result. |
| Queue | `studio-hub/queue/resq.py` | Fair turns on a scarce shared resource, build first, user hold. |

## Default terms and renaming

The default words are studio, manager, user, result, build, ready file, and the status words above.
A deploying agent asks the user what their project calls these things and sets them in `board.config.json`:
`"terms"` for the page wording, `"statuses"` for status labels (and optionally the words written in the register),
`"studios"` for the subjects. See `12_deploy_new_project.md` for the interview.

## Core rules in one list

1. Nothing starts without the user. Ideas become PROPOSED cards with a picture first.
2. The user's own requests count as approved. Their results still need the user's accept.
3. Only the user approves, accepts, merges or publishes. The manager never decides on the user's behalf.
4. Studios ask the user only through board asks, each with a picture.
5. Card statuses are kept true at all times. The user reads only the board.
6. Only accepted work goes into a ready file. Everything accepted and checked goes in at the handover call.
7. The shared resource is used only through the queue, one ticket per short chunk, tagged with its card.
8. One writer per shared file. Write with a temp file and `os.replace`. Stop only your own processes.
9. The manager stays free to talk: it dispatches long work to subagents and keeps its own turns short.

Each rule is explained, with its reason, in the file that owns it: roles in `01_roles.md`, the card flow in
`05_workflow.md`, evidence in `06_evidence.md`, the build in `08_build_and_publish.md`, the queue in
`09_shared_resources.md`, safety in `10_safety_rules.md`.
