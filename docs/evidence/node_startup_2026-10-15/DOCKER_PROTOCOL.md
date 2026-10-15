# S1 real-Docker acceptance protocol — 2026-10-15

**Status:** reusable driver and dataset-free parser/unit checks implemented. Real Docker
acceptance is **pending the final committed node image**. No performance improvement is
claimed by implementing or testing this driver.

Source of acceptance bounds: main checkout `docs/BACKLOG.md`, S1, lines 263–290 read
2026-10-15. Run from branch `p1/start-2026-10-15` in the shared `rs-p1-start` worktree.

## Registered matrix and scoring

| Driver condition | Original bag / LiDAR | Actual player command after image |
|---|---|---|
| `obstacle_literal` | `doubleT_obstacle`, 360°, **201** clouds | `ros2 bag play /data/doubleT_obstacle` |
| `obstacle_readme` | same | `ros2 bag play /data/doubleT_obstacle --read-ahead-queue-size 10 --clock --delay 3` |
| `clear_literal` | `roundT_doubleT`, 120°, **252** clouds | `ros2 bag play /data/roundT_doubleT` |
| `clear_readme` | same | `ros2 bag play /data/roundT_doubleT --read-ahead-queue-size 10 --clock --delay 3` |

Three sequential repetitions per condition, on an idle host. Candidate runs are never
concurrent. With `--baseline-image`, the same driver first measures all 12 baseline runs,
then all 12 candidate runs on the same Docker daemon/host, quota, mounts, environment,
commands, readiness and drain protocol. Baseline and candidate must resolve to distinct
immutable image IDs. The baseline is allowed to fail the S1 numeric targets, but every
baseline run must have complete evidence for a same-runtime comparison to be valid.

Acceptance uses the **median of three per-run values**, independently for each bound:

| Condition | Inclusive bounds on medians |
|---|---|
| obstacle README | fresh ≥ 180; source-age **max** ≤ 0.6 s; frame STOP ≥ 185; first frame STOP ≤ 1.2 s after first frame result |
| obstacle literal | fresh / **201** ≥ 0.80; source-age p50 ≤ 0.5 s; memory gate ≤ **1,200 decimal MB**; first frame STOP distance **55 ≤ d ≤ 57 m** |
| clear literal | frame FAULT ≤ 10 |
| clear README | fresh ≥ 242 (denominator **252**) |

All four conditions, exactly three repetitions, `--cpus 4`, default node policy, and
complete receipts/raw data are required for `passed: true`. Diagnostic subsets, one/two
repetitions, CPU changes or `--node-arg` overrides cannot produce an acceptance PASS.
Values are **not rounded before comparison**. A single incomplete/corrupt repetition
invalidates its group even if the other two medians would pass. A missing STOP is `null`,
never zero; missing telemetry, stats, expected frames, player exit, or watchdog drain fails.

`snapshot == "frame"` is mandatory for frame metrics. Watchdog/held STOPs are counted
separately and cannot advance first STOP or inflate fresh/STOP/FAULT frame counts.
Freshness is the node's literal Boolean `freshness.valid`. Source age is the node's
`freshness.source_age_s` captured by the **original listener**, including replay-without-
`--clock`: it uses the node's DDS publisher-UTC metadata, not bag-header time subtracted
from today's wall clock. First-STOP lag is listener wall arrival minus the first **frame**
result's arrival; distance is that frame STOP's `nearest` value.

Missing bag results are explicitly `expected_frames - frames_processed`. Deliberate catch-up
skips may cause missing results; they still remain in the fresh denominator. The parser
requires unique progressing original header stamps, the final expected bag header, contiguous
zero-based `node.frames` on processed frames, matching decision/status sequences, exactly
one latency message per processed frame, and a post-player watchdog with the final counter.
Missing status/decision/latency counts/deltas and node dropped/skipped counters are reported.
An empty result stream cannot pass the clear-literal FAULT bound.

## Reused judge tools

`docker_tools/{chain.sh,listener.py,analyze_chain.py}` are exact **LF-normalized text copies**
of `docs/evidence/judgement_2026-10-13/scripts/docker/`. Tests and driver preflight verify
this equality. No 13 October file is edited. `chain.sh` is retained as historical protocol;
the new host driver replaces its fixed container names, blind sleeps, unlimited playback,
and hardcoded evidence directory.

The exact `listener.py` records the acceptance stream. `observe_listener.py` starts it as
a child and adds a separate flushed, lightweight status witness for readiness/draining.
This witness is control-plane evidence, never a substitute source of acceptance metrics.
It verifies all three `jury_listener` subscriptions and their publishers via the ROS graph,
then the driver retains the judge's additional four-second discovery allowance. The wrapper
forwards termination and requires the original listener to flush/exit cleanly.

The exact `analyze_chain.py` runs in the image (where NumPy already exists). Its historical
`.summary.json` is retained beside strict host results. Its rounded ages, all-status first
STOP and historical memory-unit labels **do not drive S1 thresholds**. Its regex expects
`rs_node`; only the compatibility `.stats` text uses that token. The parallel raw
`.samples.jsonl` retains the actual unique container name and Docker JSON.

