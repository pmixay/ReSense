#!/usr/bin/env python3
"""Cold-start replays from many first frames, one row each: which start gives a clean demo bag?

    RESENSE_REPO=<tree> OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \\
    scan_starts.py --bag WIDE_BAG --first-frame 2500 --record l16.jsonl.xz --starts 2760:2980:10 \\
        --last-frame 3200 --out-dir DIR [--jobs 3]

``--starts A:B:STEP`` (or a comma list) are frame numbers of the recording. For each start, a detector that
has seen nothing before it replays the wide bag from that frame to ``--last-frame``
(``coldstart_compare.py``, i.e. the judge's ``NodeReplica``), and the STOP frames are attributed with
``person_track.py``: ``person`` (every STOP detection within 3.5 m of the walking person's distance in the
whole-recording record), ``mixed`` (a person detection and another STOP detection in the same frame),
``other`` (no STOP detection near the person: a false STOP on a structure, or an unexplained one).
Writes ``DIR/start_<A>.{jsonl,summary.json}`` and ``DIR/start_scan.tsv``.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import person_track as pt  # noqa: E402


def parse_starts(text: str) -> list[int]:
    if ":" in text:
        a, b, step = (int(v) for v in text.split(":"))
        return list(range(a, b + 1, step))
    return [int(v) for v in text.split(",")]


def replay(start: int, a, env) -> None:
    prefix = os.path.join(a.out_dir, f"start_{start}")
    if os.path.exists(prefix + ".summary.json") and not a.redo:
        return
    cmd = [sys.executable, str(HERE / "coldstart_compare.py"), "--bag", a.bag, "--record", a.record,
           "--first-frame", str(a.first_frame), "--skip", str(start - a.first_frame), "--last-frame", str(a.last_frame),
           "--out", prefix]
    subprocess.run(cmd, env=env, check=True, stdout=subprocess.DEVNULL)


def longest_run(flags: list[bool]) -> int:
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def row(start: int, a, rec, track) -> dict:
    rows = [json.loads(line) for line in open(os.path.join(a.out_dir, f"start_{start}.jsonl"))]
    rows = [r for r in rows if r["frame"] <= (a.end_frame or a.last_frame)]       # the window to judge
    summ = json.load(open(os.path.join(a.out_dir, f"start_{start}.summary.json")))
    cls: dict[str, list[int]] = {"person": [], "mixed": [], "other": []}
    for r in rows:
        if r["decision"] != "STOP":
            continue
        e = track[r["frame"]]
        near = [abs(d["d"] - e) <= pt.TOL for d in r["dets"]]
        cls["other" if not any(near) else "mixed" if not all(near) else "person"].append(r["frame"])
    stops = sorted(f for v in cls.values() for f in v)
    after = [r for r in rows if r["frame"] >= 3060]            # the record's continuous STOP phase starts at 3059
    go_after_first = [r["frame"] for r in rows if r["decision"] == "GO" and stops and r["frame"] > stops[0]]
    first = next((r for r in rows if r["decision"] == "STOP" and r["frame"] in set(cls["person"] + cls["mixed"])), None)
    first_any = next((r for r in rows if r["decision"] == "STOP"), None)
    t0 = rows[0]["bag_t"]
    return {
        "start": start, "frames": len(rows), "lead_in_frames_before_record_first_stop": 2972 - start,
        "mount_ok_frame": summ["mount_ok_from_frame_replay"], "fault_frames": summ["fault_frames_replay"],
        "stop_frames": len(stops), "stop_person": len(cls["person"]), "stop_mixed": len(cls["mixed"]),
        "stop_other": len(cls["other"]), "other_frames": cls["other"][:12],
        "first_stop_frame": first_any["frame"] if first_any else None,
        "first_stop_m": first_any["nearest"] if first_any else None,
        "first_person_stop_frame": first["frame"] if first else None,
        "first_person_stop_m": first["nearest"] if first else None,
        "first_person_stop_s_from_start": round(first["bag_t"] - t0, 1) if first else None,
        "go_after_first_stop": len(go_after_first),
        "non_stop_frames_from_3060": sum(r["decision"] != "STOP" for r in after),
        "longest_non_stop_run_from_3060": longest_run([r["decision"] != "STOP" for r in after]),
        "frames_with_other_decision_than_record": sum(
            r["decision"] != rec[r["frame"]]["decision"] for r in rows),
        "go_caution_stop_fault": [sum(r["decision"] == k for r in rows) for k in ("GO", "CAUTION", "STOP", "FAULT")],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", required=True)
    ap.add_argument("--first-frame", type=int, required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--starts", required=True)
    ap.add_argument("--last-frame", type=int, required=True, help="the replays run to this frame")
    ap.add_argument("--end-frame", type=int, default=0, help="judge the replays up to this frame (default --last-frame)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    starts = parse_starts(a.starts)
    env = dict(os.environ)
    with ThreadPoolExecutor(a.jobs) as pool:
        list(pool.map(lambda s: replay(s, a, env), starts))
    rec = pt.load(a.record)
    a0, a1, _ = pt.fit(rec)
    track = pt.follow(rec, a0, a1, last=max(a.last_frame, 3400))
    table = [row(s, a, rec, track) for s in starts]
    cols = list(table[0])
    with open(os.path.join(a.out_dir, "start_scan.tsv"), "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for t in table:
            fh.write("\t".join(json.dumps(t[c]) if isinstance(t[c], (list, type(None))) else str(t[c]) for c in cols) + "\n")
    for t in table:
        print(t["start"], "lead", t["lead_in_frames_before_record_first_stop"], "mount_ok", t["mount_ok_frame"],
              "STOP", t["stop_frames"], "person/mixed/other", t["stop_person"], t["stop_mixed"], t["stop_other"],
              t["other_frames"][:5], "first person STOP", t["first_person_stop_frame"], t["first_person_stop_m"],
              "t", t["first_person_stop_s_from_start"], "diff", t["frames_with_other_decision_than_record"],
              "GO after", t["go_after_first_stop"], "non-STOP from 3060", t["non_stop_frames_from_3060"],
              "longest", t["longest_non_stop_run_from_3060"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
