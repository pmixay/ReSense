#!/usr/bin/env python3
"""Item 6 (finding for the detector owner): what the detector itself did with the person-like returns of the Falcon
frames 4366-4430, from the state dumped by run_falcon.py (corridor indices and cluster membership of the frame as the
detector produced them, not reconstructed), and the pictures.

Person-like set (no track model): X >= 2.4 m, |Y| < 0.9 m, 0.2-1.6 m above the mount plane, X < nearest + 8 m.

    person_trace.py CTL_PREFIX DUMPDIR --out-tsv OUT.tsv --png-dir DIR [--png 4373,4385,...]
"""
import argparse, json, os, sys
import numpy as np

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
from resense.config import GaugeConfig  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("ctl"); ap.add_argument("dump")
ap.add_argument("--first", type=int, default=4366); ap.add_argument("--last", type=int, default=4430)
ap.add_argument("--out-tsv", required=True); ap.add_argument("--png-dir", default="")
ap.add_argument("--png", default="4373,4378,4385,4396,4405,4410,4413")
a = ap.parse_args()
rc = [json.loads(l) for l in open(a.ctl + ".jsonl")]
g = GaugeConfig()
png = {int(v) for v in a.png.split(",") if v}
hdr = ["frame", "decision", "n_person", "x_near", "in_corridor", "in_strict_gauge_mask", "in_any_cluster", "clusters_with_person",
       "x_lt_range_min", "model_h_p50", "bed_minus_plane", "dominant_state"]
out = []
for i in range(a.first, a.last + 1):
    f = os.path.join(a.dump, f"f{i:05d}.npz")
    d = np.load(f)
    xyz, dy, h, plane = d["xyz"], d["dy"], d["h"], float(d["plane"])
    hm = xyz[:, 2] - plane
    base = (xyz[:, 0] >= 2.4) & (np.abs(xyz[:, 1]) < 0.9) & (hm > 0.2) & (hm < 1.6)
    if not base.any():
        out.append([i, rc[i]["decision"], 0] + [""] * 9)
        continue
    x0 = xyz[base, 0].min()
    sel = np.flatnonzero(base & (xyz[:, 0] < x0 + 8.0))
    corr = set(d["corridor_idx"].tolist())
    in_corr = [k for k in sel if int(k) in corr]
    meta = json.loads(str(d["cl_meta"]))
    owners = {}
    for m in meta:
        key = f"cl_{m['k']}"
        if key in d.files:
            idx = set(d[key].tolist())
            n = sum(int(k) in idx for k in sel)
            if n:
                owners[m["k"]] = (n, m)
    n_cluster = sum(n for n, _ in owners.values())
    strict_mask = int(((np.abs(dy[sel]) <= 1.05) & (h[sel] >= 0.12) & (h[sel] <= 3.0) & (xyz[sel, 0] >= g.range_min)).sum())
    ltmin = int((xyz[sel, 0] < g.range_min).sum())
    bed = float(np.interp(np.median(xyz[sel, 0]), d["grid"], d["rail_z"])) - plane
    if len(in_corr) == 0:
        state = "no returns in the corridor: " + ("all below the model gauge floor (h<0.12)" if (h[sel] < 0.12).all() else "outside range/lateral")
    elif n_cluster == 0:
        state = "corridor returns, no cluster"
    else:
        top = max(owners.values(), key=lambda t: t[0])[1]
        state = (f"{n_cluster} in cluster(s); largest zone={top['zone']} reason={top['reason'] or '-'} kind={top['kind'] or '-'} "
                 f"n={top['n']} track={top['track']}")
    out.append([i, rc[i]["decision"], len(sel), round(float(xyz[sel, 0].min()), 2), len(in_corr), strict_mask, n_cluster,
                len(owners), ltmin, round(float(np.median(h[sel])), 2), round(bed, 2), state])
    if i in png and a.png_dir:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        os.makedirs(a.png_dir, exist_ok=True)
        near = (xyz[:, 0] > 0) & (xyz[:, 0] < 14) & (np.abs(xyz[:, 1]) < 3.0)
        fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
        ax[0].scatter(xyz[near, 0], xyz[near, 2], s=1, c="#bbbbbb")
        ax[0].scatter(xyz[sel, 0], xyz[sel, 2], s=3, c="#d62728", label=f"person-like ({len(sel)})")
        gx = np.arange(0, 14.01, 0.5)
        ax[0].plot(gx, np.interp(gx, d["grid"], d["rail_z"]), c="#1f77b4", lw=2, label="model rail head (track model)")
        ax[0].axhline(plane, c="#2ca02c", lw=2, label="mount plane (calibration)")
        ax[0].plot(gx, np.interp(gx, d["grid"], d["rail_z"]) + 0.12, c="#1f77b4", lw=1, ls="--", label="gauge floor (model)")
        ax[0].axvline(g.range_min, c="k", ls=":", label="gauge.range_min 3.0 m")
        ax[0].set_xlabel("X ahead (m)"); ax[0].set_ylabel("Z (m)"); ax[0].set_title(f"frame {i} side view, |Y|<3 m ({rc[i]['decision']})")
        ax[0].legend(fontsize=7, loc="upper left")
        ax[1].scatter(xyz[near, 0], xyz[near, 1], s=1, c="#bbbbbb")
        ax[1].scatter(xyz[sel, 0], xyz[sel, 1], s=3, c="#d62728")
        ax[1].axhline(1.05 + rc[i]["track_center"], c="k", lw=0.8); ax[1].axhline(-1.05 + rc[i]["track_center"], c="k", lw=0.8)
        ax[1].set_xlabel("X ahead (m)"); ax[1].set_ylabel("Y (m)"); ax[1].set_title("top view; black = gauge half-width 1.05 m about the model axis")
        ax[1].set_aspect("equal"); ax[1].set_ylim(-3, 3)
        fig.tight_layout(); fig.savefig(os.path.join(a.png_dir, f"person_trace_f{i}.png"), dpi=90); plt.close(fig)
with open(a.out_tsv, "w") as fo:
    fo.write("\t".join(hdr) + "\n")
    for r in out:
        fo.write("\t".join(str(v) for v in r) + "\n")
print("rows", len(out))
