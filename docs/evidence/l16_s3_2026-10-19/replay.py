"""P3 paired core replay on unmodified node-decoded inputs; raw rows retained."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()
                if k not in ('timing_ms', 'latency_p95_ms')}
    if isinstance(value, list):
        return [clean(v) for v in value if not (isinstance(v, str) and v.startswith('latency p95'))]
    return value


def one_case(task):
    repo, cache, out, index, end, keep_ring, trace = task
    os.environ['RESENSE_REPO'] = repo
    sys.path.insert(0, repo)
    import numpy as np
    import resense
    from resense import Detector, DetectorConfig
    from resense.frame import Frame, sensor_to_vehicle
    import resense.calibration as mod
    assert Path(resense.__file__).resolve().parent == Path(repo, 'resense').resolve()
    assert np.__version__ == '1.26.4', np.__version__
    meta = json.loads(Path(cache, 'meta.json').read_text())
    meta = meta[:end] if end else meta
    cfg = DetectorConfig.from_yaml(str(Path(repo, 'configs/default.yaml')))
    assert cfg.calibration.orientation_replay_frames == 0
    detector = Detector(cfg)
    rotation = mod.orientation_candidates()[index]
    row_path = Path(out, f'case_{index:02d}.jsonl')
    if row_path.exists():
        raise FileExistsError(row_path)
    counts = {'observe': 0, 'search': 0, 'max_search_points': 0}
    in_search = [False]
    if trace:
        original_observe, original_search = mod.observe_mount, detector.calib._search_orientation

        def observe(xyz, *args, **kwargs):
            counts['observe'] += 1
            if in_search[0]:
                counts['max_search_points'] = max(counts['max_search_points'], len(xyz))
            return original_observe(xyz, *args, **kwargs)

        def search(*args, **kwargs):
            counts['search'] += 1
            in_search[0] = True
            try:
                return original_search(*args, **kwargs)
            finally:
                in_search[0] = False

        mod.observe_mount, detector.calib._search_orientation = observe, search
    stops, accepted_wrong, first_mapping, sign_examples = [], [], None, []
    digest = hashlib.sha256()
    t0 = time.monotonic()
    with row_path.open('w') as stream:
        for i, m in enumerate(meta):
            path = Path(cache, f'f_{i:05d}.npz')
            with np.load(path) as d:
                # Falcon /iv_points already uses ROS vehicle axes; Pandar uses the
                # documented -y/+x/+z mapping. This truth is fixed, not fitted.
                xyz = d['xyz'] if m['topic'] == '/iv_points' else sensor_to_vehicle(d['xyz'], cfg.sensor)
                xyz = (xyz @ rotation.T.astype(np.float32)).astype(np.float32)
                ring = d['ring'] if keep_ring and m['has_ring'] else None
                result = detector.process(Frame(xyz=xyz, intensity=d['inten'], ring=ring,
                                                stamp=m['stamp'], frame_id=m['frame_id'],
                                                meta={'n_raw': m['n_raw'], 'n_near': m['n_near']}))
            row = {'i': i, 'result': clean(result.to_dict()),
                   'R': detector.mount_rotation.tolist(),
                   'mapping_confirmed': detector.calib._config_passed}
            stream.write(json.dumps(row, separators=(',', ':')) + '\n')
            digest.update(json.dumps(row, sort_keys=True).encode())
            if result.obstacle:
                stops.append(i)
            if detector.calib._config_passed:
                mapped = detector.calib._R_orient @ rotation
                if not np.array_equal(mapped, np.eye(3)):
                    accepted_wrong.append(i)
                elif first_mapping is None:
                    first_mapping = i
            if i in (0, 1, 50):
                p = xyz[::max(1, int(np.ceil(len(xyz) / 16384)))]
                sign_examples.append({'frame': i, 'positive_fraction': (p > 0).mean(axis=0).tolist(),
                                      'mount': result.mount})
    summary = {'index': index, 'frames': len(meta), 'stops': stops,
               'first_stop': stops[0] if stops else None, 'last_stop': stops[-1] if stops else None,
               'first_mapping': first_mapping, 'accepted_wrong': accepted_wrong,
               'counts': counts, 'trace': trace, 'numpy_version': np.__version__, 'payload_digest': digest.hexdigest(),
               'raw_sha256': sha(row_path), 'seconds': time.monotonic() - t0,
               'examples': sign_examples}
    Path(out, f'case_{index:02d}.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('stops', 'accepted_wrong', 'examples')}, indent=1), flush=True)
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--cache', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--cases', default='0,4,5,12')
    p.add_argument('--end', type=int, default=0)
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--keep-ring', action='store_true')
    p.add_argument('--trace', action='store_true')
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(exist_ok=False, parents=True)
    source = {str(f.relative_to(a.repo)): sha(f) for f in sorted(Path(a.repo, 'resense').glob('*.py'))}
    native = {f.name: sha(f) for f in Path(a.repo, 'resense').glob('*native*.so')}
    tasks = [(a.repo, a.cache, a.out, k, a.end, a.keep_ring, a.trace) for k in map(int, a.cases.split(','))]
    with ProcessPoolExecutor(max_workers=a.jobs) as pool:
        results = list(pool.map(one_case, tasks))
    receipt = {'repo': a.repo, 'source_commit': subprocess.check_output(['git', '-C', a.repo, 'rev-parse', 'HEAD'], text=True).strip(),
               'source': source, 'native': native, 'script_sha256': sha(__file__),
               'meta_sha256': sha(Path(a.cache, 'meta.json')), 'cache': a.cache,
               'keep_ring': a.keep_ring, 'cases': results,
               'source_unchanged': source == {str(f.relative_to(a.repo)): sha(f) for f in sorted(Path(a.repo, 'resense').glob('*.py'))}}
    Path(out, 'summary.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
