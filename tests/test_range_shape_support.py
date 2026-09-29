"""Point-identity diagnostics for range/shape support; executable on the local set F cache."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))


# Exact stage support (XYZ, effective lateral, rail-relative height) from the
# baseline paired replay, person / split 47 / frame 0017 at 114.8 m. Duplicate
# background returns are immaterial to this isolated voxel/shape mechanism test.
RECORDED_PERSON = np.array([
    [114.75431824, -.60085768, .64693326, -.11489303, 1.50201403],
    [114.75626373, -.40057656, .64693934, .08539488, 1.50201373],
    [114.80732727, -.60113525, .40677175, -.11498547, 1.26167889],
    [114.73288727, -.40049496, .40650490, .08539482, 1.26165587],
    [114.70562744, -.40039980, .08008014, .08539475, .93532039],
    [114.76325226, -.60090446, -.09213912, -.11490861, .76291238],
    [114.77133179, -.40062913, -.09214491, .08539494, .76288014],
    [114.83311462, -.60127026, -.38281190, -.11503042, .47201077],
])
RECORDED_PERSON_CONTEXT = np.array([
    [111.84999847, -.77999997, -.37000000, -.30422973, .49459394],
    [107.79000092, -1.70999992, -.09000000, -1.24864775, .78789257],
    [115.97000122, -1.16999996, .08000000, -.67979777, .93109877],
    [115.06999969, -1.75999999, .08000000, -1.27293329, .93404675],
    [112.66999817, -1.73000002, .08000000, -1.25134141, .94190801],
])


def test_recorded_resolved_person_is_lost_when_joined_to_real_corridor_background():
    from resense.clustering import cluster_labels, find_clusters, voxelize
    from resense.config import ClusterConfig

    cfg = ClusterConfig()
    joined = np.concatenate((RECORDED_PERSON, RECORDED_PERSON_CONTEXT))
    vox, _ = voxelize(joined[:, :3], cfg)
    assert len(np.unique(cluster_labels(vox, cfg))) == 1
    strict = np.r_[np.ones(8, bool), [True, False, True, False, False]]
    full = find_clusters(joined[:, :3], np.full(len(joined), 30.), joined[:, 3], joined[:, 4], strict, cfg,
                         axis_valid=221, height_valid=95, keep_thin=True, weak_from=60)
    assert not full
    person = RECORDED_PERSON
    target = find_clusters(person[:, :3], np.full(8, 30.), person[:, 3], person[:, 4], np.ones(8, bool), cfg,
                           axis_valid=221, height_valid=95, keep_thin=True, weak_from=60)
    assert len(target) == 1 and target[0].zone == "gauge"
    assert not target[0].thin and not target[0].weak and target[0].n_gauge == 8
    assert np.ptp(joined[:, 0]) == pytest.approx(8.18, abs=1e-5)
    # Merely extending the 30 m split range would still fail the 3 m strict-length bar.
    assert np.ptp(joined[strict, 0]) == pytest.approx(4.12, abs=1e-5)


def test_saved_false_body_also_has_compact_resolved_strict_support():
    from test_far_structure import FAR_BODY, _describe

    false_target = _describe(FAR_BODY[:, :3], FAR_BODY[:, 3], FAR_BODY[:, 4])[0]
    assert false_target.zone == "gauge" and not false_target.reason
    assert false_target.n_gauge == false_target.n
    assert false_target.size[0] < 1.3 and false_target.size[2] > 1.9
    # A compact vertical strict body is shared with the measured positive above;
    # neither full-component rejection nor compact-body promotion is validated here.


def test_recorded_edge_cube_has_three_corridor_voxels_but_only_two_strict():
    from resense.clustering import cluster_labels, find_clusters, voxelize
    from resense.config import ClusterConfig

    # box0.3 / split 46 / frame 0034 at 78.1 m. No fabricated ring assignment.
    xyz = np.array([[78.02462769, .40853974, -1.32243955],
                    [78.10706329, .54529905, -1.32385087],
                    [78.10577393, .68161875, -1.32384717]])
    dy = np.array([.76846086, .90558899, 1.04190292])
    h = np.array([.19642078, .19582454, .19581549])
    cfg = ClusterConfig()
    vox, _ = voxelize(xyz, cfg)
    assert len(vox) == 3 and np.all(cluster_labels(vox, cfg) == 0)
    assert np.ptp(xyz[:, 2]) < .0015
    assert not find_clusters(xyz, np.full(3, 22.4), dy, h, np.array([True, True, False]), cfg,
                             axis_valid=205, height_valid=115, keep_thin=True, weak_from=60)


def support_record(params, targets):
    """Effective descriptor inputs, including strict/target/background separation.

    These are the actual stage masks, not a reconstruction from the rail reference.
    Preserve exact points so a rejected component can be inspected without ray-casting again.
    """
    b = params["b"]
    ids = params["frame_idx"][b.idx]
    target = np.isin(ids, targets)
    strict = params.get("in_gauge")
    strict = strict[b.idx] if strict is not None else np.ones(len(ids), bool)
    inv = params.get("inv")

    def part(mask):
        points = b.pts[mask]
        return {"points": len(points),
                "size": np.ptp(points, axis=0).astype(float).tolist() if len(points) else None,
                "voxels": int(np.unique(inv[b.idx[mask]]).size) if inv is not None else None}

    cfg = params["cfg"]
    low = params.get("low_cfg")
    def array(name, fallback=None):
        value = params.get(name)
        value = fallback if value is None else value
        return None if value is None else value[b.idx].tolist()

    descriptor = None
    if inv is not None:
        descriptor = {
            "cfg": asdict(cfg), "gauge": None if params.get("gauge") is None else asdict(params["gauge"]),
            "parameters": {k: params[k] for k in ("factor", "factor_range", "axis_valid", "height_valid",
                                                  "keep_thin", "weak_from") if k in params},
            "xyz": b.pts.tolist(), "frame_idx": ids.tolist(), "voxel_ids": array("inv"),
            "dy": array("dy"), "h": array("h"), "strict": strict.tolist(),
            "rail_strict": array("in_rail", params.get("in_gauge")),
            "dy_rail": array("dy_report", params["dy"]), "dy_alt": array("dy_alt"),
            "intensity": array("intensity"), "ring": array("ring"),
            "mask_meaning": "effective_corridor", "historical_points": int((ids < 0).sum()),
        }
    return {"strict_mask_source": "effective_corridor" if "in_gauge" in params else "low_stage_not_polygon",
            "descriptor_inputs": descriptor,
            "target": part(target), "strict": part(strict),
            "target_strict": part(target & strict), "background": part(~target),
            "background_strict": part(~target & strict),
            "xyz": b.pts.astype(float).tolist(), "frame_idx": ids.tolist(),
            "target_mask": target.tolist(), "strict_mask": strict.tolist(),
            "dy": params["dy"][b.idx].astype(float).tolist(),
            "h": params["h"][b.idx].astype(float).tolist(),
            "effective_low_limits": ({k: getattr(low, k) for k in
                                      ("min_points", "min_width", "max_width", "min_height", "max_length", "min_top")}
                                     if low is not None else None),
            "effective_corridor_limits": {k: getattr(cfg, k) for k in
                                          ("min_points", "min_points_far", "far_range", "min_height", "gauge_min_points")}}


def test_effective_masks_separate_target_background_and_history():
    from resense.clustering import _Blob
    from resense.config import ClusterConfig

    # An edge target and an old/background connection occupy the same component.
    # The supplied union/reference membership, not a newly inferred rail mask, wins.
    xyz = np.array([[80, .95, .2], [80, 1.0, .4], [84, 1.3, .2], [84, 1.3, .2]])
    params = dict(b=_Blob.of(xyz, np.arange(4), 3), frame_idx=np.array([10, 11, 12, -1]),
                  in_gauge=np.array([True, False, True, True]), inv=np.array([0, 1, 2, 2]),
                  dy=xyz[:, 1], h=xyz[:, 2], cfg=ClusterConfig())
    rec = support_record(params, np.array([10, 11]))
    assert rec["target"]["points"] == 2
    assert rec["target_strict"]["voxels"] == 1
    assert rec["background_strict"]["points"] == 2
    assert rec["background_strict"]["voxels"] == 1
    assert rec["strict"]["voxels"] == 2
    np.testing.assert_allclose(rec["target"]["size"], [0, .05, .2])


def test_two_occupied_voxels_do_not_reach_the_descriptor_even_with_duplicate_returns():
    from resense.clustering import cluster_labels, find_clusters, voxelize
    from resense.config import ClusterConfig

    xyz = np.repeat([[110., .6, -.9], [110., .8, -.9]], 20, axis=0)
    cfg = ClusterConfig()
    vox, _ = voxelize(xyz, cfg)
    assert len(vox) == 2
    assert np.all(cluster_labels(vox, cfg) == -1)
    assert not find_clusters(xyz, np.ones(len(xyz)), xyz[:, 1], np.full(len(xyz), .2),
                             np.ones(len(xyz), bool), cfg, keep_thin=True, weak_from=60)


@pytest.mark.parametrize("width,stage,accepted", [(.25, "low", True), (.25, "straddle", False),
                                               (.40, "straddle", True)])
def test_flat_top_support_uses_the_effective_low_or_straddle_width(width, stage, accepted):
    from dataclasses import replace
    from resense.clustering import find_clusters
    from resense.config import ClusterConfig, LowObjectConfig

    low = LowObjectConfig()
    if stage == "straddle":
        low = replace(low, min_width=low.straddle_min_width, max_length=low.straddle_max_length,
                      min_top=low.straddle_min_top)
    # A resolved short top surface, not a long rail sliver. The same support may be
    # admissible to the bed stage yet fail straddle's independent width requirement.
    xyz = np.column_stack((np.full(7, 20.), np.linspace(.5, .5 + width, 7), np.full(7, -1.28)))
    clusters = find_clusters(xyz, np.full(7, 30.), xyz[:, 1], np.full(7, .12),
                             np.ones(7, bool), ClusterConfig(), low=np.ones(7, bool), low_cfg=low)
    assert bool(clusters) is accepted
    if accepted:
        assert clusters[0].kind == "low" and clusters[0].zone == "gauge"


def diagnose(report_path, out_path, paired_report=None, tracking_ref=None, config_path=None):
    """Replay exact draws from a set F report and trace injected indices, never nearest points."""
    from unittest.mock import patch

    root = ROOT
    sys.path.insert(0, str(root / "scripts"))
    import far_range_eval as fre
    from trace_detector_stages import TraceDetector
    from resense import clustering, synthetic
    from resense.config import DetectorConfig
    from resense.io import load_cache_stamps, _natural_key

    tracking_source = None
    if tracking_ref:
        # Shared-tree tracking work may be between source/config edits. An explicit
        # immutable baseline isolates this geometry diagnostic without editing that work.
        import subprocess
        import types
        import resense.detector as detector_module

        source = subprocess.check_output(["git", "show", f"{tracking_ref}:resense/tracking.py"], cwd=root)
        module = types.ModuleType("range_shape_baseline_tracking")
        sys.modules[module.__name__] = module
        exec(compile(source, f"{tracking_ref}:resense/tracking.py", "exec"), module.__dict__)
        tracker_class = module.Tracker
        tracking_source = {"ref": tracking_ref, "sha256": hashlib.sha256(source).hexdigest()}
    else:
        import resense.detector as detector_module
        tracker_class = detector_module.Tracker

    prior = json.loads(Path(report_path).read_text(encoding="utf-8"))
    effective_config = DetectorConfig.from_yaml(str(config_path)) if config_path else DetectorConfig()
    params = prior["parameters"]
    if params["placement_mode"] != "legacy" or params["given_speed"] or params["far_min_height"] is not None:
        raise ValueError("this diagnostic reproduces the supplied legacy, no-speed, default-height stress only")
    cache = Path(params["cache"])
    files = sorted(map(str, cache.glob("*.npy")), key=_natural_key)
    stamps = load_cache_stamps(str(cache))
    intake_path = root / "docs/extended_dataset_intake.json"
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    if hashlib.sha256(intake_path.read_bytes()).hexdigest() != params["speeds_sha256"]:
        raise ValueError("speed metadata differs from the saved stress report")
    speeds = {f["n"]: f.get("speed_tracks") or 0.0 for f in intake["files"]}
    rng = np.random.default_rng(params["seed"])
    lo, hi = map(float, params["lateral_range"].split(":"))
    original_inject = synthetic.inject_obstacles
    plain_detector_class = detector_module.Detector
    current = {}
    traces = []

    def inject(frame, tm, specs, **kwargs):
        inj = original_inject(frame, tm, specs, **kwargs)
        spec = specs[0]
        x = spec.distance + spec.size[0] / 2
        base = spec.base_z if spec.base_z is not None else float(tm.rail_z(x)) + (
            spec.base if spec.base is not None else -0.15)
        current.update(ids=np.flatnonzero(inj.labels == 1),
                       placement_base=float(base - tm.rail_z(x)),
                       placement_top=float(base + spec.size[2] - tm.rail_z(x)))
        return inj

    class Observer(TraceDetector):
        def __init__(self, cfg):
            super().__init__(cfg)
            self.parity_detector = plain_detector_class(DetectorConfig.from_dict(cfg.to_dict()))

        def process(self, frame, ego_speed=None):
            result = self.process_target(frame, current["ids"], ego_speed)
            from scripts.analyze_quality_candidates import semantic
            plain = self.parity_detector.process(frame, ego_speed)
            if semantic(result.to_dict()) != semantic(plain.to_dict()):
                raise RuntimeError(f"instrumentation semantic mismatch: {frame.frame_id}")
            self.trace.update(frame=frame.frame_id, placement_base=current["placement_base"],
                              placement_top=current["placement_top"])
            for row, cluster in zip(self.trace["clusters"],
                                    [c for c in result.candidates if np.isin(c.points_idx, self.target_indices).any()]):
                row["ring_count"] = int(cluster.ring_count)
            traces.append(self.trace)
            return result

        @contextmanager
        def _observe_blobs(self):
            originals = {name: getattr(clustering, name) for name in ("_corridor_cluster", "_low_cluster")}
            with super()._observe_blobs():
                def wrap(name):
                    observed = getattr(clustering, name)
                    original = originals[name]
                    signature = inspect.signature(original)

                    def run(*args, **kwargs):
                        bound = signature.bind(*args, **kwargs).arguments
                        b = bound["b"]
                        target = np.isin(bound["frame_idx"][b.idx], self.target_indices)
                        result = observed(*args, **kwargs)
                        if target.any():
                            rec = self.trace["blobs"][-1]
                            rec["support"] = support_record(bound, self.target_indices)
                            # Oracle diagnostic only: remove known background from this component,
                            # preserving the original voxel membership and all effective thresholds.
                            # It is NOT an implementable target-selection or reclustering rule.
                            if name == "_corridor_cluster":
                                idx = b.idx[target]
                                subset = dict(bound, b=clustering._Blob.of(
                                    bound["b"].pts, np.flatnonzero(target),
                                    int(np.unique(bound["inv"][idx]).size)))
                                subset["b"].idx = idx
                                answer = original(**subset)
                                from trace_detector_stages import cluster_record
                                rec["oracle_target_only"] = (None if answer is None else
                                                             cluster_record(answer, self.target_indices))
                        return result
                    return run

                for name in originals:
                    setattr(clustering, name, wrap(name))
                yield

    output = []
    for number in map(int, params["files"].split(",")):
        start = next(i for i, f in enumerate(files) if Path(f).name.startswith(f"new_data_{number}_"))
        selected = fre.consecutive_files(files, start, params["frames"])
        for kind in params["kinds"].split(","):
            refl = float(rng.uniform(*synthetic.OBJECT_CATALOGUE[kind].reflectivity))
            if params.get("reflectivity") is not None:
                refl = params["reflectivity"]
            lat, seed = float(rng.uniform(lo, hi)), int(rng.integers(1 << 30))
            cfg = effective_config.to_dict()
            traces = []
            job = (selected, stamps, [speeds[int(Path(f).name.split("_")[2])] for f in selected],
                   kind, params["start_m"], lat, refl, seed, cfg, None, False,
                   params["place"], "legacy", None, 0.0, 0.0)
            with patch("resense.detector.Detector", Observer), patch.object(synthetic, "inject_obstacles", inject), \
                    patch.object(detector_module, "Tracker", tracker_class):
                result = fre.run_sequence(job)
            old = next(s for s in prior["sequences"] if s["kind"] == kind and s["file0"] == result["file0"])
            parity = result["rows"] == old["rows"]
            if not parity:
                raise RuntimeError(f"saved baseline row mismatch: {kind} {result['file0']}")
            paired_parity = None
            if paired_report:
                paired = json.loads(Path(paired_report).read_text(encoding="utf-8"))
                other = next(s for s in paired["sequences"] if s["kind"] == kind and s["file0"] == result["file0"])
                paired_parity = result["rows"] == other["rows"]
            output.append(dict(kind=kind, file0=result["file0"], first=result["first"],
                               sustained=fre.sustained_range(result["rows"]), paired_parity=paired_parity,
                               prior_parity=parity, rows=result["rows"], traces=traces))
            print(kind, result["file0"], "first", result["first"], "parity", parity, flush=True)
    record = {"schema": "range-shape-diagnostic-v2", "sequences": output,
              "input_sha256": {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest()
                               for p in (report_path, intake_path, root / "resense/clustering.py",
                                         root / "resense/config.py", root / "resense/tracking.py",
                                         root / "scripts/trace_detector_stages.py",
                                          Path(__file__))},
              "config": effective_config.to_dict(), "paired_report": str(paired_report) if paired_report else None,
              "config_input": None if config_path is None else {"path": str(config_path),
                                                               "sha256": hashlib.sha256(Path(config_path).read_bytes()).hexdigest()},
              "cache": str(cache), "cache_frames": len(files), "tracking_source": tracking_source,
              "instrumentation_semantic_mismatches": 0}
    Path(out_path).write_text(json.dumps(record), encoding="utf-8")
    summarize(output)


def summarize(output):
    if isinstance(output, dict):
        output = output["sequences"]
    for seq in output:
        counts = Counter()
        examples = {}
        print("\nDIAG", seq["kind"], seq["file0"], "frames", len(seq["rows"]),
              "range", [seq["rows"][0]["d"], seq["rows"][-1]["d"]],
              "first", seq["first"], "sustained", seq.get("sustained"), "paired", seq.get("paired_parity"))
        oracle_frames = []
        for row, tr in zip(seq["rows"], seq["traces"]):
            if row["n"]:
                counts["visible_frames"] += 1
                counts["no_corridor_target"] += tr["stages"]["corridor"]["points"] == 0
                counts["no_strict_corridor_target"] += tr["stages"]["corridor"]["strict_points"] == 0
                counts["placement_top_below_floor"] += tr.get("placement_top", tr.get("physical_top")) < 0.12
                counts["observed_top_below_floor"] += tr["geometry"]["height"][1] < 0.12
                counts["target_blob_frames"] += bool(tr["blobs"])
                counts["target_candidate_frames"] += bool(tr["clusters"])
            if row["hit"] or not row["n"]:
                continue
            if any(b["output"] is None and b.get("oracle_target_only") is not None
                   and b["oracle_target_only"]["zone"] == "gauge" for b in tr["blobs"]):
                oracle_frames.append([row["frame"], row["d"]])
            for b in tr["blobs"]:
                if b["output"] is None:
                    reason = next(r["function"] + ": " + r.get("condition", "") for r in reversed(b["returns"])
                                  if r["value"] is None)
                    counts[reason] += 1
                    if reason not in examples:
                        support = b.get("support", {})
                        examples[reason] = dict(frame=row["frame"], distance=row["d"],
                                                voxels=b["voxels"], strict=b.get("strict_voxels"), size=b["size"],
                                                target=support.get("target"), limits=support.get("effective_low_limits"),
                                                oracle=b.get("oracle_target_only"))
        print("COUNTS", json.dumps(dict(counts)))
        print("FIRST_EXAMPLES", json.dumps(examples))
        print("MISSED_REJECTED_BLOB_WITH_GAUGE_TARGET_ONLY", json.dumps(oracle_frames))


def show_frame(path, kind, file0, frame):
    record = json.loads(path.read_text(encoding="utf-8"))
    seq = next(s for s in record["sequences"] if s["kind"] == kind and s["file0"] == file0)
    row, trace = next((r, t) for r, t in zip(seq["rows"], seq["traces"]) if r["frame"] == frame)
    print(json.dumps({"row": row, "trace": trace}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    replay = sub.add_parser("replay")
    replay.add_argument("report", type=Path)
    replay.add_argument("out", type=Path)
    replay.add_argument("--paired-report", type=Path)
    replay.add_argument("--tracking-ref", help="explicit git revision for an isolated baseline tracker")
    replay.add_argument("--config", type=Path, help="explicit detector configuration (default: current defaults)")
    summary = sub.add_parser("summary")
    summary.add_argument("report", type=Path)
    frame = sub.add_parser("frame")
    frame.add_argument("report", type=Path)
    frame.add_argument("kind")
    frame.add_argument("file0")
    frame.add_argument("frame")
    args = parser.parse_args()
    if args.mode == "summary":
        summarize(json.loads(args.report.read_text(encoding="utf-8")))
    elif args.mode == "frame":
        show_frame(args.report, args.kind, args.file0, args.frame)
    else:
        diagnose(args.report, args.out, args.paired_report, args.tracking_ref, args.config)
