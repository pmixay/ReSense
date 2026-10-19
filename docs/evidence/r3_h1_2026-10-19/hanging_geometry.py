"""Observe the real hanging-stage inputs, grouping and object returns."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'docs/evidence/judgement_2026-10-13/scripts')]
from judge_runner import NodeReplica  # noqa: E402
from range_test import run_frame  # noqa: E402
import resense.detector as D  # noqa: E402
import resense.clustering as C  # noqa: E402

DATA = Path('/tmp/opencode/resense-b4-data/decoded/cloud_with_fake_obj')
OUT = Path('/tmp/opencode/r3-h1/baseline')
labels = json.loads((ROOT / 'labels/cloud_with_fake_obj.json').read_text())
meta = json.loads((DATA / 'meta.json').read_text())
orig = D.find_hanging
rows = []
k = 0


def observed(xyz, intensity, dy, h, cfg, top, range_min, max_distance, in_gauge_idx=None):
    result = orig(xyz, intensity, dy, h, cfg, top, range_min, max_distance, in_gauge_idx)
    if k < 760:
        return result
    o = next((o for o in labels.get(f'{k:05d}', []) if o.get('label') == 'thin_hanging'), None)
    if o is None:
        return result
    X = o['distance']
    sel = np.flatnonzero((h > cfg.hanging_min_height) & (h <= top + cfg.hanging_link_band)
                        & (np.abs(dy) < cfg.hanging_max_lateral) & (xyz[:, 0] >= range_min)
                        & (xyz[:, 0] <= max_distance))
    groups = []
    if len(sel):
        vox, inv = C.voxelize(xyz[sel], cfg)
        labs = C.dbscan_labels(C._scaled(vox, cfg.range_scale), cfg.eps, 1)[inv]
        for lab in np.unique(labs):
            ids = sel[labs == lab]
            if not np.any(np.abs(xyz[ids, 0] - X) < .5):
                continue
            groups.append(dict(size=np.ptp(xyz[ids], axis=0).tolist(),
                               h_range=[float(h[ids].min()),float(h[ids].max())],
                               xyz=xyz[ids].tolist(),dy=dy[ids].tolist(), h=h[ids].tolist(),
                               in_gauge=np.isin(ids,in_gauge_idx).tolist()))
    near = np.abs(xyz[:, 0] - X) < .15
    row = dict(k=k,X=X,max_distance=max_distance,groups=groups,
               near_xyz=xyz[near].tolist(),near_h=h[near].tolist(),near_dy=dy[near].tolist(),
               outputs=[dict(d=c.distance,size=c.size.tolist()) for c in result])
    rows.append(row)
    print(k,round(X,2), 'max',round(max_distance,1),'groups',
          [(np.round(g['size'],2).tolist(),len(g['xyz'])) for g in groups], 'outputs',row['outputs'])
    return result


D.find_hanging = observed
rep = NodeReplica()
for k,m in enumerate(meta[:791]):
    with np.load(DATA / f'f_{k:05d}.npz') as d:
        run_frame(rep,d['xyz'],d['inten'],d['ring'],m,k)
(OUT / 'hanging_geometry.json').write_text(json.dumps(rows))
