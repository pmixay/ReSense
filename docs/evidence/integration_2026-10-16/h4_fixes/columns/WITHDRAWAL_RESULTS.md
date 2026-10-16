# H1 withdrawal measurements — author results, 16 October 2026

**The registered author shipping-selection measurements are satisfied on
`c9aea87cb5322092070158cd8987115ee44833c9`.** The default free-top master switch is
0.0. Available impacted units pass with zero failures/errors/skips; A-axis is
**82/177**, C-person retains **82.77 m / 55**, and the entire inherited-dark ride
pieces retain sealed **14 / 2** STOP frames with exact serialized centers.

This fulfills the author protocol in [WITHDRAWAL.md](WITHDRAWAL.md). Independent
H4 clearance and the parent's full-gate/re-review decision remain pending. The
inherited tall-object miss remains **OPEN under criterion 8.1**. The earlier H4
free-top candidate/attempt 08 remains rejected; explicit opt-in is experimental.

## Completed-run reuse and scope

All detector/test measurements below were already launched and completed when
this continuation inspected the runtime. **Zero new measurements were launched.**
The continuation performed offline artifact, exact-comparison, input-byte and
source-identity verification and retained the actual results. All measurements
are covered by WITHDRAWAL.md items 1–4; no additional measurement registration was
needed.

