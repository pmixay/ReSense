#!/usr/bin/env python3
"""Would a "static-world" rule (an obstacle must approach at exactly the train's speed) remove
false alarms, and what would it do to the organizers' synthetic obstacles?

    python scripts/speed_static_check.py --run out/eval/default --ref out/speed

For every confirmed alarm track of a detector run (``scripts/eval_real.py`` JSONL) the
frame-to-frame change of its distance is compared with the train's displacement from the ICP
reference (``scripts/speed_reference.py``): a track is *static* when the median of
|delta distance + reference displacement| over its consecutive alarm frames is below
``--tol`` m per frame (0.3 m = 3 m/s). Tracks in ``cloud_with_fake_obj`` are split into the
alarms on a labelled organizer object (matched by distance and lateral offset as
``score_fake_objects.py`` does, simplified) and the background ones.

The labelled objects themselves are also checked directly: the per-frame change of the nearest
face of each object against the train's displacement.
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np


def load_ref(path):
    ref = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("ref_ok"):
            ref[int(r["frame"])] = float(r["ref_dx"])
    return ref


def tracks(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        for d in r["detections"]:
            out.setdefault(d["id"], []).append((int(r["frame"]), float(d["distance"]), float(d["lateral"])))
    return out


def classify(tr, ref, tol):
    res = []
    for tid, rows in tr.items():
        rel = [(b[1] - a[1]) + ref[b[0]] for a, b in zip(rows, rows[1:]) if b[0] == a[0] + 1 and b[0] in ref]
        if not rel:
            res.append((tid, len(rows), None, rows))
            continue
        res.append((tid, len(rows), float(np.median(np.abs(rel))), rows))
    return res


def fake_labels(path):
    lab = json.load(open(path, encoding="utf-8"))
    rows = {}
    for k, v in lab.items():
        if k != "_meta":
            rows[int(k)] = v
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--tol", type=float, default=0.3)
    ap.add_argument("--labels", default="labels/cloud_with_fake_obj.json")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    report = {}
    for p in sorted(glob.glob(os.path.join(a.run, "*.jsonl"))):
        bag = os.path.splitext(os.path.basename(p))[0]
        rp = os.path.join(a.ref, f"{bag}.jsonl")
        if not os.path.exists(rp):
            continue
        ref = load_ref(rp)
        cls = classify(tracks(p), ref, a.tol)
        lab = fake_labels(a.labels) if bag == "cloud_with_fake_obj" else {}

        def on_object(rows):
            hits = 0
            for f, d, lat in rows:
                for o in lab.get(f, []):
                    if abs(d - o["distance"]) <= max(2.0, 0.03 * o["distance"]) + 0.5 * o["size"][0] and abs(lat - o["lateral"]) <= 1.0:
                        hits += 1
                        break
            return hits >= 0.5 * len(rows)
        entry = {"static_events": 0, "static_frames": 0, "moving_events": 0, "moving_frames": 0,
                 "unknown_events": 0, "unknown_frames": 0, "tracks": []}
        for tid, n, rel, rows in cls:
            kind = "unknown" if rel is None else ("static" if rel < a.tol else "moving")
            obj = on_object(rows) if lab else None
            entry[f"{kind}_events"] += 1
            entry[f"{kind}_frames"] += n
            entry["tracks"].append({"id": tid, "frames": n, "first": rows[0][0], "dist": [round(rows[0][1], 1), round(rows[-1][1], 1)],
                                    "median_rel_m_per_frame": None if rel is None else round(rel, 3), "class": kind,
                                    "on_organizer_object": obj})
        report[bag] = entry
        print(f"{bag:38s} static {entry['static_events']:3d} ev / {entry['static_frames']:4d} fr | moving {entry['moving_events']:3d} ev / "
              f"{entry['moving_frames']:4d} fr | unknown {entry['unknown_events']:3d} ev / {entry['unknown_frames']:4d} fr")
        if lab:
            for t in entry["tracks"]:
                print("    ", t)
            # the labelled objects themselves
            ref_f = ref
            objs = {}
            for f, rows in lab.items():
                for o in rows:
                    objs.setdefault(o["name"], {})[f] = o
            print("  organizer objects: approach per frame vs the train's displacement (m/frame)")
            report["objects"] = {}
            for name, fr in objs.items():
                fs = sorted(fr)
                rel = [(fr[x]["bbox"][0][0] - fr[y]["bbox"][0][0], ref_f[y]) for x, y in zip(fs, fs[1:])
                       if y == x + 1 and y in ref_f and fr[x]["plausible"] and fr[y]["plausible"] and fr[x]["distance"] < 90]
                if not rel:
                    continue
                ob = np.array([r[0] for r in rel])
                tr = np.array([r[1] for r in rel])
                frac_static = float(np.mean(np.abs(ob - tr) < a.tol))
                report["objects"][name] = {"frames": len(rel), "object_m_per_frame": round(float(np.median(ob)), 3),
                                           "train_m_per_frame": round(float(np.median(tr)), 3),
                                           "share_static_within_tol": round(frac_static, 3)}
                print(f"    {name:20s} n={len(rel):3d} object {np.median(ob):5.2f} train {np.median(tr):5.2f} "
                      f"static within {a.tol} m: {frac_static:.0%}")
    if a.json:
        json.dump(report, open(a.json, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
