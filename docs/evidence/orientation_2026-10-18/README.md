# B4: the 24 sensor orientations with auto-calibration (N2 task 1, W3) — 18.10

> **Observation only.** No detector code was changed. Development data. Owner: P4.
> Question: if a lidar is mounted, or reports its axes, differently from the configured Pandar mapping
> (`forward=-y left=+x up=+z`), does the node find the right orientation? And what does it report until it does?
> It must not be a silent `GO`.

## How

`scripts/orientation_battery.py` rotates every frame of a decoded recording as if the sensor were mounted turned
(the judge's `probe.py` transform), for all **24** axis-aligned proper rotations. Each runs through a fresh node replica
with the default configuration (`auto_calibrate` on, `search_orientations` on, `keep_up_axis` true: 8 candidates). Per
frame it records the decision, the calibration status and the orientation the detector adopted. The correct answer for
a rotation `Rt` is the correction `Rt^T`; the analysis ([analyse_b4.py](analyse_b4.py)) compares the adopted label with it.

* Recordings: `doubleT_obstacle` (201 frames, train standing, real obstacle, STOP on 193 frames) and
  `roundT_squareT_pressureGate_squareT` (545 frames, moving, no obstacle, 0 STOP).
* Versions: 1.1.0 (`492e407` tree) and 707ea9c. Runtime of the P4 protocol.
* **The Falcon manual's native frame** (x up, y right, z forward) is case 12: it is the rotation `R_vs · M` that such a
  cloud presents to the configured mapping, derived, not guessed.

## Checks

| check | result |
|---|---|
| Control: the unrotated case equals a plain `probe.py` run | **201 / 201** and **545 / 545** decisions equal |
| The adopted orientation is the right one | in all 8 cases where one is adopted, the label equals the expected correction exactly |
| Versions | 1.1.0 and 707ea9c are identical in all 48 cases, field by field, and their plain runs are equal |
| What the wrong-mount STOPs are on | one case inspected frame by frame (below) |

## Result (identical on both versions)

| group | rotations (index) | orientation found | status at the end | decisions until then / throughout | `doubleT_obstacle` STOP (plain 193) | moving, empty recording STOP (plain 0) |
|---|---|---|---|---|---|---|
| **A. up axis vertical** (upright or upside-down) | 0–3, 8–11 | **yes, correct, at frame 1** (identity: kept) | ok / identity | frame 0: `FAULT` or `CAUTION`; case 1: a single `GO` | 191–193; after adoption **198 / 200** decisions equal the plain run | 0; after adoption **534 / 544** equal |
| **B. sideways, never adopted** (spin axis along the track; **includes the Falcon native frame**, case 12) | 12–15, 20–23 | no | `pending` (all 201 frames), `fallback` from frame 399 | `CAUTION` on every frame of the empty recording; never `GO` | 0 (cases 14, 15, 20–23) or **197** (cases 12, 13: on the 193 real STOP frames + 4) | **0**, all 545 frames `CAUTION` |
| **C. sideways, accepted with the wrong orientation** (rolled 90° on its side) | 4–7, 16–19 | no | **`ok`** (one `provisional`) | `STOP` from the first frames, while still `pending` | 190–196 (the 193 real STOP frames + 0–3) | **395–509 of 545 frames STOP**: false |

What it means:

1. **Upright or upside-down mounts are handled:** all 8 adopt the right orientation in one frame. Decisions afterwards
   match the unrotated run on 98–99 % of frames (the mount tilt settles a little differently). The node shows `FAULT` or
   `CAUTION` on the frame before. The one exception is a single `GO` at frame 0 of the upside-down case 1, on both recordings.
2. **The Falcon's native frame (case 12) is not found**, as the Falcon README predicted (`keep_up_axis` keeps only the
   8 vertical candidates). On the empty recording the node stays in `CAUTION` (never a silent `GO`) and the calibration
   goes to `fallback` after 400 frames. On the obstacle recording it still gives `STOP` on the real STOP frames. The real
   Falcon recording does **not** use this frame (17.10: ROS axes, adopted at frame 1). The risk exists only if a driver
   publishes the native frame, and the launch parameters `sensor_forward:=+z sensor_left:=-y sensor_up:=+x` cover it.
3. **New: a lidar rolled 90° on its side can pass the mount check and then STOP almost all the time.** In group C the
   real floor appears to the side and a tunnel wall appears below the sensor. The calibration accepts that wall as the
   track bed (status `ok`; case 4: `ok` from frame 202, height 2.29 m, roll −0.78°, "tilt corrected"). Even before that,
   decisions are not held back while the mount is `pending`: case 4 gives `STOP` from frame 4. On the moving empty
   recording this is **395–509 false STOP frames out of 545**, with the mount reported `ok`. The status is misleading.
   **Corrected 18.10 (after P1's review, re-checked on our saved rows):** it does *not* always fail safe. Case 5 gives
   `GO` on empty-recording frames 311 and 316 (status `ok`, wrong orientation), and on the obstacle recording it turns
   **6 real STOP frames (189–194) into `CAUTION`** (and adds STOP on 5–7). The two fixes suggested here do not work:
   the forward/rear cone test (`calibration.observe_mount`) already runs first and uses `hypot(y, z)`, which a roll
   about the forward axis leaves unchanged; and the configured orientation already counts as confirmed, 327 of case 5's
   509 false STOP frames come after status `ok`. A fix needs other mount evidence (P3). Known side mounts can be set
   explicitly with launch axes; P4 checked that on 1.2.0 ([p1_branch_check](../p1_branch_check_2026-10-18/README.md)).
4. On the obstacle recording the sideways cases that `STOP` do so on about the same 193 frames as the real run (+0–4; the
   STOP *count* hides case 5's 6 lost frames, see 3). That is
   not proof that they see the obstacle: the train stands with the obstacle in view on almost every frame, and the empty
   recording shows group C `STOP`s without any obstacle.

## Files

[analyse_b4.py](analyse_b4.py), `ana_<version>_<recording>.json` (per rotation: expected and adopted orientation,
first correct frame, statuses, decisions before adoption, equality after, STOP counts), [run_b4.sh](run_b4.sh),
`b4_raw.tar.xz` (per-frame records of all 96 runs and the plain runs; SHA-256 in `SHA256SUMS`).

```
RESENSE_REPO=<checkout> PYTHONPATH=<checkout>:<checkout>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
  python scripts/orientation_battery.py run <decoded cache> battery.json
python docs/evidence/judgement_2026-10-13/scripts/probe.py <decoded cache> plain        # the control
python docs/evidence/orientation_2026-10-18/analyse_b4.py battery.json plain.jsonl ana.json
```
