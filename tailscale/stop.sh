#!/bin/sh
# Disable / shutdown: stop the daemon but keep the node identity (state dir).
[ -f /tmp/debug_apkg ] && echo "APKG_DEBUG: $0 $*" >> /tmp/debug_apkg

killall tailscaled 2>/dev/null
exit 0
