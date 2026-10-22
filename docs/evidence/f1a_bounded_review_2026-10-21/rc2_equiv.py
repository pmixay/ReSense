"""Check: rc2.frame with default options == the repo's raycast.frame (bit for bit), on scenes with boxes."""
import os, sys
from pathlib import Path
import numpy as np
ROOT = os.environ["RESENSE_REPO"]; sys.path.insert(0, ROOT); sys.path.insert(0, str(Path(ROOT) / "docs/evidence/f1a_b1_2026-10-20"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import raycast as rc, rc2
rr = lambda x: np.where((x >= 32) & (x <= 70), 0.18, 0.0)
for k, boxes in enumerate([[], [(40.0, 40.3, 0.9, 1.2, -1.5, -1.27)], [(30.0, 34.0, -0.7, -0.4, -1.5, -1.0), (50, 50.3, 0.2, 0.5, -1.5, -1.3)]]):
    a = rc.frame(rail_raise=rr, boxes=boxes, seed=1000 * k + 7)
    b = rc2.frame(rail_raise=rr, boxes=[bx + (0.0,) for bx in boxes], seed=1000 * k + 7)
    same = a.xyz.shape == b.xyz.shape and np.array_equal(a.xyz, b.xyz) and np.array_equal(a.intensity, b.intensity)
    diff = None if a.xyz.shape != b.xyz.shape else float(np.abs(a.xyz - b.xyz).max())
    print(k, a.xyz.shape, b.xyz.shape, "identical" if same else f"DIFFER max {diff}")
# positive control: a box moved by 1 cm must change the cloud
a = rc.frame(rail_raise=rr, boxes=[(40.0, 40.3, 0.9, 1.2, -1.5, -1.27)], seed=7)
b = rc2.frame(rail_raise=rr, boxes=[(40.01, 40.31, 0.9, 1.2, -1.5, -1.27, 0.0)], seed=7)
print("positive control (box moved 1 cm) differs:", a.xyz.shape != b.xyz.shape or not np.array_equal(a.xyz, b.xyz))
