#!/usr/bin/env python3
"""Verify full observer coverage against the gate's retained standard outputs."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify(run):
    errors, coverage = [], {}
    standard_paths = list((run / "gate_work").glob("*.jsonl"))
    if len(standard_paths) != 15:
        errors.append("full gate must retain six recordings + Set O + eight ride pieces")
    for p in sorted((run / "gate_work").glob("*.jsonl")):
        capture = run / "frames" / p.name
        count = 0
        with p.open(encoding="utf-8") as standard, capture.open(encoding="utf-8") as expanded:
            for i, (a, b) in enumerate(itertools.zip_longest(standard, expanded)):
                if a is None or b is None:
                    errors.append(f"frame count mismatch {p.name}:{i}")
                    break
                a, b = json.loads(a), json.loads(b)
                if a.pop("frame_id") != b["key"]["frame_id"]:
                    errors.append(f"frame identity mismatch {p.name}:{i}")
                a.pop("frame")
                if a != b["serialized"]:
                    errors.append(f"observer serialization mismatch {p.name}:{i}")
                count += 1
        coverage[p.name] = count
    sf = json.loads((run / "gate_work/setF_straight.json").read_text())
    sequences = {}
    for p in sorted((run / "frames").glob("setF_*.jsonl")):
        rows = [json.loads(s) for s in p.read_text().splitlines()]
        s = rows[0]["key"]["sequence"]
        key = (s["file0"], s["kind"], s["lateral"], s["reflectivity"])
        if key in sequences:
            errors.append("duplicate Set F sequence identity")
        sequences[key] = rows
        coverage[p.name] = len(rows)
    sf_rows = 0
    for s in sf["sequences"]:
        key = (s["file0"], s["kind"], s["lateral"], s["refl"])
        rows = sequences.pop(key)
        if len(rows) != len(s["rows"]):
            errors.append("Set F sequence length mismatch")
        for i, (a, b) in enumerate(zip(s["rows"], rows)):
            if a["frame"] != b["key"]["frame_id"] or b["key"]["index"] != i:
                errors.append("Set F frame identity mismatch")
            if a["mon"] != b["serialized"]["health"]["monitored_range"] or a["vis"] != b["serialized"]["health"]["visibility"]:
                errors.append("Set F health snapshot mismatch")
        sf_rows += len(rows)
    if sequences or sf_rows != 3060:
        errors.append("incomplete Set F inventory")
    done = json.loads((run / "completion.json").read_text())
    if coverage != done["frame_counts"]:
        errors.append("completion frame inventory mismatch")
    before = json.loads((run / "source_before.json").read_text())
    after = json.loads((run / "source_after.json").read_text())
    if before["files"] != after["files"] or before["head"] != done["commit"] or after["head"] != done["commit"]:
        errors.append("source/HEAD changed during evaluation")
    if before["git_status"] or after["git_status"] or before["crlf_files"] or before["windows_pyd"]:
        errors.append("checkout was not clean LF Linux source")
    if before["files"]["configs/default.yaml"] != before["files"]["ros2_ws/src/resense_ros/config/detector.yaml"]:
        errors.append("canonical and ROS configs differ")
    helpers = Path(__file__).resolve().parent
    snapshot = run / "helper_snapshot"
    snapshot.mkdir(exist_ok=True)
    for relative in ("run_linux_gate.py", "launch_gate.py", "hooks/sitecustomize.py", "verify_run.py", "frame_diff.py", "gate_control.py", "test_frame_diff.py"):
        target = snapshot / relative
        target.parent.mkdir(exist_ok=True, parents=True)
        shutil.copyfile(helpers / relative, target)
    (run / "observer.json").write_text(json.dumps(dict(sha256=sha(snapshot / "hooks/sitecustomize.py"),
        description="External completed-process observer, source snapshot retained; original result returned unmodified."), indent=2) + "\n")
    try:
        import yaml
        config = yaml.safe_load((run / "gate_work/config.yaml").read_text())
        (run / "gate_work/config.yaml.json").write_text(json.dumps(config, indent=2) + "\n")
    except ImportError:
        raise RuntimeError("run verification in the pinned Linux container (PyYAML required)")
    repo = Path("/evalworkspace") / run.name
    relevant = [*sorted((repo / "scripts").glob("*.py")), *sorted((repo / "labels").glob("*.json")),
                repo / "docs/extended_dataset_intake.json"]
    evaluation = {}
    for p in relevant:
        relative = p.relative_to(repo).as_posix()
        digest = sha(p)
        blob = subprocess.check_output(["git", "show", f"{done['commit']}:{relative}"], cwd=repo)
        if hashlib.sha256(blob).hexdigest() != digest:
            errors.append("evaluation file differs from measured commit: " + relative)
        evaluation[relative] = digest
    (run / "evaluation_source.json").write_text(json.dumps(evaluation, indent=2, sort_keys=True) + "\n")
    gate = json.loads((run / "gate.json").read_text())
    if gate["native"]["path"] != "native" or gate["config"]["set"] or gate["gate"]["allow"]:
        errors.append("gate did not use native/default config/no waivers")
    if gate["config"]["file_sha256"] != before["files"]["configs/default.yaml"]:
        errors.append("gate config hash differs from measured source")
    if gate["code"]["uncommitted_detector_changes"] != [] or gate["code"]["commit"] != done["commit"]:
        errors.append("gate did not report exact clean measured commit")
    expected_normal = sum(s["frames"] for s in gate["recordings"].values()) + gate["ride"]["frames"] + gate["set_O"]["frames"]
    if sum(coverage.values()) != expected_normal + sf_rows:
        errors.append("frame totals disagree with full gate results")
    result = dict(passed=not errors, errors=errors, frame_counts=coverage,
                  total_frames=sum(coverage.values()), set_f_rows=sf_rows,
                  standard_jsonl_files=len(standard_paths))
    (run / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    artifacts = [dict(path=p.relative_to(run).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
                 for p in sorted(run.rglob("*")) if p.is_file() and p.name != "artifact_inventory.json"]
    (run / "artifact_inventory.json").write_text(json.dumps(artifacts, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    raise SystemExit(verify(parser.parse_args().run))
