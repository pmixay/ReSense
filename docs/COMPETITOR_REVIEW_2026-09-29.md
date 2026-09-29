# Competitor review, 29.09: what other LCT 2026 case 5 repositories do better, and what survives a screen

> **Purpose:** which techniques of the other public case 5 (metro obstacle detection) repositories are
> better than ours, how each one fared on the organizers' recordings through the full regression gate, and
> which three are now on by default (resealed at `ee7b920`).
> **Audience:** team, jury · **Owner:** P1 (record), P3 (candidates) · **Language:** EN
> **Last verified:** 2026-09-29 evening: §6 from the full regression gates in
> [`evidence/cycle_2026-09-29/competitor_rules/`](evidence/cycle_2026-09-29/competitor_rules/gate_table.md)
> (all organizer recordings, ride and set F included); §2 from `scripts/screen_competitor_rules.py`;
> repository facts from the public clones of 29.09 · **Status:** dated record

## Summary

* **Three rules from other teams are on by default and resealed** (§6): TunnelGuard's ego-motion veto and
  shell attachment, and Tactical-Inventor's "clean run after a history of fixed infrastructure". Full gate
  against the sealed 3eeb106 result: **PASS, 7 gated metrics better, none worse**. Ride false alarms
  32 → **26** events and 31 → **28** STOP episodes; the five empty recordings 11 → 8 events and 13 → 12
  episodes; set F false detections 12 → 6 (1 m box) and 3 → 0 (cable). Set O, the set F first-detection
  distances and `doubleT_obstacle` are identical, and all 1 280 tests pass.
* **The bigger wins were not safe, and were not shipped** (§6): `lowobj.min_top` 0.08 m (ride 22 events)
  loses the organizers' 30 × 30 × 10 cm box on a rail at 10, 25, 45 and 50 m; the clean-run rule counting the
  range demotions (ride 18 events) costs set F 22 m of first detection; counting the shape signatures stops a
  hanging cable from stopping; the quadratic edge margin (13 → 2 episodes on the short recordings) costs set
  O's small cube 8 m; the team's own `fresh_stop_evidence` costs set F's trolley 16 m; far ring rails (§4)
  reach only 34-47 m on real rails and fail the gate.
* **Most of what the competitors do was already in ReSense** (§2), and the four best-ranked public
  repositories (`zeezz108/LCT2026_KIWI7200`, `Kurligin/metro-obstacle`, `ObemaM/...`, `EnglishMan47/...`)
  are no longer reachable (HTTP 404 / private, no archive snapshot), so their ideas are known only from
  search snippets.

## 1. Scope and limits

* **Read:** the code of `EhimenNathan/tunnelguard-lct2026`, `kurorodev/lct2026_metro`,
  `krisikas/MetroLidar2026`, `LesiaJr/metro-obstacle-detector`, and the READMEs of
  `hih0lp/Moscow_metro_hack_CV`, `CatherineLensis/NanoMetro1550`, `Tactical-Inventor/LCT-2026.NIIstovye`.
* **Not readable from here** (the tooling reported them as not found or not accessible): `zeezz108/LCT2026_KIWI7200`,
  `Kurligin/metro-obstacle`, `ObemaM/HackathonLoTD-2026-Task-5M`, `EnglishMan47/Gabarit_metro`. Their figures
  (KIWI7200: 0.15 % false DANGER frames, 24 ms) are public claims that were not verified. If KIWI7200's claim
  holds it is about 8-9 times below our 1.4 % of STOP frames (187 of 13 558) on what appears to be the same
  13 558 empty frames (our 2 287 + 11 271; the count matches exactly, the identity is an inference).
* **No competitor figure was reproduced.** Their READMEs are self-reported, and several are in-sample.
* **Licences:** none of the seven repositories carries a licence file or a licence declaration. Their code
  may not be copied into an MIT repository; only ideas can be re-implemented. The screen below ports two
  published threshold rules from their description and copies no code.
* **The ride events** of the screen ("2 of 27") are the residual false events of the `fresh_stop_v1` capture
  ([`RESIDUAL_EVENTS_2026-09-28.md`](RESIDUAL_EVENTS_2026-09-28.md)), an experimental configuration, not the
  sealed default; the empty-recording and set O rows are the sealed detector.
