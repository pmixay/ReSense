"""S1 evidence integrity and pre-registered acceptance bounds; no Docker required."""
from copy import deepcopy
import importlib.util
import json
import sqlite3
import struct
from types import SimpleNamespace

import pytest

from scripts import startup_acceptance as s1


@pytest.fixture
def recording():
    stamps = [1_700_000_000 + i * 0.1 for i in range(201)]
    inventory = {"expected_frames": 201, "stamps": stamps, "topic": "/points"}
    rows = []
    for i, stamp in enumerate(stamps):
        t = 100 + i * 0.1
        decision = "STOP" if i >= 8 else "FAULT"
        rows.extend([
            {"t": t, "k": "decision", "v": decision},
            {"t": t, "k": "status", "snapshot": "frame", "decision": decision,
             "stamp": stamp, "frames": i, "fresh": i >= 8, "reason": "current" if i >= 8 else "catchup",
             "age": 0.25, "nearest": 56 if i >= 8 else None, "lat_ms": 70,
             "decode_ms": 20, "detect_ms": 50, "cpu": 1.3, "rss": 700,
             "dropped": 0, "skipped": 0, "topic": "/points"},
            {"t": t, "k": "latency", "v": 70},
        ])
    rows.extend([{"t": 130, "k": "decision", "v": "FAULT"},
                 {"t": 130, "k": "status", "snapshot": "watchdog", "decision": "FAULT",
                  "frames": 201, "fresh": False, "age": None}])
    meta = {"node_advertised": True, "listener_ready": True, "drained": True, "cleanup_ok": True,
            "player_exit": 0, "listener_exit": 0, "judge_analysis_exit": 0,
            "t_start": 1, "t_ready": 2, "t_play": 90, "t_end": 121, "errors": []}
    sample = {"t": 5, "cpu_pct": 130, "docker_working_set_bytes": 800_000_000,
              "cgroup_peak_bytes": 900_000_000, "cgroup_source": "/sys/fs/cgroup/memory.peak"}
    samples = [sample, dict(sample, t=131)]
    return rows, meta, samples, inventory


def test_complete_listener_evidence_and_distinct_memory_definitions(recording):
    m = s1.summarize_run(*recording)
    assert m["complete"], m["errors"]
    assert m["fresh_frames"] == 193
    assert m["frames_processed"] == 201
    assert m["frame_results"]["FAULT"] == 8
    assert m["watchdog_results"] == {"FAULT": 1}
    assert m["source_age_p50_s"] == 0.25
    assert m["first_stop_dist"] == 56
    assert m["first_stop_after_first_result_s"] == pytest.approx(0.8)
    assert m["node_cpu_cores_p50"] == m["docker_cpu_cores_mean"] == 1.3
    assert m["node_rss_peak_mb"] == 700 * 1024**2 / 1e6
    assert m["docker_working_set_peak_mb"] == 800
    assert m["container_cgroup_peak_mb"] == m["memory_gate_mb"] == 900


def test_watchdog_stop_is_never_a_frame_or_first_stop(recording):
    rows, meta, samples, inventory = recording
    rows[:0] = [{"t": 95, "k": "decision", "v": "STOP"},
                {"t": 95, "k": "status", "snapshot": "watchdog", "decision": "STOP",
                 "frames": 0, "nearest": 999, "fresh": True}]
    m = s1.summarize_run(rows, meta, samples, inventory)
    assert m["complete"], m["errors"]
    assert m["fresh_frames"] == 193
    assert m["frame_results"]["STOP"] == 193
    assert m["first_stop_dist"] == 56
    assert m["first_stop_after_first_result_s"] == pytest.approx(0.8)


def test_actual_node_watchdogs_omit_frame_counters_without_becoming_frames(recording):
    rows, meta, samples, inventory = recording
    rows[-1]["frames"] = None
    metrics = s1.summarize_run(rows, meta, samples, inventory)
    assert metrics["complete"], metrics["errors"]
    assert metrics["frames_processed"] == 201
    assert metrics["frame_results"]["FAULT"] == 8
    assert metrics["watchdog_results"] == {"FAULT": 1}
    del rows[-5:-2]  # Nullable watchdogs cannot conceal a missing final input frame.
    metrics = s1.summarize_run(rows, meta, samples, inventory)
    assert not metrics["complete"]
    assert any("last expected bag frame missing" in e for e in metrics["errors"])


def test_skipped_frames_stay_in_denominator(recording):
    rows, meta, samples, inventory = recording
    # A complete, intentionally thinned run: only the last 100 bag frames processed.
    rows = rows[101 * 3:]
    for r in rows:
        if r["k"] == "status":
            r["frames"] -= 101
    m = s1.summarize_run(rows, meta, samples, inventory)
    assert m["complete"], m["errors"]
    assert m["frames_processed"] == m["fresh_frames"] == 100
    assert m["missing_bag_frame_results"] == 101
    assert m["fresh_fraction"] == 100 / 201
    assert m["fresh_fraction"] < 0.8


