# S1 real-Docker acceptance protocol — 2026-10-15

**Status:** real candidate-only 4-condition × 3 matrix executed on the user-selected
runtime; **S1 FAIL**, with strict completeness **false**. All twelve playback executions
finished and cleaned up. See [`docker/README.md`](docker/README.md) for every repetition,
median check, provenance, infrastructure attempts and external raw/hash indexes. No
same-runtime causal improvement is claimed.

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
one latency message per processed frame, and a post-player watchdog confirming expired
monitoring. The actual node intentionally omits counters on watchdog snapshots (`null`
in the exact listener); such snapshots never become frames or provide an invented counter.
If watchdog counters are supplied, they must be consistent with received frame counters.
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
It verifies all three `jury_listener` subscriptions and their publishers via the ROS graph
**and receipt of actual status data**,
then the driver retains the judge's additional four-second discovery allowance. The wrapper
forwards termination and requires the original listener to flush/exit cleanly.

The exact `analyze_chain.py` runs in the image (where NumPy already exists). Its historical
`.summary.json` is retained beside strict host results. Its required `.meta` playback
snapshot is written before analysis; the immutable final cleanup receipt is a separate
`.receipt.json`. Its rounded ages, all-status first
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

Docker host networking, UDP DDS and `ROS_LOCALHOST_ONLY=0` are used. Listener and player
join the node container's PID namespace (`--pid container:<node>`), preserving unique
process identities for Fast DDS participants on the shared host network. Their cgroups
and CPU/memory quotas remain separate. Docker Desktop must
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
* `out/docker/<role>_<condition>_r<N>.{jsonl,meta,receipt.json,stats,samples.jsonl,summary.json}`;
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

### Execution handoff and infrastructure repairs (15 October)

The parent subsequently authorized real candidate-only measurements on the selected
Docker Desktop / WSL2 runtime: **12 logical CPUs, 7,192,399,872 bytes daemon RAM**,
four-core **per-container** quotas and `--memory 6g --memory-swap 6g`. This is not an
exact four-vCPU-host reproduction. The registered 201/252 frame counts and numeric
acceptance thresholds are unchanged. The image is `resense:p1-start-2026-10-15`, with
node/launch source checked against `1eed357`; no detector/launch/policy tuning is allowed.

