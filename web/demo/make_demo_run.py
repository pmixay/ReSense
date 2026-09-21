#!/usr/bin/env python3
"""Build a synthetic "approach" sequence and run the detector over it.

Writes a JSONL file in exactly the format of ``python -m resense.cli run --out results.jsonl``:
one ``FrameResult.to_dict()`` per line plus the two extra keys ``frame`` (index) and
``frame_id``; no ``node`` object (that one only exists in the ROS node's status JSON).

The sequence (defaults): ``--clear-before`` empty frames of the synthetic ray-cast tunnel, then
``--approach`` frames with one obstacle injected by ray casting at a distance that shrinks
linearly from ``--start`` to ``--end`` metres (a static object seen from a train closing in at
20 m/s when the defaults 120 -> 40 m over 40 frames are used), then ``--clear-after`` empty
frames.  Runs without the organizers' dataset (needs open3d for the ray casting).

    python web/demo/make_demo_run.py                       # -> out/demo_run.jsonl
    python web/demo/make_demo_run.py --out out/x.jsonl --approach 20 --start 90 --end 40
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

# run from the worktree root: make the checkout importable even when the package is installed
# from another checkout (the editable install points wherever pip last ran)
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from resense import Detector, DetectorConfig            # noqa: E402
from resense.frame import Frame                          # noqa: E402
from resense.synthetic import (ObstacleSpec, augment_background, inject_obstacles,  # noqa: E402
                               synthetic_tunnel_frame)

KINDS = {"person": (0.4, 0.5, 1.7), "box": (0.5, 0.5, 0.5), "plank": (2.0, 0.25, 0.30),
         "cylinder": (0.4, 0.4, 0.9)}


def _restamp(frame: Frame, stamp: float, frame_id: str = "synthetic") -> Frame:
    return Frame(xyz=frame.xyz, intensity=frame.intensity, ring=frame.ring, stamp=stamp,
                 frame_id=frame_id, meta=dict(frame.meta))


def sequence(clear_before: int = 10, approach: int = 40, clear_after: int = 10,
             start: float = 120.0, end: float = 40.0, kind: str = "person", lateral: float = 0.0,
             reflectivity: float = 60.0, seed: int = 1, dt: float = 0.1, jitter: bool = True):
    """Yield ``(index, Frame, ObstacleSpec | None)`` for the approach sequence."""
    rng = np.random.default_rng(seed)
    base, _, gt = synthetic_tunnel_frame(rng=rng)
    size = KINDS[kind]
    i = 0

    def background(k: int) -> Frame:
        if not jitter:
            return base
        # light point dropout and intensity jitter only: no rotation, so the injected object
        # keeps its ground-truth distance and the track model stays comparable frame to frame
        return augment_background(base, rng=np.random.default_rng(seed * 1000 + k), dropout=0.03,
                                  range_noise=0.0, pitch_deg=0.0, yaw_deg=0.0, roll_deg=0.0,
                                  intensity_jitter=0.05)

    for _ in range(clear_before):
        yield i, _restamp(background(i), i * dt), None
        i += 1
    for k in range(approach):
        d = start + (end - start) * k / max(approach - 1, 1)
        spec = ObstacleSpec(kind=kind, size=size, distance=float(d), lateral=lateral,
                            reflectivity=reflectivity, label=f"{kind}_approach")
        inj = inject_obstacles(background(i), gt, [spec], rng=np.random.default_rng(seed * 1000 + 500 + k))
        yield i, _restamp(inj.frame, i * dt), spec
        i += 1
    for _ in range(clear_after):
        yield i, _restamp(background(i), i * dt), None
        i += 1


def run(out_path: str, quiet: bool = False, **kw) -> dict:
    """Run the detector over :func:`sequence` and write the JSONL. Returns a small summary."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    det = Detector(DetectorConfig())
    n = alarms = 0
    dists, times = [], []
    first_alarm = None
    t_start = time.perf_counter()
    with open(out_path, "w", encoding="utf-8") as out:
        for i, frame, spec in sequence(**kw):
            res = det.process(frame)
            d = res.to_dict()
            d["frame"] = i
            d["frame_id"] = frame.frame_id
            out.write(json.dumps(d) + "\n")
            n += 1
            times.append(res.timing_ms["total"])
            if res.obstacle:
                alarms += 1
                dists.append(res.nearest_distance)
                if first_alarm is None:
                    first_alarm = (i, res.nearest_distance, spec.distance if spec else None)
            if not quiet:
                truth = f"gt {spec.distance:6.1f} m" if spec else "gt   clear "
                status = f"OBSTACLE {res.nearest_distance:6.1f} m" if res.obstacle else ("warning" if res.warning else "clear")
                print(f"frame {i:4d}  {truth}  ->  {status:18s} {res.timing_ms['total']:6.1f} ms")
    dt = time.perf_counter() - t_start
    summary = {"out": out_path, "frames": n, "alarm_frames": alarms,
               "first_alarm": first_alarm, "nearest_min_m": min(dists) if dists else None,
               "nearest_max_m": max(dists) if dists else None,
               "detect_ms_mean": float(np.mean(times)), "detect_ms_p95": float(np.percentile(times, 95)),
               "wall_s": dt}
    if not quiet:
        print(json.dumps(summary, indent=1), file=sys.stderr)
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="out/demo_run.jsonl")
    p.add_argument("--clear-before", type=int, default=10)
    p.add_argument("--approach", type=int, default=40)
    p.add_argument("--clear-after", type=int, default=10)
    p.add_argument("--start", type=float, default=120.0, help="m, obstacle distance in the first approach frame")
    p.add_argument("--end", type=float, default=40.0, help="m, obstacle distance in the last approach frame")
    p.add_argument("--kind", choices=sorted(KINDS), default="person")
    p.add_argument("--lateral", type=float, default=0.0, help="m from the track axis, + left")
    p.add_argument("--reflectivity", type=float, default=60.0)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--no-jitter", action="store_true", help="identical background in every frame")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args(argv)
    run(a.out, quiet=a.quiet, clear_before=a.clear_before, approach=a.approach, clear_after=a.clear_after,
        start=a.start, end=a.end, kind=a.kind, lateral=a.lateral, reflectivity=a.reflectivity,
        seed=a.seed, jitter=not a.no_jitter)


if __name__ == "__main__":
    main()