* **What the screen is.** A rule is applied as a *post-filter* on the STOP detections the sealed detector
  already produced ([`judge_outputs_2026-09-28/`](evidence/judge_outputs_2026-09-28/README.md), the judgement's
  offline outputs, and the ride's residual false events). It is a first-order proxy: it cannot show what a
  rule does inside the tracker, and set F keeps no detection size or height, so the cost of a rule on far small
  objects cannot be seen here at all. Set O is scored with the independent judge's matcher; the harness first
  reproduces the published [`setO.json`](evidence/judgement_2026-09-28/setO.json) exactly and refuses to run if it does not.

## 2. Technique by technique

| technique (source) | in ReSense already? | screen | decision |
|---|---|---|---|
| **Shape plausibility**: beyond 40 m a cluster of fewer than 15 points thinner than 1.2 vertical beam spacings is not an object (TunnelGuard `core/detector.py`) | in kind: our `thin_far` / weak-evidence path with the approach test ([`ALGORITHM.md`](ALGORITHM.md) §3.3c, `tracking.approach_*`) | empty recordings STOP frames 23 → 16, episodes 7 → 5; ride residual events fully removed 2 of 27; **costs**: `long_low_on_rails` first STOP 87.3 → 77.2 m (52 → 44 frames), `big_above` 111.5 → 107.4 m, `small_center` 55.8 → 54.2 m | **not adopted**: a wash; TunnelGuard's own config comments record the same kind of trade for its debounce rule (a false event fewer per 2.8 km for far recall lost) |
| **Gravity**: beyond 60 m only an object standing on the floor may give STOP (same file) | partly: `elevated` / `floating` signatures, each gated | empty recordings 23 → 21 frames, 7 → 6 episodes; ride 2 of 27; **costs**: `big_center` 208 → 87 STOP frames, first STOP 98.0 → 85.8 m; `big_above` 56 → 30 frames, 111.5 → 59.6 m | **rejected**, for two independent reasons: the organizers placed the synthetic objects in the sensor's frame and only approximately (Q1, [`QUESTIONS.md`](QUESTIONS.md); the label metadata), so at range the centre box's lowest point rises to 1.85 m above the rail head; and `big_above` hangs at the top of the envelope by design, which the organizers confirmed is an obstacle (Q2). A floor-support rule vetoes exactly the objects their check uses |
| **Uncertainty-aware gauge zones**: inside the envelope shrunk by k·σ(range) gives STOP, else CAUTION (TunnelGuard `core/gauge.py`); applied to us it would promote centred `beyond_axis` / `beyond_height_ref` advisories | our hard trusted-axis and height-reference cut-offs do this job | on the empty recordings 60 + 265 centred advisories of those two reasons (each a false STOP if promoted); on set O 3 gains, all at 226-238 m, beyond the ~210 m the real sensor reaches | **not adopted**: those demotions carry most of the false-alarm suppression; the weakness is the *short trusted range*, not the cut-off (§4) |
| **Containment / shell attachment** (TunnelGuard): an object with tunnel wall beyond it, a floor-to-roof slice attached to the shell, is infrastructure | yes: `wall_face`, `column`, `edge`, `beyond_axis` ([`ALGORITHM.md`](ALGORITHM.md) §3.3) | not screenable: the saved outputs carry no wall points | already covered |
| **Odometry "carried along" veto** (TunnelGuard `ego_check`): a real object closes in at the train's speed, an artefact travelling with the train does not | yes: the approach test on far thin returns (`approach_hits`, `approach_min_speed`, `approach_max_residual`), and `stop_keep` | — | already covered |
| **3-of-5 confirmation** (TunnelGuard, ~0.3 s) against our 0.5 s | measured: `hold_misses` 2 failed the strict gate ([`SCORECARD.md`](SCORECARD.md)) | — | not adopted |
| **Learned plausibility classifier**, leave-one-recording-out (TunnelGuard) | yes, bounded: the track opinion may delay a far STOP by at most 10 frames and never vetoes ([`DECISIONS.md`](DECISIONS.md) row 19) | — | not adopted |
| **Time to collision / closing speed / braking distance** (TunnelGuard `ObstacleStatus`, MetroLidar2026) | no output | — | **not adopted**: the ТЗ asks for the presence and the distance only; train speed bought nothing in our measurement ([`DECISIONS.md`](DECISIONS.md) row 3); a braking distance needs the organizers' deceleration, which we do not have |
| **OpenBLAS instead of the reference BLAS** (TunnelGuard's Docker notes a 4x slowdown) | yes: `docker/Dockerfile` installs pip's pinned numpy (bundled OpenBLAS) and sets `OPENBLAS_NUM_THREADS=1` | — | already covered |
| **Held-out slice of the ride for the false-alarm rate** (TunnelGuard seals the last 5 min, 2.8 km) | no | — | a protocol for the next evaluation, not code: our 2.3 events/km is in-sample on all 13 km because rules were tuned on the whole ride, so a slice cannot be held out retroactively |
| **Cross-section-template axis alignment to the horizon** (TunnelGuard `core/geometry.py`) | no: our axis extends from rails and wall curvature only as far as they are seen | not screenable | **candidate**, §4 |

## 3. Other repositories

No repository reports a false-alarm rate per km that could be compared with ours except TunnelGuard
(1.8 events/km on a sealed 2.8 km slice) and NanoMetro (5.5 % of frames on the ride); the rest is unmeasured, so
every "plausibly better" below is a hypothesis for the gate, not a result. Items 1-2 were read in the code for
this review; items 3-6 come from a code-reading pass and were not re-read here.

| # | idea (source) | targets | why plausible | why parked or what it costs |
|---|---|---|---|---|
| 1 | **Far rails from single-ring crossings** (`Tactical-Inventor/LCT-2026.NIIstovye`, `obstacle_detector/route/_core/far_rails.py`): past ~30 m a ring hits a rail head once or twice, so profile bins never fill; per ring (elevation angle rounded to 0.02°) find bumps ≥ 0.06 m over the lateral median, pair two one gauge apart (±0.10 m, height difference < 0.25 m), and require all pairs to agree on one offset curve from the last near rail (`abs(b) ≤ 4e-4`, `abs(a) ≤ 0.03`, inliers within 0.08 m), centres within 0.8 m of the near-rail arc, limit 80 m | the measured axis ends at ~30 m; two-track path selection (the 0.8 m cap stops a jump to the neighbouring track) | physical bounds (gauge, cant, curvature), not tuned on a bag; targets the gap our log documents | no hit rate beyond 40 m is reported by them: first count, on the ride, the frames with ≥ 2 consistent stations beyond 30 m; returns lateral centres only, so the height reference is not extended |
| 2 | **Forecast error measured against later frames** (same repository, `route/corridor.py` `lateral_uncertainty_m`): the axis uncertainty beyond the last measured rail is a 90th percentile of the error against the rails that *later* frames saw, no labels needed; their figures on straight track: 0.12 m at +12.5 m, 0.46 m at +27.5 m, **1.1 m at +40 m** beyond the last rail (about our gauge half-width, 1.05 m) | our trusted ranges and the caps on them are set by rules, not calibrated against later frames | it is a method to *calibrate* our trusted ranges from data, and their table is independent support for the §2 result: a centred object 40 m past the rails may lie outside the gauge | it is not a promotion rule: with that error a perfectly centred object stays inside the gauge only within about 40 m past the last measured rail, and one 0.5 m off centre within about 28 m; the constants are fitted to their own route model on the same six bags |
| 3 | STOP latch that predicts the object's shape forward with the train's travel and releases only on an observed exit (same repository, `gauge/processor.py`, `gauge/decision.py`) | the single `GO` frame (frame 111) | safety-monotone: never CLEAR from a prediction | our `hold_misses` 2 failed the strict gate; a latch makes false STOPs last up to 5 frames longer against a 2.3/km budget |
| 4 | Evidence tracker with a range-weighted miss cost (same repository, `tracking/obstacle_tracker.py`) | far objects seen in 30-50 % of frames | can accumulate where our 60 %-of-10 rule cannot | overlaps our failed hold experiments; hih0lp's own sequential test gained nothing (their `SUMMARY.md` E2); easier far confirmation raises false STOPs |
| 5 | Divider-column row as a one-sided axis constraint (same repository, `route/_core/route_obstacles.py`) | two-track path selection | our `column` only demotes clusters | double-track sections only; no measured benefit |
| 6 | Cheap false-STOP discriminators: (a) a low group is furniture if other raised returns lie on a line within ±8 m in ≥ 3 separate 1 m bins (same repository, `obstacles/detector.py` `_on_a_line`); (b) shadow ratio behind a cluster (`hih0lp/Moscow_metro_hack_CV`, `tunnel_detector/detector.py`) | the residual low and far compact false events | physically motivated | both need the raw points, so they cannot be screened here; (b) in their own test the verifier it feeds, trained on synthetic data, did not transfer to the real object (`SUMMARY.md` E3) |

**Discarded.** `kurorodev/lct2026_metro`: a research prototype without a false-alarm metric (it says so).
`LesiaJr/metro-obstacle-detector`: a single baseline-subtraction design with no metrics or tests.
`krisikas/MetroLidar2026`: its gauge SDF and cross-correlation speed duplicate ours; its verification suite reads the
first frame of each recording only (`scripts/verify_system.py`, `SELECT data FROM messages LIMIT 1`), so its
"0 false stops on all six recordings" is six frames. `CatherineLensis/NanoMetro1550`: 5.5 % false frames and 95-140 ms
on its own ride check.

## 4. Far rail evidence from ring crossings: implemented, opt-in; fails on real data (§6)

**What it does.** Our near rail tracker stops at 30 m; our disabled far check
(`track._check_far_rails`, replaces a wall-derived curvature that contradicts the rails) looks for a rail
pair in two slabs beyond it and never finds one. The 19 of 24 false STOP detections that the empty recordings
give sit in one recording (`squareT_platform_squareT_switch`) at 83-148 m, the range where our axis is
extrapolated from the walls and a station hall's walls can look like a gentle curve. New evidence source:
per ring, find bumps of at least 6 cm over the lateral median, pair two one gauge apart (1.59 ± 0.10 m, height
difference below 0.25 m), and keep the pairs that agree on one smooth offset curve from the last near rail
(`resense/farrails.py`, an idea of item 1 of §3, written from its description). The rest of the check is
unchanged: the disagreement rule, the axis refit and the shortening of the trusted range.

**What was verified here** (no recordings available):

* on the ray-cast synthetic tunnel, which uses the real ring grid: 12-15 stations reaching 57-64 m, centres
  within 1-3 cm of the truth, about 7 ms per frame, on a centred and on an offset axis;
* with a wall curvature of 0.0015 m⁻¹ (R ≈ 667 m) that the rails contradict (the axis 2.7 m off at 60 m), the slab path does
  **not** correct it, as the log said, and the ring path does (axis at 60 m: 0.246 m against 0.25 m truth,
  trusted range cut to 88 m);
* negative controls: no rail heads, no stations; bumps at a 1.2 m gauge make no pair; a second pair 0.7 m off
  the axis does not steer the result; a tilted frame loses its rings, which is why ring identity is taken
  from the uncorrected frame (`Detector._fit_track` passes it);
* flags off: bit-identical output and an unchanged `estimate_track` result with and without the `ring` argument;
  flags on but walls and rails in agreement: also unchanged.

**What was not verified: anything on real data.** Real rail heads at 30-80 m may give far fewer stations than
the synthetic ones, and an axis change has knock-on effects: a related rule (`walls_min_far_support`) made
platform episodes fall from 15 to 1-10 and was rejected because it made set O, `doubleT_platform` or the ride
worse ([`EXPERIMENTS.md`](EXPERIMENTS.md), "Что пробовали и не выпустили").

**Next, in this order** (docs/DETECTOR_FREEZE.md):

1. *Measure, no decisions involved* (minutes per recording on the team VM):
   `python scripts/far_rail_yield.py --bag /data/for_hackathon/squareT_platform_squareT_switch --every 5`,
   then the other five recordings and the ride (`--npy /data/cache/new_data --every 20 --limit 300`). It
   reports the frames with far rails, their reach, the axis error and **the frames in which the check would
   act**. Stop here if the yield is low or the far centres disagree with our axis where they should agree.
2. *Gate.* Only if step 1 shows a real extension:
   `python scripts/regression_gate.py --cache /data/cache --jobs 4 --config configs/experimental_far_rail_rings.yaml --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json --out docs/evidence/results/regression_gate_<date>_far_rail_rings.json`.
   Every checked metric equal or better with no `--allow`; then the independent safety review of the
   frame-by-frame differences (no STOP lost, delayed or shortened on set O, the real obstacle, the range
   cases and the stress runs); then `detector_freeze.py create` and the seal renewed. If the gate fails, drop
   the two flags; nothing else depends on them.

*Held in reserve:* TunnelGuard's cross-section-template alignment (`core/geometry.py`, ~800 lines, numba,
about 70 ms per frame single-threaded in their measurement). It extends both the lateral and the vertical
geometry to the horizon, but it replaces the whole axis stage, and our ~30 special-case rules were tuned
against the current axis; try it only if the gate above shows the idea is right and not enough. Their range
figures (person 100 / 78 / 33 % at 80 / 120 / 160 m, ray-cast synthetic person, first second of an approach)
are not comparable to ours (6 of 15 windows at 100 m, real person transplanted) and are not evidence that it
helps here.

Why this and not a rule: our documented misses are `CAUTION`s demoted as `beyond_axis` or merged into a
`column` when the trusted range is short (transplanted person at 60 m, 4 of 15 windows;
[`SCORECARD.md`](SCORECARD.md) 8.2, 8.4), and §2 shows that relaxing the demotion instead only adds false
alarms. Extending what is *measured* is the only lever that raises range or removes far false alarms without
giving up the suppression. It is not certain to do either on real data; that is what steps 1 and 2 decide.

## 5. What was added

* **Detector (opt-in, default off):** [`resense/farrails.py`](../resense/farrails.py) (ring identity, pairing,
  consensus); `track.rails_far_rings` in `TrackConfig`, [`configs/default.yaml`](../configs/default.yaml) and the ROS
  copy; a ring-evidence branch in `track._check_far_rails` (the slab branch is untouched) and an optional `ring`
  argument of `estimate_track`, passed by `Detector._fit_track` only when both `rails_far_check_enabled` and
  `rails_far_rings` are on; the profile [`configs/experimental_far_rail_rings.yaml`](../configs/experimental_far_rail_rings.yaml).
* **Tools and tests:** [`scripts/far_rail_yield.py`](../scripts/far_rail_yield.py) (step 1 above) and
  [`tests/test_far_rail_yield.py`](../tests/test_far_rail_yield.py) (20 tests);
  [`scripts/screen_competitor_rules.py`](../scripts/screen_competitor_rules.py) with
  [`tests/test_screen_competitor_rules.py`](../tests/test_screen_competitor_rules.py) (11 tests) and its output
  [`evidence/results/competitor_rule_screen_2026-09-29.json`](evidence/results/competitor_rule_screen_2026-09-29.json),
  which a test recomputes. The screen's rules are in `RULES`: add one to test the next candidate against the same
  evidence in seconds.
* **Licences:** the ring-pair finder is written from the description of item 1, not copied; none of the seven
  repositories carries a licence.

## 6. Real-data round (29.09 afternoon): every candidate through the full gate

**Data and reproduction.** All organizer recordings were downloaded from the organizers' links (the six
recordings' archive checksum matches `scripts/cold_bags.sha256`; the ride through
`scripts/cache_extended_ride.py`, which verifies the published SHA-256) and cached as int16 + zstd
(7 GB in all). The full gate of the unchanged sealed detector on these caches reproduces the sealed 3eeb106
result exactly (0 gated metrics changed), so every row below is comparable with it. Each gate: all six
recordings, set O, the 20-minute ride (8 chunks) and set F straight; ~5 min on 4 vCPU.

