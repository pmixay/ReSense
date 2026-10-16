# S1 real-Docker candidate measurements — 2026-10-15

**Acceptance: FAIL** · **12/12 playback executions finished cleanly** · strict evidence complete: **false**.

This is the user-selected Docker Desktop / WSL2 runtime, **not an exact four-vCPU host**. There is **no measured baseline and no causal improvement claim**. The saved JSON explicitly uses `published_judge_different_runtime` and `improvement_claim_allowed: false`.

## Source and runtime

- Candidate: `resense:p1-s1-volume-62d055f-20261016`; Docker immutable ID / repo digest: `sha256:4672efcc4505b274f2110ca2075ac048c8e0524d98311f693ddb9ea58f62fdbf`.
- Verified node/launch commit: `62d055f92a1628a3e8c1da8798887d9bb147b93d`. No node, launch, policy or core source was changed during measurement.
- Host: `Windows-10-10.0.26200-SP0`; `12` host logical CPUs. Docker daemon: **12 logical CPUs**, **6.698 GiB** RAM (7,192,399,872 bytes), `6.6.87.2-microsoft-standard-WSL2`, cgroup 2.
- Each container: **4 CPU quota**, `--memory 6g --memory-swap 6g` (6 GiB, swap disabled). Separate node/player/listener cgroups; shared owned PID namespace, host UDP DDS, localhost-only disabled.
- One OMP/OpenBLAS/MKL/NumExpr/vecLib thread; default replay node policy; UID/GID 1000 player.
- Original read-only bags: **201** `doubleT_obstacle` clouds and **252** `roundT_doubleT` clouds. Bag SHA-256, all original header stamps, expected topics/counts and tool identities are in `manifest.json`.
- Driver SHA-256: `509f1d30767b2a3e47ad352966114da30c692fb61e1b35b29382c91fd555cc89`; exact snapshot is external `host_driver.py`.
- Playback storage: **docker_volume**, `rs-s1-original-bags-20261016-72a601b`. Native Linux Docker volume, mounted read-only, with full database/metadata hashes and original cloud inventories verified before any replay. Inventory digest: `51d44e1c1893e4a96cb9208d4fc03c9cd5ba6caa2720a6c12c80608c5db496c6`.
- Cache policy: explicit read-only full-bag hash prefetch immediately before every playback; warm-cache measurements, with separate prefetch receipts/times.
- Final raw root: `C:\Users\alikh\AppData\Local\Temp\opencode\resense-p1-runs-2026-10-15\attempt07_linux_volume_warm_matrix`.
- Exact judge listener/analyzer copies are retained; separate strict host analysis supplies the unrounded gate values.

## Median acceptance checks

Display values are rounded here only; `summary.json` stores unrounded comparisons. All three measured repetitions are retained, including incomplete-tail evidence; no favorable-run selection is used.

| Condition | Metric | Median | Inclusive target | Numeric check | Strict group |
|---|---|---:|---|---|---|
| obstacle_literal | `fresh_fraction` | 0.005 | >= 0.8 | FAIL | INCOMPLETE |
| obstacle_literal | `source_age_p50_s` | 1.190 | <= 0.5 | FAIL | INCOMPLETE |
| obstacle_literal | `memory_gate_mb` | 784.916 | <= 1200 | PASS | INCOMPLETE |
| obstacle_literal | `first_stop_dist` | 55.540 | >= 55 | PASS | INCOMPLETE |
| obstacle_literal | `first_stop_dist` | 55.540 | <= 57 | PASS | INCOMPLETE |
| obstacle_readme | `fresh_frames` | 85 | >= 180 | FAIL | complete |
| obstacle_readme | `source_age_max_s` | 1.941 | <= 0.6 | FAIL | complete |
| obstacle_readme | `STOP` | 147 | >= 185 | FAIL | complete |
| obstacle_readme | `first_stop_after_first_result_s` | 2.163 | <= 1.2 | FAIL | complete |
| clear_literal | `FAULT` | 16 | <= 10 | FAIL | complete |
| clear_readme | `fresh_frames` | 235 | >= 242 | FAIL | INCOMPLETE |

### Failed numeric targets

