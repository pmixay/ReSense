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


def _frames(args, cfg, npy_stride: bool = True):
    """(index, Frame) iterator for --bag / --npy. ``--every/--start/--limit`` apply to a bag and
    to a cached directory alike; for cached files the index (and the 0.1 s stamp) comes from the
    bag frame number at the end of the file name (``scripts/cache_frames.py`` output), so a
    strided cache keeps its bag time."""
    from resense.io import iter_bag_frames, iter_npy_frames
    if args.bag:
        return iter_bag_frames(args.bag, cfg.sensor, topic=args.topic, every=args.every,
                               start=args.start, limit=args.limit)
    if npy_stride:
        return iter_npy_frames(args.npy, cfg.sensor, every=args.every, start=args.start, limit=args.limit,
                               index_from_name=True)
    return iter_npy_frames(args.npy, cfg.sensor, index_from_name=True)


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
    ego_speed = getattr(args, "ego_speed", None)
    for i, frame in _frames(args, cfg):
        res = det.process(frame, ego_speed=ego_speed)
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
    """Build a labelled synthetic dataset from empty-tunnel frames (docs/DATASET.md).

    Objects come from the catalogue (``--kinds`` names, sizes and reflectivity ranges in
    ``resense.synthetic.OBJECT_CATALOGUE``), one object set per background frame. With
    ``--sequence N --speed V`` every background frame becomes N frames in which the objects
    approach by ``V * tracking.frame_dt`` per step (same background, files numbered in order,
    gt rows carrying ``seq`` / ``seq_step`` / ``speed_mps``), so ``resense eval --repeat 1``
    sees a moving-toward run and measures the first-detection distance. ``--augment``
    applies :func:`resense.synthetic.augment_background` (dropout, range noise, small
    mount rotations, intensity jitter) to the background before injection.
    """
    from resense.synthetic import OBJECT_CATALOGUE, augment_background, catalogue_spec, inject_obstacles
    from resense.track import estimate_track
    cfg = _cfg(args)
    rng = np.random.default_rng(args.seed)
    os.makedirs(args.out, exist_ok=True)
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]
    unknown = [k for k in kinds if k not in OBJECT_CATALOGUE]
    if unknown:
        raise SystemExit(f"unknown object(s) {unknown}; known: {', '.join(OBJECT_CATALOGUE)}")
    d_lo, d_hi = (float(v) for v in args.distances.split(":"))
    n_seq = max(int(args.sequence), 1)
    speed = float(args.speed)
    step = speed * cfg.tracking.frame_dt
    if n_seq > 1 and step <= 0:
        raise SystemExit("--sequence N needs --speed V > 0 (m/s)")
    gt = {"_meta": {"source": "inject", "kinds": kinds, "distances": [d_lo, d_hi], "per_frame": args.per_frame,
                    "negative_fraction": args.negative_fraction, "sequence": n_seq, "speed_mps": speed,
                    "frame_dt": cfg.tracking.frame_dt, "augment": bool(args.augment), "seed": args.seed,
                    "input": args.bag or args.npy, "every": args.every, "start": args.start}}
    n = 0
    n_bg = 0
    for i, frame in _frames(args, cfg, npy_stride=True):
        if args.augment:
            frame = augment_background(frame, rng=rng)
        # per-frame model without temporal smoothing: the same model `resense eval --reset-each` sees
        track = estimate_track(frame.xyz, cfg.track, prev=None)
        objs = []   # (name, distance, lateral, yaw, reflectivity, label) drawn once per background frame
        for j in range(args.per_frame):
            name = str(rng.choice(kinds))
            in_gauge = rng.random() >= args.negative_fraction
            lateral = rng.uniform(-0.9, 0.9) if in_gauge else rng.choice([-1, 1]) * rng.uniform(2.2, 3.0)
            refl = catalogue_spec(name, 0.0, rng=rng).reflectivity
            objs.append((name, float(rng.uniform(d_lo, d_hi)), float(lateral), float(rng.uniform(0, 360)), refl,
                         f"{name}_{n_bg}_{j}"))
        for k in range(n_seq):
            specs = [catalogue_spec(name, dist - k * step, lateral, yaw, reflectivity=refl, label=label)
                     for name, dist, lateral, yaw, refl, label in objs]
            if any(s.distance < cfg.gauge.range_min for s in specs):
                break   # the object has reached the sensor: the approach sequence ends here
            res = inject_obstacles(frame, track, specs, rng=rng)
            name_out = f"{n:05d}"
            stamp = float(frame.stamp) + k * cfg.tracking.frame_dt
            np.savez_compressed(os.path.join(args.out, name_out + ".npz"), xyz=res.frame.xyz,   # vehicle frame
                                intensity=res.frame.intensity, labels=res.labels, stamp=stamp)
            gt[name_out] = [dict(s.to_dict(), name=o[0], in_gauge=abs(s.lateral) < 1.3, n_points=int(cnt),
                                 seq=n_bg, seq_step=k, speed_mps=speed)
                            for s, o, cnt in zip(specs, objs, res.n_added)]
            print(f"{name_out}: " + ", ".join(f"{o[0]}@{s.distance:.0f}m dy={s.lateral:+.1f} -> {cnt} pts"
                                             for s, o, cnt in zip(specs, objs, res.n_added)))
            n += 1
        n_bg += 1
    with open(os.path.join(args.out, "gt.json"), "w", encoding="utf-8") as fh:
        json.dump(gt, fh, indent=1)
    print(f"wrote {n} frames ({n_bg} backgrounds) to {args.out}")


