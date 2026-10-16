# Replacement H3 — selected shipping detector after H1 withdrawal

**Full gate PASS, exit 0, on actual committed source
`c9aea87cb5322092070158cd8987115ee44833c9`.**

This is the replacement H3 record for the selected shipping configuration. H1's free-top
exemption is disabled by the committed class/canonical/ROS default `column_free_max_top=0`;
H2 structure cutting and the axis-supported monitored-range cap remain selected.
The shipping-selection protocol is `../h4_fixes/columns/WITHDRAWAL.md`.

The acceptance control is the retained clean Linux replay of sealed
`707ea9cda051369326fb9407c42488c1033dad76`. It was reused without repeating it.
The old `../h3/` record at `f8c088dc` remains historical and is not the acceptance record for
this selection. Its raw frames are used only to demonstrate removal of the previous promotion.

## Measured outcome

| Check | Result |
|---|---|
| Full gate vs 29 September shell-off baseline | **PASS, exit 0** |
| Full metric comparison vs same-Linux sealed control | **PASS** |
| Non-latency metric rows, against either control | **208 / 208 identical** |
| Gated metric rows | **146 passed**, no regressions or missing rows |
| Total comparison rows | 224; the remaining 16 are informational latency rows |
| Overrides / waivers | `config.set=[]`, `gate.allow=[]` |
| Required recordings and ride | Six recordings + Set O + eight ride pieces, **15,269 frames** |
| Set F | All 30 sequences and **3,060 frames** |
| Complete retained raw/serialized comparison | **18,329 / 18,329 frames** |
| Capture coverage | **PASS**, every normal JSONL result/identity and Set F row aligned |
| Frame-comparator contract checks | **6 passed** |
| H1 route selection | Class, canonical YAML, ROS YAML, measured YAML and resolved config all **0.0** |
| Source identity | Exact committed HEAD, clean before/after, **36 LF files** matching Git blobs |

Full 224-row JSON/text tables are in `analysis/metrics_vs_same_runtime.*` and
`analysis/metrics_vs_shell_off_2026_09_29.*`. All non-latency rows match; there is no gated
improvement claim. The 16 changed information rows are latency. Gate wall time was 911.3 s,
informational only on shared Docker CPU.

## Every frame difference vs sealed 707ea9c

Only the intended axis-related range changes and additive metadata remain. There is **no
preexisting candidate, STOP, warning, nearest-distance, detection-descriptor, track-geometry,
corridor-membership or other non-latency health change**.

Both raw and serialized representations are counted. Group frame counts overlap; schema
additions and duplicate representations are not distinct changed decisions.

| Group | Changed frames | Changed leaf/schema entries | Explanation |
|---|---:|---:|---|
| Obstacle / warning booleans | **0** | **0** | No changed STOP/advisory boolean |
| Nearest / clear result | 1,834 | 3,668 | Clear is reduced, in raw and serialized output; nearest unchanged |
| Reported detections / warnings | **0** | **0** | All IDs, reasons, geometry, confidence and descriptors match |
| Candidates | 12,781 | 51,412 | Two additive raw fields per descriptor: `cut=false`, `spared=false`; all preexisting fields match |
| Track model | 18,329 | 20,751 | New raw `wall_drift` in every frame; serialized annotation in 2,422; existing fields match |
| Health | 2,422 | 12,774 | Wall-drift annotations plus the intended monitored/clear reductions |
| Ego motion / accumulation | **0** | **0** | All captured fields match |
| Mount | **0** | **0** | All captured fields match |
| Other result fields | **0** | **0** | Includes point counts and exact raw corridor-membership identity |

All **88,605** changed leaf/schema entries have counts/examples in `frame_diff/summary.json`
and `analysis/explained_frames.json`; the complete value-by-value change JSONL remains external.
The generic report marks all frames changed because raw `TrackModel.wall_drift` is an additive
field even when its value is the no-cap sentinel `1e9`.

### Intended monitored/clear range cap

Finite wall drift is reported in **2,422 frames**. Monitored range actually decreases in
**2,131 frames**; clear distance decreases in **1,834 frames**. No range increases.

Each of the 18,329 frames independently satisfies the existing output-format equations:

```text
monitored_new = round(max(0, min(monitored_sealed, wall_drift)), 1)
clear_new     = round(max(0, min(clear_sealed,     wall_drift)), 1)
```

