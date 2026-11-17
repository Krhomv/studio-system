"""Progress notes, answers and questions to the user (studios). Append-only; never touches the register.

  python note.py <ID> "what changed / what's next" [--pct 40] [--img path ...] [--by <owner>] [--answer]
  python note.py <ID> "question for the user" --ask --img <picture> [--options "A|B|C"]
  python note.py GEN-<key> "question that belongs to no task" --ask --img <picture> [--options "A|B"]
  python note.py GEN-<key> "announcement"                 (plain note on the studio's general thread)
  python note.py <ID> --withdraw <ask id> [--reason "..."]
  python note.py <ID> --show
  python note.py --open-asks

Notes go to <progress>/<ID>.jsonl, one JSON line each: {ts, nid, by, pct, note, images[, answer][, kind][, options][, reply_to]}.
--answer   marks the note as your answer to the user's question (any later note also closes the question).
--ask      posts a question TO the user in the task's thread; the card shows "waiting for your answer" until the user replies on
           the board. --options gives one-click answers (put your recommended pick first); free text stays possible.
           Every ask should carry a picture (--img).
GEN-<key>  is a studio's general thread (key or owner name from board.config.json), for questions that belong to no task.
--withdraw closes one of YOUR open asks (e.g. re-posted, no longer needed): shown "withdrawn", never a user answer.
--show     prints the task's notes, your asks (with their ids) and the user's questions / replies ("USER REPLIED").
--open-asks prints every unanswered ask (id, studio, age, ask id, text).
Images: jpg / png / webp / gif inside the project, relative to the project root or one of the config's image_bases.
Config: --config, else env STUDIO_BOARD_CONFIG, else board.config.json next to this file.
"""
import argparse
import datetime as dt
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as S  # noqa: E402  (shared parser and rules; importing does not start a server)


