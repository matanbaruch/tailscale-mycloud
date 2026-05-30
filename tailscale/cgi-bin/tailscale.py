#!/usr/bin/env python3
"""Dashboard CGI for the Tailscale My Cloud app.

GET  -> live status (text/plain).
POST -> an ``action``: up / down / logout / set_autoupdate / restart.

Security: the auth key is consumed to build the ``tailscale up`` argv and is
never echoed back to the page or written to a log. All commands run via
argument lists (no shell), so form input cannot inject extra commands.

We deliberately do NOT use ``cgitb``: its tracebacks dump local variables (which
include the auth key) into the HTTP response on any unhandled error. Instead the
dispatcher catches everything and prints a one-line, key-free message.
"""

import cgi
import os
import subprocess
import sys

# Resolve symlinks: this file is symlinked into /var/www/cgi-bin/, but tslib.py
# lives next to the real file in the install dir. realpath finds it there.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import tslib  # noqa: E402

INSTALL_DIR = "/mnt/HD/HD_a2/Nas_Prog/tailscale"
STATE_DIR = "/mnt/HD/HD_a2/.systemfile/tailscale"
SOCKET = "/var/run/tailscale/tailscaled.sock"
BIN_DIR = INSTALL_DIR + "/bin"
TAILSCALE = BIN_DIR + "/tailscale"
DAEMON = INSTALL_DIR + "/libexec/daemon.sh"

os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ.get("PATH", "")

UP_FIELDS = (
    "authkey",
    "hostname",
    "accept_routes",
    "ssh",
    "accept_dns",
)


def emit_headers():
    print("Content-type: text/plain; charset=utf-8")
    print("")


def out(text=""):
    print(text)


def run(cmd, timeout=120):
    """Run a command; return (returncode, combined stdout+stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        # NOTE: do not surface the exception object -- its repr includes the full
        # cmd list (with the auth key). Report only the safe binary path.
        return 124, "command timed out\n"
    except OSError as exc:
        return 127, f"could not run {cmd[0]}: {exc.strerror or exc.errno}\n"


def ts(*args, timeout=60):
    """Run the tailscale CLI against our socket."""
    return run([TAILSCALE, "--socket=" + SOCKET, *args], timeout=timeout)


def read_text(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def daemon_running():
    rc, _ = run(["sh", "-c", "ps 2>/dev/null | grep -v grep | grep -q tailscaled"], timeout=10)
    return rc == 0


def ensure_daemon():
    return run([DAEMON, INSTALL_DIR], timeout=30)


def show_status():
    out("=== Tailscale on WD My Cloud EX2 Ultra ===")
    out(f"daemon_running: {'yes' if daemon_running() else 'no'}")

    netmode = read_text(STATE_DIR + "/.netmode") or "unknown"
    out(f"network_mode: {netmode}")
    if netmode == "userspace":
        out(
            "WARNING: kernel TUN unavailable -> userspace networking. The NAS can "
            "reach the tailnet (outbound) but is NOT directly reachable at its "
            "100.x address. See the README troubleshooting section."
        )

    _, ver = ts("version", timeout=15)
    out("\n--- version ---")
    out(ver.strip())

    _, ip4 = ts("ip", "-4", timeout=15)
    out("\n--- tailscale IPv4 ---")
    out(ip4.strip() or "(not connected)")

    _, status = ts("status", timeout=30)
    out("\n--- status ---")
    out(status.strip() or "(no status; not connected)")


def handle_up(form):
    params = {k: form.getfirst(k, "") for k in UP_FIELDS}
    try:
        cmd = tslib.build_up_command(params, tailscale_bin=TAILSCALE, socket=SOCKET)
    except tslib.ValidationError as exc:
        out(f"ERROR: {exc}")
        return

    # Make sure the daemon is up before we try to talk to it.
    ensure_daemon()

    rc, output = run(cmd, timeout=180)
    # NOTE: never print `cmd` -- it contains the auth key. Show tailscale's output only.
    if output.strip():
        out(output.strip())
    out(f"\n[connect {'OK' if rc == 0 else f'FAILED rc={rc}'}]")


def dispatch():
    method = os.environ.get("REQUEST_METHOD", "GET").upper()
    form = cgi.FieldStorage()

    if method != "POST":
        show_status()
        return

    action = form.getfirst("action", "")
    if action == "up":
        handle_up(form)
    elif action == "down":
        _, o = ts("down", timeout=30)
        out(o.strip() or "Disconnected (node stays logged in).")
    elif action == "logout":
        _, o = ts("logout", timeout=30)
        out(o.strip() or "Logged out of the tailnet.")
    elif action == "set_autoupdate":
        value = "true" if tslib._truthy(form.getfirst("value", "")) else "false"
        rc, o = ts("set", "--auto-update=" + value, timeout=30)
        out(o.strip() or f"auto-update set to {value}")
        if rc != 0 and not o.strip():
            out("(auto-update may not be supported for a manual static install)")
    elif action == "restart":
        _, o = ensure_daemon()
        out(o.strip() or "Service restart requested.")
    else:
        out(f"unknown action: {action!r}")


def main():
    # Headers first so a later error still produces a valid CGI response.
    emit_headers()
    try:
        dispatch()
    except Exception as exc:  # noqa: BLE001  -- never dump a traceback (would leak the key)
        out(f"error: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
