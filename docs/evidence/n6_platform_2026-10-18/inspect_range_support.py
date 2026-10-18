#!/usr/bin/env python3
"""Read-only limit of current raw paired-rail evidence near the 60m person target."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(key, '1')
SOURCE = Path('/home/resense/data/n6/source_745096f')
sys.path.insert(0, str(SOURCE))
import numpy as np  # noqa: E402
from resense.farrails import FarRailParams, far_rails, ring_pairs  # noqa: E402
from resense.track import TrackModel  # noqa: E402

HERE = Path(__file__).parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    probe_path = HERE / 'exact_source_rail_support.json'
    label_path = ROOT / 'docs/evidence/n5_labels_2026-10-17/labels_synthetic_platform.json'
    probe = json.loads(probe_path.read_text())
    labels = json.loads(label_path.read_text())
    params = FarRailParams(x_max=80., gauge=1.59, height_band=.3, cant=.1, max_gap=10.,
                           min_stations=3, pair_max_forward_gap=5., pair_use_nearer_forward=True)
    rows, inputs = [], {}
    for entry in probe['rows']:
        i = entry['frame']
        person = next((obj for obj in labels[f'{i:05d}'] if obj['label'] == 'obj03'), None)
        if person is None or not 60 <= person['distance'] <= 80:
            continue
        path = Path(f'/home/resense/data/decoded/synthetic_platform/f_{i:05d}.npz')
        with np.load(path) as cloud:
            raw = cloud['xyz']
            xyz = np.column_stack((-raw[:, 1], raw[:, 0], raw[:, 2]))
            rings = cloud['ring']
        model = TrackModel(**entry['pre_extension_model'])
        anchor = entry['variants']['synthetic']['near_seed']

        def ref_y(x):
            return model.center + float(np.tan(model.yaw)) * np.asarray(x, dtype=np.float64)

        candidates = ring_pairs(xyz, rings, ref_y, model.rail_z, anchor[0] + .5, params)
        selected = far_rails(xyz, rings, model, anchor, params)
        rows.append({'frame': i, 'person_forward_m': person['distance'],
                     'observed_validated_endpoint_m': entry['variants']['synthetic']['rail_axis_support'],
                     'range_with_existing_margin_m': entry['variants']['synthetic']['axis_valid'],
                     'raw_candidate_pairs': candidates.tolist(),
                     'raw_candidate_axis_residual_m': (candidates[:, 1] + ref_y(candidates[:, 0])
                                                       - model.center_y(candidates[:, 0])).tolist(),
                     'selected_station_x': selected.x.tolist(),
                     'selected_station_axis_residual_m': (selected.y - model.center_y(selected.x)).tolist()})
        inputs[str(path)] = sha(path)
    report = {'scope': 'Saved full-precision models on previously validated N6 extension frames while person distance60..80m. Raw candidate pairs are unclassified geometric proposals, not independent rail truth. This does not exhaust all possible raw rail algorithms or bound the physical LiDAR range. No detector replay or runtime modification.',
              'frames': len(rows), 'maximum_observed_validated_endpoint_m': max(row['observed_validated_endpoint_m'] for row in rows),
              'validated_endpoint_reaches_person_frames': [row['frame'] for row in rows if row['observed_validated_endpoint_m'] >= row['person_forward_m']],
              'existing_margin_reaches_person_frames': [row['frame'] for row in rows if row['range_with_existing_margin_m'] >= row['person_forward_m']],
              'maximum_validated_endpoint_all84_frames_m': max(row['variants']['synthetic']['rail_axis_support'] for row in probe['rows']),
              'raw_pair_at_or_beyond60_frames': [row['frame'] for row in rows if any(c[0] >= 60 for c in row['raw_candidate_pairs'])],
              'rows': rows, 'input_sha256': inputs, 'probe_sha256': sha(probe_path),
              'labels_sha256': sha(label_path), 'script_sha256': sha(Path(__file__)),
              'farrails_sha256': sha(SOURCE / 'resense/farrails.py')}
    (HERE / 'range_support_limit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('rows', 'input_sha256')}))


if __name__ == '__main__':
    main()
