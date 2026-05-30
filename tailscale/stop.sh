#!/bin/sh
# Disable / shutdown: stop the daemon but keep the node identity (state dir).
[ -f /tmp/debug_apkg ] && echo "APKG_DEBUG: $0 $*" >> /tmp/debug_apkg

killall tailscaled 2>/dev/null

# Wait for it to actually exit before returning. The WD framework runs stop.sh
# then start.sh on a disable->enable (and our Restart does the same); if we
# returned while tailscaled was still terminating, daemon.sh would see the dying
# process, think it's "already running", skip the relaunch -- and the service
# would end up DOWN. So we block until the process is gone, escalating to
# SIGKILL if it lingers. busybox-friendly ps|grep (pgrep -f isn't always present).
i=0
# shellcheck disable=SC2009
while [ "$i" -lt 10 ] && ps 2>/dev/null | grep -v grep | grep -q tailscaled; do
	sleep 1
	i=$((i + 1))
done
# shellcheck disable=SC2009
if ps 2>/dev/null | grep -v grep | grep -q tailscaled; then
	killall -9 tailscaled 2>/dev/null
	sleep 1
fi
exit 0
