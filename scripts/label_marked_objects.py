#!/usr/bin/env python3
"""Labels for the organizers' synthetic bags of 16.10 (objects inserted in place, intensity 1).

    label_marked_objects.py <decoded cache> --out <labels.json>
        [--reference <decoded cache> --ref-offset N --ref-frames A:B]

Set O (``cloud_with_fake_obj``) appended its object points after the last no-return zero, which
``label_fake_objects.py`` reads. The bags of 16.10 (``new_synth_data``) insert the object points in
place in the organized scan and remove the real returns they hide; the inserted points still carry
intensity exactly 1 (docs/evidence/extended_data_2026-10-17/README.md §5). So the object points of
a frame are taken, in order of preference, from:

* ``exact``: the points absent from a reference recording of the same frame (``--reference``, e.g.
  Set O for ``synthetic_platform`` frames 0-314 = Set O frames 1195-1509, ``--ref-offset 1195``);
* ``marker``: intensity-1 points clustered in the sensor frame (DBSCAN 0.5 m, >= 4 points) whose
  bounding box grown by 0.15 m holds at least 85 % intensity-1 points (a real dark patch is mixed
  with other intensities). Where both are available the agreement of the two is reported.

The input is the node-decoded cache (``cache_decoded.py``: sensor-frame float32 xyz, intensity,
ring); the frame is run through the judge's node replica so that every position is in the
detector's mount-calibrated vehicle frame and the lateral is measured from its own track axis,
as in ``labels/cloud_with_fake_obj.json``. Rows, keys and the file layout follow that file. The
organizers gave no intent for these objects, so ``in_gauge`` is **measured**: an object is inside
when most of its plausible rows nearer than 60 m have points in the strict envelope (all rows if it
is never that near). Run with RESENSE_REPO / PYTHONPATH set to the detector checkout used.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
import sys

import numpy as np
from sklearn.cluster import DBSCAN

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "docs/evidence/judgement_2026-10-13/scripts"


def marker_points(xyz, inten, eps=0.5, min_pts=4, purity=0.85, grow=0.15):
    """Indices of intensity-1 points in compact, mostly intensity-1 clusters."""
    one = np.flatnonzero(inten == 1.0)
    if one.size < min_pts:
        return np.zeros(0, dtype=np.int64)
    labels = DBSCAN(eps=eps, min_samples=min_pts).fit_predict(xyz[one])
    keep = []
    for lab in np.unique(labels[labels >= 0]):
        idx = one[labels == lab]
        lo, hi = xyz[idx].min(axis=0) - grow, xyz[idx].max(axis=0) + grow
        box = np.all((xyz >= lo) & (xyz <= hi), axis=1)
        if np.mean(inten[box] == 1.0) >= purity:
            keep.append(idx)
    return np.concatenate(keep) if keep else np.zeros(0, dtype=np.int64)


def exact_points(xyz, ref_xyz):
    """Indices of points whose exact float32 xyz is absent from the reference frame."""
    ref = {r.tobytes() for r in np.ascontiguousarray(ref_xyz, dtype=np.float32)}
    cur = np.ascontiguousarray(xyz, dtype=np.float32)
    return np.array([i for i, r in enumerate(cur) if r.tobytes() not in ref], dtype=np.int64)


def link_tracks(groups_per_frame, max_gap_frames=40):
    """Frame groups {k: [(x_min, y_mid, idx), ...]} -> tracks [(k, group_no), ...] by predicted x_min."""
    tracks = []
    for k in sorted(groups_per_frame):
        groups = groups_per_frame[k]
        cands = []
        for ti, t in enumerate(tracks):
            kl, gl, xl, yl = t[-1]
            if k - kl > max_gap_frames:
                continue
            if len(t) >= 2:
                ka, _, xa, _ = t[-min(len(t), 6)]
                v = (xa - xl) / max(kl - ka, 1)
            else:
                v = 1.8
            xp = xl - v * (k - kl)
            for gi, (x0, y0, _) in enumerate(groups):
                err = abs(x0 - xp)
                if err < max(6.0, 0.08 * x0) and abs(y0 - yl) < 3.0:
                    cands.append((err, ti, gi))
        t_used, g_used = set(), set()
        for err, ti, gi in sorted(cands):
            if ti in t_used or gi in g_used:
                continue
            tracks[ti].append((k, gi, groups[gi][0], groups[gi][1]))
            t_used.add(ti)
            g_used.add(gi)
        for gi, (x0, y0, _) in enumerate(groups):
            if gi not in g_used:
                tracks.append([(k, gi, x0, y0)])
    return tracks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cache")
    ap.add_argument("--out", required=True)
    ap.add_argument("--reference")
    ap.add_argument("--ref-offset", type=int, default=0)
    ap.add_argument("--ref-frames", default="", help="A:B, frames of the cache that have a reference")
    ap.add_argument("--group-eps", type=float, default=1.0, help="m, object points of one frame -> objects")
    ap.add_argument("--min-track", type=int, default=5)
    a = ap.parse_args()
    sys.path.insert(0, str(JUDGE))
    from judge_runner import NodeReplica
    from range_test import run_frame
    from resense.gauge import corridor_coordinates

    meta = json.loads(Path(a.cache, "meta.json").read_text())
    files = sorted(glob.glob(os.path.join(a.cache, "f_*.npz")))
    ref_meta = ref_files = None
    r0 = r1 = -1
    if a.reference:
        ref_files = sorted(glob.glob(os.path.join(a.reference, "f_*.npz")))
        ref_meta = json.loads(Path(a.reference, "meta.json").read_text())
        r0, r1 = (int(v) for v in a.ref_frames.split(":"))
    rep = NodeReplica()
    cfg = rep.detector.cfg
    half_w = max(abs(float(v[0])) for v in cfg.gauge.profile)
    top = max(float(v[1]) for v in cfg.gauge.profile)
    per_frame, groups_per_frame, agree = {}, {}, []
    for k, (m, f) in enumerate(zip(meta, files)):
        d = np.load(f)
        xyz, inten, ring = d["xyz"], d["inten"], d["ring"]
        run_frame(rep, xyz, inten, ring, m, k)
        det = rep.detector
        mk = marker_points(xyz, inten)
        src = "marker"
        idx = mk
        if ref_files is not None and r0 <= k < r1:
            j = k + a.ref_offset
            if abs(ref_meta[j]["stamp"] - m["stamp"]) > 1e-6:
                raise SystemExit(f"frame {k}: reference stamp differs")
            ex = exact_points(xyz, np.load(ref_files[j])["xyz"])
            agree.append({"k": k, "exact": int(ex.size), "marker": int(mk.size),
                          "both": int(np.intersect1d(ex, mk).size)})
            idx, src = ex, "exact"
        if not idx.size:
            continue
        xyz_v = xyz[idx].astype(np.float64) @ rep.R_vs.T.astype(np.float64)
        xyz_p = det.calib.apply(xyz_v.astype(np.float32)).astype(np.float64)
        dy, h = corridor_coordinates(xyz_p, det.track)
        labels = DBSCAN(eps=a.group_eps, min_samples=1).fit_predict(xyz_p)
        groups = []
        for lab in np.unique(labels):
            g = np.flatnonzero(labels == lab)
            groups.append((float(xyz_p[g, 0].min()), float(xyz_p[g, 1].mean()), g))
        groups_per_frame[k] = groups
        per_frame[k] = (xyz_p, dy, h, src)

    tracks = [t for t in link_tracks(groups_per_frame) if len(t) >= a.min_track]
    tracks.sort(key=lambda t: t[-1][0])
    gt, summary = {}, {}
    for n, track in enumerate(tracks, 1):
        name = f"obj{n:02d}"
        rows = []
        for k, gi, _, _ in track:
            xyz_p, dy, h, src = per_frame[k]
            g = groups_per_frame[k][gi][2]
            X, dd, hh = xyz_p[g, 0], dy[g], h[g]
            inside = (np.abs(dd) <= half_w) & (hh <= top) & (hh >= -0.6)
            lat = float(0.5 * (dd.min() + dd.max()))
            size = (xyz_p[g].max(axis=0) - xyz_p[g].min(axis=0)).tolist()
            row = {"kind": "inserted", "name": name, "label": name, "size": [round(v, 2) for v in size],
                   "distance": round(float(X.min()), 2), "lateral": round(lat, 2),
                   "lateral_sensor": round(float(0.5 * (xyz_p[g, 1].min() + xyz_p[g, 1].max())), 2),
                   "n_points": int(g.size), "n_in_envelope": int(inside.sum()),
                   "plausible": bool(abs(lat) < 3.5 and -1.0 < hh.min() < 5.0),
                   "gauge_margin": round(float(half_w - np.abs(dd).min()) if (dd.min() > 0 or dd.max() < 0) else half_w, 2),
                   "h_above_rail": [round(float(hh.min()), 2), round(float(hh.max()), 2)],
                   "bbox": [[round(float(v), 2) for v in xyz_p[g].min(axis=0)],
                            [round(float(v), 2) for v in xyz_p[g].max(axis=0)]],
                   "source": src}
            rows.append((k, row))
        plaus = [r for _, r in rows if r["plausible"]]
        near = [r for r in plaus if r["distance"] < 60.0] or plaus
        intent = bool(near) and float(np.mean([r["n_in_envelope"] > 0 for r in near])) >= 0.5
        for k, row in rows:
            row["in_gauge"] = intent and row["plausible"]
            gt.setdefault(f"{k:05d}", []).append(row)
        big = [r for _, r in rows if r["distance"] < 60.0] or [r for _, r in rows]
        summary[name] = {
            "in_gauge_measured": intent, "frames": [rows[0][0], rows[-1][0]], "visible_frames": len(rows),
            "first_visible_m": rows[0][1]["distance"], "last_m": rows[-1][1]["distance"],
            "size_near_m": [round(float(np.median([r["size"][i] for r in big])), 2) for i in range(3)],
            "lateral_near_m": round(float(np.median([r["lateral"] for r in big])), 2),
            "h_above_rail_near_m": [round(float(np.median([r["h_above_rail"][i] for r in big])), 2) for i in (0, 1)],
            "frames_in_envelope": sum(1 for r in plaus if r["n_in_envelope"] > 0),
            "sources": sorted({r["source"] for _, r in rows})}
    for k in range(len(meta)):
        gt.setdefault(f"{k:05d}", [])
    tot = {key: sum(r[key] for r in agree) for key in ("exact", "marker", "both")} if agree else None
    meta_out = {
        "bag": os.path.basename(os.path.normpath(a.cache)), "frames": len(meta),
        "source": "scripts/label_marked_objects.py: inserted points (exact difference against a reference "
                  "where given, else the intensity-1 marker), linked into tracks",
        "coords": "vehicle (mount-calibrated by the detector of RESENSE_REPO, node replica)",
        "detector_repo": os.environ.get("RESENSE_REPO", ""),
        "in_gauge": "measured (no organizers' intent): most plausible rows nearer than 60 m have envelope points",
        "reference": {"path": a.reference, "offset": a.ref_offset, "frames": a.ref_frames} if a.reference else None,
        "marker_vs_exact_points": tot, "objects": summary}
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write('{\n "_meta": ' + json.dumps(meta_out, ensure_ascii=False, indent=1).replace("\n", "\n ") + ",\n")
        fh.write(",\n".join(f' "{k}": {json.dumps(gt[k], ensure_ascii=False, separators=(",", ":"))}'
                            for k in sorted(gt)))
        fh.write("\n}\n")
    print(json.dumps({"objects": summary, "marker_vs_exact_points": tot}, indent=1))


if __name__ == "__main__":
    main()
