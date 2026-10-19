"""Trace the remaining moving-body delay, with matched fixed-latency plain controls."""
import json
from pathlib import Path
import runpy
import sys

import numpy as np

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from scripts.range_attrib import TrackerTrace
import resense.tracking as tracking

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
revision = sys.argv[1]
cast = runpy.run_path(str(ROOT / 'tests/fixtures/h1_physical.py'))['physical_column']
normalize = runpy.run_path(str(ROOT / 'docs/evidence/integration_2026-10-16/h3_selected/helpers/frame_diff.py'))['normalize']
result = dict(revision=revision, cases=[])
for lateral in [-.68, .68]:
    runs = {}
    for mode in ['plain', 'traced']:
        d = Detector(DetectorConfig())
        tracer = TrackerTrace(tracking)
        saved = []
        for i in range(56):
            distance = 155 - 2.2 * i
            xyz, ring, labels = cast(distance=distance, lateral=lateral, top=4.12, rails=True)
            if d._previous_latency_ms is not None:
                d._previous_latency_ms = 42.
            if mode == 'traced':
                tracer.start()
            try:
                r = d.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
            finally:
                if mode == 'traced':
                    tracer.stop()
            saved.append(dict(i=i, distance=distance, result=normalize(r.to_dict())[0],
                core=any(c.collision_core for c in r.candidates),
                hit=any(abs(t.distance - distance) < 1 and abs(t.center[1] - lateral) < .5 for t in r.detections),
                tracks=[dict(id=t.id, misses=t.misses, hits=t.hits, reported=t.reported, zone=t.zone,
                             column_held=t.column_held, clean_run=t.clean_run, column_hist=t.column_hist.copy(),
                             zone_hist=t.zone_hist.copy(), qualifies=tracer.record.get(id(t), {}).get('qualifies'),
                             gates=tracer.record.get(id(t), {}).get('gates')) for t in d.tracker.tracks]))
        runs[mode] = saved
    for a, b in zip(runs['plain'], runs['traced'], strict=True):
        assert a['result'] == b['result'] and a['core'] == b['core'] and a['hit'] == b['hit']
    result['cases'].append(dict(lateral=lateral, frames=56, plain_traced_equal=True, rows=runs['traced']))
    print('MOVING', lateral, [(r['i'], round(r['distance'], 1), r['core'], r['hit'],
                              [(t['id'], t['column_held'], t['clean_run'], t['qualifies']) for t in r['tracks']])
                             for r in runs['traced'] if r['core'] or r['hit']])
out = HERE / f'moving-trace-{revision}.json'
with out.open('x') as f:
    json.dump(result, f, indent=2)
