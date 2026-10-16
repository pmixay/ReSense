# Fresh independent H4 — revised shipping scope accepted

**ACCEPTED for the revised shipping difference `707ea9c..c9aea87`: no supported
NEW medium-or-higher finding remains in this review.** Reviewer authored none of
the production implementation or earlier H3/H4 reviews. This verdict was issued
after the replacement full H3 gate and withdrawal probes completed and their raw
evidence was independently recounted.

**The High inherited in-envelope tall-pole miss remains OPEN under criterion 8.1.**
H1/free-top is withdrawn, including its short-pole gain. Its original safety review
remains **BLOCKED** at its original source; attempt 08 remains rejected. This is
selected-difference acceptance, with that original defect explicitly outstanding.

## Exact reviewed source and evidence

- Full reviewed comparison: sealed **`707ea9cda051369326fb9407c42488c1033dad76`** to
  **`c9aea87cb5322092070158cd8987115ee44833c9`**.
- Withdrawal defaults: `795a243`; routing/experimental-test clarification: `c9aea87`.
  Later `829b243` adds only the author's withdrawal evidence.
- Replacement gate: [H3 selected](../h3_selected/README.md), run
  `candidate-c9aea87cb532-20261016T101302Z-8a9ae4d1`, **exit 0**, completed and
  verified. Sealed same-runtime run:
  `baseline-707ea9cda051-20261016T060147Z-68fb3429`.
- New author probes: [WITHDRAWAL_RESULTS.md](../h4_fixes/columns/WITHDRAWAL_RESULTS.md),
  `probes-c9aea87-20261016a`, `probes-sealed-707ea9c-20261016a`,
  `dark-c9aea87-20261016a`. These are reviewed measurements, separately attributed
  from this reviewer's new focused runs.