@pytest.mark.parametrize("change,reason", [
    (lambda r, m, s, i: m.pop("player_exit"), "player_exit"),
    (lambda r, m, s, i: m.update(player_exit=137), "player_exit"),
    (lambda r, m, s, i: m.update(drained=False), "drained"),
    (lambda r, m, s, i: m.update(cleanup_ok=False), "cleanup_ok"),
    (lambda r, m, s, i: i.pop("expected_frames"), "expected bag frames"),
    (lambda r, m, s, i: i.update(stamps=[]), "expected"),
    (lambda r, m, s, i: r.pop(1), "frame status"),
    (lambda r, m, s, i: r.pop(0), "decision messages"),
    (lambda r, m, s, i: r.pop(2), "latency messages"),
    (lambda r, m, s, i: r[1].pop("age"), "age"),
    (lambda r, m, s, i: r[1].update(fresh="true"), "freshness"),
    (lambda r, m, s, i: r[1].update(snapshot=None), "snapshot"),
    (lambda r, m, s, i: r[1].update(stamp=999), "absent from original bag"),
    (lambda r, m, s, i: r[4].update(stamp=r[1]["stamp"]), "duplicate/backwards"),
    (lambda r, m, s, i: r[-2].update(v="GO"), "mismatched"),
    (lambda r, m, s, i: s.clear(), "no Docker stats"),
    (lambda r, m, s, i: s[0].pop("cgroup_peak_bytes"), "high-water"),
    (lambda r, m, s, i: s[-1].update(t=122), "final drain"),
])
def test_incomplete_or_corrupt_evidence_fails_closed(recording, change, reason):
    change(*recording)
    metrics = s1.summarize_run(*recording)
    assert not metrics["complete"]
    assert any(reason in e for e in metrics["errors"]), metrics["errors"]


def test_missing_last_bag_frame_is_not_a_complete_run(recording):
    rows, meta, samples, inventory = recording
    del rows[-5:-2]  # Entire last frame, decision and latency; telemetry counts alone agree.
    rows[-1]["frames"] = 200
    m = s1.summarize_run(rows, meta, samples, inventory)
    assert not m["complete"]
    assert any("last expected bag frame missing" in e for e in m["errors"])


def good_matrix():
    results = []
    for condition, (_, expected, _) in s1.CONDITIONS.items():
        for repetition in (1, 2, 3):
            results.append({"condition": condition, "repetition": repetition, "metrics": {
                "complete": True, "expected_frames": expected, "fresh_frames": expected,
                "fresh_fraction": 0.9, "source_age_p50_s": 0.3, "source_age_max_s": 0.4,
                "memory_gate_mb": 1000, "first_stop_dist": 56,
                "first_stop_after_first_result_s": 1.0, "frame_results": {"STOP": 193, "FAULT": 5}}})
    return results


@pytest.mark.parametrize("condition,metric,op,bound", [
    (c, metric, op, bound) for c, checks in s1.THRESHOLDS.items() for metric, op, bound in checks
])
def test_inclusive_median_boundaries_and_no_rounding(condition, metric, op, bound):
    results = good_matrix()
    group = [r["metrics"] for r in results if r["condition"] == condition]

    def set_value(m, value):
        (m["frame_results"] if metric in s1.DECISIONS else m)[metric] = value

    for m in group:
        set_value(m, bound)
    # One outlier must not change the median.
    set_value(group[0], bound - 1e-7 if op == ">=" else bound + 1e-7)
    report = s1.evaluate_matrix(results, list(s1.CONDITIONS), 3)
    assert report["passed"], report
    set_value(group[1], bound - 1e-7 if op == ">=" else bound + 1e-7)
    report = s1.evaluate_matrix(results, list(s1.CONDITIONS), 3)
    assert not report["passed"]
    failed = [c for c in report["conditions"][condition]["checks"] if c["metric"] == metric and c["operator"] == op]
    assert failed[0]["median"] != bound
    assert not failed[0]["passed"]


@pytest.mark.parametrize("bad", ["run", "count", "missing", "duplicate", "nonfinite", "null"])
def test_one_incomplete_repetition_cannot_hide_in_good_medians(bad):
    results = good_matrix()
    if bad == "run":
        results[0]["metrics"]["complete"] = False
    elif bad == "count":
        results[0]["metrics"].pop("expected_frames")
    elif bad == "missing":
        results.pop(0)
    elif bad == "duplicate":
        results[0]["repetition"] = 2
    else:
        results[0]["metrics"]["fresh_fraction"] = float("nan") if bad == "nonfinite" else None
    assert not s1.evaluate_matrix(results, list(s1.CONDITIONS), 3)["passed"]


def test_diagnostics_cannot_pass_acceptance():
    results = good_matrix()
    assert not s1.evaluate_matrix(results[:3], ["obstacle_literal"], 3)["passed"]
    assert not s1.evaluate_matrix([r for r in results if r["repetition"] == 1], list(s1.CONDITIONS), 1)["passed"]