def _iter_npz_dataset(directory: str):
    """(key, Frame) for an injected dataset: ``<key>.npz`` files in sorted order."""
    import glob
    from resense.frame import Frame
    for f in sorted(glob.glob(os.path.join(directory, "*.npz"))):
        name = os.path.splitext(os.path.basename(f))[0]
        z = np.load(f)
        stamp = float(z["stamp"]) if "stamp" in z.files else 0.0
        yield name, Frame(xyz=z["xyz"], intensity=z["intensity"], ring=None, stamp=stamp, frame_id=name)


def _iter_labelled_source(args, cfg):
    """(key, Frame) for ``--bag`` (key = zero-padded bag frame index) or ``--npy`` (key = the
    number at the end of the file name, else the file position; ``--every/--start/--limit``
    select files like bag frames)."""
    from resense.io import iter_bag_frames, iter_npy_frames
    from resense.metrics import gt_key
    if args.bag:
        it = iter_bag_frames(args.bag, cfg.sensor, topic=args.topic, every=args.every, start=args.start,
                             limit=args.limit)
    else:
        it = iter_npy_frames(args.npy, cfg.sensor, every=args.every, start=args.start, limit=args.limit,
                             index_from_name=True)
    for i, frame in it:
        yield gt_key(i), frame


def cmd_eval(args):
    """Run the detector against ground truth and report metrics.

    * ``resense eval <dir>``: an injected dataset (``*.npz`` + ``gt.json`` from ``resense inject``);
    * ``resense eval --bag <bag> --gt gt.json [--every N]`` / ``--npy <dir> --gt gt.json``:
      a real bag or cached frames against labels keyed by the 5-digit bag frame index
      (docs/DATASET.md "Label format"). Frames absent from ``gt.json`` count as empty unless
      ``--labelled-only``; all frames are still processed so the tracker state is realistic.
    """
    from resense.metrics import Evaluation, format_summary, gt_meta, gt_objects, gt_row_speed, load_gt
    cfg = _cfg(args)
    if args.dataset:
        gt_path = args.gt or os.path.join(args.dataset, "gt.json")
        source = _iter_npz_dataset(args.dataset)
    elif args.bag or args.npy:
        if not args.gt:
            raise SystemExit("resense eval --bag/--npy needs --gt gt.json")
        gt_path = args.gt
        source = _iter_labelled_source(args, cfg)
    else:
        raise SystemExit("resense eval: give an injected dataset directory, or --bag <bag> / --npy <dir> with --gt")
    gt = load_gt(gt_path)
    meta = gt_meta(gt_path)
    # static injected frames: repeat each as often as the tracker needs to confirm a static
    # object (tracking.confirm_hits / confirm_time_s: 5 at 10 Hz) to emulate persistence;
    # sequences and real sources are already in frame order, so every frame is processed once
    repeat = args.repeat
    if repeat is None:
        repeat = cfg.tracking.frames_to_confirm() if (args.dataset and int(meta.get("sequence", 1)) <= 1) else 1
    det = Detector(cfg)
    ev = Evaluation(confirm_hits=cfg.tracking.frames_to_confirm(), frame_dt=cfg.tracking.frame_dt)
    out_fh = open(args.out, "w", encoding="utf-8") if args.out else None
    n_occluded = 0
    n_processed = 0
    const_speed = getattr(args, "ego_speed", None)
    use_gt_speed = not getattr(args, "no_gt_speed", False)
    for key, frame in source:
        if args.reset_each:
            det.reset()
        # the speed the detector is given, as the ROS node gives it: --ego-speed V, else the
        # simulated train speed of an `inject --sequence` row (speed_mps > 0), else none
        ego_speed = const_speed
        if ego_speed is None and use_gt_speed:
            ego_speed = gt_row_speed(gt.get(key, []))
        res = None
        for _ in range(repeat):
            res = det.process(frame, ego_speed=ego_speed)
        d = res.to_dict()
        d["frame"] = int(key) if key.isdigit() else None
        d["frame_id"] = frame.frame_id
        n_processed += 1
        if out_fh:
            out_fh.write(json.dumps(d) + "\n")
        if args.labelled_only and key not in gt:
            continue
        rows = gt.get(key, [])
        n_occluded += sum(1 for r in rows if r.get("n_points", 1) == 0)
        ev.add_frame(d, gt_objects(rows), speed_mps=args.speed_mps)
    if out_fh:
        out_fh.close()
    out = ev.summary()
    out["occluded_gt_skipped"] = n_occluded
    out["frames_processed"] = n_processed
    out["gt_frames"] = len(gt)
    out["repeat"] = repeat
    if args.text:
        print(format_summary(out))
        print(f"occluded gt skipped: {n_occluded}; frames processed: {n_processed}; labelled frames in gt: {len(gt)}")
    else:
        print(json.dumps(out, indent=1))
    return out


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


