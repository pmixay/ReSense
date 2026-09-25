#!/usr/bin/env python3
"""Check a captured /resense/status stream against the acceptance criteria.

Reads the JSONL produced by ``ros2 topic echo /resense/status --field data`` (one status
JSON per line; ``---`` separators and blank lines are ignored) and asserts the numbers the
dry run promises (README "Acceptance test and CI"): the bag was processed at the expected rate,
the node kept up, and the known obstacle was reported at the expected distance.

Needs nothing but python3 — it runs on the host, not in the container.

    scripts/check_dry_run.py out/status.jsonl --expect-obstacle --distance 50:62
    scripts/check_dry_run.py out/status.jsonl --expect-clear          # false-alarm check on an empty bag
    scripts/check_dry_run.py out/status.jsonl --bag /data/doubleT_obstacle   # holes of the recording itself are no drops

Dropped frames (25.09). ``--max-dropped`` applies to the input frames the node did not
process after the *settle point*: the later of ``--settle-s`` after the first processed frame and
the end of the node's start-up catch-up, but at most ``--max-settle-s``. `ros2 bag play` (Humble)
preloads the bag and then sends its first seconds back to back; the node works through that
backlog one frame every ``catchup_step`` s of recording and skips the frames in between on
purpose (``node.catchup_skipped``). The catch-up ends on the frame that is back on the newest
one (the first frame with ``node.catchup`` false after the catch-up frames of a run that starts
in the first ``--settle-s`` s); on the 360° recording on a 4-core VM that was 7.7-7.9 s of
recording (EXPERIMENTS.md section 3a). A catch-up that has not ended by ``--max-settle-s`` does
not move the settle point further: its skips after it count as drops; one that never ends (the
node is back on the newest frame only when the input stops) does not move it at all. With ``--bag`` (a rosbag2 sqlite3
directory, read with the standard library) the frames the recording itself lacks (the recorder
lost 4 frames of doubleT_obstacle at +14.0 and +16.9 s) are not counted: the criterion is then the
number of the recording's messages between the settle point and the last processed frame that
the node did not process.
"""
from __future__ import annotations

import argparse
import bisect
import glob
import gzip
import json
import math
import os
import pathlib
import re
import sqlite3
import statistics
import struct
import sys


