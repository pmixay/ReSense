#!/usr/bin/env python3
"""Replay a complete decoded recording with N6 explicitly off or on, preserving frame evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault('RESENSE_REPO', str(ROOT))
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(variable, '1')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'docs/evidence/judgement_2026-10-13/scripts'))

import numpy as np  # noqa: E402
from judge_runner import NodeReplica, record  # noqa: E402
from range_test import run_frame  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--candidate', action='store_true')
    args = parser.parse_args()
    meta = json.loads((args.cache / 'meta.json').read_text())
    files = sorted(args.cache.glob('f_*.npz'))
    if len(files) != len(meta):
        raise ValueError('incomplete cache')
    rep = NodeReplica(overrides={'track.rails_axis_extension': args.candidate})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sources = {name: digest(ROOT / name) for name in ('resense/track.py', 'resense/config.py', 'resense/detector.py')}
    start = time.perf_counter()
    supported = []
    with args.out.open('w') as stream:
        for i, (path, info) in enumerate(zip(files, meta)):
            with np.load(path) as data:
                result = run_frame(rep, data['xyz'], data['inten'], data['ring'], info, i)
            row = record(i, info['bag_t'], info['stamp'], result, 0., 0., info['frame_id'], info['topic'])
            row['model'] = result.track.to_dict()
            row['timing_ms'] = result.timing_ms
            stream.write(json.dumps(row) + '\n')
            if result.track.rail_axis_support:
                supported.append(i)
            if i % 100 == 0:
                print(f'{args.cache.name} frame {i}/{len(meta)}', flush=True)
    report = {'cache': str(args.cache), 'frames': len(meta), 'candidate': args.candidate,
              'elapsed_s': time.perf_counter() - start, 'source_sha256': sources,
              'source_unchanged': all(digest(ROOT / name) == value for name, value in sources.items()),
              'support_frames': supported, 'output_sha256': digest(args.out),
              'metadata_sha256': digest(args.cache / 'meta.json'), 'resets': rep.resets}
    args.out.with_suffix('.meta.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
