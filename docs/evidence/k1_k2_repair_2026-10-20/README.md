# K1/K2 author repairs — K2/K1 stay off in 1.2.0

**Date:** 2026-10-20. **Author role:** P3, reassigned by the user after the
[independent v5c review](../k1_k2_review_2026-10-20/README.md).
**Branch:** `fix/k1-k2-repair-20261020`. **Latest detector edit:** `ead83747` (r5a).
The original detector is `f56ad5e6`; current main `84534583` was merged before
implementation and does not change those detector bytes. The paired parent
`3ad151d0` carries review documents and regression tests but that same detector.

**Deadline disposition, 20.10: K2/K1 stay off in 1.2.0. Enablement is NO-GO.**
The registered original acceptance criteria still apply. This branch publishes
the completed author repairs and their passing/failing rows; it does not request
switch-on, resealing or acceptance of unmeasured final-source behavior.

**K1/K2 acceptance is not complete.** R3's missing-floor
fallback retains K2's output restriction and dual-axis marker. K1's stationary
averaging/rate floor now counts elapsed nominal periods. R4 addresses speed
reacquisition; r5/r5a address clipped low-object shape. R4 targets and r5 raw replays
are now complete and still fail acceptance; r5a follow-ups are identified separately. Both configuration
defaults remain off. The original positive-object losses remain grounds for
NO-GO. This author report is not independent acceptance or a captain decision.

**Limit of the repair for review finding R5:** r3 bounds a held range spatially by the last output;
it does not add a time limit to the original estimator's missing-floor hold.
Consequently the earlier review's prolonged stale-trust concern remains open.
The rejected 20 m/frame timeout demonstrates why restoring cap bookkeeping
alone must not be presented as full missing-observation acceptance.

## 1. Changes and registered revisions

| revision | exact detector edit | result |
|---|---|---|
| [r1 protocol](PROTOCOL.md) | `69ce0259` | Preserved the cap, but added 20 m/period expiry through missing observations. Rejected after full Falcon showed additional near-person losses. |
| [r2 K1 cadence](K1_CADENCE.md) | `7c0dfe56` | Minimum EMA exponent/rate multiplier scales with its respective elapsed-period switch. r1's expiry was still present. |
| [r3 finite hold](R3_REACH_HOLD.md) | `64f5d74c` | Missing-floor output holds the last finite cap; missing-wall fallback intersects it with the base estimator's existing contraction. Fresh observations replace it normally. Removes r1's additional person losses. |
| [r4 speed recovery](R4_SPEED_RECOVERY.md) | `a40cd692` | K1 opts into a jump-confidence bound proportional to elapsed time since the last accepted speed. A recovered distant value is not smoothed toward stale speed. Current confidence remains required. |
| [r5 low context](R5_LOW_CONTEXT.md) | `cdb6f692` | With K2, upper corridor returns outside the low band describe the connected straddle body's shape. Strict voxels, qualifying height and collision distance are counted separately. Three marked bags and Set O complete: marker 19 still loses frame 259. |
| r5a cap interaction | `ead83747` | R5's outside context could start before the reach cap while the strict intrusion started beyond it. Two registered numpy/native regressions reproduced this; the dual check now uses the low body's strict collision distance. Final candidate measurements remain required. |

Through r3, `resense/track.py` is the only behavioral change. R4 adds changes to
`resense/egomotion.py` and its detector wiring; r5/r5a change the low clustering
and detector straddle/dual stages. `resense/config.py` and both
YAML copies have comment updates only; all class-default values equal the
parent. Changes preserve the independent base estimator: output restrictions
do not feed back into `prev.base`. Empty boundary arrays also cannot release a
previous cap when output switches back to the base shape.

The r1 regression was committed before its failing run (10 failures / 4
controls passing after correcting the uncapped wall-drift control). Both K1
cadence tests failed before r2. Revised r3 tests failed before the r3 edit;
the recovery check was corrected to compare with a fresh observation, which
may legitimately shorten as well as lengthen range.

