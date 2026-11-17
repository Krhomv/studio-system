"""Approved / in-work tasks per studio, in the user's priority order (P1 urgent .. P4 low; no priority line = the default).

  python prio.py [--studio <key>] [--config PATH]      (ties: older task first, i.e. earlier in the register)
"""
import argparse
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--studio", default="", help="only this studio (key, owner name or prefix)")
    ap.add_argument("--config", default=None)
    a = ap.parse_args()
    S.load_config(a.config)
    text, _ = S.read_file(S.CFG["paths"]["register"])
    blocks = [b for b in S.parse_register(text)["blocks"] if b["stage"] in ("APPROVED", "IN WORK")]
    if a.studio:
        st = S.studio_by(key=a.studio) or S.studio_by(owner=a.studio) or S.studio_by(prefix=a.studio)
        if not st:
            print("no studio '%s' in the config (keys: %s)" % (a.studio, ", ".join(s["key"] for s in S.CFG["studios"])), file=sys.stderr)
            return 2
        blocks = [b for b in blocks if b["skey"] == st["key"]]
    by = {}
    for b in blocks:
        by.setdefault(b["studio"], []).append(b)
    names = S.CFG["priority"]["names"]
    for studio in sorted(by):
        print(studio)
        for b in sorted(by[studio], key=lambda x: (x["priority"], x["line"])):
            print("  P%d %-7s %-10s %-8s %s" % (b["priority"], names.get(b["priority"], ""), b["id"], b["stage"], b["title"][:90]))
    print("%d approved / in-work task(s)" % len(blocks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
