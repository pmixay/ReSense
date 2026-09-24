#!/usr/bin/env python3
"""Long-range evaluation with synthetic positives on a moving real background (set F).

Earlier synthetic sequences (``resense inject --sequence``) moved the object towards a frozen
background frame: the tunnel did not move, so neither the track model nor the tracker saw a
real approach. Here an object is placed at a fixed point of the tunnel ahead of a run of
**consecutive frames of the organizers' 20-minute ride** (``new_data``) and ray-cast into every
frame at the distance it has at that moment: ``d_k = d_0 - sum(v_i * dt_i)``, with the frame
interval from the bag stamps and the train speed of the ride (``--speeds``, the per-file speed
measured from static tracks in ``docs/extended_dataset_intake.json``). Background, motion,
far-field sparsity and sightline are real; only the object is synthetic.

Placement modes: ``legacy`` uses the evaluated frame's axis and floor estimate;
``anchored`` transports an object back from a <=30 m rail-supported near track fit using
near fits in consecutive empty frames, rejecting gaps or missing timestamps. Anchored
placement does not use the detector's far axis, but relies on estimated speed and track fits,
not surveyed ground truth. ``independent`` uses an externally measured vehicle-frame axis
and rail height; its fixed axis on a moving curve is only a sensitivity reference.

With ``--given-speed`` the train speed is handed to the detector, which then merges frames
beyond ``accumulation.min_range`` (the multi-frame path; off without a speed).

``sustained_m`` (v0.6.2) is the largest distance from which the object is detected in >= 90 %
of the frames in which it returned a point, all the way in - the "reliable" range, next to
``first_detection_m``, the first confirmed hit. ``--place rail`` lays the object on the rail head
(the organizers' 30 x 30 x 10 cm criterion) instead of standing it on the bed.

For each sequence a fresh detector runs over the frames; a frame counts as a hit when a
confirmed gauge detection lies within ``max(2 m, 3 %)`` of the object's distance and 1.2 m
laterally. Reported: first confirmed detection distance per object, recall per range bin over
the frames in which the object returned >= 1 point, false confirmed gauge detections.

    python scripts/far_range_eval.py --cache /data/cache/new_data --files 46,47,48 --kinds person,box1.0 \\
        --start 220 --out out/far/person.json

Default ``legacy`` placement uses the frame's far-field detector axis and vault drift.
``anchored`` can be paired with it using the same seed, frame cache, speed and config.
``independent`` requires separately calibrated parameters, not detector outputs. Every mode
injects synthetic objects, not measured positive examples.
"""
from __future__ import annotations

import argparse
import hashlib
import glob
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np

BINS = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 250)]


def fixed_reference(center: float, yaw_deg: float, curvature: float, rail_z0: float,
                    rail_grade: float) -> dict:
    """Externally surveyed axis/rail in the *vehicle* frame; no cloud-derived parameters."""
    values = (center, yaw_deg, curvature, rail_z0, rail_grade)
    if not all(np.isfinite(values)):
        raise ValueError("reference values must be finite")
    return dict(type="fixed_physical", center_y0_m=float(center), yaw_deg=float(yaw_deg),
                curvature_per_m=float(curvature), rail_z0_m=float(rail_z0), rail_grade=float(rail_grade))


def independent_placement(kind, d, lateral, refl, reference, lateral_offset, yaw_deg, place):
    """Return (spec, track) without consulting any cloud, detector state or far-range fit.

    ``lateral`` is the nominal displacement from the reference; ``lateral_offset`` is an
    explicit perturbation. The same reference is serialized into every object's label.
    """
    from resense.synthetic import BED_DEPTH_DEFAULT, catalogue_spec
    from resense.track import TrackModel
    track = TrackModel(floor_coef=np.array([0.0, reference["rail_grade"],
                                             reference["rail_z0_m"]]),
                       floor_range=(0.0, 300.0), rail_offset=0.0,
                       center=reference["center_y0_m"], yaw=np.radians(reference["yaw_deg"]),
                       curvature=reference["curvature_per_m"])
    spec = catalogue_spec(kind, d, lateral + lateral_offset, yaw_deg=yaw_deg, reflectivity=refl)
    x = d + spec.size[0] / 2
    z = float(track.rail_z(x)) + (spec.base if spec.base is not None else
                                   (0.0 if place == "rail" else -BED_DEPTH_DEFAULT))
    spec = replace(spec, base_z=z, reference=dict(reference),
                   perturbation={"lateral_m": float(lateral_offset), "yaw_deg": float(yaw_deg),
                                 "nominal_lateral_m": float(lateral)})
    return spec, track


