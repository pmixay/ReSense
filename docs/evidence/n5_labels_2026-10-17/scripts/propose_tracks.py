#!/usr/bin/env python3
"Raw geometry temporal proposal tracker. This has known background-attachment failures; only reviewed_boxes_*.json are accepted annotations. The recorded manual near-pass correction is required."

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
p.add_argument("spec")
p.add_argument("out")
a = p.parse_args()
spec = json.loads(Path(a.spec).read_text())
files = sorted(Path(a.cache).glob("f_*.npz"))
result = {s["name"]: {} for s in spec}
# Independent backward/forward local motion tracking from manually reviewed raw geometry seeds.
for s in spec:
    seed = s["seed"]
    sz = np.array(s["size"])
    center = np.array(s["center"])
    track = {}
    for direction in [1, -1]:
        prev = center.copy()
        history = []
        positions = []
        miss = 0
        for k in range(seed, len(files) if direction == 1 else -1, direction):
            if miss > 24:
                break
            if k < s.get("start", 0) or k > s.get("end", len(files) - 1):
                break
            if history:
                gaps = (
                    np.array([b[0] - c[0] for c, b in zip(history[-6:], history[-5:])])
                    if len(history) > 6
                    else np.diff([h[0] for h in history])
                )
                vals = np.diff([h[1] for h in history[-6:]])
                velocity = (
                    float(np.median(vals / gaps[-len(vals) :])) if len(vals) else -0.9
                )
                velocity = np.clip(velocity, -3.2, 0.08)
                pred = prev[0] + velocity * (k - history[-1][0])
            else:
                pred = center[0]
            pred_y = prev[1]
            if len(positions) >= 2:
                ka, pa = positions[-min(6, len(positions))]
                kb, pb = positions[-1]
                pred_y = prev[1] + np.clip((pb[1] - pa[1]) / (kb - ka), -2, 2) * (
                    k - kb
                )
            if pred < 2 or pred > 252:
                break
            d = np.load(files[k])
            P = d["xyz"][:, [1, 0, 2]].copy()
            P[:, 0] *= -1
            intensity = d["inten"]
            m = (
                (intensity == 1)
                & (abs(P[:, 0] - pred) < max(3.5, miss * 0.8))
                & (abs(P[:, 1] - pred_y) < sz[1] / 2 + 0.45)
                & (P[:, 2] > center[2] - sz[2] / 2 - 0.18)
                & (P[:, 2] < center[2] + sz[2] / 2 + 0.18)
            )
            q = P[m]
            core = q[q[:, 2] > center[2] - sz[2] * 0.1] if s.get("core", True) else q
            if len(core):
                q = core
            if not len(q):
                miss += 1
                continue
            qv = q[
                np.unique(
                    np.floor(q / 0.08).astype(np.int32), axis=0, return_index=True
                )[1]
            ]
            labs = DBSCAN(eps=0.38, min_samples=1).fit_predict(qv)
            cands = []
            for lab in np.unique(labs):
                vv = qv[labs == lab]
                lo = vv.min(0)
                hi = vv.max(0)
                cc = (lo + hi) / 2
                if np.any(hi - lo > sz + np.array([0.7, 0.5, 0.5])):
                    continue
                cost = (
                    abs(cc[0] - pred)
                    + 1.7 * abs(cc[1] - pred_y)
                    + abs(cc[2] - center[2])
                    - 0.18 * np.log1p(len(vv))
                )
                cands.append((cost, cc, lo, hi))
            if not cands:
                miss += 1
                continue
            cost, cc, lo, hi = min(cands, key=lambda t: t[0])
            q = P[m]
            inside = (abs(q[:, 0] - cc[0]) < sz[0] / 2 + 0.12) & (
                abs(q[:, 1] - cc[1]) < sz[1] / 2 + 0.12
            )
            v = q[inside]
            track[k] = {
                "lo": v.min(0).tolist(),
                "hi": v.max(0).tolist(),
                "n": len(v),
                "cost": cost,
                "prediction": pred,
            }
            prev = (v.min(0) + v.max(0)) / 2
            history.append((k, prev[0]))
            positions.append((k, prev.copy()))
            miss = 0
    result[s["name"]] = track
    print(
        s["name"],
        len(track),
        min(track) if track else None,
        max(track) if track else None,
        flush=True,
    )
Path(a.out + ".json").write_text(json.dumps(result))
fig, axs = plt.subplots(3, 1, figsize=(16, 14), sharex=True)
for name, tt in result.items():
    ks = sorted(map(int, tt))
    rs = [tt[k] for k in ks]
    c = (np.array([r["lo"] for r in rs]) + np.array([r["hi"] for r in rs])) / 2
    for j, ax in enumerate(axs):
        ax.plot(ks, c[:, j], ".-", label=name)
        ax.set_ylabel(["forward", "left", "up"][j] + " m")
        ax.legend()
axs[-1].set_xlabel("frame")
fig.tight_layout()
fig.savefig(a.out + ".png", dpi=100)
