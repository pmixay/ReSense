"""scripts/check_no_network.py with a fake socket module: IPv4 and IPv6 are both probed (public
literals of each family, and per host at least one resolved address of each family), a
connection over either family is a FAIL, "no IPv6 here at all" (EAFNOSUPPORT, ENETUNREACH,
EADDRNOTAVAIL) counts as blocked. No network needed, nothing is really connected."""

from __future__ import annotations

import errno
import importlib.util
import socket
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_no_network.py"
SPEC = importlib.util.spec_from_file_location("resense_check_no_network", PATH)
assert SPEC is not None and SPEC.loader is not None
net = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(net)

V4 = ["192.0.2.1", "192.0.2.2", "192.0.2.3"]              # documentation ranges: never real hosts
V6 = ["2001:db8::1", "2001:db8::2", "2001:db8::3"]


class FakeSocketModule:
    """Stands in for ``socket`` inside the script. ``v4`` / ``v6`` say what a connection over that
    family does: "open" connects; "refused" / "timeout" / "unreach" / "addrnotavail" fail at
    connect(); "no_af" fails at socket() (a kernel without IPv6). ``dns`` is "ok", "down" (no
    resolution at all) or "no_aaaa" (IPv4 records only). Every other attribute is the real one."""

    def __init__(self, v4="refused", v6="refused", dns="ok"):
        self.mode = {socket.AF_INET: v4, socket.AF_INET6: v6}
        self.dns = dns
        self.lookups, self.connects = [], []

    def __getattr__(self, name):
        return getattr(socket, name)

    def socket(self, family, type_=socket.SOCK_STREAM, *args):
        if self.mode[family] == "no_af":
            raise OSError(errno.EAFNOSUPPORT, "Address family not supported by protocol")
        return FakeSocket(self, family)

    def getaddrinfo(self, host, port, family=0, type=0, proto=0, flags=0):
        self.lookups.append((host, family))
        if self.dns == "down" or (self.dns == "no_aaaa" and family == socket.AF_INET6):
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
        out = []
        if family in (0, socket.AF_INET):
            out += [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, port)) for a in V4]
        if family in (0, socket.AF_INET6):
            out += [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (a, port, 0, 0)) for a in V6]
        return out


class FakeSocket:
    def __init__(self, fake, family):
        self.fake, self.family, self.peer = fake, family, None

    def settimeout(self, t):
        pass

    def connect(self, addr):
        self.fake.connects.append((self.family, addr[0], addr[1]))
        mode = self.fake.mode[self.family]
        if mode == "open":
            self.peer = addr
            return
        if mode == "timeout":
            raise socket.timeout("timed out")
        code = {"refused": errno.ECONNREFUSED, "unreach": errno.ENETUNREACH,
                "addrnotavail": errno.EADDRNOTAVAIL}[mode]
        raise OSError(code, "fake failure")

    def getpeername(self):
        return self.peer

    def close(self):
        pass


def run(monkeypatch, capsys, **kw):
    fake = FakeSocketModule(**kw)
    monkeypatch.setattr(net, "socket", fake)
    code = net.main()
    return code, capsys.readouterr().out, fake


# ---------------------------------------------------------------------------------------------
def test_ipv4_blocked_but_ipv6_open_fails(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, v4="refused", v6="open")
    assert code == 1
    assert "[2606:4700:4700::1111]:443: REACHABLE" in out
    assert "1.1.1.1:443: unreachable (ECONNREFUSED)" in out
    assert "pypi.org IPv6: resolves to 2001:db8::1, 2001:db8::2; REACHABLE" in out
    assert "pypi.org IPv4: resolves to 192.0.2.1, 192.0.2.2; unreachable (ECONNREFUSED)" in out
    assert "IPv4: blocked (0 of 15 connections succeeded)" in out
    assert "IPv6: REACHABLE (15 of 15 connections succeeded)" in out
    fail = [line for line in out.splitlines() if line.startswith("FAIL:")]
    assert fail and "[2001:4860:4860::8888]:443" in fail[0] and "pypi.org (IPv6)" in fail[0]
    assert "pypi.org (IPv4)" not in fail[0]


def test_ipv4_open_fails_as_before(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, v4="open", v6="no_af")
    assert code == 1
    assert "IPv4: REACHABLE" in out and "IPv6: blocked, no IPv6 on this machine" in out
    assert "1.1.1.1:443" in out.splitlines()[-1]


@pytest.mark.parametrize("v4", ["refused", "timeout", "unreach"])
def test_both_families_blocked_is_ok(monkeypatch, capsys, v4):
    code, out, fake = run(monkeypatch, capsys, v4=v4, v6="refused")
    assert code == 0
    assert out.splitlines()[-1] == "OK: no internet from here"
    assert "IPv4: blocked (0 of 15 connections succeeded)" in out
    assert "IPv6: blocked (0 of 15 connections succeeded)" in out
    assert "REACHABLE" not in out
    assert {f for f, _, _ in fake.connects} == {socket.AF_INET, socket.AF_INET6}


@pytest.mark.parametrize("v6, why", [("no_af", "EAFNOSUPPORT"), ("unreach", "ENETUNREACH"),
                                     ("addrnotavail", "EADDRNOTAVAIL")])
def test_no_ipv6_support_counts_as_blocked(monkeypatch, capsys, v6, why):
    code, out, _ = run(monkeypatch, capsys, v4="refused", v6=v6)
    assert code == 0
    assert f"[2606:4700:4700::1111]:443: unreachable (no IPv6 here: {why})" in out
    assert f"pypi.org IPv6: resolves to 2001:db8::1, 2001:db8::2; unreachable (no IPv6 here: {why})" in out
    assert "IPv6: blocked, no IPv6 on this machine (15 of 15 attempts" in out
    assert out.splitlines()[-1] == "OK: no internet from here"


def test_every_host_is_resolved_and_tried_over_each_family(monkeypatch, capsys):
    _, _, fake = run(monkeypatch, capsys)
    for host in net.HOSTS:
        assert (host, socket.AF_INET) in fake.lookups and (host, socket.AF_INET6) in fake.lookups
    v6 = [a for f, a, _ in fake.connects if f == socket.AF_INET6]
    v4 = [a for f, a, _ in fake.connects if f == socket.AF_INET]
    assert {"2606:4700:4700::1111", "2001:4860:4860::8888", "2620:fe::fe"} <= set(v6)
    assert {"1.1.1.1", "8.8.8.8", "9.9.9.9"} <= set(v4)
    # the first two resolved addresses of each family per host, in the resolver's order
    assert v6.count("2001:db8::1") == v6.count("2001:db8::2") == len(net.HOSTS) and "2001:db8::3" not in v6
    assert v4.count("192.0.2.1") == v4.count("192.0.2.2") == len(net.HOSTS) and "192.0.2.3" not in v4


def test_without_dns_the_ipv6_literals_still_catch_an_open_ipv6(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, v4="unreach", v6="open", dns="down")
    assert code == 1
    assert "pypi.org IPv6: no name resolution (gaierror)" in out
    assert "IPv6: REACHABLE (3 of 3 connections succeeded)" in out
    code, out, _ = run(monkeypatch, capsys, v4="unreach", v6="unreach", dns="down")
    assert code == 0 and "OK: no internet from here" in out


def test_a_host_without_ipv6_records_is_not_a_failure(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, v4="refused", v6="open", dns="no_aaaa")
    assert "pypi.org IPv6: no name resolution (gaierror)" in out
    assert code == 1                                  # the IPv6 literals still connect
    code, out, _ = run(monkeypatch, capsys, v4="refused", v6="refused", dns="no_aaaa")
    assert code == 0
