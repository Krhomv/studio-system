"""Stop the studio board: only the pid written in server.pid, and only if that pid is this board answering on its port.

  python stop.py [--config PATH] [--port N]

Never restart or stop the board while the user may be using it (deciding, typing an answer): ask first.
"""
import json
import os
import signal
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import server as S  # noqa: E402


def main():
    args = sys.argv[1:]
    cfg = args[args.index("--config") + 1] if "--config" in args else None
    port = int(args[args.index("--port") + 1]) if "--port" in args else None
    c = S.load_config(cfg, port)
    pidf = os.path.join(os.path.dirname(c["config_file"]), "server.pid")
    if not os.path.exists(pidf):
        print("no server.pid; nothing to stop")
        return 0
    pid = int(open(pidf).read().strip() or 0)
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/health" % c["port"], timeout=2) as r:
            h = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa
        h = None
    if h and h.get("app") == c["app_id"] and h.get("pid") != pid:
        print("port %d is served by pid %s, not server.pid %d; not stopping anything" % (c["port"], h.get("pid"), pid))
        return 1
    if not h or h.get("app") != c["app_id"]:
        print("the board does not answer on port %d; server.pid %d is stale, removed (nothing killed)" % (c["port"], pid))
        os.remove(pidf)
        return 0
    try:
        os.kill(pid, signal.SIGTERM)   # TerminateProcess on Windows
        print("stopped pid %d" % pid)
    except OSError as e:
        print("could not stop pid %d: %s" % (pid, e))
        return 1
    os.remove(pidf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
