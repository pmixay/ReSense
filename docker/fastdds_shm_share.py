#!/usr/bin/env python3
"""Open this container's Fast DDS shared-memory files to other users (RESENSE_DDS=shm only).

The entrypoint starts it in the background before the node (docker/dds_transport.sh); it polls
every 0.2 s for as long as the container runs and sets mode 0666 on the Fast DDS files the
container's own processes create in /dev/shm. Why (Fast DDS 2.6.12, the Humble version;
file:line in eProsima/Fast-DDS at tag v2.6.12):

* Fast DDS creates its segments through its bundled Boost.Interprocess with the default
  permissions 0644 and sets them again with fchmod after creating (thirdparty/boost/include/boost/
  interprocess/permissions.hpp:95-102, shared_memory_object.hpp:318-324), so umask cannot widen them;
  a port's named mutex is a POSIX semaphore made with the same 0644 (sync/posix/
  semaphore_wrapper.hpp:81). No XML or transport option sets a mode: the SHM descriptor takes
  segment_size, port_queue_capacity, healthy_check_timeout_ms, rtps_dump_file and the common
  maxMessageSize / maxInitialPeersRange (src/cpp/rtps/xmlparser/XMLParser.cpp:718-731).
* A participant of another uid that sends to the node opens the node's port segment
  ``fastrtps_port<N>`` read-write (SharedMemGlobal.hpp:1077-1078, open_only) after its semaphore
  ``sem.fastrtps_port<N>_mutex`` (SharedMemGlobal.hpp:1046-1047; glibc opens it O_RDWR); a reader
  of another uid opens the node's data segment ``fastrtps_<16 hex>`` read-write too
  (SharedMemManager.hpp:1307), to count the buffers it takes. With 0644 root files both fail, and
  there is no UDP fallback: a participant on the same host keeps only the other's shared-memory
  locators (src/cpp/rtps/builtin/data/ProxyDataFilters.hpp:60-81). The node (root) opens other
  users' files anyway.

Scope, and nothing else is touched:
  * files directly in /dev/shm, regular files, opened with O_NOFOLLOW and checked with fstat, so a
    symlink or a directory is never followed or changed;
  * owned by the uid this runs as (root in the image, i.e. the node's own files);
  * mapped by a process of this container (/proc/<pid>/maps: the container's PID namespace lists
    only its own processes), so another root process's files on the host (/dev/shm is the host's
    with --ipc=host) and files left by an earlier run are not touched, and named as Fast DDS names
    them: ``fastrtps_port<N>`` (SharedMemGlobal.hpp:1041; the domain "fastrtps",
    SharedMemTransport.cpp:35) and ``fastrtps_<16 hex>`` (SharedMemManager.hpp:539); plus
    ``sem.fastrtps_port<N>_mutex`` of such a port (mapped only while it is taken, so derived from
    the port's name);
  * the mode is set to 0666; no file is created, removed or renamed. The ``_el`` / ``_sl`` lock
    files stay 0644: others open them read-only to flock them (RobustExclusiveLock.hpp:174,
    RobustSharedLock.hpp:240).
0666 lets any local user put messages into the node's queues, as any local user can already send
it UDP datagrams, and write into the segment of the node's outgoing messages; a test stand's
concern, not a production one.

    fastdds_shm_share.py            # run until killed (the entrypoint's background process)
    fastdds_shm_share.py --check    # exit 0 when /dev/shm and /proc/self/maps can be used, else 1
    fastdds_shm_share.py --once     # one pass, print what was changed
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import stat
import sys
import time

PORT = re.compile(r"fastrtps_port[0-9]+")
DATA = re.compile(r"fastrtps_[0-9a-f]{16}")
MODE = 0o666
TAG = "[resense.shm]"


def parse_maps(data: bytes, shm_dir: str = "/dev/shm"):
    """Names of the files directly in ``shm_dir`` mapped in one /proc/<pid>/maps text; unlinked
    ones (`` (deleted)``) are left out."""
    prefix = shm_dir.rstrip("/").encode() + b"/"
    names = set()
    for line in data.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        path = parts[5]
        if path.endswith(b" (deleted)") or not path.startswith(prefix):
            continue
        name = path[len(prefix):]
        if name and b"/" not in name:
            names.add(name.decode("utf-8", "replace"))
    return names


def mapped_names(proc: str = "/proc", shm_dir: str = "/dev/shm"):
    """Every file directly in ``shm_dir`` that a process of this PID namespace maps."""
    names = set()
    try:
        entries = [e.name for e in os.scandir(proc) if e.name.isdigit()]
    except OSError:
        return names
    for pid in entries:
        try:
            with open(os.path.join(proc, pid, "maps"), "rb") as fh:
                names |= parse_maps(fh.read(), shm_dir)
        except OSError:
            continue                        # the process ended, or is not ours to read
    return names


def targets(mapped):
    """The Fast DDS files to open up, from the mapped names: port segments with their
    semaphores, and data segments. Everything else (lock files, other programs' files) is out."""
    out = set()
    for name in mapped:
        if PORT.fullmatch(name):
            out.add(name)
            out.add(f"sem.{name}_mutex")
        elif DATA.fullmatch(name):
            out.add(name)
    return out


def share(names, shm_dir: str = "/dev/shm", uid: int | None = None):
    """Set 0666 on each of ``names`` in ``shm_dir`` that is a regular file owned by ``uid`` (default:
    this process's) and not 0666 already. Returns the names changed."""
    uid = os.geteuid() if uid is None else uid
    changed = []
    dfd = os.open(shm_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in sorted(names):
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=dfd)
            except OSError:
                continue                    # gone, a symlink (ELOOP), or not ours
            try:
                st = os.fstat(fd)
                if stat.S_ISREG(st.st_mode) and st.st_uid == uid and stat.S_IMODE(st.st_mode) != MODE:
                    os.fchmod(fd, MODE)
                    changed.append(name)
            except OSError:
                pass
            finally:
                os.close(fd)
    finally:
        os.close(dfd)
    return changed


def check(proc: str = "/proc", shm_dir: str = "/dev/shm") -> bool:
    """Can this work here: /dev/shm is a directory we can open and write, and /proc/self/maps reads."""
    try:
        with open(os.path.join(proc, "self", "maps"), "rb") as fh:
            fh.read(1)
        os.close(os.open(shm_dir, os.O_RDONLY | os.O_DIRECTORY))
    except OSError:
        return False
    return os.access(shm_dir, os.W_OK | os.X_OK)


def one_pass(proc: str, shm_dir: str):
    return share(targets(mapped_names(proc, shm_dir)), shm_dir)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="exit 0 when this can work here, 1 otherwise")
    p.add_argument("--once", action="store_true", help="one pass, then exit")
    p.add_argument("--interval", type=float, default=0.2, help="s between passes (default 0.2)")
    p.add_argument("--shm-dir", default="/dev/shm")
    p.add_argument("--proc", default="/proc")
    args = p.parse_args(argv)
    if args.check:
        return 0 if check(args.proc, args.shm_dir) else 1
    if not args.once:
        # Ctrl+C in `docker run -it` is for the node; this ends with the container (or on SIGTERM)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    failed = False
    while True:
        try:
            for name in one_pass(args.proc, args.shm_dir):
                print(f"{TAG} {name}: mode {MODE:o} (other users' Fast DDS participants may open it)",
                      file=sys.stderr, flush=True)
            failed = False
        except Exception as e:  # noqa: BLE001 - keep watching; report a failure once
            if not failed:
                print(f"{TAG} pass failed, retrying: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            failed = True
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
