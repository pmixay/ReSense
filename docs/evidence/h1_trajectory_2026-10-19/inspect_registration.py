"""Print raw sequence motion and failed initialization geometry."""
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

WORK = Path('/tmp/opencode/h1-reference')
ROOT = Path(__file__).resolve().parents[3]
with np.load('/tmp/opencode/r3-h1/baseline/cache/roundT_squareT_pressureGate_squareT/f_00000.npz') as data:
    print('CACHE', [(key, data[key].shape, str(data[key].dtype)) for key in data.files])
for name in ['A', 'C']:
    seq = json.loads((WORK / f'sequence-{name}-v2.json').read_text())['rows']
    for i in [0, 1, 25, 50, 100, 150, 200, 250]:
        row = seq[i]
        for key in ['pose', 'alternate_pose']:
            pose = np.array(row[key])
            print(name, i, key, 't', pose[:3, 3].round(3).tolist(), 'rxyz', Rotation.from_matrix(pose[:3, :3]).as_euler('xyz', degrees=True).round(3).tolist())
    old = json.loads((ROOT / 'docs/evidence/h1_reference_2026-10-19/direct-reference.json').read_text())['rows']
    row = next(r for r in old if r['sequence'] == name)
    for key in ['primary_seed', 'alternate_seed']:
        pose = np.array(row[key])
        print('SEED', name, row['frame'], row['future_frame'], key, 't', pose[:3, 3].round(3).tolist(), 'rxyz', Rotation.from_matrix(pose[:3, :3]).as_euler('xyz', degrees=True).round(3).tolist())
