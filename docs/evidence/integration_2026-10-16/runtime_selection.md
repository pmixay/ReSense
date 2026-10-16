# Shipping runtime selection — 16 October 2026

**Selected: published queue/continuity/freshness behavior plus the shared v1 decision
policy and strict raw-result validation. Runtime v2 is rejected with `ValueError`.**

## Published baseline and acceptance boundary

The node and launch sources are byte-identical between:

- `origin/main` at `3fdc87957f5d09ff32573eabe6637924b91ea376`;
- `origin/final/silent-misses` at `d0d17bb5dcc2b5b23f9ddd96744a8fd0424e0b5d`.

Their published Git blob IDs are `bbbc9223a0cf6311af629f700185a1fb482e045f`
(node) and `a5d4dd8763d845b0a262738403382ee340749424` (launch).

[S1](../node_startup_2026-10-15/S1.md) remains unaccepted: its original-bag Docker
matrices failed. [C1 v2](../caution_policy_2026-10-15/EVIDENCE.md) remains
unaccepted: the saved-output rescore had 30.46% empty CAUTION against a 25% target
and lost 19 labelled in-gauge object-frame alerts. These historical candidate
reports describe their measured sources, not this shipping runtime.

The current node removes S1's 12-frame Python cap, adaptive processing-cost step,
new skip-credit/queued-epoch bookkeeping, and one-input-period freshness allowance.
Candidate implementation bytes remain in the integration history; evidence,
harnesses, and the pure offline v2 policy/rescorer remain in the tree. Original
candidate refs are retained for the parent's verified archive. This selection
makes no new numerical acceptance or performance claim for either candidate.

## Exact behavior selected

All 39 published node parameter defaults are preserved. The three additive policy
parameters are `decision_policy="v1"`, `caution_distance_m=80.0`, and
`caution_compact_max_size_m=3.0`; their launch defaults/types agree. The distance
and compactness parameters do not suppress any v1 advisory.

| Published runtime setting | Selected value/behavior |
|---|---|
| `input_queue_depth` | 40, DDS KEEP_LAST |
| `catchup_startup_step` | 0.0; preserve every observed input-period startup frame |
| `catchup_startup_max_lag` | 20.0 s |
| `catchup_step` / `catchup_max_lag` | 0.3 s / 5.0 s for later live backlogs |
| Startup window | First catch-up drains, or 1 s expires without a catch-up starting |
| Short live backlog | Process every frame within the published lag limit |
| Queue freshness | `frame_in_catchup` or queue lag above the published `1e-6` s tolerance invalidates monitoring; no one-period allowance |
| Source/residence/queue age bound | `max_result_age=0.5` s |
| Source mode / future tolerance | `live` by default, explicit `replay`; 0.05 s future tolerance |
| Continuity and drop accounting | Published topic/frame/header/reset rules and original skipped-stamp accounting |
| Runtime policy selection | Constructor and `DetectorNode.decision` reject v2; offline pure-module v2 remains callable |

The 16 queue, continuity, clock, and watchdog methods listed below were compared
by AST against the published baseline and are unchanged:

```text
_account_frame node_stats start_new_input check_continuity catchup_plan
on_cloud on_pending take_waiting prune process_next track_catchup
process_cloud begin_freshness on_watchdog subscribe remember_arrival
```

The retained P1 validation checks raw obstacle/warning booleans and health
independently through shared v1 **before** serialization, latch release, or
freshness health projection. Strings/integers are not accepted as flags. Invalid
raw health/flags produce invalid freshness, zero exposed clear/monitored range,
and FAULT or held STOP; catch-up projection cannot turn them into advisory-only
CAUTION. A strict true obstacle still has STOP priority with invalid monitoring.
The detector result is not mutated, and a genuinely fresh valid non-STOP result
can release the latch.

`DetectorNode.decision` delegates to `resense_ros.decision_policy`; the node has
no second v1 rule. Frame publishing calls `evaluate_decision` after freshness and
held-STOP projection. Status includes `decision_policy` and sorted, unique
`caution_reason` arrays, empty off CAUTION and in watchdog/processing-error
snapshots. Markers use the same accepted policy and word. Raw warning flags,
advisory boxes, and their topics remain available.

## Verification

The measured snapshot includes the integrated H1/H2/axis core. Source Git blobs
for the final tested owned Python files:

| File | Git blob |
|---|---|
| `ros2_ws/src/resense_ros/resense_ros/detector_node.py` | `b33f57bce6ff353930fce95e5c20a5f9b1908fc0` |
| `ros2_ws/src/resense_ros/launch/detector.launch.py` | `21ec3d31f26329891a394e0a78b11c9cd83ebeb7` |
| `tests/test_node.py` | `f410933e454c91066952935596a3337a534c26fd` |

Environment: Linux Docker image `resense:p1-combined-tools-7d3d5a05c258`, image ID
`sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`;
Python 3.10.12, Open3D 0.19.0. A fresh source snapshot was copied to `/source` in
the disposable container, then built/installed there with:

```text
python3 -m pip install --no-deps --no-build-isolation --force-reinstall /source
```

The runner's working directory was `/tmp`. It imported the current installed
`resense` from `/usr/local/lib/python3.10/dist-packages/resense/__init__.py`,
asserted native kernels were enabled, then added `/source` for scripts and ran
the source tests. The node fixture derives `NODE_PKG` from that source test file,
so node/launch verification did not accidentally use an old image overlay.
Native build output was confined to the disposable container.

```python
import sys
import open3d
import resense
from resense import _native
assert _native.enabled()
assert "dist-packages" in resense.__file__
sys.path.insert(0, "/source")
import pytest
raise SystemExit(pytest.main([
    "-q", "-rs", "-o", "cache_dir=/tmp/runtime-selection-pytest-cache",
    "--junitxml=/tmp/runtime-selection-results.xml",
    "/source/tests/test_node.py", "/source/tests/test_fastcloud.py",
    "/source/tests/test_decision_policy.py", "/source/tests/test_rescore_decisions.py",
]))
```

`RESENSE_REQUIRE_SYNTHETIC=1` and one-thread OMP/OpenBLAS/MKL were set. Final result:
**247 passed, 0 failed, 0 skipped, 0 deselected, 17.91 s**:

- node: 130;
- FastCloud: 62;
- pure decision policy: 48;
- rescoring: 7.

One pytest plugin assertion-rewrite warning concerned already imported `dash`.
JUnit results were retained outside the worktree at
`C:/Users/alikh/AppData/Local/Temp/opencode/runtime-selection-20261016-results.xml`.

All **51 published node test functions** remain. Their ASTs are unchanged except
the existing STOP recovery test adds assertions for policy/reason status fields.
S1-specific current-file tests were removed with their unaccepted implementation;
their original bytes remain in history. No published test was deselected or weakened.
Additional tests cover the source-AST published defaults, launch parity, runtime v2
rejection, strict dictionary decisions, raw-health/flag failures with and without a
STOP latch, source/residence ages, nonzero queue lag, and stable reason arrays.
The defaults snapshot is authenticated with `git show` when the pinned object is
available, and remains checked against source AST in shallow/installed fixtures.

`ruff check` on all three owned Python files: **PASS**. `git diff --check`: **PASS**.
The parent integration's full Linux detector gate and final complete CI remain
separate acceptance records. No sealed core, version declaration, or manifest was
changed by this runtime selection.
