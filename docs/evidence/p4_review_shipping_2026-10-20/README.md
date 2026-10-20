# P4 review of what ships on in 1.2.0 (`4cf8e27`): L16/S3, the Falcon range model, F1a, H′, R3 (20.10)

> **Purpose:** the independent P4 review of every change that ships **on** in the final commit, asked for in
> [`integration_2026-10-19/README.md`](../integration_2026-10-19/README.md) §4. **Owner:** P4 · **Status:** done
> (two reviewers on synthetic scenes; every finding marked confirmed was re-run here) · **Detector code:** not
> touched; fixes are proposed for P3, not applied. Every run here is on synthetic scenes: the bags are not reachable
> from this container.

## Result in short

| # | change (on in 1.2.0) | finding | effect | checked here |
|---|---|---|---|---|
| A1 | L16/S3 | a full-revolution Pandar starting in open air locks −Z as "forward": FAULT for the whole run, no tilt calibration | false FAULT, no missed obstacle | confirmed: 450 / 450 FAULT vs 450 / 450 GO on `aec88d2` |
| B1 | F1a | a low object whose top is 0–0.08 m into the gauge is made weak where the model's rail-head plane runs ≥ 0.11 m below the rails (seen on the ride) | **missed genuine obstacle** | confirmed: 8 STOP frames → 0 at 40 m; flat-track control identical |
| B2 | R3 | the fast confirmation starts a STOP before the ego-motion veto has its 4 hits, so a thin target carried along with the train STOPs | false STOP | confirmed at 37 m for both kinds (0 → 16–17 STOP frames) |
| B3 | R3 | the tall-cable shortcut never fires on accumulated clusters (speed known, beyond 40 m) | improvement lost, not worse than before | reviewer only |
| B4 | H′ | demotes a real object only with a mount-height error of ≥ 0.8 m at 5 m (≥ 1.6 m at 20 m) | robustness | reviewer only |
| A2 | Falcon constants | raster constants inconsistent with their sources | none (cosmetic) | arithmetic checked |

Each confirmed finding has a proposed minimal fix for P3 below. None is measured on the recordings.

**Current `main` (re-run 20.10 after H1 and PR #43 were merged, `8c2bf51`, H1's `column_core_margin` 0.02 on; the
detector imported from that worktree):** the same commands as in "Reproduce" give the same results. A1: the cue is
(0, 0, −1) at 0.2 % and 1 % above and none at 3 % and 10 %; FAULT in 450 / 450 frames in open air, GO in 450 / 450 in
the tunnel. B1: every row is the same, 8 STOP frames → 0 with the rails 0.18 / 0.20 m high, the flat-track control
equal. B2: at 37 m, STOP frames 2–17 (tall) and 1–17 (hanging) with R3, none without; the 30 m rows as tabulated.
H1 does not change these findings; their exposure on the recordings is still unmeasured.

## A. L16/S3 calibration and the Falcon range model

### A1. A correct full-revolution Pandar that starts in open air is FAULT for the whole run (confirmed)

`resense/calibration.py:297-303` (`directional_axes`) takes the only axis with more than 98 % same-sign returns as
**signed forward**, without checking that the returns form a forward cone. The dataset's full-revolution Pandar
(`doubleT_obstacle`: valid returns −104° … +106°, [`DATASET.md`](../../DATASET.md) line 160) has ~14 % of its returns
behind the sensor, so X is not one-sided. In open air almost every return is below the sensor, so **−Z** is the only
one-sided axis and becomes "forward". The cue is computed once (`:568-569`, never reset), the configured mapping then
fails `axis_ok` on every frame (`:580`), `orientation_conflict` stays set, health is error (`health.py:211`) and the
decision FAULT. No candidate can have forward −Z with up ±Z, so the search cannot recover, and the tilt is never
calibrated (status `fallback`, message "no rail pair in 400 frames").

