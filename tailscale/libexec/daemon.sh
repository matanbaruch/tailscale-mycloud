#!/bin/sh
# Ensure tailscaled is running against the persistent state dir.
# Shared by start.sh (boot/enable) and the CGI (Connect/Restart).
# Usage: daemon.sh [install_dir]
#
# tailscaled persists the node identity + prefs in the state dir, so on boot it
# reconnects on its own with no auth key and no stored flags.
[ -f /tmp/debug_apkg ] && echo "APKG_DEBUG: $0 $* $PWD" >> /tmp/debug_apkg

INSTALL_DIR="${1:-/mnt/HD/HD_a2/Nas_Prog/tailscale}"
STATE_DIR="/mnt/HD/HD_a2/.systemfile/tailscale"
SOCKET="/var/run/tailscale/tailscaled.sock"
TAILSCALED="${INSTALL_DIR}/bin/tailscaled"

mkdir -p "$STATE_DIR"
mkdir -p /var/run/tailscale

# Prefer the kernel tailscale0 interface (needs /dev/net/tun). Fall back to
# userspace networking (outbound only) if TUN is unavailable, and record the
# mode so the UI can warn about it.
if [ ! -c /dev/net/tun ]; then
	mkdir -p /dev/net
	modprobe tun 2>/dev/null
	[ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200 2>/dev/null
fi

TUN_ARGS=""
if [ -c /dev/net/tun ]; then
	echo kernel > "$STATE_DIR/.netmode"
else
	TUN_ARGS="--tun=userspace-networking"
	echo userspace > "$STATE_DIR/.netmode"
fi

# Already running? Use a busybox-friendly ps|grep (pgrep -f isn't always present).
# shellcheck disable=SC2009
if ps 2>/dev/null | grep -v grep | grep -q tailscaled; then
	echo "tailscaled already running"
	exit 0
fi

if [ ! -x "$TAILSCALED" ]; then
	echo "ERROR: tailscaled not found at $TAILSCALED"
	exit 1
fi

# shellcheck disable=SC2086  # TUN_ARGS must word-split (empty = no extra arg)
nohup "$TAILSCALED" --statedir="$STATE_DIR" --socket="$SOCKET" $TUN_ARGS \
	>> "$STATE_DIR/tailscaled.log" 2>&1 &

# Wait for the control socket so a `tailscale up` right after this doesn't race
# the daemon startup (the first Connect would otherwise fail intermittently).
i=0
while [ ! -S "$SOCKET" ] && [ "$i" -lt 15 ]; do
	sleep 1
	i=$((i + 1))
done
if [ -S "$SOCKET" ]; then
	echo "tailscaled started (mode: $(cat "$STATE_DIR/.netmode" 2>/dev/null))"
else
	echo "WARNING: tailscaled started but socket not ready after ${i}s; see $STATE_DIR/tailscaled.log"
fi
exit 0
