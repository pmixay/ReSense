"""Replay candidate A exactly, inspect raw support and histories of added alarms."""
import argparse
import json
from pathlib import Path

import numpy as np

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from resense.gauge import corridor_coordinates
from scripts.cache_io import cache_file_stem, cache_files, load_cache_array

HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-core')
DATA = Path('/tmp/opencode/resense-b4-data/cache')
p = argparse.ArgumentParser()
p.add_argument('piece')
a = p.parse_args()
rr = {s: [json.loads(x) for x in (WORK / f'gate-a-{s}-work' / f'{a.piece}.jsonl').read_text().splitlines()]
      for s in ['reference', 'candidate']}
added = {i for i, (b, c) in enumerate(zip(rr['reference'], rr['candidate'])) if c['obstacle'] and not b['obstacle']}
ids = {d['id'] for i in added for d in rr['candidate'][i]['detections']}
files = {cache_file_stem(f): f for f in cache_files(str(DATA / ('new_data' if a.piece.startswith('new_data') else a.piece)))}
d = Detector(DetectorConfig())
observed = []
out = WORK / f'inspect-a-{a.piece}'
out.mkdir(exist_ok=False)
for i, row in enumerate(rr['candidate']):
    key = row.get('frame_id') or f'{a.piece}_{i:04d}'
    f = frame_from_compact(load_cache_array(files[key]), d.cfg.sensor, stamp=row['stamp'], frame_id=key)
    r = d.process(f)
    assert [x.to_dict() for x in r.detections] == row['detections'], i
    assert [x.to_dict() for x in r.warnings] == row['warnings'], i
    tracks = [t for t in d.tracker.tracks if t.id in ids and t.last is not None]
    for t in tracks:
        c = t.last
        if not (c.collision_core or i in added):
            continue
        dy, h = corridor_coordinates(r.xyz, r.track)
        mask = (np.abs(r.xyz[:, 0] - c.distance) < 10) & (h > 0.3) & (h < 3.5)
        pts = c.points_idx if not t.misses else np.zeros(0, int)
        record = dict(i=i, added=i in added, id=t.id, core=c.collision_core, reason=c.reason,
                      reported=t.reported, zone=t.zone, column_hist=t.column_hist, zone_hist=t.zone_hist,
                      clean_run=t.clean_run, misses=t.misses, hits=t.hits,
                      size=c.size.tolist(), height=[c.height_min, c.height_max],
                      distance=c.distance, lateral=c.lateral, axis=r.track.to_dict(),
                      raw_points=r.xyz[pts].tolist(), raw_dy=dy[pts].tolist(), raw_h=h[pts].tolist())
        observed.append(record)
        if i in added or not any(x['id'] == t.id and x['core'] for x in observed[:-1]):
            np.savez_compressed(out / f'frame_{i:04d}_id{t.id}.npz', xyz=r.xyz[mask], dy=dy[mask], h=h[mask],
                                target=np.isin(np.flatnonzero(mask), pts))
result = dict(piece=a.piece, replayed=len(rr['candidate']), added=sorted(added), records=observed,
              all_detections_and_warnings_equal=True)
(out / 'trace.json').write_text(json.dumps(result, indent=2) + '\n')
print(a.piece, 'added', sorted(added), 'core observations', [(x['i'], x['id'], x['core'], x['distance'], x['lateral'])
                                                          for x in observed])
