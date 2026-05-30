#!/bin/sh
# Revert the init step (remove dashboard symlinks). Identity/state untouched.
[ -f /tmp/debug_apkg ] && echo "APKG_DEBUG: $0 $*" >> /tmp/debug_apkg

rm -f /var/www/cgi-bin/tailscale.py
rm -rf /var/www/apps/tailscale
exit 0
