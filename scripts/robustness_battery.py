#!/usr/bin/env python3
"""Standing X3 battery using the unmodified 13 October judge probe.

Example: python scripts/robustness_battery.py --repo <detector checkout>
  --cache <node-decoded root> --out <new summary.json> -j 2
  [--reference <previous summary.json>] [--judge-reference]

Exit 0: complete measurement (MEASURED without reference), or passing comparison.
Exit 1: regression / judge discrepancy. Exit 2: invalid or incomplete evidence.
The output and its .raw directory must not exist. See the committed X3 protocol.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "docs/evidence/judgement_2026-10-13/scripts"
SCHEMA = "resense-robustness-battery-v1"
BAGS = {"squareT_platform_squareT_switch": 877, "doubleT_obstacle": 201,
        "roundT_squareT_pressureGate_squareT": 545, "cloud_with_fake_obj": 1510}
VARIANTS = {
    "nominal": [], "pitch_p2": ["--pitch", "2"], "pitch_m2": ["--pitch", "-2"],
    "roll_p2": ["--roll", "2"], "hz5": ["--every", "2"],
    "drop30_s1": ["--drop", "0.3"], "drop30_s2": ["--drop", "0.3"],
    "drop30_s3": ["--drop", "0.3"], "drop30_judge7": ["--drop", "0.3"],
    "dedup": ["--dedup"],
}
RECORD_KEYS = set("i bag_t stamp frame_id topic decision obstacle warning nearest clear level dlevel "
                  "msgs monitored rail_lock dets warns n_points decode_ms detect_ms total_ms "
                  "track_center curv mount mount_h ego".split())


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_new(path, value):
    with open(path, "x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def protocol():
    return {"schema": SCHEMA, "variants": VARIANTS, "seed_rule": "s1=1,s2=2,s3=3,otherwise=7",
            "episodes": "STOP transitions in processed order, including the first processed frame",
            "matching": "judge score_objects: plausible nonzero labels, distance + lateral bbox match",
            "acceptance": {"extra_false_stop_episodes": 1, "lost_positive_stop_rows": 2},
            "scripts": {n: sha256(JUDGE / n) for n in
                        ("probe.py", "judge_runner.py", "range_test.py", "score_objects.py")},
            "driver_sha256": sha256(__file__)}


def cache_meta(cache, expected):
    meta = read_json(cache / "meta.json")
    files = sorted(cache.glob("f_*.npz"))
    if len(meta) != expected or [p.name for p in files] != [f"f_{i:05d}.npz" for i in range(expected)]:
        raise ValueError(f"incomplete or extra node cache: {cache}")
    for i, m in enumerate(meta):
        if m["i"] != i or not {"has_ring", "n_raw", "n_near", "topic", "frame_id"} <= m.keys():
            raise ValueError(f"invalid cache metadata: {cache}/{i}")
        if not all(math.isfinite(m[k]) for k in ("stamp", "bag_t")):
            raise ValueError("nonfinite input stamp")
        if i and m["stamp"] <= meta[i - 1]["stamp"]:
            raise ValueError("node cache stamps not strictly increasing")
    return meta, files


def source_info(cache, count):
    meta, files = cache_meta(cache, count)
    inventory = [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files]
    return {"path": str(cache), "frames": len(meta), "meta_sha256": sha256(cache / "meta.json"),
            "payload_sha256": hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest(),
            "files": inventory}


def load_probe():
    sys.path.insert(0, str(JUDGE))
    spec = importlib.util.spec_from_file_location("x3_judge_probe", JUDGE / "probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return probe


def identity(repo):
    import resense
    from resense import _native

    actual = Path(resense.__file__).resolve()
    if actual.parent != repo / "resense":
        raise ValueError(f"wrong resense import: {actual}")
    paths = ["resense", "native", "configs", "setup.py", "pyproject.toml",
             "ros2_ws/src/resense_ros/config"]
    dirty = git(repo, "diff", "HEAD", "--", *paths)
    if dirty:
        raise ValueError("tracked detector changes are not committed")
    if not _native.enabled():
        raise ValueError(f"native runtime required: {_native.status()}")
    binaries = list((repo / "resense").glob("*resense_native.*"))
    return {"repo": str(repo), "commit": git(repo, "rev-parse", "HEAD"),
            "version": resense.__version__, "import": str(actual), "native": _native.status(),
            "native_binaries": {str(p): sha256(p) for p in binaries if p.suffix in (".pyd", ".so")},
            "config_sha256": sha256(repo / "configs/default.yaml"),
            "source_tree": git(repo, "ls-tree", "-r", "HEAD", "--", *paths)}


def worker(job_path):
    job = read_json(job_path)
    repo = Path(job["repo"]).resolve()
    # Script directory is scripts/, so explicitly put the selected detector first.
    sys.path.insert(0, str(repo))
    ident = identity(repo)
    probe = load_probe()
    original_rng = probe.np.random.default_rng
    # probe.py has a fixed seed 7. Only substitute that RNG construction, leaving
    # the judge's transforms, float32 arithmetic, metadata and decision rule intact.
    probe.np.random.default_rng = lambda seed=7: original_rng(job["seed"])
    sys.argv = [str(JUDGE / "probe.py"), job["cache"], job["prefix"], *job["args"]]
    t0 = time.monotonic()
    try:
        probe.main()
    finally:
        probe.np.random.default_rng = original_rng
    write_new(job["prefix"] + ".complete.json", {"identity": ident, "wall_s": time.monotonic() - t0})


def checked_rows(path, meta, every=1):
    """Fail closed: no silent zip truncation, corrupt/duplicate rows or decision inconsistencies."""
    rows = []
    expected = meta[::every]
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f):
            r = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            if n >= len(expected) or not RECORD_KEYS <= r.keys():
                raise ValueError(f"extra or incomplete raw row {path}:{n}")
            m = expected[n]
            for k in ("i", "frame_id", "topic"):
                if r[k] != m[k]:
                    raise ValueError(f"raw {k} mismatch {path}:{n}")
            if any(r[k] != round(m[k], 4) for k in ("stamp", "bag_t")):
                raise ValueError(f"raw timestamp mismatch {path}:{n}")
            if (r["decision"] not in ("GO", "CAUTION", "STOP", "FAULT")
                    or type(r["obstacle"]) is not bool or type(r["warning"]) is not bool
                    or r["obstacle"] != (r["decision"] == "STOP")
                    or not isinstance(r["dets"], list) or not isinstance(r["warns"], list)
                    or bool(r["dets"]) != r["obstacle"]):
                raise ValueError(f"inconsistent raw decision {path}:{n}")
            expected_decision = ("STOP" if r["obstacle"] else "FAULT" if r["level"] == "error"
                                 else "CAUTION" if r["warning"] or r["dlevel"] == "warn" else "GO")
            if (r["decision"] != expected_decision or type(r["n_points"]) is not int or r["n_points"] < 0
                    or not all(isinstance(r[k], (int, float)) and math.isfinite(r[k]) and r[k] >= 0
                               for k in ("decode_ms", "detect_ms", "total_ms", "clear"))):
                raise ValueError(f"inconsistent raw telemetry {path}:{n}")
            for d in r["dets"] + r["warns"]:
                if (not {"d", "lat", "c", "size", "zone", "kind", "reason", "conf", "n", "age", "hmin"} <= d.keys()
                        or len(d["c"]) != 3 or len(d["size"]) != 3
                        or not all(math.isfinite(v) for v in [d["d"], d["lat"], *d["c"], *d["size"]])):
                    raise ValueError(f"incomplete detection {path}:{n}")
            rows.append(r)
    if len(rows) != len(expected):
        raise ValueError(f"incomplete raw report {path}: {len(rows)}/{len(expected)}")
    return rows


def episodes(flags):
    count, previous = 0, False
    for flag in flags:
        count += bool(flag) and not previous
        previous = bool(flag)
    return count


def matches(d, o):
    length, width = (o.get("size") or [0.5, 0.5, 0.5])[:2]
    y = (sum(p[1] for p in o["bbox"]) / 2 if "bbox" in o
         else o.get("lateral_sensor", o.get("lateral", 0.0)))
    return (abs(d["d"] - o["distance"]) <= max(2, 0.03 * o["distance"]) + length / 2
            and abs(d["c"][1] - y) <= 1 + width / 2)


def summarize(rows, labels=None):
    flags = [r["decision"] == "STOP" for r in rows]
    out = {"frames": len(rows), "stop_frames": sum(flags), "stop_episodes": episodes(flags),
           "first_stop_frame": next((r["i"] for r in rows if r["obstacle"]), None),
           "decisions": {k: sum(r["decision"] == k for r in rows) for k in ("GO", "CAUTION", "STOP", "FAULT")}}
    if labels is None:
        out["false_stop_episodes"] = out["stop_episodes"]
        return out
    objects, outside, unmatched, hit_indices = {}, [], [], {}
    for r in rows:
        used, outside_hit = set(), False
        for o in labels.get(f"{r['i']:05d}", []):
            if o.get("n_points", 1) == 0:
                continue
            hit = {j for j, d in enumerate(r["dets"]) if matches(d, o)}
            used.update(hit)  # same unmatched rule as score_objects.py, including implausible rows
            if not o.get("plausible", True):
                continue
            name = o.get("label", o.get("name"))
            p = objects.setdefault(name, {"in_gauge": bool(o["in_gauge"]), "visible_rows": 0,
                                          "stop_rows": 0, "first_stop_m": None, "first_stop_frame": None})
            if p["in_gauge"] != bool(o["in_gauge"]):
                raise ValueError(f"label intent changes: {name}")
            p["visible_rows"] += 1
            p["stop_rows"] += bool(hit)
            if hit:
                hit_indices.setdefault(name, set()).add(r["i"])
            if hit and p["first_stop_frame"] is None:
                p.update(first_stop_frame=r["i"], first_stop_m=o["distance"])
            outside_hit |= bool(hit) and not o["in_gauge"]
        outside.append(outside_hit)
        unmatched.append(r["obstacle"] and bool(r["dets"]) and not used)
    for name, p in objects.items():
        p["stop_episodes"] = episodes(r["i"] in hit_indices.get(name, set()) for r in rows)
    out.update(objects=objects, outside_false_stop_frames=sum(outside),
               outside_false_stop_episodes=episodes(outside), unmatched_stop_frames=sum(unmatched),
               unmatched_stop_episodes=episodes(unmatched))
    return out


def compare_metrics(base, current):
    rows = []

    def add(key, b, c, direction, tolerance):
        delta = c - b
        worse = max(0, delta * direction)
        rows.append({"metric": key, "baseline": b, "current": c, "delta": delta,
                     "absolute_delta": abs(delta), "worse_by": worse, "tolerance": tolerance,
                     "passed": worse <= tolerance})

    add("frames", base["frames"], current["frames"], 1, 0)
    rows[-1]["passed"] = base["frames"] == current["frames"]
    if "objects" not in base:
        add("false_stop_episodes", base["false_stop_episodes"], current["false_stop_episodes"], 1, 1)
    else:
        if set(base["objects"]) != set(current["objects"]):
            raise ValueError("reference/current object inventories differ")
        # Positive global STOP is also required: the historical doubleT acceptance row.
        if any(p["in_gauge"] for p in base["objects"].values()):
            add("positive_recording.stop_frames", base["stop_frames"], current["stop_frames"], -1, 2)
        for name, b in base["objects"].items():
            c = current["objects"][name]
            if b["in_gauge"] != c["in_gauge"] or b["visible_rows"] != c["visible_rows"]:
                raise ValueError("reference/current label denominator or intent differs")
            if b["in_gauge"]:
                add(f"objects.{name}.stop_rows", b["stop_rows"], c["stop_rows"], -1, 2)
            else:
                add(f"objects.{name}.false_stop_episodes", b["stop_episodes"], c["stop_episodes"], 1, 1)
        for key in ("outside_false_stop_episodes", "unmatched_stop_episodes"):
            add(key, base[key], current[key], 1, 1)
    return rows


def judge_comparison(entries):
    expected = {"squareT_platform_squareT_switch": ("stop_episodes", {
        "nominal": 3, "pitch_p2": 4, "pitch_m2": 7, "roll_p2": 7, "hz5": 9, "drop30_judge7": 14,
        "dedup": 3}), "doubleT_obstacle": ("stop_frames", {
        "nominal": 193, "pitch_p2": 192, "hz5": 95, "drop30_judge7": 154, "dedup": 189}),
        "roundT_squareT_pressureGate_squareT": ("stop_episodes", dict.fromkeys(VARIANTS, 0))}
    rows = []
    for bag, (metric, variants) in expected.items():
        for variant, value in variants.items():
            actual = entries[f"{bag}/{variant}"]["metrics"][metric]
            rows.append({"case": f"{bag}/{variant}", "metric": metric, "expected": value,
                         "actual": actual, "absolute_delta": abs(actual - value),
                         "passed": abs(actual - value) <= 1})
    return {"passed": all(r["passed"] for r in rows), "rows": rows}


def environment(repo, adapter):
    env = dict(os.environ, RESENSE_REPO=str(repo), OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    env["PYTHONPATH"] = os.pathsep.join([str(repo), *([str(adapter)] if adapter else [])])
    return env


def validated_entries(report, cache, repo):
    """Re-read raw evidence, not just the claimed summary, when accepting a reference."""
    wanted = {f"{b}/{v}" for b in BAGS for v in VARIANTS}
    if set(report["entries"]) != wanted or report["errors"]:
        raise ValueError("incomplete reference run")
    for key, entry in report["entries"].items():
        bag, variant = key.split("/")
        meta, _ = cache_meta(cache / bag, BAGS[bag])
        raw = Path(entry["raw_path"])
        if sha256(raw) != entry["raw_sha256"]:
            raise ValueError(f"reference raw hash differs: {key}")
        completion = read_json(raw.with_suffix(".complete.json"))
        if completion["identity"] != report["evaluation"]:
            raise ValueError("reference worker identity mismatch")
        labels = read_json(repo / f"labels/{bag}.json") if bag in ("doubleT_obstacle", "cloud_with_fake_obj") else None
        actual = summarize(checked_rows(raw, meta, 2 if variant == "hz5" else 1), labels)
        if actual != entry["metrics"]:
            raise ValueError(f"reference summary disagrees with raw: {key}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=ROOT)
    ap.add_argument("--cache", type=Path, default=Path(os.environ.get("RESENSE_DECODED", "/data/decoded")))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("-j", "--jobs", type=int, choices=(1, 2), default=2)
    ap.add_argument("--reference", type=Path)
    ap.add_argument("--judge-reference", action="store_true")
    ap.add_argument("--resource-adapter", type=Path, help="Windows scratch directory containing resource.py")
    a = ap.parse_args(argv)
    repo, cache, out = a.repo.resolve(), a.cache.resolve(), a.out.resolve()
    if out.exists() or out.with_suffix(".raw").exists():
        ap.error("output / raw directory already exists; choose a fresh --out")
    if not out.parent.is_dir():
        ap.error("output parent must already exist")
    t0 = time.monotonic()
    report = {"schema": SCHEMA, "created": datetime.now(timezone.utc).isoformat(), "protocol": protocol(),
              "runtime": {"platform": platform.platform(), "python": sys.version, "executable": sys.executable,
                          "jobs": a.jobs, "threads": 1, "resource_adapter": str(a.resource_adapter)},
              "harness_commit": git(ROOT, "rev-parse", "HEAD"), "sources": {}, "entries": {}, "errors": []}
    try:
        for bag, count in BAGS.items():
            report["sources"][bag] = source_info(cache / bag, count)
        report["labels"] = {b: sha256(repo / f"labels/{b}.json") for b in ("doubleT_obstacle", "cloud_with_fake_obj")}
        reference = read_json(a.reference) if a.reference else None
        if reference:
            if (reference["protocol"] != report["protocol"] or reference["labels"] != report["labels"]
                    or any({k: v for k, v in reference["sources"][b].items() if k != "path"}
                           != {k: v for k, v in s.items() if k != "path"} for b, s in report["sources"].items())):
                raise ValueError("reference protocol, labels or source identities differ")
            validated_entries(reference, cache, repo)
            report["reference"] = {"path": str(a.reference.resolve()), "sha256": sha256(a.reference),
                                   "evaluation": reference["evaluation"]}
        raw_dir = out.with_suffix(".raw")
        raw_dir.mkdir()  # exclusive reservation; probe's w-mode is confined to fresh variant dirs
        jobs = []
        for bag in BAGS:
            for variant, args in VARIANTS.items():
                folder = raw_dir / bag / variant
                folder.mkdir(parents=True)
                job = {"repo": str(repo), "cache": str(cache / bag), "prefix": str(folder / "probe"),
                       "args": args, "seed": int(variant[-1]) if variant.startswith("drop30_s") else 7}
                plan = folder / "job.json"
                write_new(plan, job)
                jobs.append((f"{bag}/{variant}", plan, job))

        def run(item):
            key, plan, job = item
            with open(plan.parent / "process.log", "x", encoding="utf-8") as log:
                result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", str(plan)],
                                        cwd=repo, env=environment(repo, a.resource_adapter), stdout=log,
                                        stderr=subprocess.STDOUT)
            if result.returncode:
                return key, None, f"exit {result.returncode}: {plan.parent / 'process.log'}"
            try:
                bag, variant = key.split("/")
                meta, _ = cache_meta(cache / bag, BAGS[bag])
                raw = Path(job["prefix"] + ".jsonl")
                complete = read_json(job["prefix"] + ".complete.json")
                labels = read_json(repo / f"labels/{bag}.json") if bag in report["labels"] else None
                metrics = summarize(checked_rows(raw, meta, 2 if variant == "hz5" else 1), labels)
                entry = {"raw_path": str(raw), "raw_sha256": sha256(raw), "metrics": metrics,
                         "wall_s": complete["wall_s"], "identity": complete["identity"]}
                return key, entry, None
            except (OSError, ValueError, KeyError, TypeError) as exc:
                return key, None, str(exc)

        with ThreadPoolExecutor(max_workers=a.jobs) as pool:
            for key, entry, error in pool.map(run, jobs):
                if error:
                    report["errors"].append({"case": key, "error": error})
                else:
                    ident = entry.pop("identity")
                    if report.setdefault("evaluation", ident) != ident:
                        report["errors"].append({"case": key, "error": "worker evaluation identities differ"})
                    report["entries"][key] = entry
                    print(key, entry["metrics"]["stop_frames"], entry["metrics"]["stop_episodes"], flush=True)
        if report["errors"] or len(report["entries"]) != len(jobs):
            raise ValueError("incomplete battery; see errors / process logs")
        if a.judge_reference:
            report["judge_reproduction"] = judge_comparison(report["entries"])
        if reference:
            comparisons = {key: compare_metrics(reference["entries"][key]["metrics"], e["metrics"])
                           for key, e in report["entries"].items()}
            report["comparison"] = {"passed": all(r["passed"] for rs in comparisons.values() for r in rs),
                                    "cases": comparisons}
        passed = all(report[k]["passed"] for k in ("judge_reproduction", "comparison") if k in report)
        report["status"] = ("PASS" if reference else "MEASURED") if passed else "FAIL"
        code = 0 if passed else 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report["errors"].append({"error": str(exc)})
        report["status"], code = "ERROR", 2
    report["wall_s"] = round(time.monotonic() - t0, 2)
    write_new(out, report)
    print(report["status"], out, flush=True)
    return code


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(sys.argv[2])
    else:
        sys.exit(main())
