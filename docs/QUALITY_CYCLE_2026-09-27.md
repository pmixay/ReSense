# Detector quality cycle — 27 September 2026

> **Purpose:** the record of the 27.09 detector cycle: the four open quality problems of 26.09,
> what was tried, what shipped, the independent review of the first version and what it changed,
> the acceptance evidence, the held-out check and the limits.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Status:** shipped on the working branch; sealed in
> [`detector_freeze_2026-09-27.json`](evidence/detector_freeze_2026-09-27.json) (re-sealed after
> two review rounds; detector `352ca13`, measured at `d572807`). No release published.

The user asked to fix four problems of the sealed P3d detector (26.09), to use ML where it helps,
and to re-judge. Five experiments ran in parallel (one agent each, own git worktree, one shared
machine lock), every candidate as an opt-in parameter with the old behaviour as its default and
the same full screen (`scripts/quality_screen.py`: the regression gate against P3d, the
monitoring / overclaim diagnostics, the processing-history stress). The accepted candidates were
merged, screened together, and switched on. Two independent judges then reviewed that first
version and found three safety regressions and several wrong claims, and a second round found one
more bound violated and asked for a measured (not simulated) held-out false-alarm figure; the
[review section](#independent-review-of-the-first-version-and-what-it-changed) lists every finding
and its fix. Every number below is from the final detector (`352ca13`) unless marked. Raw material:
[`evidence/results/quality_cycle_2026-09-27/`](evidence/results/quality_cycle_2026-09-27/)
(experiment reports, every screen's summary, final acceptance and history stress, ablations).

## Result

The full gate of the shipped defaults ([`regression_gate_2026-09-27_quality.json`](evidence/results/regression_gate_2026-09-27_quality.json),
measured at `d572807`, no overrides) passes against the P3d baseline with no waiver, no missing
row and no gated metric worse. Since this revision the gate also prints set F's detected frames
per 50 m bin (the review found that the median first detection hid a trade); they are information
rows, and the one worse bin is stated here: the 1 m box at 50–100 m, 125 → 123 of 133, while
100–150 m gains 41 → 46 (a waiver would have been needed to gate it, and the seal accepts none). The
monitoring-cost limits hold (at most 2.3 pp newly uncertain frames, median monitored
range at least 96.0 % of P3d on every empty recording and the ride).

| Problem (26.09) | P3d | Shipped 27.09 |
|---|---|---|
| 1. Edge objects STOP only at 5–10 m (set O #4 / #6) | #4 2 of 83 frames, first STOP 5.2 m; #6 6 of 125, 10.3 m | #4 **18** frames, first STOP **35.0 m** (held from 38.7 m); #6: its track STOPs from **28.7 m**; the scorer, which matches a detection within 1 m of the centre of this 2 m-wide box, credits 7 frames from 18.3 m |
| 2. Ride false events / STOP episodes (13 km, no obstacles) | 45 / 38 (183 alarm frames) | in-sample **32 / 31** (130 alarm frames); **held out, measured: 37** events (each ride piece run with an opinion model that never saw it); rules only (the opinion off) 43 / 35 |
| 3. Diagnostic GO / range overclaims (set O) | 46 GO (54 in all) | **16** GO (19 in all); decisions unchanged by the caps |
| 4. Clear-scene false STOP depends on processing history | captured node histories 2 STOPs (53 m); history stress 78 STOP events | captured histories **0**; history stress **55** events; rules only 75 |
| Five empty recordings: alarm frames / events / episodes | 58 / 13 / 16 | 40 / 11 / 13; rules only 56 / 13 / 16 |
| doubleT_obstacle (real person, real rail object) | person 58 of 61, rail object 125 of 126, first alarm frame 11 | person **61 of 61**, rail object 125 of 126, first alarm frame **8** — all of it from the envelope reference (58 of 61 from frame 11 with the rails alone) |
| Set O inside objects, STOP frames | 384 of 801 | **411**; background 3 → 0 frames; outside objects unchanged (#5 0, #7 6) |
| Range, set O first STOP / held from | big_above 101.3 / 111.4 m; plank 82.2 / 90.8 m; floating cube 52.5 / 57.5 m | big_above **111.4 / 123.6 m**; plank **87.2 / 95.9 m**; cube **55.8 / 60.8 m** |
| Set F straight (synthetic, the ride) | person 151.0 m, trolley 151.4 m, crate 123.9 m | first detections the same; the 1 m crate 50–100 m 125 → 123, 100–150 m 41 → 46 of 151 frames; every other kind and bin identical |
| Detector time | see [Speed](#speed) | see [Speed](#speed) |

Every number above is in-sample except where stated: the five agents saw set O, the six
recordings and the ride, and the track opinion's negatives are the rules' STOPs on the ride and
the five empty recordings. The held-out evidence is the cross-fitted ride measurement of the
learned component (below), and the placement study.

### What each mechanism contributes (ablations)

One key switched off at a time, the same full screen
([`screens/`](evidence/results/quality_cycle_2026-09-27/screens/)); measured on `65c5a5b` (the
previous opinion model: the first row there was 24 / 25, 9 / 11, 51), except the first row:

| Switched off | Ride events / episodes | Five empty events / episodes | History stress | Set O #4 first STOP / person | Set O inside STOP frames |
|---|---|---|---|---|---|
| nothing (shipped, `352ca13`) | 32 / 31 | 11 / 13 | 55 | 35.0 m / 61 of 61 from frame 8 | 411 |
| the track opinion (`tracking.doubt_extra_hits` 0) | 43 / 35 | 13 / 16 | 75 | 35.0 m / 61 of 61 from frame 8 | 411 (background 3) |
| the envelope reference (`gauge.reference` 0) | 24 / 25 | 9 / 11 | — | 5.2 m (2 frames; #6 10.3 m) / 58 of 61 from frame 11 | 394 |
| far evidence (`tracking.thin_far_min_distance` 0) | 23 / 25 | 9 / 11 | — | 35.0 m / 61 of 61 from frame 8 | 401 |

Read row by row: the ride, five-empty and history gains are mostly the learned opinion, whose
negatives are those same recordings (in-sample 43 → 32; on ride pieces its model never saw,
measured 43 → 37: about half of its in-sample gain holds out); the rules alone keep 43 / 35 ride
events and 75 history events, but remove the captured clear-run STOP (0 with or without the
opinion). The edge cube (5.2 → 35.0 m), the edge box and the real
person's three extra frames are entirely the envelope reference, i.e. the organizers'
sensor-axis placement frame; it changes no ride or empty-recording row. Far evidence gives the
set O range gains (the box at the envelope top 101.3 → 111.4 m, the plank 82.2 → 87.2 m, the
floating cube 52.5 → 55.8 m; 401 → 411 inside STOP frames) and set F's 1 m box +5 / −2 frames,
for one ride event (23 → 24 on `65c5a5b`).

## What shipped (all switched on in `configs/default.yaml` and the dataclasses)

**Envelope reference near the train (problem 1, `gauge.reference` 3: the union).** The
organizers' tool places every set O object from the sensor's X axis, while the detector measured
the envelope from the rails. On straight track the rail axis runs at a small angle to the sensor
axis: median −0.22 to −0.29° on seven of the eight recordings (the ride −0.25°, p10–p90 −0.41 to
−0.07°), but **−1.16°** on `doubleT_obstacle`, and on the roundT recordings the p10–p90 range
reaches −1.41 and +0.15° (frames with a locked rail pair, `|curvature|` ≤ 2·10⁻⁴ m⁻¹). Within
60 m, on such straight track, a return also counts as inside when it is inside the envelope
measured from the sensor axis (the offset clamped to 0.2 m): it takes the sensor-axis lateral
**only where that is nearer the centre** (`gauge.union_shift`). Neither side of the rails'
envelope is narrowed, whichever way the rig is yawed; the sensor-axis frame only adds. Candidates,
the reported lateral, the gauge distance, the bed / low-object / rail-start / clear-cap stages and
the along-track structure rules keep the rails; the rails' own strict mask is kept for the
oversize split and the wall keep. `cluster.floating_free_max_dy` 0.95 → 1.2 m keeps a compact
free-hanging cube reaching into the envelope from the side an obstacle (still inside the 1.40 m
advisory corridor). The first version shipped mode 2, a one-sided shift; see the review.

**Learned track opinion (problem 2, `tracking.doubt_*`, [`resense/opinion.py`](../resense/opinion.py)).**
60 depth-3 gradient-boosted trees (35 KB JSON in
[`resense/models/track_opinion.json`](../resense/models/track_opinion.json), evaluated in numpy,
~0.3 ms and only at a STOP onset) score a track from its last 10 matched clusters (lateral spread
and jumps, envelope share, height / size statistics, demotion shares, range roughness, hit
fraction). A track about to become a STOP with an opinion below the threshold stays advisory
(reason `doubt`) while it has budget: **at most 10 frames (~1 s) over the track's whole life**,
misses and zone flicker included. It is never delayed within 25 m — over a missed frame at its
predicted distance too — and never when its cluster stands at least 1.0 m tall within 40 m (a
standing body reaching into the envelope: every ride track the opinion withheld within 40 m was a
flat return at most 0.5 m tall; set O #6, 1.9 m tall, had been withheld at 28.7 m). It never vetoes
and never takes a STOP down. On the final detector the nearest withheld frame of any recording is
at 26.5 m.

*Training* ([`scripts/track_opinion.py`](../scripts/track_opinion.py),
[report](../resense/models/track_opinion_report.json)), retrained on the shipped detector (collected
with the opinion off): negatives are the STOP rows of the rules on the ride and the five empty
recordings; positives are 102 synthetic sequences ray-cast into real ride frames (person, 0.5 /
1.0 m boxes, trolley, cable, low box, rail object, dog; moving and standing train). Grouped
cross-validation holds out each ride piece or empty recording together with the sequences
injected into it: **held-out AUC 0.975**. Crossing persons were tried as positives and made the
separation worse (the ride's held-out events rose), so ten crossing-person sequences are a test
set only, and none of their onsets is delayed. The dominant feature is the lateral spread of the
track (importance ~0.46): a real object moving across the track looks less like the training
positives, which is why the delay is bounded rather than trusted.

*Threshold with a margin.* The highest threshold that delays no held-out synthetic sequence is
0.03; the shipped threshold is **0.015, a 2× margin** (the lowest held-out positive onset scores at
least twice the threshold).

*Measured on unseen ride pieces* ([`scripts/opinion_crossfit.py`](../scripts/opinion_crossfit.py),
[2× margin](evidence/results/quality_cycle_2026-09-27/opinion_crossfit_2x_margin.json),
[zero margin](evidence/results/quality_cycle_2026-09-27/opinion_crossfit_zero_margin.json)):
four models, each trained without two of the ride's eight pieces and without the synthetic objects
injected into them, each with its own threshold chosen the same way; every pair of pieces is then
run by the full detector with the model that never saw it and counted as the regression gate
counts. Ride false events / STOP episodes:

| | opinion off | held out, 2× margin (shipped setting) | held out, zero margin | in-sample, shipped model |
|---|---|---|---|---|
| ride (13 km) | 43 / 35 | **37 / 34** | 33 / 31 | 32 / 31 |

The margin costs four held-out events; it was chosen on this measurement (a zero-margin model
would show 25 in-sample, 33 held out). One of the four fold models' own zero-margin threshold
(0.066) would delay ten held-out test rows of set O and the crossing persons; at the 2× margin
none is delayed — the reason the margin is kept.

Counted per frame on the labelled recordings (not only where the scorer matches a detection): the
shipped detector withholds nothing on `doubleT_obstacle`, and on set O three frames at 129–141 m,
where no labelled object is inside the envelope (the plank at 134–136 m is labelled outside it in
those frames).

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
its width. This extends the column demotion (tall and narrow = advisory) to some clusters whose box
is 1.0–1.35 m wide with sparse tails: a small, real risk for tall irregular objects.

**Far evidence for approaching tracks (range, `tracking.thin_far_min_distance` 60,
`cluster.weak_min_points` 4).** Beyond 60 m a scan line inside the envelope (flatter than
`min_height`, ≥ 4 strict voxels) or a cluster one voxel under the point-count bar may start or
continue a track, only unambiguously (inside exactly one unmatched track's gate, or none). While
such a track's gauge vote needs those hits, it becomes a STOP only while its distances approach on
a line (5 hits, 2–25 m/s, RMS ≤ 0.5 m) and is **reported as advisory otherwise, never hidden**;
once its clean hits alone vote gauge (within 60 m every hit is clean, so within one zone window)
the usual rules apply, approaching or not (a person walking up to a standing train). Bed and
vault scan lines stay fixed in the sensor frame or jump with the pitch; an object approaches.

## Independent review of the first version and what it changed

Two judges (an execution lens that re-ran everything, and a safety sceptic that audited the
claims against code and raw outputs) reviewed the first version at `8b74cd0` (scores in
[SCORECARD](SCORECARD.md)). Their findings and the disposition:

| Finding | Disposition |
|---|---|
| **Safety:** `gauge.reference` 2 narrowed the strict envelope by up to 0.2 m on the side the sensor axis leaves (which side depends on the rig's yaw): an injected person 0.25 m inside on that side was STOP in 24 of 91 frames at 30–60 m (91 of 91 from the rails) | fixed: mode 3, the union (above). The review's own scenario re-run on `65c5a5b` ([side_person_check.json](evidence/results/quality_cycle_2026-09-27/side_person_check.json)): STOP in 92 of 92 frames at 30–60 m and 67 of 67 at 0–30 m on both sides, identical to the rails alone; `tests/test_envelope_reference.py::test_union_stops_edge_boxes_on_both_sides` checks both sides for both yaw signs end to end; every set O, person and history row as with mode 2 |
| **Safety:** a track ever matched by a far scan line was never reported, not even advisory, unless approaching at ≥ 2 m/s (a person walking up to a standing train); the flag was sticky and inherited by a dense object's track (set F 1 m box: STOP gap 85.3 → 72.9 m) | fixed: advisory, never hidden, and only while the gauge vote needs the far hits (above); `tests/test_far_thin.py` asserts the standing object is reported; the set F loss shrank from 6 frames to 2 (above) |
| **Safety:** the opinion delayed set O #6 (withheld at 28.7 m in frames 569–570, STOP from 24.7 m); zone flicker and misses refilled its delay, so it could exceed 1 s; its threshold sits at the edge of the held-out positives | fixed: a lifetime budget of 10 frames and the standing-body exemption (above; `tests/test_track_opinion.py`); #6's track STOPs from 28.7 m. The threshold is unchanged: a 2× margin (0.0111) gave the ride 36 events on the first version, `doubt_near` 35 m gives 29 / 25 — both screened, neither shipped |
| Claim "0 onsets delayed" on set O / `doubleT_obstacle` / synthetic persons: wrong, the simulation only counted scorer-matched rows | corrected; now counted per frame on the labelled recordings (above) |
| Claim "#6's track STOPs from ~28 m": true only with the opinion off | now true with the shipped detector (28.7 m) |
| Claim "on every recording the rails run at −0.25 ± 0.03°" | wrong: `doubleT_obstacle` −1.16°, and the spread is wider; replaced by the measured figures (above) |
| Claim "set F identical detection": the 1 m box lost frames at 83–85 m | corrected; the gate prints the per-bin rows now, and the remaining −2 frames are stated with the Result |
| The headline credited ride / history / five-empty / person gains without attribution: the ride and history gains are mostly the in-sample opinion, the person gain is entirely the envelope reference | the ablation table above; the README headline states the attribution |
| The committed `bench_native.txt` showed a 3.5 s tracking frame from before the cost bound | re-measured on the shipped code ([Speed](#speed)) |
| Docstrings and config comments said shipped mechanisms were "off by default"; `floating_free_max_dy`'s comment contradicted its value | corrected in `resense/*.py`, `configs/default.yaml` and the ROS copy |

Against the first version these fixes cost the ride 21 / 22 → 24 / 25 events / episodes, the five
empty recordings 9 / 8 → 9 / 11 and the history stress 49 → 51 (the union and far-evidence fixes
account for 21 → 22 ride events, the rest is mostly the lifetime budget: a flickering track at the
standing-train platform no longer gets its delay back), for a hard 1 s bound on any learned delay
and an envelope that is nowhere narrower than the rails'.

**Second round** (the reviewed detector `65c5a5b`; both judges re-ran the screen bit for bit, the
union's never-narrower property frame by frame, the placement run and the benchmarks):

| Finding | Disposition |
|---|---|
| The opinion kept withholding over a missed frame at a predicted 24.7 m / 25.0 m (two ride tracks), inside its stated 25 m bound: the miss branch did not check `doubt_near` | fixed in `352ca13` (`Tracker._doubt_exempt`, used in both branches; `test_a_withheld_track_is_released_when_its_predicted_distance_reaches_doubt_near`); nearest withheld frame now 26.5 m |
| The held-out figure (33) was a simulation from the model of the first integrated detector, at zero margin; the threshold had no margin | the opinion retrained on the shipped detector; a 2× margin; the held-out figure **measured** by running the detector on ride pieces each model never saw: 37 (above) |
| Stale far-evidence comments ("not reported before: not reported") in both YAMLs, `config.py`, `tracking.py`; `stop_keep_thin` / `rail_start_within` "off by default" | corrected |
| `test_far_thin` asserted only "not a STOP" for the held track | it now asserts that the track is reported as advisory |
| "Roughly a fifth of the ride gain survives" was arithmetically muddled | replaced by the measurement (43 → 37 held out, 43 → 32 in-sample) |
| The crossing-person training result was missing from the record | stated with the training (above) |
| Stale README status blocks; the deck / video quoted the 24.09 script's 148 m, the gate reads 151 m; "held from 149 m" in the presentation text; CAUTION 41 % (measured 42.4 %) | corrected; the README's set F row now leads with the gate's figures and states the 0.5 m box (1 of 6) as a blind spot |
| The median farthest placement distance covered matched cases only | both stated (44.3 m over matched cases, 24.5 m over all 72) |
| Launch needs several flags and the sysctl | `scripts/play_bag.sh <bag> [--archive ...]` does steps 0–5 in one command; a CI step runs it on the smoke bag |
| The placement study places objects in the sensor-axis frame, so it cannot show rails-frame generalization | a pre-registered reference-off run of the same plan: 722 of 2 458 (723 with the union): the held-out gain holds from the rails alone ([Held-out check](#held-out-check-organizer-objects-at-new-places)) |

The retraining with a margin costs in-sample ride events (24 → 32; held out 33 → 37) and the
history stress (51 → 55): the price of a learned delay with a safety margin.

## What was tried and not shipped

| Candidate | Result | Why not shipped |
|---|---|---|
| `gauge.reference` 2, the one-sided shift (the first version) | the first version: ride 21 / 22; every set O / person row as the union | narrows the rails' envelope by up to 0.2 m on one side (the review) |
| `tracking.doubt_near` 35 m (instead of the body exemption; first model) | releases #6; ride 29 / 25 | 7 more ride events than the body exemption for the same release |
| The retrained opinion at zero margin (0.03) | in-sample ride 25 / 24; held out, measured, 33 / 31 | no margin: one fold's zero-margin threshold would delay ten held-out test rows; the 2× margin was chosen (in-sample 32, held out 37) |
| The first model's 2× margin (0.0111, before retraining) | ride 36 events / 32 episodes | superseded by the retrained model |
| `track.axis_disagree_hold` 5 (trust after a lost boundary) | captured STOPs 0, ride 41 / 33 with the other P4 keys | in combination identical detections without it; costs 4.5 % monitored range on the platform recording |
| `tracking.zone_min_votes` 5, `tracking.start_clean`, `confirm_hits` 5 | history stress 78 → 55–70 | each delays a set F person / trolley at ~150 m or a set O object by a frame |
| `gauge.reference` over the full range (M2), clamp 0.3 m (M4) | #4 21–25 frames from 42–48 m, #7 6 → 0 | ride +6 events (84 m, 94 m); M4 not screened on the ride |
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
case kept. The plan pins the detector code, so it was registered again for each revision (the
final one: [plan](evidence/results/quality_cycle_2026-09-27/novel_plan.json), committed in
`d572807` before the run) and nothing was tuned on it. It measures sensitivity to new combinations of seen shapes
and seen backgrounds, not real hold-out recall.

| | P3d (26.09) | 27.09 (reviewed) |
|---|---|---|
| matched target frames / visible | 544 / 2 458 (22.1 %) | **723 / 2 458 (29.4 %)** |
| cases with a match | 45 / 72 | 45 / 72 |
| paired-control matches | 0 | 0 |
| median farthest matched distance (over the cases with a match; over all 72) | 32.0 m | **44.3 m** (24.5 m) |
| cases better / worse | | 23 better, 2 worse (−3 and −1 frames) |

Per object and lateral (matched / visible): floating cube 114 / 91 / 25 → **161 / 144 / 55**,
cube on the rail 101 / 74 / 36 → **112 / 93 / 43**, box at the envelope top 4 / 32 / 22 → 3 / 37 / 30,
hanging object 21 / 18 / 6 → 21 / 18 / 6 (for −0.65 / 0 / +0.65 m). Every per-case row is identical
across the three revisions of 27.09: the review fixes and the retrained opinion change nothing here.
[Results](evidence/results/quality_cycle_2026-09-27/novel_results.json.gz).

**Is the gain the placement frame?** The objects are placed from the sensor axis, the frame the
union reference adds, so a second pre-registered plan differs only in `gauge.reference` 0 (the
rails alone; [plan](evidence/results/quality_cycle_2026-09-27/novel_plan_reference_off.json),
[results](evidence/results/quality_cycle_2026-09-27/novel_results_reference_off.json.gz)):
**722 of 2 458** frames, 45 cases, 0 paired controls — one frame fewer than with the union (the
floating cube at +0.65 m). The held-out gain over P3d (544 → 722) holds from the rails alone; it
comes from the other mechanisms of the cycle, not from the organizers' placement frame.

## Speed

Re-measured on the shipped code (`65c5a5b`; `352ca13` changes only the opinion model, its threshold and one branch of its bookkeeping), one core (`OMP_NUM_THREADS=1`), the C++ kernels,
every frame, the 4-vCPU sandbox with nothing else running (the first version's committed file
showed a 3.5 s tracking frame from before the persistent-evidence cost bound; it is replaced).

| Recording | `resense bench`: detector mean / p95 / max | `bench_node_path.py`: decode + detect mean / p95 / max, peak RSS |
|---|---|---|
| set O (`cloud_with_fake_obj`, 120°) | 18.0 / 23.3 / 57.1 ms | 26.5 / 32.2 / 64.9 ms, 179 MB |
| `doubleT_obstacle` (360°) | 22.9 / 32.6 / 41.3 ms | 38.1 / 48.1 / 65.6 ms, 248 MB |
| `roundT_doubleT` (120°) | 21.2 / 30.0 / 32.7 ms | 30.2 / 38.5 / 57.4 ms, 161 MB |
| `squareT_platform_squareT_switch` | 18.6 / 22.7 / 32.9 ms | — |

([`bench_native.txt`](evidence/results/quality_cycle_2026-09-27/bench_native.txt),
[`bench_node_path.txt`](evidence/results/quality_cycle_2026-09-27/bench_node_path.txt).) The
26.09 re-judgement measured 22.7–30.7 ms mean, p95 32.8–42.1 ms for the detector on the same
recordings; the 27.09 mechanisms stay within that. The node path (the PointCloud2 decode of the
organizers' layout, crop, rotation and the detector, without ROS transport) stays below half the
100 ms frame period at p95. No measurement on the 8-core stand exists.

## Limits

- **In-sample.** The rules and the opinion's negatives come from the six recordings and the ride
  they are measured on. The ride figure 32 is in-sample; on ride pieces the opinion never saw the
  measured figure is 37 (2.8 per km), and the rules alone give 43. No other route exists to test on.
- **The opinion's positives are synthetic.** Its threshold keeps a 2× margin below the lowest
  held-out synthetic positive, but a real object unlike the training kinds (irregular debris, a
  lying person, a fallen panel, a person crossing beyond 40 m) may be delayed — by at most
  10 frames (~1 s) in the track's life, only beyond 25 m, and never if it stands 1 m tall within
  40 m. Never a veto.
- **The union reference relies on the organizers' placement frame for its gains.** It narrows
  nothing, but what it adds (the edge cube from 35 m, the person's three frames) exists because the
  organizers measure lateral positions from the sensor axis. Organizer question Q1 (rails or
  sensor axis) is unanswered. At 60 m the addition stops (a step of up to 0.2 m).
- **Far evidence** gains range and costs 2 frames of one set F box sequence at 83–85 m (the
  one worse set F bin): a track started by a far scan line carries its sparse early hits in its hit
  fraction and confirms later.
- **16 GO overclaims remain**: first sightings, the 4-frame chain building up, one lateral jump of
  the far axis, evidence below the envelope floor or beyond the trusted range.
- **History stress 55 events remain**, mostly the standing-train platform structures of
  `squareT_platform_squareT_switch` (82–147 m) under every history.
- The outside box #7 keeps its 6 false STOP frames at 142 m; the large edge box #6 is STOPped from
  28.7 m, not farther.
- **Small objects low on the bed between the rails** are a blind spot the cycle did not address:
  set F's 0.5 m box is detected in 1 of 6 approaches, set O's 0.3 m cubes STOP only from 43–56 m.
- **Objects just inside the envelope edge beyond ~35 m**: a person 0.1 m inside the edge is STOP in
  82–84 of 129 frames at 0–50 m and 0 of 126 at 50–100 m from the rails; the union adds only the
  side towards which the sensor axis is offset (an independent judge's measurement).
- No new real-obstacle recording exists; set O, set F and the placement study are synthetic.

## Acceptance record

- Full gate: PASS against P3d, 0 worse / 0 missing / no `--allow`
  ([gate](evidence/results/regression_gate_2026-09-27_quality.json)); the set F bins are
  information rows (the 1 m box −2 / +5 frames, above). It is also the new regression baseline
  ([baseline](evidence/results/regression_baseline_2026-09-27_quality.json)).
- Monitoring cost and overclaims: [final_acceptance.json](evidence/results/quality_cycle_2026-09-27/final_acceptance.json).
- History stress: [final_history.json](evidence/results/quality_cycle_2026-09-27/final_history.json)
  (P3d: [base_history.json](evidence/results/quality_cycle_2026-09-27/base_history.json)).
- Tests: 731 tests and 6 subtests pass (the full local suite with the ride cache; new in this cycle: `tests/test_envelope_reference.py`,
  `test_track_opinion.py`, `test_clear_cap_persist.py`, `test_history_robustness.py`,
  `test_far_thin.py`); tests of older mechanisms pin only the key that changes an incidental
  detail and also assert their safety outcome with the shipped defaults.
- Seal: [`detector_freeze_2026-09-27.json`](evidence/detector_freeze_2026-09-27.json)
  (the opinion model included); `python scripts/detector_freeze.py verify` in CI.

## Reproduce

```bash
python scripts/quality_screen.py --name mine --baseline docs/evidence/results/regression_baseline_2026-09-26_ride_p3d.json
python scripts/quality_screen.py --name noop --set tracking.doubt_extra_hits=0 --baseline docs/evidence/results/regression_baseline_2026-09-26_ride_p3d.json
python scripts/history_stress.py --out out/history.json
python scripts/novel_placement_eval.py run --plan docs/evidence/results/quality_cycle_2026-09-27/novel_plan.json --out out/novel.json --jobs 4
```

The caches are built as in [`DATASET.md`](DATASET.md); the ride and set O are needed for the gate.
