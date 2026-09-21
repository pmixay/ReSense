"""Command line tools: ``resense info | run | inject | eval | summarize | bench``."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from resense.config import DetectorConfig
from resense.detector import Detector


def _cfg(args) -> DetectorConfig:
    return DetectorConfig.from_yaml(args.config) if args.config else DetectorConfig()


def _frames(args, cfg):
    from resense.io import iter_bag_frames, iter_npy_frames
    if args.bag:
        return iter_bag_frames(args.bag, cfg.sensor, topic=args.topic, every=args.every,
                               start=args.start, limit=args.limit)
    return iter_npy_frames(args.npy, cfg.sensor)


def cmd_info(args):
    from resense.io import bag_info, iter_bag_compact
    info = bag_info(args.bag)
    print(json.dumps(info, indent=1, ensure_ascii=False))
    for i, stamp, frame_id, arr in iter_bag_compact(args.bag, limit=1):
        r = np.sqrt(arr["x"] ** 2 + arr["y"] ** 2 + arr["z"] ** 2)
        print(f"first frame: frame_id={frame_id} points={arr.size} range max={r.max():.1f} m "
              f"p99={np.percentile(r, 99):.1f} m rings={np.unique(arr['ring']).size}")


def cmd_run(args):
    cfg = _cfg(args)
    det = Detector(cfg)
    out = open(args.out, "w", encoding="utf-8") if args.out else None
    if args.render:
        os.makedirs(args.render, exist_ok=True)
        from resense.viz import render_frame
    n = 0
    t_start = time.perf_counter()
    for i, frame in _frames(args, cfg):
        res = det.process(frame)
        d = res.to_dict()
        d["frame"] = i
        d["frame_id"] = frame.frame_id
        if out:
            out.write(json.dumps(d) + "\n")
        status = f"OBSTACLE {res.nearest_distance:6.1f} m" if res.obstacle else ("warning" if res.warning else "clear")
        if not args.quiet:
            print(f"frame {i:5d} {status:18s} cand={len(res.candidates):2d} corr={res.corridor_idx.size:6d} "
                  f"yc={res.track.center:+.2f} {res.timing_ms['total']:6.1f} ms")
        if args.render:
            render_frame(frame, res, os.path.join(args.render, f"frame_{i:05d}.png"),
                         x_max=args.x_max, title=f"{os.path.basename(args.bag or args.npy)} #{i}")
        n += 1
    dt = time.perf_counter() - t_start
    print(f"processed {n} frames in {dt:.1f} s ({n / max(dt, 1e-6):.1f} fps incl. I/O)", file=sys.stderr)
    if out:
        out.close()


def cmd_inject(args):
    """Build a labelled synthetic dataset from empty-tunnel frames."""
    from resense.synthetic import ObstacleSpec, inject_obstacles
    from resense.track import estimate_track
    cfg = _cfg(args)
    rng = np.random.default_rng(args.seed)
    os.makedirs(args.out, exist_ok=True)
    kinds = args.kinds.split(",")
    d_lo, d_hi = (float(v) for v in args.distances.split(":"))
    gt = {}
    n = 0
    track = None
    for i, frame in _frames(args, cfg):
        # per-frame model without temporal smoothing: the same model `resense eval --reset-each` sees
        track = estimate_track(frame.xyz, cfg.track, prev=None)
        specs = []
        for _ in range(args.per_frame):
            kind = rng.choice(kinds)
            size = {"person": (0.4, 0.5, 1.7), "box": (0.5, 0.5, 0.5), "plank": (2.0, 0.25, 0.30),
                    "cylinder": (0.4, 0.4, 0.9), "sphere": (0.4, 0.4, 0.4)}[kind]
            in_gauge = rng.random() >= args.negative_fraction
            lateral = rng.uniform(-0.9, 0.9) if in_gauge else rng.choice([-1, 1]) * rng.uniform(2.2, 3.0)
            specs.append(ObstacleSpec(kind=kind, size=size, distance=float(rng.uniform(d_lo, d_hi)),
                                      lateral=float(lateral), yaw_deg=float(rng.uniform(0, 360)),
                                      reflectivity=float(rng.uniform(15, 120)),
                                      label=f"{kind}_{n}_{_}"))
        res = inject_obstacles(frame, track, specs, rng=rng)
        name = f"{n:05d}"
        xyz_s = res.frame.xyz  # store in vehicle frame with labels
        np.savez_compressed(os.path.join(args.out, name + ".npz"), xyz=xyz_s, intensity=res.frame.intensity,
                            labels=res.labels)
        gt[name] = [dict(s.to_dict(), in_gauge=abs(s.lateral) < 1.3, n_points=int(k))
                    for s, k in zip(specs, res.n_added)]
        print(f"{name}: " + ", ".join(f"{s.kind}@{s.distance:.0f}m dy={s.lateral:+.1f} -> {k} pts" for s, k in zip(specs, res.n_added)))
        n += 1
    json.dump(gt, open(os.path.join(args.out, "gt.json"), "w"), indent=1)
    print(f"wrote {n} frames to {args.out}")


def cmd_eval(args):
    """Run the detector over an injected dataset (npz + gt.json) and report metrics."""
    import glob
    from resense.frame import Frame
    from resense.metrics import Evaluation, GTObstacle
    cfg = _cfg(args)
    gt = json.load(open(os.path.join(args.dataset, "gt.json")))
    det = Detector(cfg)
    ev = Evaluation()
    n_occluded = 0
    for f in sorted(glob.glob(os.path.join(args.dataset, "*.npz"))):
        name = os.path.splitext(os.path.basename(f))[0]
        z = np.load(f)
        frame = Frame(xyz=z["xyz"], intensity=z["intensity"], ring=None, stamp=0.0, frame_id=name)
        if args.reset_each:
            det.reset()
        res = None
        for _ in range(args.repeat):   # static repeat emulates persistence on single frames
            res = det.process(frame)
        gts = [GTObstacle.from_dict(g) for g in gt.get(name, []) if g.get("n_points", 1) > 0]
        n_occluded += sum(1 for g in gt.get(name, []) if g.get("n_points", 1) == 0)
        ev.add_frame(res.to_dict(), gts)
    out = ev.summary()
    out["occluded_gt_skipped"] = n_occluded
    print(json.dumps(out, indent=1))


def _iter_jsonl(path: str, unparsed: list):
    """Yield the status dicts of a ``resense run --out`` file or of a
    ``ros2 topic echo /resense/status --field data`` capture (``---`` separators ignored);
    lines that are not a status JSON are appended to ``unparsed``."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line == "---":
                continue
            try:
                d = json.loads(line)
            except ValueError:
                unparsed.append(line)
                continue
            if not isinstance(d, dict) or "obstacle" not in d:
                unparsed.append(line)
                continue
            yield d


