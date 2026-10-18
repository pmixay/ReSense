#!/usr/bin/env python3
"""Extract only indexed committed 1.1.0 captures and reproduce all C2 screens."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.score_overclaim import EMPTY_FRAMES, read_results, reconstructed_judge_score  # noqa: E402
from resense.metrics import load_gt  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True, help="scratch directory outside the repository")
    args = parser.parse_args()
    args.inputs.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "docs/evidence/p4_eval_1.1.0_2026-10-16/raw/p4_raw_2026-10-16.tar.xz"
    output = Path(__file__).resolve().parent
    members = {"cloud_with_fake_obj":
               "p4out/battery_1.1.0_linux_haswell.raw/cloud_with_fake_obj/nominal/probe.jsonl",
               "cloud_with_fake_obj_control":
               "p4out/battery_707ea9c_linux_haswell.raw/cloud_with_fake_obj/nominal/probe.jsonl"}
    members.update({name: f"j1/prerelease_1.1.0/{name}.jsonl" for name in EMPTY_FRAMES})
    paths, sources = {}, {}
    with tarfile.open(archive) as source:
        for name, member in members.items():
            # Never extract archive paths; write only the named, fixed capture files.
            raw = source.extractfile(member).read()
            paths[name] = args.inputs / f"{name}.jsonl"
            paths[name].write_bytes(raw)
            sources[name] = {"member": member, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    commands, statuses = {}, {}
    for name, extra in {"baseline": [], "advisory_candidate": ["--apply-advisory-cap"],
                        "small_candidate": ["--apply-advisory-cap", "--cap-small-target"],
                        "approved_conservative": ["--apply-advisory-cap", "--cap-small-target",
                                                  "--acceptance-profile", "conservative_2026_10_17"]}.items():
        command = [sys.executable, str(ROOT / "scripts/score_overclaim.py"),
                   str(paths["cloud_with_fake_obj"]), "--sensor-model", "pandar128", "--require-c2",
                   "--out", str(output / f"{name}.json"), *extra]
        if extra:
            command.extend(["--write-candidate", str(args.inputs / f"{name}.jsonl")])
        for bag in EMPTY_FRAMES:
            command.extend(["--empty", f"{bag}={paths[bag]}"])
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        commands[name], statuses[name] = command, run.returncode
        if run.returncode not in (0, 1):
            raise RuntimeError(run.stderr)
        report = json.loads(run.stdout)
        print(name, report["numerical_screen"], report["set_O"]["after"]["totals"]["target_by_decision"])
    (output / "reproduction.json").write_text(json.dumps({
        "archive": str(archive.relative_to(ROOT)), "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "members": sources, "commands": commands, "exit_codes": statuses,
        "scope": "saved raw results from sealed 1.1.0; deterministic policy projection, not a new detector gate",
    }, indent=2) + "\n")
    gt = load_gt(ROOT / "labels/cloud_with_fake_obj.json")
    (output / "historical_reconstruction.json").write_text(json.dumps({
        "v1.0.0_707ea9c": reconstructed_judge_score(read_results(paths["cloud_with_fake_obj_control"]), gt),
        "v1.1.0": reconstructed_judge_score(read_results(paths["cloud_with_fake_obj"]), gt),
        "c2_advisory_candidate": reconstructed_judge_score(read_results(args.inputs / "advisory_candidate.jsonl"), gt),
        "c2_small_candidate": reconstructed_judge_score(read_results(args.inputs / "small_candidate.jsonl"), gt),
        "warning": "compatible reconstruction; original 13.10 scorer was not available",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
