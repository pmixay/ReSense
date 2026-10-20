"""Picture of a Falcon frame dumped by falcon_trace.py (shipped run): side view (X vs Z) and top view (X vs Y) of
the returns within |Y| < 3 m, 0..``--xmax`` m ahead; red: the returns near_person.py counts (|Y| < 1.2 m,
1.5-20 m, 0.2-2.2 m above the calibrated mount plane); orange: clusters of the reported detections / warnings;
magenta: the mount plane and the envelope top above it; green / grey dashed lines: the clear distance the ROS node
reports in its conservative path with the Falcon model on / the detector's own clear distance. Titles: the shipped
and the H′-off decision.

    person_plot.py <dump dir> <pair prefix> <frame> <out.png> [--xmax 20]
"""
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("dump")
ap.add_argument("pair")
ap.add_argument("frame", type=int)
ap.add_argument("out")
ap.add_argument("--xmax", type=float, default=20.0)
ap.add_argument("--plane", type=float, default=-1.772)
a = ap.parse_args()
i = a.frame


def line(path):
    with open(path) as f:
        for n, s in enumerate(f):
            if n == i:
                return json.loads(s)


on, off, c = line(a.pair + ".on.jsonl"), line(a.pair + ".off.jsonl"), line(a.pair + ".c.jsonl")
z = np.load(f"{a.dump}/f{i:05d}.npz")
xyz = z["xyz"].astype(np.float64)
hp = xyz[:, 2] - a.plane
view = (xyz[:, 0] > 0) & (xyz[:, 0] < a.xmax) & (np.abs(xyz[:, 1]) < 3.0)
band = (xyz[:, 0] > 1.5) & (xyz[:, 0] < 20) & (np.abs(xyz[:, 1]) < 1.2) & (hp > 0.2) & (hp < 2.2)
fig, ax = plt.subplots(1, 2, figsize=(15, 5.5))
for k, a_ in ((2, ax[0]), (1, ax[1])):
    a_.scatter(xyz[view, 0], xyz[view, k], s=0.4, c="0.6", lw=0)
    a_.scatter(xyz[band & view, 0], xyz[band & view, k], s=1.5, c="r", lw=0, label="returns on the track 0.2-2.2 m above the mount plane")
    for key in z.files:
        if key.startswith("own_"):
            idx = z[key]
            a_.scatter(xyz[idx, 0], xyz[idx, k], s=2, c="orange", lw=0)
    con = c["conservative.falcon_prime"]["clear"]
    a_.axvline(con, color="g", lw=1.2, label=f"node clear, conservative, model on: {con} m (off: {c['conservative.unknown']['clear']} m)")
    a_.axvline(c["detector_clear"], color="0.3", lw=0.8, ls="--", label=f"detector clear: {c['detector_clear']} m")
ax[0].axhline(a.plane, color="m", lw=1, ls="--", label="mount plane (rail head)")
ax[0].axhline(a.plane + 3.0, color="m", lw=0.8, ls=":", label="envelope top")
ax[0].set_ylabel("Z, m")
ax[1].set_ylabel("Y, m")
for a_ in ax:
    a_.set_xlabel("X, m")
    a_.set_xlim(0, a.xmax)
ax[0].legend(fontsize=7, loc="upper right")
dets = "; ".join(f"STOP {d['d']} m" for d in on["dets"]) or "no detection"
warns = "; ".join(f"warn {d['d']} m {d['reason']}" for d in on["warns"]) or "no warning"
fig.suptitle(f"Falcon frame {i}: shipped {on['decision']} ({dets}; {warns}); H′ off: {off['decision']}; "
             f"{int(band.sum())} returns on the track (red), nearest X {np.percentile(xyz[band, 0], 1) if band.any() else float('nan'):.1f} m",
             fontsize=9)
fig.tight_layout()
fig.savefig(a.out, dpi=110)
