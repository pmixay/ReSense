"""Package only this review's own files; --verify is read-only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

P = Path(__file__).resolve().parent


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(p):
    return json.loads(p.read_text())


def write(p, v):
    p.write_bytes((json.dumps(v, indent=2) + "\n").encode())


if "--verify" in sys.argv:
    data = load(P / "HASHES.json")
    for r in data["files"]:
        b = (P / r["path"]).read_bytes()
        assert len(b) == r["bytes"] and sha(b) == r["sha256"], r["path"]
    print(f"Verified {len(data['files'])} own evidence files")
    raise SystemExit(0)

names = ["rs-h4-selected-independent-c9aea87-01", "rs-h4-selected-independent-c9aea87-02",
         "rs-h4-selected-independent-c9aea87-003", "rs-h4-selected-independent-c9aea87-004"]
runtime = []
for name in names:
    d = json.loads(subprocess.check_output(["docker", "inspect", name]))[0]
    assert d["Image"] == "sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19"
    assert not d["State"]["Running"] and not d["State"]["OOMKilled"]
    assert d["State"]["ExitCode"] == (1 if name in names[:2] else 0)
    runtime.append({k:d[k] for k in ("Id", "Name", "Image", "State", "Config", "Mounts", "HostConfig")})
write(P / "runtime.json", runtime)

selected = load(P / "run-003/selected-probes.json")
paired = load(P / "run-003/paired.json")
junit = ET.parse(P / "run-003/pytest.xml").getroot()
suites = list(junit.iter("testsuite"))
assert sum(int(s.get("tests")) for s in suites) == 306
assert all(int(s.get(k, "0")) == 0 for s in suites for k in ("failures", "errors", "skipped"))
write(P / "RESULTS.json", dict(
    reviewed_sha="c9aea87cb5322092070158cd8987115ee44833c9",
    baseline_sha="707ea9cda051369326fb9407c42488c1033dad76",
    verdict="ACCEPTED revised shipping difference; no supported NEW medium-or-higher finding",
    inherited_high_8_1="OPEN: tall in-envelope pole remains advisory; original H4 safety BLOCKED retained",
    experimental_H1="withdrawn from defaults; enabled-feature acceptance remains rejected",
    new_focused_units=306, paired_tracker_sequences=paired["tracker_sequences"],
    paired_tracker_updates_per_source=paired["tracker_frames"], paired_components=len(selected["gt_components"]),
    direct_h2_boundaries=len(selected["h2"]["angular_voxel"]), residual_controls=len(selected["h2"]["residual"]),
    axis_cases=len(selected["axis_health"]["boundaries"]) + selected["axis_health"]["isolated_negative_controls"],
    health_cases=len(selected["axis_health"]["health"]),
    full_detector_frames=sum(r["frames"] for r in selected["reachability"]["full_detector"]),
    unchanged_node_methods=len(selected["runtime"]["identical_methods"]),
    h2_route=load(P / "run-004/paired.json"),
    h3_completed_before_verdict=True, h3_recount="h3_audit.json", withdrawal_recount="withdrawal_audit.json"))

# Authenticate the selected gate's compact index as well as the already recounted
# external files. Its producer owns its bytes; this check performs no writes there.
h3 = P.parent / "h3_selected"
index = load(h3 / "HASHES.json")
for r in index["files"]:
    b = (h3 / r["path"]).read_bytes()
    assert len(b) == r["bytes"] and sha(b) == r["sha256"], r["path"]
write(P / "h3_package_audit.json", dict(index_sha256=sha((h3 / "HASHES.json").read_bytes()),
    authenticated_files=len(index["files"]), passed=True))

transforms = load(P / "PACKAGE_TRANSFORMS.json") if (P / "PACKAGE_TRANSFORMS.json").exists() else []
for p in P.rglob("*"):
    if p.is_file() and p.name != "HASHES.json":
        before = p.read_bytes()
        after = before.replace(b"\r\n", b"\n")
        if before != after:
            p.write_bytes(after)
            transforms.append(dict(path=p.relative_to(P).as_posix(), before_sha256=sha(before),
                                   after_sha256=sha(after), operation="CRLF to LF, reversible text normalization"))
write(P / "PACKAGE_TRANSFORMS.json", transforms)
files = []
for p in sorted(P.rglob("*")):
    if p.is_file() and p.name != "HASHES.json":
        b = p.read_bytes()
        files.append(dict(path=p.relative_to(P).as_posix(), bytes=len(b), sha256=sha(b)))
write(P / "HASHES.json", dict(files=files))
print(json.dumps(dict(packaged_files=len(files), h3_package_files=len(index["files"]),
                      verdict="ACCEPTED revised shipping scope; inherited High 8.1 OPEN")))