The no-cap sentinel is `1e9`. Health monitored, health clear and result clear are all checked:
**54,987 checks, zero mismatches**. The exact frame comparator itself introduces no rounding or
numeric tolerance; the equations account for the detector's existing one-decimal range output.

| Dataset | Frames | Monitored reduced | Clear reduced |
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

Examples, with unchanged preexisting candidates, track geometry, corridor and STOP/warnings:

- `roundT_pressureGate_roundT_0013`: monitored/clear **170.2 -> 62.0 m**, wall drift 62 m;
  obstacle=false, warning=false and nearest=null in both runs.
- `new_data_3_0000`: monitored/clear **155.0 -> 134.0 m**, with zero candidates and no obstacle
  or warning in either run. This is a range-claim change without changing the corridor.
- `cloud_with_fake_obj_0024`: monitored **158.5 -> 94.0 m**, clear **95.1 -> 94.0 m**.
- Set F `box0.5`, approach beginning at split 168, frame `new_data_169_0015`:
  clear **94.4 -> 94.0 m**, wall drift 94 m.

All **3,060 Set F scoring/placement rows** were compared. Only `mon` changes, in **90 rows**.
GT placement, injected point count, hit, false detections, candidate-match flag and visibility
are unchanged. The report's configuration hash changes with the committed shipping config.

H2 remains configured at tolerance 1.3, spread 0.12, fit fraction 0.8 and minimum 8 voxels.
All **25,706** candidate descriptors in this plain gate have `cut=false`; there is no emitted
H2-cut candidate or other H2 output effect in this corpus. The author/independent H2 tests and
probes remain separate evidence for that path.

### Previous H1 promotion is gone

Class/default/ROS/measured configuration routes all resolve `column_free_max_top=0.0`.
Every one of the **25,706 candidates has `spared=false`**, including all six that were spared
in historical H3. The previous preexisting-candidate difference now exactly matches sealed:

```text
ride piece new_data_1, row 1354, frame_id new_data_54_0009, candidate index 8
distance: 73.55999755859375 m; n=25, n_gauge=25, ring_count=17

                       sealed 707ea9c      historical f8c088dc      selected c9aea87
reason                 "column"            ""                       "column"
zone                   "warning"           "gauge"                  "warning"
spared                 field absent        true                     false
```

The selected candidate's entire preexisting raw descriptor matches sealed. At the frame,
obstacle remains false, warning true, nearest null and clear 44.6 m; reported detections and
warnings match sealed exactly, as they do over the complete gate.

An additional **all-18,329-frame historical-to-selected comparison** finds precisely **8 changed
entries in 6 frames**: six `spared: true -> false` values and the one reason/zone reversal above.
No serialized result changes relative to historical H3 outside registered timing telemetry.
This historical check is not used as an acceptance baseline. The full six-frame witnesses and
all eight changes are in `analysis/WITHDRAWN_RESULT.json`.

### Exact comparison scope

The explanatory comparator compared **2,432,861 common captured raw numeric values** exactly.
Only **5,799** differ: 2,131 health monitored values, 1,834 health clear values and 1,834 result
clear values, all accounted for by the cap equation. There are **zero other unequal common
captured raw numeric values** and no unclassified field change.

Raw candidate/detection descriptors include unrounded numeric values and point indices.
Raw corridor-membership dtype, shape and SHA-256 match in **all 18,329 frames**, including
decision-negative frames. This does not claim that every unrecorded intermediate, cloud array
or tracker-history operation is bit-identical; health/mount values may already be rounded
inside the detector. Independent withdrawal units/probes/dark evidence address additional H4
questions. No G3 held-out case is run here.

## Source, data and resource fingerprints

| Item | Identity |
|---|---|
| Measured commit / actual detached HEAD | `c9aea87cb5322092070158cd8987115ee44833c9` |
| Candidate source digest | `a73bc44642eb7d022e1433a763761f0f7e62bd0c5dfd93b4ad6db13660234aaf` |
| Canonical and ROS config bytes | `3936780252f00cf0dc34c9205b5633738368a0d5c3bdc4f07200d21d3de6143c` |
| Effective config | `ba23b06f460934b63478bcae5160376249a912570926d0fc6b5521e5b1073562` |
| Native `.so`, identical to sealed control | `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534` |
| Cache inventory, identical to control | `87ad4712a99a3aeef62230388baec9ffd2e86c24c5a2036d6899fdd295761d9c` |
| Immutable tools image | `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19` |
| External observer, identical to control | `183cf3bf791a1221d79ff4aec4de5400f4232aa65da0dfea97512003ab1122b7` |

