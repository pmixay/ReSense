#!/usr/bin/env python3
"""Replay P4's 24 rotations with matched-object and orientation evidence.

Run the same script in separate processes for baseline and candidate:
  python run_b4.py --repo <checkout> --cache <decoded/bag> --out <result.json> --jobs 4
Environment: OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1.
Does not import the detector until the explicitly selected checkout is on sys.path.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one_case(args):
    repo, cache, index, end = args
    os.environ['RESENSE_REPO'] = repo
    sys.path[:0] = [repo, str(Path(repo, 'docs/evidence/rejudge_2026-10-16/scripts'))]
    import numpy as np
    import resense
    import resense.calibration as calibration
    from judge_runner import NodeReplica, node_decision, det_dict
    from range_test import run_frame

    assert Path(resense.__file__).resolve().parent == Path(repo, 'resense').resolve()
    rotation = calibration.orientation_candidates()[index]
    expected = calibration.axis_label(rotation.T)
    meta = json.loads(Path(cache, 'meta.json').read_text())
    if end:
        meta = meta[:end]
    rep = NodeReplica()
    rvs = rep.R_vs.astype(np.float64)
    rows, first_passing = [], []
    observe = calibration.observe_mount

    def traced(*a, **kw):
        from dataclasses import asdict
        ob = observe(*a, **kw)
        if ob.ok and not first_passing:
            first_passing.append({'frame': len(rows), **asdict(ob)})
        return ob

    calibration.observe_mount = traced
    for k, m in enumerate(meta):
        with np.load(Path(cache, f'f_{k:05d}.npz')) as d:
            xyz = d['xyz']
            if index:
                xyz = ((xyz.astype(np.float64) @ rvs.T @ rotation.T) @ rvs).astype(np.float32)
            res = run_frame(rep, xyz, d['inten'], d['ring'], m, k)
        st = rep.detector.calib.state
        rows.append({'i': k, 'decision': node_decision(res), 'status': st.status,
                     'orientation': st.orientation, 'mount': res.mount,
                     'mapping_confirmed': rep.detector.calib._config_passed,
                     'nearest': res.nearest_distance,
                     'dets': [det_dict(d) for d in res.detections],
                     'warns': [det_dict(d) for d in res.warnings]})
    calibration.observe_mount = observe
    correct = [r['i'] for r in rows if r['orientation'] == expected or
               (index == 0 and r['mapping_confirmed'])]
    wrong = [r['i'] for r in rows if r['status'] in ('ok', 'identity', 'provisional') and
             r['orientation'] != expected and not (index == 0 and r['orientation'] == 'configured')]
    return {'index': index, 'expected': expected, 'up_vertical': bool(abs(rotation[2, 2]) == 1),
            'first_correct_label': min(correct) if correct else None,
            'wrong_accepted_frames': wrong, 'first_passing_observation': first_passing,
            'decisions': {s: sum(r['decision'] == s for r in rows) for s in ('GO', 'CAUTION', 'STOP', 'FAULT')},
            'rows': rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--cache', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--only', default=','.join(map(str, range(24))))
    ap.add_argument('--end', type=int, default=0)
    a = ap.parse_args()
    repo, cache = str(Path(a.repo).resolve()), str(Path(a.cache).resolve())
    cases = [int(k) for k in a.only.split(',')]
    files = [Path(cache, 'meta.json'), *sorted(Path(cache).glob('f_*.npz'))]
    input_hash = hashlib.sha256()
    for f in files:
        input_hash.update(f.name.encode())
        input_hash.update(bytes.fromhex(sha(f)))
    source = {str(p.relative_to(repo)): sha(p) for p in sorted(Path(repo, 'resense').glob('*.py'))}
    source['configs/default.yaml'] = sha(Path(repo, 'configs/default.yaml'))
    tasks = [(repo, cache, k, a.end) for k in cases]
    with ProcessPoolExecutor(max_workers=a.jobs) as pool:
        results = list(pool.map(one_case, tasks))
    result = {'repo': repo, 'cache': cache, 'python': platform.python_version(),
              'script_sha256': sha(__file__), 'source_sha256': source,
              'input_sha256': input_hash.hexdigest(),
              'environment': {v: os.environ.get(v) for v in ('OPENBLAS_CORETYPE', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')},
              'cases': results}
    Path(a.out).write_text(json.dumps(result, indent=1))
    for c in results:
        print(c['index'], c['first_correct_label'], len(c['wrong_accepted_frames']), c['decisions'], flush=True)


if __name__ == '__main__':
    main()
