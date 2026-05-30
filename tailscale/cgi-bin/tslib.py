"""Pure, importable helpers for the Tailscale My Cloud CGI.

This module contains no CGI plumbing and no subprocess side effects, so it can
be unit-tested off-device. ``tailscale.py`` imports from it. It uses only the
standard library (``re``, ``ipaddress``) so it runs identically on the NAS's
Python 3 and on a developer/CI machine.
"""

import ipaddress
import re

# Tailscale auth keys look like: tskey-auth-XXXX..., tskey-XXXX...
AUTHKEY_RE = re.compile(r"^tskey-[A-Za-z0-9_-]+$")
# A single DNS label: starts/ends alphanumeric, hyphens allowed inside.
HOSTNAME_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")

TRUTHY = ("1", "true", "on", "yes")


class ValidationError(ValueError):
    """Raised when user-supplied input fails validation."""


def _truthy(value):
    """Interpret form-style values (checkbox 'on', '1', bool) as a boolean."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in TRUTHY


def validate_authkey(value):
    """Return the auth key if it looks like a Tailscale key, else raise."""
    value = (value or "").strip()
    if not AUTHKEY_RE.match(value):
        raise ValidationError("Auth key must look like 'tskey-...'.")
    return value


def validate_hostname(value):
    """Return a cleaned hostname (DNS label, <=63 chars), or '' if empty."""
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) > 63 or not HOSTNAME_RE.match(value):
        raise ValidationError(
            "Hostname must be a DNS label: letters, digits and hyphens only."
        )
    return value


def parse_routes(value):
    """Parse a comma-separated list of CIDRs into a normalized list of strings.

    Empty input returns ``[]``. Any malformed entry raises ``ValidationError``
    (this also rejects shell-injection attempts, since they are not valid CIDRs).
    """
    value = (value or "").strip()
    if not value:
        return []
    routes = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            net = ipaddress.ip_network(part, strict=False)
        except ValueError as exc:
            raise ValidationError(f"Invalid route {part!r}: {exc}") from exc
        routes.append(str(net))
    return routes


def needs_ip_forwarding(params):
    """True if the chosen options (exit node / subnet router) need forwarding."""
    return _truthy(params.get("advertise_exit_node")) or bool(
        parse_routes(params.get("advertise_routes"))
    )


def build_up_command(params, tailscale_bin="tailscale", socket=None):
    """Build the argv list for ``tailscale up`` from validated UI params.

    Recognized ``params`` keys:
      - ``authkey`` (optional after first auth; validated when present)
      - ``hostname`` (optional)
      - ``accept_routes``, ``ssh``, ``advertise_exit_node``, ``accept_dns`` (bools)
      - ``advertise_routes`` (comma-separated CIDR string)

    ``--reset`` is always included so the form represents the full desired
    state: toggles left unchecked are reset to their defaults. The auth key is
    emitted as a single ``--authkey=VALUE`` token; callers must never log it.
    """
    raw_key = (params.get("authkey") or "").strip()
    authkey = validate_authkey(raw_key) if raw_key else ""
    hostname = validate_hostname(params.get("hostname"))
    routes = parse_routes(params.get("advertise_routes"))

    cmd = [tailscale_bin]
    if socket:
        cmd.append(f"--socket={socket}")
    cmd += ["up", "--reset"]

    if authkey:
        cmd.append(f"--authkey={authkey}")
    if hostname:
        cmd.append(f"--hostname={hostname}")
    if _truthy(params.get("accept_routes")):
        cmd.append("--accept-routes")
    if _truthy(params.get("ssh")):
        cmd.append("--ssh")
    if _truthy(params.get("advertise_exit_node")):
        cmd.append("--advertise-exit-node")
    # accept-dns defaults to true in Tailscale, so set it explicitly both ways.
    cmd.append("--accept-dns=true" if _truthy(params.get("accept_dns")) else "--accept-dns=false")
    if routes:
        cmd.append("--advertise-routes=" + ",".join(routes))

    return cmd
