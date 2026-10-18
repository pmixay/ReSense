# B6: how far the gauge is built and how stable it is (experts' criteria 2 and 3) — 18.10

> **Observation only.** No detector code was changed. These are not G3 and not a J1 score. The six
> original bags and Set O are the recordings we developed on; the three synthetic bags are development data.
> Owner: P4. Input for N1 (the gauge display) and K1 / K2 (the axis), as acceptance and baseline numbers.

The experts' criteria (16.10): **2.** "how far the gauge is built"; **3.** "the gauge box does not blink, does not
disappear, does not leave the tracks".

## Method

`scripts/gauge_stability.py` (known-answer tests in `tests/test_gauge_stability.py`, 5 pass):

* **The detector's gauge**: its own track model per frame (centre, heading, curvature, trusted axis range),
  through the judge's node replica, for 1.1.0 (`492e407` tree) and 707ea9c. The **reported range** is the
  node's `monitored` range (health / status / clear distance), from the per-frame records.
* **Truth = the path the train actually drives next.** Frame-to-frame ICP (the judge's open3d settings, full 4x4
  motion) is composed into poses. A frame's future positions, brought into that frame's detector coordinates,
  trace where the track really goes. This needs no labels and is independent of the detector.
* **Metrics** (all on the 10 recordings, both versions):
  * **range**: the trusted axis range and the reported range per frame;
  * **blink / disappear**: frames without a gauge; "blinks" = the trusted range halves in one frame and comes back
    within 10 frames; **flicker** = how far the gauge edge at 40 / 80 / 120 m moves between frames once the
    previous frame's edge is moved by the train's own motion (motion-compensated, so a real heading change is
    not counted);
  * **off the tracks**: the gauge axis lateral against the driven path, by distance; and **honesty**: the share
    of the *reported* range (5 m steps) where the axis is more than 1.05 m (the gauge half-width) off the path.

## Checks of the method (not taken on trust)

| check | result |
|---|---|
| Is the driven path a valid truth? Three independent witnesses on a curve (`roundT_doubleT`, frames 140–170) | walls fitted from the raw points: curvature −0.0023 … −0.0027 /m (residual ≤ 0.03 m); ICP heading per metre: −0.0025 … −0.0026; **they agree** (radius ≈ 400 m). The detector reports −0.0006 … −0.0011 |
| ICP quality per recording | fitness p10 ≥ 0.94 on all ten; 1–4 path segments (breaks only at blocked frames in Set O and `synthetic_tunnels`) |
| Known answers (synthetic) | train on a 400 m circle: exact detector → only the parabola-vs-arc gap (0.30 m at 110 m), straight detector → the circle's offset; heading sway ±0.002 rad: raw edge motion 0.48 m, compensated ≈ 0; breaks start new segments |
| Refactor safety | the shared path code reproduces the first stored result byte for byte |
| 1.1.0 vs 707ea9c identical in the track metrics? | yes, and correctly so: the runs used the two checkouts, and the track model (`resense/track.py`) differs only by 1.1.0's added `wall_drift`, which shortens the **reported** range, not the axis |
| Is the 8–25 m bin a truth check? | **No, corrected 18.10.** On `doubleT_platform` (frames 75–150) the driven path is straight (lateral −0.09 … −0.14 m over 100 m, ICP fit 0.94–0.97). The detector's near heading follows a converging platform wall (wall slope −0.03 … −0.046, detector −0.031 … −0.039). That is a detector error even at 8–25 m, so the bin is reported as a detector metric |
| Recordings without truth | `doubleT_obstacle` (train stands: 0.7 m travelled) and most of `squareT_platform_squareT_switch` (0.09 m/frame) give range, blinks and flicker but few or no off-track rows |

## Result

Off-track = axis lateral error against the driven path (median, within the trusted range). Flicker = motion-compensated
frame-to-frame edge change, 90th percentile. Reported range = the node's `monitored` range.

