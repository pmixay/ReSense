"""Diagnostic only: does the far-field low-density flip come through the track model?
The dusty detector's per-frame track model is replaced by the clean detector's (oracle)."""
import argparse, copy, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame, axis_matrix
from resense import dust
from dust_reference import augment_in_reference, process_clean_reference
p = argparse.ArgumentParser(); p.add_argument("--bag"); p.add_argument("--level"); p.add_argument("--seed", type=int, default=7); p.add_argument("--guard", action="store_true")
a = p.parse_args()
class Oracle(Detector):
    oracle = None
    def _fit_track(self, xyz_cfg, periods=1):
        xyz = super()._fit_track(xyz_cfg, periods)
        self.track = copy.deepcopy(self.oracle)
        return xyz
cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")); cfg.calibration.enabled = True; cfg.dust.enabled = a.guard
folder = Path("/data/decoded") / a.bag; meta = json.loads((folder / "meta.json").read_text())
rot = axis_matrix(cfg.sensor).astype(np.float32)
c, d, o = Detector(cfg), Detector(cfg), Oracle(cfg)
st = {"clean": [], "dusty": [], "oracle_track": []}
for i, m in enumerate(meta):
    with np.load(folder / f"f_{i:05d}.npz") as z:
        fr = Frame(z["xyz"] @ rot.T, z["inten"], z["ring"], m["stamp"], m["frame_id"], {"n_raw": m["n_raw"], "n_near": m["n_near"]})
    cr, ref = process_clean_reference(c, fr)
    dfr, _, _ = augment_in_reference(fr, dust.PRESETS[a.level], ref, seed=a.seed, frame_index=i)
    o.oracle = c.track
    for k, det in (("dusty", d), ("oracle_track", o)):
        if det.process(dfr).obstacle: st[k].append(i)
    if cr.obstacle: st["clean"].append(i)
for k, f in st.items():
    print(k, len(f), "episodes", sum(1 for j, x in enumerate(f) if j == 0 or f[j-1] != x - 1))
