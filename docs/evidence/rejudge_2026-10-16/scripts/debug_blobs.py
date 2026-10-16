"""Instrument resense.clustering._corridor_cluster during a range_test replay: log blobs that overlap the
inserted object's X at the chosen frames (why an object forms no candidate)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import resense.clustering as C
import resense.detector as D
frames = {int(k): float(v) for k, v in (x.split(":") for x in os.environ["DBG_FRAMES"].split(","))}
state = {"k": -1}
orig_proc = D.Detector.process
def proc(self, frame, ego_speed=None):
    state["k"] += 1
    return orig_proc(self, frame, ego_speed)
D.Detector.process = proc
orig = C._corridor_cluster
def wrapped(b, *a, **kw):
    r = orig(b, *a, **kw)
    X = frames.get(state["k"])
    if X is not None and b.pts[:, 0].min() < X + 1.0 and b.pts[:, 0].max() > X - 0.5:
        print(f"frame {state['k']} X={X}: blob x[{b.pts[:,0].min():.1f},{b.pts[:,0].max():.1f}] y[{b.pts[:,1].min():.2f},{b.pts[:,1].max():.2f}] "
              f"z[{b.pts[:,2].min():.2f},{b.pts[:,2].max():.2f}] size {np.round(b.size,2)} n_vox {b.n_vox} -> "
              f"{'DROPPED' if r is None else (r.zone, r.reason, r.n)}", file=sys.stderr)
    return r
C._corridor_cluster = wrapped
D._corridor_cluster = wrapped if hasattr(D, "_corridor_cluster") else None
import range_test  # noqa: E402 (after patching _corridor_cluster)
sys.argv = ["range_test.py"] + sys.argv[1:]
range_test.main()
