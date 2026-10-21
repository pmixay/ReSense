# Independent review: K2 "union" revision 3 (`b88d759`) for 1.3.0

> **Reviewer:** an independent Claude session, dispatched by the captain on the user's request; not an author of the
> candidate. **Under review:** branch `claude/k1-k2-1.3` head `67051c5`, detector commit `b88d759`, switched on by
> exactly `docs/evidence/k1_k2_2026-10-21/cand_eval_commit.patch` (checked line for line against the evaluation tree).
> **Control:** v1.2.0 `3b73bbe`. No detector file was changed. G3 (held-out) was not touched.

## Verdict: **ACCEPT WITH CONDITIONS**

Under the user's terms (range and accuracy first; at most +11 added STOP episodes over Falcon + the ride + the five
empty Pandar recordings, each attributed; a lost or delayed true STOP is blocking), the union is safe to switch on in
1.3.0 **if the captain accepts condition 1 below**. If the user's "delayed true STOP" is read frame by frame, finding
2 makes this a **REJECT**.

1. **Rule explicitly on D_cube05 frame 330 (finding 2).** The union delays one true STOP onset by one frame (0.1 s).
   The train is standing, so no distance is lost. This is the only true STOP the candidate made later in all my runs.
2. **Correct the gain claims before they reach the release notes (finding 1).** The detector's real gain is the
   same-placement column of §2. The standing-person 100 m gain (82 → 255) and the 100 m appearance gain are mostly
   produced by the published track moving the judge harness's object. The judge-method drops (D_cube03, S_cube05_100,
   S_person_150, C_cube1) must be reported as well.
