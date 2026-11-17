"""Start the studio board in the background (no console window). Idempotent: if this board already answers on its port, it only
prints the URL. It never stops or replaces another program.

  python start.py [--config PATH] [--port N]

Log: server.log next to this file (or next to --config's board folder); pid: server.pid there.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import server as S  # noqa: E402


def health(port, app, timeout=1.0):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/health" % port, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
            return j if j.get("app") == app else None
    except Exception:  # noqa
        return None


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main():
    args = sys.argv[1:]
    cfg = args[args.index("--config") + 1] if "--config" in args else None
    port = int(args[args.index("--port") + 1]) if "--port" in args else None
    c = S.load_config(cfg, port)
    port, app = c["port"], c["app_id"]
    rundir = os.path.dirname(c["config_file"])
    pidf, logf = os.path.join(rundir, "server.pid"), os.path.join(rundir, "server.log")
    h = health(port, app)
    if h:
        print("already running (pid %s): http://127.0.0.1:%d/" % (h.get("pid"), port))
        return 0
    if not port_free(port):
        print("port %d is taken by another program; set another port in board.config.json or pass --port" % port)
        return 1
    cmd = [sys.executable, "-B", os.path.join(HERE, "server.py"), "--config", c["config_file"], "--port", str(port)]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
    log = open(logf, "ab")
    proc = None
    for extra in ((breakaway, 0) if breakaway else (0,)):
        try:
            proc = subprocess.Popen(cmd, cwd=rundir, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                    creationflags=flags | extra, close_fds=True,
                                    start_new_session=(os.name != "nt"))
            break
        except OSError:
            proc = None   # breakaway not allowed by the job: retry without it
    log.close()
    if proc is None:
        print("could not start the board; see", logf)
        return 1
    with open(pidf, "w") as f:
        f.write(str(proc.pid))
    for _ in range(40):
        time.sleep(0.25)
        if health(port, app):
            print("started (pid %d): http://127.0.0.1:%d/" % (proc.pid, port))
            return 0
        if proc.poll() is not None:
            break
    print("the board did not answer; see", logf)
    return 1


if __name__ == "__main__":
    sys.exit(main())
