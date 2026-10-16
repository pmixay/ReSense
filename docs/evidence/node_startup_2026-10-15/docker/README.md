# S1 real-Docker candidate measurements — 2026-10-15

**Acceptance: FAIL** · **12/12 playback executions finished cleanly** · strict evidence complete: **false**.

This is the user-selected Docker Desktop / WSL2 runtime, **not an exact four-vCPU host**. There is **no measured baseline and no causal improvement claim**. The saved JSON explicitly uses `published_judge_different_runtime` and `improvement_claim_allowed: false`.

## Source and runtime

- Candidate: `resense:p1-start-2026-10-15`; Docker immutable ID / repo digest: `sha256:70916f04ffb451922eb860afaa3f5ee185e2f13d6f0ae29ded97b5bff5857a52`.
- Verified node/launch commit: `1eed357a82ac4bd8b5a33ff8d3902c8190b2edec`. No node, launch, policy or core source was changed during measurement.
- Host: `Windows-10-10.0.26200-SP0`; `12` host logical CPUs. Docker daemon: **12 logical CPUs**, **6.698 GiB** RAM (7,192,399,872 bytes), `6.6.87.2-microsoft-standard-WSL2`, cgroup 2.
- Each container: **4 CPU quota**, `--memory 6g --memory-swap 6g` (6 GiB, swap disabled). Separate node/player/listener cgroups; shared owned PID namespace, host UDP DDS, localhost-only disabled.
- One OMP/OpenBLAS/MKL/NumExpr/vecLib thread; default replay node policy; UID/GID 1000 player.
- Original read-only bags: **201** `doubleT_obstacle` clouds and **252** `roundT_doubleT` clouds. Bag SHA-256, all original header stamps, expected topics/counts and tool identities are in `manifest.json`.
- Driver SHA-256: `3aacedb1a02fe7287ed8b606da3ef5d8313887fed2712ab3e7504e582ed59e78`; exact snapshot is external `host_driver.py`.
- Final raw root: `C:\Users\alikh\AppData\Local\Temp\opencode\resense-p1-runs-2026-10-15\attempt05_matrix`.
- Exact judge listener/analyzer copies are retained; separate strict host analysis supplies the unrounded gate values.

## Median acceptance checks

Display values are rounded here only; `summary.json` stores unrounded comparisons. All three measured repetitions are retained, including incomplete-tail evidence; no favorable-run selection is used.

| Condition | Metric | Median | Inclusive target | Numeric check | Strict group |
|---|---|---:|---|---|---|
| obstacle_literal | `fresh_fraction` | 0.000 | >= 0.8 | FAIL | INCOMPLETE |
| obstacle_literal | `source_age_p50_s` | 1.111 | <= 0.5 | FAIL | INCOMPLETE |
| obstacle_literal | `memory_gate_mb` | 797.757 | <= 1200 | PASS | INCOMPLETE |
| obstacle_literal | `first_stop_dist` | 55.630 | >= 55 | PASS | INCOMPLETE |
| obstacle_literal | `first_stop_dist` | 55.630 | <= 57 | PASS | INCOMPLETE |
| obstacle_readme | `fresh_frames` | 0 | >= 180 | FAIL | INCOMPLETE |
| obstacle_readme | `source_age_max_s` | 1.449 | <= 0.6 | FAIL | INCOMPLETE |
| obstacle_readme | `STOP` | 190 | >= 185 | PASS | INCOMPLETE |
| obstacle_readme | `first_stop_after_first_result_s` | 2.571 | <= 1.2 | FAIL | INCOMPLETE |
| clear_literal | `FAULT` | 31 | <= 10 | FAIL | INCOMPLETE |
| clear_readme | `fresh_frames` | 227 | >= 242 | FAIL | complete |

### Failed numeric targets

