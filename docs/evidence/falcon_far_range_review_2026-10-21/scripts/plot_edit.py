"""Top views (raw frame, lateral to the track reference) of one frame before and after the scene edits: look at it."""
import json, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.argv += []
import os
os.environ.setdefault("RESENSE_REPO", "/home/user/wt_cand")
sys.path.insert(0, "/home/user/rv/s")
import scene_run as S
specs = sys.argv[1:-1]; out = sys.argv[-1]
fig, ax = plt.subplots(len(specs) + 1, 1, figsize=(14, 2.6 * (len(specs) + 1)), sharex=True)
f = 2800
d = np.load(f"/home/user/data/falcon/f_{f:05d}.npz"); xyz = d["xyz"]
def show(a, p, title):
    x = p[:, 0]; lat = p[:, 1] - (S.TRACK["a"] + S.TRACK["b"] * x); h = p[:, 2] - (S.TRACK["z0"] + S.TRACK["c"] * x)
    m = (x > 40) & (x < 320) & (np.abs(lat) < 7) & (h > -0.5) & (h < 4.5)
    a.scatter(x[m], lat[m], s=0.3, c=h[m], cmap="viridis", vmin=-1, vmax=4.5); a.set_title(title, fontsize=9); a.set_ylim(-7, 7); a.grid(alpha=.3)
show(ax[0], xyz, f"frame {f} original")
for a, sp in zip(ax[1:], specs):
    spec = json.load(open(sp))
    k = 30 if spec.get("scroll") else 0
    src = xyz if not spec.get("scroll") else np.load(f"/home/user/data/falcon/f_{spec['scroll']['base_frame']:05d}.npz")["xyz"]
    p, _ = S.edit(src, k, spec)
    show(a, p, os.path.basename(sp) + (f" (window frame {k})" if k else ""))
ax[-1].set_xlabel("raw x (m)")
plt.tight_layout(); plt.savefig(out, dpi=90)
