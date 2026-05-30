"""Unit tests for the pure CGI logic (tslib).

These run off-device: no NAS, no subprocess, no network. They exercise the
input validation and the ``tailscale up`` argv construction.
"""

import pytest
import tslib  # provided on sys.path via pyproject's [tool.pytest.ini_options].pythonpath

VALID_KEY = "tskey-auth-k123ABC-def456ghiJKL"


# --------------------------------------------------------------------------- #
# validate_authkey
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "value",
    ["tskey-abc123", "tskey-auth-XXXX-YYYY", "  tskey-auth-with_underscore  "],
)
def test_authkey_valid(value):
    assert tslib.validate_authkey(value) == value.strip()


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "nope",
        "key-without-prefix",
        "tskey-abc; rm -rf /",   # injection attempt -> space/semicolon fail the regex
        "tskey-abc def",
        "tskey-$(whoami)",
    ],
)
def test_authkey_invalid(value):
    with pytest.raises(tslib.ValidationError):
        tslib.validate_authkey(value)


# --------------------------------------------------------------------------- #
# validate_hostname
# --------------------------------------------------------------------------- #
def test_hostname_empty_is_ok():
    assert tslib.validate_hostname("") == ""
    assert tslib.validate_hostname(None) == ""
    assert tslib.validate_hostname("   ") == ""


@pytest.mark.parametrize("value", ["mycloud", "mycloud-ex2", "nas123", "a"])
def test_hostname_valid(value):
    assert tslib.validate_hostname(value) == value


@pytest.mark.parametrize(
    "value",
    ["-bad", "bad-", "has space", "under_score", "x" * 64, "semi;colon", "a/b"],
)
def test_hostname_invalid(value):
    with pytest.raises(tslib.ValidationError):
        tslib.validate_hostname(value)


# --------------------------------------------------------------------------- #
# parse_routes
# --------------------------------------------------------------------------- #
def test_routes_empty():
    assert tslib.parse_routes("") == []
    assert tslib.parse_routes(None) == []


def test_routes_valid_list_normalized():
    assert tslib.parse_routes("192.168.1.0/24, 10.0.0.0/8") == [
        "192.168.1.0/24",
        "10.0.0.0/8",
    ]


def test_routes_accepts_ipv6():
    assert tslib.parse_routes("fd7a::/48") == ["fd7a::/48"]


@pytest.mark.parametrize(
    "value",
    ["999.0.0.0/8", "not-a-cidr", "192.168.1.0/33", "10.0.0.0/8; rm -rf /", "$(id)"],
)
def test_routes_invalid(value):
    with pytest.raises(tslib.ValidationError):
        tslib.parse_routes(value)


# --------------------------------------------------------------------------- #
# build_up_command
# --------------------------------------------------------------------------- #
def test_up_minimal_with_key():
    cmd = tslib.build_up_command({"authkey": VALID_KEY})
    assert cmd[:3] == ["tailscale", "up", "--reset"]
    assert f"--authkey={VALID_KEY}" in cmd
    # defaults: accept-dns explicit false (unchecked), no other toggles
    assert "--accept-dns=false" in cmd
    assert "--accept-routes" not in cmd
    assert "--ssh" not in cmd
    assert "--advertise-exit-node" not in cmd
    assert not any(c.startswith("--advertise-routes") for c in cmd)


def test_up_prefixes_binary_and_socket():
    cmd = tslib.build_up_command(
        {"authkey": VALID_KEY}, tailscale_bin="/opt/ts/tailscale", socket="/run/ts.sock"
    )
    assert cmd[0] == "/opt/ts/tailscale"
    assert cmd[1] == "--socket=/run/ts.sock"
    assert cmd[2:4] == ["up", "--reset"]


def test_up_without_key_is_allowed():
    # Re-applying settings on an already-authenticated node needs no key.
    cmd = tslib.build_up_command({"accept_routes": "on"})
    assert not any(c.startswith("--authkey") for c in cmd)
    assert "--accept-routes" in cmd


def test_up_all_toggles():
    cmd = tslib.build_up_command(
        {
            "authkey": VALID_KEY,
            "hostname": "mycloud-ex2",
            "accept_routes": "on",
            "ssh": "on",
            "advertise_exit_node": "on",
            "accept_dns": "on",
            "advertise_routes": "192.168.1.0/24,10.0.0.0/8",
        }
    )
    assert "--hostname=mycloud-ex2" in cmd
    assert "--accept-routes" in cmd
    assert "--ssh" in cmd
    assert "--advertise-exit-node" in cmd
    assert "--accept-dns=true" in cmd
    assert "--advertise-routes=192.168.1.0/24,10.0.0.0/8" in cmd


def test_up_invalid_key_raises():
    with pytest.raises(tslib.ValidationError):
        tslib.build_up_command({"authkey": "totally-not-a-key"})


def test_up_invalid_hostname_raises():
    with pytest.raises(tslib.ValidationError):
        tslib.build_up_command({"authkey": VALID_KEY, "hostname": "bad host"})


def test_authkey_appears_at_most_once():
    cmd = tslib.build_up_command({"authkey": VALID_KEY})
    assert sum(c.startswith("--authkey=") for c in cmd) == 1


def test_no_key_means_no_key_token_anywhere():
    cmd = tslib.build_up_command({"ssh": "on"})
    assert all("tskey-" not in c for c in cmd)


# --------------------------------------------------------------------------- #
# needs_ip_forwarding
# --------------------------------------------------------------------------- #
def test_forwarding_required_for_exit_node():
    assert tslib.needs_ip_forwarding({"advertise_exit_node": "on"}) is True


def test_forwarding_required_for_subnet_router():
    assert tslib.needs_ip_forwarding({"advertise_routes": "192.168.1.0/24"}) is True


def test_forwarding_not_required_by_default():
    assert tslib.needs_ip_forwarding({"authkey": VALID_KEY, "ssh": "on"}) is False
