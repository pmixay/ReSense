#!/usr/bin/env python3
"""Raw-point labels of the far target in frames 0..1724 (before the reviewed main approach).

No detector output is used. Per frame: returns beyond 240 m inside the nominal gauge around the
track reference (|lateral| < 1.05 m, 0.12..3.0 m above the rail-head reference). The per-frame
median range is kept as a label when it continues the neighbouring frames' track (|step| < 1.5 m
from the running median of the last labelled frames; a label must be confirmed by >= 3 labelled
frames within +-5). Gaps up to 25 frames are interpolated, as for the N2 anchors. Two episodes:
``far_walker`` (moving, frames until the target disappears behind the 250 m structure) and
``far_251`` (returns at a constant ~251 m afterwards, until 1724; identity not established).
Writes ``far_walker_labels.json`` and ``far_walker.png`` (range of every in-gauge return vs frame).
"""
import json
from pathlib import Path

import numpy as np

EV = Path(__file__).resolve().parents[1]
CACHE = Path("/home/user/data/falcon")
tr = json.loads((EV / "track_reference.json").read_text())["track"]

pts = []          # (frame, x, lat, h)
per = {}
for i in range(0, 1725):
    p = np.load(CACHE / f"f_{i:05d}.npz")["xyz"].astype(np.float64)
    x = p[:, 0]
    lat = p[:, 1] - (tr["a"] + tr["b"] * x)
    h = p[:, 2] - (tr["z0"] + tr["c"] * x)
    m = (x > 240) & (x < 330) & (np.abs(lat) < 1.05) & (h > 0.12) & (h < 3.0)
    for j in np.flatnonzero(m):
        pts.append((i, x[j], lat[j], h[j]))
    if m.any():
        per[i] = (float(np.median(x[m])), float(np.median(lat[m])), int(m.sum()),
                  float(h[m].min()), float(h[m].max()))
P = np.array(pts)

# track filter: a frame's median range is a label when it lies within 1.5 m of the rolling median of
# the per-frame medians of the frames with returns within +-12 frames (needs >= 3 of them); labels
# more than 50 frames apart are not joined (the sparse part beyond 285 m has 1 frame in 3-8)
fr_all = np.array(sorted(per))
xm = np.array([per[i][0] for i in fr_all])
confirmed = {}
for k, i in enumerate(fr_all):
    near = np.abs(fr_all - i) <= 12
    if near.sum() >= 3 and abs(xm[k] - np.median(xm[near])) <= 1.5:
        confirmed[int(i)] = per[int(i)]
# a label more than 3 m from both labelled neighbours is a stray return (the static 307.7 m points)
fr_s = sorted(confirmed)
for k in range(1, len(fr_s) - 1):
    a_, i, b_ = fr_s[k - 1], fr_s[k], fr_s[k + 1]
    if abs(confirmed[i][0] - confirmed[a_][0]) > 3 and abs(confirmed[i][0] - confirmed[b_][0]) > 3:
        confirmed.pop(i)
frames = sorted(confirmed)
episodes = {"far_walker": [], "far_251": []}
split = None
for a_, b_ in zip(frames, frames[1:]):
    if b_ - a_ > 100:            # the disappearance behind the 250 m structure
        split = b_
        break
for i in frames:
    episodes["far_walker" if split is None or i < split else "far_251"].append(i)


def interp(fr):
    out = {}
    for a, b in zip(fr, fr[1:]):
        out[a] = confirmed[a]
        if b - a <= 50:
            for k in range(a + 1, b):
                w = (k - a) / (b - a)
                out[k] = tuple(confirmed[a][j] * (1 - w) + confirmed[b][j] * w for j in (0, 1)) + (0, 0.0, 0.0)
    if fr:
        out[fr[-1]] = confirmed[fr[-1]]
    return out


res = {"method": __doc__.strip().splitlines()[0], "track_reference": tr, "split_frame": split, "episodes": {}}
for name, fr in episodes.items():
    full = interp(fr)
    xs = np.array([confirmed[i][0] for i in fr])
    res["episodes"][name] = {
        "labelled_frames": len(fr), "covered_frames_with_interpolation": len(full),
        "frame_range": [fr[0], fr[-1]] if fr else None,
        "range_m_min_max": [round(float(xs.min()), 1), round(float(xs.max()), 1)] if fr else None,
        "lateral_median": round(float(np.median([confirmed[i][1] for i in fr])), 2) if fr else None,
        "returns_per_labelled_frame_by_range": {
            f"{lo}-{lo + 5}": [round(float(np.mean([confirmed[i][2] for i in fr if lo <= confirmed[i][0] < lo + 5])), 2),
                                sum(lo <= v[0] < lo + 5 for v in interp(fr).values())]
            for lo in range(240, 320, 5) if any(lo <= confirmed[i][0] < lo + 5 for i in fr)},
        "path": [[k, round(v[0], 2), round(v[1], 2)] for k, v in sorted(full.items())]}
(EV / "far_walker_labels.json").write_text(json.dumps(res, indent=1))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
fig, ax = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
ax[0].scatter(P[:, 0], P[:, 1], s=1, c=P[:, 3], cmap="viridis")
for name, c in (("far_walker", "r"), ("far_251", "m")):
    pa = np.array(res["episodes"][name]["path"]) if res["episodes"][name]["path"] else np.zeros((0, 3))
    if len(pa):
        ax[0].plot(pa[:, 0], pa[:, 1], c + "-", lw=0.6, label=name)
ax[0].set_ylabel("range of in-gauge returns beyond 240 m")
ax[0].legend()
ax[0].set_title("frames 0-1724: every return inside the nominal gauge around the track reference beyond 240 m (colour = height)")
ax[1].scatter(P[:, 0], P[:, 2], s=1, c="k")
ax[1].set_ylabel("lateral m (track reference)")
ax[1].set_xlabel("frame")
plt.tight_layout()
plt.savefig(EV / "far_walker.png", dpi=80)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "path"} for k, v in res["episodes"].items()}, indent=1),
      "split", split)