- Immutable Linux image:
  `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`.
  Native binary SHA-256, independently rebuilt in both private review checkouts:
  `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
- Selected 36-file source digest:
  `a73bc44642eb7d022e1433a763761f0f7e62bd0c5dfd93b4ad6db13660234aaf`.
  Canonical/ROS YAML bytes:
  `3936780252f00cf0dc34c9205b5633738368a0d5c3bdc4f07200d21d3de6143c`.
- Private review checkouts: `/work/selected` and `/work/sealed` in volume
  `rs-h4-selected-independent-c9aea87-01-source`. Actual imports, Git-blob/LF
  authentication and clean before/after inventories are in `run-003/identity.json`.
  That inventory also covers node/launch/shared-policy/import-helper sources.

[PROTOCOL.md](PROTOCOL.md) registers the independent checks before measurement.
All repository writes by this reviewer are within this folder. No G3 held-out
cases or specification were read or executed.

## Findings and disposition

| Severity / origin | Finding or earlier blocker | Revised-scope disposition and reproducible evidence |
|---|---|---|
| **High — inherited from seal; OPEN 8.1** | An in-envelope tall pole remains a column/advisory despite abundant strict-gauge evidence | `clustering.py:663–665`, `tracking.py:119–140`; unchanged legacy classification with free-top off. Original physical-ray case 45 remains the authoritative witness: 67 m, +0.68 m, width 0.46 m, physical top 3.22 m, 80 gauge voxels / 20 rings, no matched STOP. [Original BLOCKED report](../h4_safety/BLOCKED.md#high--inherited-tall-in-envelope-pole-miss). This review's mirrored supplied-coordinate 2.72/3.22 m controls also remain advisory in both sources (`run-003/paired.json`); they corroborate inheritance, without replacing the original physical-ray evidence. |
| **Medium — original experimental H1** | Exact inherited dark mask previously added **9 + 5** STOP frames | Withdrawn from shipping reachability. New entire-piece records independently recount to sealed **14 / 2**, zero added/lost STOPs, all detection/warning descriptors exact, all 5,065 candidates unspared and observer calls zero (`withdrawal_audit.json`). Historical enabled-feature finding stays recorded as BLOCKED. |
| **Medium — original experimental H1** | First returning clean hit lost STOP because an imputed column explanation survived | The shipping classifier produces no `spared` hits, so neither provisional explanation nor its re-arm discharge activates. New unspared paired sequences match sealed across 1,344 updates. The author's retained opt-in re-arm improvement is experimental-path evidence, with no shipping detection gain credited. |
| **New medium-or-higher** | None supported by this review | New focused checks, selected-gate recount and paired GT/probe results below. |

Reproduce the original physical-ray finding from its pinned original checkout with
`python docs/evidence/integration_2026-10-16/h4_safety/launch.py components candidate --run NEW_ID`
and select case 45 / highest / dropout 0, as specified in the preserved original
report. The withdrawal's explicit-on reproduction still fails the tall and
absorbing-continuation criteria; its successful *reproduction* exit code is not
feature acceptance.

## Independent new focused measurements

Pinned Linux, native enabled, one thread per numerical library. No duplicated full
gate or critical-probe replay was launched by this reviewer.

| Registered check | Result |
|---|---|
| Nine committed runtime/policy/health/native/structure/shipping/axis/explanation test files | **306 passed, zero failures/skips/deselections**, `run-003/pytest.xml` and `focused-units.txt` |
| Unspared Tracker paired histories | **64 exhaustive three-hit prefixes, 1,344 updates per source**, identical reported states, zones, column/measured-explanation histories and returning-hit behavior; no spare/provisional history activates |
| Labelled ordinary component controls | **6 paired mirrored faces**, short 1.7 m positive and 2.72/3.22 m inherited misses; exact sealed/selected candidate and STOP-frame sets |
| H2 direct physical angular/voxel boundary | **36 cases passed**: 7/8/9 actual voxels, 0.099999° / 0.1° / 0.100001° requested span, both sides, one/two echoes; angle independently measured from physical x/y, not corridor dy |
| H2 residual boundary | **6 controls** at 1.3 m ±10 micrometres and equality, mirrored. Strict below/above controls pass; equality records actual robust-fit outcomes rather than inventing a rounded equality oracle |
| H2 full paired clustering route | **36 identical inputs per source**; sealed accepts 0, selected accepts **16**, all supported entirely by labelled in-envelope part points, `cut=true`, `spared=false`; full outcomes in `run-004` |
| Actual low-duplicate filter | **5 controls passed**: four demoted cut reasons preserve the independent low object; clean gauge cut permits duplicate suppression |
| Axis boundary tables | **18 mirrored threshold/reference cases + 2 isolated negative controls passed**, including exact maximum reference offset, strict drift threshold, insufficient near anchors and single-bin rejection |
| Health min-cap matrix | **216 cases passed**, finite/no-cap/zero/negative caps, nearer/farther obstacles/candidates, two trusted ranges and hard faults; all non-range fields unchanged |
| Ordinary full Detector reachability | **16 frames**, class and canonical YAML routes; 16 candidates, expected near-object STOPs, forbidden observer never called; spare/provisional histories all false. Explicit positive opt-in control reaches the mocked observer once |
| Published runtime AST/defaults | **39 defaults preserved**, three additive v1 parameters, **37 methods identical**. Only constructor, freshness validation, decision/publish/fault and marker methods differ; focused tests cover strict validation, freshness, latch and runtime-v2 rejection |

Analytic surface and face clouds above are **supplied-coordinate component
controls**, with independently known axis/envelope and labelled points. They are
not represented as whole-scene physical-ray recall measurements. The full
Detector reachability cloud is independently generated; its positive box ensures
the disabled-path check is not a vacuous no-candidate stream.

Primary property results are `run-001/selected-probes.json`, continued only for
runtime in `run-003/runtime.json`, sealed pairing in `run-003/paired.json`, and
`run-004/{selected,sealed,paired}.json`.

## Independently recounted completed H3 and withdrawal evidence

`audit.py` performs read-only analysis of retained outputs. It authenticates both
before/after source maps against Git, rather than relying on report labels.

- **18,329 aligned raw + serialized H3 frames**, including **3,060 Set F rows**.
- **208/208 non-latency metric rows identical**, **146 gated rows pass**; no allow
  entries or configuration overrides. All **25,706 candidates have `cut=false`
  and `spared=false`**. Every preexisting candidate descriptor, detection/warning,
  nearest distance, track geometry, mount/ego result and corridor-membership hash
  matches sealed exactly after only registered timing normalization and the
  intended range/additive-field accounting.
- **2,422** finite drift frames, **2,131** monitored reductions, **1,834** clear
  reductions; **109,974 cap-equation checks**, counting three range fields in
  *both* representations. Zero other result difference remains. Set F changes
  only `mon`, in **90 rows**, with identical placement, injection and scoring.
- H3's ordinary corpus emits no H2-cut candidate. Independent H2 controls and the
  C-person probe therefore remain essential separate evidence for that path.
- A-axis (`pole_c`) has **82/177 visible matched STOP frames**, exactly sealed's
  scored frame set and placement. There are also three raw hit flags on invisible
  rows (`189,200,205`); the unchanged scoring excludes them. No 85/177 claim.
- C-person: **55/153**, first STOP **82.77 m**, frames **98–152**. Sealed has
  frames **104–152**, **49** hits; the six additions are **98–103**, with zero lost
  hits and identical placement. Placement follows the stored baseline fitted axis,
  as the original development probe documents; this is not independent real-track
  generalization evidence.
- Exact inherited observer pieces **1 and 3**, **1,409 frames each**, independently
  compared against the completed sealed H3 captures: **14/2 STOP frames**,
  zero extras/losses, exact full detection/warning descriptors, all common raw
  candidate fields/point-index hashes exact. Only intended range/axis fields
  differ. Empty observer/spares records and zero guard counters agree with the
  disabled route, rather than suggesting the enabled algorithm was repaired.
- Preserved failed acceptance bytes independently equal Git `4c6ea25`, SHA-256
  `b3102de04d108ff4f3ecce4cc9bed6b9a7f49d56927e5fc534a6ca4124b58ebb`.

Full recounts and the exact external-file byte hashes are in `h3_audit.json`
(107 files) and `withdrawal_audit.json` (16 files). Large raw data stay in their
original external run roots. The original H4 correctness PASS and safety BLOCKED
remain attributed to their original scope; neither substitutes for this review.

## Static implementation conclusions

- `clustering.py:269–289,812–898`: H2 runs only after the old oversize split refuses,
  requires strict-gauge support and robust surface/slope checks, applies the voxel
  and physical azimuth bar, and routes every part through ordinary classification.
  `detector.py:700–707` prevents a demoted cut part from removing a separate low hit.
- `config.py:263`, both YAML files, `detector.py:595–597` and
  `clustering.py:1005–1029`: zero is the master switch. The shipping detector
  supplies no ray context; even a direct caller supplying rays cannot create the
  callback with the master disabled. Explicit tall-gap settings cannot bypass it.
- `tracking.py:669,690–697`: all new behavioral branches require `cl.spared`.
  With no spares, measured explanations retain the sealed semantics. The additive
  all-false histories and provisional discharge do not alter shipping decisions.
  `clear_cap_distance`'s `column_held` property is the original predicate.
- `track.py:490–545,1019–1022`: drift is calculated against the final smoothed /
  rate-limited axis. It changes the reported monitoring bound, not fitted geometry
  or corridor membership. `health.py:213–232` applies a min-cap and preserves hard
  fault zeroing. The new full-frame audit confirms those actual output effects.
- `detector_node.py:976–1033,1175–1230` and shared `decision_policy.py`: raw flag /
  health validity precedes latch release and freshness projection, strict STOP has
  priority, and runtime remains v1. Original queue/clock/continuity methods and
  defaults are retained. The disabled S1 and rejected offline v2 gain no acceptance
  credit here. Source-aware policy import remains reviewed and covered by units.

## Reproduction and retained adapter failures

Fresh focused run: `python docs/evidence/integration_2026-10-16/h4_selected/launch.py`
in a new uniquely named run/volume (the provided fixed names protect the existing
record from overwrite). `resume.py` / `paired_h2.py` document this run's bounded
continuations. Commands, logs, container exit/OOM state, final source inventories
and package hashes are retained here.

Offline recounts:

```text
python docs/evidence/integration_2026-10-16/h4_selected/audit.py withdrawal
python docs/evidence/integration_2026-10-16/h4_selected/audit.py h3
```

They refuse to overwrite existing audit outputs; use a fresh copy of this evidence
folder when reproducing. Package verification is read-only:
`python docs/evidence/integration_2026-10-16/h4_selected/finalize.py --verify`.

`FOLLOWUP_01.md` retains two failed review-adapter runs: a method was called
`make_markers`, not the adapter's expected `publish_markers`; the first attempted
patch left that edit unapplied. `FOLLOWUP_03.md` retains the first offline H3
audit's mistaken whole-object equality across differing source-inventory metadata
schemas. Corrected checks preserved all source, geometry, behavior and tolerance
assertions. No production fix resulted from these adapter errors.

Final packaging corrected an arithmetic label of 54 to the actual **36** H2
angular/voxel inputs (`3 × 3 × 2 × 2`); the measured row arrays and outcomes were
unchanged. `FOLLOWUP_02.md` retains that original count-label correction.

**Parent handoff:** revised selected-scope H4 is accepted at the exact SHA above.
Inherited High 8.1 remains OPEN; H5's version-bumped committed gate/seal and H6's
CI/main acceptance remain the next parent-owned steps.
