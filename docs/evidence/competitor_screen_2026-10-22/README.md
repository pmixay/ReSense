# Competitor ideas screened on the sealed 1.3.0 detector (22.10)

> **Purpose:** first measurement of the shortlist of [`../../COMPETITOR_SURVEY_2026-10.md`](../../COMPETITOR_SURVEY_2026-10.md)
> on ReSense: which ideas remove false STOP without losing a true one, and where the survey's expected lever does
> not exist in our data. Offline post-filters and one config run; **no detector file changed, the 1.3.0 seal is intact.**
> **Audience:** P3 (detector), P4 (evaluation), captain · **Owner:** P1 session of 22.10 · **Language:** EN
> **Last verified:** 2026-10-22, on `884b1fa` (1.3.0, seal `detector_freeze.py verify` PASS, 42 files).
> **Status:** author evidence, not an acceptance and not a G3 run. **Result: nothing here is good enough to ship or reseal.**
> One exploratory lead (rule `X_R1b_rail_head`) is handed to P3.

## 1. What was and was not measured

| | |
|---|---|
| Data available in this container | the six organizer recordings (2,488 frames) and set O `cloud_with_fake_obj` (1,510 frames), rebuilt as the int16 frame cache by `scripts/cache_frames.py` (counts match `docs/DATASET.md`: 201 / 345 / 252 / 268 / 545 / 877 / 1,510; cache 3.6 GB as documented) |
| **Not available** | the 20-minute ride `new_data` (90.1 GB raw, no cache here), set F straight, the Falcon recording, the marked bags. **Every statement about the ride's false-alarm pool is unmeasured here.** |
| Detector | the sealed 1.3.0 tree, unchanged; Python 3.12.3, numpy 1.26.4, scipy 1.13.1, sklearn 1.5.2, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, native kernels built by `scripts/build_native.sh` |
| The false-alarm pool on this data | **11 STOP episodes / 37 frames, all in `squareT_platform_squareT_switch`**; the other four empty recordings have none. 7 episodes are elongated (2–5 m along X, 82–94 m, lateral +0.8…+1.0 m, three tracks: ids 157, 217, 286), 4 are compact single-scan fragments at 138–147 m (ids 241, 270, 297, 313). The train is at 0–1.8 m/s during all of them (platform stop). |

## 2. Controls that were run before any result was used

| check | method | result |
|---|---|---|
| The environment reproduces 1.3.0 | `regression_gate.py` (no ride, `--allow 'ride.*' --allow 'set_F_straight.*'`) against the committed release gate `integration_1.3_2026-10-21/gate_release_ed67d25.json` | **336 of 342** shared non-timing fields identical (detections, alarms, advisory, episodes, set O per object, labelled hits); the 6 differing are `health.ok/warn` counts of 3 recordings (`doubleT_obstacle`, `doubleT_platform`, `roundT_doubleT`). In my run every warn frame of the first and third (143 + 5) is a latency message (wall-clock dependent); `doubleT_platform` has 64 warn frames, 41 latency and 23 deterministic "rail pair found in n % of the last 20 frames" messages, which fits the reference's 103 = 23 + 80 (the reference's per-frame health is not committed, so that split is consistent, not checked frame by frame) |
| Instrumented run = plain run (CLAUDE.md rule 6) | every frame of the feature pass compared with the plain baseline JSONL, every field except `timing_ms` and the latency-derived health fields | **0 of 3,998 frames differ** |
| Coordinates of the features are right | track coordinates `dy = y − axis(x)`, `h = z − rail head(x)` from `res.xyz` / `res.track`; mean `dy` of a detection's own points against the detector's own `lateral` | all 195 STOP detections of `doubleT_obstacle` within 0.3 m; median 0.025 m over all 293 detections. The 33 large misfits are CAUTION detections at ~155 m measured against the far-axis model; **the features are not valid for those and no rule uses them** |
| Screen harness identity | rule `none` (no veto) scored by the gate's own `recording_entry` / `set_o_entry` | equals the baseline gate on frames, alarms, events, episodes, advisory, every set O object and the labelled hits; the screen stops if not |
| The harness can see damage | rules that destroy the real object (R1c, R5 any) | `doubleT_obstacle` object-on-rail hits 129 → 1 and → 14: the "no loss" rows below are therefore meaningful |
| Look at the data | top-view plots of vetoed rows and of the true object ([`cases.png`](cases.png)) | frame 612 (94 m): a 5 m object at 1.3–2.9 m height among ceiling scan lines (structure); frame 696 (145 m): a lone 16-point vertical stack, 0.05 m wide, no person-like blob; the true object at 56 m is a small box between the rails. (The first row of the plot failed to show its target and is not used.) |

