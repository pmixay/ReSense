"""Package/verify already completed registered withdrawal runs; never launch a detector.

Run once to retain evidence, then use --verify for read-only integrity checks.
External artifacts use raw SHA-256; Git-retained text uses LF-normalized SHA-256.
"""
import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

P = Path(__file__).resolve().parent
ROOT = P.parents[5]
TEMP = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode")
EXTERNAL = TEMP / "resense-h4-column-withdrawal-20261016"
REFERENCE = TEMP / "resense-integration-h4-safety-20261016/run-001/replay-sealed-all"
PARENT_PROBES = TEMP / "resense-h4-columns-author-20261016/parent-critical"
DATA = TEMP / "resense-p3-data"
HEAD = "c9aea87cb5322092070158cd8987115ee44833c9"
SEALED = "707ea9cda051369326fb9407c42488c1033dad76"
IMAGE = "sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19"
NATIVE = "b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534"
RUNS = {
    "red-fc89ad2": ("fc89ad2", False),
    "green-795a243": ("795a243", False),
    "tests-c9aea87-20261016a": (HEAD, True),
    "probes-c9aea87-20261016a": (HEAD, True),
    "dark-c9aea87-20261016a": (HEAD, True),
    "experimental-c9aea87-20261016a": (HEAD, True),
    "probes-sealed-707ea9c-20261016a": (SEALED, True),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_id(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())


def load(path):
    return json.loads(path.read_bytes())


def encoded(data):
    return (json.dumps(data, indent=2, allow_nan=True) + "\n").encode()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def inspect(name):
    return json.loads(subprocess.check_output(["docker", "inspect", name]))[0]


def test_summary(run):
    groups = defaultdict(Counter)
    cases = []
    for case in ET.parse(run / "results/pytest.xml").iter("testcase"):
        outcome = next((k for k in ("failure", "error", "skipped") if case.find(k) is not None), "passed")
        groups[case.attrib["classname"]][outcome] += 1
        cases.append(dict(test=case.attrib, outcome=outcome))
    total = sum(groups.values(), Counter())
    log = (run / "worker.txt").read_text()
    deselected = re.findall(r"^  (tests/.* \(no .*\))$", log, flags=re.MULTILINE)
    return dict(totals={k: total[k] for k in ("passed", "failure", "error", "skipped")},
                deselected=len(deselected), deselected_tests=deselected,
                groups={k: dict(v) for k, v in groups.items()}, cases=cases)


def derive():
    """Validate frozen runs and derive exact comparisons, entirely offline."""
    pending, identities, runtime, external_files = {}, {}, {}, []
    for name, (revision, ok) in RUNS.items():
        run = EXTERNAL / name
        identity = load(run / "results/identity.json")
        full_head = git("rev-parse", revision).decode().strip()
        assert identity["head"] == full_head and identity["clean_git"]
        assert identity["imported"] == "/source/repo/resense/__init__.py"
        expected_files = {p: sha(git("show", full_head + ":" + p)) for p in identity["files"]}
        assert expected_files == identity["files"]
        assert sha(canonical(expected_files)) == identity["source_sha256"]
        assert sha(json.dumps(identity["config"], sort_keys=True).encode()) == identity["config_sha256"]
        assert list(identity["native"].values()) == [NATIVE]
        for filename, digest in identity["adapter_files"].items():
            assert sha((run / "author-code" / filename).read_bytes()) == digest
        for filename, digest in identity["reviewer_sources"].items():
            source = git("show", "838dd32:docs/evidence/integration_2026-10-16/h4_safety/" + filename)
            assert sha(source) == digest
        completion = load(run / "completion.json")
        assert completion["ok"] is ok
        launch = load(run / "launch.json")
        assert launch["returncode"] == 0
        argv = launch["argv"]
        state = inspect(argv[argv.index("--name") + 1])
        assert state["Image"] == IMAGE and state["State"]["Status"] == "exited"
        assert state["State"]["ExitCode"] == (0 if ok else 1)
        assert not state["State"]["OOMKilled"] and not state["State"]["Error"]
        for mount in state["Mounts"]:
            if mount["Destination"] in ("/data/cache", "/data/decoded", "/data/odometry", "/review", "/author", "/reference", "/source.git"):
                assert mount["RW"] is False
        assert "RESENSE_NATIVE=1" in state["Config"]["Env"]
        assert "RESENSE_REQUIRE_SYNTHETIC=1" in state["Config"]["Env"]
        runtime[name] = dict(id=state["Id"], image=state["Image"], state=state["State"],
                             command=state["Config"]["Cmd"], environment=state["Config"]["Env"],
                             mounts=state["Mounts"], network=state["HostConfig"]["NetworkMode"])
        assert runtime[name]["network"] == "none"
        identities[name] = identity
        for path in sorted(run.rglob("*")):
            if path.is_file():
                external_files.append(file_id(path))
                if path.suffix != ".jsonl":
                    pending["runs/" + name + "/" + path.relative_to(run).as_posix()] = path.read_bytes()
    candidate = identities["tests-c9aea87-20261016a"]
    for name, identity in identities.items():
        if identity["head"] == HEAD:
            assert identity["files"] == candidate["files"]
            assert identity["config"] == candidate["config"]
            assert identity["adapter_files"] == candidate["adapter_files"]
    assert candidate["config"]["cluster"]["column_free_max_top"] == 0.0
    assert candidate["files"]["configs/default.yaml"] == candidate["files"]["ros2_ws/src/resense_ros/config/detector.yaml"]
    assert load(REFERENCE / "identity.json")["head"] == SEALED
    assert load(REFERENCE / "completion.json")["ok"] is True
    for filename in ("identity.json", "completion.json"):
        path = REFERENCE / filename
        external_files.append(file_id(path))
        pending["reference/" + filename] = path.read_bytes()

    units = {name: test_summary(EXTERNAL / name) for name in ("red-fc89ad2", "green-795a243", "tests-c9aea87-20261016a")}
    assert units["red-fc89ad2"]["totals"] == dict(passed=0, failure=11, error=0, skipped=0)
    assert units["green-795a243"]["totals"] == dict(passed=259, failure=1, error=0, skipped=0)
    assert units["tests-c9aea87-20261016a"]["totals"] == dict(passed=260, failure=0, error=0, skipped=0)
    assert units["tests-c9aea87-20261016a"]["deselected"] == 6
    assert units["green-795a243"]["deselected_tests"] == units["tests-c9aea87-20261016a"]["deselected_tests"]
    pending["units.json"] = encoded(units)

    probes, inputs = {}, {}
    parent_identity = load(PARENT_PROBES / "results/identity.json")
    assert parent_identity["files"] == {p: sha(git("show", parent_identity["head"] + ":" + p)) for p in parent_identity["files"]}
    assert load(PARENT_PROBES / "completion.json")["ok"] is True
    for filename in ("results/identity.json", "results/C_person.json", "completion.json", "launch.json"):
        path = PARENT_PROBES / filename
        external_files.append(file_id(path))
        pending["reference/parent-critical/" + filename] = path.read_bytes()
    for name in ("pole_c", "C_person"):
        current = load(EXTERNAL / "probes-c9aea87-20261016a/results" / (name + ".json"))
        sealed = load(EXTERNAL / "probes-sealed-707ea9c-20261016a/results" / (name + ".json"))
        control = sealed if name == "pole_c" else load(PARENT_PROBES / "results/C_person.json")
        hits = lambda result: [r["k"] for r in result["rows"] if r["hit"]]
        assert hits(current) == hits(control) and current["summary"] == control["summary"]
        placement_keys = ("k", "X", "n_obj", "Y", "Zb", "axis_valid")
        for c, s in zip(current["rows"], sealed["rows"], strict=True):
            assert all(c.get(k) == s.get(k) for k in placement_keys)
        summary = current["summary"]
        assert (summary["stop_frames"], summary["visible_frames"]) == ((82, 177) if name == "pole_c" else (55, 153))
        if name == "C_person":
            assert summary["first_stop_X"] == 82.77
        probes[name] = dict(summary=summary, measured_frames=len(current["rows"]),
                            matched_stop_frames=hits(current), sealed_matched_stop_frames=hits(sealed),
                            reference="sealed 707ea9c" if name == "pole_c" else "retained parent f3074cf",
                            reference_matched_stop_frames=hits(control),
                            sealed_summary=sealed["summary"],
                            lost_vs_sealed=sorted(set(hits(sealed)) - set(hits(current))),
                            new_vs_sealed=sorted(set(hits(current)) - set(hits(sealed))),
                            lost_matched_stop_frames=[], new_matched_stop_frames=[],
                            placement_identical=True,
                            differing_full_rows=[c["k"] for c, s in zip(current["rows"], sealed["rows"], strict=True) if c != s])
        bag = summary["cache"]
        decoded = DATA / "decoded" / bag
        paths = sorted(decoded.glob("f_*.npz"))[:len(current["rows"])]
        assert len(paths) == len(current["rows"])
        paths += [decoded / "meta.json", DATA / "decoded" / (bag + "_baseline.json"),
                  DATA / "odometry" / ("icp_" + bag + ".json")]
        records = [file_id(p) for p in paths]
        inputs[name] = dict(method="Post-run raw-byte inventory of shared readonly inputs; existing stored baseline reused",
                            root=str(decoded), processed_frames=len(current["rows"]),
                            files=records, inventory_sha256=sha(canonical(records)))
    pending["probe_comparison.json"] = encoded(probes)
    pending["probe_input_identity.json"] = encoded(inputs)

    dark, matched_inputs = {}, {}
    dark_run = EXTERNAL / "dark-c9aea87-20261016a/results"
    for piece, stops in (("ride_1", 14), ("ride_3", 2)):
        ref_path, got_path = REFERENCE / (piece + ".jsonl"), dark_run / (piece + ".jsonl")
        external_files.append(file_id(ref_path))
        reference_stops, current_stops, centers, identity_rows = [], [], [], []
        mismatches = {k: [] for k in ("detection_centers", "warning_centers", "serialized", "descriptors")}
        n_candidates = 0
        with ref_path.open() as rf, got_path.open() as gf:
            for n, (r, g) in enumerate(zip(map(json.loads, rf), map(json.loads, gf), strict=True)):
                assert r["i"] == g["i"] == n
                assert all(r[k] == g[k] for k in ("frame_id", "stamp", "input", "cache_sha256", "mask"))
                assert not g["observer"] and not g["spares"]
                assert all(not c["spared"] for c in g["candidates"])
                assert all(not any(t.get("spare_hist", [])) for t in g["tracks"])
                n_candidates += len(g["candidates"])
                frame = g["frame_id"]
                identity_rows.append({k: g[k] for k in ("i", "frame_id", "stamp", "input", "cache_sha256", "mask")})
                for key in ("detections", "warnings"):
                    rc = Counter(tuple(d["center"]) for d in r["serialized"][key])
                    gc = Counter(tuple(d["center"]) for d in g["serialized"][key])
                    if rc != gc:
                        mismatches["detection_centers" if key == "detections" else "warning_centers"].append(frame)
                if r["serialized"] != g["serialized"]:
                    mismatches["serialized"].append(frame)
                if any(r["serialized"][key] != g["serialized"][key] for key in ("detections", "warnings")):
                    mismatches["descriptors"].append(frame)
                if r["serialized"]["obstacle"]:
                    reference_stops.append(frame)
                if g["serialized"]["obstacle"]:
                    current_stops.append(frame)
                    centers.append(dict(frame=frame, centers=[d["center"] for d in g["serialized"]["detections"]]))
        assert len(identity_rows) == 1409 and reference_stops == current_stops and len(current_stops) == stops
        assert not mismatches["detection_centers"] and not mismatches["warning_centers"]
        dark[piece] = dict(frames=len(identity_rows), candidates=n_candidates,
                           first_frame=identity_rows[0]["frame_id"], last_frame=identity_rows[-1]["frame_id"],
                           sealed_stop=stops, withdrawal_stop=stops, stop_frames=current_stops,
                           extra_stop_frames=[], lost_stop_frames=[], exact_stop_centers=centers,
                           center_tolerance=0, comparison="Exact serialized numeric center multiset, no rounding or rematching",
                           mismatches=mismatches, ordered_input_identity_sha256=sha(canonical(identity_rows)))
        matched_inputs[piece] = identity_rows
    guard = load(dark_run / "shipping_guard.json")
    assert guard == dict(disabled_by_effective_config=True, free_top_calls=0, frames=2818, candidates=5065,
                         spared_candidates=0, provisional_tracks=0, spare_history_tracks=0,
                         free_top_implementation_present=True, exact_observer_installed=True, observer_calls=0)
    pending["dark_comparison.json"] = encoded(dark)
    pending["dark_input_identity.json"] = encoded(matched_inputs)

    helpers = ["docs/evidence/judgement_2026-10-13/scripts/" + p for p in ("range_test.py", "judge_runner.py")]
    helpers += ["scripts/cache_io.py", "tests/conftest.py", "tests/test_column_shipping.py"]
    sources = {p: sha(git("show", HEAD + ":" + p)) for p in helpers}
    for p in helpers:
        assert git("show", HEAD + ":" + p) == (ROOT / p).read_bytes().replace(b"\r\n", b"\n")
    for p in helpers[:2]:
        assert git("show", HEAD + ":" + p) == git("show", SEALED + ":" + p)
    sources["protocol"] = file_id(P.parent / "WITHDRAWAL.md")
    sources["ride_intake"] = file_id(DATA / "cache/new_data/intake_manifest.json")
    pending["helper_source_identity.json"] = encoded(sources)
    image = json.loads(subprocess.check_output(["docker", "image", "inspect", IMAGE]))[0]
    assert image["Os"] == "linux" and image["Architecture"] == "amd64"
    pending["runtime.json"] = encoded(dict(image={k: image[k] for k in ("Id", "Os", "Architecture", "RepoDigests", "Created")}, runs=runtime))
    pending["EXTERNAL_ARTIFACTS.json"] = encoded(dict(root=str(EXTERNAL), sealed_plain=str(REFERENCE), files=external_files))
    pending["VERIFICATION.json"] = encoded(dict(
        verified_at_utc=datetime.now(timezone.utc).isoformat(), measured_head=HEAD, sealed_head=SEALED,
        author_shipping_selection="registered measurements satisfied", independent_H4_clearance=False,
        new_measurements_launched=0, unit_failures=0, unit_errors=0, unit_skips=0, unit_deselections=6,
        exact_registered_probe_frame_sets_equal=True, exact_dark_stop_frames_equal=True, exact_dark_centers_equal=True,
        free_top_calls=0, observer_calls=0, source_sha256=candidate["source_sha256"],
        config_sha256=candidate["config_sha256"], native_sha256=NATIVE,
        scope="WITHDRAWAL.md author selection only; criterion 8.1 remains OPEN; parent owns full gates/re-review"))
    return pending


def verify():
    manifest = load(P / "PACKAGE_HASHES.json")
    for name, digest in manifest.items():
        path = P.parent / "WITHDRAWAL_RESULTS.md" if name == "../WITHDRAWAL_RESULTS.md" else P / name
        assert sha(path.read_bytes().replace(b"\r\n", b"\n")) == digest, path
    for item in load(P / "EXTERNAL_ARTIFACTS.json")["files"]:
        assert file_id(Path(item["path"])) == item, item["path"]
    for entry in load(P / "probe_input_identity.json").values():
        for item in entry["files"]:
            assert file_id(Path(item["path"])) == item, item["path"]
    for entry in load(P / "dark_details.json").values():
        for item in entry["stamp_sidecars"]:
            assert file_id(Path(item["path"])) == item, item["path"]
    for path in P.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    proof = load(P / "withdrawn_test_byte_proof.json")
    original = git("show", proof["original_commit"] + ":" + proof["original_path"])
    assert original == (ROOT / proof["archived_path"]).read_bytes()
    assert sha(original) == proof["sha256"]
    print(json.dumps(dict(package_integrity="PASS", measured_head=HEAD,
                          external_artifacts=len(load(P / "EXTERNAL_ARTIFACTS.json")["files"]),
                          independent_H4_clearance=False)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--seal", action="store_true", help="Hash finished package/report without remeasuring")
    args = ap.parse_args()
    if args.verify:
        verify()
    elif args.seal:
        target = P / "PACKAGE_HASHES.json"
        assert not target.exists()
        paths = [p for p in sorted(P.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
        hashes = {p.relative_to(P).as_posix(): sha(p.read_bytes().replace(b"\r\n", b"\n")) for p in paths}
        hashes["../WITHDRAWAL_RESULTS.md"] = sha((P.parent / "WITHDRAWAL_RESULTS.md").read_bytes().replace(b"\r\n", b"\n"))
        target.write_bytes(encoded(hashes))
        verify()
    else:
        pending = derive()
        assert all(not (P / name).exists() for name in pending)
        for name, data in pending.items():
            path = P / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as f:
                f.write(data)
        print(json.dumps(dict(retained_files=len(pending), measurements_launched=0,
                              result=load(P / "VERIFICATION.json")), indent=2))


if __name__ == "__main__":
    main()
