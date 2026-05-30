# Tailscale for WD My Cloud EX2 Ultra

[![CI](https://github.com/matanbaruch/tailscale-mycloud/actions/workflows/ci.yml/badge.svg)](https://github.com/matanbaruch/tailscale-mycloud/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/matanbaruch/tailscale-mycloud?sort=semver)](https://github.com/matanbaruch/tailscale-mycloud/releases/latest)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-blue.svg)](LICENSE)

A **[Tailscale](https://tailscale.com)** app for the **Western Digital My Cloud EX2 Ultra** (firmware OS 5).
Install it the normal WD way — upload a `.bin` from the dashboard's **Apps → Install Manually** page —
then paste your auth key and control the connection from a built-in web page.

> **Heads-up / honesty note:** this package is built and verified on a Linux/Docker toolchain, but the
> maintainer cannot execute it on physical NAS hardware in CI. "Builds and unpacks correctly" is verified;
> "runs on your device" is your final test. See [Troubleshooting](#troubleshooting) for on-device debugging.

---

## What you get

A web page inside the My Cloud dashboard (**Apps → Tailscale**) with:

- **Auth key field** — paste a Tailscale auth key (`tskey-…`) to connect the NAS to your tailnet.
- **Connect / Disconnect / Logout / Restart** controls.
- **Live status** — `tailscale status`, the node's `100.x` IP, version, and network mode.
- Capability toggles:
  - **Accept subnet routes** (`--accept-routes`)
  - **Tailscale SSH** (`--ssh`)
  - **Exit node** (`--advertise-exit-node`, enables IP forwarding)
  - **Subnet router** (`--advertise-routes=<CIDR>`, enables IP forwarding)
  - **Auto-update** (`tailscale set --auto-update`)

State (your node's identity) is stored on the **persistent data volume**, so it survives reboots.
You only enter an auth key **once**.

## Install (on the NAS)

1. Download the latest `MyCloudEX2Ultra_tailscale_*.bin` from the
   [**Releases**](https://github.com/matanbaruch/tailscale-mycloud/releases/latest) page.
2. In the My Cloud dashboard go to **Apps**, click **Install an app manually** (per
   [WD's OS5 manual-install guide](https://support-en.wd.com/app/answers/detailweb/a_id/29960)),
   and choose the `.bin`.
3. Open **Apps → Tailscale**, paste your auth key (generate one at
   [login.tailscale.com → Settings → Keys](https://login.tailscale.com/admin/settings/keys)),
   pick any toggles, and click **Connect**.
4. The NAS appears in your tailnet; reach it at its `100.x.y.z` address from any other tailnet device.

## Build from source

Requires **Docker** (the WD packaging tool `mksapkg-OS5` is Linux x86-64 and runs inside the build image).

```sh
./build.sh
# → packages/MyCloudEX2Ultra_tailscale_<version>.bin
```

The bundled Tailscale version is the single source of truth in [`tailscale/apkg.rc`](tailscale/apkg.rc)
(`Version:`). `build.sh` downloads the official static `arm` build for that version from
`pkgs.tailscale.com`, **verifies its SHA-256**, packs it, and emits the `.bin`.

### Run the tests

```sh
pip install pytest && pytest        # unit tests for the CGI logic (validators + arg building)
sh tests/test_package.sh packages/MyCloudEX2Ultra_tailscale_<version>.bin   # post-build round-trip
```

## How it works

WD My Cloud apps are `.bin` files: a **200-byte APKG header** (product/model IDs + self-signature)
followed by a **gzipped tar**. The header is produced by WD's `mksapkg` tool — we use the real one
([`mksapkg-OS5`](mksapkg-OS5), vendored from [WDCommunity/wdpksrc](https://github.com/WDCommunity/wdpksrc),
BSD-3) inside Docker rather than reimplementing the header (a single wrong ID = "incompatible device").

| Path on device | Purpose |
| --- | --- |
| `/mnt/HD/HD_a2/Nas_Prog/tailscale/` | installed app (binaries + scripts) — persistent |
| `/mnt/HD/HD_a2/.systemfile/tailscale/` | `tailscaled` state dir + logs — persistent |
| `/var/run/tailscale/tailscaled.sock` | control socket |
| `/var/www/apps/tailscale/`, `/var/www/cgi-bin/tailscale.py` | the dashboard UI (symlinked by `init.sh`) |

The package lifecycle scripts (`install/init/start/stop/clean/remove`) follow the WD app convention.
`tailscaled` runs against the persistent state dir and **auto-reconnects on boot** with no stored key.

## Troubleshooting

- **Enable SSH** on the NAS (Settings → Network → SSH), then SSH in as `root`/`sshd`.
- Turn on script tracing: `touch /tmp/debug_apkg` (the lifecycle scripts log to it).
- Daemon logs: `cat /mnt/HD/HD_a2/.systemfile/tailscale/tailscaled.log`
- Status from the shell: `/mnt/HD/HD_a2/Nas_Prog/tailscale/bin/tailscale status`
- **`tailscale0`/TUN unavailable:** if the kernel lacks `/dev/net/tun`, the app falls back to
  **userspace networking** (outbound-only) and shows a warning on the status page. In that mode the
  NAS can reach the tailnet but is not directly reachable at its `100.x` address.

## Caveats & security

- The auth key is sent to the device's local CGI to run `tailscale up`; it is **never echoed back** or
  written to the page. The key authenticates the node once — afterwards only the state dir matters.
- Exit-node / subnet-router toggles enable IP forwarding (`sysctl`).
- `tailscale` CLI auto-update generally does **not** apply to a manual static install — the reliable
  upgrade path is a new release here (auto-bumped) → reinstall.
- **Uninstalling logs the node out** of your tailnet (a fresh install needs a new key).
- Only the **EX2 Ultra** artifact is shipped; other models use different mount paths.

## License

[BSD-3-Clause](LICENSE). Third-party attributions in [NOTICE](NOTICE). Not affiliated with Tailscale Inc.
or Western Digital.