| recording | trusted axis range p50 | reported range p50, 1.1.0 / v1.0.0 | reported ≥ 100 m, 1.1.0 / v1.0.0 | frames without gauge | blinks | flicker p90 at 40 / 80 / 120 m | off-track p50 at 50 / 90 / 135 m | reported range off > 1.05 m, 1.1.0 / v1.0.0 |
|---|---|---|---|---|---|---|---|---|
| doubleT_obstacle | 151 m | 151 / 151 m | 100 / 100 % | 0 | 0 | 0.01 / 0.04 / 0.09 | – (train stands) | – |
| doubleT_platform | 120 m | 120 / 120 m | 63 / 63 % | 0 | 22 | 0.09 / 0.22 / 0.49 | 0.15 / 0.17 / 0.15 | 8.6 % / 8.6 % |
| roundT_doubleT | 157 m | 142 / 147 m | 83 / 85 % | 0 | 1 | 0.09 / 0.24 / 0.42 | 0.29 / **1.78 / 7.42** | **40.1 % / 41.2 %** |
| roundT_pressureGate_roundT | 143 m | 102 / 130 m | 51 / 93 % | 0 | 5 | 0.04 / 0.15 / 0.38 | 0.07 / 0.31 / 1.58 | **2.2 % / 12.5 %** |
| roundT_squareT_pressureGate_squareT | 175 m | 134 / 157 m | 54 / 64 % | 0 | 1 | 0.04 / 0.17 / 0.39 | 0.07 / 0.15 / 0.28 | 9.3 % / 10.8 % |
| squareT_platform_squareT_switch | 151 m | 138 / 143 m | 84 / 86 % | 0 | 4 | 0.03 / 0.07 / 0.15 | 0.21 / 0.66 / 2.54 | 11.7 % / 12.3 % |
| cloud_with_fake_obj (Set O) | 155 m | 130 / 139 m | 67 / 73 % | 0 | 4 | 0.04 / 0.13 / 0.30 | 0.06 / 0.11 / 0.15 | 1.6 % / 3.0 % |
| synthetic_platform | 120 m | 80 / 84 m | 47 / 49 % | 0 | 5 | 0.04 / 0.08 / 0.21 | **0.73 / 1.46 / 2.58** | **40.4 % / 41.9 %** |
| synthetic_switch | 147 m | 124 / 143 m | 80 / 95 % | 0 | 11 | 0.03 / 0.10 / 0.23 | 0.06 / 0.18 / 0.54 | 3.5 % / 6.2 % |
| synthetic_tunnels | 139 m | 119 / 129 m | 64 / 80 % | 0 | 8 | 0.09 / 0.26 / 0.51 | 0.10 / 0.37 / 2.87 | 13.4 % / 18.4 % |

### What it says

1. **Range (criterion 2):** the detector trusts its axis to a median of 120–175 m. It reports 80–157 m (median per
   recording). 1.1.0 reports less than v1.0.0 on 8 of 10 recordings (equal on the two `doubleT` bags) (up to −28 m median on `roundT_pressureGate_roundT`).
2. **Honesty: 1.1.0's shorter range is the more truthful one.** On every recording where the versions differ, the share of the
   reported range with the axis off the track by more than the gauge half-width falls, for example 12.5 % → 2.2 %
   (`roundT_pressureGate_roundT`), 3.0 % → 1.6 % (Set O), 6.2 % → 3.5 % (`synthetic_switch`), 18.4 % → 13.4 %
   (`synthetic_tunnels`). The `wall_drift` cut of 15.10 ends the range where the axis leaves the track.
3. **The gauge does not follow curves (criterion 3, "leaves the tracks").** On the curve of `roundT_doubleT`
   (radius ≈ 400 m, three-way confirmed) the detector's curvature is 2–4× too small. The axis is off by 1.8 m at 90 m and
   7.4 m at 135 m (median), **inside the range it trusts and reports**: 40 % of the reported range is more than
   1.05 m off on both versions. The curvature limits in the configuration do not explain it (minimum radius 150 m;
   the rate limit only delays by ~25 frames). The wall fit itself returns too little bend. For P3 (K1 / K2).
4. **Platforms (criterion 3):** where no wall runs parallel to the track, the heading follows a converging wall
   (`doubleT_platform`, 2.3° at 8–25 m) or the axis drifts (`synthetic_platform`: 0.7 m off at 50 m, 40 % of the
   reported range more than 1.05 m off). The same scenes give the 45 m axis floor of A5.
5. **Blinking (criterion 3):** no frame is ever without a gauge. The trusted range "blinks" (halves and comes back
   within 1 s) 0–22 times per recording, most on `doubleT_platform` (22 in 345 frames).
6. **Flicker vs the N1 target.** On Set O the edge moves 0.04 / 0.13 / 0.30 m (p90) at 40 / 80 / 120 m per frame,
   motion-compensated. N1's proposed acceptance for the **displayed** edge is ≤ 0.05 / 0.08 / 0.15 m. So the display
   smoothing of N1 is needed at 80 and 120 m. 40 m already meets it. The raw (uncompensated) values are in the JSONs
   (`jitter`) for comparison with N1's wording.
7. **1.1.0 = v1.0.0 for the axis itself.** All track metrics are identical; only the reported range differs (item 2).

## Files

`<version>/measure_<recording>.json` (range, blinks, raw and compensated flicker, off-track by bin within and beyond
the trusted range), `<version>/honesty_<recording>.json` (the reported-range check), `monitored.json` (the reported
range per frame), [run_b6.sh](run_b6.sh), `b6_raw.tar.xz` (ICP poses and per-frame track models of all runs;
SHA-256 in `SHA256SUMS`). Per-frame node records: J1 dry-run folders and the synthetic runs (already archived).

## Reproduce

```
RESENSE_REPO=<checkout> PYTHONPATH=<checkout>:<checkout>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python scripts/gauge_stability.py poses   <decoded cache> poses.json        # once per recording
python scripts/gauge_stability.py track   <decoded cache> track.json        # per checkout
python scripts/gauge_stability.py measure track.json poses.json measure.json
python scripts/gauge_stability.py honesty track.json poses.json <node run .jsonl> honesty.json
```
