"""Pictures of a Falcon frame dumped by falcon_pair.py: for the shipped run (``on``) and the H′-off run (``off``),
a side view (X forward vs Z up, detector frame) and a top view (X vs Y) of the returns within |Y| < 3 m
and 0-25 m ahead (the committed crop). Drawn: the track model's rail head ``rail_z(X)`` and the calibrated mount's rail-head
plane (z = -height) with the envelope top above it; in ``on`` the clusters H′ looked at (red: made advisory
``height_conflict``, blue: kept); in both, the clusters of every reported detection / warning (orange: STOP
detection, green: warning), labelled with their id, decision and kind from the run's records.

    plot_pair.py <dump dir> <records prefix> <frame> <out.png>
"""
import json
import lzma
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def rec(prefix, tag, i):
    p = f"{prefix}.{tag}.jsonl" if tag != "h" else f"{prefix}.h.jsonl"
    with (lzma.open(p + ".xz", "rt") if not __import__("os").path.exists(p) else open(p)) as f:
        for n, line in enumerate(f):
            if n == i:
                return json.loads(line)


def main():
    dump, prefix, i, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    fig, ax = plt.subplots(2, 2, figsize=(15, 9), sharex=True)
    for col, tag in enumerate(("on", "off")):
        z = np.load(f"{dump}/f{i:05d}.{tag}.npz")
        r = rec(prefix, tag, i)
        xyz = z["xyz"]
        sel = (xyz[:, 0] > 0) & (xyz[:, 0] < 25) & (np.abs(xyz[:, 1]) < 3.0)
        a_side, a_top = ax[0, col], ax[1, col]
        for a, k in ((a_side, 2), (a_top, 1)):
            a.scatter(xyz[sel, 0], xyz[sel, k], s=0.3, c="0.6", lw=0)
        g, rz, plane = z["grid"], z["rail_z"], float(z["plane"])
        m = g <= 25
        a_side.plot(g[m], rz[m], "k-", lw=1, label="model rail head rail_z(X)")
        a_side.axhline(plane, color="m", lw=1, ls="--", label="mount plane (z = -height)")
        a_side.axhline(plane + 3.0, color="m", lw=0.8, ls=":", label="mount plane + envelope top (3.0 m)")
        for key in z.files:
            if key.startswith("own_"):
                did = int(key[4:])
                idx = z[key]
                a_side.scatter(xyz[idx, 0], xyz[idx, 2], s=3, c="orange", lw=0)
                a_top.scatter(xyz[idx, 0], xyz[idx, 1], s=3, c="orange", lw=0)
                c = xyz[idx].mean(axis=0) if idx.size else None
                if c is not None:
                    a_side.annotate(f"track {did}", (c[0], c[2]), fontsize=7, color="darkorange")
        hrec = rec(prefix, "h", i) if tag == "on" else {"rows": []}
        demoted = {row["k"]: row["demoted"] for row in hrec["rows"]}
        for key in z.files:
            if key.startswith("hm_"):
                idx = z[key]
                col_ = "r" if demoted.get(int(key[3:])) else "b"
                a_side.scatter(xyz[idx, 0], xyz[idx, 2], s=2, c=col_, lw=0)
                a_top.scatter(xyz[idx, 0], xyz[idx, 1], s=2, c=col_, lw=0)
        dets = "; ".join(f"STOP {d['d']} m lat {d['lat']} {d['kind']}" for d in r["dets"]) or "none"
        warns = "; ".join(f"warn {d['d']} m {d['reason'] or d['zone']}" for d in r["warns"]) or "none"
        a_side.set_title(f"{tag}: frame {i} {r['decision']}\ndets: {dets}\nwarns: {warns}", fontsize=8)
        a_side.set_ylabel("Z, m (detector frame)")
        a_top.set_ylabel("Y, m")
        a_top.set_xlabel("X, m")
        a_side.legend(fontsize=7, loc="upper left")
    fig.suptitle(f"Falcon frame {i}: H′ on (shipped) vs off; red = clusters H′ made advisory, blue = clusters H′ "
                 "looked at and kept (on); orange = clusters of reported detections/warnings", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=110)


if __name__ == "__main__":
    main()
