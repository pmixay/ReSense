# Detector quality cycle — 27 September 2026

> **Purpose:** the record of the 27.09 detector cycle: the four open quality problems of 26.09,
> what was tried, what shipped, the acceptance evidence, the held-out check and the limits.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Status:** shipped on the working branch; sealed in
> [`detector_freeze_2026-09-27.json`](evidence/detector_freeze_2026-09-27.json). No release published.

The user asked to fix four problems of the sealed P3d detector (26.09), to use ML where it helps,
and to re-judge. Five experiments ran in parallel (one agent each, own git worktree, one shared
machine lock), every candidate as an opt-in parameter with the old behaviour as its default and
the same full screen (`scripts/quality_screen.py`: the regression gate against P3d, the
monitoring / overclaim diagnostics, the processing-history stress). The accepted candidates were
merged, screened together, and switched on. Raw material:
[`evidence/results/quality_cycle_2026-09-27/`](evidence/results/quality_cycle_2026-09-27/)
(experiment reports, every screen's summary, final acceptance and history stress).

## Result

The full gate of the shipped defaults ([`regression_gate_2026-09-27_quality.json`](evidence/results/regression_gate_2026-09-27_quality.json),
measured at `25498c1`, no overrides) passes against the P3d baseline with no waiver, no missing
row and no gated metric worse; the monitoring-cost limits hold (at most 3.3 pp newly uncertain
frames, median monitored range at least 96.0 % of P3d on every empty recording and the ride).

| Problem (26.09) | P3d | Shipped 27.09 |
|---|---|---|
| 1. Edge objects STOP only at 5–10 m (set O #4 / #6) | #4 2 of 83 frames, first STOP 5.2 m; #6 6 of 125, 10.3 m | #4 **18** frames, first STOP **35.0 m** (held from 38.7 m); #6 7 frames, first STOP **18.3 m** (its track STOPs from ~28 m; the scorer's 1 m lateral tolerance credits 7) |
| 2. Ride false events / STOP episodes (13 km, no obstacles) | 45 / 38 (183 alarm frames) | **21 / 22** (85 alarm frames); over the ride and the five empty recordings 2 alarm frames that P3d did not have (95.7 m, 118.4 m), 127 of P3d's 241 gone |
| 3. Diagnostic GO / range overclaims (set O) | 46 GO (54 in all) | **16** GO (19 in all); decisions unchanged by the caps |
| 4. Clear-scene false STOP depends on processing history | captured node histories 2 STOPs (53 m); history stress 78 STOP events | captured histories **0**; history stress **49** events (the three captures, and seeded dropped-frame / catch-up / offset / dither histories on the five empty recordings) |
| Five empty recordings: alarm frames / events / episodes | 58 / 13 / 16 | 31 / 9 / 8 |
| doubleT_obstacle (real person, real rail object) | person 58 of 61, rail object 125 of 126, first alarm frame 11 | person **61 of 61**, rail object 125 of 126, first alarm frame **8** |
| Set O inside objects, STOP frames | 384 of 801 | **411**; background 3 → 0 frames; outside objects unchanged (#5 0, #7 6) |
| Range, set O first STOP / held from | big_above 101.3 / 111.4 m; plank 82.2 / 90.8 m; floating cube 52.5 / 57.5 m | big_above **111.4 / 123.6 m**; plank **87.2 / 95.9 m**; cube **55.8 / 60.8 m** |
| Set F straight (synthetic, the ride) | person 151.0 m, trolley 151.4 m, crate 123.9 m | identical detection; crate false detections 12 → 11 |
| Detector time (gate, 4 parallel jobs) | 360°: mean 22.4 / p95 32.5 ms | 24.5 / 34.2 ms |

Every number above is in-sample except where stated: the five agents saw set O, the six
recordings and the ride. The held-out evidence is the placement study below and the
cross-validation of the learned component.

## What shipped (all switched on in `configs/default.yaml` and the dataclasses)

**Envelope reference near the train (problem 1, `gauge.reference` 2).** The organizers' tool
places every set O object from the sensor's X axis, while the detector measured the envelope from
the rails; on every recording the rails run at −0.25 ± 0.03° to the sensor axis on straight track
(0.2 m at 50 m). Within 60 m, on straight track (|curvature| ≤ 2·10⁻⁴ m⁻¹) with the rail pair
locked, the strict envelope is now measured from the sensor axis, the rail-to-sensor offset
clamped to 0.2 m. Candidates, the reported lateral, the gauge distance, the bed / low-object /
rail-start / clear-cap stages and the along-track structure rules keep the rails; the rails' own
strict mask is kept for the oversize split and the wall keep. `cluster.floating_free_max_dy`
0.95 → 1.2 m keeps a compact free-hanging cube at the edge an obstacle (still inside the 1.40 m
advisory corridor). Not a union: rejected unions added ride events (M2: +6 ride events).

**Learned track opinion (problem 2, `tracking.doubt_*`, [`resense/opinion.py`](../resense/opinion.py)).**
60 depth-3 gradient-boosted trees (35 KB JSON in
[`resense/models/track_opinion.json`](../resense/models/track_opinion.json), evaluated in numpy,
~0.3 ms and only at a STOP onset) score a track from its last 10 matched clusters (lateral spread
and jumps, envelope share, height / size statistics, demotion shares, range roughness, hit
fraction). A track about to become a STOP beyond 25 m with an opinion below 0.0222 stays advisory
(reason `doubt`) for 10 more matched frames (~1 s), and is released immediately within 25 m.
It never vetoes and never takes a STOP down. Training ([`scripts/track_opinion.py`](../scripts/track_opinion.py),
[report](../resense/models/track_opinion_report.json)): negatives are the STOP rows of the rules on
the ride and the five empty recordings; positives are 102 synthetic sequences ray-cast into real
ride frames (person, 0.5 / 1.0 m boxes, trolley, cable, low box, rail object, dog; moving and
standing train). Grouped cross-validation holds out each ride piece or empty recording together
with the sequences injected into it: **held-out AUC 0.974**. Set O, doubleT_obstacle and 10
synthetic crossing persons are never trained on: 0 onsets delayed. The model was retrained on the
shipped detector's own tracks after the merge.

**Monitored-range caps (problem 3, `health.clear_cap_thin`, `health.clear_cap_persist` 4,
[`resense/evidence.py`](../resense/evidence.py)).** `clear_distance` is also capped by (a) the
nearest supported, undemoted scan-line cluster inside the envelope within the trusted range (the
M2 idea without its CAUTION) and (b) persistent sparse evidence: compact, isolated blobs of ≥ 2
envelope returns chained over 4 frames at constant lateral / height and a constant approach, as a
static object approaching the train would be. Neither changes a detection or a decision.

**History robustness (problem 4).** `tracking.gate_along_only`: the approach allowance widens the
association gate along the track only (it used to widen the whole 3D sphere, which joined
fragments on opposite sides; the same fix was found independently by the ride experiment).
`cluster.column_width_trim` 0.05 with `column_width_trim_min_cut` 0.25 m: the column rule reads the
width of the body between the 5 % and 95 % lateral quantiles when the trimmed tails are sparse
(span ≥ 0.25 m), so a 4-voxel fragment joined at the DBSCAN radius (the 26.09 clear-run cluster:
1.10 m box, 0.69 m body) no longer turns a column into an obstacle; a dense 1.0–1.1 m body keeps
its width.

**Far evidence for approaching tracks (range, `tracking.thin_far_min_distance` 60,
`cluster.weak_min_points` 4).** Beyond 60 m a scan line inside the envelope (flatter than
`min_height`, ≥ 4 strict voxels) or a cluster one voxel under the point-count bar may start or
continue a track, only unambiguously (inside exactly one unmatched track's gate, or none), and a
track that ever used such evidence becomes a STOP only while its distances approach on a line
(5 hits, 2–25 m/s, RMS ≤ 0.5 m). Bed and vault scan lines stay fixed in the sensor frame or jump
with the pitch; an object approaches.

## What was tried and not shipped

| Candidate | Result | Why not shipped |
|---|---|---|
| `track.axis_disagree_hold` 5 (trust after a lost boundary) | captured STOPs 0, ride 41 / 33 with the other P4 keys | in combination identical detections without it; costs 4.5 % monitored range on the platform recording |
| `tracking.zone_min_votes` 5, `tracking.start_clean`, `confirm_hits` 5 | history stress 78 → 55–70 | each delays a set F person / trolley at ~150 m or a set O object by a frame |
| `gauge.reference` over the full range (M2), clamp 0.3 m (M4) | #4 21–25 frames from 42–48 m, #7 6 → 0 | ride +6 events (84 m, 94 m); M4 not screened on the ride |
| Opinion threshold with a 2× safety margin (0.0111) | ride 36 events / 32 episodes | kept for the record; the shipped threshold delays no held-out positive (see limits) |
| Logistic sparse-blob scorer for the range cap | held-out AUC 0.936 on synthetic cubes | GO 30–37 within the limits: the physically motivated chain rule does better |
| Vault-anchored far height reference | +4–8 frames expected | cannot tell a tunnel-profile change from reference drift; high false-alarm risk |
| Chain length 3, coasting, gap-skipping for the range cap | GO 12–20 | fail the 95 % range retention on roundT_doubleT |

Every screen is in [`screens/`](evidence/results/quality_cycle_2026-09-27/screens/) and every
experiment's own account (including failures) in
[`experiment_reports.json`](evidence/results/quality_cycle_2026-09-27/experiment_reports.json).

## Held-out check: organizer objects at new places

The 72-case protocol of 26.09 ([protocol](evidence/results/p4_novel_protocol_2026-09-26.json)):
the organizers' own point sets of four set O objects (0.3 m cube floating, 0.3 m cube on the rail,
2 × 2 m box at the envelope top, 5 cm hanging object) transplanted at sensor lateral −0.65 / 0 /
+0.65 m onto the five empty recordings and the ride, paired with the unmodified background, every
case kept. It was registered for the 27.09 detector before its run
([plan](evidence/results/quality_cycle_2026-09-27/novel_plan.json)) and no candidate was tuned on
it. The plan pins the code, so it was registered again twice: when the evaluator gained `--jobs`
(before any result was read), and after the persistent-evidence cost bound of `25498c1`, which
only shortens `clear_distance` (the matching reads detections): the run on the final code
reproduces every per-case row of the earlier run. It measures sensitivity to new combinations of seen shapes and seen
backgrounds, not real hold-out recall.

| | P3d (26.09) | 27.09 |
|---|---|---|
| matched target frames / visible | 544 / 2 458 (22.1 %) | **723 / 2 458 (29.4 %)** |
| cases with a match | 45 / 72 | 45 / 72 |
| paired-control matches | 0 | 0 |
| median farthest matched distance | 32.0 m | **44.3 m** |
| cases better / worse | | 23 better, 2 worse (−3 and −1 frames) |

Per object and lateral (matched / visible): floating cube 114 / 91 / 25 → **161 / 144 / 55**,
cube on the rail 101 / 74 / 36 → **112 / 93 / 43**, box at the envelope top 4 / 32 / 22 → 3 / 37 / 30,
hanging object 21 / 18 / 6 → 21 / 18 / 6 (for −0.65 / 0 / +0.65 m).
[Results](evidence/results/quality_cycle_2026-09-27/novel_results.json.gz).

## Limits

- **In-sample.** The rules and the opinion's negatives come from the six recordings and the ride
  they are measured on. The ride figure 21 is in-sample; the opinion's grouped cross-validation
  (each ride piece held out) simulates 42 → 33 events kept at the shipped threshold (the
  simulation is an upper bound: it cannot remove the keep rules of a withheld track).
- **The opinion's threshold is at the edge of the held-out positives.** 0.0222 is the highest
  threshold that delays none of the 102 held-out synthetic sequences; the lowest held-out onset
  score is just above it. A real object unlike the training kinds (irregular debris, a lying
  person, a fallen panel) may be delayed by ~1 s beyond 25 m. With a 2× margin the ride keeps 36
  events. Never within 25 m, never a veto.
- **The sensor-axis reference relies on the organizers' placement frame.** Near the train the
  envelope moves up to 0.2 m towards the sensor axis: on these rigs an object up to 0.2 m inside
  the rails' envelope on one side between ~45 and 60 m is CAUTION until nearer, the other side
  gains the same. Organizer question Q1 (rails or sensor axis) is still unanswered. At 60 m the
  reference returns to the rails (a step of up to 0.2 m).
- **16 GO overclaims remain**: first sightings, the 4-frame chain building up, one lateral jump of
  the far axis, evidence below the envelope floor or beyond the trusted range.
- **History stress 49 events remain**, mostly the standing-train platform structures of
  `squareT_platform_squareT_switch` (82–147 m) under every history.
- The outside box #7 keeps its 6 false STOP frames at 142 m; the large edge box #6 is STOPped from
  ~28 m, not farther.
- No new real-obstacle recording exists; set O and the placement study are synthetic.

## Acceptance record

- Full gate: PASS against P3d, 0 worse / 0 missing / no `--allow`
  ([gate](evidence/results/regression_gate_2026-09-27_quality.json)); it is also the new
  regression baseline ([baseline](evidence/results/regression_baseline_2026-09-27_quality.json)).
- Monitoring cost and overclaims: [final_acceptance.json](evidence/results/quality_cycle_2026-09-27/final_acceptance.json).
- History stress: [final_history.json](evidence/results/quality_cycle_2026-09-27/final_history.json)
  (P3d: [base_history.json](evidence/results/quality_cycle_2026-09-27/base_history.json)).
- Tests: the whole suite passes (new: `tests/test_envelope_reference.py`,
  `test_track_opinion.py`, `test_clear_cap_persist.py`, `test_history_robustness.py`,
  `test_far_thin.py`); tests of older mechanisms pin only the key that changes an incidental
  detail and also assert their safety outcome with the shipped defaults.
- Seal: [`detector_freeze_2026-09-27.json`](evidence/detector_freeze_2026-09-27.json), 31 files
  (the opinion model included); `python scripts/detector_freeze.py verify` in CI.

## Reproduce

```bash
python scripts/quality_screen.py --name mine --baseline docs/evidence/results/regression_baseline_2026-09-26_ride_p3d.json
python scripts/history_stress.py --out out/history.json
python scripts/novel_placement_eval.py run --plan docs/evidence/results/quality_cycle_2026-09-27/novel_plan.json --out out/novel.json --jobs 4
```

The caches are built as in [`DATASET.md`](DATASET.md); the ride and set O are needed for the gate.