The source inventory contains **36 clean-LF files**, each checked against its measured Git blob.
It is unchanged before/after replay; `uncommitted_detector_changes=[]`. The ignored generated
Linux `.so` is outside seal scope; no Windows `.pyd` is present. The retained sealed control's
existing seal verified PASS before/after its original replay. No new manifest is created here.

Native build: unmodified `scripts/build_native.sh`, g++ 11.4.0. Runtime: Python 3.10.12,
NumPy 1.26.4, SciPy 1.13.1, scikit-learn 1.5.2, Open3D 0.19.0. Package, import-path, compiler,
CPU, Docker and cgroup provenance is retained. `resense.__file__`, `PYTHONPATH` and `RESENSE_REPO`
point explicitly to the measured Linux checkout.

Original cache bytes and format are unchanged: **15,499 files / 9,659,917,289 bytes**.
Active gate/recording/Set F/cache/object-scoring scripts, all label JSON and intake are
byte-identical to the control and checked against measured Git blobs. Other integrated Python
script changes are inventoried separately. The active-input hash table is in
`analysis/evaluation_and_config.json`.

The controls are `--jobs 2 --chunks 8`, actual receive stamps, default config, native enabled,
OMP/OpenBLAS/MKL/NumExpr threads 1 and `PYTHONHASHSEED=0`. Docker CPU limit is two equivalents,
memory limit 4.5 GiB plus 2 GiB swap. Maximum sampled usage was **789.8 MiB**; final container
exit is 0 and `OOMKilled=false`. Shared-host timing remains informational.

## Timing exclusions and retained evidence

Only the registered timing telemetry is normalized: `timing_ms`, health latency p95/basis/sample
age, exact latency-budget messages, and a proven latency-only WARN with decision_level=ok and
no scene message. Both effective configs explicitly have `latency_affects_decision=false`.
All other health fields, decision levels, scene messages, range, candidate and track fields remain
compared. Full timing differences remain in the indexed external audit JSONL.

- `candidate/`, `baseline/`: full gate JSON and metric rows, source inventories, clean-commit/LF
  checks, native/config/hardware provenance, input/evaluator identities and frame verification.
- `frame_diff/`: complete compact field summary with examples and changed Set F scoring rows.
- `analysis/`: all metric rows, cap-equation checks, field/group counts, shipping-route proof,
  previous-promotion witness and complete historical comparison changes.
- `helpers/`: gate, observer, comparator, analysis, collection and package-verification helpers.
- `measured_detector_changes.patch`: zero-context committed diff `707ea9c..c9aea87`; use
  `git apply --unidiff-zero` if reconstructing from the patch. The actual commit is authoritative.
- `EXTERNAL_ARTIFACTS.json`: byte sizes/SHA-256 of every retained full raw/standard frame file,
  complete comparison/timing JSONL, provenance and historical comparison inputs.
- `PACKAGE_MAP.json` / `PACKAGE_TRANSFORMS.json`: copy/derivation and LF-normalization provenance;
  original external bytes remain unchanged. Text logs use `.txt`; resource JSONL is losslessly
  represented as a JSON array for ordinary Git addability. Compact compiler banners omit their
  terminal empty line; complete original stdout and exact transformation hashes are retained.
- `HASHES.json`: compact-package byte inventory, excluding the index itself.

The raw root is:

```text
C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs
```

Current run: `candidate-c9aea87cb532-20261016T101302Z-8a9ae4d1`.
Control: `baseline-707ea9cda051-20261016T060147Z-68fb3429`.
Current full diff and explanation are in `framediff-<current-run>/` and `analysis-<current-run>/`.
Raw frame JSONL stays external. `RUN.json` names the measured SHA and the parent HEAD when copied.

Reproduction from that external evaluation root, with its retained control and original cache:

```powershell
$runs = "C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs"
python "$runs\helpers\gate_control.py" --commit c9aea87cb5322092070158cd8987115ee44833c9
```

This produces a new uniquely named run rather than overwriting the measured record. The exact
inner gate command, native build and clone commands are in `candidate/commands.json`; analysis
commands and exit codes are in `analysis/analysis_commands.json`.

This record completes the replacement full H3 gate/frame comparison. The independent H4
re-review and later version-bumped H5 gate/reseal follow the registered integration order.