@pytest.mark.parametrize("text", ['{"x":NaN}', '{"x":Infinity}', '{"x":1e999}', '{"x":1,"x":2}'])
def test_non_json_numbers_and_duplicate_keys_rejected(text):
    with pytest.raises(ValueError):
        s1.strict_json(text)


@pytest.mark.parametrize("text", ["", '{"k":"status"}', '{"k":"status"}\n{', '{}\n\n', '[]\n'])
def test_empty_truncated_or_corrupt_jsonl_rejected(tmp_path, text):
    path = tmp_path / "bad.jsonl"
    path.write_text(text)
    with pytest.raises(ValueError):
        s1.read_jsonl(path)


def test_judge_scripts_are_exact_lf_normalized_copies():
    for name in ("listener.py", "analyze_chain.py", "chain.sh"):
        assert (s1.TOOLS / name).read_text() == (s1.JUDGE / name).read_text()


def test_inventory_checks_real_sqlite_topic_counts_and_headers_read_only(tmp_path):
    db = tmp_path / "original.db3"
    (tmp_path / "metadata.yaml").write_text("original metadata\n")
    with sqlite3.connect(db) as con:
        con.executescript("CREATE TABLE topics (id INTEGER, name TEXT, type TEXT); "
                          "CREATE TABLE messages (id INTEGER, topic_id INTEGER, timestamp INTEGER, data BLOB);")
        con.execute("INSERT INTO topics VALUES (1, '/points', 'sensor_msgs/msg/PointCloud2')")
        for i in range(3):
            cdr = b"\x00\x01\x00\x00" + struct.pack("<iI", 1_700_000_000, i * 100_000_000) + b"cloud"
            con.execute("INSERT INTO messages VALUES (?, 1, ?, ?)", (i, i * 100_000_000, cdr))
    before = s1.sha256_file(db)
    inventory = s1.bag_inventory(tmp_path, 3)
    assert inventory["expected_frames"] == 3
    assert inventory["topic"] == "/points"
    assert inventory["duration_s"] == 0.2
    assert inventory["files"][0]["sha256"] == before == s1.sha256_file(db)
    with pytest.raises(ValueError, match="expected 201"):
        s1.bag_inventory(tmp_path, 201)


@pytest.mark.parametrize("text,expected", [("1GiB", 1024**3), ("800MiB", 800 * 1024**2),
                                           ("1200MB", 1_200_000_000), ("2.5kB", 2500)])
def test_docker_memory_units(text, expected):
    assert s1.memory_bytes(text) == expected


def saved_matrix(tmp_path, recording, baseline=False):
    root = tmp_path / "evidence"
    raw = root / "out/docker"
    raw.mkdir(parents=True)
    hashes = {p: "e" * 64 for p in s1.SOURCE_PATHS}
    images = [{"role": "candidate", "id": "sha256:" + "c" * 64, "detector_commit": "a" * 40,
               "expected_source_sha256_lf": hashes}]
    if baseline:
        images.insert(0, {"role": "baseline", "id": "sha256:" + "b" * 64, "detector_commit": "b" * 40,
                          "expected_source_sha256_lf": hashes})
    manifest = {"schema": "resense.s1.docker.v1", "run_id": "unit", "images": images,
                "conditions": list(s1.CONDITIONS), "domain_base": 20,
                "repeats": 3, "cpus": 4, "memory_limit": "4g", "node_args": [], "bags": {},
                "host": {"platform": "unit-host", "docker_version": {"Server": "unit"},
                         "docker_info": {"NCPU": 4}}}
    slot = 0
    for image in images:
        for condition, (bag, expected, flags) in s1.CONDITIONS.items():
            rows, meta, samples, inventory = deepcopy(recording)
            # Keep realistic frame telemetry; clear bag requires 252 distinct input headers.
            if expected == 252:
                template = deepcopy(rows[1])
                rows = []
                inventory["expected_frames"] = 252
                inventory["stamps"] = [1_700_000_000 + i * 0.1 for i in range(252)]
                for i, stamp in enumerate(inventory["stamps"]):
                    t = 100 + i * 0.1
                    rows += [{"t": t, "k": "decision", "v": "GO"},
                             dict(template, t=t, frames=i, stamp=stamp, decision="GO", fresh=True,
                                  reason="current"), {"t": t, "k": "latency", "v": 70}]
                rows += [{"t": 140, "k": "decision", "v": "FAULT"},
                         {"t": 140, "k": "status", "snapshot": "watchdog", "decision": "FAULT", "frames": 252}]
                meta["t_end"] = 130
                samples[-1]["t"] = 141
            manifest["bags"][bag] = inventory
            for repetition in (1, 2, 3):
                label = f"{image['role']}_{condition}_r{repetition}"
                receipt = dict(meta, image_id=image["id"], detector_commit=image["detector_commit"],
                               condition=condition, repetition=repetition, play_args=" ".join(flags),
                               label=label, domain=20 + slot, cpus=4, memory_limit="4g", node_args=[],
                               runtime_provenance={"source_sha256_lf": hashes, "thread_env": s1.THREAD_ENV})
                receipt["containers"] = {role: {
                    "id": role, "image": image["id"], "NanoCpus": 4_000_000_000,
                    "Memory": 4 * 1024**3, "MemorySwap": 4 * 1024**3,
                    "cmd": ["ros2", "bag", "play", f"/data/{bag}", *flags] if role == "player" else [],
                    "labels": {"resense.startup.run": "unit", "resense.startup.domain": str(20 + slot)},
                } for role in ("node", "listener", "player")}
                receipt["final_states"] = {role: {"Running": False, "OOMKilled": False, "ExitCode": 0}
                                           for role in receipt["containers"]}
                s1.write_json(raw / (label + ".meta"), receipt)
                s1.write_json(raw / (label + ".summary.json"), {"label": label})
                for suffix, data in ((".jsonl", rows), (".samples.jsonl", samples)):
                    (raw / (label + suffix)).write_text("".join(json.dumps(r) + "\n" for r in data))
                slot += 1
    s1.write_json(root / "manifest.json", manifest)
    return root


