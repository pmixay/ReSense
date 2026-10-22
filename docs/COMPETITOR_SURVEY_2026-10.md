# Competitor survey: what other case-05 solutions have that ReSense lacks

> **Purpose:** the filtered result of reading 34 other teams' public repositories against ReSense: what we do
> not have, what could really lower false alarms or extend range, what to leave alone, and which
> [`BACKLOG.md`](BACKLOG.md) card each idea belongs to. Per-repo detail:
> [`evidence/competitors_2026-10/`](evidence/competitors_2026-10/README.md).
> **Audience:** P3 (detector), P4 (evaluation), P1 · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: the statements about our code (§2 table, the `beyond_axis`, `ego_veto`, `edge_margin_per_100m2`, `far_axis_both_sides`, `axis_disagree_range` and opinion-model facts, the `configs/experimental_*.yaml` and `robustness_battery.py` mentions) re-checked against the 1.3.0 tree (`f24d939`): the facts hold, three line references had moved and are corrected, the backlog-card references are corrected (see §3), and the "ours" figures in §1 are v1.0.0 measurements of 13.10, not re-measured on 1.3.0; the other repositories' contents are not re-checked. Earlier: 2026-10-16 against the sealed `resense/` of `main` (`3fdc879`, detector = `v1.0.0`): the four
> "verified in our code" facts below were checked by the lead in the source; the rest is the agents' reading of
> the other repositories, grepped against `resense/` but not run. **Status:** current; analysis only, nothing in
> this document is measured on ReSense yet, and no detector file is changed.

## 1. Headline

* **Nobody beats ReSense on what can be compared.** The best competitor false-alarm figure that could be read
  is about 5 `STOP` episodes per km on the 13 km ride (`ivanpabl/hakatanon_lidar`, by its own odometry; ours 2.1–2.5
  per km on v1.0.0, [`SCORECARD.md`](SCORECARD.md), [judgement 13.10](evidence/judgement_2026-10-13/README.md)); other
  figures: 15 episodes on the 2 287 empty frames (`KirpaDmitriy`, ours 12), 505 before its fix
  (`bryxosmmm/tunnel-guard`), 36 on 1 510 frames (`templeJJs`). Every "0 false alarms" claim is in-sample
  (per-recording maps, thresholds tuned on the same bags) and no repository ships result files to recount.
* **Their ranges are not comparable with ours.** KIWI7200 (125 m), hakatanon (160 m), Gabarit (138 m) and
  MetroGuarder (120 m) place the test object on the detector's **own** estimated axis, so an axis error cannot
  make them miss. Our range test anchors the object to the real track. The comparison does show where the lever is:
  with the axis right, far recall is fine; our range is lost to axis trust (`beyond_axis`) on curves and double
  track (cards K1, K2).
