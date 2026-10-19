"""Diagnostic: distribution of the guard's isolated-interior density per frame, measured on the
detector's own processed frame (guard disabled in the detector, assessment run alongside)."""
import argparse, json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.dust_guard import DustGuard
from resense.frame import Frame, axis_matrix
from resense import dust
from dust_reference import augment_in_reference, process_clean_reference
p = argparse.ArgumentParser()
p.add_argument("--cache", type=Path, required=True); p.add_argument("--bags", required=True)
p.add_argument("--levels", default="clean"); p.add_argument("--atten-only", action="store_true"); p.add_argument("--seed", type=int, default=7)
a = p.parse_args()
for bag in a.bags.split(","):
    folder = a.cache / bag; meta = json.loads((folder / "meta.json").read_text())
    for level in a.levels.split(","):
        cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")); cfg.calibration.enabled = True
        rot = axis_matrix(cfg.sensor).astype(np.float32)
        clean, dusty = Detector(cfg), Detector(cfg)
        g = DustGuard(replace(cfg.dust, on_density=1e-12, on_spread=0.0))
        dens = []
        for i, m in enumerate(meta):
            with np.load(folder / f"f_{i:05d}.npz") as d:
                fr = Frame(d["xyz"] @ rot.T, d["inten"], d["ring"] if m["has_ring"] else None, m["stamp"], m["frame_id"],
                           {"n_raw": m["n_raw"], "n_near": m["n_near"]})
            cres, ref = process_clean_reference(clean, fr)
            det = clean
            if level != "clean":
                dfr, _, _ = augment_in_reference(fr, replace(dust.PRESETS[level], density=0.0) if a.atten_only else dust.PRESETS[level], ref, seed=a.seed, frame_index=i)
                dusty.process(dfr); det = dusty
            st = g.assess(det._frame_xyz, det._dy_rail, det._frame_hd[1])
            dens.append((st["isolated_density"], st["interior_returns"], st["field_density"], st["isolated_spread"]))
        d = np.array(dens)
        print(f"{bag:38s} {level:6s} iso/m3 p50 {np.median(d[:,0]):.3f} p99 {np.percentile(d[:,0],99):.3f} max {d[:,0].max():.3f} (frame {int(d[:,0].argmax())}) "
              f"spread p50 {np.median(d[:,3]):.3f} max {d[:,3].max():.3f} both(>=.3,>=.35) {((d[:,0]>=.3)&(d[:,3]>=.35)).sum()} interior p50 {np.median(d[:,1]):.0f} max {d[:,1].max():.0f} field p50 {np.median(d[:,2]):.2f} | frames >=0.3: {(d[:,0]>=0.3).sum()} >=0.15: {(d[:,0]>=0.15).sum()}", flush=True)