def legacy_placement(xyz, cfg, previous, kind, d, lateral, refl, place):
    """Historical frame-derived placement, including far vault correction and local bed."""
    from resense.synthetic import catalogue_spec, local_bed_z
    from resense.track import estimate_track
    tm = estimate_track(xyz, cfg, prev=previous)
    spec = catalogue_spec(kind, d, lateral, reflectivity=refl)
    x = d + spec.size[0] / 2
    if spec.base is None and place == "rail":
        zb = float(tm.rail_z(x)) + (float(vault_drift(xyz, tm)(x)) if x > 60.0 else 0.0)
        spec = replace(spec, base_z=zb)
    elif spec.base is None:
        zb = local_bed_z(xyz, tm, x, lateral)
        if zb is None:
            zb = float(tm.rail_z(x)) - 0.25 + float(vault_drift(xyz, tm)(x))
        spec = replace(spec, base_z=zb)
    return spec, tm


def placement_match(detection, d, spec, placement_track, detector_track, mode):
    """Independent matching compares vehicle-frame Y, never detector-relative GT lateral."""
    tol = max(2.0, 0.03 * d)
    if mode == "legacy":
        return abs(detection.distance - d) <= tol and abs(detection.lateral - spec.lateral) <= 1.2
    x = d + spec.size[0] / 2
    gt_y = float(placement_track.center_y(x)) + spec.lateral
    det_y = float(detector_track.center_y(detection.distance)) + detection.lateral
    return abs(detection.distance - d) <= tol and abs(det_y - gt_y) <= 1.2


def vault_drift(xyz, track, x0=40.0, x1=230.0, step=10.0):
    """Compatibility import for the height reference shared with ``resense inject``."""
    from resense.synthetic import vault_drift as estimate_drift
    return estimate_drift(xyz, track, x0=x0, x1=x1, step=step)


def near_anchor_placements(models, distances, lateral, length=0.0, min_rail_score=0.0):
    """Vehicle-frame object centres from a near-track anchor, independent of the far axis.

    Consecutive clear-frame near fits supply a small rigid transform. We fit its lateral
    translation and yaw on the shared 6-22 m track segment, then carry one physical point
    from the <=30 m reference through the recording. There is no pose claim across a large
    frame gap: such a sequence needs measured odometry or registration and is skipped.
    """
    if len(models) != len(distances) or not models:
        raise ValueError("models and distances must be non-empty and aligned")
    anchors = [i for i, (m, d) in enumerate(zip(models, distances))
               if 10.0 <= d <= 30.0 and m.rail_score >= min_rail_score]
    if not anchors:
        raise ValueError("no rail-supported track reference within 30 m")
    anchor = anchors[0]
    positions = [None] * len(models)
    x = distances[anchor] + length / 2.0
    positions[anchor] = np.array([x, float(models[anchor].center_y(x)) + lateral], dtype=float)
    xs = np.array([6.0, 10.0, 14.0, 18.0, 22.0])

    def transform(k):
        ds = float(distances[k] - distances[k + 1])
        if not 0.0 <= ds <= 5.0:
            raise ValueError(f"motion step {ds:.1f} m has no reliable near-track overlap")
        delta = models[k].center_y(xs + ds) - models[k + 1].center_y(xs)
        yaw, side = np.polyfit(xs, delta, 1)
        if abs(yaw) > 0.05 or np.max(np.abs(delta - (yaw * xs + side))) > 0.2:
            raise ValueError("near-track fits do not support a stable pose transform")
        c, s = np.cos(yaw), np.sin(yaw)
        return np.array([[c, -s], [s, c]]), np.array([ds, side])

    for k in range(anchor - 1, -1, -1):
        rot, shift = transform(k)
        positions[k] = rot @ positions[k + 1] + shift
    for k in range(anchor, len(models) - 1):
        rot, shift = transform(k)
        positions[k + 1] = rot.T @ (positions[k] - shift)
    return positions, anchor


def sustained_range(rows, frac: float = 0.9, min_frames: int = 5):
    """The largest distance D from which the object is detected in >= ``frac`` of the frames
    in which it returned a point, all the way in (d <= D); None if never."""
    vis = [r for r in rows if r["n"] > 0]
    best = None
    for r in vis:
        D = r["d"]
        sub = [x["hit"] for x in vis if x["d"] <= D]
        if len(sub) >= min_frames and np.mean(sub) >= frac:
            best = D if best is None else max(best, D)
    return best