def cmd_summarize(args):
    """Headline numbers of a JSONL written by ``resense run --out`` (or a status capture):
    frames, alarm frames and events, advisory frames, alarm distances, latency, bag time,
    events per hour / km, and the subsampling caveat."""
    from resense.metrics import Evaluation, format_summary, gt_key, gt_objects, load_gt
    cfg = _cfg(args)
    gt = load_gt(args.gt) if args.gt else None
    ev = Evaluation(confirm_hits=cfg.tracking.confirm_hits, frame_dt=cfg.tracking.frame_dt)
    n_occluded = 0
    unparsed = []
    for d in _iter_jsonl(args.results, unparsed):
        rows = []
        if gt is not None:
            key = gt_key(d["frame"]) if d.get("frame") is not None else None
            if key not in gt and args.labelled_only:
                continue
            rows = gt.get(key, []) if key is not None else []
        n_occluded += sum(1 for r in rows if r.get("n_points", 1) == 0)
        ev.add_frame(d, gt_objects(rows), speed_mps=args.speed_mps)
    out = ev.summary()
    out["occluded_gt_skipped"] = n_occluded
    out["unparsed_lines"] = len(unparsed)
    if args.json:
        print(json.dumps(out, indent=1))
    else:
        print(format_summary(out))
        if unparsed:
            print(f"({len(unparsed)} unparsed lines skipped)")
    return out


def cmd_bench(args):
    cfg = _cfg(args)
    det = Detector(cfg)
    times = []
    for i, frame in _frames(args, cfg):
        res = det.process(frame)
        times.append(res.timing_ms)
    keys = times[0].keys()
    for k in keys:
        v = np.array([t[k] for t in times])
        print(f"{k:10s} mean {v.mean():7.1f} ms  p95 {np.percentile(v, 95):7.1f} ms  max {v.max():7.1f} ms")


def main(argv=None):
    p = argparse.ArgumentParser(prog="resense", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_input(sp, need=True):
        g = sp.add_mutually_exclusive_group(required=need)
        g.add_argument("--bag", help="ROS 2 bag directory")
        g.add_argument("--npy", help="directory with cached *.npy frames (sensor frame)")
        sp.add_argument("--topic", default=None)
        sp.add_argument("--every", type=int, default=1, help="use every N-th frame")
        sp.add_argument("--start", type=int, default=0)
        sp.add_argument("--limit", type=int, default=None)
        sp.add_argument("--config", default=None, help="YAML config (configs/default.yaml)")

    sp = sub.add_parser("info", help="print bag metadata and first-frame stats")
    sp.add_argument("bag")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("run", help="run the detector offline")
    add_input(sp)
    sp.add_argument("--out", help="JSONL results")
    sp.add_argument("--render", help="directory for PNG renders")
    sp.add_argument("--x-max", type=float, default=150.0)
    sp.add_argument("--quiet", action="store_true")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("inject", help="inject synthetic obstacles into empty frames")
    add_input(sp)
    sp.add_argument("--out", required=True)
    sp.add_argument("--kinds", default="person,box,plank,cylinder")
    sp.add_argument("--distances", default="10:250", help="lo:hi metres")
    sp.add_argument("--per-frame", type=int, default=1)
    sp.add_argument("--negative-fraction", type=float, default=0.2, help="share of objects placed outside the gauge")
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=cmd_inject)

    sp = sub.add_parser("eval", help="evaluate on an injected dataset")
    sp.add_argument("dataset")
    sp.add_argument("--config", default=None)
    sp.add_argument("--repeat", type=int, default=3, help="process each frame N times (persistence)")
    sp.add_argument("--reset-each", action="store_true")
    sp.set_defaults(func=cmd_eval)

    sp = sub.add_parser("summarize", help="headline numbers of a `run --out` JSONL (alarm events, per hour/km, latency)")
    sp.add_argument("results", help="JSONL from `resense run --out` or a /resense/status capture")
    sp.add_argument("--speed-mps", type=float, default=None, help="constant train speed (m/s) for events per km; "
                    "a per-frame ego_speed_mps key in the JSON is used otherwise")
    sp.add_argument("--gt", default=None, help="gt.json with labels keyed by 5-digit bag frame index (docs/DATASET.md)")
    sp.add_argument("--labelled-only", action="store_true", help="with --gt: count only frames that have a gt.json entry")
    sp.add_argument("--config", default=None, help="YAML config (for tracking.confirm_hits / frame_dt in the caveat)")
    sp.add_argument("--json", action="store_true", help="print the full summary as JSON")
    sp.set_defaults(func=cmd_summarize)

    sp = sub.add_parser("bench", help="timing per stage")
    add_input(sp)
    sp.set_defaults(func=cmd_bench)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
