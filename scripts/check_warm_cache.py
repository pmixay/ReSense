#!/usr/bin/env python3
"""Read a bag once and verify Linux page-cache residency at the playback boundary.

This is a warm-cache precondition, never a detector/playback acceptance verdict.
No mlock, cache eviction, CPU affinity changes, retries or bag writes are performed.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import mmap
import os
from pathlib import Path
import sys
import time

BLOCK = 4 * 1024 * 1024


def identity(stat):
    return {'device': stat.st_dev, 'inode': stat.st_ino, 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def resources():
    """Small informational snapshots; unavailable cgroup/proc fields are explicit."""
    paths = ['/proc/meminfo', '/proc/pressure/memory', '/proc/pressure/io', '/proc/pressure/cpu',
             '/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/memory.max',
             '/sys/fs/cgroup/memory.events', '/sys/fs/cgroup/memory.pressure',
             '/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/cpu.stat', '/sys/fs/cgroup/io.stat']
    readings = {}
    for name in paths:
        try:
            readings[name] = Path(name).read_text().strip()
        except OSError as exc:
            readings[name] = {'unavailable': str(exc)}
    return {'utc_s': time.time(), 'cpu_count': os.cpu_count(),
            'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
            'readings': readings}


def resident_pages(file):
    """mincore observes without faulting pages in; private mapping never writes the file."""
    if sys.platform != 'linux':
        raise RuntimeError('warm-cache proof requires Linux mincore')
    stat = os.fstat(file.fileno())
    if stat.st_size <= 0:
        raise ValueError('empty database cannot prove a warm recording')
    # Linux may return fictitious all-resident bits for an unowned, nonwritable file.
    # Docker root has CAP_FOWNER; host runners own the restored bags. Fail otherwise.
    capabilities = next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines()
                        if line.startswith('CapEff:'))
    if stat.st_uid != os.geteuid() and not (int(capabilities, 16) & (1 << 3)):
        raise RuntimeError('mincore requires file ownership or CAP_FOWNER for trustworthy residency')
    pages = (stat.st_size + mmap.PAGESIZE - 1) // mmap.PAGESIZE
    vector = (ctypes.c_ubyte * pages)()
    libc = ctypes.CDLL(None, use_errno=True)
    libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_ubyte)]
    libc.mincore.restype = ctypes.c_int
    with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_COPY) as mapping:
        address = ctypes.addressof(ctypes.c_char.from_buffer(mapping))
        if libc.mincore(address, stat.st_size, vector):
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
    resident = sum(bool(value & 1) for value in vector)
    return {'pages': pages, 'resident': resident, 'missing': pages - resident,
            'page_size': mmap.PAGESIZE, 'fully_resident': resident == pages}


def read_complete(file, expected):
    total = 0
    while block := file.read(BLOCK):
        total += len(block)
    if total != expected:
        raise ValueError(f'incomplete/changing warm read: expected {expected}, read {total}')
    return total


def inspect_bag(bag, *, observe_only=False):
    start = time.monotonic()
    report = {'schema': 'resense-warm-cache-v1', 'scope': 'page-cache precondition only, not playback acceptance',
              'mode': 'observe' if observe_only else 'warm-once-and-verify', 'bag': str(bag),
              'before': resources(), 'files': [], 'errors': []}
    try:
        if not (bag / 'metadata.yaml').is_file():
            raise ValueError('missing bag metadata.yaml')
        paths = sorted(bag.glob('*.db3'))
        if not paths:
            raise ValueError('no SQLite bag files')
        for path in paths:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f'not a regular database: {path}')
            with path.open('rb', buffering=0) as file:
                before = identity(os.fstat(file.fileno()))
                row = {'name': path.name, 'identity': before, 'before': resident_pages(file)}
                report['files'].append(row)
                row['read_bytes'] = 0 if observe_only else read_complete(file, before['bytes'])
                if identity(os.fstat(file.fileno())) != before:
                    raise ValueError(f'file changed during warm read: {path}')
        # Check ALL files after ALL reads: warming a later split may evict an earlier split.
        for row, path in zip(report['files'], paths):
            with path.open('rb', buffering=0) as file:
                if identity(os.fstat(file.fileno())) != row['identity']:
                    raise ValueError(f'file changed before residency check: {path}')
                row['after'] = resident_pages(file)
                if not observe_only and not row['after']['fully_resident']:
                    report['errors'].append(f'{path.name}: {row["after"]["missing"]} pages not resident after full read')
    except (OSError, ValueError, RuntimeError) as exc:
        report['errors'].append(str(exc))
    report.update(after=resources(), wall_s=time.monotonic() - start)
    report['status'] = 'ERROR' if report['errors'] else 'OBSERVED' if observe_only else 'WARM_VERIFIED'
    return report


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('bag', type=Path)
    cli.add_argument('--out', type=Path, required=True)
    cli.add_argument('--observe-only', action='store_true', help='record residency/resources without warming or a warm claim')
    args = cli.parse_args(argv)
    if args.out.exists():
        cli.error('receipt already exists; use a fresh output directory')
    report = inspect_bag(args.bag, observe_only=args.observe_only)
    with args.out.open('x', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
        file.write('\n')
    print(json.dumps(report), flush=True)
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
