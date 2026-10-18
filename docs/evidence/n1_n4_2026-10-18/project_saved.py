#!/usr/bin/env python3
"""Display-only parameter check on saved, rounded Result rows; never reruns detector.

Final acceptance uses replay_gauge.py directly on full precision detector results.
"""
import argparse
import dataclasses
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from resense.track import TrackModel  # noqa: E402
from ros2_ws.src.resense_ros.resense_ros.gauge_display import GaugeDisplay  # noqa: E402


def project(path):
    rows = [json.loads(line) for line in gzip.open(path, 'rt')]
    fields = {field.name for field in dataclasses.fields(TrackModel)}
    clock = [0.]
    display = GaugeDisplay(clock=lambda: clock[0])
    output = []
    for row in rows:
        track = TrackModel(**{k: v for k, v in row['track'].items() if k in fields})
        clock[0] = row['stamp']
        state = display.update(track, row['stamp'], row['health'], row['display_speed_mps'])
        at = np.array([40, 80, 120])
        output.append({'state': state, 'raw': np.column_stack((track.center_y(at), track.rail_z(at))),
                       'shown': np.column_stack((display.center[at], display.rail[at])) if display.center is not None else None})
    jitter = {}
    for j, distance in enumerate((40, 80, 120)):
        visible = [(a,b) for a,b in zip(output, output[1:]) if a['state']['valid'] and b['state']['valid'] and min(a['state']['solid_range_m'], b['state']['solid_range_m']) >= distance]
        all_pairs = [(a,b) for a,b in zip(output, output[1:]) if a['shown'] is not None and b['shown'] is not None]
        def p90(pairs, key):
            return float(np.percentile([np.linalg.norm(b[key][j]-a[key][j]) for a,b in pairs],90)) if pairs else None
        jitter[distance] = {'visible_pairs':len(visible), 'all_adjacent_pairs':len(rows)-1,
                            'raw_supported_pairs':sum(min(a['track']['axis_valid'],b['track']['axis_valid'],
                                                         a['health'].get('monitored_range',0),b['health'].get('monitored_range',0))>=distance
                                                      for a,b in zip(rows,rows[1:])),
                            'visible_raw_3d_p90_m':p90(visible,'raw'), 'visible_display_3d_p90_m':p90(visible,'shown'),
                            'all_state_raw_3d_p90_m':p90(all_pairs,'raw'), 'all_state_display_3d_p90_m':p90(all_pairs,'shown')}
    return {'frames':len(rows), 'jitter':jitter, 'median_drawn_m':float(np.median([r['state']['drawn_range_m'] for r in output])),
            'median_support_m':float(np.median([r['state'].get('support_range_m',0) for r in output])),
            'max_spatial_lag_m':max(r['state'].get('max_spatial_lag_m',0) for r in output),
            'missing_GO_STOP_outline_frames':[row['frame'] for row,o in zip(rows,output) if row['decision'] in ('GO','STOP') and o['state']['drawn_range_m']<=3],
            'source_rows_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rows',type=Path,nargs='+')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result={'scope':'display-only projection on saved rounded detector rows; full source unchanged detector replay follows',
            'gauge_sha256':hashlib.sha256((ROOT/'ros2_ws/src/resense_ros/resense_ros/gauge_display.py').read_bytes()).hexdigest(),
            'bags':{p.name:project(p) for p in args.rows}}
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