- **obstacle_literal** `fresh_fraction`: median 0.004975, target >= 0.8.
- **obstacle_literal** `source_age_p50_s`: median 1.190454, target <= 0.5.
- **obstacle_readme** `fresh_frames`: median 85, target >= 180.
- **obstacle_readme** `source_age_max_s`: median 1.940879, target <= 0.6.
- **obstacle_readme** `STOP`: median 147, target >= 185.
- **obstacle_readme** `first_stop_after_first_result_s`: median 2.162709, target <= 1.2.
- **clear_literal** `FAULT`: median 16, target <= 10.
- **clear_readme** `fresh_frames`: median 235, target >= 242.

### Strict completeness

- `candidate_obstacle_literal_r1`: missing/extra/mismatched decision messages.
- `candidate_clear_readme_r1`: last expected bag frame missing (incomplete drain).
- `candidate_clear_readme_r2`: last expected bag frame missing (incomplete drain); missing/extra/mismatched decision messages.
- `candidate_clear_readme_r3`: last expected bag frame missing (incomplete drain); missing/extra/mismatched decision messages.

A clean player exit/watchdog drain is not substituted for an absent final original bag-frame result. The strict verdict remains incomplete/failed where that registered check is unmet.

## Every repetition

Fresh denominator is always every original bag frame (201/252), not only received results. STOP/FAULT below are **frame results only**; watchdogs are separately counted in JSON. Age is the node's DDS publication source age, including literal playback without `/clock`.

| Condition / repeat | Results / expected | Fresh | STOP | FAULT | Age p50 / max (s) | First STOP lag (s) / distance (m) | Missing bag results | Strict complete |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| obstacle_literal / 1 | 56/201 | 1 | 50 | 5 | 1.390 / 2.349 | 2.031 / 55.540 | 145 | False |
| obstacle_literal / 2 | 49/201 | 0 | 47 | 2 | 1.190 / 2.272 | 1.283 / 55.520 | 152 | True |
| obstacle_literal / 3 | 49/201 | 1 | 42 | 6 | 0.742 / 1.128 | 1.709 / 55.830 | 152 | True |
| obstacle_readme / 1 | 153/201 | 98 | 147 | 5 | 0.159 / 2.361 | 2.163 / 55.540 | 48 | True |
| obstacle_readme / 2 | 155/201 | 85 | 149 | 5 | 0.200 / 1.941 | 2.757 / 55.590 | 46 | True |
| obstacle_readme / 3 | 149/201 | 37 | 143 | 6 | 0.336 / 1.112 | 1.331 / 55.540 | 52 | True |
| clear_literal / 1 | 193/252 | 159 | 0 | 17 | 0.048 / 0.493 | — / — | 59 | True |
| clear_literal / 2 | 205/252 | 184 | 0 | 15 | 0.046 / 0.564 | — / — | 47 | True |
| clear_literal / 3 | 201/252 | 171 | 0 | 16 | 0.048 / 0.619 | — / — | 51 | True |
| clear_readme / 1 | 247/252 | 235 | 0 | 1 | 0.047 / 0.402 | — / — | 5 | False |
| clear_readme / 2 | 249/252 | 238 | 0 | 1 | 0.046 / 0.391 | — / — | 3 | False |
| clear_readme / 3 | 249/252 | 234 | 0 | 1 | 0.047 / 0.418 | — / — | 3 | False |

## CPU, memory and playback wall time

Memory is **decimal MB (bytes / 1,000,000)**. RSS is the node process `ru_maxrss` converted from its reported MiB; cgroup peak includes charged page cache and all node-container processes/probes. Docker working set is sampled/cache-adjusted and is **not** the peak gate. The gate is `max(RSS, cgroup peak)`. Docker CPU mean/max are percent / 100 and include idle preload/drain periods; node CPU is separate rolling telemetry.

