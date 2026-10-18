"""Read-only diagnostic of the superseded regular dust coordinate mismatch."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def main():
    clean_path = HERE / 'candidate_dark_person/doubleT_obstacle_clean.jsonl.gz'
    dusty_path = HERE / 'candidate_dark_person/doubleT_obstacle_medium.jsonl.gz'
    clean, dusty = read(clean_path), read(dusty_path)
    rows = []
    for index in (5, 50, 100, 200):
        row, audit = clean[index], dusty[index]['augmentation']
        mount, track = row['mount'], row['track']
        assert mount['orientation'] == 'configured'
        roll, pitch, yaw = np.radians([mount[key] for key in ('roll_deg', 'pitch_deg', 'yaw_deg')])
        cr, sr, cp, sp, cy, sy = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
        rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
        ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
        rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
        rotation = rz @ ry @ rx
        x = 20.
        z = float(np.polyval(track['floor_coef'], x) + track['rail_offset'])
        y = track['center'] + np.tan(track['yaw']) * x + .5 * track['curvature'] * x * x
        point = np.array([x, y, z])
        input_point = point @ rotation
        rows.append({'frame': index, 'recorded_dust_rail_z': audit['rail_z'],
                     'serialized_clean_model_rail_xyz': point.tolist(),
                     'estimated_same_point_input_xyz': input_point.tolist(),
                     'estimated_height_mismatch_m': audit['rail_z'] - float(input_point[2]),
                     'rounded_mount_angles_deg': {key: mount[key] for key in ('roll_deg', 'pitch_deg', 'yaw_deg')}})
    archived = HERE / 'pre_coordinate_harness/dust_battery_v1.py.gz'
    receipt = json.loads((archived.parent / 'manifest.json').read_text())
    assert sha(archived) == receipt['archive_sha256']
    assert hashlib.sha256(gzip.decompress(archived.read_bytes())).hexdigest() == receipt['source_sha256']
    result = {'scope': 'Regular v1 harness only. Set F used a separate pre-process legacy model; this specific mismatch is not established for Set F.',
              'finding': 'The v1 regular harness supplies post-mount clean rail_z to the pre-mount configured input cloud.',
              'precision': 'Diagnostic uses recorded mount angles rounded to 0.01 degree and rail offset/center rounded to 0.001m. At20m angular rounding contributes up to roughly2mm here. Exact source-level frame mismatch does not depend on these diagnostic approximations.',
              'clean_raw_sha256': sha(clean_path), 'medium_raw_sha256': sha(dusty_path),
              'archived_harness': receipt, 'rows': rows, 'review_script_sha256': sha(Path(__file__))}
    (HERE / 'independent_coordinate_review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