Initial external attempts remain under
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-p1-runs-2026-10-15/`:

1. `attempt01_diagnostic`: original transport settings, literal player deadline after
   180 s, no observed status/frame data; player SIGKILL was cleanup, **not Docker OOM**.
2. `attempt02_diagnostic`: original transport, clear README player exited normally but
   no observed data; drain timeout. ROS graph discovery alone had falsely implied readiness.
3. `attempt03_transport_diagnostic`: repaired transport delivered real frames and drained;
   exact judge analyzer failed because `.meta` had previously been deferred until cleanup.
   This attempt is preserved as incomplete, not retroactively repaired into acceptance.

The host driver now writes analyzer input metadata before running the exact analyzer,
writes the final receipt once after cleanup, permits the actual nullable watchdog-counter
schema, and distinguishes Docker OOM from cleanup SIGKILL. Tests include the real null
watchdog schema, PID/transport CLI contract, and analyzer-input-before-final-receipt order:
**83 passed in 2.75 s; Ruff all checks passed**. Fresh matrix directories are required
after repairs. An explicit `--player-timeout 600` accommodates slow Windows bind-mounted
bag preload/queue starvation; it does not alter playback arguments, expected frame counts,
node policy, or numeric thresholds. Matrix outcomes and exact commands belong in `docker/`.

4. `attempt04_matrix`: seven repetitions completed; the terminal's 2,400-second limit
   killed the host driver during repetition eight. Finished receipts remain unchanged.
   `manual_cleanup.json` records removal of the three remaining attempt-owned containers.
   This interrupted matrix is excluded from final median measurements.
5. `attempt05_matrix`: fresh full matrix launched independently of terminal deadlines with
   the stdlib `docker_tools/launch_matrix.py`; sibling `.launch.json`, `.stdout.log` and
   `.stderr.log` preserve the exact command, PID and output. The driver snapshot and its
   SHA-256 are captured in the raw directory/manifest. No numeric policy is changed.

For long runs on this host (the direct foreground invocation can exceed terminal limits):

```powershell
& $python docs/evidence/node_startup_2026-10-15/docker_tools/launch_matrix.py --out 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p1-runs-2026-10-15/NEW_MATRIX_DIRECTORY' -- --image resense:p1-start-2026-10-15 --detector-commit 1eed357 --bags 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/for_hackathon' --repeats 3 --cpus 4 --memory 6g --player-timeout 600
```

The launcher returns immediately; completion is established only by the final saved
`summary.json` plus all twelve clean receipts, not by successful launch. Its optional
`--cleanup <interrupted-raw-root>` verifies exact run labels before stopping/removing any
remaining owned containers, preserves their final states/logs, and refuses unrelated owners.
Launcher and ownership-refusal tests bring the harness suite to **85 passed in 4.05 s**;
Ruff passes. This launcher is orchestration only and does not alter measured player args.

### Final selected-runtime result

`attempt05_matrix` completed all twelve executions on 15 October UTC. All player,
listener and exact analyzer exits were 0; each owned node stopped cleanly (143), every
receipt has `cleanup_ok: true`, and Docker reported no OOM. The label-scoped final query
found no remaining containers for any of the five attempts.

The strict result is `passed: false`, `complete: false`: six runs lack the last expected
original bag-frame result; obstacle README repetition 1 also contains a recorded ~0.9 ms
backward wall-arrival-time step (original JSONL lines 940–941, parser row index 940).
Those observations remain failures; no timing tolerance, expected-count reduction or
policy change was introduced to turn them into passing evidence. All twelve per-run
metrics and all three values per median remain published without favorable selection.

Descriptive medians: obstacle literal fresh **0/201**, source-age p50 **1.110989 s**,
memory gate **797.756621 MB**, first STOP **55.63 m**; obstacle README fresh **0/201**,
source-age max **1.449263 s**, **190 STOP**, first STOP lag **2.571050 s**; clear literal
**31 frame FAULT**; clear README fresh **227/252**. Seven numeric checks fail. The
incomplete evidence means numerically passing individual checks do not grant S1 PASS.

Compact publication is generated and verified with the owned stdlib helper:

```powershell
# Publication --out must not already exist; the executed result is already in docker/.
& $python docs/evidence/node_startup_2026-10-15/docker_tools/publish_report.py --raw 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p1-runs-2026-10-15/attempt05_matrix' --attempts 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p1-runs-2026-10-15/attempt01_diagnostic' 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p1-runs-2026-10-15/attempt02_diagnostic' 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p1-runs-2026-10-15/attempt03_transport_diagnostic' 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p1-runs-2026-10-15/attempt04_matrix' --out docs/evidence/node_startup_2026-10-15/docker
& $python docs/evidence/node_startup_2026-10-15/docker_tools/publish_report.py --verify docs/evidence/node_startup_2026-10-15/docker
```

Verification passed for **24 compact publication files and 312 external files**, including
the failed/interrupted attempts and launch siblings. Parser/launcher/publication-integrity
suite: **88 passed in 4.03 s**, no skips; Ruff passes. Large bag and raw JSONL streams stay
outside Git. Report hashes are exact publication bytes; raw hashes retain the original
external bytes. Candidate source stayed at `1eed357`; harness repair commit is `e110fe9`.
Selected log excerpts normalize trailing line spaces for Git whitespace checks; their
headers and the external raw index continue to bind the untouched full source-log bytes.

## Registered Linux-volume follow-up — 2026-10-16

The user authorized a storage-environment correction after the Windows-bind matrix:
20-second obstacle recordings took 225–339 s with hundreds of player starvation warnings,
and 25-second clear recordings took 92–98 s. Such delivery gaps are directly relevant to
the existing 0.5-second freshness/silence policy. **The earlier matrix remains FAIL and
incomplete, with every raw artifact and published byte retained.**

The follow-up measures the current combined source (node correction `1f2dab7`, C1 packaging
`0caf5c2`, Docker fixture commit `9173a00`, plus this harness commit). A fresh uniquely
tagged runtime image will be built from the captured committed HEAD with the existing
offline Dockerfile and existing E2 base. Node, launch, policy, core and Dockerfiles are
not edited in this lane. Runtime verification now hashes node, launch, shared policy and
ROS setup source against the declared commit. Old source images are not reused as the
new measured candidate. Helper scripts remain external mounts.

### Data copy and pre-replay verification

`docker_tools/bags_volume.py stage` creates a **new uniquely named, labelled native local
Docker volume**. It refuses existing volumes and nonempty copy destinations. The Windows
source is mounted read-only; the only writes inside the volume are the original two bag
directories, their `.db3` files and byte-identical `metadata.yaml` files (files made 0444).
There are no helper/verification marker files in the data volume. Evidence lives separately
under the external run parent. No host metadata or bag bytes are changed.

The stage helper compares fresh host inventory to the earlier published Windows manifest
with `--reference-manifest`, copies the files, then uses a separate **read-only** Docker
mount to compare full database and metadata SHA-256, file sizes, original topics, all header
stamps, and exact cloud counts (**201 / 252**). It rejects extra files/directories and partial
copies. A canonical full-file inventory digest binds the volume label and stage receipt.

The driver accepts `--bags-volume <existing-name>` in addition to mandatory `--bags`.
`--bags` continues to supply the host original-file inventory; only playback changes to
`type=volume,...,readonly,volume-nocopy`. The driver first inspects the volume (no implicit
creation), rejects driver/bind options, and **repeats the complete read-only in-container
hash/header/count verification before any replay in each new run directory**. A cached
"verified" flag is insufficient for reuse. The manifest and final receipts distinguish
`docker_volume` from `host_bind`; actual Docker inspect mount type/name/read-only flags
are checked on reanalysis. New provenance errors cannot produce acceptance PASS.

### Preregistered execution sequence and scope

1. Finish this harness/protocol commit and its parser/volume tests before timed runs.
2. Wait until the parent's full-Linux-suite guard and all other active containers have
   finished. Check `docker ps` immediately before diagnostics and the full matrix; do not
   stop another agent's container. Volume preparation and image build are untimed setup.
3. Capture committed HEAD, build a unique runtime image offline, and retain build command,
   source revision, image identity and log in the new external evidence area.
4. Stage/verify the exact two bags in the new Linux volume, comparing the original Windows
   publication. Reuse requires fresh full verification, never an overwrite of partial data.
5. Run `attempt06_linux_volume_diagnostic`: README playback of both bags, one repetition
   each, unchanged registered flags. A subset is **never acceptance PASS**. Proceed to the
   full matrix if replay is near real time: wall time no greater than original bag duration
   + 13 s (README delay 3 s plus 10 s CLI/startup allowance). Record starvation warnings and
   freshness; freshness numeric success is not used to select or tune subsequent runs.
6. If I/O is resolved, run **all four conditions × three repetitions** in a fresh
   `attempt07_linux_volume_matrix`, default node policy, four-core per-container quotas,
   `--memory 6g --memory-swap 6g`, one BLAS thread. **All existing S1 numeric thresholds,
   expected frame counts, strict parser checks and frame-only/watchdog distinction remain.**
   Finish every repetition even if numeric targets fail; make no further numeric tuning.
7. Publish compact results in a new `docker/linux_volume_2026-10-16/` subdirectory, including
   exact source/image identity, storage verification, per-run/median metrics, selected
   receipts/logs, cleanup and hashes. Preserve the earlier Windows report unchanged.

The runtime is still the user-selected Docker Desktop/WSL2 daemon with 12 logical CPUs,
not an exact four-vCPU host. This is candidate-only; source revision and storage both differ
from the Windows run, so no isolated node-improvement/storage-only causal claim is made.
The labelled volume is retained for verified read-only reuse; only owned copy/verification/
playback containers are removed, and unrelated resources are not changed.

Example setup and diagnostic commands (substitute the actual captured HEAD, unique image,
new volume name and new output directory; parent must already exist):

```powershell
$python = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe'
$bags = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/for_hackathon'
$parent = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p1-runs-2026-10-15'
Test-Path -LiteralPath $parent
$source = git rev-parse HEAD
docker ps --format '{{.Names}} {{.Status}}'
docker build --network none --pull=false --build-arg RELEASE_IMAGE=resense:p1-e2-check --label "org.opencontainers.image.revision=$source" -f docker/Dockerfile.offline -t <unique-runtime-image> .
& $python docs/evidence/node_startup_2026-10-15/docker_tools/bags_volume.py stage --image <unique-runtime-image> --volume <new-labelled-volume> --bags $bags --reference-manifest docs/evidence/node_startup_2026-10-15/docker/manifest.json --out "$parent/volume_stage06"
docker ps --format '{{.Names}} {{.Status}}'
& $python scripts/startup_acceptance.py --image <unique-runtime-image> --detector-commit $source --bags $bags --bags-volume <new-labelled-volume> --out "$parent/attempt06_linux_volume_diagnostic" --conditions obstacle_readme clear_readme --repeats 1 --cpus 4 --memory 6g --player-timeout 600
# After confirming near-real-time playback, use launch_matrix.py with NEW --out,
# --bags-volume and the same image/source; omit --conditions and use --repeats 3.
```

Pre-measurement verification: **109 parser/launcher/volume/publication tests passed in
5.94 s**, no skips; Ruff passes. New cases exercise full-byte preservation, corrupt or
partial volume rejection, exact topics/header stamps/counts, no non-data markers, native
read-only mount arguments, missing-volume refusal, and saved provenance/mount tampering.