## 2. Checks and exact-source recordings

- **149 tests pass, zero skips**, including numpy/native observation-loss,
  recovery, repeated dropout, dual classification, rotation, cold start,
  cap-disabled/off controls, K1 EMA/rate-limited 5/10 Hz equivalence and
  moving/unknown-travel/per-frame controls, plus existing track/gauge/native
  regression tests. `open3d==0.19.0` was installed to run the two formerly
  skipped synthetic native controls. [JUnit](k1-k2-r3-tests-complete.xml),
  [receipt](k1-k2-r3-tests-complete.txt).
- ROS/canonical parameter synchronization and pinned Ruff 0.15.8 pass.
- R4: **115 tests pass**, zero skips, after three registered failures (two
  numerical recovery/cadence failures plus the K1 wiring). R5: **103 low-object
  tests** and **115 wider detector/native tests** pass, zero skips. These are
  separate runs, not a sum of distinct acceptance tests. R5a: **56 affected
  low-context/K2 tests** pass after both cap-interaction regressions failed.
  Receipts are `k1-k2-r4-*`, `k1-k2-r5-*`, and `k1-k2-r5a-*` in this folder.
- The old detector integrity seal failed on r3's four intentionally changed
  files; later revisions also change detector/clustering/ego-motion source.
  A new seal requires the final measured source and P1's disposition;
  the old seal has not been relabeled as a pass.
- Runtime: Python 3.12.15, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2;
  `OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`.
- Raw replays use `judge_runner_set.py` and exact source manifests from
  [run_recordings.py](run_recordings.py). [score_recordings.py](score_recordings.py)
  checks full lengths, ordered IDs, header/receive times, topic and frame ID.
  Timing/explicit latency-only health changes are separately recorded. Controls
  reject timestamp misalignment and detect a planted axis change / removed hit.

**Final full gate / X3 acceptance remains open.** The historical results
and the completed r3-only runs do not substitute for final-source acceptance.
Recovery receipts and the exact unfinished work are listed in [RECOVERY.md](RECOVERY.md).

### R3 default-off X3: PASS from the immutable checkout

The frozen `64f5d74c` run is complete: **40 cases /29,765 frames /260 comparisons**,
zero worker errors, no changed inside-object hit sets. The raw/completion audit
reproduces all metrics and its planted-loss controls pass.
[Report](x3-r3-off-frozen.json), [audit](x3-r3-off-frozen-audit.json),
[raw archive](x3-r3-off-frozen-raw.tar.xz),
[archive hashes](x3-r3-off-frozen-raw-package.json).
This supersedes the invalid mixed-HEAD execution below, not the enabled failure.

### R3 enabled X3: FAIL, independently re-scored from its raw outputs

The frozen evaluation checkout `d10f2b5a` contains r3 production source and the
five v5c-15 parameter overrides. **40 cases / 29,765 frames / 260 comparisons**,
no worker errors, **six failing comparisons**:

| case | metric | reference → r3 |
|---|---|---:|
| doubleT_obstacle / roll +2° | total STOP frames; crossing inside STOP frames | 192→188; 60→56 |
| doubleT_obstacle / dropout seed 2 | crossing inside STOP frames | 61→58 |
| doubleT_obstacle / deduplicated returns | crossing inside STOP frames | 61→58 |
| Set O / 5 Hz | total STOP frames; small_center inside STOP frames | 218→214; 18→14 |

[Report](x3-r3-v5c15.json), [raw archive](x3-r3-v5c15-raw.tar.xz),
[byte-verification manifest](x3-r3-v5c15-package.json),
[author raw audit](x3-r3-v5c15-audit.json). The audit verifies every raw-row
summary and completion identity, re-derives inside-object counts with a second
matcher, and detects deliberately removed detections / a three-frame metric
loss. It compares every source fingerprint except machine-local directory
paths (an initial whole-source equality check correctly exposed relocation).
The audit also reports all per-object lost/gained frame IDs, including losses
within X3's original two-frame tolerance and losses hidden by aggregate gains.
This second-method audit is not a different reviewer's acceptance.