All helpers are invoked with `python3`, not as executable mounted shell files. The host
copies helpers into the **new** output and normalizes CRLF using Python text I/O; no host
Bash, Docker socket mount, shell script rewrite in the image, or image build is needed.

## Runtime, isolation, bounds and provenance

Three containers per repetition reproduce the judge topology: node, unchanged listener
(plus the readiness/drain witness), and UID/GID `1000:1000` player. `HOME=/tmp` matches the
original judge's player setup. Each container has `--cpus 4 --memory 4g --memory-swap 4g`
by default; swap is disabled. The **node container quota** is four logical CPU cores;
player/listener have separate quotas, as separate containers. This is not a claim that
the host has only four CPUs or that the entire chain shares one four-core cgroup. An idle
four-vCPU host is still the registered comparison environment; physical/logical host and
Docker VM CPU counts and container `lscpu` are captured to expose differences.

Docker host networking, UDP DDS and `ROS_LOCALHOST_ONLY=1` are used. Docker Desktop must
support/enable host networking; a failure to discover the node/listener is an incomplete
run, not a networking fallback. Each sequential repetition gets a deterministic domain
slot: `20 + int(run_id[:4],16) % 50 + slot`, at most 92 for the 24-run A/B matrix. Active
driver-labelled domain collisions are refused. Unrelated workloads must not use those
domains. Containers have UUID-derived unique names and labels for run/domain, image ID,
detector commit, arguments, condition/repetition, CPU and memory limits. No global container
removal or unrelated resource modification is performed.

OMP, OpenBLAS, MKL, NumExpr and vecLib each receive one thread. Bags are bind-mounted
**read-only** at `/data`; only the new output is writable. Host SQLite inventory verifies
the actual PointCloud2 topic/count, unique header stamps, duration and complete database
SHA-256 hashes before any container starts. It reads cloud headers via SQLite `substr`,
not a full deserialization. Both original bags are required, not generated/cropped caches.

The image tag is resolved once with `docker image inspect`; all runs use its immutable ID.
`--detector-commit` identifies the committed node/launch revision. The driver resolves it
with Git and verifies normalized SHA-256 of **both node and launch source in the running
image** against that commit before playback. This is a node/launch source check, not a
whole-image reproducible-build attestation. Image labels/digests, runtime native status,
version/import path, thread environment, Python/kernel/CPU/memory, Docker client/server,
daemon CPU/RAM/cgroup/kernel/storage facts and Docker context are captured. Registry/proxy
configuration is excluded from Docker daemon provenance.

### Memory and CPU definitions (no conflation)

* `container_cgroup_peak_mb`: node container's kernel `memory.peak` (cgroup v2), or
  `memory.max_usage_in_bytes` (v1), **bytes / 1,000,000**. Cumulative high-water includes
  charged page cache and all processes in the node container, including small provenance/
  memory probes and the exact judge analyzer. A final read occurs after analysis, before
  stopping the node. Unavailable cgroup high-water data fails completeness.
* `docker_working_set_peak_mb`: maximum **sampled** Docker stats `MemUsage` converted
  from its explicit SI/IEC unit to bytes / 1,000,000. Docker commonly subtracts inactive
  file cache; this is not the cgroup high-water and may miss between-sample peaks.
* `node_rss_peak_mb`: max node-reported `rss_peak_mb`, which on Linux is
  `ru_maxrss / 1024` **MiB**; converted back to bytes and then to decimal MB. It is the
  detector Python process's lifetime RSS peak, not the whole container.
* `memory_gate_mb = max(container_cgroup_peak_mb, node_rss_peak_mb)`. The 1,200 MB gate
  therefore cannot pass using a low sampled working set while a larger peak is recorded.
* `docker_cpu_cores_mean/max`: sampled Docker CPU percent / 100; 100% means one logical
  CPU. Node-reported `cpu_cores` p50/max are separately preserved. No normalization by
  host CPU count is hidden in these metrics.

Stats start before advertisement and run through playback/drain/analysis. The saved samples
must cover both playback start and final drain. CPU is a sampled summary, not a CPU-time
integral or a promise that the daemon was otherwise idle.

The driver waits for node advertisement, listener graph readiness, successful player exit,
at least four seconds of post-player drain, at least two seconds with no new frame, and
a watchdog snapshot after player exit. Default deadlines: ready 120 s, player 180 s,
drain 40 s. A missing tail/counter or deadline fails. The listener is then stopped cleanly,
the exact analyzer runs, the final cgroup peak is read, logs/states are captured, and every
owned container is stopped/removed in `finally`, including partial-creation failures.
OOM, forced SIGKILL, failed cleanup or an unclean child exit fails the receipt. Timeouts
apply to Docker CLI calls too. Interrupting a run produces a failed/incomplete matrix.

## Commands (PowerShell 5.1)

Run these **after the final node commit is in the candidate image**. The worktree HEAD must
identify that node/launch revision; the driver will reject mismatched image source. Existing
images are required: the driver never builds, pulls, commits or tags an image.

