#!/usr/bin/env python3
"""Top views of single frames: the raw points (from the cache, the detector's corrected frame), the stitched
self-supervised centreline (every later rail midpoint brought back, and the label per query distance), the base and
K2 axes and the learned model's middle and calibrated band.

    fa_plot.py <cache_dir> <extract.npz> <labels.npz> <out.png> --frames 10,120 [--title ...]

The cloud is re-run through a fresh detector up to each frame so it is in the same corrected frame as the stored
state (checked: the re-run track state equals the stored one).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../../.."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from fa_labels import RAIL_Z, poses_from_T, repair  # noqa: E402
from resense import far_axis as fa  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("extract")
    ap.add_argument("labels")
    ap.add_argument("out")
    ap.add_argument("--frames", required=True)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
    from eval_real import load_cfg_dict
    D = np.load(a.extract)
    L = np.load(a.labels)
    names = [str(n) for n in D["names"]]
    want = [int(f) for f in a.frames.split(",")]
    cfg = DetectorConfig.from_dict(load_cfg_dict(os.path.join(ROOT, "configs/default.yaml"), []))
    files = cache_files(a.cache)
    stamps = load_cache_stamps(a.cache)
    M = fa.FarAxisModel.load(os.path.join(ROOT, "resense/models/far_axis_1.3.json"))
    T, rep = repair(D["T"], D["fitness"])
    P, segs = poses_from_T(T)
    rails = [r[np.isfinite(r[:, 0])] for r in D["rails"]]
    det = Detector(cfg)
    clouds = {}
    for k, f in enumerate(files[:max(want) + 1]):
        stem = cache_file_stem(f)
        det.process(frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, k * 0.1), frame_id=stem))
        if k in want:
            st = fa.model_state(det.track, det.track.curve, det._far_axis)
            assert st == json.loads(str(D["state"][k])), "re-run state differs from the extraction"
            clouds[k] = det._frame_xyz.copy()
    fig, axes = plt.subplots(len(want), 1, figsize=(13, 4.2 * len(want)))
    axes = np.atleast_1d(axes)
    xq = L["query_x"]
    for ax, t in zip(axes, want):
        xyz = clouds[t]
        st = json.loads(str(D["state"][t]))
        X = np.arange(0, 251, 1.0)
        m = (xyz[:, 0] > 0) & (xyz[:, 0] < 255)
        ax.scatter(xyz[m, 0], xyz[m, 1] - fa.base_y(st, xyz[m, 0]), s=0.2, c="0.6", rasterized=True, label="raw points")
        # every later rail midpoint brought into frame t
        Pinv = np.linalg.inv(P[t])
        pts = []
        for j in range(t + 1, len(P)):
            if segs[j] != segs[t]:
                break
            Mj = Pinv @ P[j]
            if Mj[0, 3] > 260:
                break
            r = rails[j]
            if len(r):
                p = Mj[:3, :3] @ np.stack([r[:, 0], r[:, 1], np.full(len(r), RAIL_Z)]) + Mj[:3, 3:4]
                pts.append(p[:2].T)
        if pts:
            pts = np.concatenate(pts)
            ax.scatter(pts[:, 0], pts[:, 1] - fa.base_y(st, pts[:, 0]), s=1.5, c="tab:green", label="later rail midpoints (stitched)")
        lab = np.where(L["valid"][t], L["label"][t], np.nan)
        ax.plot(xq, lab - fa.base_y(st, xq), "o", c="darkgreen", ms=5, label="label")
        ax.plot(X, 0 * X, c="tab:blue", lw=1.2, label="base axis")
        ax.plot(X, fa.curve_offset(st, X), c="tab:orange", lw=1.2, label="K2 published axis")
        prof = (D["prof_side"][t], D["prof_vault"][t], D["prof_bed"][t])
        Q = M.predict(fa.query_features(prof, st, xq))
        ax.plot(xq, Q[:, 1], c="tab:red", lw=1.5, label="learned middle")
        ax.fill_between(xq, Q[:, 0], Q[:, 2], color="tab:red", alpha=0.12, label="learned 90 % band")
        ax.axvline(min(st["axis_valid"], 250), c="tab:blue", ls=":", lw=1, label="axis_valid")
        lim = np.nanmax(np.abs(np.r_[lab - fa.base_y(st, xq), Q[:, 1], fa.curve_offset(st, X)]))
        ax.set_ylim(-max(6.0, 1.3 * lim), max(6.0, 1.3 * lim))
        ax.set_xlim(0, 255)
        ax.set_title(f"{a.title} frame {t} ({names[t]}): lateral relative to the base axis")
        ax.set_xlabel("X ahead (m)")
        ax.set_ylabel("Y - base axis (m)")
        ax.legend(fontsize=7, loc="upper left", ncol=3, markerscale=4)
    fig.tight_layout()
    fig.savefig(a.out, dpi=110)
    print(a.out)


if __name__ == "__main__":
    main()