### K1 targets: complete on r3, acceptance fails

[Protocol](K1_TARGETS.md), [scorer](score_targets.py),
[report](targets-r3-report.json), [raw outputs](targets-r3.tar.xz).
All **12 target runs equal their plain counterparts in every output field**.
Each uses its own object-free axis placement, as the registered original harness
does; therefore this is not a common world-coordinate target between variants.

| variant | 100 m STOP / visible | 150 m STOP / visible | appearance: first STOP delay | empty platform episodes | doubleT obstacle STOP |
|---|---:|---:|---:|---:|---:|
| off | 82/260 | 90/259 | 28 frames | 3 | 193/201 |
| K1 only | 84/260 | 98/260 | 11 frames | 4 | 193/201 |
| K2 v5c-15 | 255/260 | **0/260** | 5 frames | 0 | 193/201 |
| K1 + K2 | 255/260 | **0/260** | 5 frames | 0 | 193/201 |

The 150 m requirement remains at least 150 matched STOPs. Its visible denominator
is now 260 for the enabled variants; the off reference reproduces 259. Counts
are reported as measured, without coercing visibility to match history.
All 255 K2 100 m detections and all 165 sudden-appearance detections include
current injected returns. The off 150 m positional count decomposes into
**65 source-participating current detections, 14 held detections, 11 current
detections without injected returns**. This does **not** give 65 independently
correct person detections: a fixture and the injected target can merge (e.g.
frame 414: a 2.55 m long cluster starts at 147.46 m while including 18 injected
returns from the target placed at 150 m). The older background-coincidence
analysis and this source-participation check answer different questions; neither
alone supplies an independent object label.

The independent motion check reproduces all 260 standing ICP steps to B6's
published rounding (maximum delta 4.96e-8 m); the clipped/median-smoothed travel
over frames 360–619 is 0.01068 m. A moving-section positive control gives
108.59 m over frames 100–199. [Receipt](icp-standing-check.json).

**New diagnostic finding:** in the K1-only 150 m run, `_travel` is known on only
10/260 standing frames (four exactly zero). With both switches on, it is unknown
on **260/260**. Thus K1's cadence repair is not a standstill-recognition repair;
the distance-based branch is never entered during that combined target interval.
The trace also shows K2 150 m source-participating clusters rejected as
`beyond_axis` (e.g. 414/450/500/550) and `beyond_height_ref` (600). At combined
frame 500 a gauge candidate exists but is not yet reported. These sampled
mechanisms must be kept distinct from a claim that every miss has one cause.

A follow-up [travel trace](travel-diagnostic.json) still equals the plain run
on all 620 rows. Its last accepted travel sample is frame **128**; the stored
speed then remains **13.24867 m/s** through frame 619. During deceleration,
current profile speeds around 3.9, 0.95 and 0 m/s have correlations 0.80, 0.72
and 0.73, but the frame-to-frame jump penalty compares them with that arbitrarily
old accepted speed and halves confidence below 0.5. This prevents reacquisition
and also prevents K1's existing low-last-speed standstill fallback. A next
candidate must age that comparison without treating low-confidence unknown
motion as measured zero.

Measurement incident: the first r3-off X3 run used this author checkout while
documentation commits were being added. Its detector source tree was unchanged,
but workers recorded different HEAD commits, so the battery correctly returned
**ERROR**, not PASS. Its completed repeat from detached immutable `64f5d74c`
passes, as recorded above. The enabled X3 uses the separate immutable evaluation checkout
`d10f2b5a` (only its five evaluation parameters differ from r3).

### R4 K1 targets: complete, acceptance still fails