def test_saved_candidate_passes_but_cannot_claim_improvement(tmp_path, recording):
    root = saved_matrix(tmp_path, recording)
    report = s1.analyze_directory(root)
    assert report["passed"], report
    assert not report["improvement_claim_allowed"]
    assert report["comparison_mode"] == "published_judge_different_runtime"
    assert "DIFFERENT" in report["published_comparison"]["runtime"]


def test_saved_missing_frame_and_corrupt_result_cannot_pass(tmp_path, recording):
    root = saved_matrix(tmp_path, recording)
    path = root / "out/docker/candidate_obstacle_literal_r1.jsonl"
    rows = s1.read_jsonl(path)
    del rows[1]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert not s1.analyze_directory(root)["passed"]
    path.write_text('{"broken":')
    assert not s1.analyze_directory(root)["complete"]


def test_same_runtime_baseline_must_also_be_complete(tmp_path, recording):
    root = saved_matrix(tmp_path, recording, baseline=True)
    report = s1.analyze_directory(root)
    assert report["passed"], report
    assert report["comparison_mode"] == "same_runtime_measured_AB"
    path = root / "out/docker/baseline_clear_literal_r3.meta"
    path.unlink()
    report = s1.analyze_directory(root)
    assert not report["passed"]
    assert not report["improvement_claim_allowed"]


def test_wrong_cpu_or_node_overrides_are_diagnostic_only(tmp_path, recording):
    root = saved_matrix(tmp_path, recording)
    manifest_path = root / "manifest.json"
    manifest = s1.read_json(manifest_path)
    manifest["cpus"] = 8
    manifest_path.write_text(json.dumps(manifest))
    assert not s1.analyze_directory(root)["passed"]
    manifest.update(cpus=4, node_args=["catchup_startup_step:=0"])
    manifest_path.write_text(json.dumps(manifest))
    assert not s1.analyze_directory(root)["passed"]


def test_partial_container_creation_is_cleaned_up_without_docker(tmp_path, monkeypatch):
    class FakeDocker:
        def __init__(self):
            self.calls = []

        def call(self, *args, **kwargs):
            self.calls.append(args)
            return SimpleNamespace(stdout="", stderr="", returncode=0)

        def state(self, name):
            if name.endswith("-player"):
                return {"State": {"Running": False, "ExitCode": 2}}
            return {"State": {"Running": False, "ExitCode": 0}}

    # Fail during node creation; even this partial resource must be removed.
    fake = FakeDocker()
    (tmp_path / "out/docker").mkdir(parents=True)
    image = {"role": "candidate", "id": "sha256:abc", "detector_commit": "a" * 40}
    args = s1.parser().parse_args(["--bags", str(tmp_path)])
    monkeypatch.setattr(s1.time, "sleep", lambda _: None)
    meta = s1.run_one(fake, tmp_path, {"run_id": "a" * 32}, image, "obstacle_literal", 1, 70, args)
    assert meta["errors"]
    assert meta["cleanup_ok"]
    assert any(c[:2] == ("rm", meta["container_names"]["node"]) for c in fake.calls)
    run = next(c for c in fake.calls if c[0] == "run")
    assert "--cpus" in run and "--memory" in run
    assert "ROS_DOMAIN_ID=70" in run
    assert "ROS_LOCALHOST_ONLY=0" in run
    assert not any("docker.sock" in str(arg) for arg in run)


def test_existing_output_is_refused_before_any_docker_call(tmp_path, monkeypatch):
    monkeypatch.setattr(s1, "command", lambda *a, **kw: pytest.fail("Docker/git command should not run"))
    with pytest.raises(SystemExit) as error:
        s1.main(["--image", "candidate", "--detector-commit", "HEAD", "--bags", str(tmp_path), "--out", str(tmp_path)])
    assert error.value.code == 2