def run_sequence(job):
    (files, stamps, speeds, kind, d0, lateral, refl, seed, cfg_dict, far_min_height, given_speed,
     place, mode, reference, lateral_offset, yaw_deg) = job
    sys.path.insert(0, os.getcwd())
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from resense.synthetic import catalogue_spec, inject_obstacles, place_on_bed
    from resense.track import estimate_track
    cfg = DetectorConfig.from_dict(cfg_dict)
    if far_min_height is not None:
        cfg.cluster.far_min_height = far_min_height
    det = Detector(cfg)
    d = d0
    prev_t = None
    path = []

    def skipped(reason):
        return {"kind": kind, "d0": d0, "lateral": lateral, "refl": refl, "first": None,
                "fp": 0, "rows": [], "file0": os.path.basename(files[0]),
                "placement_mode": mode, "skipped": reason}

    for f, spd in zip(files, speeds):
        stem = os.path.splitext(os.path.basename(f))[0]
        t = stamps.get(stem)
        if mode in ("anchored", "independent") and t is None:
            return skipped(f"missing timestamp for {stem}")
        if prev_t is not None and t is not None:
            dt = t - prev_t
            if mode in ("anchored", "independent") and not 0.0 < dt < 10.0:
                return skipped(f"invalid timestamp step {dt:.3f} s at {stem}")
            d -= spd * (dt if 0 < dt < 10 else 0.1)
        prev_t = t
        if d < 8.0:
            break
        path.append((f, t, spd, d))
    if not path:
        return skipped("object already passed")

    models = None
    positions = None
    anchor = None
    if mode == "anchored":
        models = []
        previous = None
        for f, t, _, _ in path:
            stem = os.path.splitext(os.path.basename(f))[0]
            fr = frame_from_compact(np.load(f), cfg.sensor, stamp=t or 0.0, frame_id=stem)
            previous = estimate_track(fr.xyz, cfg.track, prev=previous)
            models.append(previous)
        try:
            positions, anchor = near_anchor_placements(
                models, [row[3] for row in path], lateral,
                length=catalogue_spec(kind, d0, reflectivity=refl).size[0],
                min_rail_score=cfg.track.rails_min_score,
            )
        except ValueError as exc:
            return skipped(str(exc))
    rows = []
    fp = 0
    first = None
    for k, (f, t, spd, path_d) in enumerate(path):
        stem = os.path.splitext(os.path.basename(f))[0]
        fr = frame_from_compact(np.load(f), cfg.sensor, stamp=t or 0.0, frame_id=stem)
        if mode == "independent":
            spec, tm = independent_placement(kind, path_d, lateral, refl, reference, lateral_offset, yaw_deg, place)
        elif mode == "anchored":
            tm = models[k]
            spec = catalogue_spec(kind, path_d, lateral, reflectivity=refl)
            x, y = positions[k]
            spec = replace(spec, distance=float(x - spec.size[0] / 2),
                           lateral=float(y - tm.center_y(x)),
                           reference={"type": "near_rail_anchor", "frame": os.path.basename(path[anchor][0]),
                                      "rail_score": float(models[anchor].rail_score)})
            if spec.base is None and place == "rail":
                z = float(tm.rail_z(x)) + (float(vault_drift(fr.xyz, tm)(x)) if x > 60.0 else 0.0)
                spec = replace(spec, base_z=z)
            elif spec.base is None:
                spec = place_on_bed(fr, tm, [spec])[0]
        else:
            spec, tm = legacy_placement(fr.xyz, cfg.track, det.track, kind, path_d, lateral, refl, place)
        x = spec.distance + spec.size[0] / 2
        y = float(tm.center_y(x)) + spec.lateral
        render_rng = np.random.default_rng(np.random.SeedSequence([seed, k, 1]))
        inj = inject_obstacles(fr, tm, [spec], rng=render_rng,
                               dropout_start=60.0, dropout_full=200.0)
        n_pts = int(inj.n_added[0])
        res = det.process(inj.frame, ego_speed=spd if given_speed else None)

        hit = False
        fps = []
        for det_ in res.detections:
            if placement_match(det_, spec.distance, spec, tm, res.track, mode):
                hit = True
            else:
                fp += 1
                fps.append([round(det_.distance, 1), round(det_.lateral, 2), [round(float(v), 2) for v in det_.size], det_.kind])
        if hit and first is None:
            first = spec.distance
        rows.append({"frame": stem, "d": round(spec.distance, 1), "path_d": round(path_d, 1),
                     "gt": spec.to_dict(), "gt_vehicle_y_m": float(y),
                     "axis_error_m": round(float(spec.lateral - lateral), 2),
                     "n": n_pts, "hit": hit, "fp_dets": fps,
                     "cand": any(placement_match(c, spec.distance, spec, tm, res.track, mode)
                                 for c in res.candidates),
                     "mon": res.health.get("monitored_range"), "vis": res.health.get("visibility")})
    return {"kind": kind, "d0": d0, "lateral": lateral, "refl": refl, "first": first, "fp": fp, "rows": rows,
            "file0": os.path.basename(files[0]), "placement_mode": mode,
            "reference": reference if mode == "independent" else None,
            "perturbation": {"lateral_m": lateral_offset, "yaw_deg": yaw_deg} if mode == "independent" else None,
            "anchor_frame": os.path.basename(path[anchor][0]) if anchor is not None else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache/new_data")
    ap.add_argument("--files", required=True, help="comma-separated split-file numbers; each starts a sequence")
    ap.add_argument("--kinds", default="person")
    ap.add_argument("--start", type=float, default=220.0, help="object distance at the first frame (m)")
    ap.add_argument("--frames", type=int, default=110, help="max frames per sequence")
    ap.add_argument("--lateral", default="-0.6:0.6")
    ap.add_argument("--reflectivity", type=float, default=None,
                    help="fixed return intensity (0-255) for a paired material-sensitivity run")
    ap.add_argument("--speeds", default="docs/extended_dataset_intake.json")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--far-min-height", type=float, default=None, help="override cluster.far_min_height")
    ap.add_argument("--given-speed", action="store_true",
                    help="hand the ride's train speed to the detector (enables multi-frame accumulation)")
    ap.add_argument("--place", choices=("bed", "rail"), default="bed",
                    help="bed: standing on the bed measured under it (default); rail: lying on the rail head")
    ap.add_argument("--placement-mode", choices=("legacy", "anchored", "independent"), default="legacy",
                    help="legacy: frame-derived axis (default); anchored: near rail fit and motion; "
                         "independent: explicit fixed physical reference")
    ap.add_argument("--axis-center", type=float, help="independent: surveyed Y at X=0 (m, vehicle frame)")
    ap.add_argument("--axis-yaw-deg", type=float, help="independent: surveyed tangent yaw (degrees)")
    ap.add_argument("--axis-curvature", type=float, help="independent: surveyed curvature (1/m)")
    ap.add_argument("--rail-z0", type=float, help="independent: surveyed rail Z at X=0 (m)")
    ap.add_argument("--rail-grade", type=float, help="independent: surveyed rail slope (m/m)")
    ap.add_argument("--lateral-offset", type=float, default=0.0, help="independent: add to nominal lateral (m)")
    ap.add_argument("--yaw-perturb-deg", type=float, default=0.0, help="independent: object yaw (degrees)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    reference = None
    axis_args = (a.axis_center, a.axis_yaw_deg, a.axis_curvature, a.rail_z0, a.rail_grade)
    if a.placement_mode == "independent":
        if any(v is None for v in axis_args):
            ap.error("independent placement requires --axis-center, --axis-yaw-deg, --axis-curvature, --rail-z0 and --rail-grade")
        reference = fixed_reference(*axis_args)
    elif any(v is not None for v in axis_args) or a.lateral_offset or a.yaw_perturb_deg:
        ap.error("axis and perturbation options require --placement-mode independent")
    if a.reflectivity is not None and not (np.isfinite(a.reflectivity)
                                            and 0.0 <= a.reflectivity <= 255.0):
        ap.error("--reflectivity must be between 0 and 255")
    import yaml
    from resense.config import DetectorConfig
    from resense.io import _natural_key, load_cache_stamps
    from resense.synthetic import OBJECT_CATALOGUE
    with open(a.config, "rb") as fh:
        config_bytes = fh.read()
    raw = yaml.safe_load(config_bytes) or {}
    cfg_dict = raw.get("resense", raw)          # read once: every sequence runs the same parameters
    DetectorConfig.from_dict(cfg_dict)
    with open(a.speeds, "rb") as fh:
        speeds_bytes = fh.read()
    intake = json.loads(speeds_bytes)
    spd_file = {f["n"]: (f.get("speed_tracks") or 0.0) for f in intake["files"]}
    stamps = load_cache_stamps(a.cache)
    allf = sorted(glob.glob(os.path.join(a.cache, "*.npy")), key=_natural_key)
    lo, hi = (float(v) for v in a.lateral.split(":"))
    if not np.isfinite([lo, hi, a.lateral_offset, a.yaw_perturb_deg]).all() or lo > hi:
        ap.error("lateral range and perturbations must be finite; lateral lo must not exceed hi")
    rng = np.random.default_rng(a.seed)
    jobs = []
    for fn in [int(v) for v in a.files.split(",") if v]:
        start = next((i for i, f in enumerate(allf) if os.path.basename(f).startswith(f"new_data_{fn}_")), None)
        if start is None:
            ap.error(f"no cached frames for new_data_{fn} in {a.cache}")
        files = allf[start:start + a.frames]
        if not files:
            ap.error(f"no frames for new_data_{fn}")
        if a.placement_mode in ("independent", "anchored"):
            missing = [os.path.basename(f) for f in files if os.path.splitext(os.path.basename(f))[0] not in stamps]
            if missing:
                ap.error(f"{a.placement_mode} placement requires bag stamps for every frame (missing {missing[:3]})")
            missing_speeds = [f for f in files if int(os.path.basename(f).split("_")[2]) not in spd_file]
            if missing_speeds:
                ap.error(f"{a.placement_mode} placement requires speed rows for every split file: {missing_speeds[:3]}")
        speeds = [spd_file.get(int(os.path.basename(f).split("_")[2]), 0.0) for f in files]
        for kind in a.kinds.split(","):
            sampled_refl = float(rng.uniform(*OBJECT_CATALOGUE[kind].reflectivity))
            refl = a.reflectivity if a.reflectivity is not None else sampled_refl
            jobs.append((files, stamps, speeds, kind, a.start, float(rng.uniform(lo, hi)), refl,
                         int(rng.integers(1 << 30)), cfg_dict, a.far_min_height, a.given_speed, a.place,
                         a.placement_mode, reference, a.lateral_offset, a.yaw_perturb_deg))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        out = list(ex.map(run_sequence, jobs))
    # summary
    summ = {"per_kind": {}, "jobs": len(jobs), "placement_mode": a.placement_mode,
            "skipped": sum(bool(o.get("skipped")) for o in out), "wall_s": round(time.time() - t0, 1)}
    for kind in a.kinds.split(","):
        seqs = [o for o in out if o["kind"] == kind]
        attempted = [o for o in seqs if not o.get("skipped")]
        firsts = [o["first"] for o in attempted if o["first"] is not None]
        bins = {}
        for lo_b, hi_b in BINS:
            vis = [r for o in attempted for r in o["rows"] if lo_b <= r["d"] < hi_b and r["n"] > 0]
            bins[f"{lo_b}-{hi_b}"] = [sum(r["hit"] for r in vis), len(vis)]
        sus = [s for s in (sustained_range(o["rows"]) for o in attempted) if s is not None]
        summ["per_kind"][kind] = {"sequences": len(attempted), "skipped": len(seqs) - len(attempted),
                                  "detected": len(firsts),
                                  "sustained_m": sorted(round(v, 1) for v in sus),
                                  "sustained_median": round(float(np.median(sus)), 1) if sus else None,
                                  "first_detection_m": sorted(round(v, 1) for v in firsts),
                                  "first_detection_median": round(float(np.median(firsts)), 1) if firsts else None,
                                  "recall_by_bin": bins, "false_detections": sum(o["fp"] for o in attempted)}
    selected_files = [os.path.basename(f) for job in jobs for f in job[0]]
    selected_stamps = {os.path.splitext(f)[0]: stamps.get(os.path.splitext(f)[0]) for f in selected_files}
    report = {"schema": "setF-placement-v1", "source": "synthetic objects on real empty ride frames",
              "parameters": {"placement_mode": a.placement_mode, "reference": reference,
                             "perturbation": {"lateral_m": a.lateral_offset, "yaw_deg": a.yaw_perturb_deg},
                             "place": a.place, "seed": a.seed, "files": a.files, "frames": a.frames,
                             "kinds": a.kinds, "start_m": a.start, "lateral_range": a.lateral,
                             "given_speed": a.given_speed, "far_min_height": a.far_min_height,
                             "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                             "speeds_sha256": hashlib.sha256(speeds_bytes).hexdigest(),
                             "selected_stamps_sha256": hashlib.sha256(json.dumps(
                                 selected_stamps, sort_keys=True).encode()).hexdigest(),
                             "cache": os.path.abspath(a.cache),
                             "cache_files": selected_files},
              "summary": summ, "sequences": out}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
