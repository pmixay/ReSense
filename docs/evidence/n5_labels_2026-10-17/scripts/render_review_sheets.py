#!/usr/bin/env python3
"Re-render final raw-point annotation contact sheets; session cache roots are explicit below."

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

bag = sys.argv[1]
base = Path("/home/resense/data/n5")
tracks = json.loads(
    (
        Path("/home/resense/ReSense/docs/evidence/n5_labels_2026-10-17")
        / f"reviewed_boxes_{bag}.json"
    ).read_text()
)["tracks"]
out = Path("/home/resense/ReSense/docs/evidence/n5_labels_2026-10-17/pictures")
out.mkdir(exist_ok=True, parents=True)
for name, t in tracks.items():
    ks = sorted(map(int, t))
    dd = np.array([t[str(k)]["lo"][0] for k in ks])
    chosen = list(
        dict.fromkeys(
            [
                ks[0],
                ks[np.argmin(abs(dd - 100))],
                ks[np.argmin(abs(dd - 40))],
                ks[np.argmin(abs(dd - 8))],
            ]
        )
    )
    fig, axs = plt.subplots(
        len(chosen), 3, figsize=(15, 3.3 * len(chosen)), squeeze=False
    )
    for row, k in enumerate(chosen):
        r = t[str(k)]
        lo = np.array(r["lo"])
        hi = np.array(r["hi"])
        c = (lo + hi) / 2
        size = hi - lo
        d = np.load(f"/home/resense/data/decoded/synthetic_{bag}/f_{k:05}.npz")
        P = d["xyz"][:, [1, 0, 2]].copy()
        P[:, 0] *= -1
        inside = np.all((P >= lo - 1e-5) & (P <= hi + 1e-5), axis=1) & (d["inten"] == 1)
        crop = (
            (abs(P[:, 0] - c[0]) < 3)
            & (abs(P[:, 1] - c[1]) < max(3, size[1] / 2 + 1))
            & (abs(P[:, 2] - c[2]) < max(2, size[2] / 2 + 0.5))
        )
        q = P[crop]
        v = P[inside]
        for col, (x, y) in enumerate([(0, 1), (0, 2), (1, 2)]):
            ax = axs[row, col]
            ax.scatter(q[:, x], q[:, y], s=0.7, c="0.68", linewidths=0)
            ax.scatter(v[:, x], v[:, y], s=5, c="#c90068", linewidths=0)
            ax.grid(alpha=0.15)
            ax.set_xlabel(["forward m", "left m", "up m"][x])
            ax.set_ylabel(["forward m", "left m", "up m"][y])
            ax.set_title(
                f"frame{k}, {len(v)} raw returns; extent "
                + ",".join(f"{d:.2f}" for d in size),
                fontsize=9,
            )
    fig.suptitle(
        f"synthetic_{bag}: {name}; candidate team annotation magenta / raw scene grey"
    )
    fig.tight_layout()
    fig.savefig(out / f"{bag}_{name}_review.png", dpi=110)
    plt.close(fig)
