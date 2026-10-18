"""Independent check of P1's explicit sideways-mount axes: P4 remount transform + launch axes, vs plain run."""
import glob, json, os, sys
from pathlib import Path
import numpy as np
JUDGE = "/home/user/ReSense/docs/evidence/judgement_2026-10-13/scripts"; sys.path.insert(0, JUDGE)
from judge_runner import NodeReplica, node_decision
from range_test import run_frame
from resense.frame import axis_matrix
CASES = {4: ([[1,0,0],[0,0,1],[0,-1,0]], ("-y", "-z", "+x")), 5: ([[1,0,0],[0,0,-1],[0,1,0]], ("-y", "+z", "-x")),
         0: ([[1,0,0],[0,1,0],[0,0,1]], None)}
cache, case, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
Rt, axes = np.array(CASES[case][0], float), CASES[case][1]
meta = json.loads(Path(cache, "meta.json").read_text()); files = sorted(glob.glob(os.path.join(cache, "f_*.npz")))
Rvs = NodeReplica().R_vs.astype(np.float64)
ov = {} if axes is None else {"sensor.forward": axes[0], "sensor.left": axes[1], "sensor.up": axes[2]}
rep = NodeReplica(overrides=ov)
rows = []
for k, (m, f) in enumerate(zip(meta, files)):
    d = np.load(f); xyz = d["xyz"]
    xs = ((xyz.astype(np.float64) @ Rvs.T @ Rt.T) @ Rvs).astype(np.float32) if case else xyz
    if k == 0:   # the corrected vehicle cloud must equal the upright one
        up = xyz.astype(np.float64) @ Rvs.T; corr = xs.astype(np.float64) @ rep.R_vs.astype(np.float64).T
        print("max |corrected - upright| m:", float(np.abs(up - corr).max()), flush=True)
    res = run_frame(rep, xs, d["inten"], d["ring"], m, k)
    st = rep.detector.calib.state
    rows.append({"i": k, "decision": node_decision(res), "status": st.status, "orientation": st.orientation,
                 "n_det": len(getattr(res, "detections", []) or []), "nearest": getattr(res, "nearest_obstacle_m", None)})
json.dump(rows, open(out, "w"))
from collections import Counter
print(case, Path(cache).name, Counter(r["decision"] for r in rows))