| check | method | result |
|---|---|---|
| the cue | [`cue_synthetic.py`](scripts/cue_synthetic.py) (written here): ground plane 1.9 m below the sensor, azimuth −104…+106°, a share of returns above the sensor | 0.2 % and 1 % above: forward **(0, 0, −1)**; 3 % and 10 % above: no cue. Control, forward-only ±50° with 10 % above: forward +X, up +Z |
| the whole detector | [`fault_open_air.py`](scripts/fault_open_air.py) (reviewer's analytic ray-cast scene [`scene.py`](scripts/scene.py): bed, rails, ground, masts; 0.18 % of returns above the sensor), 450 frames, re-run here | `4cf8e27`: **FAULT in 450 / 450**, never confirmed. `aec88d2` (before L16/S3), same scene: GO in 450 / 450, mapping confirmed |
| control | the same mount starting in a tunnel (32 % above) | GO in 450 / 450 on both commits |
| real recordings | the gate on the merge (`b2c523a`) equals `aec88d2` per frame ([P4 identity review](../p4_review_integration_2026-10-20/README.md)) | it did not fire on the six Pandar recordings or the ride; how often a real open-air start has < 2 % of returns above the sensor is **not measured** |

Severity: no obstacle is missed (a person at 40 m still gives STOP, which outranks FAULT, per the reviewer), but the
whole run is FAULT and the tilt is uncorrected. A jury bag that starts in open air with the full-revolution scan would
show it.

**Proposed fix (P3):** accept a one-sided axis as forward only when the returns lie in a cone around it (98th
percentile of the angle from the axis below 80°), and/or do not lock the cue on the first frame.
[`cone_fix_check.py`](scripts/cone_fix_check.py), re-run here: the project's 24-rotation fixture keeps forward in
24 / 24; the ±50° Pandar keeps +X; the 210° and 360° open-air clouds give no cue. Before the reseal, where the data
is: the share of returns above the sensor in the first frame of every recording.

### A2. Cosmetic: the Falcon raster constants (`resense/sensor.py:77-78`)

- `FALCON_ROI_STEP_DEG = (0.088, 0.06)`: the comment's own "60 lines over −3.98…+0.72°" is 0.080° per line, and
  [`raster_validation.json`](../falcon_long_range_2026-10-19/raster_validation.json) says "ROI line spacing ~0.06–0.1
  deg". Nothing calls it with `roi=True`, so it changes no output.
- `FALCON_FOV_STEP_DEG = (0.18, 0.235)`: the measured azimuth step is 0.176°, and no committed measurement gives
  0.235° in elevation. The product is within 0.1 % of 0.176 × 0.24, so the small-target limit is unaffected.
- Reported by the reviewer, not run here: on FAULT frames `detector_node.py:1227` publishes `monitored_small` as None
  for the Falcon (0.0 only for `pandar128`).

### A3. Checked and sound

| item | how | result |
|---|---|---|
| Falcon small-target limit 48.2 m | closed form 0.3 × 0.3 m at 0.18° × 0.235° vs `small_target_limit("falcon_prime")` | both 48.25 m, 3.00 expected returns. The reviewer's Monte Carlo over grid phase: the mean matches, but at 48.2 m only 51 % of phases give ≥ 3 returns (≥ 3 on every phase to ~36 m); the Pandar prior (88.8 m) is built the same way |
| `directional_axes` on correct forward-only installs | reviewer: 300 cases (Falcon-like raster, ±50° Pandar; tunnel and open air; roll / pitch ±15°, yaw ±20°) | 0 wrong forward or up |
| S3 sampling | reviewer: 12 recovery cases (yaw 90°, upside-down, yaw 180°; ring- and column-major order; 128k and 451k points) | the sampled winner equals the full-cloud winner in 12 / 12 |
| edge cases | reviewer: empty, 1 point, NaN, inf, identical, single octant, all within 1 m | no exception, no cue, no ok observation |
| `falcon_native` profile | determinant of the axis mapping | +1 (a proper rotation) |

Not checked: real open-air clouds; the Falcon line spacing at the edges of the field of view; numpy 1.26 (this
container has 2.x).

## B. F1a, H′ and R3

### B1. F1a can drop a genuine low obstacle inside the gauge (confirmed)

A plain low cluster is built only from returns below the envelope floor, 0.12 m above the **model's** rail-head plane
(`resense/lowobj.py:188`, `h < h_bottom`), so its `height_max` is always below 0.12. F1a (`lowobj.py:333`) compares
that capped top with the frame's own rail line + 0.01 m. Wherever the line reads ≥ 0.11 m above the model's plane,
every plain low cluster becomes weak, whatever the object's real height. The object's part above the floor forms an
ordinary cluster, which the corridor stage drops as track hardware when it is small (`clustering.py:357`: top under
0.35 m, narrower than 0.4 m, shorter than 0.3 m). The condition occurs on the ride: at frame 5709 (43.4 m) the rails'
lines read 0.063 and 0.173 m above the model's plane ([F1 `HANDOFF.md`](../f1_false_alarms_2026-10-19/HANDOFF.md)
line 52), so a cluster at the centre gets a reference of about 0.12 m.

[`f1a_ab.py`](scripts/f1a_ab.py) (reviewer's scene [`f1a_capped_top.py`](scripts/f1a_capped_top.py) on the numpy
ray-cast tunnel [`raycast.py`](scripts/raycast.py)): the rail heads stand 0.18 / 0.20 m higher over 32–70 m, so the
model's rail head is 0.16–0.19 m low at 40 m; a 0.30 × 0.30 m box stands on the bed on the axis at 40 m; 12 frames of a
standing train. Re-run here on `4cf8e27` (pure Python):

| rails | box top above the true rail head | F1a off | F1a on (shipped) |
|---|---|---|---|
| level (control) | 0.12–0.30 m, or no box | 8 STOP frames on the box (none without a box) | identical |
| +0.18 / +0.20 m | 0.12–0.17 m (and 0.20 m at +0.18) | **8 STOP frames, kind `low`** | **0** |
| +0.18 / +0.20 m | ≥ 0.25 m (≥ 0.20 m at +0.20) | 8 (ordinary cluster) | 8 |