3. **Book the false-alarm budget.** +3 attributed false episodes (+8 counting Falcon's person-episode splits literally)
   of the +11 bound, with the traced causes of finding 3.
4. **Before release:** reseal the detector freeze and update the two default-pinning tests. X3 (G-2) was **not**
   re-run by me (Google Drive quota, §5); it stays the author's result until someone re-runs it.

## 1. Findings (ranked by severity)

| # | severity | finding | reproducer |
|---|---|---|---|
| 1 | **Medium (claims / judge-facing)** | `_published_track` makes the result's `track` the curve on curve frames. The judge harness (`range_test.py`, "own-axis placement") places its objects along that track, so "own placement" puts the object in a different place for each tree. **At the same placement, which lies within ~0.1 m of the driven path where truth exists, the gains are:** B person first STOP **46.49 → 71.19 m** (larger than the claimed 51.8 → 71.19), C person **76.89 / 84.25 → 94.58 / 104.98 m**, B cube05 50.03 → 71.19, C cube05 75.42 → 90.15, with **0 lost frames in all 37 jobs**. But `S_person_100` is **248 → 255**, not 82 → 255: v1.2.0 at the true position already holds 248/260. The README's K1-1 / K1-5 gains are mostly placement. Conversely, by the judge's own-placement method the candidate **drops**: D_cube03 83 frames / 84.59 m → **0**, S_cube05_100 94 → 32, S_person_150 90 → 0, C_cube1 first / held 85.72 / 94.58 → 84.25 / 91.63, B_cube03 41.19 → 39.42 m. The README reports only S_person_150 (as "predicted"). These drops are not detector losses: at the same placement v1.2.0 gets D_cube03 0, S_cube05_100 26, S_person_150 0. They are what a jury scoring with the published track would see. | `runs/range/cmp_ctlatcand_vs_cand_same_placement.txt` (control run with the candidate's object-free baseline files: `scripts`'s `range.sh` logic, tag `ctlatcand`); `runs/range/cmp_ctl_vs_cand_own.txt`; truth: `runs/range/placement_truth.txt` (`scripts/placement_truth.py`, B6 ICP poses): D_cube03 \|control placement − truth\| p50 0.42 m vs candidate 0.10 m; S_cube05_100 0.87 vs 0.10 m. Picture: [`placement_vs_truth.png`](placement_vs_truth.png) |
| 2 | **Medium (blocking under a per-frame reading)** | **D_cube05 frame 330 (R-1): a true STOP onset delayed by one frame.** At control's placement the cube (84.59 m, train standing) is GO/CAUTION over 322–329 in both trees. Control STOPs again at 330; the candidate at 331, then identical. Without the cube, the object-free run is CAUTION at 330–335, so the STOP is caused by the cube: it is a true STOP. The mechanism is tracker association: a curve-added cluster keeps a dying track alive, and that track needs one frame more than a fresh one. 36 of 37 jobs are identical at control's placement; Falcon, the marked bags and the attacks show no other delay. Under the amendment's object-level reading (first STOP equal, no object loses its STOP) this passes; under "a delayed true STOP is blocking" per frame it does not. | `runs/range/cmp_ctl_vs_candatctl_control_placement.txt` (row D_cube05, lost [330]); frames 318–335 printed from `range/ctl/D_cube05.json` vs `range/candatctl/D_cube05.json` (in `runs/range/range_jobs.tar.xz`); object-free decisions from `cache_ctl/squareT_platform_squareT_switch_baseline.json` |
| 3 | **Medium (false alarms, inside the bound)** | **Ride +3 STOP episodes / +8 frames**, reproduced exactly: piece 2 frames 1066–1069, 1071–1072 and 1317–1318; 23 / 26 / 111 → 25 / 29 / 119 events / episodes / frames. Traced on a replay equal to the plain gate run in all 1,331 frames. (a) **1066–1072:** curve clusters added at 1062–1063 (6.7 × 2.3 × 2.5 m, at 122–124 m) join track 447. Three to nine frames later, with no curve addition in those frames, the track is STOP on v1.2.0's **own** clusters, two of them with reason `beyond_axis`. So the union is add-only per cluster and per frame, but not per decision: through the tracker's zone votes it changes v1.2.0's verdict on clusters it did not add. (b) **1317–1318:** track 550 starts from a curve-added cluster at 68.7 m, 0.34–0.86 m above the rail head. In frames 1310–1317 the curve gauge adds 11 such clusters in 6 frames, all topping out at 0.86 m or less above the rail head, 1.7–4.5 m right of the base axis (26 additions in 20 of the 291 traced frames). The joint fit follows a boundary that is not this track's. | `runs/gate/cmp_gate.txt`, `runs/gate/gate_{control,cand}.json`; trace `runs/ride/ride_trace_p2.jsonl.xz` (`scripts/ride_trace.py /data/cache <gate work_cand> 2 1040 1330`; reports "rows differing from the plain gate run: 0") |
| 4 | Low–Medium | **The curve is sometimes wrong inside its own trusted range, with no guard.** B (`roundT_doubleT`) frames 1–7, the detector's warm-up: published curve 3.7–10 m off the driven path within 99–135 m (control: 11–22 m off). C frames 105–124: 21 of 170 curve frames 1.1–1.5 m off at 120–130 m. The trust held after a boundary disappears (previous range − 20 m per period) keeps the curve trusted to 155 m at ride frame 1066, where the base trusts 60 m. On such frames the second gauge is a displaced corridor that adds obstacles, which is the mechanism behind 3 (b). | `runs/b6/curve_wrong.txt` (`scripts/curve_wrong.py`; tracks from `scripts/gauge_stability.py track` per tree in `runs/b6/b6_tracks.tar.xz`) |
| 5 | Low (design) | The curve pass re-clusters the current frame without the low-object, bed, rail-start or straddle stages. The post-stages that then run on the union list (`mark_rail_line`, `_rail_reference`, `_shell`, `_hanging`, `_mount_cross_check`, `no_rail_advisory`) judge the added clusters in the base axis' coordinates (`dy_rail`, `h_all`), which are metres off on exactly the frames where clusters are added. The rail-line protections therefore cannot see a rail-level cluster lying on the curve's rails. This is a plausible contributor to 3 (b); I did not trace which rule would have fired. | `resense/detector.py` lines 406–429 (stages after `_curve_clusters`), 885–936 |
| 6 | Low (display / records) | An added obstacle reports `lateral` measured from the **base** axis (e.g. −1.69 m at ride frame 1317), while `result.track` is the curve. The published model switches between the base and the curve shapes from frame to frame (curve frames: tunnels 404 / 545, switch 417 / 736). The published trusted range on curve frames is shorter than the range to which the base gauge still detects. The ROS `GaugeDisplay` was not run. | `resense/detector.py` `_published_track`, `_curve_clusters` (`k.lateral = b.lateral` / `dy_base`); `runs/markers/*.jsonl.xz` (`curv`, `track_center` per frame) |
| 7 | Info (time) | Per-frame time, each tree alone on the same machine (p50 / p95 ms): ride piece 2, frames 0–899: 33.3 / 51.4 → 42.5–45.6 / 67.6–73.7; B 43.8 / 73.9 → 54.7–56.0 / 94.2–98.0; C 33.4 / 48.8 → 46.1–46.2 / 66.5–68.5; `doubleT_obstacle` 55.6 / 89.3 → 72.5–76.1 / 110.3–115.5 (two candidate runs). That is +25–38 % at p50. Not an acceptance criterion now. | `runs/timing_*.json` (`scripts/timing.py`) |

## 2. Re-derived rows (fresh runs; control = fresh v1.2.0)

| row | control | candidate | author's claim | reproduced? |
|---|---|---|---|---|
| Gate, seal baseline, no `--allow` | exit 0 | exit 0 | exit 0 | yes |
| Ride events / episodes / frames | 23 / 26 / 111 | 25 / 29 / 119 | same | yes, same frames |
| Five empty recordings (episodes) | 11 | 11 (frame for frame identical) | 11 → 11 | yes |
| Six recordings + set O, per frame | — | 0 STOP frames lost; 0 differing detection / warning rows on the six and set O | identical | yes |
| Falcon person STOP frames lost (of 1,360) | — | **0** | 0 | yes |
| Falcon first person STOP | 2972, 124.84 m | **2958, 126.36 m** | same | yes |
| Falcon new STOP frames | — | 33, every one at a control detection / warning of the person (≤ 1.5 m, ≤ 1.0 m) | 33 at the person | yes |
| Falcon STOP episodes | 7 (2 outside the person segment) | 12 (2 outside) | 7 → 12 | yes |
| Marked bags, STOP frames | 126 / 185 / 142 | identical, every object identical | identical | yes (3 frames GO → CAUTION in tunnels 191–193) |
| Range at control's placement (R-1) | — | 36 / 37 identical; D_cube05 loses frame 330 | same | yes (finding 2) |
| B person, own placement | 51.8 / 57.11 m | 71.19 / 78.19 m | same | yes |
| **B person, same placement** | **46.49 / 50.03 m** | **71.19 / 78.19 m** | not reported | new |
| C person, own placement | 82.77 / 91.63 m | 94.58 / 104.98 m | same | yes |
| **C person, same placement** | **76.89 / 84.25 m** | **94.58 / 104.98 m** | not reported | new |
| `S_person_100` own / same placement | 82 / 248 | 255 / 255 | 82 → 255 | numbers yes; attribution no (finding 1) |
| `S_person_150` own / control's / same placement | 90 / 90 / 0 | 0 / 90 / 0 | 0 own, 90 at control's | yes |
| D_cube03 own / same placement | 83 frames, 84.59 m / 0 | 0 / 0 | not reported | finding 1 |

The ICP odometry I recomputed equals the committed P4 file in all 544 steps of A (maximum |dx| difference 0). The
control rows reproduce v1.2.0's history: B 51.8, C 82.77 / 91.63, A 218.38, `S_person_100` 82, `S_person_150` 90,
Falcon 1,360 / 2972 / 124.84 m.

## 3. Code review (`git diff 3b73bbe b88d759 -- resense configs ros2_ws native` + the patch)

* **What the union cannot change:**
  * The track model every stage reads. `_joint_output` returns `base`; the curve rides along as `.curve` and is not
    serialised. The detector's `self.track` is base, so bed, low objects, ego speed, mount, health and clear-distance
    stages see v1.2.0's model.
  * v1.2.0's obstacles. `_curve_clusters` adds only zone-`gauge`, reason-free curve clusters that overlap no base
    obstacle (`_overlap_xy`, 0.3 m margin). It removes only base clusters that are not obstacles and overlap an
    addition, which escalates them.
  * Detector state. Everything that `_corridor` / `_cluster` write (`_far_axis`, `_dy_rail`, `_frame_hd`, `_thin`,
    `_low_height`, `_near_low`) is saved and restored; no module-level caches exist.
  * Numpy and native. The native kernels are stateless and take the model's coefficients; a bent curve (`curv_step`
    ≠ 0) falls back to numpy. **Checked:** on ride piece 2 (1,330 frames, 588 curve frames, including every new STOP
    frame), `RESENSE_NATIVE=0` and native give identical rows, and both equal the gate's rows
    (`scripts/native_vs_numpy_ride.py`).
