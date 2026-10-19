"""Diagnostic only (not acceptance): per reported gauge detection, describe the current-frame
points of its track's last cluster with augmentation truth (real vs generated) and candidate
features. Truth is used for diagnosis only, never passed to the detector."""
import argparse, gzip, json, sys
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
p.add_argument("--level", required=True); p.add_argument("--out", type=Path, required=True)
p.add_argument("--set", action="append", default=[])
p.add_argument("--seed", type=int, default=20261018)
a = p.parse_args()
import yaml
def make():
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")); cfg.calibration.enabled = True
    for o in a.set:
        k, v = o.split("=", 1); s, k = k.split(".", 1); setattr(getattr(cfg, s), k, yaml.safe_load(v))
    return cfg
cfg = make()
folder = a.cache / a.bag; meta = json.loads((folder / "meta.json").read_text())
rot = axis_matrix(cfg.sensor).astype(np.float32)
clean, dusty = Detector(cfg), Detector(make())
out = gzip.open(a.out, "wt"); last = None
for i, m in enumerate(meta):
    with np.load(folder / f"f_{i:05d}.npz") as d:
        fr = Frame(d["xyz"] @ rot.T, d["inten"], d["ring"] if m["has_ring"] else None, m["stamp"], m["frame_id"],
                   {"n_raw": m["n_raw"], "n_near": m["n_near"]})
    if last is not None and (fr.stamp - last > 1 or fr.stamp - last < -.5):
        clean, dusty = Detector(cfg), Detector(make())   # battery resets; approximate
    last = fr.stamp
    cres, ref = process_clean_reference(clean, fr)
    if a.level == "clean":
        res, det, src = cres, clean, np.arange(fr.n)
        dfr = fr
    else:
        dfr, audit, src = augment_in_reference(fr, dust.PRESETS[a.level], ref, seed=a.seed, frame_index=i)
        res = dusty.process(dfr); det = dusty
    xyz = det._frame_xyz
    tree = None
    rows = []
    for dd in res.detections + res.warnings:
        t = next((t for t in det.tracker.tracks if t.id == dd.id), None)
        if t is None or t.last is None or t.misses: continue
        idx = np.asarray(t.last.points_idx, dtype=np.int64)
        real = src[idx] >= 0 if idx.size else np.zeros(0, bool)
        if tree is None:
            tree = cKDTree(xyz)
        P = xyz[idx]
        rng = np.linalg.norm(P, axis=1) if idx.size else np.zeros(0)
        r = .15 + rng * np.tan(np.radians(.2))
        nb = np.array([len(tree.query_ball_point(q, rr)) - 1 for q, rr in zip(P, r)]) if idx.size else np.zeros(0)
        rows.append({"id": dd.id, "zone": dd.zone, "dist": dd.distance, "reason": dd.reason, "kind": dd.kind,
                     "n_vox": dd.n_points, "n_idx": int(idx.size), "n_real": int(real.sum()),
                     "n_acc": int(t.last.n_raw - idx.size), "imax": float(dfr.intensity[idx].max()) if idx.size else None,
                     "size": [round(float(s), 2) for s in dd.size], "age": dd.age, "misses": t.misses,
                     "nb_ge2": int((nb >= 2).sum()), "nb_ge2_real": int(((nb >= 2) & real).sum())})
    out.write(json.dumps({"i": i, "stop": bool(res.obstacle), "clean_stop": bool(cres.obstacle), "dets": rows,
                          "speed": res.ego_speed, "axis": float(res.track.axis_valid), "n_acc": res.n_accumulated}) + "\n")
out.close()
