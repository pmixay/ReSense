#!/usr/bin/env python3
"""Independent checks of labels made by ``label_marked_objects.py`` (exact reference).

    check_synth_labels.py <decoded cache> <labels.json> --reference <cache> [--ref-offset N]
        --out <check.json> [--png-dir DIR --png-frames 30,100,...] [--half-width 1.05]

Works from the raw sensor-frame points, not from the labeller's transforms:

1. intensity: every exactly-new point should carry intensity 1 (the organizers' insertion);
2. coverage: the share of exactly-new points that ended in a label row (track filter losses);
3. distance: the label distance (vehicle frame, mount-calibrated) against the plain sensor-forward
   distance of the same object's points (Pandar: forward = -y), and frame-to-frame steps against
   the median step (the train speed) - a jump means a wrong track link;
4. size: spread of the near (< 60 m) sizes of each object;
5. gauge: the lateral extent (lateral +- W/2) of each object against the strict half width;
6. pictures: top and side views of chosen frames (all points grey, exactly-new points red, the
   label's numbers in the title) for a human look.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from label_marked_objects import exact_points  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cache")
    ap.add_argument("labels")
    ap.add_argument("--reference", required=True)
    ap.add_argument("--ref-offset", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--png-dir", default="")
    ap.add_argument("--png-frames", default="")
    ap.add_argument("--half-width", type=float, default=1.05)
    a = ap.parse_args()
    lab = json.load(open(a.labels))
    frames = sorted(int(k) for k in lab if k != "_meta")
    inten_bad = new_total = labelled_pts = 0
    per_obj = {}
    pics = {int(v) for v in a.png_frames.split(",") if v}
    for k in frames:
        d = np.load(os.path.join(a.cache, f"f_{k:05d}.npz"))
        xyz, inten = d["xyz"], d["inten"]
        ex = exact_points(xyz, np.load(os.path.join(a.reference, f"f_{k + a.ref_offset:05d}.npz"))["xyz"])
        new_total += ex.size
        inten_bad += int(np.sum(inten[ex] != 1.0))
        rows = lab[f"{k:05d}"]
        labelled_pts += sum(r["n_points"] for r in rows)
        for r in rows:
            P = per_obj.setdefault(r["name"], {"k": [], "d": [], "fwd": [], "size": [], "lat": [], "w": []})
            P["k"].append(k)
            P["d"].append(r["distance"])
            P["size"].append(r["size"])
            P["lat"].append(r["lateral"])
            # the same object's points in the raw cloud: exactly-new points near the label distance
            fwd = -xyz[ex, 1]
            near = ex[np.abs(fwd - r["distance"]) < 3.0 + r["size"][0]]
            P["fwd"].append(float(-xyz[near, 1].min()) if near.size else None)
        if k in pics and a.png_dir:
            draw(xyz, ex, rows, k, a.png_dir)
    objs = {}
    for name, P in per_obj.items():
        k, dd = np.array(P["k"]), np.array(P["d"])
        steps = np.diff(dd) / np.maximum(np.diff(k), 1)
        med = float(np.median(steps)) if steps.size else 0.0
        jumps = [(int(k[i + 1]), round(float(steps[i]), 2)) for i in range(steps.size) if abs(steps[i] - med) > 1.0]
        fwd_err = [abs(f - d) for f, d in zip(P["fwd"], P["d"]) if f is not None]
        near = [s for s, d in zip(P["size"], P["d"]) if d < 60.0]
        lat = np.array(P["lat"])
        w = np.array([s[1] for s in P["size"]])
        lat_near = [(la, wi) for la, wi, d in zip(lat, w, dd) if d < 60.0]
        inner = [abs(la) - wi / 2 for la, wi in lat_near]
        objs[name] = {
            "rows": len(k), "frames": [int(k[0]), int(k[-1])],
            "median_step_m_per_frame": round(med, 3), "step_jumps_gt_1m": jumps,
            "label_vs_sensor_forward_m": {"median": round(float(np.median(fwd_err)), 3),
                                          "max": round(float(np.max(fwd_err)), 3)} if fwd_err else None,
            "size_near_p10_p90": [[round(float(np.percentile([s[i] for s in near], q)), 2) for q in (10, 90)]
                                  for i in range(3)] if near else None,
            "inner_edge_near_m": {"median": round(float(np.median(inner)), 2),
                                  "min": round(float(np.min(inner)), 2)} if inner else None,
            "inside_strict_half_width_near": (bool(np.median(inner) < a.half_width) if inner else None),
        }
    out = {"labels": a.labels, "frames_checked": len(frames), "exact_points": new_total,
           "exact_points_not_intensity_1": inten_bad, "points_in_label_rows": labelled_pts,
           "half_width_m": a.half_width, "objects": objs}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))
    return 0


def draw(xyz, ex, rows, k, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(out_dir, exist_ok=True)
    fwd, lat, z = -xyz[:, 1], xyz[:, 0], xyz[:, 2]  # Pandar: forward -y, left +x
    far = max([r["distance"] for r in rows] + [40.0]) + 15.0
    sel = (fwd > 0) & (fwd < far) & (np.abs(lat) < 8)
    fig, ax = plt.subplots(2, 1, figsize=(11, 7))
    for a_, yv, yl in ((ax[0], lat, "left (m)"), (ax[1], z, "z sensor (m)")):
        a_.scatter(fwd[sel], yv[sel], s=0.3, c="0.6", linewidths=0)
        a_.scatter(fwd[ex], yv[ex], s=3, c="red", linewidths=0)
        a_.set_xlim(0, far)
        a_.set_ylabel(yl)
    ax[0].set_ylim(-8, 8)
    ax[1].set_ylim(-3, 4)
    ax[1].set_xlabel("forward (m), sensor frame; red = exactly-new points")
    ax[0].set_title(f"frame {k}: " + "; ".join(
        f"{r['name']} d={r['distance']} lat={r['lateral']} size={r['size']} in_gauge={r['in_gauge']}" for r in rows),
        fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, f"frame_{k:05d}.png"), dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
