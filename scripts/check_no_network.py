#!/usr/bin/env python3
"""Assert that this machine / container cannot reach the internet (the test stand has none,
docs/organizers/answers.md section 7).

Run inside the image before an offline check (CI, ``scripts/dry_run.sh`` with ``OFFLINE=1``):

    docker run --rm --network none resense:latest python3 scripts/check_no_network.py

Prints the network interfaces, then tries TCP connections over IPv4 and IPv6: to public
addresses of both families (port 443) and, per host a build would need (Docker Hub, the Ubuntu
and ROS apt repositories, PyPI), to up to two resolved addresses of each family. Exits 0 when
none of them can be reached, 1 when any can (the check that followed would then not prove
anything about running without internet). A name that still resolves (Docker's embedded DNS may
answer on an internal network) is reported but is not a failure; a connection is. An IPv6
attempt that fails because the machine has no IPv6 at all (no IPv6 socket, route or source
address: EAFNOSUPPORT, ENETUNREACH, EADDRNOTAVAIL) counts as blocked. The last lines give the
result per family.
"""
from __future__ import annotations

import errno
import socket
import sys
from concurrent.futures import ThreadPoolExecutor

PUBLIC = [("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443),
          ("2606:4700:4700::1111", 443), ("2001:4860:4860::8888", 443), ("2620:fe::fe", 443)]
HOSTS = ["registry-1.docker.io", "archive.ubuntu.com", "packages.ros.org", "pypi.org",
         "files.pythonhosted.org", "cdn.jsdelivr.net"]
TIMEOUT_S = 3.0
PER_FAMILY = 2                  # resolved addresses tried per host and address family
FAMILIES = (("IPv4", socket.AF_INET), ("IPv6", socket.AF_INET6))
NO_IPV6 = {errno.EAFNOSUPPORT, errno.ENETUNREACH, errno.EADDRNOTAVAIL}     # "no IPv6 here at all"


def interfaces() -> list[str]:
    try:
        with open("/proc/net/dev", encoding="ascii") as f:
            return [line.split(":", 1)[0].strip() for line in f.readlines()[2:]]
    except OSError:
        return ["?"]


def family_name(family) -> str:
    return "IPv6" if family == socket.AF_INET6 else "IPv4"


def attempt(family, addr: str, port: int) -> dict:
    """One TCP connection to (addr, port): family, connected, what happened, and whether it failed
    because this machine has no IPv6 at all (blocked, like any other failure)."""
    out = {"family": family_name(family), "connected": False, "no_ipv6": False}
    try:
        s = socket.socket(family, socket.SOCK_STREAM)
    except OSError as e:
        return {**out, **_failure(family, e)}
    try:
        s.settimeout(TIMEOUT_S)
        s.connect((addr, port))
        return {**out, "connected": True, "detail": f"connected to {tuple(s.getpeername()[:2])}"}
    except OSError as e:
        return {**out, **_failure(family, e)}
    finally:
        s.close()


def _failure(family, e: OSError) -> dict:
    if isinstance(e, (socket.timeout, TimeoutError)):
        return {"detail": "timeout"}
    name = errno.errorcode.get(e.errno, type(e).__name__) if e.errno else type(e).__name__
    if family == socket.AF_INET6 and e.errno in NO_IPV6:
        return {"detail": f"no IPv6 here: {name}", "no_ipv6": True}
    return {"detail": name}


def _outcome(tries) -> str:
    hits = [t["detail"] for t in tries if t["connected"]]
    if hits:
        return f"REACHABLE ({hits[0]})"
    return f"unreachable ({', '.join(dict.fromkeys(t['detail'] for t in tries))})"


def check_public(addr: str, port: int) -> dict:
    """A public address literal: one connection over its own family."""
    family = socket.AF_INET6 if ":" in addr else socket.AF_INET
    shown = f"[{addr}]:{port}" if family == socket.AF_INET6 else f"{addr}:{port}"
    tries = [attempt(family, addr, port)]
    return {"line": f"{shown}: {_outcome(tries)}", "tries": tries,
            "reached": shown if tries[0]["connected"] else None}


def check_host(host: str, label: str, family) -> dict:
    """A host name over one family: its first resolved addresses of that family, each tried."""
    try:
        infos = socket.getaddrinfo(host, 443, family, socket.SOCK_STREAM)
    except OSError as e:           # socket.gaierror: no DNS, no such record (e.g. no AAAA)
        return {"line": f"{host} {label}: no name resolution ({e.__class__.__name__})", "tries": [],
                "reached": None}
    addrs = list(dict.fromkeys(ai[4][0] for ai in infos if ai[0] == family))[:PER_FAMILY]
    if not addrs:
        return {"line": f"{host} {label}: no {label} address", "tries": [], "reached": None}
    tries = [attempt(family, a, 443) for a in addrs]
    return {"line": f"{host} {label}: resolves to {', '.join(addrs)}; {_outcome(tries)}", "tries": tries,
            "reached": f"{host} ({label})" if any(t["connected"] for t in tries) else None}


def family_summary(results, label: str) -> str:
    tries = [t for r in results for t in r["tries"] if t["family"] == label]
    hits = sum(t["connected"] for t in tries)
    if not tries:
        return f"{label}: not tried"
    if hits:
        return f"{label}: REACHABLE ({hits} of {len(tries)} connections succeeded)"
    if all(t["no_ipv6"] for t in tries):
        return (f"{label}: blocked, no IPv6 on this machine ({len(tries)} of {len(tries)} attempts: "
                "no IPv6 socket, route or address)")
    return f"{label}: blocked (0 of {len(tries)} connections succeeded)"


def main() -> int:
    print("interfaces:", " ".join(interfaces()))
    jobs = [(check_public, addr, port) for addr, port in PUBLIC]
    jobs += [(check_host, host, label, family) for host in HOSTS for label, family in FAMILIES]
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:      # at most ~TIMEOUT_S * PER_FAMILY in all
        results = list(ex.map(lambda j: j[0](*j[1:]), jobs))
    for r in results:
        print(f"  {r['line']}")
    for label, _ in FAMILIES:
        print(family_summary(results, label))
    reached = [r["reached"] for r in results if r["reached"]]
    if reached:
        print("FAIL: this environment reaches the internet:", ", ".join(reached))
        return 1
    print("OK: no internet from here")
    return 0


if __name__ == "__main__":
    sys.exit(main())
