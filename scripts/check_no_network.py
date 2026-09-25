#!/usr/bin/env python3
"""Assert that this machine / container cannot reach the internet (the test stand has none,
docs/organizers/answers.md section 7).

Run inside the image before an offline check (CI, ``scripts/dry_run.sh`` with ``OFFLINE=1``):

    docker run --rm --network none resense:latest python3 scripts/check_no_network.py

Prints the network interfaces, then tries TCP connections to public addresses and to the hosts a
build would need (Docker Hub, the Ubuntu and ROS apt repositories, PyPI). Exits 0 when none of
them can be reached, 1 when any can (the check that followed would then not prove anything about
running without internet). A name that still resolves (Docker's embedded DNS may answer on an
internal network) is reported but is not a failure; a connection is.
"""
from __future__ import annotations

import socket
import sys

PUBLIC = [("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443)]
HOSTS = ["registry-1.docker.io", "archive.ubuntu.com", "packages.ros.org", "pypi.org",
         "files.pythonhosted.org", "cdn.jsdelivr.net"]
TIMEOUT_S = 3.0


def interfaces() -> list[str]:
    try:
        with open("/proc/net/dev", encoding="ascii") as f:
            return [line.split(":", 1)[0].strip() for line in f.readlines()[2:]]
    except OSError:
        return ["?"]


def reachable(addr: str, port: int) -> str | None:
    """None when (addr, port) cannot be connected to, else a description of the connection."""
    try:
        with socket.create_connection((addr, port), timeout=TIMEOUT_S) as s:
            return f"connected to {s.getpeername()}"
    except OSError:
        return None


def main() -> int:
    print("interfaces:", " ".join(interfaces()))
    reached = []
    for addr, port in PUBLIC:
        hit = reachable(addr, port)
        print(f"  {addr}:{port}: {hit or 'unreachable'}")
        if hit:
            reached.append(f"{addr}:{port}")
    for host in HOSTS:
        try:
            addrs = sorted({ai[4][0] for ai in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        except OSError as e:
            print(f"  {host}: no name resolution ({e.__class__.__name__})")
            continue
        hits = [a for a in addrs[:2] if reachable(a, 443)]
        print(f"  {host}: resolves to {', '.join(addrs[:2])}; {'REACHABLE' if hits else 'unreachable'}")
        if hits:
            reached.append(host)
    if reached:
        print("FAIL: this environment reaches the internet:", ", ".join(reached))
        return 1
    print("OK: no internet from here")
    return 0


if __name__ == "__main__":
    sys.exit(main())