- **obstacle_literal** `fresh_fraction`: median 0.000000, target >= 0.8.
- **obstacle_literal** `source_age_p50_s`: median 1.110989, target <= 0.5.
- **obstacle_readme** `fresh_frames`: median 0, target >= 180.
- **obstacle_readme** `source_age_max_s`: median 1.449263, target <= 0.6.
- **obstacle_readme** `first_stop_after_first_result_s`: median 2.571050, target <= 1.2.
- **clear_literal** `FAULT`: median 31, target <= 10.
- **clear_readme** `fresh_frames`: median 227, target >= 242.

### Strict completeness

- `candidate_obstacle_literal_r1`: last expected bag frame missing (incomplete drain).
- `candidate_obstacle_readme_r1`: row 940: invalid/non-progressing arrival clock; last expected bag frame missing (incomplete drain).
- `candidate_obstacle_readme_r2`: last expected bag frame missing (incomplete drain).
- `candidate_obstacle_readme_r3`: last expected bag frame missing (incomplete drain).
- `candidate_clear_literal_r1`: last expected bag frame missing (incomplete drain).
- `candidate_clear_literal_r3`: last expected bag frame missing (incomplete drain).

A clean player exit/watchdog drain is not substituted for an absent final original bag-frame result. The strict verdict remains incomplete/failed where that registered check is unmet.

## Every repetition

Fresh denominator is always every original bag frame (201/252), not only received results. STOP/FAULT below are **frame results only**; watchdogs are separately counted in JSON. Age is the node's DDS publication source age, including literal playback without `/clock`.

| Condition / repeat | Results / expected | Fresh | STOP | FAULT | Age p50 / max (s) | First STOP lag (s) / distance (m) | Missing bag results | Strict complete |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| obstacle_literal / 1 | 44/201 | 0 | 42 | 2 | 1.111 / 2.697 | 0.384 / 55.630 | 157 | False |
| obstacle_literal / 2 | 36/201 | 0 | 34 | 2 | 0.994 / 1.430 | 0.417 / 55.810 | 165 | True |
| obstacle_literal / 3 | 47/201 | 0 | 45 | 2 | 1.223 / 2.285 | 0.464 / 55.570 | 154 | True |
| obstacle_readme / 1 | 196/201 | 0 | 190 | 6 | 0.161 / 1.449 | 2.571 / 55.540 | 5 | False |
| obstacle_readme / 2 | 196/201 | 2 | 190 | 5 | 0.158 / 0.886 | 1.126 / 55.540 | 5 | False |
| obstacle_readme / 3 | 195/201 | 0 | 189 | 6 | 0.161 / 1.523 | 4.154 / 55.540 | 6 | False |
| clear_literal / 1 | 31/252 | 0 | 0 | 31 | 0.290 / 0.702 | — / — | 221 | False |
| clear_literal / 2 | 33/252 | 0 | 0 | 33 | 0.452 / 1.141 | — / — | 219 | True |
| clear_literal / 3 | 31/252 | 0 | 0 | 31 | 0.658 / 1.347 | — / — | 221 | False |
| clear_readme / 1 | 252/252 | 224 | 0 | 25 | 0.047 / 0.448 | — / — | 0 | True |
| clear_readme / 2 | 252/252 | 227 | 0 | 22 | 0.046 / 1.343 | — / — | 0 | True |
| clear_readme / 3 | 252/252 | 229 | 0 | 20 | 0.045 / 1.297 | — / — | 0 | True |

## CPU, memory and playback wall time

Memory is **decimal MB (bytes / 1,000,000)**. RSS is the node process `ru_maxrss` converted from its reported MiB; cgroup peak includes charged page cache and all node-container processes/probes. Docker working set is sampled/cache-adjusted and is **not** the peak gate. The gate is `max(RSS, cgroup peak)`. Docker CPU mean/max are percent / 100 and include idle preload/drain periods; node CPU is separate rolling telemetry.

