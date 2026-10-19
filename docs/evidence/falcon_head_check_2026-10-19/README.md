# Falcon Prime check of `main` `aec88d2` (merged 1.2.0 candidate) — 19.10

> **Owner:** P1 (captain's check, agent-executed). **Observation only:** no detector code changed. Development data,
> not G3 and not a J1 score. Purpose: answer "were the new lidar's documents and data processed, does
> auto-calibration work, how good is the system on the new lidar, can it reach 300 m", and re-check the evidence
> behind the jury's gauge comments, without trusting earlier reports.

## What was run

* **Source:** `aec88d2` (merge of PR #38), exported with `git archive`; `scripts/detector_freeze.py verify` PASS in
  the repository and in the export (38 files, source digest `68dee667…`). Native kernels built with the
  `scripts/build_native.sh` flags. Python 3.12.3, numpy 1.26.4, scipy 1.11.4, scikit-learn 1.4.2,
  `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, 4 shared vCPU (timings are not benchmarks).
* **Data:** the organizers' links checked live on 19.10 ([listing](out/yandex_listing_2026-10-19.txt)):
  `falcon_test.zst` SHA-256 `90dea27d…` is the file N2/B2 measured; `new_synth_data.zst`, Set O and the ride are
  unchanged; nothing was added after 16.10 (no dust data).
* **Replay:** the whole recording streamed once with the unchanged `scripts/stream_falcon.py` through
  [`falcon_dual_stream.py`](scripts/falcon_dual_stream.py), which feeds every message to two judge node replicas
  (`judge_runner.NodeReplica`): the **default launch** (configured Pandar axes + `auto_calibrate`) and the
  **explicit `falcon_ros` axes**. It also records uncropped range histograms and dumps 139 raw frames
  ([list](out/dump_frames.txt)) for geometry checks. 4,443 / 4,443 messages, 0 lost, 20,281,548,800 bytes; first and last
  stamps equal the committed B2 run ([meta](out/stream_meta.json)).

## Controls (CLAUDE.md)

| check | result |
|---|---|
| Instrumentation: wrapper output vs the plain `stream_falcon.py` on the same 300-frame prefix | every field equal except `level` on frames 10–21, the wall-clock line "latency p95 102–103 ms over the 100 ms budget" (two detectors in one process); decisions equal ([controls](out/controls.txt)) |
| `aec88d2` vs the committed 1.1.0 B2 run (`falcon_full_2026-10-18`) | all **4,443 decisions** and every non-timing field equal; only 2 frames differ in the same latency line. The B4 calibration change did not alter the Falcon run, although no whole-Falcon run had been claimed for it |
| Orientation probe control | the identity mount reproduces the main run's decisions on frames 0–9 |
| Datasheet model vs real returns | predicts 6.2 returns on a person at 250 m in the ROI; the reviewed person has 5–8 at 240–248 m |
| N1 jitter | 12 / 12 published visible-edge numbers reproduced by an own formula from the stored rows |
| B6 curve finding | reproduced with a different method (parabola fit of the driven path per frame) |
| Test suite on the export | 1,969 passed, 8 deselected (external caches), 0 failed after installing the missing `open3d`; the first run's 26 failures were all missing `open3d` / package import ([tests](out/tests.txt)) |

## Results

**Decisions** ([analysis](out/analysis.txt)):

| run | GO | CAUTION | STOP | FAULT |
|---|---:|---:|---:|---:|
| default launch | 8 | 3,062 (68.9 %) | 1,372 | 1 |
| explicit `falcon_ros` axes | 13 | 3,043 | 1,387 | 0 |

**Auto-calibration.** Frame 0 runs on the configured Pandar mapping (FAULT); frame 1 adopts sensor
+x → forward, +y → left, +z → up (checked on the dumped rotation matrices). The tilt stays `pending` for 192 frames
(~19 s), then pitch −2.39°, height 1.77 m above the rail head, lateral 0.77 m. An independent bed-plane RANSAC on
19 raw frames ([floor fit](out/floor_fit.txt)) gives pitch **−2.37°**, roll 0.16° (below the detector's apply
threshold), bed 1.98 m below the sensor (rail head ≈ 0.21 m above the bed).

**Other axis conventions** on 10 real frames ([probe](out/orient_probe.txt)): yaw 90 / 180 / 270, upside-down and
upside-down + yaw 90 are recovered by frame 1 (yaw 270 is the configured mapping itself). The manufacturer's native
frame (x up) is never confirmed by the default launch (CAUTION on every frame, no silent GO) and works with the
explicit `falcon_native` axes. A 90° roll is adopted as a wrong orientation and gives STOP on frames 5–9 of an empty
tunnel: limitation L16, unchanged for ring-free sensors.

**The walking person** (team's raw-cloud review `n2_falcon_2026-10-18/raw_person_review/atlas_proposals.json`,
matched by distance ±max(4 m, 3 %)):

| | default launch | explicit axes |
|---|---|---|
| first matched warning | frame 2713, person at 155.8 m | same |
| first matched STOP | frame 2972, **124.8 m** | frame 2950, **127.2 m** |
| STOP after the first STOP, person at 100–130 m | 282 / 326 frames | 294 / 348 |
| person at 60–100 m / 20–60 m | 648 / 648, 320 / 320 | same |
| person at 0–20 m (near blind zone) | 110 / 135 | 117 / 135 |

The raw cloud shows the person from ~249 m (5–8 returns per frame at 240–248 m, 7 at 200–240 m, 14 at 150–200 m,
26 at 120–150 m). While the person is at 128–155 m the detector reports them at lateral −1.2…−1.36 m, outside the
1.05 m half-width, and the first STOP comes as the lateral reaches −0.9 m ([trace](out/caution_stability.txt));
whether the person was really outside the gauge is unknown (no gauge truth).

**False STOPs:** 12 frames not matched to the person: 4 on the static structure at 110–120 m, 8 below 10 m at the
end (the floor patch of B2). **CAUTION:** 2,114 frames carry only the two static gauge-edge warnings (105.6 m,
115 m); in the first 2,000 frames (no person) the output is CAUTION 99.5 % of the time.

**Gauge range on the Falcon:** trusted axis range median 123 m (p10–p90 107–167 m); it changes by ≥ 20 m between
consecutive frames in 34.3 % of frames (p90 48 m). The N1 display was not measured on the Falcon.

**What the sensor returns, by range** (empty frames 100–1,500, [range profile](out/range_profile.txt)):

| range | corridor returns / frame (\|y\| < 3 m) | of them near the bed | outside the corridor |
|---|---:|---:|---:|
| 50–100 m | 2,239 | 177 | 2,526 |
| 100–150 m | 331 | 9.6 | 200 |
| 150–200 m | 59 | 0 | 29 |
| 200–250 m | 26 | 0.1 | 6.6 |
| 250–300 m | 8.4 | 0.6 | 2.8 |
| 300–400 m | 0.1 | 0 | 4.4 |

All returns beyond 250 m lie within ±2.4° azimuth and −2.8…−1.1° elevation and are bright (intensity p90 128
against 22 overall): a straight tunnel with bright far objects up to 510 m, but **no bed or rail return beyond about
150 m**. The gauge can only be extrapolated there; the detector's code crops at 250 m (`sensor.max_range`).

**Datasheet model** ([model](out/datasheet_model.txt)): a person-size target gives ~4.3 returns per frame at 300 m
in the ROI and ~0.7 outside it; a 1 m box 5.1 / 0.8. Square-root reflectivity scaling (a heuristic) puts the
90 %-detection range at ~354 m for 20 % reflectivity and ~177 m for 5 %.

**Curves (jury: gauge out of sync with turns)** ([curve check](out/curve_check.txt)): on `roundT_doubleT`
frames 140–170 the driven path curves at −0.00248 /m (R ≈ 403 m), the detector's axis at −0.00070 /m (3.6× too
straight); lateral gap 0.04 / 0.64 / 1.63 m at 30 / 45 / 60 m; the trusted range there is 60 m. 1.1.0 and v1.0.0
are identical.

## What this does not show

No ROS node, Docker, DDS or RViz run (the replica models the node's decode and decision rule; the clear range here
is the legacy policy, not the conservative Falcon one). The person's identity and trajectory are the team's
review, not organizer truth; gauge membership is unknown. Nothing in the recording stands beyond 249 m, so no
detection at 300 m can be measured on it. Raw frame dumps (160 MB) are not committed: rerun with
`FALCON_DUMP=$(cat out/dump_frames.txt)`.

## Reproduce

```bash
export RESENSE_REPO=<checkout> PYTHONPATH=<checkout>:<checkout>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
FALCON_DUMP=$(cat out/dump_frames.txt) python scripts/falcon_dual_stream.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out <dir>/head
python scripts/analyze_falcon.py <dir>/head ../n2_falcon_2026-10-18/raw_person_review/atlas_proposals.json
python scripts/floor_fit.py <dir>;  python scripts/range_profile.py <dir>;  python scripts/orient_probe.py <dir> <dir>/head.jsonl
python scripts/caution_stability.py <dir>/head ../n2_falcon_2026-10-18/raw_person_review/atlas_proposals.json
python scripts/curve_check.py <unpacked gauge_stability_2026-10-18/b6_raw.tar.xz> roundT_doubleT v110 140 170 60
python scripts/n1_jitter_recompute.py ../n1_n4_2026-10-18/final_core_f5ff15f/rows
python scripts/datasheet_model.py
```

Per-frame records: [`out/head.jsonl.xz`](out/head.jsonl.xz) (default launch), [`out/head_ros.jsonl.xz`](out/head_ros.jsonl.xz)
(explicit axes, with the mount dict), [`out/head_extra.jsonl.xz`](out/head_extra.jsonl.xz) (mount, `axis_valid`, range
histograms), [`out/plain_prefix300.jsonl.xz`](out/plain_prefix300.jsonl.xz) (plain-tool control). SHA-256 in
[`SHA256SUMS`](SHA256SUMS).
