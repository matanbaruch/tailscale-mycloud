#!/bin/sh
# Pre-install backup tasks (none needed for Tailscale).
[ -f /tmp/debug_apkg ] && echo "APKG_DEBUG: $0 $*" >> /tmp/debug_apkg
exit 0