| Condition / repeat | Node cores p50 / max | Docker cores mean / max | RSS MB | Cgroup peak MB | Docker working-set peak MB | Memory gate MB | Player wall s | Queue-starvation warnings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| obstacle_literal / 1 | 1.410 / 1.440 | 0.053 / 1.545 | 784.335 | 776.823 | 769.760 | 784.335 | 369.388 | 0 |
| obstacle_literal / 2 | 1.355 / 1.410 | 0.052 / 1.390 | 827.222 | 819.536 | 800.483 | 827.222 | 352.787 | 0 |
| obstacle_literal / 3 | 1.410 / 1.420 | 0.057 / 1.448 | 797.757 | 790.594 | 784.545 | 797.757 | 356.644 | 0 |
| obstacle_readme / 1 | 0.100 / 1.010 | 0.123 / 1.013 | 517.892 | 503.308 | 391.119 | 517.892 | 339.168 | 315 |
| obstacle_readme / 2 | 0.180 / 0.710 | 0.169 / 1.007 | 505.623 | 490.607 | 389.441 | 505.623 | 225.628 | 209 |
| obstacle_readme / 3 | 0.110 / 0.300 | 0.145 / 1.002 | 626.105 | 610.869 | 430.650 | 626.105 | 294.027 | 273 |
| clear_literal / 1 | 0.490 / 1.370 | 0.067 / 1.363 | 345.716 | 348.594 | 330.197 | 348.594 | 150.666 | 0 |
| clear_literal / 2 | 1.420 / 1.420 | 0.093 / 1.524 | 339.214 | 340.959 | 322.961 | 340.959 | 96.200 | 0 |
| clear_literal / 3 | 0.500 / 1.420 | 0.085 / 1.512 | 337.641 | 339.595 | 322.227 | 339.595 | 96.087 | 0 |
| clear_readme / 1 | 0.150 / 0.450 | 0.166 / 1.013 | 241.802 | 226.439 | 225.968 | 241.802 | 97.562 | 89 |
| clear_readme / 2 | 0.160 / 0.290 | 0.165 / 1.043 | 245.157 | 233.701 | 229.428 | 245.157 | 95.036 | 87 |
| clear_readme / 3 | 0.150 / 0.450 | 0.156 / 1.027 | 254.804 | 239.092 | 191.155 | 254.804 | 92.283 | 84 |

### Message loss

| Condition / repeat | Missing status | Decision delta (status − decision) | Latency delta (frames − latency) | Node dropped / skipped |
|---|---:|---:|---:|---:|
| obstacle_literal / 1 | 0 | 0 | 0 | 155 / 151 |
| obstacle_literal / 2 | 0 | 0 | 0 | 162 / 158 |
| obstacle_literal / 3 | 0 | 0 | 0 | 152 / 148 |
| obstacle_readme / 1 | 0 | 0 | 0 | 8 / 4 |
| obstacle_readme / 2 | 0 | 0 | 0 | 8 / 4 |
| obstacle_readme / 3 | 0 | 0 | 0 | 9 / 5 |
| clear_literal / 1 | 0 | 0 | 0 | 220 / 218 |
| clear_literal / 2 | 0 | 0 | 0 | 216 / 208 |
| clear_literal / 3 | 0 | 0 | 0 | 212 / 203 |
| clear_readme / 1 | 0 | 0 | 0 | 0 / 0 |
| clear_readme / 2 | 0 | 0 | 0 | 0 / 0 |
| clear_readme / 3 | 0 | 0 | 0 | 0 / 0 |

Missing bag results and the node's inferred dropped/skipped telemetry are distinct measurements; the latter is not used to reduce expected frame counts or the fresh denominator.

## Per-condition descriptive medians

These summarize all three runs regardless of strict completeness; they do not override a failed gate.

| Condition | Results | Fresh / expected | STOP | FAULT | Age p50 / max s | First STOP lag s / m | Memory gate MB |
|---|---:|---:|---:|---:|---:|---:|---:|
| obstacle_literal | 44 | 0/201 | 42 | 2 | 1.111 / 2.285 | 0.417 / 55.630 | 797.757 |
| obstacle_readme | 196 | 0/201 | 190 | 6 | 0.161 / 1.449 | 2.571 / 55.540 | 517.892 |
| clear_literal | 31 | 0/252 | 0 | 31 | 0.452 / 1.141 | — / — | 340.959 |
| clear_readme | 252 | 227/252 | 0 | 22 | 0.046 / 1.297 | — / — | 245.157 |

