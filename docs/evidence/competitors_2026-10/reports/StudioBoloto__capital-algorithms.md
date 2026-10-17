# StudioBoloto/capital-algorithms

## Verdict
Public repo has no production detector: only a ~130-line causal corridor prototype (`runtime/prototype.py`) plus docs and a deck. The headline results (0 alarms on 2,287 infrastructure frames, 43/45 Person frames) come from an unpublished pipeline with a learned range-image U-Net stage and are proxy, in-sample on one event. Not verifiable from this repo.

## Pipeline
Public prototype only (`runtime/prototype.py`); the production stages are described in `docs/architecture.md` and slides 5-6, not implemented here:
1. Input: pre-converted XYZ frames as JSON lines (`prototype.py:run`). No ROS node in the repo; `docs/ros2_contract.md` describes topics only.
2. Fixed corridor: |x| <= 2.0 m, forward 0.5-80 m, raw z 0.10-2.8 m (`CausalClearancePrototype.__init__`, `_candidates`). No floor, rail or axis model.
3. 0.5 m 2-D occupancy cells with >= 4 points each become candidates.
4. Nearest candidate by forward distance.
5. Causal persistence: nearest candidate within 1.5 m of the previous one for >= 2 frames gives an alarm (`process`).
6. Output status `public_causal_baseline`. Production (not in repo): angular/ring density normalisation, local path-profile clearance, causal background suppression, range-image U-Net without intensity as second stage, 2-frame confirmation.

## Candidate ideas
| # | idea | where in code | mechanism | have in ReSense? | expected effect: recall / range / FPR | cost & risk | evidence in repo |
|---|---|---|---|---|---|---|---|
| 1 | Learned range-image verifier (U-Net, no intensity) on geometric proposals | not in repo: `docs/architecture.md` step 6, deck slide 5 | CNN on range-image patch confirms candidate; alarm only after 2 frames | partial: `resense/opinion.py` is a GBM on track features, delay-only, trained on synthetic positives plus ride/empty negatives (`docs/DECISIONS.md` row 19). No range-patch model; `docs/RESEARCH.md` section 4 rejects learned detectors for lack of positives | FPR on platforms/switches could fall if trained on the 13 km ride as negatives; recall unchanged if delay-only. Range: none | high: needs labelled positives; ReSense's own injector (`resense inject`) could supply them; a veto would hide real objects | none: no weights, data or recipe; claim "trained without intensity" is untestable |
| 2 | Angular/ring sampling for density normalisation | `docs/architecture.md` step 2 | Normalise point density across rings before geometry | partial: `resense/clustering.py:_scaled` (range-normalised voxels); `resense/farrails.py:ring_index` and `Cluster.ring_count` (ring evidence; cross-ring rule experimental, `docs/EXPERIMENT_CROSS_RING.md`) | none new | low | none |
| 3 | Causal two-frame nearest-candidate persistence | `prototype.py:CausalClearancePrototype.process` | Alarm after 2 consecutive frames near the same distance | yes, stronger: ReSense needs >= 3 matched frames over >= 0.5 s with track association (`resense/tracking.py`) | none | none | none |
| 4 | Local clearance from a path profile instead of a fixed corridor | described only (`docs/architecture.md` step 3) | Free-gauge estimate without a map | yes: `resense/track.py:_fit_floor`, rail-based gauge (`resense/gauge.py`), wall-based axis (`track.py:estimate_axis_from_walls`) | none | none | none |

Only idea 1 differs in kind, and it is not auditable from the repo.

## Things done worse than ReSense / red flags
- Core detector absent; the headline numbers cannot be reproduced from this repo. Slide 7 notes cite `docs/full_real_submission_report.md`, which is not published.
- "0 alarms on 2,287 infrastructure frames" covers only the five short bags. The 20-min ride (`new_data`, 11,271 frames, ~13 km, where ReSense has 30 STOP episodes) is not mentioned (frame counts from `docs/DATASET.md`).
- 43/45 Person frames is in-sample on the only labelled event. doubleT has 45 alarm frames in total, 43 of them inside the 45 labelled frames. That is frame overlap on one event, not a precision or recall estimate for any other scene.
- `smoke_test.py` checks `examples/sample_output.json` (status `mvp_causal_obstacle_candidate`), while `prototype.py` prints `public_causal_baseline`; CI therefore never checks what the container actually prints.

## Eval/data tooling worth borrowing
- `docs/evaluation.md` states proxy vs precision/recall explicitly; worth copying as a reporting habit.
- Demo overlay convention (`demo/README.md`): red = final alarm, green = manual track used for scoring only, and a "clean" label when geometric proposals exist but the alarm is suppressed. Useful for reviewing FPs on infrastructure scenes.
- `SHA256SUMS.json` manifest for a submission package (tamper evidence). Minor.
- Demo video was checked for metadata only (39.1 s, 1050x556 H.264), not reviewed frame by frame.