def age(ts):
    try:
        m = int((dt.datetime.now() - dt.datetime.fromisoformat(ts[:19])).total_seconds() // 60)
    except ValueError:
        return "?"
    return "%d min" % m if m < 60 else "%d h %02d" % (m // 60, m % 60)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", nargs="?", default="")
    ap.add_argument("text", nargs="?", default="")
    ap.add_argument("--pct", type=float, default=None, help="0-100, progress estimate")
    ap.add_argument("--img", nargs="+", default=[], help="image path(s)")
    ap.add_argument("--by", default=None, help="your owner name (default: the task's owner)")
    ap.add_argument("--answer", action="store_true", help="this note answers the user's question")
    ap.add_argument("--ask", action="store_true", help="this note is a question to the user")
    ap.add_argument("--options", default="", help='one-click answers for --ask, e.g. "keep|lighter|darker"')
    ap.add_argument("--withdraw", metavar="ASK_ID", default="", help="close your own open ask (id from --show / --open-asks)")
    ap.add_argument("--reason", default="", help="why the ask is withdrawn (with --withdraw)")
    ap.add_argument("--show", action="store_true", help="print the task's notes and the user's questions")
    ap.add_argument("--open-asks", action="store_true", help="print every unanswered question to the user")
    ap.add_argument("--config", default=None, help="board.config.json")
    a = ap.parse_args()
    S.load_config(a.config)
    text, _ = S.read_file(S.CFG["paths"]["register"])
    all_blocks = S.parse_register(text)["blocks"]

    if a.open_asks:
        dec, cur = S.read_decisions(), S.relayed_cursor()
        blocks = [dict(id=b["id"], title=b["title"], progress=S.progress_summary(b["id"], dec, cur)) for b in all_blocks]
        gens = [dict(id=g, title="general", general=True, progress=S.progress_summary(g, dec, cur)) for g in S.gen_threads()]
        asks = S.collect_open_asks(blocks, gens)
        for q in asks:
            opts = ("  [%s]" % " | ".join(q["options"])) if q["options"] else ""
            print("%-12s %-18s %8s  [%s]  %s%s" % (q["id"], q["studio"], age(q["ts"]), q["nid"], q["note"], opts))
        print("%d open ask(s)" % len(asks))
        return 0

    if not a.id:
        print("give a task ID (or --open-asks)", file=sys.stderr)
        return 2
    if S.GEN_RE.match(a.id):
        st = S.gen_studio(a.id)
        if not st:
            print("%s: no configured studio '%s'. Use GEN-<key> with one of: %s" % (
                a.id, a.id[4:], ", ".join(s["key"] for s in S.CFG["studios"])), file=sys.stderr)
            return 2
        b = {"id": a.id, "studio": st["owner"], "title": "general thread", "status": "general"}
    else:
        blocks = [x for x in all_blocks if x["id"] == a.id]
        if not blocks:
            print("no task %s in %s\nknown ids: %s (or GEN-<key> for a general thread)" % (
                a.id, S.CFG["paths"]["register"], ", ".join(x["id"] for x in all_blocks)), file=sys.stderr)
            return 2
        b = blocks[0]
    by = (a.by or b["studio"]).strip()[:60]
    if by.lower() == "user":
        print("--by user is reserved for the user", file=sys.stderr)
        return 2

    if a.withdraw:
        dec, cur = S.read_decisions(), S.relayed_cursor()
        asks = [n for n in S.progress_summary(a.id, dec, cur)["notes"] if n.get("kind") == "ask" and n["nid"] == a.withdraw]
        if not asks:
            print("no ask %s in %s (ids: note.py %s --show, or --open-asks)" % (a.withdraw, a.id, a.id), file=sys.stderr)
            return 2
        ask = asks[0]
        if ask["by"] != by:
            print("that ask is %s's, not %s's: you withdraw only your own asks (--by)" % (ask["by"], by), file=sys.stderr)
            return 2
        if ask["ask_state"] != "open":
            print("that ask is already %s" % ask["ask_state"], file=sys.stderr)
            return 2
        rec = S.append_note(a.id, by, None, " ".join(a.reason.split())[:1000], [], kind="withdraw", reply_to=ask["nid"])
        print("withdrew %s on %s  %s" % (ask["nid"], a.id, rec["ts"]))
        return 0

    if a.show:
        notes = S.read_notes(a.id)
        print("%s  %s  %s  [%s]  %d note(s)" % (b["id"], b["studio"], b["title"], b["status"], len(notes)))
        for n in reversed(notes):
            pct = "" if n["pct"] is None else "  %d%%" % n["pct"]
            if n["by"] == "user":
                who = "USER REPLIED (to %s)" % n["reply_to"] if n.get("kind") == "reply" else "USER ASKED"
            elif n.get("kind") == "ask":
                who = "%s ASKS USER [id %s]" % (n["by"], n["nid"])
            elif n.get("kind") == "withdraw":
                who = "%s WITHDREW ask %s" % (n["by"], n["reply_to"])
            else:
                who = ("%s ANSWER" % n["by"]) if n.get("answer") else n["by"]
            opts = ("  [%s]" % " | ".join(n["options"])) if n.get("options") else ""
            print("- %s  %s%s: %s%s" % (n["ts"].replace("T", " ")[:19], who, pct, n["note"], opts))
            for im in n["images"]:
                print("    img %s%s" % (im["raw"], "" if im["rel"] else "  (not found)"))
        return 0

    note = " ".join((a.text or "").split())
    if a.ask and not note:
        print("--ask needs the question text", file=sys.stderr)
        return 2
    if a.ask and a.answer:
        print("--ask and --answer don't go together", file=sys.stderr)
        return 2
    options = [o.strip()[:120] for o in a.options.split("|") if o.strip()][:8] if a.options else []
    if options and not a.ask:
        print("--options only goes with --ask", file=sys.stderr)
        return 2
    if not note and a.pct is None and not a.img:
        print("nothing to add: give a text, --pct or --img", file=sys.stderr)
        return 2
    pct = None
    if a.pct is not None:
        if not 0 <= a.pct <= 100:
            print("--pct must be 0-100", file=sys.stderr)
            return 2
        pct = int(round(a.pct))
    imgs = []
    for p in a.img:
        rel = S.resolve_image(p)
        if not rel:
            print("image refused (missing, not jpg/png/webp/gif, or outside the project): %s" % p, file=sys.stderr)
            return 2
        imgs.append(rel)
    if a.ask and not imgs:
        print("note: this ask has no picture (--img). The user decides from pictures; add one when you can.", file=sys.stderr)
    rec = S.append_note(a.id, by, pct, note[:4000], imgs, answer=a.answer, kind="ask" if a.ask else None, options=options or None)
    verb = "asked the user on" if a.ask else ("answered" if a.answer else "noted")
    print("%s %s  %s%s  %d image(s)%s  [id %s]" % (verb, a.id, rec["ts"], "" if pct is None else "  %d%%" % pct, len(imgs),
                                                  ("  options: " + " | ".join(options)) if options else "", rec["nid"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
