# X2: the false-STOP ledger of v1.2.0 (2026-10-21)

Branch `claude/x2-ledger-1.3`; detector bytes equal v1.2.0 (`scripts/detector_freeze.py verify` PASS, digest 6d091081...; no file under
`resense/`, `native/`, `configs/`, `ros2_ws/` changed). Deliverables: `scripts/false_stop_ledger.py`, `tests/test_false_stop_ledger.py`
(28 tests, no organizer data needed), this directory.

## Result in one table

| the card's done-when (restated for v1.2.0: 37 episodes, so at least 35 of 37 = 34/36) | result |
|---|---|
| ride 23 alarm events / 26 STOP episodes, five empty recordings 7 / 11 reproduced from a fresh gate run | **reproduced exactly** (below) |
| window replay (150 frames pre-roll, calibration off, fresh detector) reproduces >= 35 of 37 episodes, onset +-2 frames, distance +-2 m | **NOT met: 20 of 37** (pre-roll 300: 23, 600: 29) |
| ... at least 2x faster than full replays | met for that window: 2.64x wall (61.3 s vs 161.9 s, 4 jobs), 2.68x processing time, 2.5x fewer frames |
| window replay from a detector snapshot taken 30 frames before the onset (not a fresh detector) | 37 of 37, every replayed frame identical to the run (see "The window replay") |
| every episode has a pass-by class | **yes, 37 of 37** (25 flagged ambiguous; 20 carry a question for a human, `ambiguous_for_human.md`) |
| `ledger.json` with the PNGs committed, compressed | yes: ledger.json 0.3 MB, 37 PNGs 1.7 MB, whole directory 5.1 MB |
| positive controls for the classifier, classes checked against the snapshots | yes, with misses listed below; 37 of 37 snapshots looked at, 0 disagreements (my reading, not a human's) |
| F2 summary | below |

**The first criterion that the card sets for the window replay is not met and cannot be met by lengthening the pre-roll cheaply.** The far
false STOPs of the sealed detector are decided at the level of millimetres of the fitted track (below), so a fresh detector does not
reproduce them reliably; only a replay from the piece start (a full replay) or from a snapshot of the same detector does.

## 1. The fresh gate run (v1.2.0)

`python scripts/regression_gate.py --cache /data/cache --jobs 4 --baseline docs/evidence/r3_completion_2026-10-20/gate-a-candidate.json`
on commit 54a81f0 of this branch (detector equal to v1.2.0), Python 3.13.16, numpy 2.5.4, native kernel, 4 CPUs, 329 s. Exit 0, "GATE PASS: no
gated metric worse". Against the R3 gate (`gate-a-candidate.json`):

| metric | R3 gate | this run |
|---|---|---|
| five empty recordings: frames / alarm frames / events / STOP episodes | 2287 / 37 / 7 / 11 | **2287 / 37 / 7 / 11** |
| ride: frames / alarm frames / events / STOP episodes / advisory frames | 11271 / 111 / 23 / 26 / 4764 | **11271 / 111 / 23 / 26 / 4764** |
| set O: STOP in visible inside object-frames; false STOP frames outside | 414 of 801; 6 | 414 of 801; 6 |
| doubleT_obstacle labelled hits | 190 / 246 | 190 / 246 |
| set F straight (5 kinds) | - | every gated row "same" |

Not identical: latency rows (this machine is faster) and the **health level of the ride** (ok 11076 / warn 195 here, ok 82 / warn 11189 in
R3): the messages are "latency p95 ... over the 100 ms budget" and "rail pair found in x % of the last 20 frames"; the STOP / alarm
fields do not depend on them. An independent `eval_real.py` replay of the five recordings and the ride (run for debugging) equals the
gate's per-frame outputs in all 13,558 frames, every field but the timing and the latency-driven health fields (checked frame by frame).
The ride needs `<cache>/new_data/intake_manifest.json` (`scripts/cache_extended_ride.py` writes it after verifying the archive's SHA-256);
the VM_GUIDE 2.3 shell pipeline does not, and the gate then refuses ("incomplete or invalid ride cache"). Also `zstd` is not installed in this container image.
Files: `gate/gate_x2.json`, `gate/gate_table.txt`, `gate/config.yaml`, `gate/ride_intake_log.txt`, `gate/per_frame_runs.tar.gz` (the gate's per-frame JSONL, 3 MB;
the ledger reads them).

## 2. The ledger (`ledger.json`, `png/`)

37 episodes in 13,558 empty frames: 11 in squareT_platform_squareT_switch, 26 on the ride, none in the other four recordings. Per row: onset frame,
distance, lateral, size, centre, kind, reason, zone, points, confidence, age, curvature, the track model of the onset frame, `rail_lock`, health,
ego (the detector's own speed fields), mount, the episode (frames, last frame, minimum distance), `window` (fresh window), `checkpoint_window`
(snapshot window), `passby` (class, per-frame classifications, mechanism columns). Kind and reason are empty for 33 of 37 episodes (the
far clusters carry neither); mount is `identity` for 33, `pending` for 4 (ride start); health ok for 36.

| episode | onset m | lat m | size m | curv 1e-3 | rail lock | mount | pass-by class | dy of the position at pass-by | axis error m | fresh window | flagged |
|---|---|---|---|---|---|---|---|---|---|---|---|
| squareT_platform:312 | 82 | +0.8 | 4.2x0.4x0.2 | +0.40 | 1.0 | identity | in_envelope (surface) | 1.42 | 0.66 | fresh | yes |
| squareT_platform:316 | 83 | +0.9 | 3.4x0.5x0.9 | +0.34 | 1.0 | identity | in_envelope (surface) | 1.41 | 0.46 | fresh | yes |
| squareT_platform:437 | 83 | +0.9 | 2.2x0.4x1.2 | +0.29 | 1.0 | identity | side | 1.5 | 0.57 | - |  |
| squareT_platform:490 | 83 | +1.0 | 2.2x0.4x1.2 | +0.27 | 1.0 | identity | side | 1.56 | 0.54 | - |  |
| squareT_platform:500 | 147 | -0.4 | 0.0x0.4x0.7 | +0.25 | 1.0 | identity | side (surface) | 1.26 | 1.66 | fresh | yes |
| squareT_platform:522 | 83 | +1.0 | 2.1x0.4x1.7 | +0.29 | 1.0 | identity | side | 1.6 | 0.64 | - |  |
| squareT_platform:527 | 83 | +1.0 | 2.1x0.4x1.2 | +0.25 | 1.0 | identity | side | 1.56 | 0.54 | - |  |
| squareT_platform:580 | 147 | -0.6 | 0.1x0.4x0.4 | +0.28 | 1.0 | identity | side (surface) | 1.36 | 2.0 | - | yes |
| squareT_platform:612 | 94 | +0.8 | 5.0x0.3x1.6 | +0.29 | 1.0 | identity | side (surface) | 1.81 | 0.99 | fresh | yes |
| squareT_platform:640 | 147 | -0.6 | 0.1x0.4x0.7 | +0.26 | 1.0 | identity | side (surface) | 1.47 | 2.02 | - | yes |
| squareT_platform:692 | 146 | -0.3 | 0.1x0.4x0.7 | +0.27 | 1.0 | identity | side (surface) | 1.54 | 1.83 | fresh | yes |
| new_data:23 | 144 | -0.2 | 0.1x0.4x1.0 | +0.25 | 1.0 | pending | side (surface) | 1.48 | 1.67 | fresh | yes |
| new_data:1378 | 139 | -0.1 | 0.2x0.3x1.9 | -0.04 | 1.0 | identity | side | 3.33 | 3.48 | fresh |  |
| new_data:1393 | 124 | +0.1 | 0.4x0.7x1.6 | -0.09 | 1.0 | identity | side | 3.29 | 3.17 | fresh |  |
| new_data:1847 | 155 | +0.5 | 5.3x1.6x1.8 | -0.54 | 1.0 | identity | side | 1.26 | 0.73 | - |  |
| new_data:2668 | 42 | +0.7 | 1.2x0.4x0.1 | -0.00 | 1.0 | identity | side (surface) | 0.72 | -0.02 | fresh | yes |
| new_data:2729 | 105 | +0.7 | 4.0x0.6x1.2 | +0.22 | 1.0 | identity | in_envelope | -0.43 | -1.16 | fresh | yes |
| new_data:3060 | 97 | +0.5 | 1.8x0.1x0.9 | +0.47 | 1.0 | identity | side (surface) | 1.56 | 1.02 | fresh | yes |
| new_data:5065 | 136 | +0.2 | 0.4x0.5x2.0 | -0.09 | 1.0 | identity | side | 3.08 | 2.9 | - |  |
| new_data:5699 | 112 | -0.7 | 0.2x0.5x1.4 | -0.50 | 1.0 | pending | side (surface) | -2.83 | -2.15 | fresh | yes |
| new_data:5716 | 22 | +1.2 | 1.4x0.7x0.4 | -0.11 | 1.0 | pending | side (surface) | 1.6 | 0.37 | fresh | yes |
| new_data:5901 | 29 | +0.6 | 0.1x0.2x0.1 | +1.40 | 0.0 | pending | in_envelope (surface) | 1.3 | 0.66 | - | yes |
| new_data:6859 | 43 | -1.2 | 4.5x0.9x1.7 | +1.53 | 1.0 | identity | side | -0.72 | 0.47 | - | yes |
| new_data:7338 | 98 | -0.7 | 1.7x0.4x0.5 | -0.22 | 1.0 | identity | side (surface) | -1.09 | -0.35 | - | yes |
| new_data:7347 | 86 | -0.5 | 3.8x0.4x0.4 | -0.46 | 1.0 | identity | side (surface) | -1.42 | -0.97 | - | yes |
| new_data:7859 | 48 | +1.2 | 5.5x0.8x1.4 | -0.59 | 1.0 | identity | side (surface) | 2.39 | 1.23 | fresh | yes |
| new_data:7868 | 41 | +1.2 | 6.0x0.7x1.4 | -0.66 | 1.0 | identity | side (surface) | 2.17 | 0.96 | fresh | yes |
| new_data:7943 | 104 | -0.7 | 2.8x1.6x1.6 | -1.45 | 1.0 | identity | side (by position) | -8.27 | -7.59 | - | yes |
| new_data:9125 | 84 | -1.3 | 1.2x0.5x1.1 | +2.28 | 1.0 | identity | side | -1.46 | -0.2 | - |  |
| new_data:9263 | 110 | -0.2 | 1.2x0.6x1.9 | +1.60 | 1.0 | identity | side (by position) | 9.22 | 9.38 | fresh | yes |
| new_data:9271 | 101 | +1.3 | 0.1x0.1x1.4 | +1.01 | 1.0 | identity | side (by position) | 7.83 | 6.49 | - | yes |
| new_data:9284 | 123 | +0.3 | 0.1x0.6x0.6 | +0.68 | 1.0 | identity | side (by position) | 8.52 | 8.19 | fresh | yes |
| new_data:9786 | 125 | -0.5 | 0.1x0.5x0.2 | -0.25 | 1.0 | identity | bed_rail | -0.7 | -0.16 | fresh |  |
| new_data:9800 | 118 | -0.2 | 1.2x0.6x0.5 | -0.31 | 1.0 | identity | side (surface) | -0.93 | -0.69 | - | yes |
| new_data:10486 | 48 | +0.9 | 0.7x0.2x0.0 | -1.17 | 0.9 | identity | side (surface) | 0.83 | -0.03 | - | yes |
| new_data:10644 | 98 | +0.0 | 5.7x2.1x0.2 | -0.02 | 1.0 | identity | side | 0.04 | 0.04 | fresh |  |
| new_data:10648 | 96 | +0.7 | 7.9x1.9x0.6 | -0.02 | 1.0 | identity | side | 0.7 | 0.0 | fresh |  |

`axis error` = where the carried position stands relative to the re-fitted axis at the pass-by (dy), minus the lateral the onset reported: how far
the far axis was off for the cluster to lie in the gauge. "(surface)" = the structure is the tunnel surface itself (wall, platform edge, vault)
right at the position, "(by position)" = nothing is seen there and the class rests on the carried position (beyond the gauge).

### How the pass-by class is made

1. **Ego transport.** The ego is integrated from the onset: speed per frame (the detector's estimate on 47 % of the ride frames, interpolated over gaps
   of up to 30 frames (25 % of the frames), the organizers' per-split speed from `docs/extended_dataset_intake.json` over longer gaps (28 %); the empty recordings only have the
   estimate), heading change from the track model's curvature, translation along the track's yaw at the vehicle. The path continues into the
   later ride pieces (the pieces restart the detector, not the train). The pitch of the path is not integrated (see checks). Total path of the
   ride: 13,378 m (the DATASET figure is ~13 km).
2. **Band.** The frames in which the carried position is 10-25 m ahead (at most 6, evenly); if the train never gets that close (it stops
   at a platform) the frames within 2.5 m of the closest approach, flagged `beyond_band` (2 episodes, 27.7 and 28.9 m).
3. **Re-fit.** The detector replayed over that stretch gives the track model and cloud of each band frame (the run's own, by the snapshot windows below;
   identical to the run's frames).
4. **Classification** in a window around the position (half length 2 m + 0.05 m per metre travelled, at most 7 m; half width 1.2 m + 0.012 per m, at most 2.5 m;
   height window growing 0.03 m per metre): `in_envelope` = returns with |dy| <= 1.4 m and 0.15 < h <= 3.0 m that are not continuous along the track;
   else `side` (|dy| > 1.4 m) or `overhead` (h > 3.0 m) *structure* = returns that stand out of the tunnel's own surface (in front of the wall by 0.5 m, below
   the vault by 0.5 m) and are not continuous along the track; else the tunnel surface right at the position (flagged); else `side` by position when
   the carried position is beyond 2.4 m of the axis; else `bed_rail` (only returns with h <= 0.15 m) or `phantom` (no returns). The episode class is the
   most frequent class of the band frames; ambiguous when fewer than 70 % agree, when the structure is the tunnel surface, has few points
   (< 12), mixes classes, or sits within 0.2 m of |dy| 1.4 m / 0.3 m of h 3.0 m. All constants are in `ClassifierParams`.

## 3. The window replay

| mode | reproduced (onset +-2 frames, distance +-2 m) | frames replayed | time |
|---|---|---|---|
| full replay (reference) | 37 of 37 (by definition) | 13,558 | 161.9 s wall (4 jobs); 471 s of processing time |
| fresh detector, calibration off, 150 frames pre-roll (the card) | **20 of 37** (squareT 5/11, ride 15/26; far onsets 10/17) | 5,414 | 61.3 s wall; 176 s |
| the same with 300 frames | 23 of 37 | 10,414 | not timed |
| the same with 600 frames | 29 of 37 | 18,138 | not timed |
| detector restored from a snapshot 30 frames before the onset | **37 of 37**, every replayed frame equal to the run (STOP flag, nearest detection, track centre, curvature, bed height) | 7,811 | snapshot pass 8,467 frames, 94.5 s, 0 differing frames; windows 92.2 s |

What the investigation showed (`investigation/`): the 17 episodes that the 150-frame window misses give no STOP at all in the window (16) or a
STOP 2 frames early and 3.4 m nearer (1). Calibration on or off changes nothing in any of 136 replays. The result is not monotonic in the pre-roll
(6859 and 10486 reproduce at 300 frames, not at 600). A fresh detector's fitted track never converges to the run's: after 150 frames
`track.center` still differs in 96-121 of 154 frames and the bed height in 132-150 (checked on three episodes). The differences are tiny, median 0.5 mm in the centre
and 0.05 mm in the bed height at the onset where the window reproduces, 2 mm and 1.1 mm where it does not (one outlier: 0.30 m), which says
that these STOPs are knife-edge decisions of the far track model and that any fresh window is a different draw. The detector state is picklable (5 MB, 7 ms) and a restored detector is exact
(`investigation/snapshot_resume_check.py`), so the snapshot windows reproduce all 37 and serve the ledger's own analysis (pass-by tracks, traces).
For a **changed** detector the snapshots are void: the full replay of all 13.5 k frames takes 162 s at 4 jobs, and it is the only way to say that
an episode is gone. A window may screen a change quickly (2.64x), but an episode that "disappears" in a fresh window may have been a window artifact
and one that stays may be one too.

## 4. Controls (`controls.json`, `controls_summary.json`)

Classes against a known answer, the answer derived from the organizers' labels (their own appended points), not from this classifier:

| source | class | frames | right |
|---|---|---|---|
| set O objects at their labelled positions (10-25 m) | in_envelope (big_center, small_center, small_on_rail, small_edge_inside, long_low_on_rails) | 27 | 25 |
| set O objects at their labelled positions | overhead (big_above 2 x 2 m above the gauge, thin_hanging) | 12 | 12 |
| set O objects carried 110 m -> 10-25 m by the ledger's transport | in_envelope | 26 | 20 |
| set O objects carried by the transport | overhead | 12 | 12 |
| doubleT_obstacle: the person crossing in the gauge (frames 10-60) and the object on the rail (from 75) | in_envelope | 10 | 9 |
| doubleT_obstacle: the second person beside the track (lateral 2.4 m) | side | 5 | 5 |
| synthetic boxes added to real frames of 9 places (9 valid frames; each frame's empty control position had to be clean) | in_envelope / side (beside the wall) / overhead (3.3 m) / bed only / empty above the crown (phantom) | 9 each | 9 each; the empty position inside the envelope was never in_envelope (9/9) |

Misses, all listed in `controls.json`: small_on_rail carried by the transport (6 frames, classified overhead: this object's transported height
is 3.7 m off, its labelled path leaves the tunnel), small_on_rail at its labelled position in one frame (side), long_low_on_rails (0.2 m high) in one
frame and the 0.3 m object on the rail of doubleT_obstacle in one frame (bed_rail: the objects are barely above the 0.15 m bed limit). The
organizers' *outside* objects (small_outside_near, big_outside, big_edge_inside, 2 x 2 m beside the gauge) are not scored: their inner faces stand at
1.2-1.35 m, on the wrong side of the card's 1.4 m for an "outside" truth, and are classified in_envelope and flagged. The class `side`
is therefore tested only by the second person of doubleT_obstacle and the synthetic boxes, not by an organizer object.
**The controls were used while building the classifier** (they exposed the wall-as-structure error, the vault seen only at range, the
pitch drift): they show that the classifier does what it is specified to do, they are not an independent validation of the thresholds.

Transport error against the set-O labels (57 frame pairs, 100 m of travel): x median 2.8 m, p90 4.9 m; y 0.34 / 0.52 m; z 0.09 / 1.8 m. The speed estimate (`investigation/`)
has a mean absolute error of 1.2 m/s per frame against the objects' own steps. The longitudinal window (2-7 m) is sized to that error.

## 5. What was checked and how (CLAUDE.md)

* **Independent source.** Gate counts against the R3 gate's file; the eval_real replay against the gate's per-frame outputs (13,558 frames); the ego path
  against the organizers' per-split speeds and the ~13 km of the ride (13.4 km); the transport against the labels of set O; classes against
  the labels of set O and doubleT_obstacle.
* **Positive control for every negative result.** "No STOP in the fresh window" is only a finding because the same replay reproduces 20 episodes and the
  full replay and the snapshot windows reproduce all 37. The classifier's phantom / bed / side / overhead / in-envelope each have a case with a known answer (section 4).
* **Every label.** Per-frame classes and the counts behind them are in `ledger.json`; all 37 snapshots (BEV and side, onset and pass-by) were
  looked at: 37 agree, 0 disagree (`snapshot_review.json`; it is the author's reading). 25 episodes are flagged by the script, 20 carry a question for a human (`ambiguous_for_human.md`).
* **Physical plausibility.** Ride path 13.4 km; transported positions at the pass-by lie 0-3 m from the axis except four episodes at 6.5-9.4 m (outside the tunnel,
  `by position`); the far axis error is 1.7-3.5 m where the onset axis curved.
* **Instrumentation equals plain run.** The snapshot pass (8,467 frames) and all snapshot windows (7,811 frames) equal the run's frames; a pickled detector equals the original
  for 100 frames.
* **Failures on the way:** the first classifier called the tunnel wall "side structure" for every episode (window larger than the tunnel); integrating the
  gradient made the transported height worse (0.75 m vs 0.09 m median error), so it is not integrated; the vault is invisible within 10 m, so an
  occupancy test of the slices behind the window made it "localized": replaced by a surface outline; `unreached` classes at the end of a ride piece came from
  not following the ride into the next piece.

## 6. F2: the 17 far-onset (>= 100 m) episodes (13 ride, 4 squareT)

| pass-by class | far episodes | of them ambiguous |
|---|---|---|
| side | 15 | 11 |
| in_envelope | 1 (new_data:2729) | 1 |
| bed_rail | 1 (new_data:9786) | 0 |
| overhead | 0 | - |
| phantom | 0 | - |

By mechanism: **13 of 17 (76 %) are a side structure that the far axis put into the gauge**: |axis error| 1.7-9.4 m, median 2.0 m (IQR 1.7-3.5 m); 82 % of the far
episodes are off by at least 0.9 m (the strict edge at 100 m), 76 % by at least 1.4 m. Six are the tunnel surface (wall, platform edge) at the
position: squareT 500, 580, 640, 692 (147 m: axis error 1.7-2.0 m; the onset axis's curvature of 2.5e-4 alone is 2.7 m of sideways extrapolation at 147 m), new_data:23 (144 m), 5699; seven are a localized
side object: a tall thin box (1.9-2.0 x 0.3-0.5 m) on a column row at dy 1.7 m (1378, 1393, 5065) or a structure 7-9 m beside the straight tunnel where the onset axis curved
away (7943, 9263, 9271, 9284: the class rests on the transport). Two more (1847, 9800) are side structures within 0.9 m of the reported lateral. One is an in-envelope structure
(2729: a dense block ahead of the train at the pass-by, probably another train or station equipment: real) and one a bed fitting or phantom (9786: a 0.1 x 0.45 x 0.24 m cluster, only bed and rails at
19 m). The overhead branch (height reference from the extrapolated bed) is empty on the far episodes. 12 of 17 are central (|lat| <= 0.6 m) as reported;
they are central only on the far axis, not in the tunnel. **For F2: the lateral extrapolation of the far axis dominates, not the height reference**; the first branch of the card's task list (a far onset must stay in the gauge under the median of the
last 5 axes) is the one the data supports, with 2 residuals that no axis rule removes (2729, 9786). The 20 non-far episodes are likewise side structures (17), in_envelope
(3: platform kerbs at the 1.4 m limit, a low object) and none overhead.

## 7. What is unverified

* Whether a human agrees with the classes (the 20 questions in `ambiguous_for_human.md`); the snapshot review is mine.
* The transport in curves has no ground truth (set O is nearly straight); the four `by position` classes (7943, 9263, 9271, 9284) rest on it, and the
  structure itself is not visible at the pass-by. The odometry uses the detector's speed estimate (MAE 1.2 m/s per frame, cumulative error 3-5 % of the path) and, for
  28 % of the ride frames, the organizers' per-split speed; the ICP reference of `scripts/speed_reference.py` was not run.
* The classifier's thresholds (window, outline margin 0.5 m, continuity share 0.5) were set by me against the controls and the pictures, not pre-registered.
* The fresh-window reproduction at other detector versions: only v1.2.0 was run; the card's 34/36 may have held for 1.0.
* Health-level counts of the ride differ from R3's (machine speed); not used.

## 8. Reproduce

```bash
pip install -e ".[dev]" "rosbags==0.11.5"; scripts/build_native.sh        # python 3.13 here; open3d is not needed
# data: VM_GUIDE 2.1-2.3 (+ python scripts/cache_extended_ride.py --cache $CACHE/new_data --spool $SPOOL --reserve-gib 3 for the intake manifest)
export RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python scripts/regression_gate.py --cache $CACHE --jobs 4 --baseline docs/evidence/r3_completion_2026-10-20/gate-a-candidate.json --work out/gate --out out/gate/gate.json
python scripts/false_stop_ledger.py --runs out/gate --windows $CACHE --out docs/evidence/false_stops_<date> --sweep 300,600 --jobs 4   # ~10 min
python scripts/false_stop_ledger.py --controls --runs out/gate --windows $CACHE --controls-out controls.json \
    --synthetic-frame roundT_doubleT:150 --synthetic-frame roundT_pressureGate_roundT:150 --synthetic-frame roundT_squareT_pressureGate_squareT:200 \
    --synthetic-frame squareT_platform_squareT_switch:250 --synthetic-frame doubleT_platform:60 --synthetic-frame new_data:3000 \
    --synthetic-frame new_data:6000 --synthetic-frame new_data:9000 --synthetic-frame new_data:4500
python docs/evidence/false_stops_<date>/build_review.py docs/evidence/false_stops_<date>   # after editing its verdict table
```
`--runs` accepts the per-frame JSONL of `regression_gate.py --work` or `eval_real.py --out` (`gate/per_frame_runs.tar.gz` here). `--no-checkpoint` skips the snapshot windows
(the pass-by then uses a fresh detector with 60 frames of pre-roll); `--sweep` adds pre-roll lengths to the fresh-window table.
