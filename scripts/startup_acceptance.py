#!/usr/bin/env python3
"""S1 original-bag Docker acceptance. Host dependencies: Python stdlib + Docker CLI.

See docs/evidence/node_startup_2026-10-15/DOCKER_PROTOCOL.md. No builds, socket mounts,
mutable image tags during playback, or changes to the 13 October judge evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import statistics
import struct
import subprocess
import sys
import threading
import time
import uuid


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "docs/evidence/node_startup_2026-10-15/docker_tools"
JUDGE = REPO / "docs/evidence/judgement_2026-10-13/scripts/docker"
CONDITIONS = {
    "obstacle_literal": ("doubleT_obstacle", 201, []),
    "obstacle_readme": ("doubleT_obstacle", 201,
                        ["--read-ahead-queue-size", "10", "--clock", "--delay", "3"]),
    "clear_literal": ("roundT_doubleT", 252, []),
    "clear_readme": ("roundT_doubleT", 252,
                     ["--read-ahead-queue-size", "10", "--clock", "--delay", "3"]),
}
DECISIONS = ("GO", "CAUTION", "STOP", "FAULT")
THREAD_ENV = {k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}
SOURCE_PATHS = ("ros2_ws/src/resense_ros/resense_ros/detector_node.py",
                "ros2_ws/src/resense_ros/launch/detector.launch.py",
                "ros2_ws/src/resense_ros/resense_ros/decision_policy.py",
                "ros2_ws/src/resense_ros/setup.py")
PUBLISHED_COMPARISON = {
    "source": "docs/BACKLOG.md S1; judgement_2026-10-13",
    "runtime": "Published judge, DIFFERENT runtime/host; not a same-runtime A/B baseline",
    "obstacle_literal": {"processed": 146, "expected": 201, "fresh": 0,
                         "source_age_p50_s": 7.33, "source_age_max_s": 10.51,
                         "reported_rss_mb": 3357},
    "obstacle_readme": {"fresh": 35, "expected": 201, "source_age_max_s": 1.2},
    "clear_literal": {"fault": 47},
    "memory_note": "Historical MB labels are not reinterpreted as this protocol's decimal MB.",
}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def integer(value):
    return type(value) is int and value >= 0


def strict_json(text):
    def invalid(token):
        raise ValueError(f"Non-finite JSON constant: {token}")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def floating(token):
        value = float(token)
        if not math.isfinite(value):
            raise ValueError(f"Non-finite JSON number: {token}")
        return value

    return json.loads(text, parse_constant=invalid, parse_float=floating, object_pairs_hook=pairs)


def read_json(path):
    value = strict_json(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def read_jsonl(path):
    text = Path(path).read_text(encoding="utf-8")
    if not text or not text.endswith("\n"):
        raise ValueError(f"Empty/truncated JSONL: {path}")
    rows = [strict_json(line) for line in text.splitlines()]
    if any(not isinstance(r, dict) for r in rows):
        raise ValueError(f"Non-object JSONL row: {path}")
    return rows


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bag_inventory(folder, expected):
    """Read only sqlite metadata + the 12-byte CDR header, never whole point clouds.

    Original bag header stamps, not reception times, identify distinct frame results.
    Full database hashes bind evidence to the recordings, including their cloud data.
    """
    folder = Path(folder).resolve(strict=True)
    dbs = sorted(folder.glob("*.db3"))
    if not dbs or not (folder / "metadata.yaml").is_file():
        raise ValueError(f"Original sqlite rosbag/metadata missing: {folder}")
    stamps, topics, times, files = [], set(), [], []
    for db in dbs:
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as con:
            found = con.execute("SELECT id, name FROM topics WHERE type = ?",
                                ("sensor_msgs/msg/PointCloud2",)).fetchall()
            if len(found) != 1:
                raise ValueError(f"Expected one PointCloud2 topic in {db}")
            tid, topic = found[0]
            topics.add(topic)
            for timestamp, prefix in con.execute(
                    "SELECT timestamp, substr(data, 1, 12) FROM messages "
                    "WHERE topic_id = ? ORDER BY timestamp, id", (tid,)):
                if len(prefix) != 12 or prefix[:2] not in (b"\x00\x01", b"\x00\x00"):
                    raise ValueError(f"Unsupported/truncated CDR in {db}")
                sec, ns = struct.unpack(("<" if prefix[1] else ">") + "iI", prefix[4:12])
                if sec <= 0 or ns >= 1_000_000_000:
                    raise ValueError(f"Invalid PointCloud2 header in {db}")
                stamps.append(sec + ns * 1e-9)
                times.append(timestamp)
        files.append({"name": db.name, "bytes": db.stat().st_size, "sha256": sha256_file(db)})
    if len(stamps) != expected or len(set(stamps)) != expected or len(topics) != 1:
        raise ValueError(f"{folder.name}: expected {expected} unique frames / one topic, "
                         f"got {len(stamps)} / {len(set(stamps))} / {topics}")
    if stamps != sorted(stamps):
        raise ValueError("Original bag headers must progress")
    return {"path": str(folder), "expected_frames": expected, "topic": topics.pop(),
            "stamps": stamps, "duration_s": (max(times) - min(times)) / 1e9,
            "files": files, "metadata_sha256": sha256_file(folder / "metadata.yaml")}


def memory_bytes(text):
    m = re.fullmatch(r"\s*([\d.]+)\s*(B|kB|KB|MB|GB|KiB|MiB|GiB)\s*", text)
    if not m:
        raise ValueError(f"Unrecognised docker memory value: {text}")
    units = {"B": 1, "kB": 1000, "KB": 1000, "MB": 10**6, "GB": 10**9,
             "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}
    value = float(m[1]) * units[m[2]]
    if not finite(value):
        raise ValueError("Non-finite Docker memory")
    return value


def memory_limit_bytes(text):
    """Docker CLI RAM limits use binary k/m/g suffixes, unlike Docker stats SI units."""
    match = re.fullmatch(r"([0-9]+)(b|k|kb|m|mb|g|gb)?", text.lower())
    if not match:
        raise ValueError("--memory must be positive bytes or an integer k/m/g limit (e.g. 4g)")
    suffix = match[2] or "b"
    value = int(match[1]) * {"b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[suffix[0]]
    if value <= 0:
        raise ValueError("--memory must be positive")
    return value


def volume_tools():
    spec = importlib.util.spec_from_file_location("s1_bags_volume", TOOLS / "bags_volume.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def player_data_mount(args):
    if args.bags_volume:
        return f"type=volume,src={args.bags_volume},dst=/data,readonly,volume-nocopy"
    return f"type=bind,src={Path(args.bags).resolve()},dst=/data,readonly"


def storage_identity(storage):
    return {k: storage[k] for k in ("kind", "source", "inventory_digest") if k in storage}


def validate_volume_storage(storage, inventories):
    tool = volume_tools()
    verification = storage.get("verification", {})
    result = verification.get("result", {})
    mounts = [m for m in verification.get("mounts", []) if m.get("Destination") == "/data"]
    if (storage.get("kind") != "docker_volume" or not storage.get("source") or
            storage.get("inventory_digest") != tool.inventory_digest(inventories) or
            result.get("verified") is not True or result.get("inventory_digest") != storage["inventory_digest"] or
            result.get("bags") != tool.identity(inventories) or verification.get("read_only") is not True or
            verification.get("cleanup_ok") is not True or verification.get("state", {}).get("ExitCode") != 0 or
            verification.get("state", {}).get("OOMKilled") is not False or len(mounts) != 1 or
            mounts[0].get("Type") != "volume" or mounts[0].get("Name") != storage["source"] or
            mounts[0].get("RW") is not False):
        raise ValueError("Docker-volume full-file identity / read-only verification incomplete or mismatched")


def verify_volume(docker, root, image, name, inventories, run_id):
    inspected = strict_json(docker.call("volume", "inspect", name).stdout)[0]
    if inspected.get("Name") != name or inspected.get("Driver") != "local" or inspected.get("Options"):
        raise ValueError("Playback requires an existing native local Docker volume, without bind/driver options")
    tool = volume_tools()
    write_json(root / "volume_expected.json", inventories)
    shutil.copyfile(TOOLS / "bags_volume.py", root / "bags_volume.py")
    verification = tool.container_job(docker, image, root, name, "verify", run_id, host_api=sys.modules[__name__])
    storage = {"kind": "docker_volume", "source": name,
               "host_inventory_source": {bag: v["path"] for bag, v in inventories.items()},
               "inventory_digest": tool.inventory_digest(inventories), "volume_inspect": inspected,
               "verification": verification}
    validate_volume_storage(storage, inventories)
    write_json(root / "bags_volume_verification.json", storage)
    return storage


def summarize_run(rows, meta, samples, inventory):
    """Strict, unrounded S1 analysis of the unchanged judge listener's schema.

    Missing bag frames are reported and remain in the fresh denominator. They may be
    deliberate catch-up skips. Missing *telemetry* or an undrained/truncated run is an
    infrastructure failure, never a zero that can pass a median threshold.
    """
    errors = list(meta.get("errors", []))
    expected = inventory.get("expected_frames")
    stamps = inventory.get("stamps", [])
    if not integer(expected) or not expected or len(stamps) != expected:
        errors.append("missing/invalid expected bag frames")
    if not stamps or any(not finite(s) for s in stamps) or len(set(stamps)) != len(stamps):
        errors.append("missing/invalid expected header stamps")
    for key in ("node_advertised", "listener_ready", "drained", "cleanup_ok"):
        if meta.get(key) is not True:
            errors.append(f"{key} not confirmed")
    for key in ("player_exit", "listener_exit", "judge_analysis_exit"):
        if type(meta.get(key)) is not int or meta[key] != 0:
            errors.append(f"{key} not zero")
    for key in ("t_start", "t_ready", "t_play", "t_end"):
        if not finite(meta.get(key)):
            errors.append(f"{key} missing/non-finite")
    if all(finite(meta.get(k)) for k in ("t_start", "t_ready", "t_play", "t_end")):
        if not meta["t_start"] <= meta["t_ready"] <= meta["t_play"] < meta["t_end"]:
            errors.append("invalid run wall-time ordering")
    statuses, frames, decisions, latencies = [], [], [], []
    last_t = -math.inf
    for i, r in enumerate(rows):
        if not finite(r.get("t")) or r["t"] < last_t:
            errors.append(f"row {i}: invalid/non-progressing arrival clock")
        else:
            last_t = r["t"]
        kind = r.get("k")
        if kind == "status":
            statuses.append(r)
            if r.get("decision") not in DECISIONS:
                errors.append(f"row {i}: unknown decision")
            if r.get("snapshot") == "frame":
                frames.append(r)
                for k in ("stamp", "lat_ms", "decode_ms", "detect_ms", "cpu", "rss", "age"):
                    if not finite(r.get(k)):
                        errors.append(f"row {i}: missing/non-finite {k}")
                for k in ("frames", "dropped", "skipped"):
                    if not integer(r.get(k)):
                        errors.append(f"row {i}: invalid {k} counter")
                if type(r.get("fresh")) is not bool or not isinstance(r.get("reason"), str):
                    errors.append(f"row {i}: invalid freshness")
                if r.get("topic") != inventory.get("topic"):
                    errors.append(f"row {i}: unexpected input topic")
                if r.get("decision") == "STOP" and (
                        not finite(r.get("nearest")) or r["nearest"] <= 0):
                    errors.append(f"row {i}: STOP distance missing/invalid")
            elif r.get("snapshot") == "processing_error":
                errors.append("processing_error snapshot")
            elif r.get("snapshot") != "watchdog":
                errors.append(f"row {i}: missing/unknown snapshot kind")
        elif kind == "decision" and r.get("v") in DECISIONS:
            decisions.append(r["v"])
        elif kind == "latency" and finite(r.get("v")) and r["v"] >= 0:
            latencies.append(r["v"])
        else:
            errors.append(f"row {i}: invalid message kind/value")
    if not frames:
        errors.append("no frame results")
    counters = [r.get("frames") for r in frames]
    # node.frames is emitted before the node increments n_frames for that result.
    if counters != list(range(len(frames))):
        errors.append("missing/duplicate frame status messages (non-contiguous node.frames)")
    received = [r.get("stamp") for r in frames]
    if any(not finite(s) for s in received):
        errors.append("invalid frame stamps")
    elif received:
        if any(b <= a for a, b in zip(received, received[1:])):
            errors.append("duplicate/backwards frame stamps")
        if any(not any(abs(s - e) <= 2e-6 for e in stamps) for s in received):
            errors.append("frame stamp absent from original bag")
        if not stamps or abs(received[-1] - stamps[-1]) > 2e-6:
            errors.append("last expected bag frame missing (incomplete drain)")
    watchdogs = [r for r in statuses if r.get("snapshot") == "watchdog"]
    final_watchdogs = [r for r in watchdogs if finite(r.get("t")) and
                       finite(meta.get("t_end")) and r["t"] >= meta["t_end"] and
                       r.get("frames") in (None, len(frames))]
    if not final_watchdogs:
        errors.append("no post-player watchdog confirming expired monitoring")
    decision_delta = len(statuses) - len(decisions)
    latency_delta = len(frames) - len(latencies)
    if decision_delta or decisions != [r.get("decision") for r in statuses]:
        errors.append("missing/extra/mismatched decision messages")
    if latency_delta:
        errors.append("missing/extra latency messages")
    valid_samples = []
    for sample in samples:
        if (not finite(sample.get("t")) or not finite(sample.get("cpu_pct")) or sample["cpu_pct"] < 0 or
                not finite(sample.get("docker_working_set_bytes")) or
                sample["docker_working_set_bytes"] <= 0 or
                not integer(sample.get("cgroup_peak_bytes")) or sample["cgroup_peak_bytes"] <= 0 or
                sample.get("cgroup_source") not in ("/sys/fs/cgroup/memory.peak",
                                                    "/sys/fs/cgroup/memory/memory.max_usage_in_bytes")):
            errors.append("invalid/missing Docker stats / cgroup high-water sample")
        else:
            valid_samples.append(sample)
    if not valid_samples:
        errors.append("no Docker stats / cgroup memory peak evidence")
    elif finite(meta.get("t_play")) and finite(meta.get("t_end")):
        if min(s["t"] for s in valid_samples) > meta["t_play"] or max(
                s["t"] for s in valid_samples) < meta["t_end"] + 4:
            errors.append("Docker stats do not cover playback and final drain")
    if frames and expected and len(frames) > expected:
        errors.append("more results than original bag frames")

    def values(key):
        return [r[key] for r in frames if finite(r.get(key))]

    def median_or_none(items):
        return statistics.median(items) if items else None

    first_stop = next((r for r in frames if r.get("decision") == "STOP"), None)
    fresh = sum(r.get("fresh") is True for r in frames)
    peak_mb = max((s["cgroup_peak_bytes"] / 1e6 for s in valid_samples), default=None)
    rss_mb = max((r * 1024**2 / 1e6 for r in values("rss")), default=None)
    # Frame counters are zero-based; watchdog counters are the completed-result total.
    counter_end = max(max((c + 1 for c in counters if integer(c)), default=0),
                      max((r["frames"] for r in watchdogs if integer(r.get("frames"))), default=0))
    if counter_end != len(frames) or any(r.get("frames") is not None and
                                       not integer(r["frames"]) for r in watchdogs):
        errors.append("missing/invalid status messages according to completed-result counter")
    return {
        "complete": not errors, "errors": errors, "expected_frames": expected,
        "frames_processed": len(frames), "fresh_frames": fresh,
        "fresh_fraction": fresh / expected if integer(expected) and expected else None,
        "missing_bag_frame_results": max(0, expected - len(frames)) if integer(expected) else None,
        "missing_status_messages": max(0, counter_end - len(frames)),
        "missing_decision_messages": max(0, decision_delta),
        "extra_decision_messages": max(0, -decision_delta),
        "missing_latency_messages": max(0, latency_delta),
        "extra_latency_messages": max(0, -latency_delta),
        "decision_message_delta": decision_delta, "latency_message_delta": latency_delta,
        "frame_results": {d: sum(r.get("decision") == d for r in frames) for d in DECISIONS},
        "watchdog_results": dict(Counter(r.get("decision") for r in watchdogs)),
        "decision_messages": dict(Counter(decisions)),
        "freshness_reasons": dict(Counter(str(r.get("reason")) for r in frames)),
        "first_stop_after_first_result_s": first_stop["t"] - frames[0]["t"] if first_stop else None,
        "first_stop_dist": first_stop.get("nearest") if first_stop else None,
        "source_age_p50_s": median_or_none(values("age")),
        "source_age_max_s": max(values("age"), default=None),
        "latency_p50_ms": median_or_none(latencies),
        "node_cpu_cores_p50": median_or_none(values("cpu")),
        "node_cpu_cores_max": max(values("cpu"), default=None),
        "docker_cpu_cores_mean": statistics.mean(s["cpu_pct"] / 100 for s in valid_samples)
        if valid_samples else None,
        "docker_cpu_cores_max": max((s["cpu_pct"] / 100 for s in valid_samples), default=None),
        "docker_working_set_peak_mb": max((s["docker_working_set_bytes"] / 1e6
                                           for s in valid_samples), default=None),
        "container_cgroup_peak_mb": peak_mb, "node_rss_peak_mb": rss_mb,
        "memory_gate_mb": max(peak_mb, rss_mb) if peak_mb is not None and rss_mb is not None else None,
        "dropped": frames[-1].get("dropped") if frames else None,
        "skipped": frames[-1].get("skipped") if frames else None,
    }


# Every bound is inclusive. No display rounding precedes a comparison.
THRESHOLDS = {
    "obstacle_readme": (("fresh_frames", ">=", 180), ("source_age_max_s", "<=", 0.6),
                        ("STOP", ">=", 185), ("first_stop_after_first_result_s", "<=", 1.2)),
    "obstacle_literal": (("fresh_fraction", ">=", 0.8), ("source_age_p50_s", "<=", 0.5),
                         ("memory_gate_mb", "<=", 1200), ("first_stop_dist", ">=", 55),
                         ("first_stop_dist", "<=", 57)),
    "clear_literal": (("FAULT", "<=", 10),),
    "clear_readme": (("fresh_frames", ">=", 242),),
}


def evaluate_matrix(results, selected, repeats):
    """Require exactly three complete replicates per condition before median acceptance."""
    groups, errors = {}, []
    if repeats != 3 or set(selected) != set(CONDITIONS) or len(selected) != len(CONDITIONS):
        errors.append("acceptance requires all four conditions and exactly three repetitions")
    for condition in selected:
        group = [r for r in results if r.get("condition") == condition]
        issues = []
        if len(group) != repeats or sorted(r.get("repetition", -1) for r in group) != list(range(1, repeats + 1)):
            issues.append("missing/duplicate repetitions")
        if any(r.get("metrics", {}).get("complete") is not True for r in group):
            issues.append("incomplete/corrupt run")
        expected = CONDITIONS[condition][1]
        if any(r.get("metrics", {}).get("expected_frames") != expected for r in group):
            issues.append("expected frame count absent/wrong")
        checks = []
        for metric, op, bound in THRESHOLDS[condition]:
            vals = [(r.get("metrics", {}).get("frame_results", {}).get(metric)
                     if metric in DECISIONS else r.get("metrics", {}).get(metric)) for r in group]
            if len(vals) != repeats or not vals or not all(finite(v) for v in vals):
                med = None
            else:
                med = statistics.median(vals)
            passed = med is not None and (med >= bound if op == ">=" else med <= bound)
            checks.append({"metric": metric, "median": med, "operator": op,
                           "bound": bound, "passed": passed})
        groups[condition] = {"complete": not issues, "errors": issues, "checks": checks,
                             "passed": not issues and all(c["passed"] for c in checks)}
    if len(results) != len(selected) * repeats:
        errors.append("missing/extra condition results")
    return {"passed": not errors and all(g["passed"] for g in groups.values()),
            "errors": errors, "conditions": groups}


def command(args, timeout=30, input_text=None, check=True):
    proc = subprocess.run([str(a) for a in args], input=input_text, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    if check and proc.returncode:
        raise RuntimeError(f"Command exited {proc.returncode}: {args}\n{proc.stderr}\n{proc.stdout}")
    return proc


class Docker:
    def __init__(self, root):
        self.root = root
        self.lock = threading.Lock()

    def call(self, *args, timeout=30, check=True):
        p = command(["docker", *args], timeout=timeout, check=check)
        with self.lock:
            with (self.root / "docker_commands.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"t": time.time(), "argv": ["docker", *args],
                                    "exit": p.returncode}, allow_nan=False) + "\n")
        return p

    def state(self, name):
        return strict_json(self.call("inspect", name).stdout)[0]


def source_hashes(commit):
    full = command(["git", "-C", REPO, "rev-parse", "--verify", commit + "^{commit}"], timeout=10).stdout.strip()
    hashes = {}
    for p in SOURCE_PATHS:
        text = command(["git", "-C", REPO, "show", full + ":" + p], timeout=10).stdout
        hashes[p] = hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()
    return full, hashes


def image_info(docker, image, commit):
    inspected = strict_json(docker.call("image", "inspect", image).stdout)[0]
    full, hashes = source_hashes(commit)
    return {"reference": image, "id": inspected["Id"], "detector_commit": full,
            "expected_source_sha256_lf": hashes,
            "inspect": {k: inspected.get(k) for k in ("Id", "RepoTags", "RepoDigests", "Created", "Architecture", "Os")},
            "image_labels": inspected.get("Config", {}).get("Labels")}


def wait_until(test, seconds, message):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if test():
            return
        time.sleep(0.3)
    raise TimeoutError(message)


def stats_sample(docker, name):
    raw = strict_json(docker.call("stats", "--no-stream", "--format", "{{json .}}", name,
                                 timeout=15).stdout)
    peak = strict_json(docker.call("exec", name, "python3", "/tools/runtime_probe.py",
                                  "memory", timeout=15).stdout)
    usage = raw["MemUsage"].split("/")[0].strip()
    return {"t": time.time(), "cpu_pct": float(raw["CPUPerc"].removesuffix("%")),
            "docker_working_set_bytes": memory_bytes(usage),
            "cgroup_peak_bytes": peak["bytes"], "cgroup_source": peak["source"],
            "docker_stats": raw}, usage


def save_sample(samples, legacy, sample, usage):
    samples.write(json.dumps(sample, allow_nan=False) + "\n")
    samples.flush()
    # The exact original analyzer hardcodes rs_node; raw JSON retains the real name.
    legacy.write(f"{sample['t']} rs_node {sample['cpu_pct']}% {usage}\n")
    legacy.flush()


def collect_stats(docker, name, base, stop, errors):
    with Path(str(base) + ".samples.jsonl").open("x", encoding="utf-8") as samples, \
            Path(str(base) + ".stats").open("x", encoding="utf-8") as legacy:
        while not stop.is_set():
            try:
                sample, usage = stats_sample(docker, name)
                save_sample(samples, legacy, sample, usage)
            except Exception as e:
                errors.append(f"stats monitor: {type(e).__name__}: {e}")
                return
            stop.wait(0.5)


def drained(base, t_end):
    path = Path(str(base) + ".observer.jsonl")
    if not path.exists():
        return False
    # A concurrent append may leave a partial last line. It is control-plane only;
    # the final listener JSONL is parsed strictly after a clean listener shutdown.
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        rows = [strict_json(s) for s in lines]
    except ValueError:
        return False
    frames = [r for r in rows if r.get("snapshot") == "frame"]
    return bool(frames and rows and rows[-1].get("snapshot") == "watchdog" and
                rows[-1]["t"] > t_end and time.time() - t_end >= 4 and
                time.time() - frames[-1]["t"] >= 2)


def run_one(docker, root, manifest, image, condition, repetition, domain, args):
    label = f"{image['role']}_{condition}_r{repetition}"
    base = root / "out/docker" / label
    prefix = "rs-s1-" + manifest["run_id"][:12] + "-" + label.replace("_", "-")
    names = {role: prefix + "-" + role for role in ("node", "listener", "player")}
    meta = {"label": label, "condition": condition, "repetition": repetition, "errors": [],
            "image_id": image["id"], "detector_commit": image["detector_commit"],
            "domain": domain, "container_names": names, "cpus": args.cpus,
            "memory_limit": args.memory, "play_args": " ".join(CONDITIONS[condition][2]),
            "node_args": args.node_arg, "t_start": time.time()}
    if manifest.get("data_storage"):
        meta["data_storage"] = storage_identity(manifest["data_storage"])
    created, monitor = [], None
    stop, stat_errors = threading.Event(), []
    bag, _, flags = CONDITIONS[condition]
    # Domains are deterministic per run/slot; refuse collisions with another active driver.
    collision = docker.call("ps", "-q", "--filter", f"label=resense.startup.domain={domain}").stdout.strip()
    if collision:
        raise RuntimeError(f"Active S1 run already owns ROS_DOMAIN_ID={domain}: {collision}")

    def start(role, extra, cmd):
        options = ["run", "-d", "--init", "--name", names[role], "--network", "host",
                   "--cpus", str(args.cpus), "--memory", args.memory, "--memory-swap", args.memory,
                   "--label", f"resense.startup.run={manifest['run_id']}",
                   "--label", f"resense.startup.domain={domain}",
                   "--label", f"resense.startup.image_id={image['id']}",
                   "--label", f"resense.startup.detector_commit={image['detector_commit']}",
                   "--label", f"resense.startup.condition={condition}",
                   "--label", f"resense.startup.repetition={repetition}",
                   "--label", f"resense.startup.args={json.dumps(cmd)}",
                   "--label", f"resense.startup.cpus={args.cpus}",
                   "--label", f"resense.startup.memory={args.memory}",
                   "--env", f"ROS_DOMAIN_ID={domain}", "--env", "ROS_LOCALHOST_ONLY=0",
                   "--env", "PYTHONUNBUFFERED=1", "--env", "HOME=/tmp",
                   "--env", "RESENSE_DDS=udp", "--env", "ROS_HOME=/tmp/.ros",
                   "--env", "ROS_LOG_DIR=/tmp/.ros/log"]
        for k, v in THREAD_ENV.items():
            options += ["--env", f"{k}={v}"]
        # Fast DDS uses process identity in participant GUIDs. Separate PID namespaces
        # can give the witness and player the same PID on the same host network.
        if role != "node":
            options += ["--pid", "container:" + names["node"]]
        options += extra + [image["id"]] + cmd
        # Register intended name first: a CLI timeout can occur after Docker created it.
        created.append(names[role])
        docker.call(*options, timeout=45)
        inspected = docker.state(names[role])
        meta.setdefault("containers", {})[role] = {
            "id": inspected["Id"], "image": inspected["Image"],
            "NanoCpus": inspected["HostConfig"]["NanoCpus"],
            "Memory": inspected["HostConfig"]["Memory"],
            "MemorySwap": inspected["HostConfig"]["MemorySwap"],
            "cmd": inspected["Config"]["Cmd"], "labels": inspected["Config"].get("Labels"),
            "pid_mode": inspected["HostConfig"].get("PidMode", ""),
            "network_mode": inspected["HostConfig"].get("NetworkMode"),
            "ros_localhost_only": dict(e.split("=", 1) for e in inspected["Config"].get("Env", [])
                                        if "=" in e).get("ROS_LOCALHOST_ONLY"),
            "mounts": inspected.get("Mounts", []),
        }
        if inspected["Image"] != image["id"] or inspected["HostConfig"]["NanoCpus"] != int(args.cpus * 1e9):
            raise RuntimeError("Docker did not apply the requested immutable image / CPU limit")
        if inspected["HostConfig"]["Memory"] <= 0:
            raise RuntimeError("Docker did not apply a memory bound")

    mounts = ["--mount", f"type=bind,src={root / 'tools'},dst=/tools,readonly",
              "--mount", f"type=bind,src={root},dst=/evidence"]
    try:
        node_cmd = ["ros2", "launch", "resense_ros", "detector.launch.py", "freshness_mode:=replay",
                    *args.node_arg]
        start("node", mounts, node_cmd)
        monitor = threading.Thread(target=collect_stats,
                                   args=(docker, names["node"], base, stop, stat_errors), daemon=True)
        monitor.start()

        def advertised():
            if not docker.state(names["node"])["State"]["Running"]:
                raise RuntimeError("Node exited before advertising")
            logs = docker.call("logs", names["node"])
            return "listening on" in logs.stdout + logs.stderr

        wait_until(advertised, args.ready_timeout, "node did not advertise")
        meta.update(node_advertised=True, t_ready=time.time())
        provenance = strict_json(docker.call("exec", names["node"], "python3",
                                             "/tools/runtime_probe.py", "provenance").stdout)
        meta["runtime_provenance"] = provenance
        if provenance["source_sha256_lf"] != image["expected_source_sha256_lf"]:
            raise RuntimeError("Image node/launch source does not match --detector-commit")
        start("listener", mounts, ["python3", "/tools/observe_listener.py",
                                   "--base", f"/evidence/out/docker/{label}"])

        def listener_ready():
            if not docker.state(names["listener"])["State"]["Running"]:
                raise RuntimeError("Listener exited before graph readiness")
            return Path(str(base) + ".ready").exists()

        wait_until(listener_ready, args.ready_timeout, "listener not ready")
        meta["listener_ready"] = True
        time.sleep(4)  # Original judge discovery allowance, after positive graph readiness.
        meta["t_play"] = time.time()
        start("player", ["--user", "1000:1000", "--mount", player_data_mount(args)],
              ["ros2", "bag", "play", f"/data/{bag}", *flags])
        wait_until(lambda: not docker.state(names["player"])["State"]["Running"],
                   args.player_timeout, "player timeout")
        meta["t_end"] = time.time()
        player_state = docker.state(names["player"])["State"]
        meta["player_exit"] = player_state["ExitCode"]
        if meta["player_exit"] != 0 or player_state.get("OOMKilled"):
            raise RuntimeError(f"Player failed: {player_state}")
        wait_until(lambda: drained(base, meta["t_end"]), args.drain_timeout,
                   "queue/watchdog drain timeout")
        meta["drained"] = True
        docker.call("stop", "--time", "12", names["listener"], timeout=20)
        meta["listener_exit"] = docker.state(names["listener"])["State"]["ExitCode"]
        # The exact judge analyzer reads <label>.meta. Preserve this immutable
        # playback-time snapshot, then write final cleanup evidence separately.
        write_json(str(base) + ".meta", meta)
        analyzer = docker.call("exec", "--workdir", "/evidence", names["node"], "python3",
                               "/tools/analyze_chain.py", label, check=False)
        meta["judge_analysis_exit"] = analyzer.returncode
        Path(str(base) + ".analysis.log").write_text(analyzer.stdout + analyzer.stderr, encoding="utf-8")
        if analyzer.returncode:
            raise RuntimeError(f"Exact judge analysis failed: {analyzer.stdout}{analyzer.stderr}")
    except (Exception, KeyboardInterrupt) as e:
        meta["errors"].append(f"{type(e).__name__}: {e}")
    finally:
        stop.set()
        if monitor:
            monitor.join(timeout=35)
            if monitor.is_alive():
                meta["errors"].append("stats monitor did not terminate")
            else:
                try:
                    # Read the kernel's cumulative high-water after all playback/analysis work.
                    sample, usage = stats_sample(docker, names["node"])
                    with Path(str(base) + ".samples.jsonl").open("a", encoding="utf-8") as samples, \
                            Path(str(base) + ".stats").open("a", encoding="utf-8") as legacy:
                        save_sample(samples, legacy, sample, usage)
                except Exception as e:
                    stat_errors.append(f"final cgroup peak: {e}")
        meta["errors"].extend(stat_errors)
        cleanup_ok = True
        for role in ("listener", "player", "node"):
            name = names[role]
            if name not in created:
                continue
            try:
                docker.call("stop", "--time", "12", name, timeout=20)
                state = docker.state(name)["State"]
                meta.setdefault("final_states", {})[role] = state
                if state.get("OOMKilled"):
                    meta["errors"].append(f"{role} OOMKilled")
                elif state["ExitCode"] == 137:
                    meta["errors"].append(f"{role} SIGKILL (OOMKilled=false)")
                if role == "node" and state["ExitCode"] not in (0, 143):
                    meta["errors"].append(f"unexpected node exit: {state['ExitCode']}")
                logs = docker.call("logs", name, check=False)
                Path(str(base) + f".{role}.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
                docker.call("rm", name)
            except Exception as e:
                cleanup_ok = False
                meta["errors"].append(f"cleanup {name}: {e}")
                docker.call("rm", "--force", name, check=False)
        meta["cleanup_ok"] = cleanup_ok
        write_json(str(base) + ".receipt.json", meta)
    return meta


def validate_receipt(meta, manifest, image, condition, repetition, domain):
    """Verify runtime receipts, not only the high-level successful-run booleans."""
    label = f"{image['role']}_{condition}_r{repetition}"
    bag, _, flags = CONDITIONS[condition]
    if (meta.get("label") != label or meta.get("image_id") != image["id"] or
            meta.get("detector_commit") != image["detector_commit"] or
            meta.get("play_args") != " ".join(flags) or meta.get("condition") != condition or
            meta.get("repetition") != repetition or meta.get("domain") != domain or
            meta.get("cpus") != manifest["cpus"] or meta.get("memory_limit") != manifest["memory_limit"] or
            meta.get("node_args") != manifest["node_args"]):
        raise ValueError("Run receipt differs from manifest / planned arguments or domain")
    provenance = meta.get("runtime_provenance", {})
    if (not image.get("expected_source_sha256_lf") or
            provenance.get("source_sha256_lf") != image["expected_source_sha256_lf"] or
            provenance.get("thread_env") != THREAD_ENV):
        raise ValueError("Missing/mismatched image source or single-thread provenance")
    for role in ("node", "listener", "player"):
        container = meta.get("containers", {}).get(role, {})
        labels = container.get("labels") or {}
        if (not container.get("id") or container.get("image") != image["id"] or
                container.get("NanoCpus") != int(manifest["cpus"] * 1e9) or
                container.get("Memory") != memory_limit_bytes(manifest["memory_limit"]) or
                container.get("MemorySwap") != container["Memory"] or
                labels.get("resense.startup.run") != manifest["run_id"] or
                labels.get("resense.startup.domain") != str(domain)):
            raise ValueError(f"Missing/mismatched {role} container quota/image/domain receipt")
        state = meta.get("final_states", {}).get(role, {})
        if (state.get("Running") is not False or state.get("OOMKilled") is not False or
                state.get("ExitCode") not in ((0, 143) if role == "node" else (0,))):
            raise ValueError(f"Missing/unclean {role} final process state")
    if meta["containers"]["player"].get("cmd") != ["ros2", "bag", "play", f"/data/{bag}", *flags]:
        raise ValueError("Actual player command is not the registered literal/README command")
    if manifest.get("data_storage"):
        storage = manifest["data_storage"]
        mounts = [m for m in meta["containers"]["player"].get("mounts", []) if m.get("Destination") == "/data"]
        expected_type = "volume" if storage["kind"] == "docker_volume" else "bind"
        if (meta.get("data_storage") != storage_identity(storage) or len(mounts) != 1 or
                mounts[0].get("Type") != expected_type or mounts[0].get("RW") is not False or
                (expected_type == "volume" and mounts[0].get("Name") != storage["source"])):
            raise ValueError("Player data mount differs from verified read-only storage provenance")


def analyze_directory(root):
    manifest = read_json(root / "manifest.json")
    images = manifest.get("images")
    conditions = manifest.get("conditions")
    if (manifest.get("schema") != "resense.s1.docker.v1" or
            not isinstance(images, list) or not all(isinstance(i, dict) for i in images) or
            [i.get("role", "") for i in images] not in (
                ["candidate"], ["baseline", "candidate"]) or
            not isinstance(conditions, list) or not conditions or
            any(not isinstance(c, str) or c not in CONDITIONS for c in conditions) or
            len(set(conditions)) != len(conditions) or
            not integer(manifest.get("repeats")) or not 1 <= manifest["repeats"] <= 3 or
            not finite(manifest.get("cpus")) or manifest["cpus"] <= 0 or
            not isinstance(manifest.get("memory_limit"), str) or
            not isinstance(manifest.get("node_args"), list) or
            not integer(manifest.get("domain_base")) or not 20 <= manifest["domain_base"] <= 69 or
            not isinstance(manifest.get("host"), dict) or
            not all(manifest.get("host", {}).get(k) for k in ("docker_version", "docker_info", "platform"))):
        raise ValueError("Incomplete/invalid manifest or Docker/host provenance")
    results = {i["role"]: [] for i in manifest["images"]}
    slot = 0
    for image in manifest["images"]:
        for condition in manifest["conditions"]:
            for repetition in range(1, manifest["repeats"] + 1):
                label = f"{image['role']}_{condition}_r{repetition}"
                base = root / "out/docker" / label
                try:
                    receipt_path = Path(str(base) + ".receipt.json")
                    # Preserve the ability to inspect attempts made by v1 before
                    # the analyzer-order repair; these lack final receipt files.
                    meta = read_json(receipt_path if receipt_path.exists() else str(base) + ".meta")
                    validate_receipt(meta, manifest, image, condition, repetition,
                                     manifest["domain_base"] + slot)
                    original_summary = read_json(str(base) + ".summary.json")
                    if original_summary.get("label") != label:
                        raise ValueError("Missing/invalid exact judge analysis")
                    inventory = manifest["bags"][CONDITIONS[condition][0]]
                    if inventory["expected_frames"] != CONDITIONS[condition][1]:
                        raise ValueError("Original expected frame count absent/wrong")
                    metrics = summarize_run(read_jsonl(str(base) + ".jsonl"), meta,
                                            read_jsonl(str(base) + ".samples.jsonl"), inventory)
                except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
                    metrics = {"complete": False, "errors": [f"{type(e).__name__}: {e}"]}
                results[image["role"]].append({"condition": condition, "repetition": repetition,
                                               "label": label, "metrics": metrics})
                slot += 1
    evaluations = {role: evaluate_matrix(rows, manifest["conditions"], manifest["repeats"])
                   for role, rows in results.items()}
    protocol_errors = []
    if manifest.get("cpus") != 4 or manifest.get("node_args"):
        protocol_errors.append("acceptance requires --cpus 4 and default node/launch policy")
    if not all(re.fullmatch(r"sha256:[0-9a-f]{64}", i.get("id", "")) and
               re.fullmatch(r"[0-9a-f]{40}", i.get("detector_commit", ""))
               for i in manifest["images"]):
        protocol_errors.append("immutable image/commit provenance missing")
    if len({i["id"] for i in manifest["images"]}) != len(manifest["images"]):
        protocol_errors.append("baseline and candidate must have different image IDs")
    storage = manifest.get("data_storage")
    if storage:
        try:
            if storage["kind"] == "docker_volume":
                validate_volume_storage(storage, manifest["bags"])
                if read_json(root / "bags_volume_verification.json") != storage:
                    raise ValueError("Volume verification receipt differs from manifest")
            elif storage["kind"] != "host_bind":
                raise ValueError("Unknown data storage kind")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
            protocol_errors.append(f"Invalid storage provenance: {e}")
    complete = all(r["metrics"]["complete"] for rows in results.values() for r in rows)
    same_runtime = "baseline" in results
    # Baseline need not pass S1, but its telemetry must be complete before any comparison.
    passed = not protocol_errors and complete and evaluations.get("candidate", {}).get("passed", False)
    return {"schema": "resense.s1.docker.v1", "run_id": manifest["run_id"],
            "passed": passed, "complete": complete, "protocol_errors": protocol_errors,
            "comparison_mode": "same_runtime_measured_AB" if same_runtime else "published_judge_different_runtime",
            "improvement_claim_allowed": same_runtime and passed,
            "published_comparison": PUBLISHED_COMPARISON, "evaluations": evaluations,
            "runs": results, "manifest": "manifest.json"}


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analyze", type=Path, help="Reparse a saved directory; no Docker, no writes")
    ap.add_argument("--image", help="Existing candidate image (resolved to immutable ID)")
    ap.add_argument("--detector-commit", help="Candidate image's committed node/launch revision")
    ap.add_argument("--baseline-image", help="Optional existing baseline image, measured first")
    ap.add_argument("--baseline-detector-commit")
    ap.add_argument("--bags", help="Original for_hackathon directory, mounted read-only")
    ap.add_argument("--bags-volume", help="Existing verified native Docker volume for playback; --bags remains host identity source")
    ap.add_argument("--out", type=Path, help="NEW output directory; refuses an existing path")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--cpus", type=float, default=4)
    ap.add_argument("--memory", default="4g", help="Hard per-container bound, swap disabled (default 4g)")
    ap.add_argument("--conditions", nargs="+", choices=tuple(CONDITIONS), default=list(CONDITIONS))
    ap.add_argument("--node-arg", action="append", default=[], help="Diagnostic launch override; disables acceptance")
    ap.add_argument("--ready-timeout", type=float, default=120)
    ap.add_argument("--player-timeout", type=float, default=180)
    ap.add_argument("--drain-timeout", type=float, default=40)
    return ap


def main(argv=None):
    ap = parser()
    args = ap.parse_args(argv)
    if args.analyze:
        try:
            result = analyze_directory(args.analyze.resolve())
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
            result = {"passed": False, "complete": False, "errors": [f"{type(e).__name__}: {e}"]}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result["passed"] else 1
    for name in ("image", "detector_commit", "bags", "out"):
        if not getattr(args, name):
            ap.error(f"--{name.replace('_', '-')} is required")
    if bool(args.baseline_image) != bool(args.baseline_detector_commit):
        ap.error("--baseline-image and --baseline-detector-commit must be supplied together")
    if (args.repeats < 1 or args.repeats > 3 or not finite(args.cpus) or args.cpus <= 0 or
            len(set(args.conditions)) != len(args.conditions) or
            any(not finite(t) or t <= 0 for t in (args.ready_timeout, args.player_timeout, args.drain_timeout))):
        ap.error("use 1..3 repeats, positive cpus, and distinct conditions")
    try:
        memory_limit_bytes(args.memory)
    except ValueError as e:
        ap.error(str(e))
    root = args.out.resolve()
    if root.exists():
        ap.error(f"Refusing to overwrite existing output: {root}")
    if not root.parent.is_dir():
        ap.error(f"Output parent directory must already exist: {root.parent}")
    # Preflight before creating any Docker resource or accepting any evidence.
    for name in ("listener.py", "analyze_chain.py", "chain.sh"):
        if (TOOLS / name).read_text() != (JUDGE / name).read_text():
            ap.error(f"Judge copy differs (LF-normalized): {name}")
    inventory_conditions = CONDITIONS if args.bags_volume else args.conditions
    bag_counts = {CONDITIONS[c][0]: CONDITIONS[c][1] for c in inventory_conditions}
    try:
        inventories = {bag: bag_inventory(Path(args.bags) / bag, count) for bag, count in bag_counts.items()}
    except (OSError, ValueError, sqlite3.Error) as e:
        print(json.dumps({"passed": False, "complete": False, "errors": [f"Bag preflight: {e}"]}, allow_nan=False))
        return 1
    root.mkdir()
    (root / "out/docker").mkdir(parents=True)
    shutil.copytree(TOOLS, root / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(__file__, root / "host_driver.py")
    # Normalize text with Python, so Windows CRLF checkouts need no shell rewriting.
    for path in (root / "tools").iterdir():
        if path.suffix in (".py", ".sh"):
            text = path.read_text(encoding="utf-8")
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.write(text)
    docker = Docker(root)
    manifest = None
    try:
        images = []
        for role, image, commit in (("baseline", args.baseline_image, args.baseline_detector_commit),
                                    ("candidate", args.image, args.detector_commit)):
            if image:
                images.append(dict(role=role, **image_info(docker, image, commit)))
        if len({i["id"] for i in images}) != len(images):
            raise ValueError("Baseline and candidate resolve to the same immutable image")
        run_id = uuid.uuid4().hex
        storage = (verify_volume(docker, root, images[-1]["id"], args.bags_volume, inventories, run_id)
                   if args.bags_volume else {"kind": "host_bind", "source": str(Path(args.bags).resolve())})
        info = strict_json(docker.call("info", "--format", "{{json .}}").stdout)
        # Host provenance excludes registry/proxy configuration and credentials.
        info_keys = ("ServerVersion", "OperatingSystem", "OSType", "Architecture", "NCPU", "MemTotal",
                     "CgroupDriver", "CgroupVersion", "Driver", "KernelVersion", "Name")
        manifest = {
            "schema": "resense.s1.docker.v1", "run_id": run_id,
            "driver_sha256": sha256_file(root / "host_driver.py"),
            "created_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv if argv is None else argv,
            "images": images, "conditions": args.conditions, "repeats": args.repeats,
            "cpus": args.cpus, "memory_limit": args.memory, "swap": "disabled",
            "node_args": args.node_arg, "bags": inventories,
            "data_storage": storage,
            "domain_base": 20 + int(run_id[:4], 16) % 50,
            "tools_sha256": {p.name: sha256_file(p) for p in (root / "tools").iterdir() if p.is_file()},
            "host": {"platform": platform.platform(), "python": sys.version,
                     "hostname": platform.node(), "logical_cpus": os.cpu_count(),
                     "machine": platform.machine(), "docker_context": docker.call("context", "show").stdout.strip(),
                     "docker_version": strict_json(docker.call("version", "--format", "{{json .}}").stdout),
                     "docker_info": {k: info.get(k) for k in info_keys}},
            "timeouts_s": {"ready": args.ready_timeout, "player": args.player_timeout, "drain": args.drain_timeout},
            "memory_definition": "MB=1e6 bytes. Gate=max(node-container cgroup memory high-water incl cache, "
            "node ru_maxrss MiB converted to MB). Docker stats is sampled cache-adjusted working set, reported separately.",
        }
        write_json(root / "manifest.json", manifest)
        slot = 0
        for image in images:
            for condition in args.conditions:
                for repetition in range(1, args.repeats + 1):
                    print(f"{image['role']} {condition} {repetition}/{args.repeats}", file=sys.stderr, flush=True)
                    meta = run_one(docker, root, manifest, image, condition, repetition,
                                   manifest["domain_base"] + slot, args)
                    slot += 1
                    if meta["errors"]:
                        raise RuntimeError(f"Incomplete run {meta['label']}: {meta['errors']}")
        result = analyze_directory(root)
    except (Exception, KeyboardInterrupt) as e:
        result = analyze_directory(root) if manifest and (root / "manifest.json").exists() else {
            "passed": False, "complete": False}
        result.setdefault("errors", []).append(f"{type(e).__name__}: {e}")
        result["passed"] = False
    write_json(root / "summary.json", result)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