def _summarize_file(path: str, args, cfg, gt) -> dict:
    """``Evaluation.summary()`` of one JSONL file (plus ``occluded_gt_skipped``,
    ``unparsed_lines`` and ``file``)."""
    from resense.metrics import Evaluation, gt_key, gt_objects
    ev = Evaluation(confirm_hits=cfg.tracking.frames_to_confirm(), frame_dt=cfg.tracking.frame_dt)
    n_occluded = 0
    unparsed = []
    for d in _iter_jsonl(path, unparsed):
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
    out["file"] = path
    return out


def cmd_summarize(args):
    """Headline numbers of a JSONL written by ``resense run --out`` (or a status capture):
    frames, alarm frames and events, advisory frames, alarm distances, latency, bag time,
    events per hour / km, and the subsampling caveat. With two or more files (positional or
    ``--compare``) a before/after table is printed instead (one column per file, a delta
    column for exactly two) and a list of summaries is returned."""
    from resense.metrics import format_comparison, format_summary, load_gt
    files = list(args.results or []) + list(args.compare or [])
    if not files:
        raise SystemExit("resense summarize: give at least one JSONL file (or --compare a.jsonl b.jsonl)")
    cfg = _cfg(args)
    gt = load_gt(args.gt) if args.gt else None
    outs = [_summarize_file(f, args, cfg, gt) for f in files]
    if len(outs) == 1:
        out = outs[0]
        if args.json:
            print(json.dumps(out, indent=1))
        else:
            print(format_summary(out))
            if out["unparsed_lines"]:
                print(f"({out['unparsed_lines']} unparsed lines skipped)")
        return out
    if args.json:
        print(json.dumps(outs, indent=1))
    else:
        print(format_comparison(outs))
    return outs


def cmd_bench(args):
    cfg = _cfg(args)
    det = Detector(cfg)
    times = []
    ego_speed = getattr(args, "ego_speed", None)
    for i, frame in _frames(args, cfg):
        res = det.process(frame, ego_speed=ego_speed)
        times.append(res.timing_ms)
    if not times:
        source = args.bag or args.npy
        raise SystemExit(f"resense bench: no input frames found in {source!r}; provide a ROS bag or non-empty cache")
    keys = times[0].keys()
    for k in keys:
        v = np.array([t[k] for t in times])
        print(f"{k:10s} mean {v.mean():7.1f} ms  p95 {np.percentile(v, 95):7.1f} ms  max {v.max():7.1f} ms")


