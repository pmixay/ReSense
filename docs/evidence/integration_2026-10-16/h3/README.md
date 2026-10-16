# H3 combined detector — full Linux gate and explained frame comparison

**H3 gate PASS, exit 0. Ready for independent H4 review.**

Measured commit: **`f8c088dc4f3243fbd15a3aae9be0459e8a0aa941`**.
Same-runtime sealed control: `707ea9cda051369326fb9407c42488c1033dad76`.
The measured SHA is the actual detached Linux Git HEAD, not the later parent worktree HEAD.
`RUN.json` records both the measured SHA and the parent HEAD at evidence-copy time.

## Acceptance and coverage

| Check | Measured result |
|---|---|
| Full regression gate against the 29 September shell-off baseline | **PASS, exit 0** |
| Comparison against the retained same-Linux sealed control | **PASS** |
| Non-latency metric rows, against either control | **208 / 208 identical** |
| Gated metric rows | **146 passed**, no regressions or missing rows |
| Total metric rows | 224; the other 16 rows are informational latency metrics |
| Overrides / waivers | `config.set=[]`, `gate.allow=[]` |
| Normal gate outputs | All six recordings, Set O, and eight ride pieces: **15,269 frames** |
| Set F | All 30 sequences and **3,060 frames** |
| Complete raw + serialized frame comparison | **18,329 / 18,329 frames** |
| Observer coverage verification | **PASS**; every standard JSONL result/identity and Set F row aligned |
| Infrastructure contract checks | **6 passed** |
| Explanatory ride-piece replay | **1,409 frames**, zero raw/serialized mismatches outside registered timing telemetry |

The full 224-row tables are in `analysis/metrics_vs_same_runtime.{json,txt}` and
`analysis/metrics_vs_shell_off_2026_09_29.{json,txt}`. Both have no changed non-latency row,
no gated improvement, no gated regression, and no missing row. All 16 changed information
rows are latency. This is not a timing-performance improvement claim: Docker CPU was shared.

## Source, native backend and evaluation inputs

- Filesystem inventory: **36 files**, exactly matching measured Git blobs, clean LF bytes;
  `uncommitted_detector_changes=[]`, clean before and after the full gate.
- Candidate source digest:
  `a34cb1612f3f212d063370ebe0ad8648657aa15b62d751a69964eb1c825d3618`.
- Sealed-control source digest:
  `075a20df9fcdba6605a92e6505ae4dfdb3bf410ec09d17a8b3c79ce714db9292`.
  The control's existing seal verified PASS before and after its replay. The candidate is
  checked against its committed source inventory; this H3 measurement does not create a seal.
- Immutable tools image:
  `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`.
- Python 3.10.12, NumPy 1.26.4, SciPy 1.13.1, scikit-learn 1.5.2, Open3D 0.19.0.
  Package, import-path, compiler, CPU and cgroup provenance is retained for both runs.
