stamp: <YYYY-MM-DDTHH:MM> (<round>, NOT final until the handover call ~{{HANDOVER}})
accepted:
  <ID> <title>: user ACCEPTED <date time> "<the user's words, incl. the pick>" (web tool / relayed by the {{TERM_MANAGER}}).
    Sheets: <proposal picture> (proposal), <result sheet> ({{TERM_RESULT}}).

already live: <what is already installed in the shared files, so the {{TERM_BUILD}} only rebuilds; "nothing" if none>

apply tonight:
 1. <ID> (<pick>):
  python <studio installer> --opt <pick>            (dry run <time>: exit 0, <N> files would change)
  python <studio installer> --opt <pick> --apply    (backup in studios/<key>/backup/<stamp>/; log the stamp in RESUME_BUILD.md)
  revert <ID> alone: python <studio installer> --revert <stamp>   (byte for byte; then <describe the steps to re-run>)
  What it installs: <files touched and what changes in them>
  Depends on / stacks on: <other items, or "independent">

build-script changes: <edits to this round's own copies of the build scripts, or "none">

check:
  - <where to look> : expected <numbers>; worse = <what a regression looks like>
  - side effects: <what else changes, or "nothing else changes">

not ready: <work in progress the {{TERM_BUILD}} must NOT take, with the reason (not accepted yet / not checked)>
