import sys, os, json, numpy as np
J = os.path.join(os.environ["RESENSE_REPO"], "docs/evidence/judgement_2026-10-13/scripts")
sys.path.insert(0, J)
from judge_runner import NodeReplica
from range_test import load_cache, run_frame
cache = "/data/decoded_f1/roundT_squareT_pressureGate_squareT"
meta, files = load_cache(cache)
rep = NodeReplica()
out = {}
for k, (m, f) in enumerate(zip(meta, files)):
    if k > 306: break
    d = np.load(f)
    res = run_frame(rep, d["xyz"], d["inten"], d["ring"], m, k)
    if k in (300, 306):
        det = rep.detector
        X = det._frame_xyz[:, 0]; h = det._frame_hd[1]; dy = det._dy_rail
        sel = (X > 20) & (X < 60) & (np.abs(dy) < 1.4) & (h > -0.5) & (h < 0.4)
        np.savez_compressed(os.environ["SP"] + f"/band_{k}.npz", X=X[sel], dy=dy[sel], h=h[sel])
        print(k, "rail_z(45)", float(det.track.rail_z(45.0)), "center", det.track.center, "curv", det.track.curvature, "floor", det.track.floor_coef, det.track.floor_range, det.track.rail_slabs)
