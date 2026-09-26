#!/usr/bin/env python3
"""Per-object score of a detector run on the organizers' synthetic-obstacle recording.

    resense run --npy /data/cache/cloud_with_fake_obj --out out/fake.jsonl --quiet
    python scripts/score_fake_objects.py out/fake.jsonl --gt labels/cloud_with_fake_obj.json \
        --out out/fake-score.json

For every labelled object (``scripts/label_fake_objects.py``) and every frame in which it has
points, a detection is matched with the rule of ``resense eval`` (``resense.metrics.match``:
the distance within max(2 m, 3 %) plus half the object's length, the lateral offset within
1 m; one-to-one, see ``_assign_detections``):

* an object the organizers put inside the envelope (``in_gauge``) should be matched by an
  alarm (``detections``, the decision STOP). The score gives the alarm frames out of the
  visible frames per range bin, the farthest distance at which it was first confirmed, the
  distance from which the alarm was held in at least 90 % of the remaining visible frames,
  and the frames that were only advisory (``warnings``, CAUTION);
* an object outside the envelope must not be matched by an alarm: every such frame is a
  false alarm on that object (advisory frames are allowed and counted).

Alarms that match no object are background false alarms: the distinct track IDs never matched
to an object in any frame (as ``fp_events`` of ``resense eval``) and the frames that carry one.
Frames are counted where the object is visible and ``plausible`` (inside the tunnel cross-
section: far away the organizers' path leaves the tunnel), so the recall denominators are
the frames in which the sensor had at least one return from a physically possible object.
``in_envelope`` splits them by whether any point lies inside the envelope *measured from the
rails*: the organizers placed the objects from the sensor's axis, which runs at 0.24 deg to
the rails in this recording, so the two frames disagree near the envelope edge.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from resense.metrics import GTObstacle, _assign_detections, _bin_order, gt_meta, load_gt, range_bin  # noqa: E402

HOLD_FRACTION = 0.9


def _held_from(dist_hit):
    """Largest distance D such that the object was matched in >= 90 % of its visible frames closer than D."""
    if not dist_hit:
        return None
    arr = sorted(dist_hit, key=lambda t: t[0])           # nearest first
    hits = np.cumsum([h for _, h in arr])
    held = None
    for i, (d, _) in enumerate(arr):
        if hits[i] >= HOLD_FRACTION * (i + 1):
            held = d
    return held


def _missed_intervals(frames):
    """Visible, plausible object-frame runs without a STOP, split at hits or data gaps."""
    intervals, run = [], []

    def finish():
        if not run:
            return
        distances = [row[1] for row in run]
        intervals.append({"start_frame": run[0][0], "end_frame": run[-1][0], "frames": len(run),
                          "from_m": round(max(distances), 1), "to_m": round(min(distances), 1)})
        run.clear()

    previous_frame = None
    for row in sorted(frames, key=lambda item: item[0]):
        frame, _distance, hit = row[:3]
        if hit or (previous_frame is not None and frame != previous_frame + 1):
            finish()
        if not hit:
            run.append(row)
        previous_frame = frame
    finish()
    return intervals


def score(results, gt):
    objs = {}
    unmatched_by_frame = []           # per frame: IDs of alarms that matched no object there
    matched_ids = set()               # IDs matched to an object in some frame
    alarm_frames = 0
    for r in results:
        key = f"{int(r['frame']):05d}"
        rows = [row for row in gt.get(key, []) if row.get("n_points", 1) > 0]
        gts = [GTObstacle.from_dict(row) for row in rows]      # every visible row takes part in matching
        dets, warns = r.get("detections", []), r.get("warnings", [])
        alarm_frames += int(bool(r.get("obstacle")))
        a_alarm = _assign_detections(dets, gts)
        a_warn = _assign_detections(warns, gts)
        used = set(a_alarm.values())
        for gi, (row, g) in enumerate(zip(rows, gts)):
            if not row.get("plausible", True):
                continue
            o = objs.setdefault(row["label"], {"in_gauge": row["in_gauge"], "frames": [], "bins": {}})
            hit = gi in a_alarm
            adv = (not hit) and gi in a_warn
            o["frames"].append((int(r["frame"]), g.distance, hit, adv, row.get("n_in_envelope", 1) > 0))
            b = o["bins"].setdefault(range_bin(g.distance), [0, 0, 0])
            b[0] += int(hit)
            b[1] += int(adv)
            b[2] += 1
        matched_ids.update(int(dets[i]["id"]) for i in used if "id" in dets[i])
        unmatched_by_frame.append([int(d["id"]) if "id" in d else None
                                   for i, d in enumerate(dets) if i not in used])
    out = {}
    for label, o in objs.items():
        fr = o["frames"]
        hits = [f for f in fr if f[2]]
        advs = [f for f in fr if f[3]]
        entry = {
            "in_gauge": o["in_gauge"],
            "visible_frames": len(fr),
            "first_visible_m": round(max(f[1] for f in fr), 1),
            "alarm_frames": len(hits),
            "advisory_only_frames": len(advs),
            "frames_in_envelope": sum(1 for f in fr if f[4]),
            "alarm_frames_in_envelope": sum(1 for f in hits if f[4]),
            "bins": {k: {"alarm": v[0], "advisory_only": v[1], "visible": v[2]}
                     for k, v in sorted(o["bins"].items(), key=lambda kv: _bin_order(kv[0]))},
        }
        if o["in_gauge"]:
            entry["missed_intervals"] = _missed_intervals(fr)
        if o["in_gauge"]:
            entry["first_alarm_m"] = round(max(f[1] for f in hits), 1) if hits else None
            entry["first_alarm_frame"] = min(f[0] for f in hits) if hits else None
            held = _held_from([(f[1], f[2]) for f in fr])
            entry["alarm_held_from_m"] = round(held, 1) if held is not None else None
            entry["first_advisory_or_alarm_m"] = (round(max(f[1] for f in hits + advs), 1)
                                                  if hits or advs else None)
            entry["verdict"] = ("detected" if hits else "advisory only" if advs else "missed")
        else:
            entry["false_alarm_frames"] = len(hits)
            entry["false_alarm_from_m"] = round(max(f[1] for f in hits), 1) if hits else None
            entry["verdict"] = "false alarm" if hits else ("advisory" if advs else "ignored (correct)")
        out[label] = entry
    # as Evaluation.fp_events: a track matched to an object in any frame is that object (held
    # a frame after its label rows end, or briefly beyond the lateral tolerance), not background
    bg_ids = {i for ids in unmatched_by_frame for i in ids if i is not None} - matched_ids
    bg_frames = sum(1 for ids in unmatched_by_frame if any(i is None or i in bg_ids for i in ids))
    return out, {"frames": len(results), "alarm_frames": alarm_frames,
                 "background_alarm_frames": bg_frames, "background_alarm_ids": len(bg_ids)}


def markdown(objs, bg, order):
    lines = ["| # | object | envelope | visible frames (from) | in measured envelope | alarm frames | advisory-only | first STOP | STOP held from | verdict |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---|"]
    for i, label in enumerate(order, 1):
        e = objs.get(label)
        if e is None:
            lines.append(f"| {i} | `{label}` | | not visible | | | | | | |")
            continue
        first = e.get("first_alarm_m") if e["in_gauge"] else e.get("false_alarm_from_m")
        held = e.get("alarm_held_from_m") if e["in_gauge"] else None
        lines.append(f"| {i} | `{label}` | {'inside' if e['in_gauge'] else 'outside'} | "
                     f"{e['visible_frames']} (from {e['first_visible_m']} m) | {e['frames_in_envelope']} | "
                     f"{e['alarm_frames']} | "
                     f"{e['advisory_only_frames']} | {'' if first is None else f'{first} m'} | "
                     f"{'' if held is None else f'{held} m'} | {e['verdict']} |")
    lines.append(f"\nBackground (alarms matching no object): {bg['background_alarm_frames']} frames, "
                 f"{bg['background_alarm_ids']} track IDs; all alarm frames {bg['alarm_frames']} of {bg['frames']}.")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("results", help="JSONL of `resense run --out` on cloud_with_fake_obj (every frame)")
    p.add_argument("--gt", default="labels/cloud_with_fake_obj.json")
    p.add_argument("--out", default=None, help="write the score as JSON")
    a = p.parse_args()
    with open(a.results, encoding="utf-8") as fh:
        results = [json.loads(line) for line in fh if line.strip()]
    gt = load_gt(a.gt)
    order = list(gt_meta(a.gt).get("objects", {}))
    objs, bg = score(results, gt)
    print(markdown(objs, bg, order or sorted(objs)))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"objects": objs, "background": bg, "results": a.results, "gt": a.gt}, fh,
                      ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