| Condition / repeat | Node cores p50 / max | Docker cores mean / max | RSS MB | Cgroup peak MB | Docker working-set peak MB | Memory gate MB | Player wall s | Queue-starvation warnings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| obstacle_literal / 1 | 1.420 / 1.430 | 0.367 / 1.564 | 745.642 | 784.916 | 769.130 | 784.916 | 31.523 | 0 |
| obstacle_literal / 2 | 1.380 / 1.480 | 0.290 / 1.535 | 827.431 | 859.824 | 843.999 | 859.824 | 28.374 | 0 |
| obstacle_literal / 3 | 1.370 / 1.380 | 0.238 / 1.389 | 665.426 | 706.109 | 663.644 | 706.109 | 26.256 | 0 |
| obstacle_readme / 1 | 1.060 / 1.410 | 0.500 / 1.525 | 728.865 | 750.785 | 634.388 | 750.785 | 25.528 | 0 |
| obstacle_readme / 2 | 1.090 / 1.490 | 0.484 / 1.722 | 724.985 | 724.529 | 602.721 | 724.985 | 25.552 | 0 |
| obstacle_readme / 3 | 1.110 / 1.400 | 0.546 / 1.485 | 621.701 | 627.986 | 575.039 | 627.986 | 25.246 | 0 |
| clear_literal / 1 | 0.500 / 0.990 | 0.339 / 1.202 | 301.780 | 313.577 | 263.927 | 313.577 | 27.371 | 0 |
| clear_literal / 2 | 0.490 / 0.940 | 0.317 / 1.176 | 337.851 | 374.673 | 344.982 | 374.673 | 27.222 | 0 |
| clear_literal / 3 | 0.470 / 1.000 | 0.337 / 1.202 | 335.439 | 347.472 | 336.488 | 347.472 | 27.185 | 0 |
| clear_readme / 1 | 0.490 / 1.060 | 0.367 / 1.137 | 180.250 | 189.034 | 171.128 | 189.034 | 30.729 | 0 |
| clear_readme / 2 | 0.500 / 0.930 | 0.325 / 1.211 | 178.363 | 180.085 | 162.424 | 180.085 | 30.993 | 0 |
| clear_readme / 3 | 0.470 / 1.030 | 0.338 / 1.103 | 184.025 | 186.745 | 168.506 | 186.745 | 30.863 | 0 |

### Explicit read-only prefetch (outside player wall time)

The native-volume page cache was warmed with a full-file hash read before **every** repetition. The separate helper had a 6 GiB limit and no swap, was removed before playback, and is not part of the node-container memory gate. Its time is not hidden in player timing.

| Condition / repeat | Prefetch bytes | Prefetch wall s |
|---|---:|---:|
| obstacle_literal / 1 | 4821251075 | 8.530 |
| obstacle_literal / 2 | 4821251075 | 7.670 |
| obstacle_literal / 3 | 4821251075 | 8.171 |
| obstacle_readme / 1 | 4821251075 | 8.195 |
| obstacle_readme / 2 | 4821251075 | 4.803 |
| obstacle_readme / 3 | 4821251075 | 4.512 |
| clear_literal / 1 | 2014868458 | 4.409 |
| clear_literal / 2 | 2014868458 | 3.141 |
| clear_literal / 3 | 2014868458 | 2.009 |
| clear_readme / 1 | 2014868458 | 1.767 |
| clear_readme / 2 | 2014868458 | 1.408 |
| clear_readme / 3 | 2014868458 | 1.387 |

### Message loss

| Condition / repeat | Missing status | Decision delta (status − decision) | Latency delta (frames − latency) | Node dropped / skipped |
|---|---:|---:|---:|---:|
| obstacle_literal / 1 | 0 | -1 | 0 | 149 / 145 |
| obstacle_literal / 2 | 0 | 0 | 0 | 151 / 143 |
| obstacle_literal / 3 | 0 | 0 | 0 | 156 / 152 |
| obstacle_readme / 1 | 0 | 0 | 0 | 52 / 48 |
| obstacle_readme / 2 | 0 | 0 | 0 | 50 / 34 |
| obstacle_readme / 3 | 0 | 0 | 0 | 56 / 52 |
| clear_literal / 1 | 0 | 0 | 0 | 59 / 59 |
| clear_literal / 2 | 0 | 0 | 0 | 47 / 43 |
| clear_literal / 3 | 0 | 0 | 0 | 50 / 45 |
| clear_readme / 1 | 0 | 0 | 0 | 4 / 4 |
| clear_readme / 2 | 0 | -1 | 0 | 2 / 2 |
| clear_readme / 3 | 0 | -1 | 0 | 2 / 2 |

Missing bag results and the node's inferred dropped/skipped telemetry are distinct measurements; the latter is not used to reduce expected frame counts or the fresh denominator.

## Per-condition descriptive medians

These summarize all three runs regardless of strict completeness; they do not override a failed gate.

