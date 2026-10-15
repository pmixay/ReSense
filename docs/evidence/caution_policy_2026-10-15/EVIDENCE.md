# C1 startup: saved-output rescore and checks, 15 October 2026

**Result: v2 is not accepted.** At proposed defaults (D_c = 80 m, compact box
extent <= 3 m), this available-data rescore fails both the <= 25% empty CAUTION
target and in-gauge object-frame CAUTION-or-STOP retention. v1 remains the runtime
default in the shared module and existing consumers. See `CONTRACT.md` for the
API, proposed semantics, additive reason codes and parent integration details.

## Source and limits

- Worktree: `C:/Users/alikh/AppData/Local/Temp/opencode/rs-p1-policy`, branch
  `p1/decision-policy-2026-10-15`, based on `d0d17bb` (`origin/final/silent-misses`).
- Rescored **previously generated**, read-only outputs:
  `C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-runs/gates/baseline_work/`.
  Five empty bags + eight ride pieces = 13,558 frames; set O = 1,510 frames.
- The adjacent `baseline.json` identifies producer commit
  `264f5b29304fd685f4042ded9eb382070da90563`, branch `p3/range-screen`, version
  **1.0.0**, default configuration, no detector overrides, cache path
  `resense-p3-data/cache`, Windows Python 3.11.9 / numpy 2.4.4 and native kernels.
  `git diff d0d17bb 264f5b2 -- resense native configs
  ros2_ws/src/resense_ros/config pyproject.toml setup.py` is empty: these saved
  baseline detector bytes match this branch's detector base.
- These are the regression gate's cached-input outputs, **not final-1.1.0
  judge-runner / node-decoded acceptance evidence**. They differ from the old
  judge's 5,872 CAUTION / 173 STOP empty counts in C1. No claim is made to reproduce
  the historical offline ablation percentages; C1 did not specify that ablation's
  numeric compactness predicate, and this proposal defines its own explicit bar.
- Labels: existing `labels/cloud_with_fake_obj.json`; hash in the JSON report.
  Intent, plausibility, visibility and the measured-envelope subset are retained
  as separate definitions. There are 801 visible/plausible in-gauge object-frames,
  on 694 distinct frames; 505 object-frames have measured envelope points.
- The main checkout and this worktree do not contain
  `docs/evidence/judgement_2026-10-13/out/raw.tar.xz` or an unpacked `out/`.
  Available B/C range probe JSONs (e.g. `h1-probes/C_person_14.10.json`) contain
  decisions, nearby single-frame candidates and object visibility, but not the
  confirmed warnings plus health needed to reconstruct v2. Nearby B/C battery
  JSONL files are empty-background perturbations, not the labelled visible-object
  range tests. **B/C visible-object alert retention remains unmeasured.**
- No new detector replay, held-out data or held-out run, or detector tuning was
  performed. Existing synthetic unit fixtures were used only by consumer tests.

## Measured results

Full source hashes, policy/tool hashes, transitions, reason counts and all 19
lost-frame examples are in `scratch_baseline_rescore.json`.

| measure | v1 | proposed v2 | conclusion |
|---|---:|---:|---|
| Empty CAUTION / 13,558 | 5,710 (42.12%) | 4,130 (30.46%) | **FAIL** <= 25% |
| Empty STOP | 165 | 165 | unchanged |
| Empty FAULT | 0 | 0 | unchanged |
| All set-O CAUTION / 1,510 | 324 | 249 | descriptive only |
| All set-O STOP | 447 | 447 | unchanged |
| All set-O FAULT | 2 | 2 | unchanged |
| In-gauge object-frame CAUTION-or-STOP / 801 | 619 | 600 | **FAIL**, 19 losses; 96.93% v1-alert retention |
| Distinct in-gauge-frame CAUTION-or-STOP / 694 | 529 | 510 | **FAIL**, 19 losses; 96.41% retention |
| Measured-envelope object-frame CAUTION-or-STOP / 505 | 434 | 433 | **FAIL**, 1 loss; 99.77% retention |

Object-frame losses by label: small_center 2, small_on_rail 4, big_above 11,
thin_hanging 2. The other four in-gauge labels have no loss. In particular the
big_above losses at frames 584–594 are margin advisories at 100.74 down to 80.25 m;
the thin_hanging losses at 763–764 have a noncompact beyond-height-reference
warning. These are **frame-level alert retention** counts: an alert can be caused
by an unrelated object / structure. They are not object-matched detection recall.
The report's per-frame nonregression check does not let newly gained alerts
cancel lost v1 alerts.

`--require-targets` returned **1** as expected (two failed targets, B/C unmeasured).
No parameter search was made to force a passing number.

## Reproduce the rescore