* **The best evidence available is convergence**, because no repository has held-out real data: where several
  independent teams arrived at the same technique, it ranks higher. Everything below is a hypothesis to test
  offline on the ride and the real positive before any detector change, under
  [`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md).

## 2. Verified in our code (by the lead, 16.10)

| fact | where |
|---|---|
| beyond the trusted axis range a cluster is a hard `beyond_axis` demotion to `CAUTION` (no graded trust); the range is the last observed boundary bin + 15 m (+ 50 m straight) | `resense/clustering.py:733-734` (`_advisory_reason`; also `resense/detector.py:950`, `:1031` for the K2 curve gauge), `resense/config.py:93-94` |
| no turnout / branch concept, no behind-the-object (opacity) test, no along-track recurrence or collinearity test | `resense/clustering.py`, `tracking.py`, `track.py`, `gauge.py`, `lowobj.py` (grep) |
| `ego_veto` needs at least 4 hits and 4 m of travel and a track beyond 25 m, so artefacts fragmenting into short tracks escape it | `resense/config.py:437-441` |
| the second-opinion model sees track-level cluster statistics only, no frame-context features | `resense/opinion.py:30` (`FEATURES`) |

**Constraint from our own experiments** that every idea below must respect:
[`EXPERIMENT_FAR_STRUCTURE.md`](EXPERIMENT_FAR_STRUCTURE.md) (28.09) found that most remaining false far targets are
compact (0.1–0.4 m along X), have multi-ring support and sit 0.2–0.5 m from structure, and that applying an
infrastructure signature to a whole connected component erased localized bodies; the D1 context rule was rejected
(outside-object false `STOP` 6 → 9). So: judge the compact target against its **surroundings**, downgrade or delay,
never delete a component, and keep the "demote, never delete" rule.

## 3. Shortlist

Ranked by convergence and fit to the weaknesses in [`BACKLOG.md`](BACKLOG.md) §3. "Card" = the existing backlog
card the idea attaches to; nothing here needs a new card except where marked. Since 22.10 the cards X1, X3 and H2 are closed and the K2 card no longer has a numbered task list; they are in [`archive/BACKLOG_history_2026-10-19.md`](archive/BACKLOG_history_2026-10-19.md), and "K2 task (1)" is the offline wall-vs-axis error study of the archived K2 card.

| # | idea | sources (convergence) | targets | evidence in the source | risk and constraint | card |
|---|---|---|---|---|---|---|
| 1 | **Context tests on the compact far target:** opacity (returns behind it at its own height and lateral band: a surface), front-lift (ground in front rises ≥ 0.1 m above its bottom: ramp or platform edge), attachment ratio (outside returns within 0.35 + 0.008 d outnumber its own), depth-edge test per laser row (nearer than both lateral neighbours on ≥ 2 rows) | hakatanon `plausibility.py` (`behind_n`, `front_lift`); I.MOSCOW `detector.py:process`; W2nner `surfaces.py:foreground_edges`; MetroGuarder intrusion depth | far false `STOP` on platforms, curves, columns; the compact-fragment majority of ride episodes | hakatanon, in-sample: organizer-bag false `STOP` frames 19 → 4, empty-recording `STOP` frames 2.0 % → 0.39 %, no real object lost | a real person in front of a curve wall, platform end or against a wall is flagged; D1 precedent; start in shadow mode, then **CAUTION or delayed start beyond ~40 m**, never a delete | F2 (far onset ≥ 100 m), F1 |
| 2 | **Per-return structure peeling before the shape tests:** remove returns that are structure (recur along the track, connect outward to the wall, slack to the lining) from a merged cluster, then judge the residual | tunnel-guard `geometry.py:structural_mask`; templeJJs `structures.py:explain` (+ re-cluster); MetroGuarder `tunnel.py:estimate_free_space` | **the judge's silent GO on curves** (a person-size box merged with a 46–55 m corridor-edge blob and dropped as oversize, [problem 2](evidence/judgement_2026-10-13/README.md)) and column merges | none measured in the sources; each bundled with other changes, no ablation | long real objects along the track are "recurrent": need an exception (nothing explained inside the collision volume above ~0.5 m, templeJJs' slab rule); a hypothesis for H2 (structure-cut evidence bar), not a proven fix | H2, F2 |
| 3 | **Graded trust beyond the axis range** instead of the hard `beyond_axis` cut: keep reporting with a shrinking envelope (≈ 0.01 m per m, cap ≈ 0.9 m) or a forecast uncertainty ≈ 0.0006 d² (straight) / 0.034 d (turns); refuse only where near-optimal axis hypotheses disagree by > ~0.9 m | KIWI7200 `obstacle_detector.cpp:detect`; NIIstovye `route/corridor.py:lateral_uncertainty_m`; tunnel-guard covariance σ; ValeraYakovlev; Kirpa (extrapolation) | range at 80–200 m, our main miss | KIWI: 114 → 173 of 201 real-obstacle frames at 0.15 % false DANGER (in-sample); Kirpa: recall at 150 m 0 → 83 % **but** +20 points of background alarms; tunnel-guard: demoting uncertified objects loses the 100 m object | highest range upside, real false-alarm risk on platforms and double track; coefficients must be re-fitted on anchored placements; our opt-in quadratic edge margin (`gauge.edge_margin_per_100m2`) and `far_axis_both_sides` were measured and not shipped | K2, K1 |
| 4 | **Inner-wall sight-line model on curves:** exclude inner-wall edge points beyond the tangent point of the curve | ValeraYakovlev `parallel_path.py:hidden_edges` | K2's own cause: "the smooth inner wall carries 3–10× the weight but is hidden by the curve beyond 56–96 m"; our 60 m `axis_disagree_range` cap may partly be this artefact | none measured; ~100 lines, low risk | novelty grepped by the agent only | K2 task (1) |
| 5 | **Along-track continuation / recurrence / collinearity** as evidence for CAUTION or `explained_run`: same lateral and height returns before and after the cluster; three or more clusters at one lateral offset and height spanning > 4 m; per-ring pieces on one line for ≥ 5 m; a low line over ≥ 8 bins of 2 m | Gabarit `detect.py:_longitudinal`; MetroGuarder `mark_linear_infrastructure`; NIIstovye `_on_a_line`; ObemaM `longitudinal_mask`; tunnel-guard, templeJJs (as in 2) | elongated false targets on platforms and switches (ride events with 4–7 m along X) | six repositories converge; each in-sample | does not help the compact fragments; same exception as 2 | F1, F2 |
| 6 | **Pooled "carried-along" test for young or fragmented tracks** (extension of `ego_veto`) | EhimenNathan `core/detector.py:_pooled_carried` (our `ego_veto` already ports `_carried_along`) | artefacts that split into < 4-hit tracks | their sealed drive 6.7 → 4.7 events (swings 2–11 with the seed) | ~40 lines; active only when speed ≥ 4 m/s is known; replay on the ride's residual events first | F2 |
| 7 | **Switch / turnout branch hypotheses:** a second rail pair diverging 0.45–1.8 m with growing separation; points explained by a credible branch are not obstacles (like `explained_run`, not a corridor cap) | MoscowMetropilot `LocalTrackHypothesisSet`; ObemaM `track_path.cpp`; Gabarit `_detect_turnout` (display only) | our worst false `STOP` pool: `squareT_platform_squareT_switch` (11 episodes) | no measured gain anywhere (Gabarit's own 4 residual false events are this case) | ambiguous frames reset the gate (recall cost); capping beyond a switch hides real objects | X2 (classify the ride episodes first), F2 |
| 8 | **Frame-context features for the doubt model** (`behind_n`, front max height, beam count, range spread p90–p10) | hakatanon; templeJJs | calibration of a delay-only gate | none | small effect (delay-only, synthetic positives); only after 1 works | G2 |

## 4. Evaluation items worth taking (no detector risk)

| item | source | card |
|---|---|---|
| **label-free axis error:** predict the far axis at frame t, compare with the rails measured when the train arrives there; calibrates `axis_valid` and `beyond_axis` on the 13 km ride without labels (five repositories do a variant) | tunnel-guard, templeJJs, KIWI7200, NIIstovye, Kirpa | K2 task (1), X1 |
| report **rays hit next to detected** (sensor limit vs detector limit); scene-clustered confidence intervals for injection trials; a false-alarm-per-hour upper bound by the rule of three | templeJJs `validation/synth.py` | X1, G3 |
| **mirror replay** (x → −x) of every bag as a fragility check (it exposed a hysteresis false detection in their detector); noise added to the perturbation battery (we already have tilt, 5 Hz, dropout) | ValeraYakovlev; KIWI7200 | X3 |
| the injected-trial tool marks a trial **ambiguous** where the detector already fires without the injection | hakatanon | X1, X2 |
| **leave-one-recording-out** table showing the worst fold; a pre-registered experiment record (hypothesis, expected effect, failure condition, leakage check) | Kirpa | G3 |
| bit-exact diff of two result journals (guards the native kernels); a per-channel Pandar128 reach table for realistic range tests (`config/pandar128_channels.csv`) | KulakovPetr; EhimenNathan | S2, X1 |
| ask the organizers or the team about three labelled synthetic sets seen in another repository (`Synthetic_data`, `Last_synth_data`, `FINAL_STEP/mix3`, per-point labels and `/tf` truth), none of which is in our `labels/` | ValeraYakovlev | O1 |

Point counts from the organizers' labels (what a detector has to work with) are in
[`evidence/axis_profile_2026-10-16/`](evidence/axis_profile_2026-10-16/README.md): a 0.3 m cube has 1–2 returns beyond
80 m, a 2 m box 16 at 200 m+; this bounds R1 and R2 physically (beyond ~60 m a cube is a one- or two-point
cluster; only multi-frame accumulation, which needs a known speed, can use it).

## 5. Not worth adopting

* **Hard-delete rules** (`shell`-like): I.MOSCOW `_extends_above`, MetroGuarder `full_height` / `thin_along_track`,
  NIIstovye "within 25 cm of the 3 m ceiling is set aside", igor688 span rule, krisikas / NanoMetro cluster deletion
  (a `dz ≥ 0.22 m` gate cannot see a 10 cm object), Andreymazo station-mode box deletion. They break "demote,
  never delete" and repeat the rejected `shell` lesson.
* **Learned rankers:** Kirpa's recall falls to 6.5–14 % on unseen shapes; zuykovmikhail's U-Net has no gauge logic;
  ikonushok's forest memorised the 55.0–56.7 m range of the one real object.
* **Artefacts of the organizers' generator:** bq777xCube's "98–99 m detections" come from a test of points slightly
  off the sensor's 128 calibrated beams, which targets the insertion generator, not obstacles.
* **Range-costly or risky rules:** "`STOP` beyond 30 m only if `STOP` in the previous frame" cost 25–40 m of range
  (hakatanon); holding a `STOP` through misses with a projected shape lengthens false episodes (NIIstovye).
* **Large axis-estimator rewrites** (cross-section Gauss-Newton template, clearance-tube beam search, free-form
  curvature axis, wall-parallel path with steps): high cost, unproven, and four of these repositories admit failure
  on one-sided platforms or double-track mouths. Revisit only through K2's offline study.
* Several competitors use another gauge (2.67 × 3.65, 2.7, 2.8 × 3.75, 2.83, 2.0 × 2.8 m instead of 2.1 × 3.0 m):
  their ranges and false-alarm counts are not comparable.

## 6. Suggested order

1. **No detector change.** Use the existing replay assets (the 11 271-frame ride trace, the switch recording, set O,
   `doubleT_obstacle`, the anchored range test) and compute per-event features for ideas 1, 5, 6, 7 offline; run the
   label-free axis check (§4) to see where `beyond_axis` is too tight. This also tells which pool (compact
   fragments, elongated, turnout) is largest.
2. **Flags default off** in `configs/experimental_*.yaml`, then the full gate with criteria written before the run:
   no positive lost (real person, set O, anchored range), false episodes down on held-out ride parts (not the parts
   that picked the thresholds), latency delta measured.
3. Idea 3 (range) last: it has the largest upside and the largest false-alarm risk.

No estimate of the final gain is defensible: all source numbers are in-sample and we have one real positive.
