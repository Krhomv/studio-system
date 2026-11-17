"""Project-specific checks for tick.py. Edit this file per project; tick.py calls checks(ctx) on every tick.

ctx keys: cfg (resolved board config), now (epoch s), server (the server module: read_file, parse_register, ...),
queue (the resq module or None), blocks (parsed register blocks), building (True while BUILD_RUNNING exists),
flags (the flags tick.py found so far, read-only).
Return a list of flag strings (without the leading "FLAG "). Keep each check fast (a few seconds) and read-only.

Examples of checks other projects added (write your own; delete what you don't need):
- a stale marker file left by a crashed job (marker names a pid that is dead) -> "BUSY stale marker <dir>"
- which desktop apps hold the GPU memory while the queue's gate is shut -> "GATE apps: <name> <MB>, ... -> tell the user"
- a shared settings file that a test run left changed -> "CONFIG <file> differs from its snapshot"
- the published product older than the last build marker -> "BUILD output missing for <label>"
"""
import os


def checks(ctx):
    flags = []
    cfg = ctx["cfg"]
    # Example: warn when a studio folder has no NOTES.md (every studio keeps one).
    studios_dir = os.path.join(cfg["root"], "studios")
    for s in cfg["studios"]:
        if os.path.isdir(os.path.join(studios_dir, s["key"])) and not os.path.isfile(os.path.join(studios_dir, s["key"], "NOTES.md")):
            flags.append("LOCAL studios/%s has no NOTES.md" % s["key"])
    return flags
