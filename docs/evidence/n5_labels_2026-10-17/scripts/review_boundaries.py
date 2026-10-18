#!/usr/bin/env python3
"Development earlier-boundary probe, with session cache paths. Inspect explicit inclusion/rejection decisions in boundary_review_*.json."

import json
import sys
from pathlib import Path

import numpy as np

bag = sys.argv[1]
base = Path("/home/resense/data/n5")
specs = {s["name"]: s for s in json.loads((base / f"{bag}_specs.json").read_text())}
tracks = json.loads((base / f"{bag}_reviewed_tracks.json").read_text())
result = {}
for name, t in tracks.items():
    ks = sorted(map(int, t))
    take = ks[: min(12, len(ks))]
    c = np.array([(np.array(t[str(k)]["lo"]) + t[str(k)]["hi"]) / 2 for k in take])
    px = np.polyfit(take, c[:, 0], 1)
    py = np.polyfit(take, c[:, 1], 2)
    s = specs[name]
    found = []
    for k in range(max(0, ks[0] - 50), ks[0]):
        pred = np.array([np.polyval(px, k), np.polyval(py, k)])
        d = np.load(f"/home/resense/data/decoded/synthetic_{bag}/f_{k:05}.npz")
        P = d["xyz"][:, [1, 0, 2]].copy()
        P[:, 0] *= -1
        q = P[
            (d["inten"] == 1)
            & (abs(P[:, 0] - pred[0]) < 4)
            & (abs(P[:, 1] - pred[1]) < 4)
            & (abs(P[:, 2] - s["center"][2]) < s["size"][2] / 2 + 0.3)
        ]
        if len(q):
            found.append(
                {
                    "frame": k,
                    "pred": pred.tolist(),
                    "n": len(q),
                    "lo": q.min(0).tolist(),
                    "hi": q.max(0).tolist(),
                }
            )
    result[name] = {"searched": [max(0, ks[0] - 50), ks[0] - 1], "found": found}
    print(name, found, flush=True)
(base / f"{bag}_boundary_review.json").write_text(json.dumps(result, indent=1))