Exact source **`a40cd692`**. All 12 trace/plain target pairs equal; all eight
recording controls are complete. Only the interrupted combined crossing control
was restarted (164 old rows preserved, fresh full 201-row run).
[Report](targets-r4-report.json), [raw package](targets-r4.tar.xz),
[hashes and recovery receipts](targets-r4-package.json).

| variant | 100 m STOP / visible | 150 m STOP / visible | appearance delay | empty platform episodes | crossing STOP |
|---|---:|---:|---:|---:|---:|
| off | 82/260 | 90/259 | 28 frames | 3 | 193/201 |
| K1 only | 84/260 | 87/260 | 11 frames | 4 | 193/201 |
| K2 v5c-15 | 255/260 | **0/260** | 5 frames | 0 | 193/201 |
| K1 + K2 | 255/260 | **0/260** | 5 frames | 0 | 193/201 |

The original 150 m minimum remains 150 matched STOPs. In the combined 150 m
run, travel is unknown on **260/260 standing frames**. The final stored speed
is now about 0.003324 m/s rather than r3's 13.24867 m/s, but current profile
confidence remains insufficient (frame-619 input correlation about 0.327).
R4 removes the demonstrated stale jump bound; it does not establish usable
standing motion estimates or meet the K1 target. Combined 100 m has known
travel on just one of 260 frames. Source-participation diagnostics and their
planted-removal checks remain in the report, separate from positional scoring.

### R5 marked bags and Set O: complete, one original marker frame still lost

Exact source **`cdb6f692`** against frozen r3 **`64f5d74c`**. All **3,177 default-off
rows** equal the r3 reference after the explicit timing normalization. R3's
previous default-off identity to the original parent is documented above/below.

- Tunnels marker 19: **29 →28 STOPs**, only **frame 259** lost. R5 recovers 15
  of r3's 16 lost frames; first STOP improves from r3's 27.607 m to **53.359 m**,
  still below the original **54.994 m**. Other gains do not cancel this loss.
- Platform/switch: r5 enabled output equals r3 enabled output in all non-timing
  fields. Their gains relative to off are existing K2 effects, not r5 gains.
- Set O: one non-timing payload row changes versus r3/on, frame **739**: low
  object's width 1.94 →1.95 m, lateral 0.10 →0.11 m, center Y 0.04 →0.05 m.
  STOP, distance 10.95 m, support, confidence and age are unchanged.

Audits: [tunnels](r5-synthetic_tunnels_cloud_with_markers-audit.json),
[platform](r5-synthetic_platform_cloud_with_markers-audit.json),
[switch](r5-synthetic_switch_cloud_with_markers-audit.json),
[Set O](r5-cloud_with_fake_obj-audit.json). All complete raw pairs, source
manifests and archive-input receipts are under [`runs/`](runs/).
These are r5 results; r5a's cap-interaction follow-ups are not inferred from them.

### R5a marked / Set O follow-up: complete, the original frame remains lost

Exact source **`ead83747`**, measured separately on all three marked bags and Set O.
All **3,177 default-off rows** agree with the frozen reference. The marker
results remain **28/29** for tunnels object 19, with frame **259** lost and
first STOP **53.359 m**. Platform/switch enabled outputs still equal r3/on.
The completed r3 reference rows were reused with source and byte hashes;
only r5a was replayed. [Tunnels audit](r5a-synthetic_tunnels_cloud_with_markers-audit.json),
[platform audit](r5a-synthetic_platform_cloud_with_markers-audit.json),
[switch audit](r5a-synthetic_switch_cloud_with_markers-audit.json), raw manifests
under [`runs/`](runs/). [Set O audit](r5a-cloud_with_fake_obj-audit.json) reproduces
the single payload change versus r3/on at frame 739. The [r5a-versus-r5
comparison](r5a-vs-r5-audit.json) finds zero non-timing changes in both modes
across all four recordings. This measured equivalence does not accept the
remaining original losses or replace final-source gate/X3/target checks.

### Falcon: all 4,443 frames per run