Use the shared Python
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe`.
Set `PYTHONPATH` to this repository, its `ros2_ws/src/resense_ros`, and the approved
scratch resource adapter directory `C:/Users/alikh/AppData/Local/Temp/opencode`;
set `RESENSE_REPO` to this worktree and `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS`,
`MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS` to `1`. For backend tests append this
worktree's `webapp/backend` to `PYTHONPATH`.

From the worktree, PowerShell input construction (no detector execution):

```powershell
$base = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-runs/gates/baseline_work'
$bags = @('doubleT_platform', 'roundT_doubleT', 'roundT_pressureGate_roundT',
          'roundT_squareT_pressureGate_squareT', 'squareT_platform_squareT_switch')
$bags += 0..7 | ForEach-Object { "new_data_$_" }
$bags += 'cloud_with_fake_obj'
$inputs = $bags | ForEach-Object { "$base/$_.jsonl" }
& 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe' `
  scripts/rescore_decisions.py --policy v2 --require-targets `
  --out docs/evidence/caution_policy_2026-10-15/scratch_baseline_rescore.json @inputs
```

The script accepts full FrameResult JSONL and `judge_runner.record` JSONL
(`i`, `level`, `dlevel`, `warns[].d` aliases are expanded explicitly). It never
uses saved `decision` as a substitute for missing evidence. Use `--empty`,
`--objects` and `--range` to assign nonstandard filenames; full range records
also need a boolean `visible`. Decision-only range summaries are rejected.
Non-frame watchdog/error snapshots are excluded from per-frame counts. Duplicate
input paths are rejected. Missing targets report `not_measured` and never pass.

## Verification

Final targeted run: **220 passed, 3 deselected**, in 38.29 s, with the environment
above:

```text
python -m pytest -q
  tests/test_decision_policy.py tests/test_rescore_decisions.py
  tests/test_quality_acceptance.py tests/test_synthetic_sensitivity.py
  tests/test_synthetic_import_layout.py tests/test_cross_ring.py
  tests/test_thin_monitoring.py tests/test_node.py
  webapp/backend/tests/test_pure.py webapp/backend/tests/test_evaluation.py
  -k 'not source_identity_hashes_selected_detector_checkout and
      not cloud_stride_and_writer and not results_index_and_paging'
```

Coverage includes actual FrameResult / Detection / JSON equivalence, the valid
v1 precedence truth table, opt-in v2 reason / distance / compactness boundaries,
runtime parameter validation, STOP before health error (including held STOP
without current boxes), health and doubt retention, latency-only warnings,
invalid / missing advisory evidence, malformed flags / health, stable additive
reason serialization, no mutation, source and installed pure-module imports,
shared callables in all five consumers, and health-only cross-ring differences.
Rescorer checks cover label alignment, overlapping objects, visibility,
plausibility, intent versus measured envelope, losses, threshold boundaries,
judge aliases, ignored snapshots, duplicate paths, incomplete inputs and CLI
failure reporting.

The initial unfiltered run was **107 passed, 3 failed**. The three failures were
on unchanged Windows-specific code paths:

- `test_source_identity_hashes_selected_detector_checkout`: existing source
  identity uses Windows backslashes; its test expects POSIX separators.
- Backend `test_cloud_stride_and_writer` and `test_results_index_and_paging`:
  existing storage readers call `os.pread`, unavailable on Windows.

These are explicitly deselected above, not counted as passing. The backend
decision, summary and evaluation tests pass. Node tests were run read-only on
this branch's existing node; this does not verify the parent's future wiring.

`ruff check` on all nine changed/new Python files: **PASS** (ruff 0.11.13).
`git diff --check`: **PASS**. Changes are outside the detector seal; no detector
gate was rerun for this policy-only startup.

## Remaining acceptance conditions / handoff

1. Captain review of the proposed paragraph and explicit compactness definition;
   no organizer approval is recorded or implied.
2. Parent integrates the runtime policy parameters, word call and additive status
   fields into node/launch while preserving full freshness and STOP-latch logic
   (see `CONTRACT.md`). P2 consumes reason arrays in the displays.
3. On **final 1.1.0**, rescore five empty judge-path bags + ride: CAUTION <= 25%,
   and set-O in-gauge and B/C visible-object CAUTION-or-STOP no fewer than v1.
   Current proposed defaults do **not** satisfy the available-data checks.
4. Parent measures/tests the <= one-input-period catch-up freshness change:
   roundT_doubleT catch-up CAUTION 9 -> 0, with node safety invariants intact.
5. Integrated `tests/test_node.py`, Linux consumer/backend checks and CI Docker
   job green; confirm the final runtime version remains explicit and publish the
   accepted contract with captain review before opting into v2 in deployment.