* **Where it does reach decisions beyond adding a cluster:**
  * The tracker's zone votes and association. Finding 3 (a): later STOPs on v1.2.0's own clusters. Finding 2: an
    onset one frame late.
  * The opinion record. `obs_as` gives curve clusters the replaced base cluster's features, so the doubt model sees
    the base reasons. Revision 3 keeps the sticky rule.
  * `clear_distance`. `_clear_cap` receives the union list, so added obstacles can shorten it. It can only become
    more conservative.
  * The published `track` (finding 1, finding 6).
* **Held trust:** `held − 20·k` decays the curve's range by 20 m per period only while boundaries are missing; there
  is no warm-up guard (finding 4).

## 4. Attacks on scenes the author did not test

Objects ray-cast into the real curve recordings with the unchanged `range_test.py`, at the **same** placement for
both trees (the candidate's curve, ≈ the driven path near the objects): `scripts/attack_range.sh`, scored by
`scripts/cmp_attack.py` → `runs/attack/cmp_attack.txt`.

| scene (B = `roundT_doubleT`, R ≈ 400 m double track; C = `roundT_pressureGate_roundT`, curve entry) | result |
|---|---|
| person 0.3–0.6 m outside the gauge (lateral ±1.6 / ±1.9 m), 0.5 m cube at ±1.4 m, 3 m post at ±2.4 m, both sides, B and C | candidate adds **0** STOP frames in all 16 jobs; where control already STOPs (B +1.6 / +1.9 m, cube +1.4 m, C cube +1.4 m) the candidate is identical |
| 4 m car body (3 × 3.5 m) on the adjacent track (±4.1 m), B and C | 0 STOP frames in both trees |
| receding (5 m/s), crossing, appearing at 100 m, person at ±0.5 m | 0 frames lost; gains on B receding (+3), B / C appearing (+14 / +11), B ±0.5 (+11 / +13), C −0.5 (+13) |
| 40 m straight box at ±4.1 m | not a valid test: `range_test` places an axis-aligned box at the curve's lateral at its centre, so on R 400 m its near end lies on our own track (Y −8.38 vs track −8.09 m at X 69 m); its STOPs are real intrusions in both trees. Kept in the table, discounted |
| Falcon geometry | the full recording (§2) |
| wrong boundary | ride piece 2 traced (finding 3); B warm-up and C 105–124 (finding 4) |

**Not tested (unverified):** S-curves and radii of 300 m or below. My synthetic scene harness
(`scripts/attack_synth.py`, `run_synth.sh`, `cmp_synth.py`, kept for the record) could not reproduce the base
detector's behaviour: the rail pair was found only intermittently, and v1.2.0 did not STOP a person at 48–60 m. A harness
that never STOPs cannot reveal a difference, so its runs are not used. Real data has no S-curve or curve exit of
known geometry; the ride's curves have no truth.

## 5. Positive controls, instrumentation, what was not checked

* **Comparators catch known losses:**
  * marked bags: v5c-15 run fresh, tunnels object 19 **29 → 13** STOP frames, first STOP 55.0 → 27.6 m
    (`runs/markers/per_object_tunnels_v5c_positive_control.txt`);
  * Falcon: v5c-15 fresh, exactly the 10 lost person frames of the v5c review (2972–2975, 3059–3063, 4382), first
    2979 at 124.02 m (`runs/falcon/score_v5c_positive_control.txt`);
  * gate comparator: a planted lost frame (`doubleT_obstacle` 58) is found;
  * range comparator: control against the candidate at own placement shows D_cube03 83 lost frames, a placement
    effect.
* **Instrumentation:** the ride trace equals the plain gate run in all 1,331 frames, every non-timing field. The
  numpy and native replays equal the gate rows. An earlier replay of mine differed in 105 / 400 published-track rows;
  the cause was my script reading the config without unwrapping its top-level `resense:` key (code defaults, union
  off). I fixed it, re-ran, and got 0 differences; nothing from the faulty run is used.
* **Data identity:**
  * the six recordings' frame counts match VM_GUIDE §2.4;
  * set O 1,510 frames; ride 221 splits, archive SHA-256 verified by the intake script;
  * marked bags archive SHA-256 `04d176b4…8682760` = the intake value;
  * `falcon_test.zst` SHA-256 `90dea27d…5611` = Yandex's.
* **Not checked:**
  * **X3 (G-2) was not re-run.** It needs decoded caches of A, D, `doubleT_obstacle` and set O, and Google Drive
    returned "Quota exceeded" for the dataset archive. The author's 0 / 260 stands unverified. If it later ran, the
    result is in `runs/x3/`; see the note at the end.
  * the switch-off identity (ID row);
  * B6 honesty on all ten recordings;
  * the ROS display;
  * the ride and Falcon curve gauges against truth (none exists).

## 6. The post-hoc re-scoring (amendment 1)

* **Arithmetic is right.** Ride 26 → 29 (+3), five empty 11 → 11, Falcon 7 → 12. All 5 extra Falcon episodes are
  splits inside the person's own STOP sequence (outside the person segment 2 → 2), so attributed false episodes are
  **+3**, or **+8** counted literally, against a bound of +11.
* **Hard rows:**
  * R-1 was re-read from frame level ("no STOP frame lost") to object level. The amendment's own wording ("no
    positive object may lose its STOP; a first STOP may be later by at most …") supports that, but the author made
    this mapping for its own candidate, and it conflicts with the user's "a lost or delayed true STOP is blocking".
    Hence condition 1.
  * K1-100 is unchanged as a row but its gain is mostly placement (finding 1).
  * The other hard rows are unchanged and reproduced.
* **Would r3 have been chosen anyway?** Not necessarily. Revisions 2–3 were built to cut false alarms under the
  original strict terms, and they removed real gains (committed r1 outputs: marked objects +22 STOP frames,
  platform 23 first STOP 86.76 → 90.54 m). r1's cost was ride 26 → 35 episodes: +9 attributed, +14 literal with the
  same Falcon splits. Under range-first terms r1 would pass the attributed bound and give more range. I took these r1
  numbers from the author's committed outputs and did not re-run them. r3 is the more conservative and fully
  measured choice; whether to spend more of the +11 budget on r1's gains is the user's decision, not this review's.

## 7. Reproduce

Python 3.12 venv (numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, rosbags 0.11.5, open3d 0.19.0),
`OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `RESENSE_REPO` / `PYTHONPATH` per tree. Trees: `/opt/base` = `3b73bbe`;
`/opt/cand3` = `docs/evidence/k1_k2_2026-10-21/scripts/make_cand.sh b88d759 /opt/cand3`, native built in each.

* **Data:** VM_GUIDE §2 (six recordings and set O caches; ride via `scripts/cache_extended_ride.py`); decoded caches
  via `judgement_2026-10-13/scripts/cache_decoded.py`; ICP via `k1_k2_gauge_2026-10-19/tools/icp_odometry.py`;
  B6 poses from `gauge_stability_2026-10-18/b6_raw.tar.xz`.
* **Gate:** `regression_gate.py --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json` per
  tree, then `scripts/cmp_gate.py`.
* **Falcon:** one stream teed to `f1_false_alarms_2026-10-19/scripts/falcon_trace.py` of control / candidate / v5c,
  then `scripts/score_falcon.py`.
* **Marked bags:** `scripts/markers.sh`, then `n5_markers_2026-10-20/scripts/per_object.py`.
* **Range:** `k1_k2_gauge_2026-10-19/tools/prebuild_range.py` with tags `ctl`, `cand`, `ctlatcand` (control with
  `cache_cand/*_baseline.json` copied in), `candatctl` (the reverse), then `scripts/cmp_range.py`.
* **Attacks:** `scripts/attack_range.sh`. **Ride trace:** `scripts/ride_trace.py`. **Curve against truth:**
  `scripts/curve_wrong.py`. **Placement against truth:** `scripts/placement_truth.py`, `scripts/plot_placement.py`.

All raw outputs are compressed under `runs/` (about 6 MB).
