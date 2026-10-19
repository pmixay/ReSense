# Extended dataset of 16.10: intake, characterization, sealed 1.1.0 observation

**19.10 correction: the synthetic bags do contain dust.** The organizers said so on 19.10, and their marked copies
of the same bags locate it: 11 bursts of 1–4 boxes of 3–6 cm, 1–14 points each, for one or two frames, 3.4–7.2 m
ahead (platform frames 21, 27, 35–36; switch 481, 483, 611, 613; tunnels 70, 166–167, 195, 446). The searches below
looked for a volume of dust and could not see it. Finding 1 ("no dust or suspension") and row 7 of the risk table are
wrong. See [`../synth_markers_2026-10-19/`](../synth_markers_2026-10-19/README.md).

**18.10 correction to the historical partial observation below:** the complete verified Falcon decode now
covers all 4,443 frames. Its valid `is_2nd_return` flags show a median 2,005 second-return points per frame;
the earlier blanket "single return" description is superseded. Raw maximum range is 509.97 m. The original
partial replay measurements below remain historical results. See the
[complete characterization](../n2_falcon_2026-10-18/characterization_summary.json) and its source/cache receipts.

> **Owner:** P4 · **Date:** 2026-10-17 · **Audience:** P1, P3, P4 · **Status:** observation only
> **Data:** `new_synth_data.zst` (three synthetic bags) and `falcon_test.zst` (real recording from the second lidar,
> Seyond / Innovusion Falcon Prime), from the organizers' folder [SfBeRHbs8bNJAQ](https://disk.yandex.ru/d/SfBeRHbs8bNJAQ)
> ([intake note](../../organizers/extended_dataset_2026-10-16.md)).
> **Detector:** the sealed 1.1.0 checkout, run through the judge's node-faithful runner
> (`../rejudge_2026-10-16/scripts/judge_runner.py`, unmodified, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`).
> No detector, config, label or judge-script change was made. Machine-readable facts: [`inventory.json`](inventory.json).
>
> **These runs are observations.** If anyone tunes on this data, it becomes development data. It is **not** the
> registered G3 held-out set, and G3 was not touched.
>
> **Measured vs inferred:** a number in a table is measured unless it is marked *(inferred)*. Inferred means a
> reading of measured data that another explanation could also fit.

## 1. Summary

| | `synthetic_platform` | `synthetic_switch` | `synthetic_tunnels` | `falcon_test_second_dark` |
|---|---|---|---|---|
| what | Pandar128 ride + inserted objects | same | same | real, second lidar |
| frames / duration | 386 / 38.5 s | 736 / 73.5 s | 545 / 54.4 s | 4,443 / 444.3 s (1,859 analysed) |
| topic, `frame_id` | `/lidar_points`, `hesai_lidar` | same | same | **`/iv_points`, `seyond`** |
| fields | x y z intensity ring timestamp (26 B), as the original six bags | same | same | **x y z timestamp intensity flags elongation scan_id scan_idx is_2nd_return (48 B), no `ring`** |
| axes (forward / left / up) | −y / +x / +z | same | same | **+x / +y / +z** |
| background | Set O frames 1195–1509 + 71 later frames (exact match) | the same ride, not on our disk *(inferred)* | the same ride, not on our disk *(inferred)* | standing train in a dark tunnel |
| inserted objects | 3 (one person-shaped) | ≥ 5 | ≥ 3 | none (real data); one moving object, a person walking *(inferred)* |
| dust / suspension | **none** (exact diff, frames 0–314) | not found *(heuristic)* | not found *(heuristic)* | – |
| 1.1.0 STOP / CAUTION / GO / FAULT | 185 / 135 / 66 / 0 | 142 / 294 / 300 / 0 | 126 / 223 / 196 / 0 | prefix 1 / 975 / 8 / 1; window 296 / 569 / 8 / 1 |
| false STOP episodes | 0 | 1 (8 frames) + 2 short mixed ones | 2 (3 frames + 1 frame) | 1 frame (prefix); 4 short episodes at the same static object (window) |

Headline findings:

1. **No dust or suspension in this delivery.** The experts announced it, but none of the three bags contains a volume of
   added returns. In `synthetic_platform`, where we have the real reference, every added point belongs to a compact
   object (at most 6 unclustered points per frame). In the other two bags no such cloud was found. That check is a
   heuristic, because those two bags have no reference. **N3 cannot be measured on the organizers' data yet.**
2. **The new synthetic data uses a different insertion convention.** Inserted points sit **in place** in the organized
   1-D grid: they have consistent `ring` and per-point `timestamp` values, and the real returns they hide are removed.
   Set O instead appended a block after the last no-return zero. **`scripts/label_fake_objects.py` does not apply.**
   Two things still mark the inserted points: their intensity is exactly 1 (99.97 % of the 108,632 points added beyond 3 m in
   `synthetic_platform` frames 0–314), and a reference recording shows the difference.
3. **The 1.1.0 calibration copes with the Falcon's axes.** Frame 0 is `FAULT` ("view blocked"). The orientation search
   then adopts sensor forward = +x, left = +y, up = +z from frame 1, and the mount is `ok` at frame 192 (height
   1.77 m, pitch −2.39°, lateral 0.77 m). The node decoder reads the 48-byte layout through its generic path with no
   error. The cloud has no `ring`, so the runner, like the node, passes `ring=None`.
4. **On the Falcon, 1.1.0 is in `CAUTION` 65–99 % of the time, on a standing train in an empty-looking tunnel.** Two
   static warnings sit at 105.6 m (lateral +1.3 m) and 115.0 m (lateral +1.0 m), at the gauge edge. One of them also
   gives short `STOP`s at ~115 m. This is what the jury will see first when they play the Falcon bag.
5. **The synthetic person in `synthetic_platform` reaches `STOP` only at 44 m.** It is in the data from 200.9 m and is
   tracked as `CAUTION` from ~166 m. During that approach the health `monitored_range` stays capped at 45 m (118
   frames, station platform). This matters because the experts score the first-detect range.

## 2. Identity and hashes

| archive | bytes | SHA-256 (streamed, = Yandex API value) | modified (UTC) |
|---|---:|---|---|
| `new_synth_data.zst` | 2,532,818,915 | `e09336cb939e6b5a6fdb35ccacce59f3808d875a4084142a02cbd1cf88a26bc7` | 2026-10-16 18:43 |
| `falcon_test.zst` | 6,758,209,772 | `90dea27d8636bcb2e5cdddf9bc15add3eae0e05196c2b3de959482da7e505611` | 2026-10-16 14:41 |
| `cloud_with_fake_obj.zst` (re-listed, not downloaded) | 1,746,145,824 | `d41c2fb2…` (API; = our 24.09 intake) | 2026-09-24 |
| `new_data.zst` (re-listed, not downloaded) | 17,078,961,996 | `8124b627…` (API) | 2026-09-17 |

Both new archives were hashed while streaming. Each digest equals the `sha256` that the Yandex public API reports.
The MD5 values from the API are in `inventory.json`.

## 3. Inventory

| member | bytes |
|---|---:|
| `synthetic_platform_cloud_only/synthetic_platform_cloud_only_0.db3` (+ `metadata.yaml` 1,031) | 3,085,340,672 |
| `synthetic_switch_cloud_only/synthetic_switch_cloud_only_0.db3` (+ `metadata.yaml` 1,027) | 5,882,982,400 |
| `synthetic_tunnels_cloud_only/synthetic_tunnels_cloud_only_0.db3` (+ `metadata.yaml` 1,029) | 4,355,866,624 |
| `falcon_test_second_dark/metadata.yaml` | 5,111 |
| `falcon_test_second_dark/falcon_test_second_dark_0.db3` (one split) | **20,281,548,800** |

The archives contain no ground-truth or label file. All bags are rosbag2 v5, sqlite3, uncompressed. The synthetic
bags each have one topic, QoS reliable / volatile, depth 10. Their bag receive times are 2026-10-16 14:25–14:30 UTC:
they were written the day before by playing and recording.

| bag | start (bag time, UTC) | duration | messages |
|---|---|---:|---|
| synthetic_platform | 2026-10-16 14:25:49 | 38.52 s | 386 `/lidar_points` |
| synthetic_switch | 2026-10-16 14:27:38 | 73.48 s | 736 `/lidar_points` |
| synthetic_tunnels | 2026-10-16 14:29:22 | 54.39 s | 545 `/lidar_points` |
| falcon_test_second_dark | 2026-10-09 ~11:14 | 444.29 s | 4,443 `/iv_points`, 215 `/rosout`; `/parameter_events`, `/initialpose`, `/goal_pose`, `/clicked_point`, `/events/write_split` declared, 0 messages |

**How the 20.3 GB Falcon split was read** (disk limit). Two parts were analysed:

* **prefix**: the first 4.5 GB, streamed out of the archive. Its readable rows (985 frames, t = 0–98.4 s) were copied
  into a valid bag with `scripts/prefix_bag.py`. The truncated file's header still declares the full page count, and
  sqlite rejects such a file unless `writable_schema` is on.
* **window**: bytes 11.0–15.0 GB. 874 complete messages (t = 241.2–328.5 s, no gap > 1 s after sorting) were
  recovered from the sqlite overflow chains with `scripts/window_bag.py`. On a test file its output is byte-identical
  to sqlite's own read.

t = 98–241 s and 329–444 s were not seen here; they are read in [B2](../falcon_full_2026-10-18/README.md) (18.10).

## 4. Characterization

### 4.1 PointCloud2 layout

| | synthetic (all three) | Pandar128 originals / Set O | Falcon |
|---|---|---|---|
| fields (offset, type) | x 0 f32, y 4 f32, z 8 f32, intensity 12 f32, ring 16 u16, timestamp 18 f64 | the same; Set O has no `ring` | x 0 f32, y 4 f32, z 8 f32, timestamp 16 f64, intensity 24 f32, flags 28 u8, elongation 29 u8, scan_id 30 u16, scan_idx 32 u16, is_2nd_return 34 u8 |
| point_step / height / is_dense | 26 / 1 / false | 26 / 1 / false | **48** / 1 / **true** |
| slots per frame (`width`) | 307,200 (one frame per bag: 242,688–271,872) | 307,200 | 94,366–95,386 (varies) |
| valid points per frame (min / median / max) | platform 157k / 164k / 190k; switch 143k / 189k / 193k; tunnels 159k / 190k / 272k | ~185k (120°) | 94.5k / 95.0k / 95.3k (every slot valid) |
| no-return slots | zeros kept (~45 %) | zeros kept | none (dense) |
| ring-like channel | `ring` 0–127, 128 values | 128 (absent in Set O) | **none**; `scan_id` 0–37 is a scan line of the polygon pattern spanning several degrees of elevation (scan_id 10: −4.0…+2.7°), not a fixed-elevation ring; `scan_idx` 0–1272 |
| returns | dual: 49 % of points are exact duplicates (≈ 97 % in identical pairs) | the same | **single**: 94,847 distinct xyz of 94,848; ~2 % flagged `is_2nd_return`, never a duplicate |
| intensity | 0–255, median 4–11 | 0–255, median 6–7 | 0–215, median 10, p99 93–96 |
| per-point timestamp | f64, epoch-2000 clock, ~32 ms per frame | the same | f64, sensor clock, ~95 ms per frame |
| header stamp | 946,685,906… (2000-01-01 clock, as Set O) | the same | **~3105 s: seconds since the lidar powered up**, not UTC |
| rate (header stamps) | 0.1000 s median, min 0.09997, max 0.10002, no gap > 0.15 s | ~10 Hz | 0.1000 s, min 0.09999, max 0.10001, no gap |

### 4.2 Axes, field of view, ranges

| | synthetic | Pandar128 (doubleT_platform, Set O) | Falcon (measured) |
|---|---|---|---|
| forward | −y | −y | **+x** (every point has x > 0, x up to 400 m) |
| left / up | +x / +z | +x / +z | +y / +z (right-handed; floor below the sensor) |
| azimuth about forward | −50…+50° | −50…+50° (120° grid) | **−59.6…+59.6°** |
| elevation | −25.1…+14.4° | −25.1…+14.4° | **−13.8…+12.4°** |
| range: min / max per frame (median) | 0.6 m / 199–206 m | 2.5 m (cache) / ~201–209 m | 3.3 m / 381 m |
| points per frame beyond 100 / 150 / 200 / 250 m (median) | 388–591 / 50–81 / 0–8 / 0 | similar | 665–697 / 119–132 / 46–48 / 16–17 |
| mount (1.1.0 calibration) | identity, height 1.09–1.12 m | identity, 1.12 m | adopted orientation (above), height 1.77 m, pitch −2.39°, lateral 0.77 m |

Synthetic frames contain a few single points beyond 250 m (up to 739 m in `synthetic_tunnels`). The sealed
`max_range` of 250 m drops them. The Falcon reaches farther than the Pandar: 46 points per frame lie beyond 200 m,
against 0–8. It has about as many distinct points per frame as the Pandar's 120° cloud (95k against 85–95k distinct; half the
Pandar's raw count, because the Pandar stores each echo twice), spread over a narrower vertical field. In both Falcon parts the scene is static: frame 984 against frame
100 has a median nearest-neighbour distance of 0.015 m, so the train stands.

`/rosout` (Seyond driver): about 0.95 M points/s. It reports `points_2nd_return=0`, but the cloud flags ~2 % of points
as second returns. There is one firmware `WARN`: "channel A correlation coefficient 0.9866 < 0.99".

## 5. Synthetic content

**Background.** `synthetic_platform` frames 0–314 have exactly the header stamps of Set O (`cloud_with_fake_obj`)
frames 1195–1509. Frame 0 is identical to Set O frame 1195 point for point within 2.5–201.7 m. Frames 315–385
continue the same real recording past Set O's end. `synthetic_switch` follows (stamps 946685971–946686044), and
`synthetic_tunnels` starts 0.1 s after the switch bag ends. So all three are cut from the ride Set O came from *(the
same ride: inferred from contiguous stamps)*. That part of the ride is not in any recording we hold.

**Objects in `synthetic_platform`**, measured as the exact difference against Set O. Object points have intensity 1.

| id | what (size, place in sensor frame) | frames | first in data | last | 1.1.0 |
|---|---|---|---:|---:|---|
| A | box ~0.5 × 0.4 × 0.45 m at the right rail (x −1.05…−1.36 m, on the bed) | 31–174 | 197.1 m | 3.8 m | `STOP` 106–118 (87→70 m) and 142–166 (39→12 m), `CAUTION` between and after |
| B | box ~0.55 × 0.55 × 0.45 m on the left, outside the gauge (x +2.1 → +1.4 m) | 68–252 | 200.5 m | 3.7 m | `CAUTION` only (track lateral +1.35…+1.4 m), never `STOP` |
| C | **person-shaped**: 0.6 m wide, 0.24 m deep, 1.72 m tall, standing on the bed; x 0.0 → −1.0 m while approaching | 90–385 | 200.9 m | train stops 7.84 m before it | `CAUTION` from ~166 m, **first `STOP` at 44.0 m** (frame 239), `STOP` to the end (147 frames) |

Per frame up to 2,294 points are added and up to ~2,000 hidden ones removed. The static boxes drift 0.2–0.8 m
laterally in the sensor frame over the approach (track geometry). Whether C also walks sideways is not settled.

**Objects in `synthetic_switch` and `synthetic_tunnels`.** These bags have no reference. The objects below were found
from the intensity-1 marker: compact intensity-1 clusters (`scripts/find_inserted.py`) and the share of intensity-1
points under each detector box (`scripts/classify_detections.py`). The list may be incomplete.

| bag | object *(inferred from intensity 1 + geometry)* | frames | 1.1.0 |
|---|---|---|---|
| switch | small box on the right rail | 60–80 (152→145 m) | not reported |
| switch | small box ~0.45 × 0.3 × 0.3 m near the right rail | 141–251 (113→7 m) | `STOP` 145–155 (111→103 m), then `CAUTION` |
| switch | low object, lateral +2.6 → +0.9 m | 304–352 (72→3 m) | `STOP` 318–352 from 51 m |
| switch | **thin object hanging from above**, 0.2–0.47 m wide, bottom ~1.7 m above the rail head | 324–415 (143→3 m) | `STOP` 374–416 from 69 m |
| switch | small box near the right rail | 611–681 (112→6 m) | `STOP` 616–659 from 104 m |
| tunnels | small object ~0.3 × 0.5 × 0.3 m, lateral −0.9…−1.1 m | – | `STOP` 259–287 from 55 m |
| tunnels | vertical panel ~2.0 m wide × 1.6–1.9 m tall, lateral −0.5 m | – | `STOP` 391–443 from 97 m |
| tunnels | flat object ~2.2 m wide lying across the rails | – | `STOP` 452–489 from 70 m |

No person-shaped object was identified in `switch` or `tunnels`. The tall object in `switch` hangs from the ceiling.

**Dust / suspension.** Not present in `synthetic_platform`, which was measured exactly: every added point belongs to
one of A, B, C, apart from ≤ 6 near-field points per frame. In `switch` and `tunnels` the free corridor shows no
volume-filling cloud of returns, either of intensity 1 or of any intensity. Isolated intensity-1 points stay at
~150–300 per frame. The only spikes come from objects passing close (`scripts/corridor_scan.py`,
`scripts/find_inserted.py`). This result is a heuristic. Perhaps the organizers will hand the dust out separately:
the bag names end in `_cloud_only`.

**Ground truth.** None was supplied.

## 6. Sealed 1.1.0 observation

| run | frames | STOP | CAUTION | GO | FAULT | CAUTION share | resets | wall (offline) | per frame p50 / p95 |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| synthetic_platform | 386 | 185 | 135 | 66 | 0 | 35 % | none | 13.5 s | 28 / 44 ms |
| synthetic_switch | 736 | 142 | 294 | 300 | 0 | 40 % | none | 25.5 s | 29 / 40 ms |
| synthetic_tunnels | 545 | 126 | 223 | 196 | 0 | 41 % | none | 21.1 s | 32 / 44 ms |
| falcon prefix (0–98 s) | 985 | 1 | 975 | 8 | 1 | 99 % | none | 19.6 s | 16 / 23 ms |
| falcon window (241–329 s) | 874 | 296 | 569 | 8 | 1 | 65 % | none | 17.4 s | 16 / 24 ms |
| *variant:* falcon prefix, axes as launch parameters | 985 | 5 | 968 | 12 | 0 | 98 % | none | – | – |
| *variant:* falcon window, axes as launch parameters | 874 | 307 | 559 | 8 | 0 | 64 % | none | – | – |

The variant rows set `sensor.forward=+x`, `left=+y`, `up=+z` and nothing else. They are not the jury default.

**Synthetic STOP episodes.** Each episode is classified by the share of intensity-1 points under the detection box.

| bag | episodes on inserted objects (first frame @ first distance) | false STOP episodes |
|---|---|---|
| platform | 106 @ 86.8 m (A), 142 @ 38.8 m (A), 239 @ 44.0 m (C, person) | none |
| switch | 145 @ 110.6, 318 @ 51.4, 374 @ 69.1, 616 @ 104.0, 624 @ 92.9, 641 @ 66.5 m | 7–14 @ 147→142 m (8 frames, intensity-1 share 0.06); 540–541 and 544–545 @ 23→15 m (2 + 2 frames, mixed 0.5–0.77: an object edge merged with background) |
| tunnels | 259 @ 55.0, 391 @ 96.8, 452 @ 70.4 m | 147–149 @ 70→67 m (3 frames), 367 @ 131.5 m (1 frame) |

CAUTION frames with a warning on an inserted object, against background only: platform 110 / 25, switch 144 / 150,
tunnels 19 / 204. In every bag the mount is `pending` for the first 190 frames, then `identity`. There is no `FAULT`.

**Falcon.** The runner works, with no decode error.

* Frame 0: `FAULT` (level `error`: "6 of 6 central 10 deg sectors without returns: view blocked", "track visible to 3
  m only (< 60 m)"). The configured −y forward looks at the sensor's side, where there are no returns.
* Frame 1: orientation adopted, reported as `forward=+y left=-x up=+z` relative to the configured vehicle frame,
  which is sensor +x / +y / +z. From then on `rail_lock` is 1.0 in 98 % of frames and `monitored_range` has a median
  of 111–115 m.
* Frame 192: mount `ok`, height 1.77 m, pitch −2.39°, lateral 0.77 m.
* Two static warnings remain for the whole time we saw: 105.6 m at lateral +1.1…+1.35 m and 115.0 m at +0.7…+1.3 m.
  So the node is in `CAUTION` almost always. Single `STOP`s fall on the 115 m object (prefix frame 159; window
  104–129, 640–641) and on a 152.8 m object (window frame 483).
* Window frames 568–873: `STOP` on an object 0.3–0.6 m deep, ~0.8–0.9 m wide and 0.8–1.7 m tall. It comes from
  ~127 m to ~97 m at ~1.2 m/s and turns back, *(inferred)* a person walking in the track. On a real obstacle this
  `STOP` is the right answer. It starts at 123 m.
* **Corrected 18.10 ([B2, whole recording](../falcon_full_2026-10-18/README.md)):** the person does not turn back;
  they walk on to 6 m in front of the train (the window ended at 329 s). Window frames 640–641 are the person
  (lateral −0.30 m), not the static 115 m object. t = 98–241 s and 329–444 s are now read.

Outputs: `/home/user/rs-data/extended/runs/*.jsonl|csv|meta.json|summary.json` (`falcon_*_axes_xyz.jsonl` for the
variant). Per-frame stats: `/home/user/rs-data/extended/char/`. Sample frames (.npz, 76 MB):
`/home/user/rs-data/extended/samples/`. The raw and derived bags were deleted after analysis because of disk space. They can be
re-created from the archives with the scripts below (hashes in §2).

## 7. Risks and impacts

| # | risk | card | evidence |
|---|---|---|---|
| 1 | The Falcon bag shows the jury `CAUTION` most of the time on a standing train, plus `STOP`s on a static object at 115 m (false-positive criterion 4) | N2 | §6 |
| 2 | First frame `FAULT` and the Falcon-specific geometry: the mount is 1.77 m high, pitched −2.4° and 0.77 m off the axis, while the defaults were measured at 1.075–1.12 m | N2 | §6 |
| 3 | No `ring` on the Falcon. The node passes `ring=None`, and ring-dependent tests fall back to geometry tuned on the Pandar grid (column free-top test). Offline tools fill ring = 0. `scan_id` is not a substitute, because it is not a fixed elevation | N2 | §4.1; Falcon README F1–F3 |
| 4 | Single return on the Falcon, where the Pandar recordings hold each echo twice: point-count bars tuned on duplicated pairs see about half the support per surface *(inferred)* | N2 | §4.1; `configs/default.yaml` `column_free_min_returns` comment |
| 5 | The Falcon header stamp is sensor uptime (~3105 s), not UTC. With `freshness_mode:=live` it is decades stale, as the Pandar bags (year 2000) already are, so the jury launch must stay on `freshness_mode:=replay` | N4 | §4.1, node docstring |
| 6 | Late `STOP` on the synthetic person (44 m; in the data from 201 m) while `monitored_range` is capped at 45 m at the platform. The experts score first-detect range | criterion 1 | §5 |
| 7 | Dust was announced but is absent, so our robustness to it is still unmeasured on organizer data, and the jury's own dust set may come later | N3 | §5 |
| 8 | Insertion is in place, not appended: Set O tooling (`label_fake_objects.py`) does not label these bags. The intensity-1 marker works but is not ground truth | eval | §5 |
| 9 | False `STOP`s on background in synthetic switch (8 frames at 147 m) and tunnels (3 + 1 frames) | F1 | §6 |
| 10 | Parts of the Falcon recording were not seen (98–241 s, 329–444 s): the train may move there | N2 | §3 |

## 8. Recommended next steps

| owner | step |
|---|---|
| **P1** (release / launch) | Write the second-lidar launch line in the jury README: `sensor_forward:=+x sensor_left:=+y sensor_up:=+z` for `/iv_points`, `frame_id` `seyond`. Auto-calibration also finds it after one `FAULT` frame. Keep `freshness_mode:=replay` for both lidars. Check that the node discovers `/iv_points` on its own. Do the N4 two-bag switch with a Pandar bag followed by the Falcon bag (the `frame_id` change must reset the detector). |
| **P1** | Ask the organizers: (a) whether dust / suspension data is still to come (the `_cloud_only` names suggest a dust-free variant); (b) ground truth for the new synthetic objects; (c) what the walking figure at 97–127 m in the Falcon recording is, and whether the train moves later in it. |
| **P3** (detector) | Look at the two static Falcon warnings at 105.6 / 115.0 m: real gauge-edge structure, or the 0.77 m offset / 1.77 m height / −2.4° pitch handled wrongly. Assess ring-dependent rules with `ring` absent, and the single-return point density. Keep it measurement first: no tuning on this data without registering it as development data. |
| **P3** | Examine why the person in `synthetic_platform` stays `CAUTION` from 166 m to 44 m (the `monitored_range` cap at 45 m at the platform). Same caveat. |
| **P4** (evaluation) | Build per-object labels for the three synthetic bags from the intensity-1 marker: exact for platform frames 0–314 against Set O, marker-based elsewhere. Score first-STOP distance per object. Read the unseen Falcon parts (98–241 s, 329–444 s) with `window_bag.py` and two more streamed windows, about 4 GB each. Keep G3 untouched. |
| **P4** | Run N3 with our own dust generator. The organizers' data offers no dust to measure against. |

## 9. Answers to the open items of the Falcon document audit

[`../../sensor/falcon_prime/README.md`](../../sensor/falcon_prime/README.md) was written from the manual before the bag
was decoded. Measured on the bag:

| item there | measured here |
|---|---|
| axis convention of the recording "open" (manual: native x up, y right, z forward) | the bag publishes the **ROS convention: x forward, y left, z up**, not the native frame. The "native" row of its §3 table (blind detector) does not happen with this bag. The second row applies: `sensor_forward:=+x sensor_left:=+y sensor_up:=+z`, or the default with auto-calibration (one `FAULT` frame, adopted at frame 1) |
| topic / frame (manual, ROS 1: `/iv_points`, `innovusion`) | topic `/iv_points`; `frame_id` is **`seyond`**, not `innovusion` |
| W1 field list | §4.1: no `ring`; `scan_id` 0–37 and `scan_idx` 0–1272; `timestamp` f64; `flags`, `elongation`, `is_2nd_return`; 48-byte point |
| F4 dual-return duplicates | single return (no duplicate xyz) |
| R1 range histogram | median per frame: 665–697 points beyond 100 m, 119–132 beyond 150 m, 46–48 beyond 200 m, 16–17 beyond 250 m (dropped by `max_range` 250); max ~380–500 m |
| G3 frame span | per-point timestamps span ~95 ms per frame (Pandar ~32 ms) |
| G1 floor / rail fit | `rail_lock` 1.0 in 98 % of frames, `monitored_range` median 111–115 m (standing train) |
| A4 switching lidars in one node | not run. With the default axes, each `frame_id` change makes a new detector, and auto-calibration finds both sensors *(inferred from the two separate runs)*. With explicit Falcon axes, a following Pandar bag would need its own search: to be tested (N4) |

## Scripts (in `scripts/`)

| script | what |
|---|---|
| `zst_tar_stdin.py` | list / extract a zstd tar from stdin; truncated prefix (`--max-bytes`) or window (`--skip-bytes`) of a member |
| `prefix_bag.py` | readable rows of a truncated sqlite split → a valid bag |
| `window_bag.py` | message blobs of a byte window of a split (sqlite overflow chains) → a valid bag |
| `characterize_bag.py` | per-frame layout, counts, ranges, fields, duplicates, stamps |
| `diff_vs_reference.py` | exact added / removed points against a decoded reference recording, clustered |
| `corridor_scan.py` | free-space box counts and clusters ahead of the sensor |
| `find_inserted.py` | intensity-1 object clusters and free intensity-1 points (dust indicator) without a reference |
| `classify_detections.py` | intensity-1 share under each detector box of a judge_runner run |
| `summarize_run.py` | decision counts, STOP episodes, health / mount summary of a judge_runner jsonl |
