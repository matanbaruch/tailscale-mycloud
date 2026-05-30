#!/bin/sh
# Uninstall: log the node out of the tailnet (best effort), then purge
# binaries, state and dashboard symlinks. $1 = installed app path.
[ -f /tmp/debug_apkg ] && echo "APKG_DEBUG: $0 $*" >> /tmp/debug_apkg

INSTALL_DIR="${1:-/mnt/HD/HD_a2/Nas_Prog/tailscale}"
STATE_DIR="/mnt/HD/HD_a2/.systemfile/tailscale"
SOCKET="/var/run/tailscale/tailscaled.sock"

# Best-effort logout so a stale node doesn't linger in the tailnet.
if [ -x "${INSTALL_DIR}/bin/tailscale" ]; then
	"${INSTALL_DIR}/bin/tailscale" --socket="$SOCKET" logout 2>/dev/null
fi
killall tailscaled 2>/dev/null

rm -rf "$INSTALL_DIR"
rm -rf "$STATE_DIR"
rm -f /var/www/cgi-bin/tailscale.py
rm -rf /var/www/apps/tailscale
exit 0
