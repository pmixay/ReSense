"""Diagnostic only: STOP frames under generator ablations (injection-only / attenuation-only)
and per-frame track/mount differences against the clean run."""
import argparse, json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame, axis_matrix
from resense import dust
from dust_reference import augment_in_reference, process_clean_reference
import yaml
p = argparse.ArgumentParser()
p.add_argument("--cache", type=Path, required=True); p.add_argument("--bag", required=True)
p.add_argument("--level", required=True); p.add_argument("--set", action="append", default=[])
p.add_argument("--seed", type=int, default=20261018); p.add_argument("--first", type=int, default=0); p.add_argument("--last", type=int, default=10**9); p.add_argument("--drop", type=float, default=0.02)
a = p.parse_args()
def make():
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")); cfg.calibration.enabled = True
    for o in a.set:
        k, v = o.split("=", 1); s, k = k.split(".", 1); setattr(getattr(cfg, s), k, yaml.safe_load(v))
    return cfg
base = dust.PRESETS[a.level]
variants = {"full": base, "inject_only": replace(base, extinction=0.0), "atten_only": replace(base, density=0.0),
            "uniform_drop": None}   # non-dust control: drop a uniform random share of ALL returns (--drop)
p2 = a.drop
folder = a.cache / a.bag; meta = json.loads((folder / "meta.json").read_text())
rot = axis_matrix(make().sensor).astype(np.float32)
clean = Detector(make()); dets = {k: Detector(make()) for k in variants}
stops = {k: [] for k in ["clean", *variants]}; last = None
diffs = {k: [] for k in variants}
for i, m in enumerate(meta):
    if i > a.last: break
    with np.load(folder / f"f_{i:05d}.npz") as d:
        fr = Frame(d["xyz"] @ rot.T, d["inten"], d["ring"] if m["has_ring"] else None, m["stamp"], m["frame_id"],
                   {"n_raw": m["n_raw"], "n_near": m["n_near"]})
    if last is not None:
        gap = fr.stamp - last
        if gap < -.5 or gap > 30:
            clean = Detector(make()); dets = {k: Detector(make()) for k in variants}
        elif gap > 1:
            clean.reset(); [d.reset() for d in dets.values()]
    last = fr.stamp
    cres, ref = process_clean_reference(clean, fr)
    if cres.obstacle: stops["clean"].append(i)
    for k, spec in variants.items():
        if spec is None:
            keep = np.random.default_rng([a.seed, i, 99]).random(fr.n) >= a.drop
            dfr = Frame(fr.xyz[keep], fr.intensity[keep], None if fr.ring is None else fr.ring[keep], fr.stamp, fr.frame_id,
                        {**fr.meta, "n_raw": int(fr.meta.get("n_raw", fr.n)) - int((~keep).sum())})
        else:
            dfr, _, _ = augment_in_reference(fr, spec, ref, seed=a.seed, frame_index=i)
        r = dets[k].process(dfr)
        if r.obstacle: stops[k].append(i)
        if i >= a.first:
            x = np.array([60., 100., 147.])
            diffs[k].append([float(np.abs(r.track.center_y(x) - cres.track.center_y(x))[2]),
                             float(np.abs(r.track.rail_z(x) - cres.track.rail_z(x))[2]),
                             float(np.degrees(np.arccos(np.clip((np.trace(dets[k].calib.R.T @ clean.calib.R) - 1) / 2, -1, 1))))])
def episodes(f):
    return sum(1 for j, x in enumerate(f) if j == 0 or f[j - 1] != x - 1)
for k, f in stops.items():
    extra = ""
    if k in diffs and diffs[k]:
        dd = np.array(diffs[k]); extra = f" |dy147| p50/p95 {np.median(dd[:,0]):.3f}/{np.percentile(dd[:,0],95):.3f} |dz147| {np.median(dd[:,1]):.3f}/{np.percentile(dd[:,1],95):.3f} dR deg {np.median(dd[:,2]):.3f}/{np.percentile(dd[:,2],95):.3f}"
    print(f"{k:12s} STOP {len(f):4d} episodes {episodes(f):3d}{extra}")
