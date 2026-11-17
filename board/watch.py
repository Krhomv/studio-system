"""Decisions watcher for the manager's Monitor: prints each new line of the decision log after the relayed cursor, as it arrives,
then exits after --minutes (so Monitor loops never pile up as orphans). Re-arm it each time it ends.

  python watch.py [--minutes 30] [--config PATH] [--all]

Each printed line is one user action to relay (quote the user's words and time). 'live' / 'revert' lines come from mark_live.py
and need no relay; they are skipped unless --all. After relaying, run `python tick.py --relayed` to move the cursor.
Lines already printed by this run are not printed again; a new run starts again from the cursor.
"""
import argparse
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as S  # noqa: E402


def fmt(line):
    try:
        d = json.loads(line)
    except ValueError:
        return "DECISION (unparsed) " + line.strip()[:300]
    act = d.get("action", "?")
    words = str(d.get("comment") or "").strip()
    extra = ""
    if act == "priority":
        extra = " %s -> %s" % (d.get("from", "?"), d.get("to", "?"))
    if act == "answer":
        extra = " (to ask %s)" % d.get("reply_to", "?")
    return "DECISION %s %s %s%s | %s | status: %s | words: %s" % (
        str(d.get("ts", ""))[:16].replace("T", " "), d.get("id", "?"), act, extra, d.get("studio", "?"),
        d.get("status", ""), ('"%s"' % words[:300]) if words else "(none)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutes", type=float, default=30.0)
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--all", action="store_true", help="also print live / revert lines")
    ap.add_argument("--config", default=None)
    a = ap.parse_args()
    S.load_config(a.config)
    path = S.CFG["paths"]["decisions"]
    seen = S.relayed_cursor()
    end = time.time() + a.minutes * 60
    print("watching %s from line %d for %g min" % (os.path.basename(path), seen, a.minutes), flush=True)
    while time.time() < end:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = [x for x in f.read().splitlines() if x.strip()]
        except OSError:
            lines = []
        if len(lines) < seen:      # log rotated / cursor reset
            seen = 0
        for ln in lines[seen:]:
            if not a.all and ('"action": "live"' in ln or '"action": "revert"' in ln):
                continue
            print(fmt(ln), flush=True)
        seen = max(seen, len(lines))
        time.sleep(a.interval)
    print("watch ended after %g min: re-arm it" % a.minutes, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
