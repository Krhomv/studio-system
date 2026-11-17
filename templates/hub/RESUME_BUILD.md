# <rNN> resume file (<label>)

Updated after every step. A fresh {{TERM_BUILD}} agent reads this first and continues at NEXT. Times are local.

NEXT: <the exact next step, with its command>

## State
- BUILD_RUNNING: <present since HH:MM / removed HH:MM>
- Queue: owner `build-<rNN>`; lock <held / released>
- Usage at start: <N %>; last check <time> <N %>

## Done
| Time | Step | Result | Backup / revert stamp | Log |
|---|---|---|---|---|
| <HH:MM> | <owner> <ID> dry run | exit 0 | - | <path> |
| <HH:MM> | <owner> <ID> --apply | exit 0 | <stamp> | <path> |

## Running in the background
- <process / pid / log path / what "done" looks like / the watcher that fires on it>

## Problems
- <time> <what happened, what was done, what is left>