## 3. Results

Rules and thresholds were fixed before reading any result, from the survey and the hakatanon report (ported by description, thresholds
unchanged, nothing tuned). A vetoed STOP is demoted to CAUTION, never deleted. Counts are the gate's: five empty recordings, `doubleT_obstacle`
labelled hits (190 at baseline), set O inside-object STOP frames (414). "Episodes" count GO→STOP transitions of the filtered frames
(a post-filter can split one track into several; see the last row).

| rule (survey idea) | empty STOP frames | empty episodes | `doubleT_obstacle` hits | set O inside STOP frames | what was lost | verdict |
|---|---:|---:|---:|---:|---|---|
| none (1.3.0) | 37 | 11 | 190 | 414 | | |
| **R1a opacity** (1: returns behind the object, d > 60 m, ≥ 2) | 25 | 6 | 190 | 410 | 4 frames of `big_center` (first/held unchanged) | see §4 |
| **R1b front lift** (1: ground in front ≥ 0.1 m above the object's bottom, d > 40 m) | 23 | 6 | **174** | 414 | **16 frames of the real object on the rail** (129 → 113 hits) | rejected |
| **R1c attachment ratio** (1: outside returns > own) | 28 | 10 | **61** | 363 | the real object on the rail 129 → 1; set O `big_above` 56 → 34 frames, first STOP 111.4 → 73.3 m | rejected |
| **R5 line, elongated** (5: ≥ 2 m long on a ≥ 16 m same-height line) | 32 | 8 | 190 | 409 | `big_edge_inside` loses its held STOP (10.3 m → none), `long_low_on_rails` held 95.9 → 90.8 m | rejected |
| **R5 line, any** (5) | 32 | 8 | **75** | 394 | the real object on the rail 129 → 14 | rejected |
| R1 all, R1 + R5 | 19 | 6 | 61 | 359 / 354 | as R1c | rejected |
| *X: R1b with the rail-head plane (exploratory, chosen after the data)* | **16** | **7** (4 false tracks, was 7) | 190 | 413 | **1 frame of set O `small_on_rail`, first STOP 42.7 → 40.9 m** | lead only, §4 |

Not run, with the reason:

| idea | why not |
|---|---|
| 3 graded trust beyond the axis range (the survey's largest upside) | **the lever is not there on our data.** For `big_above` beyond 100 m the axis is trusted to 201–225 m (`track.axis_valid`), yet the detector reports nothing at all in 62 of 68 frames, not even a `beyond_axis` CAUTION: the limit is sparse returns inside the gauge (16 returns at 200 m, 0–4 in the envelope). Curves are already handled by 1.3.0's K2 union. Cheap form tested instead, below. |
| 6 pooled carried-along veto | acts only at ≥ 4 m/s; the train is at 0–1.8 m/s during all 11 false episodes here. Needs the ride. |
| 7 turnout branch hypotheses | needs a new rail-pair model; its 7 elongated rows are three tracks in one recording, too few to evaluate. The front-lift rows suggest those three are structure lines at lateral +0.9 m. |
| 2 structure peeling, 4 inner-wall sight line, 8 context features for the doubt model | new clustering / axis code plus curve injection harness; not attempted. 8 depends on 1. |

**Idea 3 in its cheapest form (config only): `farrange.enabled=true` on the Pandar** ([`results/gate_farrange_enabled_on_pandar.json`](results/gate_farrange_enabled_on_pandar.json),
`--set farrange.enabled=true`, same cache): **18 of 324 fields differ and none improves.** Set O `big_above` loses 5 STOP frames, first STOP 111.4 → 101.3 m, held
from 123.6 → 111.4 m; `monitored_range_median` falls on 5 of 6 recordings (e.g. `roundT_squareT_pressureGate_squareT` 132.5 → 110.0 m); advisory frames rise by 4–12.
Five-empty STOP counts and `doubleT_obstacle` hits unchanged. The gate fails. Rejected.

## 4. What this means

* **No idea tested here brings a clear gain.** The only rule that does not hurt a real object (R1a) works as a "this structure continues behind it"
  test, not as opacity: all 12 vetoed false rows are the elongated structures at 82–94 m (three tracks, one recording); the four compact fragments
  at 138–147 m that the survey expected idea 1 to catch have `behind_n` = 0 and are untouched. The real positive is at 55 m, below R1a's 60 m gate,
  so **no real object beyond 60 m tests it.** Its only measurable cost, 4 STOP frames of `big_center`, comes from the organizers' generator, which inserts
  objects without occlusion, so far synthetic boxes can have returns behind them; a real box would not. The gate's rule "STOP frames must not drop" would still fail on it.
* **Exploratory lead `X_R1b_rail_head`** (veto if d > 40 m and the highest return in front of the object, in its lateral band and below its top, is
  ≥ 0.15 m above the **rail-head plane**): false STOP frames 37 → 16 and false tracks 7 → 4 (all three elongated tracks gone), `doubleT_obstacle` untouched
  (190 / 190), set O one frame and 1.8 m on the synthetic cube `small_on_rail`. Why it is not more: it was chosen after seeing that R1b's failure is a rail
  artefact (the rail head in front of an object on a rail is 0.107–0.129 m above its bottom in all 16 lost rows; on the real positive no STOP row has the ground in front higher than
  −0.004 m above the rail head, so the margin to 0.15 m is real, but on one object), so it is tuned on the single real positive and the single false recording; it still costs a set O frame;
  the compact fragments (4 of the 7 false tracks, 23 of the 37 baseline frames: ids 241, 270, 297, 313) are not removed, only 16 STOP frames remain in total, mostly id 313; and the evidence is one recording. It **needs the ride** (P4's held-out parts) and a decision on the set O frame **before** it is anything but a hypothesis.
* **Nothing was resealed.** The permission to reseal for "something really good" was not used: no tested idea passes the gate's own rule (no true STOP lost) with a measurable gain.
* **Unverified:** everything about the ride and Falcon; any tracker-level effect of a veto (a post-filter is a first-order proxy, DECISIONS row 30);
  the ported thresholds are the survey's description, not the source code of the other repositories; the per-laser-row depth-edge test of idea 1 was not ported (no ring per
  processed point, no threshold given).

## 5. Reproduce

```bash
export SCRATCH=<a work directory with ~20 GB free>
# 1. environment: python3.12 venv with the pins above, then scripts/build_native.sh
# 2. data: scripts/build_cache.sh (six bags, one at a time) and scripts/build_setO.sh -> $SCRATCH/cache/<bag>/
# 3. baseline and the variant:   scripts/run_variant.sh base ;  scripts/run_variant.sh farrange_on --set farrange.enabled=true
# 4. features (one process per recording; RESENSE_REPO = the checkout under test):
python scripts/context_features.py $SCRATCH/cache <bag> $SCRATCH/out/feat/<bag>.jsonl
# 5. screen (stops unless the identity control reproduces the baseline gate):
python scripts/screen_eval.py --feat $SCRATCH/out/feat --base $SCRATCH/out/base/gate.json --out $SCRATCH/out/screen
```

Files: `scripts/` (feature pass, evaluator, plot, cache builders, variant runner), `results/` (`screen.json` with every vetoed row, `screen_table.txt`, the baseline gate of
this run and the `farrange` gate), `cases.png`.
