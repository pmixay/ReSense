"""Full existing regression harness on explicitly transformed N2 inputs.

This is a sensor sensitivity experiment, never a default-source freeze gate.
Keep every cache/seed/config/label and use one hook after Set F object insertion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def hashes(root, patterns):
    files = sorted({p for pattern in patterns for p in root.rglob(pattern)})
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in files
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--smoke", action="store_true",
                        help="explicitly allow incomplete gate membership for a harness smoke test")
    args = parser.parse_args()
    args.source, args.cache, args.out = (
        p.resolve() for p in (args.source, args.cache, args.out)
    )
    folder = Path(__file__).resolve().parent
    root = folder.parents[2]
    if not args.smoke:
        sys.path.insert(0, str(root))
        from scripts.cache_io import validate_extended_ride_cache, validate_ride_intake_manifest
        ride = str(args.cache / "new_data")
        validate_ride_intake_manifest(ride, validate_extended_ride_cache(ride))
    if args.out.exists():
        raise SystemExit("Use a new output directory; existing evidence is never overwritten")
    args.out.mkdir(parents=True)
    hook = args.out / "hook"
    shutil.copytree(folder / "proxy_hook", hook, ignore=shutil.ignore_patterns("__pycache__"))
    helper = hook / "lidar_input_variants.py"
    shutil.copy2(root / "scripts/lidar_input_variants.py", helper)
    receipt_dir = args.out / "input_receipts"
    env = dict(os.environ)
    env.update(
        PYTHONPATH=str(hook),
        RESENSE_N2_PROXY="1",
        RESENSE_N2_SOURCE=str(args.source),
        RESENSE_N2_HELPER=str(helper),
        RESENSE_N2_PROXY_RECEIPTS=str(receipt_dir),
        OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
        OPENBLAS_CORETYPE="Haswell",
    )
    command = [
        sys.executable, str(root / "scripts/regression_gate.py"),
        "--cache", str(args.cache), "--config", str(args.source / "configs/default.yaml"),
        "--jobs", "1", "--chunks", "8", "--nominal-stamps",
        "--work", str(args.out / "work"), "--out", str(args.out / "gate.json"),
    ]
    if args.baseline:
        command += ["--baseline", str(args.baseline.resolve()), "--changed-only"]
    before = hashes(args.source, ("*.py", "*.yaml", "*.so"))
    receipt = {
        "transformed_input_experiment_not_default_gate": True,
        "smoke_test_only": args.smoke,
        "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source": str(args.source), "source_hashes": before,
        "hook_hashes": hashes(hook, ("*.py",)),
        "harness_hashes": hashes(root / "scripts", ("regression_gate.py", "eval_real.py", "far_range_eval.py", "cache_io.py")),
        "command": command,
        "blas_coretype": "Haswell",
        "baseline_sha256": hashlib.sha256(args.baseline.read_bytes()).hexdigest() if args.baseline else None,
        "cache_provenance_hashes": {
            str(p.relative_to(args.cache)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [args.cache / "originals_receipt.json", args.cache / "set_o_receipt.json",
                      args.cache / "new_data/intake_manifest.json"] if p.exists()
        },
        "limitations": [
            "Nearest real Pandar return per approximate Falcon angular cell; not curved raster, noise, wavelength or denser ROI simulation.",
            "Cached inputs already have the original range crop; no unobserved near returns can be recovered.",
            "Original n_raw/n_near metadata retained; raw health statistics are not a complete simulated sensor.",
            "Set F uses the unchanged legacy placement protocol, which depends on the evaluated detector track; no identical-positive-geometry claim.",
            "Default-source hash equality does not establish default-input behavior: the external hook changes every processed frame.",
        ],
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    started = time.monotonic()
    with (args.out / "gate.log").open("w") as log:
        result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt.update(exit_code=result.returncode, wall_s=time.monotonic() - started,
                   source_unchanged=before == hashes(args.source, ("*.py", "*.yaml", "*.so")))
    totals = {"processed_source_frames": 0, "before_points": 0, "after_points": 0,
              "output_ring_frames": 0, "metadata_changed_frames": 0}
    by_worker = {}
    for path in sorted(receipt_dir.glob("frames_*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        by_worker[path.name] = {"frames": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        totals["processed_source_frames"] += len(rows)
        for row in rows:
            totals["before_points"] += row["before_points"]
            totals["after_points"] += row["after_points"]
            totals["output_ring_frames"] += row["output_has_ring"]
            totals["metadata_changed_frames"] += not row["metadata_preserved"]
    receipt.update(input_totals=totals, input_workers=by_worker,
                   activated_processes=[json.loads(p.read_text()) for p in sorted(receipt_dir.glob("activated_*.json"))])
    gate_path, set_f_path = args.out / "gate.json", args.out / "work/setF_straight.json"
    if gate_path.exists():
        gate = json.loads(gate_path.read_text())
        receipt["gate_sha256"] = hashlib.sha256(gate_path.read_bytes()).hexdigest()
        receipt["ride_present"] = gate.get("ride", {}).get("available", False)
        receipt["set_f_present"] = gate.get("set_F_straight", {}).get("available", False)
        receipt["expected_processed_source_frames"] = (
            sum(item["frames"] for item in gate["recordings"].values())
            + gate["set_O"]["frames"] + gate.get("ride", {}).get("frames", 0)
        )
    if set_f_path.exists():
        set_f = json.loads(set_f_path.read_text())
        receipt["set_f_sha256"] = hashlib.sha256(set_f_path.read_bytes()).hexdigest()
        receipt["set_f_hook_activated"] = any(
            any("far_range_eval.py" in str(arg) for arg in process["argv"])
            for process in receipt["activated_processes"]
        )
        receipt["set_f_sequences"] = len(set_f.get("sequences", []))
        receipt["expected_processed_source_frames"] += sum(
            len(sequence.get("rows", [])) for sequence in set_f["sequences"]
        )
    receipt["input_coverage_matches"] = (
        receipt.get("expected_processed_source_frames") == totals["processed_source_frames"]
    )
    if not args.smoke and result.returncode in (0, 1):
        if not (receipt.get("ride_present") and receipt.get("set_f_present")
                and receipt.get("set_f_hook_activated") and receipt["input_coverage_matches"]):
            receipt["coverage_error"] = "Full transformed-input coverage was not established, including the Set F child hook"
            (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            raise RuntimeError("Full transformed-input coverage was not established, including the Set F child hook")
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"exit_code": result.returncode, "input_totals": totals}), flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
