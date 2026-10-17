#!/usr/bin/env python3
"Development gap/near-pass probe, with session cache paths. Its output is a proposal requiring review, not ground truth."

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import DBSCAN

bag = sys.argv[1]
base = Path("/home/resense/data/n5")
specs = {s["name"]: s for s in json.loads((base / f"{bag}_specs.json").read_text())}
tracks = json.loads((base / f"{bag}_seed_tracks3.json").read_text())
out = {}
audit = {}
for name, t in tracks.items():
    s = specs[name]
    size = np.array(s["size"])
    ks = sorted(map(int, t))
    centers = np.array([(np.array(t[str(k)]["lo"]) + t[str(k)]["hi"]) / 2 for k in ks])
    added = []
    empty = []
    for k in range(ks[0], ks[-1] + 1):
        if str(k) in t:
            continue
        pred = np.array([np.interp(k, ks, centers[:, j]) for j in range(3)])
        d = np.load(f"/home/resense/data/decoded/synthetic_{bag}/f_{k:05}.npz")
        P = d["xyz"][:, [1, 0, 2]].copy()
        P[:, 0] *= -1
        mask = (
            (d["inten"] == 1)
            & (abs(P[:, 0] - pred[0]) < 2.5)
            & (abs(P[:, 1] - pred[1]) < size[1] / 2 + 0.7)
            & (abs(P[:, 2] - s["center"][2]) < size[2] / 2 + 0.25)
        )
        q = P[mask]
        if not len(q):
            empty.append(k)
            continue
        labels = DBSCAN(eps=0.5, min_samples=1).fit_predict(q)
        candidates = []
        for lab in np.unique(labels):
            v = q[labels == lab]
            lo = v.min(0)
            hi = v.max(0)
            cc = (lo + hi) / 2
            if np.any(hi - lo > size + [0.6, 0.5, 0.6]):
                continue
            score = (
                abs(cc[0] - pred[0])
                + abs(cc[1] - pred[1])
                + abs(cc[2] - pred[2])
                - 0.1 * np.log1p(len(v))
            )
            candidates.append((score, v))
        if not candidates:
            empty.append(k)
            continue
        cost, v = min(candidates, key=lambda s: s[0])
        t[str(k)] = {
            "lo": v.min(0).tolist(),
            "hi": v.max(0).tolist(),
            "n": len(v),
            "cost": cost,
            "prediction": pred[0],
            "recovered_gap": True,
        }
        added.append(k)
    # Review the first frame after the core-tracked lifespan; radial cutoff is not a forward cutoff.
    k = ks[-1] + 1
    if k < (736 if bag == "switch" else 545):
        delta = np.median(np.diff(centers[-6:], axis=0), axis=0)
        pred = centers[-1] + delta
        d = np.load(f"/home/resense/data/decoded/synthetic_{bag}/f_{k:05}.npz")
        P = d["xyz"][:, [1, 0, 2]].copy()
        P[:, 0] *= -1
        q = P[
            (d["inten"] == 1)
            & (abs(P[:, 0] - pred[0]) < 0.8)
            & (abs(P[:, 1] - pred[1]) < size[1] / 2 + 0.2)
            & (abs(P[:, 2] - s["center"][2]) < size[2] / 2 + 0.15)
        ]
        if len(q):
            t[str(k)] = {
                "lo": q.min(0).tolist(),
                "hi": q.max(0).tolist(),
                "n": len(q),
                "near_pass_extension": True,
            }
            added.append(k)
    out[name] = dict(sorted(t.items(), key=lambda kv: int(kv[0])))
    audit[name] = {
        "added": added,
        "no_marker_support_on_interpolated_path": empty,
        "frames": [min(map(int, t)), max(map(int, t))],
    }
    print(name, len(t), audit[name], flush=True)
(base / f"{bag}_reviewed_tracks.json").write_text(json.dumps(out, indent=1))
(base / f"{bag}_gap_review.json").write_text(json.dumps(audit, indent=1))
