"""Observe unchanged detector routes for visually identified static Falcon supports."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=600)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    folder = Path(__file__).resolve().parent
    sys.path[:0] = [str(args.source), str(args.source / "ros2_ws/src/resense_ros")]
    os.environ["RESENSE_REPO"] = str(args.source)
    import numpy as np

    from resense.frame import Frame

    judge = load("n2_static_judge", args.source / "docs/evidence/judgement_2026-10-13/scripts/judge_runner.py")
    trace = load("n2_static_trace", root / "scripts/trace_detector_stages.py")
    rep = judge.NodeReplica(config=str(args.source / "configs/default.yaml"))
    rep.detector = trace.TraceDetector(rep.cfg)
    cache = Path("/home/resense/data/decoded/falcon_test_second_dark")
    metadata = json.loads((cache / "meta.json").read_text())
    selected = {0, 1, 10, 100, *range(150, 163), *range(190, 196), 300, 500, 599}
    targets = {"support105": ([105.35, 1.4, -6.7], [105.9, 2.1, -3.4]),
               "support115": ([114.8, 1.4, -7.2], [115.5, 2.15, -4.0])}
    inventory, observed = [], []
    for index, meta in enumerate(metadata[:args.limit]):
        with np.load(cache / f"f_{index:05d}.npz") as data:
            raw, intensity = data["xyz"], data["inten"]
        groups = {name: np.flatnonzero(np.all((raw >= lo) & (raw <= hi), axis=1))
                  for name, (lo, hi) in targets.items()}
        rep.continuity(meta["topic"], meta["frame_id"], meta["stamp"], index)
        frame = Frame(xyz=raw @ rep.R_vs.T, intensity=intensity, ring=None, stamp=meta["stamp"],
                      frame_id=meta["frame_id"], meta={"n_raw": meta["n_raw"], "n_near": meta["n_near"]})
        # TraceDetector instrumentation only surrounds explicitly selected frames.
        if index in selected:
            result = rep.detector.process_target(frame, groups)
            observed.append({"frame": index, "decision": judge.node_decision(result), "trace": rep.detector.trace,
                             "dets": [judge.det_dict(item) for item in result.detections],
                             "warns": [judge.det_dict(item) for item in result.warnings]})
        else:
            # Base implementation: diagnostic subclass hooks need initialized trace state.
            result = rep.detector.process_target(frame, {})
        row = {"frame": index, "decision": judge.node_decision(result), "mount": result.mount,
               "axis_105_115": [float(result.track.center_y(x)) for x in (105.6, 115.2)],
               "targets": {name: {"points": len(ids), "raw_median": np.median(raw[ids], axis=0).tolist()
                           if len(ids) else None} for name, ids in groups.items()},
               "dets": [judge.det_dict(item) for item in result.detections],
               "warns": [judge.det_dict(item) for item in result.warnings]}
        inventory.append(row)
        if index % 100 == 0:
            print(index, flush=True)
    (folder / "static_trace.json").write_text(json.dumps({"source": str(args.source),
        "target_selection": "Raw ROS FLU boxes around repeated left-side vertical structures seen in independent point plots; detector outputs do not define these boxes.",
        "raw_boxes": targets, "selected": observed}, indent=2) + "\n")
    (folder / "static_inventory.jsonl").write_text("".join(json.dumps(row) + "\n" for row in inventory))


if __name__ == "__main__":
    main()