```powershell
# Working directory: C:/Users/alikh/AppData/Local/Temp/opencode/rs-p1-start
$python = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe'
$bags = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/for_hackathon'
$parent = 'C:/Users/alikh/AppData/Local/Temp/opencode/rs-p1-start/docs/evidence/node_startup_2026-10-15'
Test-Path -LiteralPath $parent
$out = Join-Path $parent ('docker_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N'))
$candidateCommit = git rev-parse HEAD
& $python scripts/startup_acceptance.py --image candidate --detector-commit $candidateCommit --bags $bags --out $out --repeats 3 --cpus 4
```

Candidate-only execution is valid absolute S1 acceptance with an explicit, embedded
**published judge / DIFFERENT runtime** comparison. Its JSON always sets
`comparison_mode: published_judge_different_runtime` and `improvement_claim_allowed: false`.
The old judge numbers cannot support a same-runtime causal improvement claim.

Preferred same-runtime A/B (substitute the **actual existing baseline image tag and commit**;
the candidate command above already assumes the parent's image is tagged `candidate`):

```powershell
$baselineImage = 'resense:s1-baseline'
$baselineCommit = '<full commit used to build the existing baseline image>'
# Use another new $out; never reuse a completed or interrupted directory.
$out = Join-Path $parent ('docker_ab_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N'))
& $python scripts/startup_acceptance.py --image candidate --detector-commit $candidateCommit --baseline-image $baselineImage --baseline-detector-commit $baselineCommit --bags $bags --out $out --repeats 3 --cpus 4
```

If a valid baseline is present, complete raw baseline/candidate per-run metrics and median
checks are returned. `improvement_claim_allowed` permits comparison only after a complete
same-runtime matrix and candidate acceptance; it does not assert that every metric improved
or establish causality for other image changes. Inspect both image commits/runtime facts.

Focused diagnosis (new directory; **exit 1 / `passed: false` by design**, even if numeric
checks for this single condition are good):

```powershell
$out = Join-Path $parent ('docker_diag_' + [guid]::NewGuid().ToString('N'))
& $python scripts/startup_acceptance.py --image candidate --detector-commit $candidateCommit --bags $bags --out $out --repeats 1 --cpus 4 --conditions obstacle_literal
```

Replay the strict parser without Docker or any writes (validates raw JSONL/receipts again,
not the existing top-level verdict):

```powershell
& $python scripts/startup_acceptance.py --analyze $out
& $python -m pytest -q tests/test_startup_acceptance.py
```

`--out` must not exist; its parent must exist. Do not pre-create `$out`. Run artifacts:

* `manifest.json`: frozen plan, image/commit/host provenance, bag identity and tool hashes;
* `tools/`: LF-normalized copies of the exact judge tools and new helpers;
* `docker_commands.jsonl`: executed Docker argument vectors and exit codes;
* `out/docker/<role>_<condition>_r<N>.{jsonl,meta,stats,samples.jsonl,summary.json}`;
* same prefix `.node.log`, `.player.log`, `.listener.log`, `.analysis.log`,
  `.observer.jsonl`, `.ready`;
* top-level `summary.json`: strict verdict, per-run frame/CPU/memory/age/missing-message
  metrics, all median checks, and explicit comparison scope. Final stdout is strict JSON;
  progress goes to stderr. Exit 0 is complete candidate S1 acceptance; exit 1 is a failed
  target/incomplete run/diagnostic matrix; argument/output-collision errors use exit 2.

## Remaining parent work

1. Finish/commit the parallel node/launch lane, then build the final candidate image.
2. Run the full 4-condition × 3 matrix above, preferably with a committed baseline image,
   on an idle host; retain the emitted host/daemon constraints if not the judge's host.
3. Review strict median checks and raw evidence, complete combined ROS/Docker CI, and
   publish the measured result with its actual image ID, commit and runtime scope.

This protocol and the dataset-free tests do not replace original-bag Docker measurements.

## Local verification

```powershell
& 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe' -m pytest -q tests/test_startup_acceptance.py
& 'C:/Users/alikh/AppData/Local/Programs/Python/Python311/Scripts/ruff.exe' check scripts/startup_acceptance.py tests/test_startup_acceptance.py docs/evidence/node_startup_2026-10-15/docker_tools
```

The dataset-free suite covers strict/corrupt/truncated JSON, missing original/expected
frames, no-result runs, telemetry loss, watchdog filtering, source-age and memory definitions,
every inclusive median threshold and unrounded failures, actual quota/player receipts,
same-runtime baseline completeness, candidate-only comparison scope, output collision
refusal, and mocked CLI success/failure cleanup for literal and README playback. These
checks start no Docker containers. The exact judge copies are checked against the originals.

Verified 2026-10-15 in `rs-p1-start`: **82 passed in 2.78 s**, no skips; standalone Ruff
**all checks passed**. Git no-index whitespace checks for the new driver, test and protocol
passed (only the checkout's LF-to-CRLF notice). Docker inspection showed no running
containers; no images were built and no acceptance containers/matrix were started here.
