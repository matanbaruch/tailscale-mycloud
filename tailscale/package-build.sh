#!/bin/sh
# Build the WD My Cloud .bin for the Tailscale app. Runs INSIDE the Docker
# image (needs mksapkg-OS5 + glibc/libxml2/openssl). Driven by ../build.sh.
#
#   - reads the bundled Tailscale version from apkg.rc (single source of truth)
#   - downloads the official static `arm` build and verifies its SHA-256
#   - packs everything into MyCloudEX2Ultra_tailscale_<ver>.bin
set -e

cd "$(dirname "$0")"            # -> tailscale/
APP_NAME="tailscale"
MODELS="${MODELS:-MyCloudEX2Ultra}"
MKSAPKG="${MKSAPKG:-mksapkg-OS5}"
TS_VERSION="$(awk '/^Version:/{print $2}' apkg.rc)"

if [ -z "$TS_VERSION" ]; then
	echo "ERROR: could not read Version from apkg.rc" >&2
	exit 1
fi
echo "==> Tailscale version: $TS_VERSION"

# 1. Download + verify the official static arm build.
TARBALL="tailscale_${TS_VERSION}_arm.tgz"
URL="https://pkgs.tailscale.com/stable/${TARBALL}"
echo "==> Downloading ${URL}"
wget -q "$URL" -O "/tmp/${TARBALL}"
wget -q "${URL}.sha256" -O "/tmp/${TARBALL}.sha256"

EXPECTED="$(awk '{print $1}' "/tmp/${TARBALL}.sha256")"
ACTUAL="$(sha256sum "/tmp/${TARBALL}" | awk '{print $1}')"
if [ "$EXPECTED" != "$ACTUAL" ]; then
	echo "ERROR: SHA-256 mismatch" >&2
	echo "  expected: $EXPECTED" >&2
	echo "  actual:   $ACTUAL" >&2
	exit 1
fi
echo "==> Checksum OK: $ACTUAL"

# 2. Extract the two binaries we ship.
rm -rf bin /tmp/ts-extract
mkdir -p bin /tmp/ts-extract
tar -xzf "/tmp/${TARBALL}" -C /tmp/ts-extract --strip-components=1
cp /tmp/ts-extract/tailscale /tmp/ts-extract/tailscaled bin/
chmod +x bin/tailscale bin/tailscaled
echo "==> Bundled: $(cd bin && echo *)"

# 3. Make sure the icon exists.
[ -f web/tailscale.png ] || python3 web/make_icon.py web/tailscale.png

# 4. Ensure all package scripts are executable (mksapkg preserves modes).
chmod +x ./*.sh libexec/*.sh cgi-bin/*.py 2>/dev/null || true

# Strip build cruft so it never lands in the package tar.
find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
rm -f apkg.xml apkg.sign

# 5. Pack with the real WD tool. -E = auto-enable after install, -s = self-sign.
for model in $MODELS; do
	echo "==> Packaging for ${model}"
	"$MKSAPKG" -E -s -m "$model"
done

# 6. Collect output. mksapkg writes "<MODEL>_<pkg>_<ver>.bin(MMDDYYYY)" into
#    the parent of this dir (the repo root); rename to drop the date suffix.
RELEASE_DIR="../packages"
mkdir -p "$RELEASE_DIR"
found=0
for f in ../*_"${APP_NAME}"_*.bin*; do
	[ -e "$f" ] || continue
	base="$(basename "$f")"
	clean="${base%.bin*}.bin"
	mv "$f" "${RELEASE_DIR}/${clean}"
	echo "==> ${RELEASE_DIR}/${clean}"
	found=1
done
if [ "$found" -ne 1 ]; then
	echo "ERROR: no .bin produced by mksapkg" >&2
	exit 1
fi

# 7. Hand artifacts back to the host user (container runs as root).
if [ -n "$HOST_UID" ]; then
	chown -R "${HOST_UID}:${HOST_GID:-$HOST_UID}" "$RELEASE_DIR" bin 2>/dev/null || true
fi

echo "==> Build complete."
