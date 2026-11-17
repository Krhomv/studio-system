# Proposals register: Example Game

Studios: read `studio-hub/TASKS_GUIDE.md` first. One block per task; write it with a temp file + os.replace and touch only your own
block. Progress goes through `note.py`, never into this file.

Entry format:
```
## <ID>  <owner>  <short title>  — STATUS (note)
what:    <the change, in one or two lines>
why:     <what looks wrong / what improves>
visual:  <picture path(s): current state, a marked crop, a mock>
scope:   <where / how many; rule or one-off>
cost:    <time, resource tickets, risk>
decision: <user, date, words>          (the board writes it)
priority: <P1..P4 (user, date)>        (the board writes it; none = P3)
result:  <A/B picture path>            (the studio, when done)
accept:  <user, date, words>           (the board writes it)
handoff: <ready-file stamp>            (the studio) / live in <label> (mark_live.py)
```

---

## ART-01  art-studio  Rock textures read flat at mid distance  — LIVE (v3, r3 11-16)
what:    add a mid-distance detail layer to the cliff rock material so the rocks keep their shape from 20-60 m.
why:     from the main path the cliffs read as flat grey walls; up close they are fine.
visual:  studios/art/cards/ART-01_rocks_ab.png
scope:   all cliff rock instances (one material rule, not per object).
cost:    2 short GPU tickets; low risk.
decision: user, 2026-11-15 18:29, "Approve." (board)
result:  studios/art/cards/ART-01_rocks_ab.png
accept:  user, 2026-11-16 06:29, "Accept." (board)
handoff: live in v3 (r3, 2026-11-16 16:29, mark_live)

## ART-02  art-studio  Torch glow too orange in the cave  — ACCEPTED
what:    move the cave torch light from orange to a warmer white and lower its radius by a fifth.
why:     the cave reads like it is on fire; the torches should read as small warm lights.
visual:  studios/art/cards/ART-02_torch_ab.png
scope:   the 14 cave torches (one light preset).
cost:    1 short ticket.
decision: user, 2026-11-16 20:29, "Approve." (board)
result:  studios/art/cards/ART-02_torch_ab.png
accept:  user, 2026-11-17 19:29, "Accept." (board)
handoff:

## ART-03  art-studio  Grass tint on the north hill  — RESULT (variants A / B / C, pick in the ask)
what:    tone the north hill grass down from lime to a dry green; three strengths.
why:     the hill reads neon next to the forest edge.
visual:  studios/art/cards/ART-03_grass_now.png
scope:   north hill grass only (a region mask), not site-wide.
cost:    1 ticket per variant set.
decision: user, 2026-11-17 02:29, "Approve." (board)
priority: P2 (user, 2026-11-17 02:29, board)
result:  studios/art/cards/ART-03_grass_abc.png
accept:
handoff:

## ART-04  art-studio  Signboard text unreadable at the market  — IN WORK
what:    redraw the market signboard text at twice the texel density, same style.
why:     user: "I can't read any of the shop signs".
visual:  studios/art/cards/ART-04_sign_aim.png
scope:   the 6 market signs (one atlas).
cost:    CPU work, 1 ticket for the A/B.
decision: user, 2026-11-17 13:29, "Approve." (board)
priority: P2 (user, 2026-11-17 14:29, board)
result:
accept:
handoff:

## ART-05  art-studio  New icon set for the inventory  — PROPOSED
what:    replace the 40 placeholder inventory icons with one consistent drawn set (mock attached: 6 of them).
why:     the placeholders mix three styles; players mix up potions and food.
visual:  studios/art/cards/ART-05_icons_mock.png
scope:   inventory icons only.
cost:    about a day of CPU work; no GPU.
decision:
result:
accept:
handoff:

## ART-06  art-studio  Darker lake water  — BACKLOG (user: not now)
what:    darken the lake water and add a little murk near the shore.
why:     the lake reads like a swimming pool.
visual:  studios/art/cards/ART-06_water.png
scope:   the lake material.
cost:    2 tickets.
decision: user, 2026-11-15 22:29, "Backlog." (board)
result:
accept:
handoff:

## AUD-01  audio-studio  Footsteps on wood sound like stone  — APPROVED, IN WORK (result rejected: rework)
what:    tag the wooden floors with the wood surface type so the footstep set switches.
why:     every wooden floor plays the stone steps.
visual:  studios/audio/cards/AUD-01_steps.png
scope:   all wooden floor meshes (a surface-type rule).
cost:    CPU only.
decision: user, 2026-11-16 16:29, "Approve." (board)
result:  studios/audio/cards/AUD-01_steps.png
accept:  user, 2026-11-17 16:29, "Rework. the bridge still sounds like stone" (board)
handoff:

## AUD-02  audio-studio  Ambient wind loop clicks at the loop point  — HANDOFF
what:    re-cut the wind loop on a zero crossing and cross-fade 200 ms.
why:     a click every 41 s in the open areas.
visual:  studios/audio/cards/AUD-02_wind_loop.png
scope:   one sound file.
cost:    minutes.
decision: user, 2026-11-16 18:29, "Approve." (board)
result:  studios/audio/cards/AUD-02_wind_loop.png
accept:  user, 2026-11-17 17:29, "Accept." (board)
handoff: studio-hub/ready/audio-studio.md stamp 2026-11-17 18:29

## AUD-03  audio-studio  Lower the music under dialogue  — PROPOSED
what:    duck the music by 6 dB while a character speaks, with a 300 ms fade.
why:     the music covers quiet lines in two scenes.
visual:  studios/audio/cards/AUD-03_ducking.png
scope:   the music bus (one rule).
cost:    CPU only.
decision:
result:
accept:
handoff:

## AUD-04  audio-studio  New menu click sound  — REJECTED
what:    a softer click for the menu buttons.
why:     the current click is sharp.
visual:
scope:   menu only.
cost:    minutes.
decision: user, 2026-11-15 00:29, "Reject. the click is fine" (board)
result:
accept:
handoff:

## LVL-01  levels-studio  Gap in the bridge railing  — APPROVED (waiting for LVL-02)
what:    close the gap in the east bridge railing.
why:     the player can walk off the bridge there.
visual:  studios/levels/cards/LVL-01_railing.png
scope:   one railing segment (in the level bundle).
cost:    minutes; goes in the open bundle.
decision: user, 2026-11-17 10:29, "User request." (board)
priority: P1 (user, 2026-11-17 10:29, board)
result:
accept:
handoff:

## LVL-02  levels-studio  Cave entrance too narrow for the camera  — IN WORK
what:    widen the cave entrance by 1 m so the follow camera stops clipping into the rock.
why:     the camera jumps inside the wall for a second on the way in.
visual:  studios/levels/cards/LVL-02_cave.png
scope:   the cave entrance only.
cost:    one bundle change, 2 tickets for the A/B.
decision: user, 2026-11-16 22:29, "Approve." (board)
result:
accept:
handoff:

## LVL-03  levels-studio  Old spawn area clean-up  — CLOSED (moved to LVL-02: same rock edit)
what:    clean up the old spawn area rocks.
why:     overlapping rocks.
visual:
scope:   spawn area.
cost:    small.
decision: user, 2026-11-15 10:29, "Approve." (board)
result:
accept:
handoff:

## LVL-04  levels-studio  Ledge too high to climb near the mill  — PROPOSED
what:    lower the mill ledge by 40 cm.
why:     players expect to climb it.
this line has no field name, so the board shows a parser warning for this card
visual:  studios/levels/cards/LVL-04_ledge.png
scope:   one ledge.
cost:    minutes.
decision:
result:
accept:
handoff:
