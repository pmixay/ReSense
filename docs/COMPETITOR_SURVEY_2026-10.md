# Competitor survey: what other case-05 solutions have that ReSense lacks

> **Purpose:** the filtered result of reading 34 other teams' public repositories against ReSense: what we do
> not have, what could really lower false alarms or extend range, what to leave alone, and which
> [`BACKLOG.md`](BACKLOG.md) card each idea belongs to. Per-repo detail:
> [`evidence/competitors_2026-10/`](evidence/competitors_2026-10/README.md).
> **Audience:** P3 (detector), P4 (evaluation), P1 · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-16 against the sealed `resense/` of `main` (`3fdc879`, detector = `v1.0.0`): the four
> "verified in our code" facts below were checked by the lead in the source; the rest is the agents' reading of
> the other repositories, grepped against `resense/` but not run. **Status:** current; analysis only, nothing in
> this document is measured on ReSense yet, and no detector file is changed.
> **Update 29.10:** §7 adds the finalists (pitch schedule 23.10), their repositories and a comparison table.
> **It supersedes the first bullet of §1 on false alarms:** for the finalists the "nobody beats ReSense" claim does
> not hold on the claims that could be read (§7.4). §1–§6 are the 16.10 text, unchanged.

## 1. Headline

* **Nobody beats ReSense on what can be compared.** The best competitor false-alarm figure that could be read
  is about 5 `STOP` episodes per km on the 13 km ride (`ivanpabl/hakatanon_lidar`, by its own odometry; ours 2.1–2.5
  per km, [`SCORECARD.md`](SCORECARD.md), [judgement 13.10](evidence/judgement_2026-10-13/README.md)); other
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
| beyond the trusted axis range a cluster is a hard `beyond_axis` demotion to `CAUTION` (no graded trust); the range is the last observed boundary bin + 15 m (+ 50 m straight) | `resense/clustering.py:349`, `resense/config.py:93-94` |
| no turnout / branch concept, no behind-the-object (opacity) test, no along-track recurrence or collinearity test | `resense/clustering.py`, `tracking.py`, `track.py`, `gauge.py`, `lowobj.py` (grep) |
| `ego_veto` needs at least 4 hits and 4 m of travel and a track beyond 25 m, so artefacts fragmenting into short tracks escape it | `resense/config.py:361-365` |
| the second-opinion model sees track-level cluster statistics only, no frame-context features | `resense/opinion.py:28` |

**Constraint from our own experiments** that every idea below must respect:
[`EXPERIMENT_FAR_STRUCTURE.md`](EXPERIMENT_FAR_STRUCTURE.md) (28.09) found that most remaining false far targets are
compact (0.1–0.4 m along X), have multi-ring support and sit 0.2–0.5 m from structure, and that applying an
infrastructure signature to a whole connected component erased localized bodies; the D1 context rule was rejected
(outside-object false `STOP` 6 → 9). So: judge the compact target against its **surroundings**, downgrade or delay,
never delete a component, and keep the "demote, never delete" rule.

## 3. Shortlist

Ranked by convergence and fit to the weaknesses in [`BACKLOG.md`](BACKLOG.md) §3. "Card" = the existing backlog
card the idea attaches to; nothing here needs a new card except where marked.

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

## 7. Finalists (update 29.10)

> **Status:** analysis of public repositories, read-only; no competitor code was run (see §7.5), no detector file
> changed. Competitor figures are **their own claims on recordings they tuned on** unless marked ✓.
> ✓ = recomputed by us from raw rows; "claimed" = from the team's README or report; n/a = no data in the repository.
> The ranking in §7.6 is a judgement with the weights stated there, not a measurement.

### 7.1 Who the finalists are

The pitch schedule of 23.10 lists ten teams: МичГАУ, **Молоток (us)**, ITL-RailGuard, xixi-square, Attention Please,
СахалИИн, Криперы, Дальнобои, =УСПЕШНЫЕ РОСТОВЧАНЕ=, IRS-MIREA. Five of the nine rivals were matched to a repository.
The code stop is 20.10 23:59 MSK = 20:59 UTC ([`BACKLOG.md`](BACKLOG.md)).

