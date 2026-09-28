#!/usr/bin/env python3
"""Recompute the figures of README.md in this folder from the committed per-frame outputs.

    python3 docs/evidence/judge_outputs_2026-09-28/recompute.py            # table
    python3 docs/evidence/judge_outputs_2026-09-28/recompute.py --json out.json

Counting is the team's own (``scripts/regression_gate.py``: ``recording_entry`` for alarm frames,
alarm events = distinct confirmed track ids, STOP episodes and the labelled hits of
``doubleT_obstacle``; ``set_o_entry`` = ``scripts/score_fake_objects.py`` for set O), applied to
judge A's outputs of the sealed detector instead of the gate's own replay of the frame cache.
It also lists, for every committed node capture of ``doubleT_obstacle`` and for the offline run,
the frames after the person has left the object on the rail (frame >= 75) whose decision is not
STOP. Needs the repository's Python dependencies only (no recordings).
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for _p in (ROOT, os.path.join(ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import regression_gate as rg  # noqa: E402  (scripts/)
from check_dry_run import load as load_status, read_bag  # noqa: E402  (scripts/)
from resense.config import DetectorConfig  # noqa: E402

FIVE = {
    "doubleT_platform": "empty_doubleT_platform",
    "roundT_doubleT": "rt_offline",
    "roundT_pressureGate_roundT": "empty_roundT_pressureGate_roundT",
    "roundT_squareT_pressureGate_squareT": "empty_roundT_squareT_pressureGate_squareT",
    "squareT_platform_squareT_switch": "empty_squareT_platform_squareT_switch",
}
COUNTS = ("frames", "alarm_frames", "alarm_events", "stop_episodes", "advisory_frames")
ALONE = rg.OBJECT_ALONE_FROM
EVIDENCE = os.path.join(ROOT, "docs", "evidence")
NODE_CAPTURES = (sorted(glob.glob(os.path.join(EVIDENCE, "node_input_2026-09-28", "ab", "*obst*_status.jsonl.gz")))
                 + [os.path.join(EVIDENCE, "node_input_2026-09-28", "cold_local", "doubleT_obstacle_status.jsonl.gz")]
                 + sorted(glob.glob(os.path.join(EVIDENCE, "p1_p2_supported_playback_2026-09-27", "**",
                                                 "doubleT_obstacle_status.jsonl.gz"), recursive=True)))


def unzip(name: str, tmp: str) -> str:
    out = os.path.join(tmp, name + ".jsonl")
    with gzip.open(os.path.join(HERE, "offline", name + ".jsonl.gz"), "rt", encoding="utf-8") as src, \
            open(out, "w", encoding="utf-8") as dst:
        dst.write(src.read())
    return out


def node_frames(path: str, n_messages: int, bag_stamps=None):
    """Node status results with ``frame`` = the bag message index: the index of the header stamp
    among the recording's own stamps (``--bag``), else its rank among the processed stamps, which
    is the message index only when the node processed every message."""
    frames, _ = load_status(path)
    stamps = sorted({f["stamp"] for f in frames})
    if bag_stamps is not None:
        rank = {s: min(range(len(bag_stamps)), key=lambda k: abs(bag_stamps[k] - s)) for s in stamps}
    elif len(stamps) != n_messages:
        return None, len(stamps)
    else:
        rank = {s: i for i, s in enumerate(stamps)}
    last = {}
    for f in frames:
        last[rank[f["stamp"]]] = f
    rows = []
    for i in sorted(last):
        f = dict(last[i])
        f["frame"] = i
        f["obstacle"] = bool(f.get("detector_obstacle", f["obstacle"]))
        rows.append(f)
    return rows, len(stamps)


def not_stop_after(rows, decision_key="decision"):
    out = []
    for r in rows:
        if int(r["frame"]) >= ALONE:
            stop = r.get(decision_key) == "STOP" if decision_key in r else bool(r["obstacle"])
            if not stop:
                out.append([int(r["frame"]), r.get(decision_key, "no obstacle")])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", help="also write the figures as JSON")
    ap.add_argument("--bag", help="the original doubleT_obstacle recording (rosbag2 directory): index the node "
                                  "captures by its message stamps, also those that skipped frames at start-up")
    a = ap.parse_args(argv)
    bag_stamps = read_bag(a.bag)[1] if a.bag else None
    cfg = DetectorConfig.from_yaml(os.path.join(ROOT, "configs/default.yaml"))
    res = {"five_empty": {}, "ride_segments": {}, "node_doubleT_obstacle": {}}
    with tempfile.TemporaryDirectory() as tmp:
        total = dict.fromkeys(COUNTS, 0)
        for rec, name in FIVE.items():
            e = rg.recording_entry(rec, [unzip(name, tmp)], cfg)
            res["five_empty"][rec] = {k: e[k] for k in COUNTS + ("alarm_dist",)}
            for k in COUNTS:
                total[k] += e[k]
        res["five_empty"]["total"] = total
        path = unzip("dto_offline", tmp)
        e = rg.recording_entry("doubleT_obstacle", [path], cfg, os.path.join(ROOT, "labels/doubleT_obstacle.json"))
        rows = [d for _, d in rg._read_jsonl([path])]
        res["doubleT_obstacle_offline"] = {k: e[k] for k in ("frames", "alarm_frames", "alarm_events", "stop_episodes",
                                                              "first_alarm_frame", "alarm_dist", "labelled")}
        res["doubleT_obstacle_offline"]["not_stop_from_frame_75"] = not_stop_after(rows)
        so = rg.set_o_entry([unzip("seto_offline", tmp)], os.path.join(ROOT, rg.SET_O_LABELS))
        res["set_O_offline"] = so
        for seg in ("ride_46", "ride_68"):
            e = rg.recording_entry(seg, [unzip(seg, tmp)], cfg)
            res["ride_segments"][seg] = {k: e[k] for k in COUNTS}
        node_rows, n = node_frames(os.path.join(HERE, "node_set_o", "status.jsonl.gz"), 1510)
        if node_rows is not None:
            p = os.path.join(tmp, "node_set_o.jsonl")
            with open(p, "w", encoding="utf-8") as fh:
                fh.writelines(json.dumps(r) + "\n" for r in node_rows)
            res["set_O_node"] = rg.set_o_entry([p], os.path.join(ROOT, rg.SET_O_LABELS))
    for path in NODE_CAPTURES:
        rows, n = node_frames(path, 201, bag_stamps)
        key = os.path.relpath(path, EVIDENCE)
        if rows is None:
            res["node_doubleT_obstacle"][key] = {"frames_processed": n,
                                                 "note": "not every message processed: pass --bag to index it"}
            continue
        hits = rg.labelled_hits([(0, r) for r in rows], os.path.join(ROOT, "labels/doubleT_obstacle.json"))
        res["node_doubleT_obstacle"][key] = {"frames_processed": n, "not_stop_from_frame_75": not_stop_after(rows),
                                             "labelled_hits": hits}

    def row(name, e):
        return f"  {name:38s} " + "  ".join(f"{k} {e[k]}" for k in COUNTS)
    print("five obstacle-free recordings, offline on the raw bags (judge A):")
    for rec, e in res["five_empty"].items():
        print(row(rec, e))
    d = res["doubleT_obstacle_offline"]
    lab = d["labelled"]
    print("doubleT_obstacle, offline on the raw bag:", f"alarm frames {d['alarm_frames']}, STOP episodes {d['stop_episodes']},",
          f"first alarm frame {d['first_alarm_frame']}, distance error max {lab['distance_error_max_m']} m")
    for k, v in lab["per_label"].items():
        print(f"  {k}: {v['hits']} of {v['frames']}")
    print(f"  not STOP from frame {ALONE}: {d['not_stop_from_frame_75']}")
    for key in ("set_O_offline", "set_O_node"):
        if key not in res:
            continue
        s = res[key]
        print(f"{key}: inside STOP frames {s['inside_stop_frames']} of {s['inside_visible_frames']}, objects with a STOP "
              f"{s['inside_objects_with_stop']} of {s['inside_objects']}, outside false STOP frames "
              f"{s['outside_false_stop_frames']}, background alarm frames {s['background']['alarm_frames']}")
        for name, o in s["objects"].items():
            if o.get("in_gauge"):
                print(f"  {name:20s} STOP {o['stop_frames']:3d} of {o['visible_frames']:3d}, first STOP {o['first_stop_m']} m, "
                      f"held from {o['held_from_m']} m")
            elif o.get("in_gauge") is False:
                print(f"  {name:20s} (outside) false STOP frames {o['false_stop_frames']}, from {o['false_stop_from_m']} m")
    print("ride segments (judge A, frame cache of new_data 46-48 / 68-70):")
    for seg, e in res["ride_segments"].items():
        print(row(seg, e))
    print(f"node captures of doubleT_obstacle, decisions that are not STOP from frame {ALONE} (bag message index):")
    for key, v in res["node_doubleT_obstacle"].items():
        print(f"  {key}: {v.get('not_stop_from_frame_75', v.get('note'))} ({v['frames_processed']} frames processed)")
        if "labelled_hits" in v:
            print("      labelled hits: " + ", ".join(f"{k} {h['hits']} of {h['frames']}" for k, h in v["labelled_hits"].items()))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
