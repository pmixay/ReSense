"""Independent raw SQLite/CDR and NumPy-view input checks for the author suite."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np

repo = Path('/home/aiops/resense')
here = repo / 'docs/evidence/l16_s3_2026-10-19'
cache = Path('/tmp/opencode/l16-s3/falcon-decoded')
db = Path('/tmp/opencode/l16-s3/falcon_test_second_dark/falcon_test_second_dark_0.db3')
sys.path.insert(0, str(repo / 'ros2_ws/src/resense_ros'))
from resense_ros import fastcloud  # noqa: E402

reference = json.loads((repo / 'docs/evidence/n2_falcon_2026-10-18/playback_subset_receipt.json').read_text())
metadata = json.loads((cache / 'meta.json').read_text())
con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
topic_id = con.execute("SELECT id FROM topics WHERE name='/iv_points'").fetchone()[0]
count = con.execute('SELECT count(*) FROM messages WHERE topic_id=?', [topic_id]).fetchone()[0]
assert count == len(metadata) == 4443
samples = {0, 1, 50, 99, 100, 500, 1000, 2000, 3000, 3800, 4200, 4370, 4400, 4442}
checks, raw_hashes, example = [], [], {}
types = {1: 'i1', 2: 'u1', 3: 'i2', 4: 'u2', 5: 'i4', 6: 'u4', 7: 'f4', 8: 'f8'}
for i, (timestamp, raw) in enumerate(con.execute('SELECT timestamp,data FROM messages WHERE topic_id=? ORDER BY timestamp', [topic_id])):
    assert metadata[i]['i'] == i and metadata[i]['bag_t'] == timestamp / 1e9
    if i < 100:
        raw_hashes.append(hashlib.sha256(raw).hexdigest())
    if i not in samples:
        continue
    msg = fastcloud.parse_pointcloud2(raw)
    fields = {f.name: f for f in msg.fields}
    endian = '>' if msg.is_bigendian else '<'
    dtype = np.dtype({'names': ['x', 'y', 'z'],
                      'formats': [endian + types[fields[n].datatype] for n in ('x', 'y', 'z')],
                      'offsets': [fields[n].offset for n in ('x', 'y', 'z')], 'itemsize': msg.point_step})
    points = np.ndarray((msg.height, msg.width), dtype=dtype, buffer=msg.data,
                        strides=(msg.row_step, msg.point_step)).reshape(-1)
    xyz = np.column_stack([points[n] for n in ('x', 'y', 'z')])
    radial = np.sqrt((xyz * xyz).sum(axis=1))
    good = np.isfinite(xyz).all(axis=1) & (radial >= 2.5) & (radial <= 250)
    manual = xyz[good].astype(np.float32)
    with np.load(cache / f'f_{i:05d}.npz') as d:
        saved = d['xyz']
    assert np.array_equal(manual, saved), i
    assert 'ring' not in fields and metadata[i]['has_ring'] is False
    checks.append({'frame': i, 'points': len(saved), 'exact_manual_numpy_view_match': True,
                   'raw_cdr_sha256': hashlib.sha256(raw).hexdigest(),
                   'positive_xyz_fraction': (saved > 0).mean(axis=0).tolist()})
    if i in (0, 3800, 4370):
        example[i] = saved
assert raw_hashes == reference['raw_cdr_sha256']
changed = bytearray(raw)
changed[-1] ^= 1
assert hashlib.sha256(changed).hexdigest() != hashlib.sha256(raw).hexdigest()
receipt = {'raw_sqlite_messages': count, 'cache_frames': len(metadata),
           'metadata_rows_compared': len(metadata), 'known_cdr_hashes_exact': len(raw_hashes),
           'manual_numpy_decode_samples': checks, 'changed_byte_positive_control': True}
(here / 'input_check.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2), flush=True)

import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
fig, axes = plt.subplots(2, 3, figsize=(13, 7))
for column, (i, xyz) in enumerate(example.items()):
    xyz = xyz[::max(1, len(xyz) // 14000)]
    for row, component in enumerate((1, 2)):
        axes[row, column].scatter(xyz[:, 0], xyz[:, component], s=.4, alpha=.5)
        axes[row, column].set(xlim=(0, 150), ylim=((-7, 7) if component == 1 else (-3, 6)),
                               xlabel='raw ROS forward X, m', ylabel=('left Y, m' if component == 1 else 'up Z, m'),
                               title=f'Falcon original frame {i}')
        axes[row, column].grid(alpha=.2)
fig.tight_layout()
fig.savefig(here / 'raw_falcon_examples.png', dpi=140)
