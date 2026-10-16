"""Verify retained author evidence and restoration; does not turn a rejection into PASS."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
ROOT = P.parents[4]
S = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-h4-columns-author-20261016")


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def save(name, data):
    p = P / name
    assert not p.exists(), p
    p.write_text(json.dumps(data, indent=2) + "\n")


manifest = json.loads((P / "EXTERNAL_ARTIFACTS.json").read_text())
for item in manifest["files"]:
    path = S / item["path"]
    assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], path
parent = json.loads((S / "parent-critical/results/identity.json").read_text())
files = {p: hashlib.sha256(subprocess.check_output(["git", "show", "HEAD:" + p], cwd=ROOT)).hexdigest()
         for p in parent["files"]}
assert files == parent["files"]
digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
assert digest == "c90f76cc485f6c479e64de23236785cc22cfcb5af5a282d514304f95a402ca51"
owned = ["resense/clustering.py", "resense/config.py", "configs/default.yaml",
         "ros2_ws/src/resense_ros/config/detector.yaml", "tests/test_column_free_top.py"]
subprocess.run(["git", "diff", "--exit-code", "--", *owned], cwd=ROOT, check=True)
for p in P.glob("*.py"):
    ast.parse(p.read_text(), filename=str(p))
ast.parse((ROOT / "tests/test_h4_column_evidence.py").read_text())
candidate = json.loads((P / "rejected_attempt_08_identity.json").read_text())
reconstructed = json.loads((S / "retained-08-reconstruction/results/identity.json").read_text())
assert candidate["files"] == reconstructed["files"] and candidate["config"] == reconstructed["config"]
assert candidate["native"] == reconstructed["native"]
assert json.loads((S / "retained-08-reconstruction/completion.json").read_text())["ok"]
restored = json.loads((S / "restored-dark/results/identity.json").read_text())
assert restored["files"] == files
assert json.loads((S / "restored-dark/completion.json").read_text())["ok"]
restored_comparison = json.loads((P / "restored-dark-comparison.json").read_text())
for piece, excess in [("ride_1", 9), ("ride_3", 5)]:
    row = restored_comparison["pieces"][piece]
    assert len(row["extra_stop_frames"]) == excess and not row["lost_stop_frames"]
    for witness in row["witnesses"]:
        assert all(pair["exact_warning_matches"] for pair in witness["pairs"])
dark_centers = {}
reference = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-h4-safety-20261016\run-001\replay-sealed-all")
for piece in ["ride_1", "ride_3"]:
    lost, added, n = [], [], 0
    with (reference / (piece + ".jsonl")).open() as rf, \
            (S / "attempt-08-dark/results" / (piece + ".jsonl")).open() as cf:
        for r, c in zip(map(json.loads, rf), map(json.loads, cf), strict=True):
            assert r["frame_id"] == c["frame_id"] and r["input"] == c["input"]
            rs = {tuple(d["center"]) for d in r["serialized"]["detections"]}
            cs = {tuple(d["center"]) for d in c["serialized"]["detections"]}
            lost.extend(dict(frame=r["frame_id"], center=x) for x in sorted(rs - cs))
            added.extend(dict(frame=r["frame_id"], center=x) for x in sorted(cs - rs))
            n += 1
    dark_centers[piece] = dict(frames=n, lost_exact_detection_centers=lost, new_exact_detection_centers=added)
save("DARK_CENTER_COMPARISON.json", dark_centers)
probe = json.loads((P / "probe_comparison.json").read_text())
delta = probe["pole_c"]["comparisons"]["attempt-08-probes"]
assert len(delta["lost_matched_stop_frames"]) == 18 and not delta["new_matched_stop_frames"]
extra_files, states = [], {}
for name in ["retained-08-reconstruction", "restored-dark"]:
    run = S / name
    for p in sorted(run.rglob("*")):
        if p.is_file():
            extra_files.append(dict(path=str(p.relative_to(S)), bytes=p.stat().st_size, sha256=sha(p)))
    states[name] = json.loads(subprocess.check_output(
        ["docker", "inspect", "rs-h4-columns-" + name, "--format", "{{json .State}}"], text=True))
    assert states[name]["ExitCode"] == 0 and not states[name]["OOMKilled"]
save("EXTERNAL_ARTIFACTS_ADDENDUM.json", dict(root=str(S), files=extra_files, runtime=states))
save("VERIFICATION.json", dict(artifact_integrity="PASS", author_acceptance="BLOCKED",
                              accepted_column_fix=False, runtime_restored=True,
                              git_head_before_evidence_commit=subprocess.check_output(
                                  ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                              restored_source_sha256=digest,
                              rejected_source_sha256=candidate["source_sha256"],
                              exact_reconstruction=True,
                              zero_dark_detection_center_differences=all(not r["lost_exact_detection_centers"]
                                  and not r["new_exact_detection_centers"] for r in dark_centers.values()),
                              new_portable_tests_remain_red_on_restored_runtime=True,
                              lost_A_axis_frames=[r["parent"]["k"] for r in delta["lost_matched_stop_frames"]]))
hashes = {str(p.relative_to(P)): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
          for p in sorted(P.rglob("*"))
          if p.is_file() and "__pycache__" not in p.parts and p.name != "HASHES.json"}
save("HASHES.json", hashes)
print(json.dumps(dict(artifact_integrity="PASS", author_acceptance="BLOCKED",
                     restored_source_sha256=digest, rejected_source_sha256=candidate["source_sha256"]), indent=2))
