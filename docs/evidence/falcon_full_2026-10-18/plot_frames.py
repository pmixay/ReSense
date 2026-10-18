#!/usr/bin/env python3
"""Top and side views of dumped Falcon frames (detector frame) with the run's STOP detections and warnings.

    plot_frames.py <run .jsonl> <dump prefix> <png dir> <frame> [<frame> ...]
"""
import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    run, prefix, out = sys.argv[1:4]
    rows = {r["i"]: r for r in map(json.loads, open(run))}
    t0 = rows[0]["bag_t"]
    os.makedirs(out, exist_ok=True)
    for k in map(int, sys.argv[4:]):
        d = np.load(f"{prefix}_f{k:05d}.npz")
        xyz = d["xyz"].astype(float) @ d["R_vs"].T @ d["mount"].T
        r = rows[k]
        dets = r["dets"]
        far = max([x["d"] for x in dets] + [60.0]) + 25
        sel = (xyz[:, 0] > 0) & (xyz[:, 0] < far) & (np.abs(xyz[:, 1]) < 8)
        fig, ax = plt.subplots(2, 1, figsize=(11, 7))
        for a, yv, lab, lim in ((ax[0], xyz[:, 1], "left (m)", (-8, 8)), (ax[1], xyz[:, 2], "up (m)", (-3, 5))):
            a.scatter(xyz[sel, 0], yv[sel], s=0.3, c="0.6", linewidths=0)
            a.set_ylabel(lab)
            a.set_ylim(*lim)
            a.set_xlim(0, far)
        for x in dets:
            L, W, H = x["size"]
            m = sel & (np.abs(xyz[:, 0] - x["d"] - L / 2) < L / 2 + 0.3) & (np.abs(xyz[:, 1] - x["lat"]) < W / 2 + 0.3)
            ax[0].scatter(xyz[m, 0], xyz[m, 1], s=4, c="red", linewidths=0)
            ax[1].scatter(xyz[m, 0], xyz[m, 2], s=4, c="red", linewidths=0)
        for x in r["warns"]:
            ax[0].plot([x["d"]], [x["lat"]], marker="s", mfc="none", mec="orange", ms=9)
        ax[1].set_xlabel("forward (m), detector frame; red = points of STOP detections, orange = warnings")
        ax[0].set_title(f"frame {k}, t = {r['bag_t'] - t0:.1f} s, {r['decision']}: " + "; ".join(
            f"STOP d={x['d']:.1f} lat={x['lat']:.2f} size={x['size']}" for x in dets), fontsize=8)
        fig.tight_layout()
        fig.savefig(f"{out}/frame_{k:05d}.png", dpi=85)
        plt.close(fig)
        print(k, r["decision"], [(round(x["d"], 1), round(x["lat"], 2)) for x in dets])


if __name__ == "__main__":
    main()
