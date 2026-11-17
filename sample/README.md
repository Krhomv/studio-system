# Sample project: "Example Game"

A fictional small game run by three studios, to see the board with real-looking data and to test changes to the tool.

| Studio | Key | Prefix | Owner name |
|---|---|---|---|
| Art | `art` | `ART-` | `art-studio` |
| Audio | `audio` | `AUD-` | `audio-studio` |
| Levels | `levels` | `LVL-` | `levels-studio` (owns the level bundle) |

What it shows:
- 14 cards covering every status: PROPOSED, APPROVED (waiting for another card), IN WORK (one stale, one in rework), RESULT with a
  variant ask (Accept: A / B / C), ACCEPTED, HANDOFF, LIVE, BACKLOG, REJECTED, CLOSED (moved to another card), and one card with a
  line outside the field format (the board's parser warning).
- Progress notes with pictures and percentages, a withdrawn ask, the user's question and the studio's answer, open asks with
  one-click options, a general thread (`GEN-levels`) with a plain note and an ask.
- A decision log with two lines not relayed yet (`tick.py` flags them), a bundle waiting for the merge button, a requests inbox,
  two ready files, a review pass, and placeholder pictures.

Times are written relative to the moment you run `make_sample.py`, so "stale" and "2 h ago" read the same every time.

## Use it
From `C:/AI/studio-system`:
```
python sample/make_sample.py --config
python board/start.py --config sample/studio-hub/board/board.config.json
python board/tick.py --config sample/studio-hub/board/board.config.json
python board/note.py --config sample/studio-hub/board/board.config.json --open-asks
python board/stop.py --config sample/studio-hub/board/board.config.json
```
Every click on the board writes to these sample files. Run `make_sample.py` again to reset them (it replaces the data files only).
The queue panel uses `queue/resq.py` from the runbook folder and keeps its state in `sample/studio-hub/queue/`.