| candidate (source) | gate | 5 empty: STOP ep. / events | ride: STOP ep. / events | what else changed |
|---|---|---|---|---|
| sealed baseline | — | 13 / 11 | 31 / 32 | — |
| `lowobj.min_top` 0.08 (the team's fittings measurement) | PASS | 12 / 8 | 25 / 22 | **not shipped**: the organizers' 10 cm box on a rail is measured at 0.055-0.075 m at 10, 25, 45, 50 m (its top falls between rings) and is lost there; `tests/test_envelope.py` now covers 25 and 50 m |
| `fresh_stop_evidence` (team candidate) | FAIL | 9 / 8 | 26 / 27 | set F trolley first detection 151 → 135 m |
| clean run after any demotion (Tactical #2) | FAIL | 10 / 8 | 18 / 22 | set F person 151 → 129 m, 1 m box 124 → 99 m: far objects start life `beyond_axis` |
| clean run, infrastructure reasons incl. shape signatures | PASS | 12 / 10 | 29 / 29 | but the ray-cast hanging-cable and scan-line keep tests fail: shape signatures excluded |
| ego veto, first odometry | PASS | 13 / 11 | 31 / 32 | never fired: 142 odometry restarts in 300 ride frames |
| ego veto, robust odometry (TunnelGuard) | PASS | 13 / 9 | 30 / 27 | — |
| shell attachment (TunnelGuard) | PASS | 13 / 11 | 29 / 31 | — |
| quadratic edge margin 0.3 m / (100 m)² (Tactical #4, calibrated on our axis) | FAIL (quick gate) | 2 / 4 | — | set O small cube first STOP 55.8 → 47.5 m, edge cube 35 → 27.6 m; the 83 m platform end needs 0.33 m of margin, the organizers' boxes at 98-111 m need little |
| far ring rails (§4) | FAIL (quick gate) | 9 / 9 | — | a new low STOP at 3 m on `doubleT_platform` |
| **shipped: clean run (column, overhead, retro, shell) + shell + ego veto** | **PASS** | **12 / 8** | **28 / 26** | set F false detections 12 → 6 (box1.0), 3 → 0 (cable); nothing worse |

**Why the edge-margin idea still matters.** The axis error against the track measured by the anchored set F
placements (p75) is 0.06 / 0.17 / 0.45 / 0.91 m at 60-80 / 80-100 / 100-120 / 120-140 m, far above the
0.15 m-per-100 m margin beyond 80 m, and 7 of the 12 station episodes of `squareT_platform_squareT_switch`
come from one platform-end structure at 83 m that a wall-bent axis puts 0.3 m inside the envelope. The rails
there also curve (1.3-2.4e-4 1/m against 3e-4 from the walls), so neither the rails nor a range-only margin
removes it without costing the organizers' far objects; a per-frame axis uncertainty is the open problem.

**What is left on the ride (28 episodes).** Far structures at 80-155 m that do close in at the train's speed
(static things near the envelope edge; the ego veto correctly keeps them), station structures 4-6 m long at
|lateral| ≈ 1.2 m and 31-48 m, low clusters 11-12 cm above the rail head near a rail (indistinguishable by
height from the real object on the rail), and one wide flat structure across the track at 96 m.

**Seal.** `ee7b920` carries the three defaults; its full gate
([`gate.json`](evidence/cycle_2026-09-29/competitor_rules/gate.json)) is the validation of the new manifest
[`detector_freeze_2026-09-29_competitor_rules.json`](evidence/detector_freeze_2026-09-29_competitor_rules.json);
`python3 scripts/detector_freeze.py verify` passes. Code: `resense/tracking.py` (`explained_run`,
`_carried_along`, `_odometry`), `resense/detector.py` (`_shell`, the veto's speed estimate),
`resense/gauge.py` (`edge_margin_at`, the opt-in quadratic term), with tests in `tests/test_explained_run.py`,
`tests/test_ego_veto.py`, `tests/test_shell_attachment.py`, `tests/test_edge_margin_quadratic.py`.