| Team | Repository | How identified | Last commit (UTC, all branches) |
|---|---|---|---|
| СахалИИн | `EhimenNathan/tunnelguard-lct2026` | the finals presentation is titled with the team name | 20.10 01:02 |
| Attention Please (Perm) | `BelousovArts/fod` | the README names the team | 20.10 16:58 |
| IRS-MIREA | `garabot11/I.MOSCOW` | team contact in the README and in the launch file | 20.10 20:37 (22 min before the stop) |
| Дальнобои | `ValeraYakovlev/LIDAR` | **medium confidence**: the author is on the team roster and is active in the final window; the team name is not in the repository | 20.10 19:53 |
| (name unknown) | `EnglishMan47/Gabarit_metro` | a finalist: the repository holds notes of the 16.10 finalists' meeting and a "Final release" commit; the team name is a placeholder in the deck script; the organizers' SourceCraft path is `…-team-56` | 19.10 15:42 |

**Not found:** МичГАУ, ITL-RailGuard, xixi-square, Криперы, Ростовчане. They are not among the 34 repositories of §1–§6.
Web searches on GitHub (unique bag names, task wording) returned only known repositories; GitVerse and SourceCraft
hosts are blocked in our environment, so nothing could be read there. Do not infer a team from a repository name.

Method and its controls (34 repositories fetched with all branches: 32 of the 16.10 survey that are still readable, plus
`valuncilh/metro_obstacle_detection` and `BelousovArts/fod`; `CatherineLensis/NanoMetro1550` and `templeJJs/test_lidar`
are no longer reachable):

* The date of the last commit on any branch, against the code stop. 26 of the 34 have no commit after 29.09; several
  end 29.09 20:41–20:59 UTC, which is 23:59 MSK, the qualification stop. Control: all four known finalists and Gabarit
  are active 19–20.10. Other late activity: `zuykovmikhail1305-boop/3D-lidar_ml` 04.10 (a visualisation app),
  `Matymij/MetroLiDAR_Sentinel_Humble` 01.10, `KoTeHok22/Argus` (a side branch to 09.10, team name removed from the
  docs), `krisikas/MetroLidar2026` (team MOPSY, not on the list, one commit on 29.10 after the stop).
* A keyword search for finals terms (finalist, "in the final", 16 October, meeting with experts, …) in all text files:
  no further finalist. The matches in other repositories are the public Q&A transcript and generic text.
* Limit: a finalist can keep a repository private or on another host; the heuristic only finds public GitHub ones.

### 7.2 Comparison on the Falcon recording and on the criteria

All teams use the same recording `falcon_test_second_dark` (4 443 clouds): a real person appears at about 250–310 m and
walks to the train (a reference path exists for 4 411 frames).