def test_analyze_missing_manifest_returns_strict_failure_json(tmp_path, capsys):
    assert s1.main(["--analyze", str(tmp_path)]) == 1
    assert json.loads(capsys.readouterr().out)["passed"] is False


@pytest.mark.parametrize("field", ["runtime_provenance", "containers", "final_states", "cpus", "node_args"])
def test_missing_runtime_receipts_cannot_pass(tmp_path, recording, field):
    root = saved_matrix(tmp_path, recording)
    path = root / "out/docker/candidate_obstacle_literal_r1.meta"
    receipt = s1.read_json(path)
    receipt.pop(field)
    path.write_text(json.dumps(receipt))
    assert not s1.analyze_directory(root)["passed"]


def test_actual_player_flags_must_match_condition(tmp_path, recording):
    root = saved_matrix(tmp_path, recording)
    path = root / "out/docker/candidate_obstacle_literal_r1.meta"
    receipt = s1.read_json(path)
    receipt["containers"]["player"]["cmd"] += ["--read-ahead-queue-size", "10"]
    path.write_text(json.dumps(receipt))
    assert not s1.analyze_directory(root)["passed"]


def test_missing_original_bags_returns_json_before_docker(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(s1, "command", lambda *a, **kw: pytest.fail("Docker/git must not run"))
    assert s1.main(["--image", "candidate", "--detector-commit", "HEAD", "--bags", str(tmp_path),
                    "--out", str(tmp_path / "new")]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["passed"] is report["complete"] is False
    assert not (tmp_path / "new").exists()


@pytest.mark.parametrize("bad", [None, [], "corrupt", {"schema": "resense.s1.docker.v1", "images": [None]}])
def test_corrupt_manifest_returns_strict_failure_json(tmp_path, capsys, bad):
    (tmp_path / "manifest.json").write_text(json.dumps(bad))
    assert s1.main(["--analyze", str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["passed"] is report["complete"] is False


def test_incorrect_actual_memory_limit_cannot_pass(tmp_path, recording):
    root = saved_matrix(tmp_path, recording)
    path = root / "out/docker/candidate_obstacle_literal_r1.meta"
    receipt = s1.read_json(path)
    receipt["containers"]["node"].update(Memory=8 * 1024**3, MemorySwap=8 * 1024**3)
    path.write_text(json.dumps(receipt))
    assert not s1.analyze_directory(root)["passed"]


def test_docker_cli_limit_and_stats_units_are_distinct():
    assert s1.memory_limit_bytes("4g") == 4 * 1024**3
    assert s1.memory_limit_bytes("1200MB") == 1200 * 1024**2
    assert s1.memory_bytes("1200MB") == 1_200_000_000


def test_no_frame_results_cannot_pass_the_clear_fault_bound(recording):
    rows, meta, samples, inventory = recording
    metrics = s1.summarize_run(rows[-2:], meta, samples, inventory)
    assert metrics["frame_results"]["FAULT"] == 0
    assert metrics["fresh_frames"] == 0
    assert metrics["fresh_fraction"] == 0
    assert not metrics["complete"]
    assert "no frame results" in metrics["errors"]


def test_balanced_topic_loss_cannot_hide_missing_status_counter(recording):
    rows, meta, samples, inventory = recording
    del rows[-3]  # A latency message.
    del rows[0]  # A decision message.
    del rows[0]  # The first frame status, with later node counters still preserved.
    metrics = s1.summarize_run(rows, meta, samples, inventory)
    assert not metrics["complete"]
    assert metrics["missing_status_messages"] == 1
    assert metrics["missing_bag_frame_results"] == 1
    assert metrics["missing_decision_messages"] == 0  # Both corresponding status and decision lost.
    assert metrics["extra_latency_messages"] == 0
    assert metrics["decision_message_delta"] == metrics["latency_message_delta"] == 0


def test_same_runtime_baseline_may_fail_targets_but_must_be_measured(tmp_path, recording):
    root = saved_matrix(tmp_path, recording, baseline=True)
    for repetition in (1, 2, 3):
        path = root / f"out/docker/baseline_obstacle_literal_r{repetition}.jsonl"
        rows = s1.read_jsonl(path)
        for row in rows:
            if row.get("snapshot") == "frame":
                row.update(fresh=False, reason="source_stale", age=7.3)
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    report = s1.analyze_directory(root)
    assert report["passed"], report
    assert report["complete"]
    assert not report["evaluations"]["baseline"]["passed"]


@pytest.mark.parametrize("condition", ["obstacle_literal", "clear_readme"])
@pytest.mark.parametrize("player_exit", [0, 2])
@pytest.mark.parametrize("bags_volume", [None, "native-test-bags"])
def test_driver_player_contract_and_cleanup_for_success_and_failure(tmp_path, monkeypatch, condition, player_exit, bags_volume):
    """Exercise real orchestration with a fake CLI; no container/process is started."""
    manifest = {"run_id": "a" * 32, "cpus": 4, "memory_limit": "4g", "node_args": []}
    image = {"role": "candidate", "id": "sha256:" + "c" * 64, "detector_commit": "d" * 40,
             "expected_source_sha256_lf": {p: "e" * 64 for p in s1.SOURCE_PATHS}}
    base = tmp_path / f"out/docker/candidate_{condition}_r1"
    base.parent.mkdir(parents=True)
    removed = []
    states = {}

    class FakeDocker:
        def call(self, *args, **kwargs):
            out = ""
            if args[0] == "run":
                name = args[args.index("--name") + 1]
                labels = dict(args[i + 1].split("=", 1) for i, arg in enumerate(args) if arg == "--label")
                cmd = list(args[args.index(image["id"]) + 1:])
                role = name.rsplit("-", 1)[1]
                if role == "player":
                    data_mounts = [v for v in args if isinstance(v, str) and "dst=/data" in v]
                    assert len(data_mounts) == 1 and "readonly" in data_mounts[0]
                    assert (f"type=volume,src={bags_volume}" in data_mounts[0]) if bags_volume else (
                        "type=bind" in data_mounts[0])
                if role != "node":
                    assert args[args.index("--pid") + 1].endswith("-node")
                assert "ROS_LOCALHOST_ONLY=0" in args
                states[name] = {
                    "Id": name, "Image": image["id"],
                    "Config": {"Cmd": cmd, "Labels": labels},
                    "HostConfig": {"NanoCpus": 4_000_000_000, "Memory": 4 * 1024**3,
                                   "MemorySwap": 4 * 1024**3},
                    "State": {"Running": role != "player", "ExitCode": player_exit if role == "player" else 0,
                              "OOMKilled": False},
                }
                if role == "listener":
                    s1.Path(str(base) + ".ready").write_text("ready")
            elif args[0] == "logs":
                out = "ReSense detector listening on /points"
            elif args[0] == "stats":
                out = json.dumps({"MemUsage": "800MB / 4GiB", "CPUPerc": "130%"})
            elif args[0] == "exec":
                if args[-1] == "provenance":
                    out = json.dumps({"source_sha256_lf": image["expected_source_sha256_lf"],
                                      "thread_env": s1.THREAD_ENV})
                elif args[-1] == "memory":
                    out = json.dumps({"bytes": 900_000_000, "source": "/sys/fs/cgroup/memory.peak"})
                elif "/tools/analyze_chain.py" in args:
                    original_meta = s1.read_json(str(base) + ".meta")
                    assert original_meta["t_end"] >= original_meta["t_play"]
                    assert original_meta["play_args"] == " ".join(s1.CONDITIONS[condition][2])
                    assert not s1.Path(str(base) + ".receipt.json").exists()
            elif args[0] == "stop":
                states[args[-1]]["State"]["Running"] = False
            elif args[0] == "rm":
                removed.append(args[-1])
            return SimpleNamespace(stdout=out, stderr="", returncode=0)

        def state(self, name):
            return states[name]

    class NoBackgroundThread:
        def __init__(self, **kwargs):
            pass

        def start(self):
            pass

        def join(self, **kwargs):
            pass

        def is_alive(self):
            return False

    monkeypatch.setattr(s1.threading, "Thread", NoBackgroundThread)
    monkeypatch.setattr(s1.time, "sleep", lambda _: None)
    monkeypatch.setattr(s1, "drained", lambda *a: True)
    args = s1.parser().parse_args(["--bags", str(tmp_path)] + (["--bags-volume", bags_volume] if bags_volume else []))
    meta = s1.run_one(FakeDocker(), tmp_path, manifest, image, condition, 1, 20, args)
    assert set(removed) == set(meta["container_names"].values())
    assert meta["cleanup_ok"]
    bag, _, flags = s1.CONDITIONS[condition]
    assert meta["containers"]["player"]["cmd"] == ["ros2", "bag", "play", f"/data/{bag}", *flags]
    if player_exit:
        assert meta["errors"] and "Player failed" in meta["errors"][0]
        assert "drained" not in meta
    else:
        assert meta["errors"] == []
        assert meta["player_exit"] == meta["listener_exit"] == meta["judge_analysis_exit"] == 0
        receipt = s1.read_json(str(base) + ".receipt.json")
        assert receipt["cleanup_ok"] and "judge_analysis_exit" not in s1.read_json(str(base) + ".meta")
        s1.validate_receipt(meta, manifest, image, condition, 1, 20)


def load_launcher():
    spec = importlib.util.spec_from_file_location("s1_matrix_launcher", s1.TOOLS / "launch_matrix.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detached_launcher_captures_exclusive_logs_and_does_not_wait(tmp_path, monkeypatch, capsys):
    launcher = load_launcher()
    root = tmp_path / "long_matrix"
    launched = []

    def popen(cmd, **kwargs):
        launched.append((cmd, kwargs))
        return SimpleNamespace(pid=12345)

    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(launcher.sys, "argv", ["launch_matrix.py", "--out", str(root), "--",
                                              "--image", "candidate", "--memory", "6g"])
    launcher.main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["pid"] == 12345
    assert launched[0][0][-4:] == ["--image", "candidate", "--memory", "6g"]
    assert launched[0][1]["stdin"] == launcher.subprocess.DEVNULL
    assert s1.Path(receipt["stdout"]).exists() and s1.Path(receipt["stderr"]).exists()
    assert s1.read_json(str(root) + ".launch.json")["driver_sha256"] == s1.sha256_file(s1.REPO / "scripts/startup_acceptance.py")
    with pytest.raises(SystemExit):
        launcher.main()
    assert len(launched) == 1


def test_manual_cleanup_refuses_a_mismatched_container_owner(tmp_path, monkeypatch):
    launcher = load_launcher()
    s1.write_json(tmp_path / "manifest.json", {"run_id": "owned"})
    calls = []

    def command(args, **kwargs):
        calls.append(args)
        if args[1] == "ps":
            out = "candidate-id\n"
        else:
            out = json.dumps([{"Config": {"Labels": {"resense.startup.run": "someone-else"}}}])
        return SimpleNamespace(stdout=out, stderr="", returncode=0)

    monkeypatch.setattr(s1, "command", command)
    with pytest.raises(RuntimeError, match="another run"):
        launcher.cleanup(tmp_path)
    assert not any(args[1] in ("stop", "rm") for args in calls)


@pytest.mark.parametrize("changed", ["publication", "raw", "launch", "staging"])
def test_publication_verifier_detects_tampered_report_raw_and_launch_artifacts(tmp_path, capsys, changed):
    spec = importlib.util.spec_from_file_location("s1_report_publisher", s1.TOOLS / "publish_report.py")
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    out, raw = tmp_path / "report", tmp_path / "raw"
    out.mkdir()
    raw.mkdir()
    report_file, raw_file, launch_file = out / "summary.json", raw / "status.jsonl", tmp_path / "raw.launch.json"
    staging_file = tmp_path / "stage.json"
    for path in (report_file, raw_file, launch_file, staging_file):
        path.write_text("original\n")
    s1.write_json(out / "raw_hash_index.json", {"attempts": [{
        "raw_root": str(raw), "files": [publisher.indexed(raw_file, raw)],
        "sibling_files": [publisher.indexed(launch_file, tmp_path)]}],
        "staging": {"raw_root": str(tmp_path), "files": [publisher.indexed(staging_file, tmp_path)]}})
    s1.write_json(out / "publication_hash_index.json", {
        "files": [publisher.indexed(p, out) for p in sorted(out.iterdir())]})
    publisher.verify(out)
    assert json.loads(capsys.readouterr().out)["verified"]
    {"publication": report_file, "raw": raw_file, "launch": launch_file, "staging": staging_file}[changed].write_text("altered\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        publisher.verify(out)


@pytest.fixture
def original_volume_bags(tmp_path):
    source, volume = tmp_path / "windows_bags", tmp_path / "linux_volume"
    source.mkdir()
    volume.mkdir()
    expected = {}
    for bag, count in {v[0]: v[1] for v in s1.CONDITIONS.values()}.items():
        folder = source / bag
        folder.mkdir()
        (folder / "metadata.yaml").write_bytes(("unchanged original " + bag + "\r\n").encode())
        db = folder / (bag + "_0.db3")
        with sqlite3.connect(db) as con:
            con.executescript("CREATE TABLE topics (id INTEGER, name TEXT, type TEXT); "
                              "CREATE TABLE messages (id INTEGER, topic_id INTEGER, timestamp INTEGER, data BLOB);")
            con.execute("INSERT INTO topics VALUES (1, '/points', 'sensor_msgs/msg/PointCloud2')")
            for i in range(count):
                cdr = b"\x00\x01\x00\x00" + struct.pack("<iI", 1_700_000_000 + i // 10, (i % 10) * 100_000_000) + b"cloud"
                con.execute("INSERT INTO messages VALUES (?, 1, ?, ?)", (i, i * 100_000_000, cdr))
        expected[bag] = s1.bag_inventory(folder, count)
    return source, volume, expected


def test_volume_copy_and_read_only_inventory_preserve_full_original_bytes(original_volume_bags):
    source, volume, expected = original_volume_bags
    tool = s1.volume_tools()
    before = {p.relative_to(source).as_posix(): s1.sha256_file(p) for p in source.rglob("*") if p.is_file()}
    copied = tool.copy_bags(source, volume, expected)
    assert copied["copied"] and len(copied["files"]) == 4
    verified = tool.verify_bags(volume, expected)
    assert verified["verified"] and verified["inventory_digest"] == tool.inventory_digest(expected)
    after = {p.relative_to(source).as_posix(): s1.sha256_file(p) for p in source.rglob("*") if p.is_file()}
    assert before == after == {p.relative_to(volume).as_posix(): s1.sha256_file(p)
                              for p in volume.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="nonempty"):
        tool.copy_bags(source, volume, expected)


@pytest.mark.parametrize("corruption", ["database", "metadata", "extra_file", "extra_directory", "frames", "stamps", "size"])
def test_volume_reuse_rejects_corrupt_partial_or_wrong_inventory(original_volume_bags, corruption):
    source, volume, expected = original_volume_bags
    tool = s1.volume_tools()
    tool.copy_bags(source, volume, expected)
    bag = next(iter(expected))
    if corruption in ("database", "metadata"):
        target = volume / bag / (expected[bag]["files"][0]["name"] if corruption == "database" else "metadata.yaml")
        target.chmod(0o666)
        with target.open("ab") as f:
            f.write(b"changed bytes")
    elif corruption == "extra_file":
        (volume / "helper-marker.txt").write_text("forbidden non-data file")
    elif corruption == "extra_directory":
        (volume / bag / "extra").mkdir()
    elif corruption == "frames":
        expected[bag]["expected_frames"] -= 1
    elif corruption == "stamps":
        expected[bag]["stamps"][0] += 0.01
    else:
        expected[bag]["files"][0]["bytes"] -= 1
    with pytest.raises(ValueError):
        tool.verify_bags(volume, expected)


def verified_volume_storage(original_volume_bags):
    source, volume, expected = original_volume_bags
    tool = s1.volume_tools()
    tool.copy_bags(source, volume, expected)
    return {"kind": "docker_volume", "source": "native-bags", "inventory_digest": tool.inventory_digest(expected),
            "verification": {"result": tool.verify_bags(volume, expected), "read_only": True,
                             "cleanup_ok": True, "state": {"ExitCode": 0, "OOMKilled": False},
                             "mounts": [{"Type": "volume", "Name": "native-bags", "Destination": "/data", "RW": False}]}}


@pytest.mark.parametrize("changed", ["digest", "metadata_digest", "mount_rw", "name", "cleanup", "verified"])
def test_volume_provenance_cannot_claim_unverified_or_writable_data(original_volume_bags, changed):
    storage = verified_volume_storage(original_volume_bags)
    expected = original_volume_bags[2]
    s1.validate_volume_storage(storage, expected)
    if changed == "digest":
        storage["inventory_digest"] = "0" * 64
    elif changed == "metadata_digest":
        storage["verification"]["result"]["bags"][next(iter(expected))]["metadata_sha256"] = "0" * 64
    elif changed == "mount_rw":
        storage["verification"]["mounts"][0]["RW"] = True
    elif changed == "name":
        storage["source"] = "wrong-volume"
    elif changed == "cleanup":
        storage["verification"]["cleanup_ok"] = False
    else:
        storage["verification"]["result"]["verified"] = False
    with pytest.raises(ValueError, match="verification incomplete or mismatched"):
        s1.validate_volume_storage(storage, expected)


def test_missing_volume_is_not_implicitly_created(tmp_path):
    class MissingVolumeDocker:
        def __init__(self):
            self.calls = []

        def call(self, *args, **kwargs):
            self.calls.append(args)
            raise RuntimeError("No such volume")

    docker = MissingVolumeDocker()
    with pytest.raises(RuntimeError, match="No such volume"):
        s1.verify_volume(docker, tmp_path, "image", "absent", {}, "run")
    assert docker.calls == [("volume", "inspect", "absent")]
    assert list(tmp_path.iterdir()) == []


def test_saved_volume_requires_matching_readonly_player_mount_and_verification(tmp_path, recording, original_volume_bags):
    root = saved_matrix(tmp_path, recording)
    storage = verified_volume_storage(original_volume_bags)
    manifest_path = root / "manifest.json"
    manifest = s1.read_json(manifest_path)
    manifest.update(data_storage=storage, bags=original_volume_bags[2])
    manifest_path.write_text(json.dumps(manifest))
    s1.write_json(root / "bags_volume_verification.json", storage)
    for receipt_path in (root / "out/docker").glob("*.meta"):
        receipt = s1.read_json(receipt_path)
        receipt["data_storage"] = s1.storage_identity(storage)
        receipt["containers"]["player"]["mounts"] = [{"Type": "volume", "Name": storage["source"],
                                                      "Destination": "/data", "RW": False}]
        receipt_path.write_text(json.dumps(receipt))
    assert s1.analyze_directory(root)["passed"]
    bad_receipt = root / "out/docker/candidate_obstacle_literal_r1.meta"
    receipt = s1.read_json(bad_receipt)
    receipt["containers"]["player"]["mounts"][0]["RW"] = True
    bad_receipt.write_text(json.dumps(receipt))
    assert not s1.analyze_directory(root)["passed"]
