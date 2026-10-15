#!/usr/bin/env python3
"""Publish compact, hash-indexed S1 evidence from a finished external raw matrix.

No bag/JSONL streams are copied to the repository. Recomputes the strict verdict,
requires all twelve clean execution receipts, and refuses existing output paths.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import statistics
import sys

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from scripts import startup_acceptance as s1  # noqa: E402


def fmt(value, digits=3):
    if value is None:
        return "—"
    return str(value) if isinstance(value, int) else f"{value:.{digits}f}"


def indexed(path, root):
    return {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
            "sha256": s1.sha256_file(path)}


def copy_new(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, target.open("xb") as dst:
        shutil.copyfileobj(src, dst)


def excerpt(source, target):
    lines = source.read_text(encoding="utf-8").splitlines()
    chosen = lines if len(lines) <= 36 else lines[:18] + [
        f"[... {len(lines) - 30} source lines omitted; full source in raw root / hash index ...]"] + lines[-12:]
    with target.open("x", encoding="utf-8", newline="\n") as f:
        f.write(f"Source: {source}\nSHA256: {s1.sha256_file(source)}\nFull source lines: {len(lines)}\n\n")
        # Excerpts are presentation text, not exact raw copies. The source SHA
        # binds original bytes; trim line-end spaces so Git whitespace checks pass.
        f.write("\n".join(line.rstrip() for line in chosen) + "\n")


def publish(raw, attempts, out):
    manifest = s1.read_json(raw / "manifest.json")
    summary = s1.read_json(raw / "summary.json")
    recomputed = s1.analyze_directory(raw)
    if summary != recomputed:
        raise ValueError("Saved verdict differs from strict reanalysis")
    if len(summary["runs"]["candidate"]) != 12 or manifest["conditions"] != list(s1.CONDITIONS):
        raise ValueError("Publication requires the full registered 4 x 3 matrix")
    if summary["comparison_mode"] != "published_judge_different_runtime" or summary["improvement_claim_allowed"]:
        raise ValueError("This report is explicitly candidate-only")
    image = manifest["images"][0]
    observations, receipts = [], {}
    for slot, run in enumerate(summary["runs"]["candidate"]):
        label = run["label"]
        base = raw / "out/docker" / label
        receipt = s1.read_json(str(base) + ".receipt.json")
        s1.validate_receipt(receipt, manifest, image, run["condition"], run["repetition"],
                            manifest["domain_base"] + slot)
        if receipt.get("errors") or not receipt.get("cleanup_ok") or any(
                receipt.get(k) != 0 for k in ("player_exit", "listener_exit", "judge_analysis_exit")):
            raise ValueError(f"Execution did not finish cleanly: {label}")
        receipts[label] = receipt
        play_log = Path(str(base) + ".player.log").read_text(encoding="utf-8")
        observations.append({"label": label, "play_wall_s": receipt["t_end"] - receipt["t_play"],
                             "player_queue_starvation_warnings": play_log.count("Message queue starved"),
                             "strict_errors": run["metrics"]["errors"]})

    if out.exists() or not out.parent.is_dir():
        raise ValueError("Report output must be NEW, with an existing parent")
    roots = list(dict.fromkeys([p.resolve() for p in attempts] + [raw]))
    cleanup = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "runs": []}
    for root in roots:
        run_id = s1.read_json(root / "manifest.json")["run_id"]
        remaining = s1.command(["docker", "ps", "-aq", "--filter",
                                f"label=resense.startup.run={run_id}"]).stdout.split()
        cleanup["runs"].append({"raw_root": str(root), "run_id": run_id, "remaining_container_ids": remaining})
        if remaining:
            raise ValueError(f"Owned containers remain for {root}: {remaining}")
    cleanup["clean"] = True
    out.mkdir()
    for name in ("summary.json", "manifest.json"):
        copy_new(raw / name, out / name)
    launch = Path(str(raw) + ".launch.json")
    if launch.exists():
        copy_new(launch, out / "launch.json")
    s1.write_json(out / "cleanup.json", cleanup)
    s1.write_json(out / "runtime_observations.json", observations)
    medians = {}
    for condition, (_, expected, _) in s1.CONDITIONS.items():
        group = [r["metrics"] for r in summary["runs"]["candidate"] if r["condition"] == condition]
        metrics = {key: statistics.median(m[key] for m in group)
                   if all(s1.finite(m.get(key)) for m in group) else None for key in group[0]
                   if key not in ("complete", "errors", "frame_results", "decision_messages",
                                  "watchdog_results", "freshness_reasons")}
        metrics["frame_results"] = {d: statistics.median(m["frame_results"][d] for m in group)
                                    for d in s1.DECISIONS}
        metrics["expected_frames"] = expected
        medians[condition] = metrics
    s1.write_json(out / "condition_medians.json", medians)

    for condition in s1.CONDITIONS:
        label = f"candidate_{condition}_r1"
        base = raw / "out/docker" / label
        copy_new(Path(str(base) + ".receipt.json"), out / "selected" / (label + ".receipt.json"))
        for role in ("node", "player", "listener"):
            excerpt(Path(str(base) + f".{role}.log"), out / "selected" / (label + f".{role}.excerpt.log"))

    attempt_index = []
    for root in roots:
        old_manifest = s1.read_json(root / "manifest.json")
        old_summary = s1.analyze_directory(root)
        record = {"raw_root": str(root), "run_id": old_manifest["run_id"],
                  "included_in_final_medians": root == raw,
                  "saved_summary_exists": (root / "summary.json").exists(),
                  "strict_complete": old_summary["complete"], "passed": old_summary["passed"],
                  "receipt_count": len(list((root / "out/docker").glob("*.receipt.json"))),
                  "files": [indexed(p, root) for p in sorted(root.rglob("*")) if p.is_file()
                            and "__pycache__" not in p.parts]}
        record["sibling_files"] = [indexed(p, root.parent) for p in sorted(root.parent.glob(root.name + ".*"))
                                   if p.is_file()]
        attempt_index.append(record)
    s1.write_json(out / "raw_hash_index.json", {
        "hash": "SHA256 over exact bytes", "external_raw_parent": str(raw.parent),
        "final_raw_root": str(raw), "attempts": attempt_index,
        "note": "Only the final raw root supplies median measurements; failed/interrupted roots are preserved."})

    checks = summary["evaluations"]["candidate"]["conditions"]
    failed = [(condition, c) for condition, group in checks.items() for c in group["checks"] if not c["passed"]]
    incomplete = [r for r in summary["runs"]["candidate"] if not r["metrics"]["complete"]]
    host = manifest["host"]
    info = host["docker_info"]
    lines = [
        "# S1 real-Docker candidate measurements — 2026-10-15", "",
        f"**Acceptance: {'PASS' if summary['passed'] else 'FAIL'}** · **12/12 playback executions finished cleanly** · "
        f"strict evidence complete: **{str(summary['complete']).lower()}**.", "",
        "This is the user-selected Docker Desktop / WSL2 runtime, **not an exact four-vCPU host**. "
        "There is **no measured baseline and no causal improvement claim**. The saved JSON explicitly uses "
        "`published_judge_different_runtime` and `improvement_claim_allowed: false`.", "",
        "## Source and runtime", "",
        f"- Candidate: `{image['reference']}`; Docker immutable ID / repo digest: `{image['id']}`.",
        f"- Verified node/launch commit: `{image['detector_commit']}`. No node, launch, policy or core source was changed during measurement.",
        f"- Host: `{host['platform']}`; `{host['logical_cpus']}` host logical CPUs. "
        f"Docker daemon: **{info['NCPU']} logical CPUs**, **{fmt(info['MemTotal'] / 1024**3)} GiB** RAM "
        f"({info['MemTotal']:,} bytes), `{info['KernelVersion']}`, cgroup {info['CgroupVersion']}.",
        f"- Each container: **{manifest['cpus']:g} CPU quota**, `--memory {manifest['memory_limit']} "
        f"--memory-swap {manifest['memory_limit']}` (6 GiB, swap disabled). Separate node/player/listener cgroups; shared owned PID namespace, host UDP DDS, localhost-only disabled.",
        "- One OMP/OpenBLAS/MKL/NumExpr/vecLib thread; default replay node policy; UID/GID 1000 player.",
        "- Original read-only bags: **201** `doubleT_obstacle` clouds and **252** `roundT_doubleT` clouds. "
        "Bag SHA-256, all original header stamps, expected topics/counts and tool identities are in `manifest.json`.",
        f"- Driver SHA-256: `{manifest.get('driver_sha256')}`; exact snapshot is external `host_driver.py`.",
        f"- Final raw root: `{raw}`.",
        "- Exact judge listener/analyzer copies are retained; separate strict host analysis supplies the unrounded gate values.", "",
        "## Median acceptance checks", "",
        "Display values are rounded here only; `summary.json` stores unrounded comparisons. "
        "All three measured repetitions are retained, including incomplete-tail evidence; no favorable-run selection is used.", "",
        "| Condition | Metric | Median | Inclusive target | Numeric check | Strict group |",
        "|---|---|---:|---|---|---|",
    ]
    for condition, group in checks.items():
        for c in group["checks"]:
            lines.append(f"| {condition} | `{c['metric']}` | {fmt(c['median'])} | {c['operator']} {c['bound']} | "
                         f"{'PASS' if c['passed'] else 'FAIL'} | {'complete' if group['complete'] else 'INCOMPLETE'} |")
    lines += ["", "### Failed numeric targets", ""]
    lines += [f"- **{condition}** `{c['metric']}`: median {fmt(c['median'], 6)}, target {c['operator']} {c['bound']}."
              for condition, c in failed] or ["- None."]
    lines += ["", "### Strict completeness", ""]
    if incomplete:
        lines += [f"- `{r['label']}`: {'; '.join(r['metrics']['errors'])}." for r in incomplete]
        lines += ["", "A clean player exit/watchdog drain is not substituted for an absent final original bag-frame result. "
                  "The strict verdict remains incomplete/failed where that registered check is unmet."]
    else:
        lines += ["All twelve runs pass strict telemetry, expected-tail, provenance, process-state and stats checks."]
    lines += ["", "## Every repetition", "",
              "Fresh denominator is always every original bag frame (201/252), not only received results. "
              "STOP/FAULT below are **frame results only**; watchdogs are separately counted in JSON. "
              "Age is the node's DDS publication source age, including literal playback without `/clock`.", "",
              "| Condition / repeat | Results / expected | Fresh | STOP | FAULT | Age p50 / max (s) | First STOP lag (s) / distance (m) | Missing bag results | Strict complete |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in summary["runs"]["candidate"]:
        m = r["metrics"]
        lines.append(f"| {r['condition']} / {r['repetition']} | {m['frames_processed']}/{m['expected_frames']} | "
                     f"{m['fresh_frames']} | {m['frame_results']['STOP']} | {m['frame_results']['FAULT']} | "
                     f"{fmt(m['source_age_p50_s'])} / {fmt(m['source_age_max_s'])} | "
                     f"{fmt(m['first_stop_after_first_result_s'])} / {fmt(m['first_stop_dist'])} | "
                     f"{m['missing_bag_frame_results']} | {m['complete']} |")
    lines += ["", "## CPU, memory and playback wall time", "",
              "Memory is **decimal MB (bytes / 1,000,000)**. RSS is the node process `ru_maxrss` "
              "converted from its reported MiB; cgroup peak includes charged page cache and all node-container "
              "processes/probes. Docker working set is sampled/cache-adjusted and is **not** the peak gate. "
              "The gate is `max(RSS, cgroup peak)`. Docker CPU mean/max are percent / 100 and include idle "
              "preload/drain periods; node CPU is separate rolling telemetry.", "",
              "| Condition / repeat | Node cores p50 / max | Docker cores mean / max | RSS MB | Cgroup peak MB | Docker working-set peak MB | Memory gate MB | Player wall s | Queue-starvation warnings |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    by_label = {r["label"]: r for r in observations}
    for r in summary["runs"]["candidate"]:
        m, obs = r["metrics"], by_label[r["label"]]
        lines.append(f"| {r['condition']} / {r['repetition']} | {fmt(m['node_cpu_cores_p50'])} / {fmt(m['node_cpu_cores_max'])} | "
                     f"{fmt(m['docker_cpu_cores_mean'])} / {fmt(m['docker_cpu_cores_max'])} | {fmt(m['node_rss_peak_mb'])} | "
                     f"{fmt(m['container_cgroup_peak_mb'])} | {fmt(m['docker_working_set_peak_mb'])} | {fmt(m['memory_gate_mb'])} | "
                     f"{fmt(obs['play_wall_s'])} | {obs['player_queue_starvation_warnings']} |")
    lines += ["", "### Message loss", "",
              "| Condition / repeat | Missing status | Decision delta (status − decision) | Latency delta (frames − latency) | Node dropped / skipped |",
              "|---|---:|---:|---:|---:|"]
    for r in summary["runs"]["candidate"]:
        m = r["metrics"]
        lines.append(f"| {r['condition']} / {r['repetition']} | {m['missing_status_messages']} | "
                     f"{m['decision_message_delta']} | {m['latency_message_delta']} | {m['dropped']} / {m['skipped']} |")
    lines += ["", "Missing bag results and the node's inferred dropped/skipped telemetry are distinct measurements; "
              "the latter is not used to reduce expected frame counts or the fresh denominator.", "",
              "## Per-condition descriptive medians", "",
              "These summarize all three runs regardless of strict completeness; they do not override a failed gate.", "",
              "| Condition | Results | Fresh / expected | STOP | FAULT | Age p50 / max s | First STOP lag s / m | Memory gate MB |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for condition, m in medians.items():
        lines.append(f"| {condition} | {fmt(m['frames_processed'])} | {fmt(m['fresh_frames'])}/{m['expected_frames']} | "
                     f"{fmt(m['frame_results']['STOP'])} | {fmt(m['frame_results']['FAULT'])} | "
                     f"{fmt(m['source_age_p50_s'])} / {fmt(m['source_age_max_s'])} | "
                     f"{fmt(m['first_stop_after_first_result_s'])} / {fmt(m['first_stop_dist'])} | {fmt(m['memory_gate_mb'])} |")
    lines += ["",
              "## Infrastructure attempts (excluded from final medians)", "",
              "1. `attempt01_diagnostic`: graph-only readiness, original PID/localhost-only settings; literal player deadline (180 s), no data; cleanup SIGKILL, Docker OOM false.",
              "2. `attempt02_diagnostic`: same transport; clear README player exit 0, no data, drain timeout.",
              "3. `attempt03_transport_diagnostic`: repaired shared PID/UDP settings and actual-data readiness delivered frames; exact analyzer then exposed missing pre-analysis `.meta` input. Preserved incomplete.",
              "4. `attempt04_matrix`: seven clean receipts, terminal killed host process at 2,400 s during run eight. Explicit label-verified manual cleanup recorded; excluded in full.",
              "5. `attempt05_matrix`: fresh detached full matrix; these twelve repetitions alone supply every median above.", "",
              "Repairs are harness-only: transport/process identity and actual-data readiness, pre-analysis immutable `.meta` "
              "+ final `.receipt.json`, actual nullable watchdog-counter schema, explicit SIGKILL/OOM attribution, and detached execution. "
              "No failed numeric target was tuned around. Filesystem caches were not cleared; no cold-cache or exact judge-host claim is made.", "",
              "Windows bind-mounted playback shows long preload/play wall times and queue-starvation warnings (table above). "
              "These are measured runtime observations, not evidence of isolated detector causality. A different-runtime historical "
              "judge table cannot establish a same-runtime improvement or regression caused by the node change.", "",
              "## Exact commands", "", "```powershell",
              "$python = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe'",
              "# From C:/Users/alikh/AppData/Local/Temp/opencode/rs-p1-start; choose another NEW --out to reproduce.",
              "& $python " + " ".join(["docs/evidence/node_startup_2026-10-15/docker_tools/launch_matrix.py", "--out", f"'{raw}'", "--",
                  "--image", image["reference"], "--detector-commit", image["detector_commit"], "--bags",
                  "'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/for_hackathon'",
                  "--repeats 3 --cpus 4 --memory 6g --player-timeout 600"]),
              f"& $python scripts/startup_acceptance.py --analyze '{raw}'",
              "& $python -m pytest -q tests/test_startup_acceptance.py",
              "& 'C:/Users/alikh/AppData/Local/Programs/Python/Python311/Scripts/ruff.exe' check scripts/startup_acceptance.py tests/test_startup_acceptance.py docs/evidence/node_startup_2026-10-15/docker_tools",
              "```", "",
              "The launcher returning successfully is not acceptance; strict reanalysis exits 1 for this failed matrix. "
              "`launch.json` retains the exact actually launched argument vector and driver hash.", "",
              "## Retained evidence / cleanup", "",
              "- `summary.json`: exact full strict result and all per-run metrics; `manifest.json`: exact runtime/image/bag/source provenance.",
              "- `selected/`: first repetition's full receipt per condition plus explicitly marked node/player/listener log excerpts, each identifying full source path and hash.",
              "- `runtime_observations.json`: every repetition's wall time, starvation warnings and strict errors.",
              "- `condition_medians.json`: descriptive median of each numeric metric over all three repetitions per condition.",
              "- `raw_hash_index.json`: SHA-256/size/path of every external attempt artifact and detached-launch sibling; failed and interrupted attempts are preserved.",
              "- `publication_hash_index.json`: exact-byte hashes for the compact committed report artifacts (excluding itself).",
              "- `cleanup.json`: Docker query for every attempt run ID found **no remaining owned containers**. Unrelated containers were not modified.", "",
              "Large raw listener/witness/stats/command JSONL streams and bags are **not copied into Git**. "
              "Full raw paths and hashes are retained; review the raw files locally before external archival/removal.", "",
              "## Outcome and remaining work", "",
              "This measurement answers S1 only on the selected runtime and the source/image named above. "
              "The failed targets remain open. Any later policy/runtime work needs separately authorized changes and a fresh registered matrix; "
              "the present result does not grant S1 completion or replace combined CI/release approval.", ""]
    with (out / "README.md").open("x", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    s1.write_json(out / "publication_hash_index.json", {
        "hash": "SHA256 over exact bytes; index excludes itself",
        "files": [indexed(p, out) for p in sorted(out.rglob("*")) if p.is_file()]})
    print(json.dumps({"out": str(out), "passed": summary["passed"], "strict_complete": summary["complete"],
                      "clean_executions": len(receipts), "failed_numeric_checks": len(failed),
                      "incomplete_runs": len(incomplete), "cleanup": cleanup["clean"]}, indent=2))


def verify(out):
    index = s1.read_json(out / "publication_hash_index.json")
    for item in index["files"]:
        path = out / item["path"]
        if path.stat().st_size != item["bytes"] or s1.sha256_file(path) != item["sha256"]:
            raise ValueError(f"Publication hash mismatch: {path}")
    raw_index = s1.read_json(out / "raw_hash_index.json")
    checked = 0
    for attempt in raw_index["attempts"]:
        root = Path(attempt["raw_root"])
        for item in attempt["files"]:
            path = root / item["path"]
            if path.stat().st_size != item["bytes"] or s1.sha256_file(path) != item["sha256"]:
                raise ValueError(f"Raw hash mismatch: {path}")
            checked += 1
        for item in attempt["sibling_files"]:
            path = root.parent / item["path"]
            if path.stat().st_size != item["bytes"] or s1.sha256_file(path) != item["sha256"]:
                raise ValueError(f"Launch sibling hash mismatch: {path}")
            checked += 1
    print(json.dumps({"verified": True, "publication_files": len(index["files"]), "external_files": checked}))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path)
    ap.add_argument("--attempts", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--verify", type=Path)
    a = ap.parse_args()
    if a.verify:
        verify(a.verify.resolve())
    elif a.raw and a.out:
        publish(a.raw.resolve(), a.attempts, a.out.resolve())
    else:
        ap.error("use --raw --out [--attempts ...] or --verify")


if __name__ == "__main__":
    main()