- `bash scripts/build_native.sh` built the native backend in the Linux checkout.
  Its `.so` is ignored and outside seal scope; there is no Windows `.pyd`.
  Native binary SHA-256 is identical in both runs:
  `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
- Original read-only cache, unchanged input format: **15,499 files / 9,659,917,289 bytes**.
  Full input-inventory digest is identical:
  `87ad4712a99a3aeef62230388baec9ffd2e86c24c5a2036d6899fdd295761d9c`.
  Individual cache byte hashes remain external and are indexed by `EXTERNAL_ARTIFACTS.json`.
- Active gate, recording, Set F, cache, object-scoring and intake scripts, plus all label JSON,
  are byte-identical to the control and checked against their measured Git blobs. Their exact
  hashes are in `analysis/evaluation_and_config.json`. The wider Python-script inventory also
  records unrelated integration changes; it is not silently treated as identical.
- Canonical and ROS config files match exactly, SHA-256
  `1ff8f3de68a25dacc3f554f76383c27103b803c75d3478b16631313ab1a6e60c`.
  Fourteen additive configured keys cover column free-top hardening, surface-cut bars and the
  monitored-range cap; no preexisting configured value changed. The complete key diff is retained.
  Effective config SHA-256 is
  `10419e3190e4a86e859f9c344a41e0236514f4d1277da16eff5d1acfbf5c9e24`.
- The measured clustering import is `from resense.sensor import AZIMUTH_STEP_DEG, expected_points`.
  `measured_detector_changes.patch` retains the complete committed detector/config/build diff.

Controls are identical: `--jobs 2 --chunks 8`, actual receive stamps, default config, native enabled,
OMP/OpenBLAS/MKL/NumExpr threads 1, `PYTHONHASHSEED=0`, explicit checkout `PYTHONPATH` and
`RESENSE_REPO`. Maximum sampled candidate memory was **806.9 MiB**; container exit was 0,
`OOMKilled=false`. The gate's 836.7-second wall time is informational only.

## Every changed field group

Counts below include both raw and serialized representations and additive schema entries.
Changed-frame groups overlap; leaf/schema-entry counts are not counts of changed decisions.

| Group | Changed frames | Changed leaf/schema entries | Explanation |
|---|---:|---:|---|
| Obstacle / warning booleans | **0** | **0** | No STOP or advisory-boolean transition changed |
| Nearest / clear result | 1,834 | 3,668 | Clear reduced in raw and serialized output; nearest unchanged |
| Reported detections / warnings | **0** | **0** | IDs, reasons, geometry, confidence and all other fields unchanged |
| Candidates | 12,781 | 51,414 | 51,412 additive `cut`/`spared` entries; two preexisting categorical changes in one frame, traced below |
| Track model | 18,329 | 20,751 | Added raw `wall_drift` in every frame, plus 2,422 serialized annotations; all preexisting fields unchanged |
| Health | 2,422 | 12,774 | Added wall-drift annotations and intended monitored/clear reductions; other non-latency health unchanged |
| Ego motion / accumulation | **0** | **0** | All captured fields unchanged |
| Mount | **0** | **0** | All captured fields unchanged |
| Other result fields | **0** | **0** | Includes unchanged point counts and exact corridor-membership dtype/shape/hash |

All **88,607** changed leaf/schema entries are retained externally, with field-level counts and
examples in `frame_diff/summary.json` and `analysis/explained_frames.json`.
Every frame is marked changed in the generic report because raw `TrackModel.wall_drift` is a new
field even when its value is the no-cap sentinel `1e9`; this does not mean every decision changed.

### Intended axis-supported monitored/clear cap

Finite wall-drift evidence is reported in **2,422 frames**. It actually reduces monitored range in
**2,131 frames** and clear distance in **1,834 frames**. There are no increases.

For every one of the 18,329 frames, the explanatory checker independently verifies:

```text
monitored_new = round(max(0, min(monitored_control, wall_drift)), 1)
clear_new     = round(max(0, min(clear_control,     wall_drift)), 1)
```

The no-cap sentinel is `1e9`. These equations use the detector's existing one-decimal health
output representation; the full field comparator itself does not round or tolerate differences.
All three checked range fields—health monitored, health clear and result clear—match exactly:
**54,987 checks, zero mismatches**. All other non-latency scene-health fields and preexisting
track-model fields remain unchanged.

| Dataset | Frames | Monitored range reduced | Clear distance reduced |
|---|---:|---:|---:|
| doubleT_obstacle | 201 | 0 | 0 |
| doubleT_platform | 345 | 0 | 0 |
| roundT_doubleT | 252 | 8 | 8 |
| roundT_pressureGate_roundT | 268 | 134 | 131 |
| roundT_squareT_pressureGate_squareT | 545 | 110 | 110 |
| squareT_platform_squareT_switch | 877 | 46 | 45 |
| Set O | 1,510 | 193 | 159 |
| Ride | 11,271 | 1,550 | 1,348 |
| Set F | 3,060 | 90 | 33 |
| **Total** | **18,329** | **2,131** | **1,834** |

Examples with unchanged candidates/track geometry/corridor membership and unchanged STOP/warnings:

- `roundT_pressureGate_roundT_0013`: monitored and clear **170.2 -> 62.0 m**, wall drift 62 m;
  obstacle=false, warning=false, nearest=null in both runs.
- `new_data_3_0000`: monitored and clear **155.0 -> 134.0 m**, wall drift 134 m; no candidate in
  either run, obstacle=false and warning=false. This demonstrates a range-only change without
  changing the corridor or a decision.
- `cloud_with_fake_obj_0024`: monitored **158.5 -> 94.0 m**, clear **95.1 -> 94.0 m**.
- Set F `box0.5`, approach beginning at split 168, `new_data_169_0015`:
  clear **94.4 -> 94.0 m**, wall drift 94 m.

Per-dataset trace examples and exact raw field values are in `analysis/explained_frames.json`.
Median reductions among changed frames are 40.4 m monitored and 37.8 m clear; maximum reductions
are 160.3 m and 131.5 m respectively. These are reductions of a range claim, not obstacle-recall gains.

All **3,060 Set F scoring/placement rows** were compared. The only changed sequence-row field is
`mon` on **90 rows**. GT placement, injected point count, hit, false detections, candidate-match
flag and visibility are unchanged. The report's config hash changes with the configured additions.

### Non-axis candidate change: preserve it for H4

There are **25,706 candidate descriptors** across all frames. `cut` is false in all of them;
`spared` is true in **6** and false in 25,700. Thus this gate does not emit an accepted
surface-cut candidate; the registered H2 tests/probes remain relevant to independent review.

One preexisting raw candidate changes in exactly two categorical fields:

```text
ride piece new_data_1, row 1354, frame_id new_data_54_0009, candidate index 8
distance 73.55999755859375 m; n=25, n_gauge=25, ring_count=17
reason: "column" -> ""
zone:   "warning" -> "gauge"
```

This is the free-top/column-spare feature, not the axis cap and not a numeric-rounding difference.
`FrameResult.to_dict()` reports candidate count rather than candidate descriptors, so the ordinary
JSONL alone would not reveal it. The raw comparator retains it explicitly.

To explain persistence, `trace_h3_candidate.py` replays the original ride piece from its original
fresh-detector boundary with the committed source mounted read-only. All **1,409** replayed raw and
serialized non-latency results match the measured H3 run exactly. The trace records:

- `_uncorroborated_spare` receives prior spare history `[false,false,true,false]`, enough for the
  configured two-spare rule, and leaves this spared candidate in `gauge` with empty reason.
- The candidate belongs to **track 422**, whose resulting column history is
  `[true,false,true,false,false]`. With `column_hold=2`, `column_held=true`.
- Its zone history is `[false,false,false,false,true]`; `vote_zone`, `rule_zone` and final `zone`
  all remain `warning`. `reported=false`, `seen_reported=false`.
- At that frame obstacle remains false, nearest remains null, clear remains 44.6 m, and the existing
  warning list remains exactly unchanged. Track 422 is not in that reported list.

The trace and compact witness are `analysis/candidate_promotion_trace.json` and
`analysis/promotion_interpretation.json`. The initial structural classifier leaves the two fields
in `other_preexisting_field_change` / `other_or_unexplained_changes`; that bucket means outside the
range/additive-metadata classes. This section supplies their measured source/state explanation
rather than dropping them from the report. H4 should inspect this candidate promotion explicitly.

### Exact arithmetic and corridor-identity scope

The explanatory comparator compared **2,432,861 common captured raw numeric values** exactly.
Exactly **5,799** differ: 2,131 health monitored values, 1,834 health clear values and 1,834 result
clear values, all accounted for by the checked cap equation. There are **zero other unequal common
captured raw numeric values**. The categorical candidate changes above remain separate.

This establishes equality for the captured result fields, including unrounded candidate/detection
descriptors and point indices. It does **not** establish bit-identity of every internal intermediate
or arithmetic operation. Health/mount values may already be rounded internally; full processed cloud
arrays were not duplicated. Raw corridor-membership **dtype, shape and SHA-256 are identical in all
18,329 frames**, including frames with no obstacle. No corridor hash difference is hidden.

## Timing exclusions

The exact comparator normalizes only the pre-registered timing fields:

1. `timing_ms`.
2. `health.latency_p95_ms`, `health.latency_basis`, `health.latency_sample_age_frames`.
3. Health messages matching exactly `^latency p95 \d+ ms over the \d+ ms budget$`.
4. A proven latency-only `health.level=warn` with `decision_level=ok` and no remaining scene message.

Both effective configs explicitly set `latency_affects_decision=false`. Scene health severity,
decision levels, all remaining messages, all range fields and all track/candidate fields stay in
the comparison. The complete excluded timing audit remains external and is hash-indexed.

## Evidence layout and reproduction

- `candidate/`, `baseline/`: full gate JSON, all metric rows, source inventories, clean-commit/LF
  checks, native/config/hardware provenance, input identity, evaluator hashes, frame coverage and
  complete raw-artifact inventories.
- `frame_diff/`: compact full-field summary with counts/examples and every changed Set F scoring row.
- `analysis/`: complete metric tables, formula checks, category/field counts, range examples and
  the validated candidate-promotion replay/state witness.
- `helpers/`: measured gate/observer/comparator and explanatory/reproduction helpers.
- `measured_detector_changes.patch`: exact committed detector/config/build diff `707ea9c..f8c088dc`.
- `EXTERNAL_ARTIFACTS.json`: byte sizes/SHA-256 of complete external gate work, expanded captures,
  complete changes/timing audits, manifests and runtime provenance.
- `PACKAGE_MAP.json`: copy/derivation provenance; `.log` text is stored as `.txt`, and resource
  JSONL is losslessly represented as a JSON array so all compact evidence is normally Git-addable.
  `PACKAGE_TRANSFORMS.json` records exact before/after hashes for compact text whose CRLF line
  endings were normalized to LF. Original external evidence bytes are retained unchanged.
- `HASHES.json`: compact-package file inventory and SHA-256 values; it excludes itself.

External root:

```text
C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs
```

The run IDs are in `RUN.json`. Full 18k-frame raw/standard JSONL and complete diff JSONL remain
there, outside Git. The compact evidence folder is under 1 MB before this explanatory README.

Run a fresh measurement in that external root, where the retained sealed control is available:

```powershell
$runs = "C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs"
python "$runs\helpers\gate_control.py" --commit f8c088dc4f3243fbd15a3aae9be0459e8a0aa941
```

This generates uniquely named resources and a new full committed replay/comparison. The archived
`helpers/` copies can be restored to an external evaluation root with the retained control and
cache; raw data should stay outside this documentation folder.

The exact inner measurement command is retained in `candidate/commands.json`:

```text
python3 scripts/regression_gate.py --cache /data/cache --jobs 2 --chunks 8
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json
  --work /evidence/<candidate-run>/gate_work --out /evidence/<candidate-run>/gate.json
```

Explanatory replay/metric-collection argv and exit codes are in `analysis/analysis_commands.json`.
This is the pre-version H3 detector record for H4; the final committed H5 gate/reseal follows the
registered integration acceptance order.
