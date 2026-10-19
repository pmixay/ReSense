"""Capture actual calibration/model state of the rejected ring-free startup."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

repo = Path('/tmp/opencode/l16-s3/rejected_candidate')
here = Path('/home/aiops/resense/docs/evidence/l16_s3_2026-10-19')
sys.path.insert(0, str(repo))
from resense import Detector, DetectorConfig  # noqa: E402
from resense.calibration import orientation_candidates  # noqa: E402
from resense.frame import Frame  # noqa: E402

cache = Path('/tmp/opencode/l16-s3/falcon-decoded')
meta = json.loads((cache / 'meta.json').read_text())
rotation = orientation_candidates()[4]
detectors = {k: Detector(DetectorConfig.from_yaml(str(repo / 'configs/default.yaml')))
             for k in ('correct', 'automatic_side', 'explicit_side')}
explicit = detectors['explicit_side'].calib
explicit._R_orient = rotation.T.copy()
explicit.state.R = rotation.T.copy()
explicit._config_passed = True
explicit.state.orientation_confirmed = True
rows = []
for i in range(32):
    with np.load(cache / f'f_{i:05d}.npz') as d:
        xyz, inten = d['xyz'], d['inten']
    state = {'frame': i}
    for name, detector in detectors.items():
        points = xyz if name == 'correct' else xyz @ rotation.T.astype(np.float32)
        result = detector.process(Frame(points, inten, stamp=meta[i]['stamp']))
        state[name] = deepcopy({'recent': detector.calib._recent, 'obs': detector.calib._obs,
                       'since_obs': detector.calib._since_obs,
                       'applied': detector.calib._applied, 'track': detector.track.to_dict(),
                       'track_age': detector.track.age, 'R': detector.mount_rotation.tolist(),
                       'STOP': result.obstacle, 'dets': [d.to_dict() for d in result.detections]})
    rows.append(state)
assert len(rows[0]['correct']['recent']) == 1
assert len(rows[0]['automatic_side']['recent']) == 0
assert all(r['correct']['recent'] == r['explicit_side']['recent'] for r in rows)
assert all(r['correct']['track'] == r['explicit_side']['track'] for r in rows)
assert any(r['correct']['track'] != r['automatic_side']['track'] for r in rows[1:])
invalid = json.loads((here / 'rejected_startup_snapshots.json').read_text())
assert len(invalid[0]['correct']['recent']) == 5
record = {'source': str(repo), 'source_sha256': {
              name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
              for name in ('resense/calibration.py', 'resense/detector.py')},
          'numpy_version': np.__version__, 'frames': rows,
          'snapshot_correction': 'Initial driver retained list aliases (frame 0 showed 5 future observations).'
                                 ' Corrected deep-copy snapshots show 1 correct / 0 automatic observations.'}
(here / 'rejected_startup_trace_verified.json').write_text(json.dumps(record, indent=2) + '\n')
for row in rows[:6]:
    print(json.dumps({'frame': row['frame'], **{name: {'recent': s['recent'], 'track_age': s['track_age'],
                                                    'applied': s['applied']}
                                              for name, s in row.items() if name != 'frame'}}, indent=1))
