"""Fixed H1 physical sweeps and unchanged critical node-replica probes."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import copy
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

import numpy as np

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame

from run_checks import HERE, REF, ROOT, WORK, run

J = ROOT / 'docs/evidence/judgement_2026-10-13/scripts'
A = 'roundT_squareT_pressureGate_squareT'
C = 'roundT_pressureGate_roundT'
R3 = Path('/tmp/opencode/r3-h1')
parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['physical', 'probes'])
parser.add_argument('--revision', default='')
parser.add_argument('--candidate-only', action='store_true')
options = parser.parse_args()
suffix = '-' + options.revision if options.revision else ''


def physical():
    helpers = runpy.run_path(str(ROOT / 'tests/test_column_collision_core.py'))
    cast, matched, stop = (helpers[n] for n in ['physical_column', 'matched', 'stop_history'])
    result = dict(component=[], full=[], outside=[], source=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
    off = DetectorConfig()
    off.cluster.column_core_margin = 0
    for distance in [37., 67., 109., 137.]:
        for lateral in [-.68, .68]:
            for top, absorbing in [(2.72, None), (3.22, None), (4.12, None), (4.12, (2.54, 4.12))]:
                xyz, ring, labels = cast(distance=distance, lateral=lateral, top=top, absorbing=absorbing)
                record = dict(distance=distance, lateral=lateral, top=top, absorbing=absorbing,
                              object_points=int((labels == 1).sum()), xyz_sha256=hashlib.sha256(xyz.tobytes()).hexdigest())
                for side, cfg in [('off', off), ('on', DetectorConfig())]:
                    cc = matched(xyz, ring, labels, cfg=cfg)
                    record[side] = [dict(zone=c.zone, reason=c.reason, core=c.collision_core, voxels=c.n_gauge,
                                         h=[c.height_min, c.height_max], observed_y=[float(xyz[c.points_idx, 1].min()),
                                                                                float(xyz[c.points_idx, 1].max())],
                                         stop=any(stop(c))) for c in cc]
                result['component'].append(record)
                xyz, ring, labels = cast(distance=distance, lateral=lateral, top=top, absorbing=absorbing, rails=True)
                record = dict(distance=distance, lateral=lateral, top=top, absorbing=absorbing,
                              object_points=int((labels == 1).sum()))
                for side, cfg in [('off', off), ('on', DetectorConfig())]:
                    d = Detector(copy.deepcopy(cfg))
                    rows = []
                    for i in range(14):
                        r = d.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
                        hit = any(abs(t.distance - distance) < 1 and abs(t.center[1] - lateral) < .5 for t in r.detections)
                        rows.append(dict(i=i, hit=hit, obstacle=r.obstacle, track=r.track.to_dict(),
                                         dets=[t.to_dict() for t in r.detections],
                                         candidates=[dict(reason=c.reason, core=c.collision_core,
                                                          distance=c.distance, lateral=c.lateral) for c in r.candidates]))
                    record[side] = rows
                result['full'].append(record)
    # Larger error controls are reported, not passed off as inside the registered budget.
    for distance in [37., 67., 109., 137.]:
        for lateral in [-1.29, 1.29, -1.5, 1.5]:
            xyz, ring, labels = cast(distance=distance, lateral=lateral, top=4.12)
            for error in [-.6, -.3, 0., .3, .6]:
                cc = matched(xyz, ring, labels, axis_error=error)
                record = dict(distance=distance, lateral=lateral, error=error, core=any(c.collision_core for c in cc),
                              matched_stop=any(any(stop(c)) for c in cc))
                result['outside'].append(record)
                if abs(error) <= .3:
                    assert not record['core'] and not record['matched_stop'], record
    with (HERE / f'physical-sweep{suffix}.json').open('x') as f:
        json.dump(result, f, indent=2)
    for case in result['full']:
        print('physical full', case['distance'], case['lateral'], case['top'], case['absorbing'],
              sum(r['hit'] for r in case['off']), '->', sum(r['hit'] for r in case['on']), flush=True)


def probes():
    jobs = []
    out = WORK / f'supplement{suffix}'
    out.mkdir(exist_ok=False)
    for side, repo in [('reference', REF), ('candidate', ROOT)]:
        if options.candidate_only and side == 'reference':
            continue
        for name, args in [
            ('E6', [J / 'range_test.py', R3 / 'baseline/cache' / A, R3 / 'baseline' / f'icp_{A}.json',
                    out / f'{side}-E6', '--obj', '0.05,0.05,2.6', '--start', '150', '--d0', '230', '--end', '340', '--base', '0.2']),
            ('A-axis', [J / 'range_test.py', R3 / 'baseline/cache' / A, R3 / 'baseline' / f'icp_{A}.json',
                        out / f'{side}-A-axis', '--obj', '0.3,0.3,2.8', '--start', '150', '--d0', '230', '--end', '340']),
            ('C-person', [J / 'range_test.py', R3 / 'supplement-range/decoded' / C, R3 / 'supplement-range' / f'icp_{C}.json',
                          out / f'{side}-C-person', '--obj', '0.5,0.5,1.75', '--start', '0', '--d0', '230']),
            ('Falcon', [J / 'probe.py', '/tmp/opencode/l16-s3/falcon-decoded', out / f'{side}-Falcon'])]:
            jobs.append((f'supplement{suffix}-{side}-{name}', repo, [sys.executable, *args]))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda job: run(*job), jobs))
    assert not any(results)


if __name__ == '__main__':
    {'physical': physical, 'probes': probes}[options.mode]()
