"""Mark register items as shipped in a build (LIVE), or send one the build reverted back to work. The manager runs it after a build.

  python mark_live.py <build label> [--round R] <ID> [<ID> ...] [--force]
  python mark_live.py <build label> [--round R] --revert-to-work <ID> --reason "..."

LIVE:   status -> 'LIVE (<label>[, <round>] <MM-DD>)', handoff: filled if empty. Only ACCEPTED / HANDOFF items unless --force.
Revert: status -> 'APPROVED, IN WORK (reverted in <label>: <reason>)'.
Each change is a safe single-block write of the register (re-read, temp + os.replace, line endings kept) and one line in the
decision log (action "live" / "revert"). The label is free text: a build name, a version, or a date for projects that ship
continuously. Status words follow board.config.json.
"""
import argparse
import datetime as dt
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as S  # noqa: E402


def clean(s):
    return " ".join(str(s or "").replace("(", "[").replace(")", "]").replace("—", "-").split())


def rewrite(bid, check, new_status, fill_handoff=None, tries=3):
    """one block: re-read, check, rewrite the header (+ handoff), write; retries if the file moved under us"""
    for attempt in range(tries):
        text, meta = S.read_file(S.CFG["paths"]["register"])
        blocks = [b for b in S.parse_register(text)["blocks"] if b["id"] == bid]
        if not blocks:
            return None, "not in the register"
        if len(blocks) > 1:
            return None, "duplicate id in the register"
        b = blocks[0]
        err = check(b)
        if err:
            return b, err
        lines = text[b["start"]:b["end"]].splitlines(keepends=True)
        S.set_status(lines, new_status)
        if fill_handoff and not b["fields"].get("handoff", "").strip():
            S.set_field(lines, meta["eol"], "handoff", fill_handoff)
        try:
            S.write_file(S.CFG["paths"]["register"], text[:b["start"]] + "".join(lines) + text[b["end"]:], meta)
            return b, None
        except S.Conflict:
            if attempt == tries - 1:
                return b, "the register kept changing while writing; try again"
    return None, "not written"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("label", help="build label, e.g. v12 or 2026-11-18")
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--round", default="", help="build round, e.g. r15 (optional)")
    ap.add_argument("--force", action="store_true", help="also items that are not ACCEPTED / HANDOFF")
    ap.add_argument("--revert-to-work", metavar="ID", help="send this item back to APPROVED, IN WORK")
    ap.add_argument("--reason", default="", help="why the build reverted it (with --revert-to-work)")
    ap.add_argument("--config", default=None)
    a = ap.parse_intermixed_args()
    S.load_config(a.config)
    W = S.W
    label, rnd = clean(a.label), clean(a.round)
    now = dt.datetime.now()

    if a.revert_to_work:
        reason = clean(a.reason)
        if not reason:
            print("--reason is needed with --revert-to-work", file=sys.stderr)
            return 2
        status = "%s, %s (reverted in %s: %s)" % (W("APPROVED"), W("IN WORK"), label, reason)
        ok_stages = ("LIVE", "ACCEPTED", "HANDOFF")
        b, err = rewrite(a.revert_to_work, lambda b: None if (a.force or b["stage"] in ok_stages) else
                         "is %s, not %s / %s / %s (use --force)" % (b["status"], W("LIVE"), W("ACCEPTED"), W("HANDOFF")), status)
        if err:
            print("%s: %s" % (a.revert_to_work, err), file=sys.stderr)
            return 1
        S.log_decision({"ts": now.isoformat(timespec="seconds"), "id": b["id"], "studio": b["studio"], "action": "revert",
                        "comment": reason, "status": status, "title": b["title"], "build": label})
        print("%s: %s -> %s" % (b["id"], b["status"], status))
        return 0

    if not S.enabled("LIVE"):
        print("LIVE is switched off in board.config.json; nothing to mark", file=sys.stderr)
        return 2
    if not a.ids:
        print("give one or more IDs (or --revert-to-work ID --reason ...)", file=sys.stderr)
        return 2
    where = ", ".join(x for x in (label, (rnd + " " if rnd else "") + now.strftime("%m-%d")) if x)
    status = "%s (%s)" % (W("LIVE"), where)
    handoff = "live in %s (%s%s, mark_live)" % (label, (rnd + ", ") if rnd else "", now.strftime("%Y-%m-%d %H:%M"))
    bad = 0
    for bid in a.ids:
        b, err = rewrite(bid, lambda b: None if (a.force or b["stage"] in ("ACCEPTED", "HANDOFF")) else
                         "is %s, not %s / %s (use --force)" % (b["status"], W("ACCEPTED"), W("HANDOFF")), status, fill_handoff=handoff)
        if err:
            print("%s: SKIPPED, %s" % (bid, err), file=sys.stderr)
            bad += 1
            continue
        S.log_decision({"ts": dt.datetime.now().isoformat(timespec="seconds"), "id": b["id"], "studio": b["studio"],
                        "action": "live", "comment": "", "status": status, "title": b["title"], "build": label})
        print("%s: %s -> %s" % (b["id"], b["status"], status))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
