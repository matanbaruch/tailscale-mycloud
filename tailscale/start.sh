#!/bin/sh
# Enable / boot: start the Tailscale daemon. $1 = installed app path.
[ -f /tmp/debug_apkg ] && echo "APKG_DEBUG: $0 $* $PWD" >> /tmp/debug_apkg

APKG_PATH=$(readlink -f "$1")
"${APKG_PATH}/libexec/daemon.sh" "${APKG_PATH}"
exit 0
