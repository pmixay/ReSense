#!/usr/bin/env python3
"""Check a captured /resense/status stream against the acceptance criteria.

Reads the JSONL produced by ``ros2 topic echo /resense/status --field data`` (one status
JSON per line; ``---`` separators and blank lines are ignored) and asserts the numbers the
submission dry run promises (docs/SUBMISSION.md): the bag was processed at the expected rate,
the node kept up, and the known obstacle was reported at the expected distance.

Needs nothing but python3 — it runs on the host, not in the container.

    scripts/check_dry_run.py out/status.jsonl --expect-obstacle --distance 50:62
    scripts/check_dry_run.py out/status.jsonl --expect-clear          # false-alarm check on an empty bag
"""
from __future__ import annotations

import argparse
import json
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
    """Parse the echo capture, skipping separators and any non-JSON noise."""
    frames, skipped = [], 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line == "---":
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                skipped += 1
                continue
            if isinstance(obj, dict) and "obstacle" in obj:
                frames.append(obj)
            else:
                skipped += 1
    return frames, skipped


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("status_jsonl")
    p.add_argument("--expect-obstacle", action="store_true",
                   help="require at least --min-alarm-frames frames with obstacle = true")
    p.add_argument("--expect-clear", action="store_true",
                   help="require no frame with obstacle = true (false-alarm check on an empty bag)")
    p.add_argument("--distance", default=None, metavar="LO:HI",
                   help="expected obstacle distance window in metres, e.g. 50:62")
    p.add_argument("--min-alarm-frames", type=int, default=3,
                   help="with --expect-obstacle: how many alarm frames are enough (default 3)")
    p.add_argument("--min-frames", type=int, default=50, help="minimum status messages seen (default 50)")
    p.add_argument("--max-p95-latency", type=float, default=100.0,
                   help="ms, p95 of node.latency_ms = decode + detect (default 100, the 10 Hz frame period)")
    p.add_argument("--max-dropped", type=int, default=0, help="allowed dropped input frames (default 0)")
    p.add_argument("--min-fps", type=float, default=None, help="minimum of the last reported node.fps")
    args = p.parse_args(argv)

    frames, skipped = load(args.status_jsonl)
    if not frames:
        print(f"FAIL: no status messages parsed from {args.status_jsonl} ({skipped} unparsed lines)")
        return 2

    latencies = [f["node"]["latency_ms"] for f in frames if "node" in f and "latency_ms" in f["node"]]
    totals = [f.get("timing_ms", {}).get("total") for f in frames]
    totals = [t for t in totals if t is not None]
    last_node = frames[-1].get("node", {})
    dropped = last_node.get("dropped_frames")
    fps = last_node.get("fps")
    alarms = [f for f in frames if f["obstacle"]]
    distances = [f["nearest_distance"] for f in alarms if f.get("nearest_distance") is not None]

    p95 = percentile(latencies, 95)
    print(f"status messages      : {len(frames)}" + (f" ({skipped} lines skipped)" if skipped else ""))
    print(f"alarm frames         : {len(alarms)}")
    if distances:
        print(f"obstacle distance    : {min(distances):.1f} .. {max(distances):.1f} m")
    if latencies:
        print(f"latency decode+detect: mean {sum(latencies)/len(latencies):.0f} / "
              f"p95 {p95:.0f} / max {max(latencies):.0f} ms")
    if totals:
        print(f"detector stage total : mean {sum(totals)/len(totals):.0f} / "
              f"p95 {percentile(totals, 95):.0f} ms")
    print(f"dropped input frames : {dropped}")
    print(f"fps (last report)    : {fps}")

    failures = []
    if len(frames) < args.min_frames:
        failures.append(f"only {len(frames)} status messages, expected >= {args.min_frames} "
                        "(the node started late or dropped most of the bag)")
    if args.expect_obstacle and len(alarms) < args.min_alarm_frames:
        failures.append(f"{len(alarms)} alarm frames, expected >= {args.min_alarm_frames}")
    if args.expect_clear and alarms:
        failures.append(f"{len(alarms)} false alarms on a bag expected to be clear")
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
    if dropped is not None and dropped > args.max_dropped:
        failures.append(f"{dropped} dropped input frames > {args.max_dropped}")
    if args.min_fps is not None and (fps is None or fps < args.min_fps):
        failures.append(f"fps {fps} < {args.min_fps}")

    print()
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: all dry-run criteria met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