def percentile(values, q):
    """p-th percentile, linear interpolation — same convention as numpy.percentile."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = (len(s) - 1) * q / 100.0
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def load(path):
    """Parse frame results, excluding watchdog/error snapshots (not processed frames).
    A ``*.gz`` capture (the committed evidence, ``docs/evidence/``) is read as is."""
    frames, skipped = [], 0
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line == "---":
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                skipped += 1
                continue
            if (isinstance(obj, dict) and "obstacle" in obj
                    and (obj.get("decision") != "FAULT" or "node" in obj)):
                frames.append(obj)
            else:
                skipped += 1
    return frames, skipped


def startup_catchup_end(rel, flags, settle_s):
    """End of the node's start-up catch-up in s after the first frame: the first frame with
    ``node.catchup`` false after the last run of catch-up frames that starts within ``settle_s``
    (the frame on which the node is back on the newest one). ``rel``: the frames' stamps of one
    recording relative to its first; ``flags``: their ``node.catchup`` (None where the node does
    not report it). None: no start-up catch-up (or a node without the flag); ``math.inf``: it
    never ended - no such frame, or only the recording's last one past ``settle_s`` (a node that
    is behind all along reaches the newest frame only when the input stops)."""
    if not any(f is not None for f in flags):
        return None
    end, i, n = None, 0, len(flags)
    while i < n:
        if flags[i] and rel[i] < settle_s:
            j = next((j for j in range(i + 1, n) if flags[j] is False), None)
            if j is None or (j == n - 1 and rel[j] > settle_s):
                return math.inf
            end, i = rel[j], j + 1
        else:
            i += 1
    return end


def _natural(path):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", os.path.basename(path))]


def cdr_stamp(blob):
    """header.stamp of a CDR-serialized message whose first field is a std_msgs/Header."""
    if blob is None or len(blob) < 12:
        return None
    sec, nsec = struct.unpack_from("<iI" if blob[1] == 1 else ">iI", blob, 4)   # 00 01 = CDR little-endian
    return sec + nsec * 1e-9


def read_bag(bag_dir, topic=None):
    """``(topic, receive times in s sorted, header stamp of the first message)`` of the PointCloud2
    topic of a rosbag2 sqlite3 bag (``topic`` if the bag has it, else its busiest PointCloud2
    topic); None when there is no ``*.db3`` or it cannot be read. Only the receive times and one
    message are read, not the clouds."""
    files = sorted(glob.glob(os.path.join(bag_dir, "*.db3")), key=_natural)
    if not files:
        return None
    times, first, name = [], None, None
    try:
        for path in files:
            con = sqlite3.connect(pathlib.Path(path).absolute().as_uri() + "?mode=ro", uri=True)
            try:
                ids = {n: i for i, n, t in con.execute("SELECT id, name, type FROM topics")
                       if t == "sensor_msgs/msg/PointCloud2"}
                if name is None:
                    if topic in ids:
                        name = topic
                    elif ids:
                        counts = {n: con.execute("SELECT COUNT(*) FROM messages WHERE topic_id = ?", (i,)).fetchone()[0]
                                  for n, i in ids.items()}
                        name = max(counts, key=counts.get)
                if name not in ids:
                    continue
                rows = con.execute("SELECT id, timestamp FROM messages WHERE topic_id = ? ORDER BY timestamp",
                                   (ids[name],)).fetchall()
                if rows and first is None:
                    first = cdr_stamp(con.execute("SELECT data FROM messages WHERE id = ?", (rows[0][0],)).fetchone()[0])
                times.extend(t * 1e-9 for _, t in rows)
            finally:
                con.close()
    except sqlite3.Error:
        return None
    if not times or first is None:
        return None
    times.sort()
    return name, times, first


def match_recording(stamps, rec_times, first_header, period):
    """Index into ``rec_times`` of the recording message behind every processed header stamp
    (None when none is within half a frame period). Header stamps and receive times differ by an
    offset: the first message's, refined by the median residual of the nearest matches."""
    def nearest(t):
        i = bisect.bisect_left(rec_times, t)
        return min((k for k in (i - 1, i) if 0 <= k < len(rec_times)), key=lambda k: abs(rec_times[k] - t))

    off = first_header - rec_times[0]
    if stamps:
        off += statistics.median(s - off - rec_times[nearest(s - off)] for s in stamps)
    out = []
    for s in stamps:
        k = nearest(s - off)
        out.append(k if abs(s - off - rec_times[k]) < 0.5 * period else None)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("status_jsonl")
    p.add_argument("--expect-obstacle", action="store_true",
                   help="require at least --min-alarm-frames frames with obstacle = true")
    p.add_argument("--expect-clear", action="store_true",
                   help="require no frame with obstacle = true (false-alarm check on an empty bag)")
    p.add_argument("--max-alarm-frames", type=int, default=None, metavar="N",
                   help="with --expect-clear: allow up to N alarm frames (the known ones of a recording, "
                        "e.g. 2 at 128-130 m in roundT_doubleT, EXPERIMENTS.md section 0)")
    p.add_argument("--distance", default=None, metavar="LO:HI",
                   help="expected obstacle distance window in metres, e.g. 50:62")
    p.add_argument("--min-alarm-frames", type=int, default=3,
                   help="with --expect-obstacle: how many alarm frames are enough (default 3)")
    p.add_argument("--min-frames", type=int, default=50, help="minimum status messages seen (default 50)")
    p.add_argument("--first-clear", type=int, default=0, metavar="N",
                   help="the first N status messages must report no obstacle (clear lead-in of a bag)")
    p.add_argument("--max-p95-latency", type=float, default=100.0,
                   help="ms, p95 of node.latency_ms = decode + detect (default 100, the 10 Hz frame period)")
    p.add_argument("--max-dropped", type=int, default=0,
                   help="allowed input frames not processed after the settle point: the later of --settle-s and "
                        "the end of the node's start-up catch-up, at most --max-settle-s (default 0)")
    p.add_argument("--settle-s", type=float, default=5.0,
                   help="s of recording time after the first processed frame in which dropped frames are not "
                        "counted: `ros2 bag play` (Humble) preloads the bag and then sends its first seconds "
                        "back to back, which the node works through catchup_step s apart, skipping the "
                        "frames in between (EXPERIMENTS.md section 3b); default 5")
    p.add_argument("--max-settle-s", type=float, default=15.0,
                   help="the node's start-up catch-up (node.catchup, 25.09) moves the settle point past "
                        "--settle-s to the frame on which the node is back on the newest one, but not past this "
                        "many s: the skips of a catch-up that has not ended by then count as drops (default 15; "
                        "the 360-degree recording took 7.7-7.9 s on a 4-core VM, EXPERIMENTS.md section 3a)")
    p.add_argument("--bag", default=None, metavar="DIR",
                   help="the played rosbag2 directory (sqlite3): count the recording's messages the node did not "
                        "process instead of the stamp gaps, so that frames missing from the recording itself "
                        "(doubleT_obstacle lacks 4) are not drops; one recording per capture")
    p.add_argument("--min-fps", type=float, default=None, help="minimum of the last reported node.fps")
    p.add_argument("--expect-inputs", type=int, default=0, metavar="N",
                   help="N recordings played one after another into one node (node.recording counts them); "
                        "with --expect-obstacle every one of them must have --min-alarm-frames alarms")
    p.add_argument("--obstacle-in", default=None, metavar="LIST",
                   help="with --expect-inputs and --expect-obstacle: only these recordings (1-based, e.g. 2 or 1,3) must show the obstacle; default every one")
    args = p.parse_args(argv)

    frames, skipped = load(args.status_jsonl)
    if not frames:
        print(f"FAIL: no status messages parsed from {args.status_jsonl} ({skipped} unparsed lines)")
        return 2

    latencies = [f.get("node", {}).get("latency_ms") for f in frames]
    valid_latencies = [v for v in latencies if isinstance(v, (int, float)) and math.isfinite(v) and v >= 0]
    totals = [f.get("timing_ms", {}).get("total") for f in frames]
    totals = [t for t in totals if t is not None]
    last_node = frames[-1].get("node", {})
    dropped = last_node.get("dropped_frames")
    if not isinstance(dropped, int):
        dropped = None
    catchup_skipped = last_node.get("catchup_skipped")
    if not isinstance(catchup_skipped, int) or isinstance(catchup_skipped, bool):
        catchup_skipped = None
    t0 = frames[0].get("stamp")
    rec0 = frames[0].get("node", {}).get("recording")
    first = [f for f in frames if f.get("node", {}).get("recording") == rec0
             and isinstance(f.get("stamp"), (int, float)) and t0 is not None and f["stamp"] >= t0]
    rel = [f["stamp"] - t0 for f in first]
    # settle point: the later of --settle-s and the end of the start-up catch-up, at most --max-settle-s
    catchup_end = startup_catchup_end(rel, [f.get("node", {}).get("catchup") for f in first], args.settle_s)
    settle = args.settle_s
    if catchup_end is not None and math.isfinite(catchup_end):
        settle = max(settle, min(catchup_end, args.max_settle_s))
    if catchup_end is not None and not math.isfinite(catchup_end):
        after = f"the first {args.settle_s:g} s (the start-up catch-up never ended)"
    elif catchup_end is None or catchup_end <= args.settle_s:
        after = f"the first {args.settle_s:g} s"
    elif catchup_end <= args.max_settle_s:
        after = f"+{settle:.1f} s (the end of the start-up catch-up)"
    else:
        after = f"+{settle:.1f} s (the start-up catch-up had not ended by then)"
    dropped_settled, k = dropped, None
    if dropped is not None and t0 is not None and settle > 0:
        k = next((i for i, f in enumerate(frames) if f.get("stamp") is not None
                  and 0 <= f["stamp"] - t0 and f["stamp"] - t0 >= settle), None)
        base = frames[k].get("node", {}).get("dropped_frames") if k is not None else dropped
        dropped_settled = dropped - base if isinstance(base, int) else None
    # --bag: the recording's messages after the settle point that were not processed (its own holes are no drops)
    lost, bag_line = None, None
    if args.bag:
        recs = {f.get("node", {}).get("recording") for f in frames}
        bag = read_bag(args.bag, frames[0].get("node", {}).get("input_topic")) if len(recs) == 1 else None
        window = [f["stamp"] for f in frames[(k or 0):] if isinstance(f.get("stamp"), (int, float))]
        if len(recs) > 1:
            bag_line = f"--bag not applied: {len(recs)} recordings in the capture"
        elif bag is None:
            bag_line = f"--bag not applied: no readable rosbag2 sqlite3 bag in {args.bag}"
        elif k is None and settle > 0:
            bag_line = "--bag not applied: no frame after the settle point"
        else:
            name, rec_times, first_header = bag
            period = (last_node.get("input_period_ms") or 100.0) / 1e3
            idx = match_recording(window, rec_times, first_header, period)
            matched = [i for i in idx if i is not None]
            if len(matched) < 0.9 * len(idx) or not matched:
                bag_line = (f"--bag not applied: {len(idx) - len(matched)} of {len(idx)} processed frames match no "
                            f"message of {name} in {args.bag}")
            else:
                lo, hi = min(matched), max(matched)
                lost = (hi - lo + 1) - len(set(matched))
                span = (rec_times[hi] - rec_times[lo]) / period + 1
                holes = max(0, round(span) - (hi - lo + 1))
                bag_line = (f"{hi - lo + 1} messages of {name} after {after}, {holes} frame(s) missing from the "
                            f"recording itself; {lost} of its messages not processed")
    fps = last_node.get("fps")
    alarms = [f for f in frames if f["obstacle"]]
    distances = [f["nearest_distance"] for f in alarms if f.get("nearest_distance") is not None]

    p95 = percentile(valid_latencies, 95)
    print(f"status messages      : {len(frames)}" + (f" ({skipped} lines skipped)" if skipped else ""))
    print(f"alarm frames         : {len(alarms)}")
    if distances:
        print(f"obstacle distance    : {min(distances):.1f} .. {max(distances):.1f} m")
    if valid_latencies:
        print(f"latency decode+detect: mean {sum(valid_latencies)/len(valid_latencies):.0f} / "
              f"p95 {p95:.0f} / max {max(valid_latencies):.0f} ms")
    if totals:
        print(f"detector stage total : mean {sum(totals)/len(totals):.0f} / "
              f"p95 {percentile(totals, 95):.0f} ms")
    print(f"dropped input frames : {dropped}" + (f" ({catchup_skipped} of them skipped by the node's catch-up)"
                                                 if catchup_skipped is not None else "")
          + (f"; {dropped_settled} after {after}" if dropped_settled != dropped else ""))
    if catchup_end is not None:
        print("dropped input settle : start-up catch-up "
              + (f"back on the newest frame at +{catchup_end:.1f} s; drops counted after +{settle:.1f} s (the later "
                 f"of {args.settle_s:g} s and that, at most {args.max_settle_s:g} s)" if math.isfinite(catchup_end)
                 else f"never back on the newest frame while the input ran; drops counted after +{settle:.1f} s"))
    if bag_line:
        print(f"dropped input vs bag : {bag_line}")
    print(f"fps (last report)    : {fps}")
    if len(first) > 1:               # the start of the (first) recording: holes, the first STOP
        gaps = [b - a for a, b in zip(rel, rel[1:]) if a < args.settle_s]
        stop = next((r for f, r in zip(first, rel) if f.get("decision") == "STOP"), None)
        print(f"start of the input   : {sum(1 for r in rel if r < args.settle_s)} frames in the first "
              f"{args.settle_s:g} s after the first one, largest gap {max(gaps or [0.0]):.1f} s"
              + (f", first STOP at +{stop:.1f} s" if stop is not None else ""))

    failures = []
    if len(valid_latencies) != len(frames):
        failures.append(f"node.latency_ms missing or invalid in {len(frames) - len(valid_latencies)} "
                        "status messages: cannot check p95 latency")
    if any(not isinstance(f.get("node", {}).get("dropped_frames"), int) for f in frames):
        failures.append("node.dropped_frames missing or invalid in status messages: cannot check input drops")
    if len(frames) < args.min_frames:
        failures.append(f"only {len(frames)} status messages, expected >= {args.min_frames} "
                        "(the node started late or dropped most of the bag)")
    if args.expect_obstacle and len(alarms) < args.min_alarm_frames:
        failures.append(f"{len(alarms)} alarm frames, expected >= {args.min_alarm_frames}")
    allowed = args.max_alarm_frames or 0
    if args.expect_clear and len(alarms) > allowed:
        failures.append(f"{len(alarms)} false alarms on a bag expected to be clear"
                        + (f" (allowed {allowed})" if allowed else ""))
    if args.first_clear > 0:
        early = [i for i, f in enumerate(frames[:args.first_clear]) if f["obstacle"]]
        if early:
            failures.append(f"{len(early)} of the first {args.first_clear} frames report an obstacle "
                            f"(first at message {early[0]}); expected a clear lead-in")
    if args.distance and distances:
        lo, hi = (float(v) for v in args.distance.split(":"))
        out = [d for d in distances if not lo <= d <= hi]
        if out:
            failures.append(f"{len(out)} of {len(distances)} reported distances outside "
                            f"{lo:.0f}..{hi:.0f} m (e.g. {out[0]:.1f} m)")
    elif args.distance and args.expect_obstacle:
        failures.append("no obstacle distance reported, cannot check the distance window")
    if p95 is not None and p95 > args.max_p95_latency:
        failures.append(f"p95 latency {p95:.0f} ms > {args.max_p95_latency:.0f} ms")
    if lost is not None:
        if lost > args.max_dropped:
            failures.append(f"{lost} frames of the recording not processed after {after} > {args.max_dropped}")
    elif dropped_settled is not None and dropped_settled > args.max_dropped:
        failures.append(f"{dropped_settled} dropped input frames after {after} > {args.max_dropped}")
    if args.min_fps is not None and (fps is None or fps < args.min_fps):
        failures.append(f"fps {fps} < {args.min_fps}")
    if args.expect_inputs:
        rec = [f.get("node", {}).get("recording") for f in frames]
        recs = sorted({r for r in rec if r is not None})
        topics = sorted({f.get("node", {}).get("input_topic") for f in frames if f.get("node", {}).get("input_topic")})
        print(f"recordings seen      : {len(recs)} {topics}")
        if len(recs) < args.expect_inputs:
            failures.append(f"{len(recs)} recordings seen, expected {args.expect_inputs} "
                            "(the node did not take the next bag / topic)")
        if args.expect_obstacle:
            want = {int(x) for x in args.obstacle_in.split(",")} if args.obstacle_in else None
            for r in recs:
                if want is not None and r not in want:
                    continue
                n = sum(1 for f, x in zip(frames, rec) if x == r and f["obstacle"])
                if n < args.min_alarm_frames:
                    failures.append(f"recording {r}: {n} alarm frames, expected >= {args.min_alarm_frames}")

    print()
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: all dry-run criteria met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
