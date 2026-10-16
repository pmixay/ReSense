#!/usr/bin/env python3
"""Establish and verify Linux page-cache residency within a bounded setup phase.

This is a warm-cache precondition, never a detector/playback acceptance verdict.
One full read, one mapped page-touch sweep and at most one missing-page repair sweep.
No mlock, cache eviction, CPU affinity changes, playback retries or bag writes.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import ctypes
import json
import mmap
import os
from pathlib import Path
import sys
import time

BLOCK = 4 * 1024 * 1024
SETUP_BUDGET_S = 60.0
MAX_MAPPED_SWEEPS = 2


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
    try:
        wanted = ('Uid:', 'CapEff:', 'VmRSS:', 'VmSize:')
        readings['/proc/self/status:selected'] = [line for line in Path('/proc/self/status').read_text().splitlines()
                                                  if line.startswith(wanted)]
        counters = ('pgfault', 'pgmajfault', 'pgscan_kswapd', 'pgsteal_kswapd', 'pgscan_direct', 'pgsteal_direct',
                    'workingset_refault_file', 'workingset_activate_file')
        readings['/proc/vmstat:selected'] = {key: int(value) for key, value in
                                            (line.split() for line in Path('/proc/vmstat').read_text().splitlines())
                                            if key in counters}
    except OSError as exc:
        readings['process/reclaim_counters'] = {'unavailable': str(exc)}
    return {'utc_s': time.time(), 'cpu_count': os.cpu_count(),
            'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
            'readings': readings}


def page_state(file):
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
    summary = {'pages': pages, 'resident': resident, 'missing': pages - resident,
               'page_size': mmap.PAGESIZE, 'fully_resident': resident == pages}
    return summary, vector


def resident_pages(file):
    return page_state(file)[0]


def check_budget(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise RuntimeError('warm setup time budget exhausted (no playback attempted)')


def read_complete(file, expected, *, deadline=None):
    total = 0
    while True:
        check_budget(deadline)
        block = file.read(BLOCK)
        if not block:
            break
        total += len(block)
    check_budget(deadline)
    if total != expected:
        raise ValueError(f'incomplete/changing warm read: expected {expected}, read {total}')
    return total


def touch_pages(mapping, indices, deadline):
    """Synchronously read one byte per requested page; no advisory-only warm claim."""
    touched = 0
    checksum = 0
    for page in indices:
        if touched % 256 == 0:
            check_budget(deadline)
        checksum ^= mapping[page * mmap.PAGESIZE]
        touched += 1
    check_budget(deadline)
    return {'pages_touched': touched, 'sample_xor': checksum}


def mapped_setup(paths, rows, deadline, setup):
    """Fixed work schedule: full mapped touch, then only the measured missing pages once.

    Keep mappings across both sweeps/all splits, but close every mapping and descriptor
    before the caller's independent final mincore check. Mappings are not mlocked.
    """
    with ExitStack() as stack:
        files, mappings = [], []
        for path, row in zip(paths, rows):
            check_budget(deadline)
            file = stack.enter_context(path.open('rb', buffering=0))
            if identity(os.fstat(file.fileno())) != row['identity']:
                raise ValueError(f'file changed before mapped setup: {path}')
            files.append(file)
            mappings.append(stack.enter_context(mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)))
        for sweep in range(MAX_MAPPED_SWEEPS):
            record = {'sweep': sweep + 1, 'kind': 'all-pages' if sweep == 0 else 'missing-pages-once', 'files': []}
            setup['sweeps'].append(record)
            for file, mapping, row in zip(files, mappings, rows):
                check_budget(deadline)
                before, vector = page_state(file)
                indices = range(before['pages']) if sweep == 0 else (i for i, bit in enumerate(vector) if not bit & 1)
                item = {'name': row['name'], 'before': before}
                record['files'].append(item)
                item.update(touch_pages(mapping, indices, deadline))
            # Record all files together after each sweep; do not select a successful
            # intermediate result or loop until lucky. The second sweep is always bounded.
            for file, item in zip(files, record['files']):
                item['after'] = resident_pages(file)
                check_budget(deadline)
        for file, row in zip(files, rows):
            if identity(os.fstat(file.fileno())) != row['identity']:
                raise ValueError(f'file changed during mapped setup: {row["name"]}')
    setup['mappings_released_before_final_check'] = True


def inspect_bag(bag, *, observe_only=False):
    start = time.monotonic()
    deadline = None if observe_only else start + SETUP_BUDGET_S
    report = {'schema': 'resense-warm-cache-v1', 'scope': 'page-cache precondition only, not playback acceptance',
              'mode': 'observe' if observe_only else 'bounded-read-and-mapped-faults', 'bag': str(bag),
              'before': resources(), 'files': [], 'errors': []}
    if not observe_only:
        report['setup'] = {'budget_s': SETUP_BUDGET_S, 'max_mapped_sweeps': MAX_MAPPED_SWEEPS,
                           'sweeps': [], 'mappings_released_before_final_check': False,
                           'method': 'one buffered read, one all-page mapped touch, one missing-page mapped touch'}
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
                row['read_bytes'] = 0 if observe_only else read_complete(file, before['bytes'], deadline=deadline)
                if identity(os.fstat(file.fileno())) != before:
                    raise ValueError(f'file changed during warm read: {path}')
        if not observe_only:
            for row, path in zip(report['files'], paths):
                with path.open('rb', buffering=0) as file:
                    row['after_read'] = resident_pages(file)
            mapped_setup(paths, report['files'], deadline, report['setup'])
        # Final ALL-file check after ALL setup mappings have been released. No warm
        # claim based solely on the sequential read or an earlier successful sweep.
        for row, path in zip(report['files'], paths):
            with path.open('rb', buffering=0) as file:
                if identity(os.fstat(file.fileno())) != row['identity']:
                    raise ValueError(f'file changed before residency check: {path}')
                row['after'] = resident_pages(file)
                if not observe_only and not row['after']['fully_resident']:
                    report['errors'].append(f'{path.name}: {row["after"]["missing"]} pages not resident after bounded setup')
        check_budget(deadline)
    except (OSError, ValueError, RuntimeError) as exc:
        report['errors'].append(str(exc))
    report.update(after=resources(), wall_s=time.monotonic() - start)
    if not observe_only and report['wall_s'] >= SETUP_BUDGET_S and not report['errors']:
        report['errors'].append('warm setup time budget exhausted before receipt completion')
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