| Criterion | ReSense | СахалИИн | Attention Please | IRS-MIREA | Дальнобои | Gabarit |
|---|---|---|---|---|---|---|
| 1. Person on Falcon, first detect | **124.8 m** ✓ | **257.2 m** ✓ | 256–270 m claimed (timeline ✓) | 154 m claimed (timeline ✓) | 188 m claimed | n/a; synthetic person 138 m mean, 157 m max, claimed |
| 2. Gauge range on Falcon | median 115 m ✓ | median **387.6 m**, measured part 202 m ✓ | median 263 m claimed | Falcon not stated; Hesai 83–175 m claimed | ≤150 m geometry, up to 300 m hybrid, claimed | limit 350 m stated, "not a proven range" |
| 3. Gauge stability | reported range jumps 102–159 m between frames ✓; STOP does not flicker ✓; display box not measured on Falcon | 0 geometry dropouts in 4 413 frames ✓ | track breaks at 246–270 m (own report) | n/a | n/a | n/a |
| 4. False alarms | ride: 26 STOP episodes (gate); Falcon: 13 STOP frames not on the person ✓ | ~1.8 events/km claimed; Falcon: 10 frames at the end of the recording ✓ | 1 per 6.3 min; 4 of 11 435 frames, claimed | **0** on the 11 271-frame ride, claimed (the detector reported nothing at all there) | 10 episodes on 40 recordings, claimed | ride: 27 events, 209 frames; switch: 3 known false, claimed |
| 5. Misses (Falcon, share of frames) | STOP on 95 % of frames with the person ≤125 m, 83 % ≤150 m, 66 % ≤200 m, 40 % ≤260 m ✓ | 72 % of frames with a reference ✓ | person 0 of 7 missed, flat object 7 of 7 missed, claimed | 49 % of object-frames in the gauge, claimed | 58.9 % of frames, claimed | 582 alarm frames of 4 443: at most 13 % of the person's frames (upper bound) |
| 6. 10 Hz | Falcon decode+detect p95 **25 ms** ✓; Pandar 360° p95 106–119 ms (v1.0.0, not recomputed) | Falcon p95 **29 ms** ✓; 57–63 ms on 4 vCPU claimed | 50–85 ms on an RTX 5080, claimed | 39–75 ms on GPU, claimed | 78–170 ms on a cloud VM, misses 10 Hz, claimed | **not met**: ~5.9 frames/s in ROS (own report) |
| 9. Launch | CPU, offline, 472 MB | Docker, ML on numpy | NVIDIA GPU required | GPU, 13.3 GB image, emergency CPU mode | Docker, CPU | CPU, 4 packages, Docker, offline |

### 7.3 What was recomputed (and how)

* **Our Falcon stream** (`docs/evidence/falcon_full_2026-10-18/`, 4 443 rows, v1.1.0, not 1.2.0): decode+detect
  p50 17.9 ms, p95 24.8 ms, one frame over 100 ms (frame 0, 218 ms, warm-up); decisions STOP 1 372 / CAUTION 3 062
  (68.9 %) / GO 8 / FAULT 1. Control: a synthetic series with 3 planted slow frames, 1 planted range blink and 1 planted
  STOP gap — all found, none extra.
* **Reported range on Falcon:** median 115 m; it changes by more than 20 m between neighbouring frames on 35 % of
  frames (values 102, 107, 111, 115, 123, 154, 159 m), 19 range "blinks" in 444 s. This is the detector field
  `monitored`; the node publishes null/zero range on Falcon by design, and the smoothing of the displayed box was
  measured on Pandar recordings only.
* **Join with the person's reference path** (the path in СахалИИн's `docs/finals/rows.json`, an automatic trajectory,
  not a human label): our first STOP on the person is frame 2972 at 124.8 m; 1 359 of our 1 372 STOP frames are within
  3 m of the person; the 13 others are frames 159, 2312–2314, 3135 and 4394–4401 (the 4 known structure frames at ~115 m,
  one new frame, and the tunnel-ceiling frames that H′ removes in 1.2.0, per the P4 bundle). Control: shifting the
  frame index by 1 000 gives 0 matches; **a shift of ±137 still gives ~360 matches (the person stands still), so that
  control does not discriminate**.
* **СахалИИн, `rows.json`** (4 443 rows): first level-2 frame with an obstacle is frame 53 at 257.2 m (their text:
  257.36 m); gauge median 387.6 m, measured part 202 m; 0 geometry dropouts after frame 60; 3 159 STOP frames matched
  to the reference; 10 unmatched STOP frames (4411–4420, ~2.9 m, no reference at the end); per-frame time p95 29 ms.
* **Timeline of three teams agrees:** the reference path is 154.5 m at frame 2723, 99.1 m at 3181, 92.7 m at 3690,
  3.8 m at 4400, 255.4 m at 3 s. IRS-MIREA states 154 m at frame 2723, standing at 100 m in 3181–3690, walking to 4 m
  by 4400; Attention Please states confirmation at 256 m on the third second. The person is real and present from
  frame 0 at about 253 m.
* **Gauge table of B6** (`gauge_stability_2026-10-18/monitored.json`): the 20 medians of the reported range
  (10 recordings × 2 versions) equal the published table.
