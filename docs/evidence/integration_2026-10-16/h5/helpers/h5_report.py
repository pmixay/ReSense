#!/usr/bin/env python3
"""Authenticate version-only reviewed-core changes and compare every final/selected frame."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

from frame_diff import changes, normalize

ROOT = Path(__file__).resolve().parent.parent
COMMIT = "52115654417a660669b8dddfce447692c1d782cc"
SELECTED = "c9aea87cb5322092070158cd8987115ee44833c9"
REVIEW = "70072f1300d922d7542a6b45688084e7a426d7c7"
RUN = "candidate-52115654417a-20261016T110150Z-d9084fe4"
PREVIOUS = "candidate-c9aea87cb532-20261016T101302Z-8a9ae4d1"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    args = parser.parse_args()
    analysis = ROOT / ("analysis-" + RUN)
    current, previous = ROOT / RUN, ROOT / PREVIOUS
    scope = load(current / "source_after.json")["files"]
    old_scope = load(previous / "source_after.json")["files"]
    assert scope.keys() == old_scope.keys()
    changed_scope = [p for p in sorted(scope) if scope[p] != old_scope[p]]
    assert changed_scope == ["pyproject.toml", "resense/__init__.py"]

    def git(*argv):
        return subprocess.check_output(["git", *argv], cwd=args.parent)

    replacements = {
        "resense/__init__.py": (b'__version__ = "1.0.0"', b'__version__ = "1.1.0"'),
        "pyproject.toml": (b'version = "1.0.0"', b'version = "1.1.0"'),
        "ros2_ws/src/resense_ros/setup.py": (b'version="1.0.0"', b'version="1.1.0"'),
        "ros2_ws/src/resense_ros/package.xml": (b'<version>1.0.0</version>', b'<version>1.1.0</version>')}
    version_proof = {}
    for path, (old, new) in replacements.items():
        before = git("show", SELECTED + ":" + path)
        after = git("show", COMMIT + ":" + path)
        assert before.count(old) == 1 and before.replace(old, new, 1) == after, path
        version_proof[path] = dict(before_sha256=hashlib.sha256(before).hexdigest(), after_sha256=hashlib.sha256(after).hexdigest(), exact_single_version_replacement=True)
    paths = ["resense", "native", "configs", "setup.py", "pyproject.toml", "scripts/build_native.sh", "ros2_ws/src/resense_ros/config"]
    review_changes = git("diff", "--name-only", REVIEW, COMMIT, "--", *paths).decode().splitlines()
    assert review_changes == changed_scope
    patch = git("diff", "--no-color", "--no-ext-diff", "--unified=0", SELECTED, COMMIT, "--", *replacements)
    (analysis / "reviewed_selected_to_final_versions.patch").write_bytes(patch)
    counts = Counter(frames=0, changed_frames=0, changed_entries=0, setF_frames=0)
    differences = []
    for path in sorted((previous / "frames").glob("*.jsonl")):
        with path.open() as left, (current / "frames" / path.name).open() as right:
            for i, (x, y) in enumerate(itertools.zip_longest(left, right)):
                if x is None or y is None:
                    raise ValueError("selected/final frame counts differ")
                a, b = json.loads(x), json.loads(y)
                assert a["key"] == b["key"]
                da, db = {}, {}
                for rep in ("raw", "serialized"):
                    da[rep], _ = normalize(a[rep])
                    db[rep], _ = normalize(b[rep])
                delta = list(changes(da, db))
                counts["frames"] += 1
                counts["setF_frames"] += path.name.startswith("setF_")
                if delta:
                    counts["changed_frames"] += 1
                    counts["changed_entries"] += len(delta)
                    differences.append(dict(sequence_file=path.name, row=i, key=a["key"], changes=[dict(field=p, selected=v, final=w) for p, v, w in delta]))
    assert counts["frames"] == 18329 and counts["setF_frames"] == 3060
    assert load(current / "cache_identity.json") == load(previous / "cache_identity.json")
    assert load(current / "provenance.json")["native_sha256"] == load(previous / "provenance.json")["native_sha256"]
    assert load(current / "gate.json")["config"] == load(previous / "gate.json")["config"]
    explained = load(analysis / "explained_frames.json")
    versions = load(analysis / "final_versions_and_config.json")
    result = dict(measured_commit=COMMIT, independently_reviewed_selected_commit=SELECTED, independent_review_commit=REVIEW,
        gate_exit=load(current / "completion.json")["gate_exit"], source_sha256=load(current / "source_after.json")["source_sha256"],
        changed_frozen_files_from_reviewed_selection=changed_scope, version_only_proof=version_proof,
        numerical_core_bytes_identical_to_reviewed_scope=True, all_versions_1_1_0=versions["all_versions_1_1_0"],
        selected_to_final_frame_comparison=dict(counts), selected_to_final_differences=differences,
        final_vs_sealed_axis_and_metadata_only=not explained["other_or_unexplained_changes"] and not any(explained["changed_frames_by_explicit_result_group"].values()),
        current_spared_true=explained["added_cluster_flags"]["spared"].get("true", 0),
        metrics_summaries=load(analysis / "evaluation_and_config.json")["metrics_summaries"],
        config_unchanged_from_reviewed_selection=True, source_files=scope,
        seal_protocol="Commit this passing gate evidence first; then create the new manifest from a clean Linux checkout of a commit containing this exact evidence and identical measured frozen bytes. Explicit 29 September shell-off baseline and explicit new manifest path. No G3 cases.")
    write(analysis / "H5_RESULT.json", result)
    print(json.dumps({k: result[k] for k in ("measured_commit", "gate_exit", "source_sha256", "changed_frozen_files_from_reviewed_selection", "numerical_core_bytes_identical_to_reviewed_scope", "all_versions_1_1_0", "selected_to_final_frame_comparison", "final_vs_sealed_axis_and_metadata_only", "config_unchanged_from_reviewed_selection")}, indent=2))


if __name__ == "__main__":
    main()