| person retention row | original off | original v5c-15 | r2 v5c-15 | r3 v5c-15 |
|---|---:|---:|---:|---:|
| person-matched STOP frames | 1,360 | 1,366 | 1,356 | 1,366 |
| first matched STOP frame | 2,972 | 2,979 | 2,979 | 2,979 |
| first matched STOP distance | 124.84 m | 124.02 m | 124.02 m | 124.02 m |
| original person STOP frames lost | — | 10 | 17 | 10 |

R3/off is identical to parent/off on all 4,443 rows. R3/v5c-15 has 21 changed
non-timing rows versus parent/v5c-15 (range/advisory bookkeeping); its person
STOP set returns to the original v5c set. R2's extra losses 4366–4372 are
removed. The original losses **2972–2975, 3059–3063, 4382 remain**. Sixteen
gained frames do not cancel those losses.

[score_falcon.py](score_falcon.py) preserves the historical position scorer's
definition and adds alignment and planted-loss/delay controls. Its positions
come from reference detections, not independent person ground truth.

### Marked bags and set O

R1 parent/off versus r1/off and parent/v5c-15 versus r1/v5c-15 are identical
on all 1,667 marked frames and all 1,510 raw set O frames after explicit timing
normalization. Raw replay is distinct from the gate's compact16 replay.

The tunnels marker 19 still loses **29 →13 STOP frames**, first STOP
**54.994 →27.607 m**. The existing independent `per_object.py` scorer reproduces
the same 16 lost frame IDs as the new alignment-checked scorer. No marked
object loses STOP frames on the platform/switch bags in this r1 comparison.
Final r3 repeats are recorded separately rather than relabeled from r1.

The complete r3 repeats confirm the same outcome: **3,177/3,177 default-off
rows identical to the parent**, and **3,177/3,177 v5c-15 rows identical to
the unmodified v5c-15 detector** after timing normalization. Together with
Falcon, the default-off identity covers **7,620 frames** on five raw recordings.
The marker-19 loss remains exactly the same 16 frames. All r1/r2 and r3 replays
are retained in `runs/` with source manifests and scorer reports.

## 3. Frame inspection and remaining mechanisms

### Small center: weak candidates are present

The 350-frame off/K2 traces match their plain raw replays. In K2 frames
331–334, the four-return box is present as weak evidence with **two strict
voxels**, zone `warning`, no infrastructure demotion. `_far_thin` only passes
zone `gauge`, so these observations do not seed a track. Off has four strict
voxels and starts its track earlier. Frame 336 is absent from both candidate
lists. This is a candidate-admission/confirmation history issue, not proof
that the object vanished from the cloud. Strict gate scoring must use the
gate's own quantized inputs; these raw traces establish the mechanism only.

### Crossing entry: all three failing X3 transformations traced

The exact X3 worker (including its RNG substitution and float32 transforms) was
instrumented through [trace_x3.py](trace_x3.py). **Six full 201-frame runs**
(off/K2 × roll +2°, dropout seed 2, dedup) equal their plain reference outputs
after explicit timing normalization. Complete raw, hooks and identity receipts:
[crossing trace package](crossing-r3-trace.tar.xz).

For all ten lost crossing rows (roll 9–12, dropout 8–10, dedup 8–10), the current
target cluster is `gauge` without a demotion reason. The track is already
reported, but its actually evaluated `rule_zone` is `warning`; earlier ordinary
hits had too few strict voxels. At roll frame 9 the vote is 2/8; at dropout
frame 8 it is 2/5; at dedup frame 8 it is 2/5. None of these three examples has
a column hold, opinion withholding or fresh-evidence block. The recent geometry
history, rather than absence of the person or a missed persistence threshold,
delays STOP. Changing a confirmation threshold alone would not establish which
axis is geometrically correct.

An additional feedback path needs investigation: mount calibration reads the
joint **output** track, although the estimator carries an independent `base`.
At the deduplicated frame-4 provisional calibration, off chooses roll 3.12° and
K2 3.24°; dropout gives 3.00° versus 2.97°. Both differ before subsequent shape
comparison. These are measured mount differences, not yet proof of how much
of the crossing loss that feedback causes. The next geometric review must
separate mount/frame effects from axis-shape and track-vote effects.