* **IRS-MIREA "0 false frames":** their own protocol defines a false frame as a reported detection with no labelled
  object; on the 11 271-frame ride their table shows 0 reported frames, i.e. the detector never fired there. Their
  "false-alarm phase" on Falcon is the first 2 723 frames, in which the reference path puts the person at 154–309 m;
  nothing is reported there by design (two detectors must agree), which is counted as correct.

### 7.4 Corrections to §1

* "Nobody beats ReSense on what can be compared" does not hold for the finalists on false alarms. Claimed: IRS-MIREA 0
  reported frames on the ride (but 49 % of in-gauge object-frames on the organizers' marker set), Attention Please 1 per
  6.3 min, СахалИИн ~1.8 events/km. Ours: 23 events on 13 km (~1.8/km, gate definition) and 26 STOP episodes. The
  definitions differ and none of the claims is held-out, so this is "at best equal", not "ahead".
* On the real Falcon person the ranges **are** comparable (same recording, same person), unlike the synthetic-axis tests
  of §1: 125 m (us), 154 m (IRS-MIREA), 188 m (Дальнобои), 256–270 m (Attention Please), 257 m (СахалИИн).
* The 16.10 remark that Gabarit's 138 m is measured on its own axis stands: that is a synthetic figure, and its Falcon
  coverage is the weakest of the six.

### 7.5 What could not be done

* No competitor project was deployed. The recordings (Yandex Disk, Google Drive) and GitVerse/SourceCraft are blocked
  by the environment's network policy, there is no Docker daemon and no GPU, and 26 GB of disk is less than the 20 GB
  Falcon bag plus the 17 GB ride. Nothing was mocked.
* Not verified at all: all GPU and cloud-VM timings, every claim about the ride, Attention Please and Дальнобои as a
  whole, СахалИИн's "1.8 events/km", our own 26 ride episodes (no per-frame ride rows in the repository), Pandar 360°
  timing of 1.2.0, and the 1.2.0 Falcon timing (the stream above is v1.1.0).
* The scripts of §7.3 were written in a session scratchpad and are not committed.

### 7.6 Ranking (judgement)

Weights: detection range 15, gauge range 10, stability 10, false alarms 15, misses 20, 10 Hz 10, launch 10 (filter and
extra features are not in the table). Share of the maximum per criterion, our judgement:

| Criterion (weight) | СахалИИн | Attention Please | IRS-MIREA | ReSense | Дальнобои | Gabarit |
|---|---:|---:|---:|---:|---:|---:|
| 1. Range (15) | 1.0 | 0.95 | 0.6 | 0.5 | 0.7 | 0.45 |
| 2. Gauge range (10) | 1.0 | 0.7 | 0.35 | 0.3 | 0.45 | 0.3 |
| 3. Stability (10) | 0.9 | 0.5 | 0.4 | 0.4 | 0.4 | 0.4 |
| 4. False alarms (15) | 0.75 | 0.8 | 0.9 | 0.7 | 0.6 | 0.65 |
| 5. Misses (20) | 0.8 | 0.75 | 0.5 | 0.45 | 0.55 | 0.35 |
| 6. 10 Hz (10) | 0.95 | 0.9 | 0.9 | 0.8 | 0.3 | 0.35 |
| 9. Launch (10) | 0.7 | 0.2 | 0.5 | 1.0 | 0.7 | 0.9 |
| **Total / 90, in %** | **86** | **71** | **60** | **58** | **54** | **48** |

Where the data are missing the share is a neutral 0.4. Ranks 1–2 hold under other weights; ranks 3–5 are within the
error of the judgement. Of the five found rivals we are fourth; four finalists are unknown, so the place among ten can
be worse. A rough model (СахалИИн ahead, Attention Please ahead with 75 %, IRS-MIREA ahead with 60 %, each unknown team
ahead with 40 %) gives about 10 % for a top-3 place; hidden-data variance raises the upper bound to about 15 %. This is
not a forecast of the jury's weights. Hidden-set behaviour is untested: the registered G3 set has not been run.
