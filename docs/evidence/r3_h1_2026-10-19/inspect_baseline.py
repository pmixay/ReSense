"""Read raw reproduction states; independently check attribution and physical H1 witness."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import runpy
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import range_attrib as ra  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402

OUT = Path('/tmp/opencode/r3-h1/baseline')


def diff(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in a.keys() | b.keys() for d in diff(a.get(k), b.get(k), f'{path}/{k}')]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f'{path}/{i}')]
    return [] if a == b else [(path, a, b)]


def main():
    cfg = DetectorConfig()
    report = {}
    for case in ['E6', 'setO']:
        r = json.loads((OUT / f'{case}.attrib.json').read_text())
        counts = Counter(x.get('cause', 'STOP') for x in r['rows'])
        checks = []
        for cause in sorted(counts):
            rows = [x for x in r['rows'] if x.get('cause') == cause]
            for row in rows[::max(1, len(rows)//3)][:3]:
                ok, ev = ra.recheck(row, r['frames'][str(row['k'])], cfg)
                checks.append({'k': row['k'], 'cause': cause, 'confirmed': ok, 'evidence': ev})
        report[case] = {'counts': dict(counts), 'checks': checks,
                        'hooks_off': r['hooks_off'],
                        'rows': r['rows']}
        print(case, counts, 'confirmed', sum(x['confirmed'] for x in checks), '/', len(checks))
    on, off = [[json.loads(x) for x in (OUT / f'setO.{mode}.jsonl').read_text().splitlines()]
               for mode in ['on', 'off']]
    diffs = [dict(i=a['i'], differences=diff(a, b)) for a, b in zip(on, off) if a != b]
    paths = Counter(p for row in diffs for p, a, b in row['differences'])
    print('setO diff paths', paths)
    print('first difference', diffs[:1])
    def normalize(row):
        row = dict(row)
        for k in ra.TIMING:
            row.pop(k, None)
        row['msgs'] = [m for m in row['msgs'] if not m.startswith('latency p95')]
        row['level'] = row['dlevel']
        return row
    normalized_equal = all(normalize(a) == normalize(b) for a,b in zip(on, off))
    print('all non-latency fields equal', normalized_equal, len(on))
    assert normalized_equal
    report['setO_trace_differences'] = {'paths': dict(paths), 'examples': diffs[:5]}
    report['setO_trace_differences']['registered_latency_normalization_equal'] = normalized_equal
    r = json.loads((OUT / 'E6.attrib.json').read_text())
    for row in r['rows']:
        k = row['k']
        if row['X'] < 140:
            s = r['frames'][str(k)]
            cl = {int(i): c for i,c in s['clusters'].items() if abs(c['d']-row['X']) < 1}
            ts = [{key:t.get(key) for key in ['id','hits','misses','span_s','hit_fraction','confidence','reported']}
                  for t in s['tracks'] if t['last'] in cl]
            print('E6', k, row['X'], row.get('cause','STOP'), ts)
    helper = runpy.run_path(str(ROOT / 'docs/evidence/integration_2026-10-16/h4_fixes/columns/withdrawn_acceptance.py.txt'))
    xyz, ring, labels = helper['physical_column']()
    c = helper['object_cluster'](xyz, ring, labels)
    obj = xyz[labels == 1]
    report['H1'] = {'raw_points': len(obj), 'raw_height_range': [float(x) for x in
                    [np.min(obj[:, 2]+1.83), np.max(obj[:, 2]+1.83)]],
                    'cluster': {k: (v.tolist() if isinstance(v, np.ndarray) else v)
                                for k,v in vars(c).items()},
                    'raw_object_xyz': obj.tolist()}
    print('H1', {k:v for k,v in report['H1'].items() if k != 'raw_object_xyz'})
    (OUT / 'inspection.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