External run root:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-h4-column-withdrawal-20261016/`.
Each run's original launch command, completion, log, identity, small result files
and frozen author adapters are copied under [withdrawal/runs/](withdrawal/runs/).
[runtime.json](withdrawal/runtime.json) records actual container IDs, start/finish
times, exit codes, environment and mounts. Names beginning `green-` are original
run names, not a statement that they passed.

| Existing run | Source | Actual outcome |
| --- | --- | --- |
| `red-fc89ad2` | `fc89ad2` | Expected pre-config red: **11 failed**, 0 passed, 0 errors/skips; exit 1 |
| `green-795a243` | `795a243` | **259 passed, 1 failed, 6 deselected**, 0 errors/skips; exit 1 |
| `tests-c9aea87-20261016a` | `c9aea87` | **260 passed, 6 deselected**, 0 failures/errors/skips; exit 0 |
| `probes-c9aea87-20261016a` | `c9aea87` | A-axis 82/177; C-person 82.77 m / 55; exit 0 |
| `dark-c9aea87-20261016a` | `c9aea87` | Entire pieces 1/3: 1,409 frames each, 14/2 STOP; exit 0 |
| `experimental-c9aea87-20261016a` | `c9aea87` | Explicit-on controls reproduce both known unmet criteria; exit 0 for reproduction |
| `probes-sealed-707ea9c-20261016a` | `707ea9c` | A-axis 82/177; C-person 73.94 m / 49; exit 0 |

The separate parent-owned whole-gate container
`rs-gate-candidate-c9aea87cb532-20261016t101302z-8a9ae4d1` was observed running
during packaging. Its outcome belongs to the parent. This report covers
withdrawal measurements only.

## 1. Units and retained red evidence

[units.json](withdrawal/units.json) is parsed from original JUnit XML and includes
every executed case and the six deselection reasons. The final suite ran the 19
registered column, tracking/re-arm, structure, native, synthetic, CLI and default
test files in the pinned Linux image with `RESENSE_NATIVE=1` and
`RESENSE_REQUIRE_SYNTHETIC=1`. It includes all **11 shipping expectations**,
**28 native tests**, and **40 synthetic sensitivity/diagnosis tests**.

The initial `795a243` failure was
`tests/test_structure_cut.py::test_a_cut_part_meets_the_column_rule_and_its_free_top_test`:
that algorithm test still inherited the newly disabled default. Its already
committed explicit opt-in clarification at `c9aea87` is included in the final
260-pass result. The failed run and expected pre-config 11-failure witness are
retained verbatim, including their nonzero completions.

The six deselections are existing `realdata(path)` collection behavior in
`tests/conftest.py`: five require
`D:/Datasets/ReSense/cross_ring_2026-09-28_measurement`, and one requires
`C:/Users/alikh/AppData/Local/Temp/opencode/fresh-stop-positive-stress`.
They are not six passing cases; their exact names/reasons are preserved in
units.json and the log. There were **zero pytest skips**.

The withdrawn failed acceptance file remains byte-exact against `4c6ea25`:
7,051 bytes, Git blob `8e82688d6765de842bfb9597bf82ea9776b880a9`, SHA-256
`b3102de04d108ff4f3ecce4cc9bed6b9a7f49d56927e5fc534a6ca4124b58ebb`.
See [withdrawn_test_byte_proof.json](withdrawal/withdrawn_test_byte_proof.json).
Archival is not a passed acceptance criterion.

## 2. Unchanged critical development probes

The original `range_test.py`/`judge_runner.py` and node-decoded inputs, stored
baseline placement and ICP odometry were reused. Their source hashes and the
post-run input-byte inventory are in
[helper_source_identity.json](withdrawal/helper_source_identity.json) and
[probe_input_identity.json](withdrawal/probe_input_identity.json).

| Probe | Actual withdrawal result | Exact registered-reference comparison |
| --- | --- | --- |
| A-axis / raw output name `pole_c` | 340 processed frames; **82 matched STOP / 177 visible**, first STOP 218.38 m | Same visible matched frame set and summary as sealed `707ea9c`; zero lost/added matched frames |
| C-person | 268 processed frames; **55 matched STOP / 153 visible**, first STOP **82.77 m**, held-from 91.63 m | Same 55 matched frames, `k=98..152`, and summary as retained parent `f3074cf`; zero lost/added matched frames |

The sealed C-person control is **73.94 m / 49**, `k=104..152`. Withdrawal retains
the parent's six additional matched frames `98..103`. This comparison distinguishes
the sealed baseline from the registered C-person retention expectation.

[probe_comparison.json](withdrawal/probe_comparison.json) preserves both raw
per-row hit sets, summaries, unchanged object placement fields and sealed
comparisons. The launch worker's `matched_stop_frames` lists every raw `hit=True`
row: A-axis has **85** such flags, including `k=189,200,205` with `n_obj=0`.
The unchanged range-test scoring rule counts only visible object frames
(`X > 3`, `n_obj > 0`), giving the required **82/177** on both sources.
[probe_scoring_details.json](withdrawal/probe_scoring_details.json) preserves the
exact scored 82-frame sets and all three excluded rows. C-person has no such
excluded hit rows. All A-axis raw rows also match sealed exactly; C-person raw
row differences against sealed are retained at `k=94..103`.

The probe shipping guard covered **608 frames / 1,037 candidates**, with zero
free-top calls, spared candidates, provisional histories or spare histories.

## 3. Entire ride pieces through the exact inherited dark observer

The unchanged observer is `h4_safety/replay.py` from `838dd32`, SHA-256
`c772069e053b45566ccdffcbec1b9bc5ce8263dd96c0da3504df94d5ec844f07`.
The author adapter substitutes its verified config through `common.identity`,
installs a raising `top_is_free` guard, then calls
`replay.main(["--mode", "dark-inherited"])`. The inherited mask code is
unchanged; the effective master switch prevents entering it. Any observer call
would reach the raising guard before it could produce a record.

| Entire piece | Frame span | Frames / candidates | Sealed plain → withdrawal STOP |
| --- | --- | --- | --- |
| 1 | `new_data_27_0032` through `new_data_55_0012` | 1,409 / 2,805 | **14 → 14** |
| 3 | `new_data_82_0045` through `new_data_110_0025` | 1,409 / 2,260 | **2 → 2** |

Both are the complete zero-based pieces 1 and 3 of the natural-order 11,271-frame
ride split into eight pieces, exactly as the inherited adapter selects them.
[dark_details.json](withdrawal/dark_details.json) verifies that completeness and
every consumed cache file's raw SHA-256 against the logged input identity.
Ordered frame IDs, timestamps, compact-array identities, cache bytes and all-true
input masks match the sealed plain replay in
[dark_input_identity.json](withdrawal/dark_input_identity.json).

The fail-fast [shipping guard](withdrawal/runs/dark-c9aea87-20261016a/results/shipping_guard.json)
records **2,818 frames / 5,065 candidates**, **0 free-top calls**, **0 observer
calls**, **0 spared candidates**, **0 provisional tracks**, and **0 spare-history
tracks**. Every JSONL observer/spares record is empty and every candidate is
unspared.

[dark_comparison.json](withdrawal/dark_comparison.json) preserves every STOP ID
and serialized detection center. Both pieces have **zero extra/lost STOP frames**
and **zero detection- or warning-center multiset differences**, with **zero
tolerance** and no added rounding or spatial rematching. Detection/warning
descriptors also match exactly on every frame. Full serialized records differ on
32 / 169 frames, solely in wall-drift and clear/monitored-range fields; exact
field values and path counts are in dark_details.json. These are not represented
as full-record equality.

Sealed plain reference:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-integration-h4-safety-20261016/run-001/replay-sealed-all/`.
Its identity/completion are retained under [withdrawal/reference/](withdrawal/reference/),
and its raw ride JSONL hashes are in the external artifact manifest.

