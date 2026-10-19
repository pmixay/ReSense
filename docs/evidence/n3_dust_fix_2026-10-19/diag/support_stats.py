"""Diagnostic only: local-support statistics of corridor candidate returns by truth class.
Truth (generated vs real, label bbox) is used for this analysis only."""
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame, axis_matrix
from resense import dust
from dust_reference import augment_in_reference, process_clean_reference
p = argparse.ArgumentParser()
p.add_argument("--cache", type=Path, required=True); p.add_argument("--bag", required=True)
p.add_argument("--level", required=True); p.add_argument("--every", type=int, default=5)
p.add_argument("--radius", default="0.10:0.004")  # a:tan  r = a + R*tan
a = p.parse_args()
r0, rt = map(float, a.radius.split(":"))
cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")); cfg.calibration.enabled = True
folder = a.cache / a.bag; meta = json.loads((folder / "meta.json").read_text())
labels = json.loads((ROOT / "labels" / f"{a.bag}.json").read_text()) if (ROOT / "labels" / f"{a.bag}.json").exists() else {}
rot = axis_matrix(cfg.sensor).astype(np.float32)
clean, dusty = Detector(cfg), Detector(cfg)
stats = {}
def add(cls, R, nb):
    for lo in range(0, 80, 10):
        m = (R >= lo) & (R < lo + 10)
        if m.any():
            s = stats.setdefault((cls, lo), [])
            s.extend(nb[m].tolist())
for i, m in enumerate(meta):
    with np.load(folder / f"f_{i:05d}.npz") as d:
        fr = Frame(d["xyz"] @ rot.T, d["inten"], d["ring"] if m["has_ring"] else None, m["stamp"], m["frame_id"],
                   {"n_raw": m["n_raw"], "n_near": m["n_near"]})
    cres, ref = process_clean_reference(clean, fr)
    if a.level == "clean":
        dfr, src = fr, np.arange(fr.n); det = clean; res = cres
    else:
        dfr, audit, src = augment_in_reference(fr, dust.PRESETS[a.level], ref, seed=20261018, frame_index=i)
        res = dusty.process(dfr); det = dusty
    if i % a.every:
        continue
    xyz = det._frame_xyz
    ci = np.asarray(res.corridor_idx); ci = ci[(ci >= 0) & (ci < len(xyz))]
    roi = (xyz[:, 0] > 0) & (xyz[:, 0] < 250) & (np.abs(xyz[:, 1]) < 8)
    tree = cKDTree(xyz[roi])
    P = xyz[ci]; R = np.linalg.norm(P, axis=1)
    nb = tree.query_ball_point(P, r0 + R * rt, return_length=True) - 1
    real = src[ci] >= 0
    obj = np.zeros(len(ci), bool)
    for lab in labels.get(f"{i:05d}", []):
        if lab.get("bbox") and lab.get("n_points", 0) > 0:
            lo, hi = np.asarray(lab["bbox"]); obj |= ((dfr.xyz[ci] >= lo) & (dfr.xyz[ci] <= hi)).all(1)
    add("dust", R[~real], nb[~real]); add("object", R[real & obj], nb[real & obj]); add("other_real", R[real & ~obj], nb[real & ~obj])
for (cls, lo), v in sorted(stats.items()):
    v = np.array(v)
    print(f"{cls:10s} {lo:3d}-{lo+10:3d}m n={len(v):7d} " + " ".join(f">={k}:{(v>=k).mean():.3f}" for k in (1, 2, 3, 4, 6, 8)))
