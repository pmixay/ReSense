#!/usr/bin/env python3
"Full-frame raw geometry proposal sweep. Intensity-only candidates are NOT labels. Use --every1 for the evidence sweep."

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
from sklearn.cluster import DBSCAN

matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument("cache")
p.add_argument("out")
p.add_argument("--every", type=int, default=4)
p.add_argument("--end", type=int, default=100000)
a = p.parse_args()
rows = []
hist = []
frames = []
for path in sorted(Path(a.cache).glob("f_*.npz")):
    k = int(path.stem[2:])
    if k % a.every or k >= a.end:
        continue
    d = np.load(path)
    P = d["xyz"][:, [1, 0, 2]].copy()
    P[:, 0] *= -1
    intensity = d["inten"]
    m = (
        (P[:, 0] > 2.5)
        & (P[:, 0] < 250)
        & (abs(P[:, 1]) < 120)
        & (P[:, 2] > -4)
        & (P[:, 2] < 4)
        & (intensity == 1)
    )
    q = P[m]
    h = np.histogram(q[:, 0], bins=np.arange(0, 251, 0.25))[0]
    hist.append(h)
    frames.append(k)
    # Forward scale clusters link angularly sparse object returns without fusing them longitudinally.
    q = q[np.unique(np.floor(q / 0.12).astype(np.int32), axis=0, return_index=True)[1]]
    sc = q.copy()
    sc[:, 1] *= 0.7
    sc[:, 2] *= 0.7
    labs = DBSCAN(eps=0.65, min_samples=2).fit_predict(sc)
    for lab in np.unique(labs[labs >= 0]):
        v = q[labs == lab]
        lo = v.min(0)
        hi = v.max(0)
        size = hi - lo
        if size[0] > 4 or size[1] > 4 or size[2] > 4:
            continue
        rows.append(
            {
                "k": k,
                "lo": lo.round(5).tolist(),
                "hi": hi.round(5).tolist(),
                "n": len(v),
            }
        )
    if k % 100 == 0:
        print(k, len(q), len(rows), flush=True)
Path(a.out).parent.mkdir(exist_ok=True, parents=True)
Path(a.out + ".json").write_text(json.dumps(rows))
fig, axs = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
axs[0].imshow(
    np.log1p(hist),
    aspect="auto",
    origin="lower",
    extent=[0, 250, frames[0], frames[-1]],
    cmap="magma",
)
rs = np.array(
    [
        [r["k"], (r["lo"][0] + r["hi"][0]) / 2, (r["lo"][1] + r["hi"][1]) / 2, r["n"]]
        for r in rows
        if r["hi"][0] - r["lo"][0] < 1
        and abs(r["lo"][1]) < 3.5
        and abs(r["hi"][1]) < 3.5
        and r["lo"][2] > -1.45
    ]
)
axs[1].scatter(
    rs[:, 1],
    rs[:, 0],
    c=rs[:, 2],
    s=np.clip(rs[:, 3], 2, 25),
    cmap="coolwarm",
    vmin=-3,
    vmax=3,
)
for ax in axs:
    ax.set_xlim(0, 250)
    ax.set_ylabel("frame")
axs[1].set_xlabel("sensor-forward m")
fig.tight_layout()
fig.savefig(a.out + ".png", dpi=110)