| Condition | Results | Fresh / expected | STOP | FAULT | Age p50 / max s | First STOP lag s / m | Memory gate MB |
|---|---:|---:|---:|---:|---:|---:|---:|
| obstacle_literal | 49 | 1/201 | 47 | 5 | 1.190 / 2.272 | 1.709 / 55.540 | 784.916 |
| obstacle_readme | 153 | 85/201 | 147 | 5 | 0.200 / 1.941 | 2.163 / 55.540 | 724.985 |
| clear_literal | 201 | 171/252 | 0 | 16 | 0.048 / 0.564 | — / — | 347.472 |
| clear_readme | 249 | 235/252 | 0 | 1 | 0.047 / 0.402 | — / — | 186.745 |

## Prior attempts / diagnostic (excluded from these medians)

- `attempt05_matrix`: source `1eed357`, storage `host_bind`, strict complete `False`, passed `False`. Original artifacts remain at the indexed external root.
- `attempt06_linux_volume_diagnostic`: source `9247354`, storage `docker_volume`, strict complete `False`, passed `False`. Original artifacts remain at the indexed external root.
- `attempt06b_linux_volume_warm_diagnostic`: source `62d055f`, storage `docker_volume`, strict complete `False`, passed `False`. Original artifacts remain at the indexed external root.
- **`attempt07_linux_volume_warm_matrix` alone supplies all twelve repetitions and every median in this report.**

Repairs are harness-only: transport/process identity and actual-data readiness, pre-analysis immutable `.meta` + final `.receipt.json`, actual nullable watchdog-counter schema, explicit SIGKILL/OOM attribution, and detached execution. The Linux-volume follow-up changes storage and verifies its full data identity without changing registered counts or thresholds. No failed numeric target was tuned around. Filesystem caches were not cleared; no cold-cache or exact judge-host claim is made.

The earlier Windows-bind matrix remains FAIL/incomplete and is not replaced or relabelled. Playback wall times and starvation counts are reported for this actual storage path. Source revision and storage both differ across the follow-up; comparisons do not isolate algorithm or storage causality. No baseline was measured.

## Exact commands

```powershell
$python = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe'
# From C:/Users/alikh/AppData/Local/Temp/opencode/rs-p1-start; choose another NEW --out to reproduce.
& $python docs/evidence/node_startup_2026-10-15/docker_tools/launch_matrix.py --out 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-p1-runs-2026-10-15\attempt07_linux_volume_warm_matrix' -- --image resense:p1-s1-volume-62d055f-20261016 --detector-commit 62d055f92a1628a3e8c1da8798887d9bb147b93d --bags 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/for_hackathon' --bags-volume rs-s1-original-bags-20261016-72a601b --bags-prefetch --repeats 3 --cpus 4 --memory 6g --player-timeout 600
& $python scripts/startup_acceptance.py --analyze 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-p1-runs-2026-10-15\attempt07_linux_volume_warm_matrix'
& $python -m pytest -q tests/test_startup_acceptance.py
& 'C:/Users/alikh/AppData/Local/Programs/Python/Python311/Scripts/ruff.exe' check scripts/startup_acceptance.py tests/test_startup_acceptance.py docs/evidence/node_startup_2026-10-15/docker_tools
```

The launcher returning successfully is not acceptance; strict reanalysis exits 1 for this matrix. `launch.json` retains the exact actually launched argument vector and driver hash.

## Retained evidence / cleanup

- `summary.json`: exact full strict result and all per-run metrics; `manifest.json`: exact runtime/image/bag/source provenance.
- `selected/`: first repetition's full receipt per condition plus explicitly marked node/player/listener log excerpts, each identifying full source path and hash.
- `runtime_observations.json`: every repetition's wall time, starvation warnings and strict errors.
- Volume runs also retain `bags_volume_verification.json` and, when supplied, `volume_stage.json`; full staging artifacts are externally hash-indexed.
- `condition_medians.json`: descriptive median of each numeric metric over all three repetitions per condition.
- `raw_hash_index.json`: SHA-256/size/path of every external attempt artifact and detached-launch sibling; failed and interrupted attempts are preserved.
- `publication_hash_index.json`: exact-byte hashes for the compact committed report artifacts (excluding itself).
- `cleanup.json`: Docker query for every attempt run ID found **no remaining owned containers**. Unrelated containers were not modified.

Large raw listener/witness/stats/command JSONL streams and bags are **not copied into Git**. Full raw paths and hashes are retained; review the raw files locally before external archival/removal.

## Outcome and remaining work

This measurement answers S1 only on the selected runtime and the source/image named above. The failed targets remain open. Any later policy/runtime work needs separately authorized changes and a fresh registered matrix; the present result does not grant S1 completion or replace combined CI/release approval.