## Infrastructure attempts (excluded from final medians)

1. `attempt01_diagnostic`: graph-only readiness, original PID/localhost-only settings; literal player deadline (180 s), no data; cleanup SIGKILL, Docker OOM false.
2. `attempt02_diagnostic`: same transport; clear README player exit 0, no data, drain timeout.
3. `attempt03_transport_diagnostic`: repaired shared PID/UDP settings and actual-data readiness delivered frames; exact analyzer then exposed missing pre-analysis `.meta` input. Preserved incomplete.
4. `attempt04_matrix`: seven clean receipts, terminal killed host process at 2,400 s during run eight. Explicit label-verified manual cleanup recorded; excluded in full.
5. `attempt05_matrix`: fresh detached full matrix; these twelve repetitions alone supply every median above.

Repairs are harness-only: transport/process identity and actual-data readiness, pre-analysis immutable `.meta` + final `.receipt.json`, actual nullable watchdog-counter schema, explicit SIGKILL/OOM attribution, and detached execution. No failed numeric target was tuned around. Filesystem caches were not cleared; no cold-cache or exact judge-host claim is made.

Windows bind-mounted playback shows long preload/play wall times and queue-starvation warnings (table above). These are measured runtime observations, not evidence of isolated detector causality. A different-runtime historical judge table cannot establish a same-runtime improvement or regression caused by the node change.

## Exact commands

```powershell
$python = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe'
# From C:/Users/alikh/AppData/Local/Temp/opencode/rs-p1-start; choose another NEW --out to reproduce.
& $python docs/evidence/node_startup_2026-10-15/docker_tools/launch_matrix.py --out 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-p1-runs-2026-10-15\attempt05_matrix' -- --image resense:p1-start-2026-10-15 --detector-commit 1eed357a82ac4bd8b5a33ff8d3902c8190b2edec --bags 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/for_hackathon' --repeats 3 --cpus 4 --memory 6g --player-timeout 600
& $python scripts/startup_acceptance.py --analyze 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-p1-runs-2026-10-15\attempt05_matrix'
& $python -m pytest -q tests/test_startup_acceptance.py
& 'C:/Users/alikh/AppData/Local/Programs/Python/Python311/Scripts/ruff.exe' check scripts/startup_acceptance.py tests/test_startup_acceptance.py docs/evidence/node_startup_2026-10-15/docker_tools
```

The launcher returning successfully is not acceptance; strict reanalysis exits 1 for this failed matrix. `launch.json` retains the exact actually launched argument vector and driver hash.

## Retained evidence / cleanup

- `summary.json`: exact full strict result and all per-run metrics; `manifest.json`: exact runtime/image/bag/source provenance.
- `selected/`: first repetition's full receipt per condition plus explicitly marked node/player/listener log excerpts, each identifying full source path and hash.
- `runtime_observations.json`: every repetition's wall time, starvation warnings and strict errors.
- `condition_medians.json`: descriptive median of each numeric metric over all three repetitions per condition.
- `raw_hash_index.json`: SHA-256/size/path of every external attempt artifact and detached-launch sibling; failed and interrupted attempts are preserved.
- `publication_hash_index.json`: exact-byte hashes for the compact committed report artifacts (excluding itself).
- `cleanup.json`: Docker query for every attempt run ID found **no remaining owned containers**. Unrelated containers were not modified.

Large raw listener/witness/stats/command JSONL streams and bags are **not copied into Git**. Full raw paths and hashes are retained; review the raw files locally before external archival/removal.

## Outcome and remaining work

This measurement answers S1 only on the selected runtime and the source/image named above. The failed targets remain open. Any later policy/runtime work needs separately authorized changes and a fresh registered matrix; the present result does not grant S1 completion or replace combined CI/release approval.