def run_cli(argv=None):
    """Parse ``argv`` and run the command; returns the command's result (a dict for ``eval`` /
    ``summarize``, else None) so that tests can inspect it."""
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
    sp.add_argument("--ego-speed", type=float, default=None,
                    help="train speed in m/s given to the detector on every frame (ego_speed_source 'given', "
                         "as the ROS node does with ego_speed_mps / odometry); default: none, the detector "
                          "uses the single-frame path unless accumulation.estimate_speed is enabled")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("inject", help="inject synthetic obstacles into empty frames")
    add_input(sp)
    sp.add_argument("--out", required=True)
    sp.add_argument("--kinds", default="person,box,plank,cylinder",
                    help="comma-separated catalogue names: person, hivis, box0.2, box0.5, box1.0, box (= box0.5), "
                         "plank, trolley, cylinder, sphere (sizes and reflectivity ranges in docs/DATASET.md)")
    sp.add_argument("--distances", default="10:250", help="lo:hi metres")
    sp.add_argument("--per-frame", type=int, default=1)
    sp.add_argument("--negative-fraction", type=float, default=0.2, help="share of objects placed outside the gauge")
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--sequence", type=int, default=1, help="N frames per background with the object approaching "
                    "by --speed * tracking.frame_dt per step (first-detection distance with eval --repeat 1)")
    sp.add_argument("--speed", type=float, default=0.0, help="m/s, simulated train speed for --sequence")
    sp.add_argument("--augment", action="store_true", help="augment the background (dropout, range noise, small "
                    "mount rotations, intensity jitter) before injection")
    sp.set_defaults(func=cmd_inject)

    sp = sub.add_parser("eval", help="evaluate on an injected dataset, or a bag / npy directory against gt.json labels")
    sp.add_argument("dataset", nargs="?", default=None, help="injected dataset directory (*.npz + gt.json)")
    add_input(sp, need=False)
    sp.add_argument("--gt", default=None, help="gt.json (default <dataset>/gt.json; required with --bag/--npy)")
    sp.add_argument("--repeat", type=int, default=None, help="process each frame N times; default for a static injected "
                    "dataset: the frames the tracker needs to confirm (5 at 10 Hz, emulates persistence); 1 for "
                    "inject --sequence datasets, bags and npy")
    sp.add_argument("--reset-each", action="store_true")
    sp.add_argument("--labelled-only", action="store_true", help="count only frames that have a gt.json entry "
                    "(all frames are still processed)")
    sp.add_argument("--speed-mps", type=float, default=None, help="constant train speed for events per km")
    sp.add_argument("--out", default=None, help="also write the per-frame results as JSONL (for summarize / renders)")
    sp.add_argument("--text", action="store_true", help="human-readable summary instead of JSON")
    sp.add_argument("--ego-speed", type=float, default=None,
                    help="train speed in m/s given to the detector on every frame (ego_speed_source 'given'); "
                          "default: the speed_mps of `inject --sequence` rows, else none (single-frame unless "
                          "accumulation.estimate_speed is enabled)")
    sp.add_argument("--no-gt-speed", action="store_true",
                    help="do not give the detector the speed_mps of `inject --sequence` rows (single-frame / "
                         "single-frame by default; estimated only if enabled)")
    sp.set_defaults(func=cmd_eval)

    sp = sub.add_parser("summarize", help="headline numbers of a `run --out` JSONL (alarm events, per hour/km, latency); "
                                          "two or more files give a before/after table")
    sp.add_argument("results", nargs="*", help="JSONL from `resense run --out` or a /resense/status capture; "
                                               "several files are compared side by side")
    sp.add_argument("--compare", nargs="+", default=None, metavar="JSONL",
                    help="more files to put next to the first one (before/after table: frames, alarm frames, "
                         "events, advisory, first alarm frame, distance range, latency)")
    sp.add_argument("--speed-mps", type=float, default=None, help="constant train speed (m/s) for events per km; "
                    "a per-frame ego_speed_mps key in the JSON is used otherwise")
    sp.add_argument("--gt", default=None, help="gt.json with labels keyed by 5-digit bag frame index (docs/DATASET.md)")
    sp.add_argument("--labelled-only", action="store_true", help="with --gt: count only frames that have a gt.json entry")
    sp.add_argument("--config", default=None, help="YAML config (for tracking.confirm_hits / frame_dt in the caveat)")
    sp.add_argument("--json", action="store_true", help="print the full summary as JSON")
    sp.set_defaults(func=cmd_summarize)

    sp = sub.add_parser("bench", help="timing per stage")
    add_input(sp)
    sp.add_argument("--ego-speed", type=float, default=None,
                    help="train speed in m/s given to the detector (skips the estimator, enables accumulation)")
    sp.set_defaults(func=cmd_bench)

    args = p.parse_args(argv)
    return args.func(args)


def main(argv=None) -> int:
    """Console-script entry point (``resense ...``): exit status 0 on success."""
    run_cli(argv)
    return 0


if __name__ == "__main__":
    main()