### Tunnels cube: clipping and low-stage sensitivity remain to repair

The full 545-frame K2 trace equals the plain run apart from explicit latency
effects. The marker lies partly inside the envelope. Independent paired-rail
fits in seven usable near frames put its center at median **−1.165 m** from
the rail midpoint, range −1.189…−1.133 m. The low-object search clips its body
at the envelope boundary. The subsequent [low-stage trace](trace_low.py)
records the actual executed `_low_cluster` return line and the admission
masks for frames 245–290, rather than inferring a reason from final detections.
Both full 545-frame instrumented runs match their plain outputs.

At frame 259, off admits a 0.478 m wide straddling cluster; K2 clips the same
body to **0.226 m**, below `straddle_min_width=0.35`, and returns at the width
rejection. At frame 270, K2 leaves **0.121 m** of the straddling body and four
ordinary low raw returns; no target-associated ordinary `_low_cluster` call
reaches the traced shape checks, so the earlier clustering rejection still
needs its own attribution.
At 274 its ordinary slice is **0.083 m**, below `min_width=0.15`. At 279 the
straddle cluster is also merged into a **1.226 m** long patch and hits the
extent check. These are observed rule executions on the stated frames, not
a single label for every lost frame. A repair needs full-object context with
separate strict-envelope intrusion checks, plus rail-fixture controls; lowering
all size thresholds would erase the infrastructure discrimination.

Retaining the cap does not address this loss. The historical “outside the
gauge” explanation cannot close M-1.

### Falcon: inspect detections, not only STOP frame totals

The final 4,443-frame trace equals the plain r3 replay in every non-timing
field (51 explicit latency-only rows). Selected raw clouds were plotted and
inspected in [falcon-end.png](falcon-end.png):

- At 2972 and 3059 the person cluster is currently `gauge`, but the recent
  track zone votes are insufficient. This explains the advisory at those
  sampled lost frames; all lost intervals still need rule-by-rule repair.
- At 4382 the fitted rail plane is above the visible near body. Its local
  fitted slope is about **0.128 m/m**, not a plausible metro grade; the body
  falls below the modeled floor. This is a height-reference failure, not the
  reach-cap disappearance repaired here.
- At 4366 the frame contains the person STOP **and two additional detections
  on the ceiling**, at 36.28/38.56 m and Z ≈2.49 m in detector coordinates. The
  model's rail plane rises into that ceiling. A person-matched frame total
  hides these extra detections; they need their own object-level disposition.
- Frames 4410–4411 are outside the position scorer's extrapolated domain:
  its predicted near face has already crossed 2.5 m (2.239/2.132 m). The raw
  4410 detection is instead at 3.00 m, width 0.643 m, observed height 0.354 m;
  4411 is a one-miss continuation. The plot shows a compact near body, not a
  ceiling patch. They remain **unattributed by the registered scorer**; this
  is not evidence that they are false alarms. Independent frame labeling is
  still required before declaring them additional person detections.

## 4. Handoff / remaining acceptance

The author repair is intentionally not an enablement recommendation. Remaining
work is detection/confirmation repair for small_center and crossing entry,
the marked low cube, Falcon's original lost frames and height-reference
failure; successful target-specific K1 100/150 m and sudden-appearance tests with
platform false-alarm controls (r3's completed targets fail); K2/B6 reference-axis
accuracy and range honesty. Then
repeat all registered exact-source acceptance rows, obtain a **different
independent reviewer**, and hand the switch/reseal decision to captain/P1.

This session is now the patch author; its earlier v5c review does not count as
an independent review of this patch. Ownership ambiguity is resolved. Remaining
acceptance failures and reviewer/captain handoffs are distinct from data access:
the public archives are accessible on this server.