## 4. Explicit-on feature remains rejected

The completed experimental control changes only the copied effective config's
`column_free_max_top` to **2.95**, using the byte-preserved acceptance helpers:

* `case45_tall_miss`: `zone=warning`, `reason=column`, `spared=false`, 80 gauge
  points / 20 rings; the inherited tall-object miss remains.
* `absorbing_continuation_false_free_evidence`: `zone=gauge`, `reason=""`,
  `spared=true`, 68 gauge points / 17 rings; false free-top evidence remains.

The actual coordinates' hashes, heights and outcomes are in
[experimental_still_rejected.json](withdrawal/runs/experimental-c9aea87-20261016a/results/experimental_still_rejected.json),
whose `accepted` field is **false**. Exit 0 means faithful reproduction of known
rejected behavior. Historical attempt-08 source reconstruction, failures and
reports remain the earlier evidence for its rejection.

## Provenance and package verification

All measured candidate jobs import clean detached committed source from
`/source/repo/resense/__init__.py`, with per-file LF bytes verified against Git.
The image is Linux/amd64, native enabled, network disabled; cache, decoded,
odometry, observer and frozen adapter mounts are readonly. Native code is the
previously pinned Linux binary copied from the readonly H3 reference volume.
All numerical thread limits are 1, and `PYTHONHASHSEED=0`.

| Identity | SHA-256 / value |
| --- | --- |
| Measured Git commit | `c9aea87cb5322092070158cd8987115ee44833c9` |
| Linux/Open3D image | `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19` |
| Native `_resense_native.so` | `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534` |
| 36-file source/config manifest | `a73bc44642eb7d022e1433a763761f0f7e62bd0c5dfd93b4ad6db13660234aaf` |
| Effective config, sorted JSON with default separators | `bcb17deab69ec0eba0b030c9c8386743a962c0b77d46345bccc8b59c92481b92` |
| Canonical YAML and identical ROS mirror bytes | `3936780252f00cf0dc34c9205b5633738368a0d5c3bdc4f07200d21d3de6143c` |
| Sealed probe source manifest | `075a20df9fcdba6605a92e6505ae4dfdb3bf410ec09d17a8b3c79ce714db9292` |

[EXTERNAL_ARTIFACTS.json](withdrawal/EXTERNAL_ARTIFACTS.json) inventories all seven
completed run folders, the used sealed replay artifacts and the retained parent
C-person control, with raw byte lengths/SHA-256. Large raw ride JSONL files remain
at their recorded external locations. [PACKAGE_HASHES.json](withdrawal/PACKAGE_HASHES.json)
hashes the Git-retained text with LF normalization, including this report.
[VERIFICATION.json](withdrawal/VERIFICATION.json) records author measurement
fulfillment and explicitly records `independent_H4_clearance=false`.

Read-only package verification, without launching a measurement:

```powershell
python -B docs/evidence/integration_2026-10-16/h4_fixes/columns/withdrawal/package.py --verify
```

**Remaining review boundary:** parent-owned full gates and independent H4 re-review
against `707ea9c`; inherited criterion 8.1 tall-object miss OPEN. The six named
external-data unit deselections remain a coverage limit of this unit artifact.
No withdrawal measurement is pending.