The reviewer also ran an approach at 8 m/s from 58 m: F1a off STOPs from 50 m (27 frames), F1a on not down to 27 m
(not re-run here).

**Proposed fix (P3):** take the top over the cluster's own footprint including this frame's returns above the floor
(h < `foot_max_top`), as `mark_rail_line` already does. The reviewer's patched copy brings the box back (8 / 8), keeps
the repo's F1a tests identical and still rejects the rail fragment; its effect on the ride's false STOPs is **not
measured**.

### B2. R3 starts a STOP the ego-motion veto would have held (confirmed)

The veto (`tracking.py:458-461`, `ego_veto_min_speed` 4 m/s) holds a track advisory while it is carried along with the
train, but only before the STOP is earned, and it needs 4 hits and 4 m of travel to decide. R3's fast path
(`tracking.py:941-951`) confirms a tall cable at 3 hits / 0.3 s and a hanging one at 2 hits / 0.2 s, so the STOP is
earned before the veto can act. [`r3_veto.py`](scripts/r3_veto.py): a thin vertical target held at a constant
distance while the train moves at 15 m/s with the speed given; re-run here:

| target | R3 on | R3 off | veto |
|---|---|---|---|
| tall, 37 m | STOP frames 2–17 | **none** | "carried along" from frame 3 |
| hanging, 37 m | STOP frames 1–17 | **none** | same |
| hanging, 30 m | STOP frames 1–14 | none | same |
| tall, 30 m | STOP frames 2–14 | STOP frames 4–14 | same (the veto does not hold it without R3 either) |
| control: static, approached | STOP 2–3 frames earlier with R3 | STOP | — |

How often a thin target moves with the train on real data is unknown; the R3 evidence shows no STOP added on the ride.
**Proposed fix (P3):** beyond `ego_veto_min_distance`, do not let the fast path start a STOP while the veto still
lacks its hits, or keep a fast-started STOP open to the veto until it has them.

### B3. R3's tall-cable shortcut is inert on accumulated clusters (reviewer only)

With the speed known, accumulation runs beyond 40 m and the cable's cluster carries points of earlier frames; the
shortcut requires current-frame points only (`tracking.py:924`, `n_raw != len(points_idx)`), so `cable_kind` stays 0.
Reviewer's scene, cable approached at 10 m/s from 80 m: speed unknown, first STOP 78.0 m with R3 vs 76.0 m without;
speed given, 76.0 m in both. An improvement lost, not a regression. Fix: test the shape on the current-frame points.

### B4. H′ is safe unless the mount height is far off (reviewer only)

By direct calls of `Detector._mount_cross_check` (`detector.py:950-976`): an object hanging 0.3 m into the envelope is
demoted (and, being in `_NOT_ESCALATED`, never escalated) only with a calibrated-height error of ≥ 0.8 m at 5 m,
1.0 m at 10 m, 1.6 m at 20 m; a standing person never. With the mount right and the model 1.5 m high nothing real is
demoted; the repo's test still demotes the Falcon tunnel ceiling (positive control).

### B5. Checked and sound (reviewer)

- R3's counters reset on a miss, on any other continuation source and on an ineligible hit; time is in seconds from
  the measured interval (repo tests and a frame trace).
- The `not bent` guards in `gauge.py` / `health.py`: with the native library built, the guarded paths equal the bent
  axis exactly; the unguarded native path is 7.8 m off (positive control).
- Accepted review issue B1 of the F1 lane (pieces of a long low object along a rail raise their own reference) is
  still present with the shipped settings: the repo test shows all 6 pieces made weak.
- A traced F1a run equals the plain run; 184 tests passed in the relevant files (41 skipped: `open3d`).

Not checked in part B: anything on the recordings (ride, Falcon, gate); the fixes' effect on the ride's false STOPs;
the `open3d` synthetic tests.

## Reproduce

```
S=docs/evidence/p4_review_shipping_2026-10-20/scripts; W=<worktree of 4cf8e27>; B=<worktree of aec88d2>
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python -I $S/cue_synthetic.py $W                                    # A1, the cue
PYTHONPATH=$W python $S/fault_open_air.py $W                        # A1, 450 frames (and PYTHONPATH=$B ... $B)
PYTHONPATH=$W python $S/cone_fix_check.py                           # A1, the proposed fix
cd $S && PYTHONPATH=$W:. python f1a_ab.py                           # B1
cd $S && PYTHONPATH=$W:. python r3_veto.py                          # B2 at 30 m; at 37 m:
cd $S && PYTHONPATH=$W:. python -c "from r3_veto import run; [print(k, r3, [r[0] for r in run(15.0, 37.0, True, r3, n=18, kind=k) if r[2] == 'STOP']) for k in ('tall', 'hanging') for r3 in (True, False)]"
```
