# P4 review of what ships on in 1.2.0 (`4cf8e27`): L16/S3, the Falcon range model, F1a, H′, R3 (20.10)

> **Purpose:** the independent P4 review of every change that ships **on** in the final commit, asked for in
> [`integration_2026-10-19/README.md`](../integration_2026-10-19/README.md) §4. **Owner:** P4 · **Status:** in
> progress (part A, calibration and the Falcon model, is done; part B, F1a / H′ / R3, follows) · **Detector code:** not
> touched; fixes are proposed for P3, not applied. Every run here is on synthetic scenes: the bags are not reachable
> from this container.

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

In progress.
