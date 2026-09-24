# Experiments log

## Re-measurement on the current code (24.09)

The v0.6.3 numbers were measured on commit `c1c2b6a` (merged as `1210580`); `a92625e` then changed
the detector and `configs/default.yaml` (two opt-in stages, both off) without data at hand, and set F
had not been re-run since v0.6.2. On 24.09 the organizers' data was downloaded again and cached at
full rate (all 13 759 frames), and the current code (`main` at `4cd32d6`) and v0.6.3 were run on it
(raw summaries: [`experiments_2026-09-24_remeasure.json`](experiments_2026-09-24_remeasure.json)):

| check | result |
|---|---|
| real frames: per-frame output of the current code against v0.6.3 (obstacle, warning, nearest and clear distance, every detection's id, distance, lateral, kind, zone) | **identical on all 13 759 frames.** Every real-data number of §0 holds for the current code: five obstacle-free bags 107 alarm frames / 20 events / 27 STOP episodes; ride 204 / 47 / 39 (3.6 events per km); the person 58 of 61 frames from frame 11, distance error ≤ 0.23 m; the object on the rail 124 of the 126 frames from frame 75 (127 of 185 by its own detection); 3 STOP episodes on `doubleT_obstacle`; health warnings other than latency on 196 frames (1.4 %) |
| false alarms by the first processed frame (`scripts/start_offsets.py`) | 30 of 30 rows identical to the v0.6.3 record (14–20 events on the five bags) |
| set F (synthetic objects in the moving ride) | first confirmations unchanged; the held ranges, frame recall and off-object detections moved because round 2 predates v0.6.3's hold over one missed frame — with the hold off the current code reproduces round 2's straight set value for value. Round 3 table: §2d |
| offline timing, the two versions back to back (`resense bench`, every frame, `OMP_NUM_THREADS=1`, an idle 4-core sandbox — not the machine of 23.09) | current code 36.5–52.2 ms mean, p95 50.3–67.1 ms; v0.6.3 35.1–57.4 ms, p95 46.3–75.4 ms; per recording −9…+6 % (run-to-run noise), no regression. §3's 42–64 / 53–78 ms of 23.09 stays the quoted figure |
| derived figures that had no recorded source | `CAUTION` (warning or a non-latency health warning, no obstacle) on 27–68 % of the frames of the five obstacle-free recordings and on 41 % of the ride; 16 of the 47 ride events are first confirmed beyond 100 m (a review had counted 14) |

## Sprint 5 local freeze (2026-09-23; no new real-data measurements)

The shipped `track.rails_far_check_enabled`, `lowobj.near_enabled` and
`accumulation.estimate_speed` are all `false` in both parameter files and the Python defaults.
The first two are experimental opt-in paths; the LiDAR-only speed estimator is opt-in as well.
Historical set F results below use **synthetic positives with legacy, detector-derived
placement on real backgrounds**, not real long-range positives or independent placement.
No new recall, false-event, FPS or latency measurement on bags/cache or in ROS is claimed by
this local freeze: the cache/bags and a reachable Docker daemon were unavailable. Open3D was
also unavailable locally, so Open3D-dependent tests were skipped. Re-evaluate the opt-in paths
on real recordings before interpreting them as shipped improvements. (The shipped defaults were
re-measured on the data on 24.09: "Re-measurement" above. The opt-in paths are still not
evaluated.)

## Sprint 4 acceptance check (2026-09-23, no new ROS measurements)

This workspace run had no reachable Docker daemon and no ROS bag/cache files. Therefore Sprint 4
does not claim a new ROS FPS, ROS latency, dropped-frame count, or obstacle acceptance result. The
Docker acceptance scripts now check the daemon before starting and report the limitation explicitly;
`smoke_test.sh` also fails fast when it is run outside the ROS 2 image. Historical ROS numbers in
§3b remain dated measurements from the earlier Docker environment and must not be read as results
of this run. Offline latency can be measured with `resense bench --npy <cache>` or
`scripts/bench_node_path.py --npy <cache>` when a non-empty cache is available; no threshold or
experimental flag is changed by this check.

## Sprint 3 protocol (no new measured results)

The historical set F results below use `scripts/far_range_eval.py`'s **legacy** placement:
the synthetic object is anchored on a per-frame track fit and vault correction derived from
the evaluated background. That can flatter recall on curves and at the envelope edge.
There is no independent set F run recorded here; the historical set F positives do not
establish real long-range obstacle generalisation. For a reproducible sensitivity run when
`new_data` full-rate cache and its stamps are available, first obtain a separately surveyed
vehicle-frame axis and rail profile (not the detector's far fit), then run e.g.:

```bash
python scripts/far_range_eval.py --cache /data/cache/new_data --files 46,68,98,140,168,172 \
  --frames 110 --kinds person,box0.5,box1.0 --start 200 --seed 3 --jobs 4 \
  --placement-mode independent --axis-center <survey_m> --axis-yaw-deg <survey_deg> \
  --axis-curvature <survey_per_m> --rail-z0 <survey_m> --rail-grade <survey_m_per_m> \
  --lateral=-0.8:0.8 --lateral-offset 0.15 --yaw-perturb-deg 10 \
  --out out/far_independent.json
```

Create `out/` first. The generated `setF-placement-v1` JSON contains run parameters,
config and speed-input SHA256s, cache filenames, per-frame truth/visibility and the summary;
the selected frame stamps are hashed as well. A single fixed vehicle-frame axis over a moving
curve is an approximation: validate the physical reference for each sequence before using
its outcomes as evidence about curves. Do not copy the old JSON numbers into it. Repeat with other offsets, yaws, surveyed curves,
and the same seed for comparisons. Without the cache and independent reference there are no
new recall, first/sustained range or real-positive generalisation numbers to report.

**Reading order.** §0 is the shipped version (v0.6.3, 23.09; re-measured on the current code on
24.09, section "Re-measurement" at the top) on all real data; §0a is v0.6.1,
the version the organizers' Q&A answers produced; §1–§1d and §2–§2d are the record of how the
detector got there (real bags; synthetic obstacles in real frames; long range on the moving
ride), §3 timing, §4–§5 lessons and next steps, §6 mount calibration, §7 the recognition methods
side by side, §8 the learned second opinion. Raw summaries:
[`experiments_2026-09-24_remeasure.json`](experiments_2026-09-24_remeasure.json) (the re-measurement
of every headline number on the current code, 24.09),
[`experiments_v0.6.3_real_fullrate.json`](experiments_v0.6.3_real_fullrate.json) (v0.6.3 over all
13 759 frames, STOP episodes, the leave-one-out check),
[`experiments_v0.6.3_start_offsets.json`](experiments_v0.6.3_start_offsets.json) (false alarms by
the first processed frame),
[`experiments_v0.6.2_real_fullrate.json`](experiments_v0.6.2_real_fullrate.json) (v0.6.1 and every
v0.6.2 step over all 13 759 frames, plus the leave-one-out check),
[`experiments_v0.6.2_setF.json`](experiments_v0.6.2_setF.json) (set F round 2: small objects,
rail heads, the envelope edge, curves, station stops, sustained range),
[`experiments_v0.6.2_margins_lying.json`](experiments_v0.6.2_margins_lying.json) (the straddle
thresholds' margins, the low-object width cap, the lying person),
[`experiments_v0.6.1_real_fullrate.json`](experiments_v0.6.1_real_fullrate.json),
[`experiments_v0.6.1_setF.json`](experiments_v0.6.1_setF.json) (set F round 1). Every number is
**real** (recording named) or **synthetic** (said so).

Headline numbers of v0.5 were for **v0.5 (real data, 2026-09-21, Sprint 2)**: every frame of the six
organizer bags cached as `*.npy` (`scripts/cache_frames.py`, 2 488 frames), pure Python on the
4-core sandbox (the jury's i7-9700E has 8 faster cores; the load of every timing run is
stated). Raw per-frame results of the v0.3 baseline are the captain's
`/data/results/v0.3/<bag>.jsonl` (commit f2c57e5, 21.09); the v0.5 runs are
`python -m resense.cli run --npy /data/cache/<bag> --out <bag>.jsonl --quiet` with
`configs/default.yaml` of commit 9b56bdf (merged as 82815e9) (per-bag summaries in
[`experiments_v0.5_real_fullrate.json`](experiments_v0.5_real_fullrate.json)); the
same-machine A/B configs are listed in §1b. Every number below is either **real** (bag named)
or **synthetic** (said so). The day-1 numbers on subsampled frames that this file carried
before 21.09 are superseded (they understated the 10 Hz false-alarm rate by an order of
magnitude, CAPTAIN.md finding 2 of 21.09).

## 0. v0.6.2 (23.09) — after the criteria review; v0.6.3 after the second one

**v0.6.3 (23.09, after the second independent review; raw: [`experiments_v0.6.3_real_fullrate.json`](experiments_v0.6.3_real_fullrate.json),
per-frame fingerprints for refactors: `scripts/output_fingerprint.py`; measured on commit `c1c2b6a`,
merged as `1210580`. `a92625e` then added two opt-in stages to the detector and
`configs/default.yaml`, both off by default; re-run on 24.09, the current code gives **identical
output on every one of the 13 759 frames**, so every number of this section holds for it — see
"Re-measurement" at the top).** Three changes, each measured on all
13 759 frames against v0.6.2 (the per-frame outputs of both runs compared):

1. **Low-object width cap 1.6 → 2.2 m** (the envelope's width): a person lying across the track
   on a shallow bed is kept (§2d); decision and distance **identical on every real frame**.
2. **Mount calibration**: between two spaced observations the frame is no longer measured
   (it cost 10–15 ms per frame for the first ~20 s of every recording, i.e. all of a short
   control bag), and a tilt is applied from 0.75° instead of 0.5° — 1.5× the p90 error of the
   20-observation median on a moving train (§6). With the old threshold the new sampling applied
   a noise-level +0.51° roll on one ride piece and gained 6 false events; with 0.75° the decision
   and distance are **identical on every real frame** and every rig correction stays (the
   `doubleT_obstacle` rig: roll +3.02°, pitch −0.88°). The re-mount check of §6 gives the same
   residuals for every supported mount.
3. **A reported obstacle is held over one missed frame** (`tracking.hold_misses` = 1, at its
   predicted distance): the decision flickered — a confirmed obstacle missed in one frame gave
   `GO` for that frame. Events cannot change (the hold neither creates nor confirms a track);
   alarm frames and STOP episodes do:

| | v0.6.2 | **v0.6.3** |
|---|---|---|
| five obstacle-free bags: alarm frames / events / STOP episodes | 81 / 20 / 36 | **107 / 20 / 27** |
| ride (13 km): alarm frames / events / STOP episodes | 164 / 47 / 52 | **204 / 47 / 39** |
| the crossing person: frames reported of 61, first alarm | 58, frame 11 | **58, frame 11** |
| the object on the rail, its own detection: of 185 / of the 126 after the person leaves | 121 / 118 | **127 / 124** |
| `doubleT_obstacle` STOP episodes | 6 | **3** |

The hold costs 27 % more false-alarm frames (245 → 311 over all obstacle-free data) and saves
25 % of the STOP episodes (88 → 66) — a braking
signal that switches off for one frame and back on is worse than one that stays on 0.1 s
longer; events, the number of times a train would stop for nothing, are unchanged.

**Where processing starts** (review 23.09: through ROS the first 2–4 s of a played bag are lost,
so the jury's runs start after frame 0; `scripts/start_offsets.py`, v0.6.3, raw:
[`experiments_v0.6.3_start_offsets.json`](experiments_v0.6.3_start_offsets.json)). Alarm frames /
events / STOP episodes by the first processed frame:

| recording | start 0 | 10 | 20 | 30 | 40 |
|---|---|---|---|---|---|
| `doubleT_platform` | 4 / 4 / 1 | 8 / 3 / 3 | 12 / 3 / 1 | 7 / 1 / 1 | 0 / 0 / 0 |
| `roundT_doubleT` | 2 / 1 / 1 | 4 / 2 / 2 | 3 / 2 / 2 | 1 / 1 / 1 | 2 / 1 / 1 |
| `roundT_pressureGate_roundT`, `roundT_squareT_pressureGate_squareT` | 0 | 0 | 0 | 0 | 0 |
| `squareT_platform_squareT_switch` | 101 / 15 / 25 | 73 / 15 / 20 | 83 / 15 / 17 | 86 / 16 / 18 | 74 / 13 / 17 |
| **five bags** | **107 / 20 / 27** | 85 / 20 / 25 | 98 / 20 / 20 | 94 / 18 / 20 | 76 / 14 / 18 |
| person in the envelope, frames reported | 58 / 61 | 50 / 59 | 40 / 49 | 31 / 39 | 20 / 29 |
| object on the rail, own detection | 127 / 185 | 129 / 176 | 129 / 174 | 129 / 171 | 128 / 161 |

Starting at frame 0 is the worst case for the false alarms in total (107 / 20), so the figures of
this file are not flattered by it; single recordings move by a few frames (a trackside device at
48–54 m in `roundT_doubleT` and a bed fixture at 26–49 m in `doubleT_platform` are confirmed from
some start frames and not from others). What a late start costs is the first second: a person
already inside the envelope when processing begins is reported ~9–10 frames later (the track
model and the 0.5 s confirmation start from nothing); the object on the rail is found from every
start.

**v0.6.2.** The criteria review ([`SCORECARD.md`](SCORECARD.md)) found three things on the detection side:
the organizers' object on the rail was missed (2 of its 185 frames by its own detection), there were too many false
stops (82 events on the 20-minute ride), and nothing showed that the tuning was not fitted to
one stretch of track. v0.6.2 is v0.6.1 plus three changes, each measured by a full run over the
13 759 real frames (`scripts/eval_real.py`, the ride in 8 pieces with a fresh detector each):

| run | change | five bags: frames / events | ride: frames / events | person (61 frames in the envelope) | object on the rail, its own detection: of 185 frames / of the 126 after the person leaves |
|---|---|---|---|---|---|
| v0.6.1 | — | 104 / 30 | 289 / 82 | 58, first frame 11 | 2 / 2 |
| v0.6.2a | an object straddling the envelope floor is clustered whole (ALGORITHM.md §3.3b) | 126 / 39 | 396 / 131 | 58, 11 | 122 / 118 |
| v0.6.2b | + it must be ≥ 0.35 m across the track and ≤ 0.8 m along it | 105 / 31 | 292 / 83 | 58, 11 | 122 / 118 |
| v0.6.2c | + confirmation 0.5 s instead of 0.3 s (`tracking.confirm_time_s`) | 81 / 20 | 258 / 61 | 58, 11 | 121 / 118 |
| **v0.6.2** | + no rail pair in the near range → clusters beyond 40 m advisory (`gauge.no_rail_range`) | **81 / 20** | **164 / 47** | **58, 11** | **121 / 118** |

* **The object on the rail** (0.45 × 0.6 × 0.3 m lying across the right rail at 56 m, top
  0.10–0.15 m above the rail-head plane): **118 of the 126 frames after the person leaves it**
  (v0.6.1: 2), 121 of 185 over the whole recording (v0.6.1: 2; counted by the object's own
  bed-level detection within 0.4 m — with a 1 m window, as §0a and §1d counted before, the person's
  track next to it adds frames: 27 for v0.6.1, 146 for v0.6.2). Most of its ~21 points are below the rail
  head, ~3 above the 0.12 m envelope floor; v0.6.1 had the main stage see 0–3 points and the
  low-object stage a sliver, so neither confirmed it. v0.6.2 clusters all bed anomalies and the
  corridor points just above the floor together and reports a cluster whose top reaches 0.10 m
  above the rail head (rail fittings reach 1–8 cm, §1d). Without a shape rule (v0.6.2a) the
  trackside devices beside the rails — train stops, lubricators, signalling boxes, 0.2–0.35 m
  tall but mounted *along* the rail — added 49 ride events; they are 0.2–0.3 m across and
  0.5–1.4 m long, the object is 0.6 m across and 0.45 m long.
* **Confirmation 0.5 s** removed 11 of 31 events on the five bags and 22 of 83 on the ride. It
  costs 0.2 s (4.4 m at 80 km/h) for an object that appears inside the envelope, nothing for one
  tracked while it approaches: the real person, stepping in from the side, is still reported
  from frame 11, 0.3 s after entering the envelope.
* **No rails, no far alarm**: the ride's station stops (pieces 1 and 4) lost 14 events and 94
  alarm frames; nothing else changed, including the five bags (the platform-end structure of
  `squareT_platform_squareT_switch` is seen with the rails locked). Cost: at a station where the
  rails are not found an object beyond 40 m is a `CAUTION` until the train is within 40 m, and
  the verified-clear distance says 40 m.
* **Ride: 47 events in 13.0 km = 3.6 per km** (v0.6.1: 6.3 per km); alarm frames
  1.5 % of the ride. By cause (`scripts/mine_objects.py`, `labels/new_data_objects.json`):
  corridor-edge structures 18, bed-level fixtures 11, far small clusters 7 (91–180 m),
  other 6, tall structures 2, hanging equipment 2, person-like 1 (a wall cabinet in a curve,
  checked by eye in v0.6). The organizers confirmed in writing (23.09) that the ride contains no
  obstacle, so every one of these is a false alarm.
* Health warnings other than latency: 196 of 13 759 frames (1.4 %, rails lost at stations and
  switches), as in v0.6.1.
* **Long range and small objects** (set F, §2d, objects ray-cast into the moving ride; round 2
  on v0.6.2, round 3 on v0.6.3 = the current code): a person on straight track first confirmed
  at 148 m (median of 6), detected in ≥ 90 % of the frames from 135 m inward (round 3, with the
  v0.6.3 hold: 149 m) and in ≥ 90 % of every 10 m band from 115 m inward; 167 m first
  confirmation with a train speed given; curves R ≈ 350 m 6 of 7 approaches (58–86 m, the
  sightline); station stops 6 of 6 from 113 m; 30 cm objects on a rail head 6 of 6 from 42–44 m
  (round 3, new draws: 42–49 m); objects on the bed between the rails are below the envelope
  (policy, §3.3b).
* **Through ROS in Docker** (§3b): the organizers' procedure on the real frames, two recordings
  into one node; the first run found and fixed a transport bug (best-effort input lost 196 of
  201 ten-megabyte clouds).

**Is the gain spread over the data?** The parameters were chosen on the frames they are scored
on — there is no held-out data with obstacles. `scripts/consistency_check.py` splits the data
into 13 subsets (the five empty recordings and the ride's eight ~2.5-minute pieces) and asks,
leaving each subset out in turn, whether v0.6.2 would still have been chosen over v0.6.1 on the
rest (fewer events there, the real person and object still found):

| subset | v0.6.1 → v0.6.2 events | subset | v0.6.1 → v0.6.2 events |
|---|---|---|---|
| `doubleT_platform` | 6 → 4 | ride piece 0 | 4 → 3 |
| `roundT_doubleT` | 2 → 1 | ride piece 1 | 20 → 11 |
| `roundT_pressureGate_roundT` | 1 → 0 | ride piece 2 | 12 → 8 |
| `roundT_squareT_pressureGate_squareT` | 0 → 0 | ride piece 3 | 4 → 2 |
| `squareT_platform_squareT_switch` | 21 → 15 | ride piece 4 | 18 → 7 |
| | | ride piece 5 | 11 → 6 |
| | | ride piece 6 | 7 → 6 |
| | | ride piece 7 | 6 → 4 |

(events = distinct confirmed track ids, as `eval_real.py` counts them.) **Fewer events in 12 of
13 subsets, more in none; chosen in every leave-one-out.** The same check for the 0.5 s
confirmation alone: 12 fewer, 0 more; for the rail rule alone: fewer in the two pieces with
station stops, equal elsewhere. This is not a held-out test of the ~15 infrastructure rules
tuned since v0.5 — those were tuned on the same recordings — but none of the v0.6.2 gains rests
on one recording.

**Threshold margins of the straddle stage** (23.09, second review: "the thresholds sit close to
the one real object"). Each threshold moved by 20–25 % either way, one full run over the 13 759
frames each, compared subset by subset with the shipped run (`scripts/consistency_check.py`;
events summed over the 13 subsets, 67 for v0.6.2):

| variant | events (13 subsets) | object on the rail, of 185 frames | person |
|---|---|---|---|
| **v0.6.2** (top ≥ 0.10 m, ≥ 0.35 m across, ≤ 0.8 m along) | **67** | **121** | 58 / 61 |
| `straddle_min_top` 0.08 | 66 | 127 | 58 / 61 |
| `straddle_min_top` 0.12 | 67 | 91 | 58 / 61 |
| `straddle_min_width` 0.30 | 68 | 121 | 58 / 61 |
| `straddle_min_width` 0.40 | 68 | 110 | 58 / 61 |
| `straddle_max_length` 0.6 | 67 | 121 | 58 / 61 |
| `straddle_max_length` 1.0 | 69 | 121 | 58 / 61 |

The false alarms barely move (66–69 events) — the rail fittings (≤ 8 cm) and the trackside
devices (0.2–0.3 m across) are well inside the thresholds — while the object loses a quarter
of its frames at a 0.12 m top threshold and 9 % at 0.40 m width. The margin that is thin is the
one on the object's side; 0.10 m sits between the fittings' 8 cm and the object's 11–16 cm, and
lowering it to 0.08 m would add object frames at no measured cost here, but at the fittings' own
height — kept at 0.10 m.

**Low-object width cap 1.6 → 2.2 m** (23.09, second review). A person lying across the track
on a shallow bed is ~1.8 m wide; the low-object stage capped clusters at 1.6 m across, so it was
rejected (set F, §2d: 2 of 6 approaches). The cap is now the envelope's 2.1 m plus margin: **the
decision and the distance are identical on every one of the 13 759 real frames** (full run,
`lowobj.max_width=2.2` against v0.6.2), and the lying person is found in 6 of 6 approaches (§2d).
Raw summaries of both: [`experiments_v0.6.2_margins_lying.json`](experiments_v0.6.2_margins_lying.json).

## 0a. v0.6.1 (22.09) — after the organizers' Q&A session

The organizers' recorded Q&A session ([`organizers/QA_session.md`](organizers/QA_session.md))
changed the target: the envelope to monitor is **2.1 m × 3.0 m** (not our assumed 2.8 × 3.5 m),
the size criterion is **30 × 30 × 10 cm**, **hanging cables must be detected**, the **LiDAR mount
varies**, the hidden check uses rides through other tunnels plus the organizers' **synthetic
obstacles**, and there is an **object on the rail** in `doubleT_obstacle`. v0.6 implements all of
it and is measured on **every frame of every recording** the organizers gave — 13 759 frames:
the six bags (2 488) and the 20-minute ride `new_data` (11 271) — cached once
(`scripts/cache_frames.py --int16 --stamps`) and run with `scripts/eval_real.py` (the ride in 8
parallel pieces with a fresh detector each; bag receive times; 4-core sandbox shared by the
four pieces, so the latencies in these runs are inflated ×2–3 — clean timing in §3).

| | v0.5 logic (same frames, same harness) | **v0.6.1** |
|---|---|---|
| five obstacle-free bags (2 287 frames): alarm frames / events | 116 / 32 | **104 / 30** |
| 20-minute ride (11 271 frames, 13.0 km): alarm frames / events | 448 / 93 | **289 / 82** (6.3 per km, 4.1 per minute) |
| frames with a health warning other than latency (all 13 759) | — | **196 (1.4 %)**: track model lost its rails at stations / switches (v0.6: 42 %, drift monitor) |
| crossing person, frames inside the 2.1 m envelope (61): reported / first alarm | 61 / frame 8 | 58 / frame 11 (0.3 s after entering) |
| object on the rail (185 visible frames) | 24 (only while the person stood next to it) | 27 (see §1d: 126/126 with the bed-level setting) |
| hanging cable, 10 cm box on a rail (synthetic tunnel) | not reported (column / floating / hardware rules) | reported (`tests/test_envelope.py`) |
| person approaching on the moving ride (set F, §2d): first confirmed detection | ~106 m (far rule off) | **150 m median, 169 m max** (6/6); **177 m** with a train speed given |
| other mounts (upside down, `+x` forward, backwards, rolled / pitched) | blind / skewed corridor | recovered from the data (§6) |

**v0.6 → v0.6.1** changed only the mount calibration (§6, ALGORITHM.md §2b): v0.6 froze the
median of the first 5 frames, which on a moving train is the local cant, not the mount — the
pieces of the ride froze −0.97…+1.63° of "roll" for one level sensor, `roundT_doubleT` −1.55°,
`squareT_platform_squareT_switch` −0.69° of pitch — and its drift monitor then warned on 42 %
of all frames. v0.6.1 finds those rigs level (the ride's survey: −0.09°) and keeps the 3.0° of
the `doubleT_obstacle` rig. Recordings whose calibration came out the same are bit-identical
between the two runs; on the others 139 alarm frames appeared and 87 disappeared (v0.6: 83 / 25
and 258 / 74): the edge structures that make most of the false alarms react to sub-degree tilts
in both directions, so these counts carry a ±20 % spread from the mount state alone. The v0.6.1
numbers are the ones with the physically right mount.

The v0.5 row is the v0.5 detection logic run by the v0.6 harness with the calibration off
(`calibration.enabled: false`); it differs slightly from EXPERIMENTS.md §1 (96 / 32) because of
the bag receive times, the int16 cache and the v0.6 track warm-up (§6).

## 1. Real bags at full rate (every frame, 10 Hz)

The five bags other than `doubleT_obstacle` contain no obstacle inside the gauge: every alarm
there is false. `doubleT_obstacle` has one true obstacle, the person crossing the track at
55–57 m (in the strict gauge in frames 2–72, `labels/doubleT_obstacle.json`).

| bag | frames | v0.3 alarm frames / events / advisory | **v0.5 alarm frames / events / advisory** | v0.5 first alarm (frame) | v0.5 alarm distances | what alarms in v0.5 |
|---|---|---|---|---|---|---|
| `doubleT_obstacle` (stationary, person crossing) | 201 | 76 / 3 / 199 | **69 / 1 / 199** | 7 | 55.5–56.6 m | the person only (v0.3: also the column row at 17–19 m and 34 m, 2 false events) |
| `doubleT_platform` | 345 | 178 / 29 / 110 | **15 / 4 / 271** | 2 | 3.0–114.5 m | a 2.1 m tall, 0.5 m wide post at 85–87 m left of the axis (10 frames; 0.1 m under the column rule), one frame of a 5 m long 0.2 m high strip at the nose at frame 177 and one 4-voxel cluster at 104.5 m |
| `roundT_doubleT` | 252 | 126 / 20 / 140 | **0 / 0 / 226** | — | — | nothing (v0.3: columns and wall segments of the diverging double-track section, pulled in by the half curvature and the yaw jitter) |
| `roundT_pressureGate_roundT` | 268 | 106 / 19 / 135 | **16 / 5 / 262** | 48 | 42.0–77.9 m | five duct / cabinet fragments at \|dy\| = 1.5–1.6 m, 42–78 m, 1–8 frames each (inner edge 0.05–0.15 m inside the 1.40 m gauge) |
| `roundT_squareT_pressureGate_squareT` | 545 | 87 / 19 / 396 | **5 / 3 / 499** | 99 | 101.3–127.2 m | three far clusters at 101–127 m (6–16 voxels), one of them lasting 3 frames |
| `squareT_platform_squareT_switch` | 877 | 504 / 105 / 680 | **60 / 20 / 779** | 67 | 71.9–119.2 m | the platform-end structure at 82.9 m while the train stands at the platform (2.2 × 0.4 × 1.2 m, lowest point at the bed, 5–8 voxels, 15 events of 1–7 frames, ~50 frames): a low ramp / rail at dy +1.2…+1.8 m by the single-frame axis that the run's left-bending curvature (R ≈ 3 km from the hall walls) puts at +0.5…+1.0 m; plus four single-frame far clusters at 87–119 m |
| **five obstacle-free bags** | 2 287 | **1 001 / 192** / 1 461 | **96 / 32** / 2 037 | | | |

The per-bag "what alarms" column and the cause table below were written for the first cut of v0.5 (89 / 29); the final defaults carry the two safety tweaks of the review of 22.09 (`wall_face_min_height` 2.0 m and `floating_max_height` 1.2 m so that a person on a platform edge stays an obstacle; `walls_max_yaw` 0.09), which add 3 alarm frames / 1 event on `doubleT_platform` (a near strip at the nose in frame 2) and 4 / 2 on the switch bag, and change nothing on the person.

Renders (`img/`): `roundT_doubleT_0145_v03.png` vs `roundT_doubleT_0145_v05.png` (the v0.3 axis pulls the
column row of the diverging double-track tunnel into the corridor, v0.5 follows the rails),
`squareT_platform_switch_0400_v03.png` vs `_v05.png` (the train standing at the platform: roof strips and
the hall end wall are advisory in v0.5), `doubleT_obstacle_0030_v05.png` (the person on the track at
55.7 m; the whole bag as `video/doubleT_obstacle_offline.mp4`).

On the labels of `doubleT_obstacle` (`resense eval --npy /data/cache/doubleT_obstacle --gt
labels/doubleT_obstacle.json --text`, 71 in-gauge person frames): v0.3 recall 63/71, first
alarm frame 9, 13 false-alarm frames / 2 events (the column row); **v0.5 recall 66/71 (93 %),
first alarm frame 7, 3 / 0 (frames 73–75, the person 0.1–0.2 m outside the gauge) false-alarm frames / events**; the person is
confirmed inside 50–62 m in 69 (frames 7–75, one track) consecutive frames.

Evolution (the day-1 rows were measured on 272 subsampled frames and are kept for the
record; from v0.4 on the numbers are full rate):

| version | change | false-alarm frames / events on the empty bags | person recall (`doubleT_obstacle`) | ms/frame (4-core sandbox) |
|---|---|---|---|---|
| v0.0 (15.09) | fixed lateral centre, box corridor, raw DBSCAN | 149 / — (231 subsampled frames) | — | 42–1461 |
| v0.1 | rail-based self-calibration, rail-relative gauge, voxelised range-normalised DBSCAN, zones | 92 / — | — | 32–75 |
| v0.2 | wall-based yaw/curvature, robust two-stage floor fit | 76 / — | — | 38–75 |
| v0.3 (f2c57e5) | nearer-boundary rule, gauge 1.4 m, hardware/linear/wall filters, corridor validity range, overhead demotion | 67 / — subsampled; **1 001 / 192 at full rate** (2 287 frames) | 63/71, first alarm frame 9 | 48–83 mean, 84–132 p95 |
| v0.4 (f4e311f, 21.09) | ego-speed estimate + 5-frame accumulation beyond 40 m, verified bed extrapolation, retro rule, smear guard | 1 016 / 187 (+1.5 % frames, +9 % beyond 60 m) | 64/71 (one frame gained by lateral smear), first alarm 9 | 73–133 mean, 112–193 p95 |
| **v0.5 (real data, 21.09)** | axis: yaw from the rail slabs, curvature 1/R from the walls with the tangent fixed (v0.3 applied half the curvature), rate limits, side-agreement caps; height reference trusted 20 m beyond the bed fit (60) or as verified; five infrastructure signatures (column, elevated, floating, edge, wall face); zone / hit history over 10 frames, persistence in seconds; no merging below 1 m/s, lateral smear guard; vectorised binning | **89 / 29** | **66/71 (93 %)**, first alarm frame 7 | 43–84 mean, 51–171 p95 (quiet 4-core sandbox, §3); v0.3 code back to back: 56 / 71 and 71 / 76 on the two reference bags |

## 1b. False alarms by cause (why v0.3 alarmed on 44 % of the frames) and what removed them

Method: every confirmed gauge track id of the v0.3 full-rate runs on the five empty bags was
listed with its frames, distance range, lateral offset, size, lowest / highest point above
the rail head, voxel count, confidence and intensity, the worst cases were rendered
(`resense run --render --x-max 160`) and the raw points of the far structures dumped in
corridor coordinates. Each track is classified by the signature of its median cluster (first
matching rule); a frame can carry several causes, so the rows add up to more than the totals.
Counts are alarm frames / events:

| cause (v0.3 track signature) | `doubleT_platform` | `roundT_doubleT` | `roundT_pressureGate_roundT` | `roundT_squareT_pressureGate_squareT` | `squareT_platform_squareT_switch` | **total** | v0.5 |
|---|---|---|---|---|---|---|---|
| beyond the bed fit + 20 m: height reference (extrapolated bed 0.3–0.65 m off at 85–105 m lifts far rails / switch parts into the low zone and pulls the roof, h ≈ 4 m, into the polygon top) | 5 / 4 | 35 / 6 | 0 | 21 / 2 | 442 / 35 | **503 / 47** | — |
| column / post: > 2.2 m tall, < 1 m wide, pulled onto the axis by the yaw error in the diverging double-track section | 16 / 2 | 70 / 7 | 0 | 0 | 8 / 3 | 94 / 12 | — |
| elevated wide: lowest point > 1.2 m, > 2 m wide (roof strips / beams at 104–130 m of the stopped train) | 0 | 0 | 0 | 0 | 356 / 9 | 356 / 9 | — |
| floating small: lowest point > 0.7 m, < 1.5 m tall, < 1 m wide (signs, lamps on the wall at 46–73 m) | 109 / 8 | 3 / 1 | 1 / 1 | 5 / 1 | 10 / 4 | 128 / 15 | — |
| edge fragment: \|lateral\| > 1.2 m, long and low (duct / bench segments of the round tunnel at 3–35 m) | 0 | 0 | 90 / 11 | 12 / 4 | 17 / 4 | 119 / 19 | — |
| other corridor-edge structure at \|lateral\| > 1.2 m (platform-edge posts at 23–25 m, column row at 17–19 m, cabinets, signs) | 99 / 5 | 33 / 5 | 25 / 7 | 62 / 12 | 13 / 5 | 232 / 34 | — |
| wall / portal face (the platform-hall end wall at 72–78 m of the stopped train, full height, corridor centre empty) | 0 | 0 | 0 | 0 | 206 / 13 | 206 / 13 | — |
| other | 32 / 9 | 2 / 1 | 0 | 0 | 198 / 32 | 232 / 42 | — |
| **all** | 178 / 29 | 126 / 20 | 106 / 19 | 87 / 19 | 504 / 105 | **1 001 / 192** | **89 / 29** (per bag: 12 / 3, 0 / 0, 16 / 5, 5 / 3, 56 / 18) |

Three findings behind the causes, all measured this round:

1. **The axis bent half as much as the tunnel.** `estimate_axis_from_walls` fitted each
   boundary with a free quadratic, stored the quadratic coefficient (1/2R) as `curvature` and
   `center_y` applied it as 1/R: on a hand-made R = 800 m scene the estimated curvature was
   6.2e-4 against 1.25e-3 and the axis was 2.4 m off at 100 m (`tests/test_algorithm.py::
   test_axis_follows_a_curved_track`). On the curve bags the free fit also traded yaw against
   curvature: the rail-pair midpoints measured in three slabs (4–12, 12–20, 20–30 m) show the
   v0.3 axis 0.8–1.0° off the rail direction on `roundT_pressureGate_roundT` #100/#150/#200,
   `roundT_doubleT` #60/#145, `doubleT_platform` #100/#300 (up to 2.9° on `roundT_doubleT`
   #120), its yaw saturated at the ±2° clip in every moving bag, and it jumped by 0.5–1.2°
   between frames (p90–p99 of |Δyaw| on `roundT_doubleT` and `doubleT_platform`; a train at
   15 m/s on R = 700 m yaws 0.12° per frame). The rail-ridge profile itself was built in
   absolute Y, so in a curve the ridges smeared over 0.5 m and the centre was biased (0.9 m on
   the hand-made scene). v0.5: profile in the previous axis' coordinates, yaw and centre from
   the rail slabs, curvature 1/R from the walls with that tangent fixed, rate limits of 0.17°
   and 1e-4 m⁻¹ per frame, straight bonus only with two agreeing boundaries, range caps with
   one boundary (120 m) or disagreeing ones (60 m). Frame-to-frame |Δyaw| on the moving bags
   fell from p95 0.2–0.7° to 0.06–0.17° (v0.5 runs, `roundT_doubleT` / `doubleT_platform`).
2. **The height reference beyond the bed fit is not usable for the polygon's top and
   bottom.** On `squareT_platform_squareT_switch` frames 400/500/650 the run's EMA floor was
   −1.67 / −1.69 / −1.73 m at 72 / 85 / 105 m against a measured bed (5th percentile of Z
   within ±1 m of the axis) of −2.00 / −2.34 / −2.22 m: 0.3–0.65 m too high, so a roof beam at
   h = 4.1 m read 3.4–3.6 m (inside the 3.5 m top) and switch rails at h ≈ 0 read 0.3–0.5 m
   (inside the 0.12 m low zone); the 353- and 346-frame events at 127–130 m and 104–105 m
   (ids 325, 332) and the ~90 frames at 147.5 m are this. The bed fit ends at 50–110 m on the
   bags (p10–p90), the v0.4 verification reaches 105–145 m; v0.5 trusts the reference 20 m
   beyond the fit or as far as verified (was 60 m unverified).
3. **Corridor-edge structures at \|dy\| = 1.5–1.6 m are 0.1–0.2 m outside the 1.40 m gauge.**
   Ducts and benches of the round tunnels, the platform edge (1.6 m) and its fittings, the
   column row of the double-track tunnel (1.7 m) all sit at that distance; any axis error
   above 0.1 m at 20–80 m makes a sliver of them "inside" for a few frames, and three such
   frames were an alarm. The near axis is now good to a few centimetres (rails), the
   persistence needs 60 % of the last ten hits inside and 60 % matched, and the edge / column
   / floating / wall-face signatures cover the shapes; what remains is measured below.

**Ablation (all six bags, every frame, same code = commit 9b56bdf (merged as 82815e9), one lever group
switched off at a time by `--config`; five-bag alarm frames / events, and the person of
`doubleT_obstacle`: recall on the 71 labelled frames, first alarm frame):**

| variant | five empty bags: alarm frames / events | `doubleT_obstacle`: recall, first alarm, false frames / events | reading |
|---|---|---|---|
| v0.3 (f2c57e5 results) | 1 001 / 192 | 63/71, 9, 13 / 2 | baseline |
| v0.5 code with the v0.3 switches (`rails_yaw_enabled: false`, rate limits and caps 0, `walls_max_yaw: 0.035`, `floor_valid_margin: 60`, verification / retro / accumulation off, signatures 0, zone window 5, `confirm_time_s: 0`) | 785 / 155 (reviewer's run of 22.09: platform 212 / 20, `roundT_doubleT` 87 / 16, gate 94 / 15, `roundT_squareT` 0 / 0, switch 392 / 104) | 65/71, 8, 1 / 0 | only the curvature fix and the rail profile in curve coordinates remain: this is what the axis bug alone cost |
| **v0.5 first cut (the code the ablations were run on)** | **89 / 29** | **66/71, 7, 3 / 0** | |
| **v0.5 final defaults** (review tweaks: `wall_face_min_height` 2.0, `floating_max_height` 1.2, `walls_max_yaw` 0.09) | **96 / 32** | **66/71, 7, 3 / 0** | +7 frames / +3 events for keeping a person on a platform edge an obstacle |
| − axis levers (rail yaw, rate limits, side caps off, yaw clip 2°) | 171 / 56 (gate 57 / 8, switch 89 / 41) | 62/71, 11, 2 / 0 | |
| − infrastructure signatures (column, elevated, floating, edge, wall face = 0) | 513 / 62 (switch 374 / 37, `roundT_doubleT` 36 / 6) | 66/71, 7, 3 / 0 | |
| − height-reference margin (`floor_valid_margin: 60`) | 391 / 46 (switch 353 / 33) | 66/71, 7, 3 / 0 | |
| − history rules (`min_hit_fraction: 0`, zone window 5 / 0.5) | 143 / 44 | 68/71, 5, 1 / 0 | |
| − accumulation (`accumulation.enabled: false`, estimator off) | 89 / 29 (identical: without a given speed nothing is merged in the offline runs) | 66/71, 7, 3 / 0 | |
| + `confirm_time_s: 0.5` (5 frames at 10 Hz) | 69 / 21 | 66/71, 7, 3 / 0 | latency 0.5 s = 11 m at 80 km/h instead of 0.3 s = 6.7 m; not shipped: P4's tests pin the 3-frame confirmation (`tests/test_cli.py --repeat 3`, `tests/test_core.py` 4-frame loops) |
| + edge margin 0.05 m + 0.20 m per 100 m | not run | not run | |
| + edge margin 0.15 m per 100 m only | not run | not run | |
| + `confirm_time_s: 0.5` and edge margin 0.05 + 0.20 / 100 m | not run | not run | |

Reading (captain's runs of 22.09 on the six cached bags, every frame, commit 9b56bdf with one
lever group switched off per row by `--config`): the two levers that matter most are the
**infrastructure signatures** (without them 513 alarm frames — the platform-hall end wall, roof
strips and posts of the stopped train come back, 374 frames in the switch bag alone) and the
**height-reference range** (391 frames: the unverified extrapolation lifts far rails and pulls
the roof into the polygon exactly as §1b finding 2 describes). The **axis levers** cut 171 → 89 (first cut)
and, on the person, bring the first alarm from frame 11 to 7 (the rail-slab yaw keeps the person inside
the gauge as soon as they are). The **history rules** trade 54 alarm frames for two frames of person
recall and a first alarm two frames earlier (68/71, frame 5 without them). A **0.5 s
confirmation** (`tracking.confirm_time_s: 0.5`) removes another 20 frames / 8 events at no cost
on the person (he is confirmed at frame 7 either way, 0.5 s after entering the gauge) and is the
first knob to turn if the control bag shows more short-lived false alarms; it stays at 0.3 s so
that the 3-frame confirmation the synthetic tests and the dry-run checker assume keeps holding.
The accumulation row is identical to the defaults because the offline runs have no train speed
and nothing is merged; the given-speed behaviour is measured in §2c. The edge-margin variants
were not run.

**Accumulation default.** The multi-frame accumulation stays in the code and stays *enabled for a given speed* (the node's `ego_speed_mps` / odometry, `eval` sequences; P4's CLI tests pin this path), but the LiDAR-only estimator that fed it in v0.4 is **off by default** (`accumulation.estimate_speed: false`): with the estimator on, the same code alarmed on 119 frames / 30 events of the five empty bags instead of 88 / 27 (pre-vectorisation copy of the code; the final code measures 89 / 29, `roundT_pressureGate_roundT` 8 → 31 frames, `roundT_squareT_pressureGate_squareT` 5 → 20), it did not change the person's recall or first alarm on `doubleT_obstacle` (66/71, frame 7, with the stopped-train guard), and it costs 7–8 ms per frame; the final-code number is in the ablation row above. The synthetic gain of §2b (person 189 vs 178 m on the tunnel at 22 m/s) is real but has no real-data counterpart yet (no moving bag with an obstacle); with a given speed the given-speed rows of §2c and the given-speed runs of the ablation table are the measured behaviour. Regression rule of EVALUATION.md §3.6: false-alarm frames on E 1 001 → 96 and p95 latency (§3: 51 vs 71 ms on `roundT_doubleT`, 60 vs 76 ms on `doubleT_obstacle`, back to back) are both better than v0.3; on R the first alarm frame is 7 (≤ 9) and the recall 66/71 (≥ 64/71).

## 1c. v0.5 on the organizers' extended recording (22.09, unlabelled, every frame)

The 20-minute bag `new_data` (221 split files, 11 271 frames, seven stops, top speed 77 km/h,
tunnels / curves / stations / a switch; `DATASET.md` "Extended dataset") streamed once through
the v0.5 defaults, a fresh detector per 51-frame file, no speed given. No labels exist, so
these are false-alarm numbers on a ride, not recall:

| recording | frames | alarm frames | alarm events | events / hour | events / km | latency mean / p95 / max |
|---|---|---|---|---|---|---|
| `new_data` (1 200 s, ≈ 13 km) | 11 271 | 358 (3.2 %) | 102 | 306 | 7.9 | 41 / 74 / 157 ms |
| five obstacle-free organizer bags (230 s, §1) | 2 287 | 96 (4.2 %) | 32 | ≈ 500 | — | see §3 |

Causes, by the median lateral offset of the 102 events (per-event rows in
`extended_dataset_intake.json`): 40 at the left gauge edge (contact-rail side, brackets 0.6 m
above the rail head flipping into the gauge at 40–100 m), 16 at the right edge (column row in
double-track sections), 28 central — 11 of them in the five files where the track model is not
locked (a switch, platform ends) and 17 with ≤ 15 points at 60–140 m — and 18 in between. The
biggest single family is therefore the left edge (the mirror image of the column-row family of
§1b), the second the unlocked track model at stations and switches; both are on P3's list in
`DATASET.md` "What follows". The tracker's measured-interval gate (§1b review fix) is exercised
for real here: the last third of the recording has holes of 1.2–7.1 s between frames.

## 1d. v0.6 on all real data: the variants that led to the defaults

Every row is a full run over the 13 759 frames (`scripts/eval_real.py`, ~14 min each); the
five-bag column sums `doubleT_platform`, `roundT_doubleT`, `roundT_pressureGate_roundT`,
`roundT_squareT_pressureGate_squareT`, `squareT_platform_squareT_switch`.

| run | what changed | five bags: frames / events | ride: frames / events | person (61) | object on the rail (185) |
|---|---|---|---|---|---|
| v0.5 logic | — | 116 / 32 | 448 / 93 | 61, first 8 | 24 |
| v0.6a | envelope 2.1 × 3.0 m, calibration, health, **low-object stage reporting every bump above the bed** | 1 310 / 256 | 6 391 / **1 482** | 54 | 26 |
| v0.6b | + a low object must reach 5 cm below the rail head | 528 / 99 | 1 502 / 345 | 61 | 102 |
| v0.6c | low stage off; far-field rule, near-axis tall objects allowed | 393 / 49 | 857 / 121 | 61 | 25 |
| v0.6d | + columns ≥ 0.25 m wide demoted anywhere, `edge` at 1.0 m, edge margin 0.15 m / 100 m, far clusters ≤ 3 m long and grounded; low stage with candidates ≥ 3 cm above the rail head | 81 / 21 | 239 / 60 | 58, first 11 | 29 |
| v0.6f | low stage: the cluster's top at the rail head, candidates from 5 cm excess, own clustering radius | 412 / 169 | 1 735 / 734 | 58 | **170** |
| v0.6g | low stage: every candidate ≥ 3 cm above the rail head again | 85 / 27 | 272 / 88 | 58 | 29 |
| v0.6 (h) | + a low object needs 5 hits (0.5 s) | 83 / 25 | 258 / 74 | 58, first 11 | 27 |
| **v0.6.1 (shipped)** | mount tilt over 20 s instead of 5 frames, median drift monitor (§6) — the detection logic of v0.6h | **104 / 30** | **289 / 82** | **58, first 11** | 27 |

**The bed is full of objects.** v0.6a reported every bump more than 7 cm above the learned bed
cross-section inside the envelope: 1 350 of the ride's 1 482 events were low-object events. The ones looked at
(`new_data_46` frames 26–39, a straight section at 20 m/s): 0.3 m wide, 5–12 cm tall bumps in the
middle of the track approaching at the train's speed (train-control inductors, drain covers),
0.6–1 m wide transverse ones (cable crossings), all with their top 15–30 cm *below the rail
head*. Geometrically a 30 × 30 × 10 cm box lying on the bed is the same thing. The train
envelope starts at the rail head, so such an object is below it; v0.6 reports low objects that
reach the rail-head plane.

**The rail area is full of objects too.** v0.6f let a cluster through when its top reached the
rail head (candidates from 5 cm above the bed): 734 events on the ride, at \|lateral\| 0.5–0.9 m —
the rails and just inside them (guard rails in curves, joints, fastenings), 3–43 m away, tops
1–8 cm above the rail head (median 3 cm), excess over the bed 0.14 m median; no single-frame
threshold on height, width, excess or voxel count separates them (measured on 1 330 false clusters of 12 ride files vs 125 clusters of the
object). v0.6f finds the object in 170 of 185 frames and would stop the train every 1.6 s.
Shipped: every low candidate must be ≥ 3 cm above the rail head and the object must be seen in
5 frames (the false clusters flicker for 2 frames median, 3 at the 90th percentile): 18 low
events on the ride, a 10 cm box lying on a rail head found at 10–25 m (synthetic tunnel), the
real object in 2–4 of the 126 frames after the person leaves it. `lowobj.min_point_top: -1` with
`min_top: 0` restores the v0.6f behaviour for a line known to be clean.

**Why the real object is missed — corrected 23.09** (a jury-style review questioned the height,
and we re-measured it on the frames with the final v0.6.1 calibration): the object's top is
**0.10–0.15 m (median 0.13 m) above the detector's rail-head plane** in the 111 frames after the
person leaves — at the 0.12 m floor of the envelope, not "4–5 cm above its rail" as written here
before (that figure was taken against the rail ridge, ~6 points at 56 m, and is not confirmed).
What the pipeline produces at its position: **nothing in 99 of the 111 frames** — 0–3 points
above the envelope floor, below the main stage's cluster minimum — and a 3-point low-object
sliver 0.03–0.07 m high in 12 frames, too few hits to confirm. The object falls *between* the two
stages; clustering an object that straddles the envelope floor as one object is the fix to try
next (SCORECARD.md "What is left").

**Mount roll changes what "on the rail" means.** The rail pair of `doubleT_obstacle` has its
right head 8 cm above the left over 4–30 m on a straight, stationary track: that rig is rolled
by 3.0–3.2°. Without the correction (v0.5) the object reads 0.15–0.2 m above the *mean* rail
level and the corridor stage saw its top; with it, it is 0.10–0.15 m above the rail-head plane,
at the envelope floor, where it falls between the stages (above). The calibration is right (the
gauge is defined in the rail plane); the
organizers said the hidden data use the mount of the empty-tunnel rides, on which the
calibration finds `roundT_doubleT` and `doubleT_platform` level within 0.5° (v0.6.1, §6; the −1.0…−1.6° v0.6 measured on `roundT_doubleT` was the 5-frame window).

**Where the ride's remaining events come from** (the v0.6h run, 74 events; `scripts/mine_objects.py`, classes by
median geometry, `labels/new_data_objects.json`): corridor-edge structures 21 (at \|lateral\|
0.9–1.2 m, 30–70 m; a quarter of them at the station of files 52–55), station / platform-end
structures 13, low objects 12 (+6 low tracks classed otherwise), far small clusters 11
(105–180 m, 8–12 points), hanging equipment 8 (1.5–2.7 m above the rail head, 50–80 m), tall
structures 7, person-like 2 (both infrastructure, below). 874 tracks were confirmed on the
ride in total, 800 of them advisory (mostly the edge structures). The 11 person-like tracks
were checked by eye on close-ups (`img/new_data_person_like_check.png`): poles from the bed to
the vault, cabinets, signs, the wall of the R ≈ 350 m curve — no person anywhere near the
track, as the organizers said.

**Per bag (v0.6.1):** `doubleT_platform` 5 / 6 (low objects at the platform, 4 events),
`roundT_doubleT` 3 / 2, `roundT_pressureGate_roundT` 2 / 1, `roundT_squareT_pressureGate_squareT`
0 / 0, `squareT_platform_squareT_switch` 94 / 21 (v0.6: 75 / 17 with a spurious −0.69° pitch) —
the platform-end structure at 82–84 m while the train stands at the platform (§1), unchanged
since v0.5: the station-curvature limitation of ALGORITHM.md §6.

## 2. Synthetic obstacles injected into real empty frames (`resense inject` / `resense eval`)

### 2a. Day-1 numbers (v0.3, 26 frames of `roundT_doubleT`, every 10th, synthetic objects)

One object per frame (person 0.5×1.7 m, box 0.5 m, plank 2×0.25×0.3 m), uniformly 10–220 m,
20 % placed outside the gauge as negatives; objects whose rays are all occluded by real
geometry (7 of 26) excluded. Recall v0.3: 0–50 m 3/3, 50–100 m 1/2, 100–150 m 0/5,
150–200 m 0/3, 200–300 m 0/3. First-detection distances: person 13.7 / 19.5 / 23.2 m (placed
there), box 53.7 m. Ray-cast point budget (single frame): person 24 pts @80 m, 10 pts @110 m,
3–5 pts @150–190 m, 0–1 @>200 m — consistent with the analytic estimate in DATASET.md.
Synthetic-tunnel unit tests (`tests/`): box 0.6 m detected at 30 and 80 m, person at 150 m, no
alarm on the clear tunnel, object 2.3 m off-axis not alarmed, occlusion of the background
verified.

### 2b. Multi-frame accumulation on the synthetic tunnel (v0.4, 21.09) — synthetic

**Every number in this section is synthetic** (`resense.synthetic.synthetic_tunnel_frame`, a
featureless round tunnel with benches at 1.95 m; `tests/test_algorithm.py`), 4-core sandbox.
The approach of a train at 22 m/s is emulated by injecting the object at 200, 197.8, … m
(2.2 m per 10 Hz frame) into the *same* background frame; the sequences use
`dropout_start=60, dropout_full=200`, which reproduces the real-frame budget (person 2–5
returns at 185–200 m; box 0.5 m: 4–6 at 100–130 m).

| object, sequence (given ego speed 22 m/s) | first confirmed alarm, v0.3 (base commit) | v0.4, accumulation off | v0.4, accumulation on (5 frames) |
|---|---|---|---|
| person 0.4×0.5×1.7 m from 200 m, 6 seeds | 162.6 m (corridor validity) | 167–189 m, median 178 m, frames 5–15 | **189–191 m in 6/6 seeds**, frames 4–5 |
| box 0.5 m from 140 m, 4 seeds | 114.6 m | 89–116 m (one seed collapses to 89 m) | **113.6–115.8 m in 4/4 seeds** |

What limited v0.3 at range on the synthetic tunnel was the corridor validity (bed fit to
107.5 m + 60 m), not the point count; the verified extrapolation (ALGORITHM.md §3.1) reaches
195 m there. The 0.5 m box does not gain range from accumulation (beyond ~118 m it is sampled
by a single ring). Ego-speed estimator on synthetic texture: 22.0 m/s ± 2 with posts on the
walls, "unknown" on a stopped train and on the featureless tunnel. Retro-reflector rule: sign
plate 0.05×0.6×0.8 m with reflectivity 220 → advisory, the same plate matte → obstacle, person
15 / 60 / 200 → obstacle, 1 m crate 220 → obstacle, 0.5 m box 220 → advisory (documented
choice). The independent review of v0.4 on real data (every frame, no speed given) found the
stopped-train merge smearing the crossing person laterally (width 1.06 vs 0.57 m), the
verified corridor promoting phantoms at 135–142 m, +17–23 ms per real frame, and the retro
rule never firing on the six bags (intensity ≥ 100 on < 1 % of the returns); all four are
addressed in v0.5 (§1b, §3) and the estimator's real-bag behaviour is in §2c.

### 2c. Recall by range on real backgrounds (set S, v0.5, 21.09) — synthetic objects, real frames

Sets built this round with the merged `resense inject` (commit 9b56bdf (merged as 82815e9); objects are placed
on the per-frame track model of *this* code, so the frames differ slightly from P4's sets of
f4e311f): the two static sets `S_roundT_doubleT` (26 frames) and
`S_roundT_pressureGate_roundT` (27), every 10th frame, one catalogue object per frame
(`person, box0.5, box1.0, plank, trolley`), 10–250 m, 20 % negatives, `--seed 1`, evaluated
with `resense eval --repeat 3`; and six approach sequences (`--sequence 8 --speed 15`, seeds
1–3 on both bags, 208–215 frames each, one random kind per background). Two protocol facts
decide how the far bins can be read:

* **Sightline.** Both bags are curves: from the v0.5 axes the inner wall (2.2 m from the
  axis) hides the track beyond √(2·R·2.2 m) ≈ 88 m (median frame of
  `roundT_pressureGate_roundT`, R = 1.8 km) and 124 m (`roundT_doubleT`, R = 3.5 km); only
  93 / 268 and 119 / 252 frames see further than 150 m. Nothing placed beyond the sightline
  can be detected by any sensor.
* **Placement.** The injector stands objects on the per-frame extrapolated bed, which beyond
  the fit (48–100 m in these frames) swings between +1.4 and −3.3 m at 100–250 m
  (`S_roundT_doubleT` rows at 133, 230, 102 m); combined with the sightline this leaves
  **11 of the 22 in-gauge objects of each static set fully occluded (all beyond 80 m)** and
  436 of the 1 269 sequence rows; they are excluded from recall and counted here. The far
  bins therefore hold 3–7 visible objects per set and measure the injector as much as the
  detector (§5: placement on the local bed).

**Static sets (53 frames, 26 in-gauge visible objects; recall = matched / visible in-gauge
objects, counts per bin):**

| config | 0–50 m | 50–100 m | 100–150 m | 150–200 m | 200–300 m | all | first detection (max) | fp events |
|---|---|---|---|---|---|---|---|---|
| v0.5 code with the v0.3 switches | 5/7 | 4/9 | 0/3 | 0/4 | 0/3 | 9/26 | person 42.6, box1.0 84.8, trolley 84.2, plank 14.6 m | 16 |
| **v0.5 defaults** | 5/7 | 3/9 | 0/3 | 0/4 | 0/3 | 8/26 | the same; trolley 50–100 m 1/3 instead of 2/3 | 11 |
| v0.5 defaults + retro rule on | 5/7 | 3/9 | 0/3 | 0/4 | 0/3 | 8/26 | identical to the defaults (no object of these sets is retro-reflective) | 11 |

Per kind (defaults): person 3/4 (the miss is at 158 m), box0.5 0/4 (46.8, 76, 102 m and one
beyond: the 0.5 m box at 46.8 m sits next to a column in the double-track section and merges
with it at that range), box1.0 3/7, plank 1/5, trolley 1/6. The static sets are too small to
separate the two configs (one object per cell); the sequences below carry the numbers.

**Approach sequences (six sets, 1 269 frames, 692 visible in-gauge object-frames; the
detector is reset at every background change — a train cannot jump between the 26
backgrounds of a set, and the smoothed, rate-limited axis of v0.5 needs 3–5 frames after such
a jump, which the plain `resense eval` does not give it; recall per bin = matched
object-frames / visible object-frames, "first detection" = the largest range at which a label
was matched, max and median over the labels of the kind):**

| config (all kinds) | 0–50 m | 50–100 m | 100–150 m | 150–200 m | 200–300 m | all | fp events / fp frames |
|---|---|---|---|---|---|---|---|
| v0.5 code with the v0.3 switches | 69/156 | 87/211 | 10/159 | 0/126 | 0/40 | 166/692 | 4 / 94 |
| **v0.5 defaults, no speed given** (single frame; with the estimator on it reports 473 "estimated" frames, all below 1 m/s because the background does not move, so nothing is merged either way — identical numbers) | 84/156 | 86/211 | 1/159 | 0/126 | 0/40 | **171/692** | 1 / 35 |
| v0.5 defaults, speed 15 m/s given (5-frame merge beyond 40 m; the background of these sets does *not* move, so the merged background is smeared by 1.5 m per frame — an artefact that works against accumulation) | 79/156 | 81/211 | 1/159 | 0/126 | 0/40 | 161/692 | 1 / 12 |
| v0.5 defaults + retro rule on, speed given | 73/156 | 81/211 | 1/159 | 0/126 | 0/40 | 155/692 | 1 / 12 |

Per kind, v0.5 defaults without a speed (matched / visible object-frames; first detection =
max / median over the labels of the kind, n labels ever matched):

| kind | 0–50 m | 50–100 m | 100–150 m | 150–200 m | 200–300 m | first detection (m) | v0.3-switch first detection (m) |
|---|---|---|---|---|---|---|---|
| person 0.4×0.5×1.7 m | 28/37 | 38/68 | 1/30 | 0/21 | 0/9 | 104.9 / 56.7 (11) | 104.9 / 70.7 (10) |
| box 0.5 m | 15/21 | 4/11 | 0/20 | 0/35 | 0/15 | 57.6 / 49.1 (4) | 57.6 / 49.1 (3) |
| box 1.0 m | 23/29 | 23/59 | 0/38 | 0/1 | — | 81.8 / 55.0 (8) | 89.6 / 55.0 (8) |
| plank 2×0.25×0.3 m | 0/45 | 3/40 | 0/14 | 0/16 | 0/6 | 86.3 (1) | — (0) |
| trolley 0.6×0.6×1.0 m | 18/24 | 18/33 | 0/57 | 0/53 | 0/10 | 78.7 / 71.9 (5) | 149.5 / 88.6 (6) |

Reading. (1) Up to 100 m the v0.5 defaults match or beat the v0.3 switches (0–50 m 84 vs
69 object-frames, 50–100 m 86 vs 87) with a quarter of the false-alarm events (1 vs 4) and a
third of the false-alarm frames (35 vs 94). (2) The 100–150 m bin loses 9 of its 10 v0.3
object-frames (a trolley matched at 149.5 m and persons at 100–105 m): the shorter trusted
height-reference range (fit + 20 m or verified) and the axis caps demote far clusters to
advisory — the price of the 503-frame cause of §1b; which lever costs what is measured in the
ablation rows of §1b (sequence runs with `floor_valid_margin: 60` and the axis levers off are
in `evalC/seq_reset2` of the run directory, quoted in §5). (3) Beyond 150 m nothing is
matched by any config: of the 126 + 40 object-frames there, 436 rows of the sets are fully
occluded (sightline, placement) and the visible ones return 1–5 points, below the 3-voxel
floor. (4) The given-speed merge costs 10 object-frames on these sets and removes 23
false-alarm frames; both effects are within what the static-background artefact can produce,
so the sequences do not decide the accumulation question — the real bags do (§1b). (5) The
retro rule costs 6 trolley frames (catalogue reflectivity 40–120 %) and gains nothing here or
on the bags: off by default. (6) The plank of the spec stays invisible by design (0/121
object-frames; the low-hardware rule, ALGORITHM.md §6.6), except three frames at 86 m where
the axis error lifted it.

The `person` first detection of 104.9 m and the `box1.0` 81.8 m are the honest single-frame
ranges on these two curved bags; the Sprint 2 targets (person ≥ 150 m, box ≥ 100 m) hold on
the synthetic tunnel only (§2b) and are not met on real backgrounds by any configuration
measured this round.

## 2d. The far field and long range on a moving background (set F, v0.6 – v0.6.2)

**What a straight tunnel returns far away** (`new_data_46`, 20 m/s, R > 100 km): of ~188 000
points per frame, 422 lie 100–125 m ahead, 217 at 125–150 m, 73 at 150–175 m and 56 at
175–215 m; no return of any frame of any recording lies beyond 210 m (every recording stops at 209.2–210.0 m: a cut-off of the sensor, not a gradual fade). Beyond ~100 m the bed does
not return (grazing incidence); only the vault (4.4–4.7 m above the rail head) and the walls at
±2 m do. **The extrapolated height reference drifts**: relative to the vault measured at 20–60 m,
the vault seen through the model is +0.07 m at 65 m, +0.15 at 85 m, +0.24 at 95 m, +0.49 at 115 m
and +0.79 at 135 m (file 46); +0.10 at 85 m, +0.25 at 115 m, +0.40 at 155 m, +0.5 at 175–195 m
(file 98) — the model's rail level runs low by that much (a vertical curve ahead, or the
extrapolated slope). The lateral residual of the walls is ±0.3 m. That is why the corridor was
trusted only to the bed fit + 20 m or the side-base verification (100–130 m), and why v0.6
extends the alarm range for **tall, grounded, short** clusters only (ALGORITHM.md §3.3c): a 0.5 m
error does not move a 1.7 m person out of a 3 m envelope, but it does lift flat far-bed returns
into its bottom. A lining-anchored far reference (correct the model by the vault drift) is
measurable to ~200 m and is the next step (not in v0.6: the lateral residuals are too noisy to
anchor the axis).

**Set F** (`scripts/far_range_eval.py`): an object is placed at a fixed point of the tunnel
220 m ahead of 110 consecutive frames of the ride and ray-cast into every frame at the distance
it has then (the train speed of the ride from the static-track drift of each split file, the bag
frame intervals); it stands on the bed measured under it where the bed returns, else on the
model's rail level corrected by the vault drift above; laterally uniform in ±0.6 m; dropout
from 60 m to 200 m scaled by reflectivity (the real-frame budget, §2b). A fresh detector per
sequence, **no speed given** (single-frame pipeline + persistence). A frame is a hit when a
confirmed gauge detection lies within max(2 m, 3 %) and 1.2 m laterally of the object.

**Round 3 (v0.6.3, the current code, 24.09)** — the same sets re-run on the shipped code
(raw summaries with the per-approach band ranges:
[`experiments_2026-09-24_remeasure.json`](experiments_2026-09-24_remeasure.json)). Round 2 below
was measured on v0.6.2 and never repeated after v0.6.3's hold over one missed frame
(`tracking.hold_misses` 1): with the hold switched off, the current code reproduces round 2's
straight set value for value, so every difference between the two tables is the hold. First
confirmations do not change (the hold neither creates nor confirms a track); the held ranges and
the frame recall rise where a single missed frame used to break a run, and so do the confirmed
detections away from the object (a held false detection counts once more). Placements are those
of round 2 (same files, start, lateral range, seed) except where marked: the envelope-edge set and
the rail-head and lying-on-the-rails sets of round 2 were drawn with parameters that the stored
summaries do not fully record, so these rows are new draws of the same scenario.

| set | object | detected | first confirmed, median (range) | sustained ≥ 90 %, median (range) | every 10 m band ≥ 90 %, median (per approach) | frame recall 0–50 / 50–100 / 100–150 / 150–200 m | confirmed detections away from the object |
|---|---|---|---|---|---|---|---|
| straight, \|lateral\| ≤ 0.6 m | person 0.4 × 0.5 × 1.7 m | 6 / 6 | 148 m (110–169) | 149 m (92–177) | 115 m (20–160) | 96 / 94 / 68 / 9 % | 9 |
|  | trolley 0.6 × 1.0 m | 6 / 6 | 144 m (85–154) | 115 m (22–129) | 70 m (20–110) | 96 / 90 / 29 / 3 % | 25 |
|  | crate 1.0 m | 6 / 6 | 111 m (79–156) | 119 m (22–129) | 105 m (20–110) | 96 / 92 / 28 / 1 % | 6 |
|  | cable 3 cm hanging to 1.0 m above the rail head | 6 / 6 | 95 m (13–108) | 53 m (19–98, 4 of 6) | 20 m (10–40) | 74 / 59 / 6 / 0 % | 4 |
|  | box 0.5 m in the bed | 1 / 6 | 52 m | 56 m, 1 of 6 | 50 m (50–50, 1 of 6) | 16 / 2 / 0 / 0 % | 2 |
| same, **train speed given** (5-frame accumulation) | person | 6 / 6 | 167 m (143–188) | 151 m (22–195) | 105 m (20–170) | 96 / 83 / 62 / 36 % | 6 |
|  | trolley | 6 / 6 | 175 m (110–194) | 122 m (22–186) | 110 m (20–160) | 96 / 84 / 44 / 44 % | 2 |
|  | crate 1.0 m | 6 / 6 | 182 m (142–201) | 79 m (22–174) | 70 m (10–120) | 95 / 73 / 58 / 41 % | 7 |
| to the envelope edge, \|lateral\| ≤ 1.0 m (new random placements) | person | 6 / 6 | 136 m (87–155) | 120 m (22–170) | 95 m (20–150) | 96 / 92 / 64 / 3 % | 6 |
|  | crate 1.0 m | 6 / 6 | 108 m (77–152) | 108 m (22–127) | 95 m (20–110) | 96 / 89 / 16 / 1 % | 9 |
|  | trolley | 6 / 6 | 122 m (96–151) | 109 m (22–120) | 95 m (20–110) | 96 / 90 / 21 / 1 % | 9 |
|  | cable hanging to 0.2 m above the rail head | 3 / 6 | 136 m (136–138) | 39 m (35–44, 2 of 6) | 30 m (10–40, 3 of 6) | 34 / 39 / 33 / 0 % | 4 |
| curves R ≈ 350 m (7 approaches) | person | 6 / 7 | 78 m (58–86) | 85 m (61–94, 6 of 7) | 75 m (50–80, 6 of 7) | 100 / 50 / 0 / 0 % | 0 |
|  | crate 1.0 m | 6 / 7 | 68 m (47–89) | 68 m (50–95, 4 of 7) | 60 m (40–70, 4 of 7) | 89 / 35 / 0 / 0 % | 8 |
|  | trolley | 6 / 7 | 68 m (51–89) | 72 m (24–97, 6 of 7) | 65 m (20–90, 6 of 7) | 92 / 39 / 0 / 0 % | 11 |
| station stops (6) | person | 6 / 6 | 113 m (89–144) | 122 m (78–127, 5 of 6) | 75 m (10–120) | 93 / 87 / 30 / 0 % | 111 |
|  | crate 1.0 m | 6 / 6 | 102 m (79–144) | 97 m (83–103, 3 of 6) | 60 m (10–90, 4 of 6) | 79 / 77 / 10 / 0 % | 91 |
|  | dog-sized box 0.6 × 0.3 × 0.45 m on the bed | 1 / 6 | 41 m | — | — | 3 / 0 / 0 / 0 % | 81 |
| small objects on a rail head (start 150 m) | 0.3 × 0.3 × 0.1 m | 6 / 6 | 42 m (28–46) | 45 m (30–50) | 40 m (20–40) | 79 / 0 / 0 % | 4 |
|  | 0.3 m cube | 6 / 6 | 49 m (44–64) | 53 m (46–70) | 45 m (40–60) | 95 / 10 / 0 % | 0 |
| across a rail (replica of the organizers' object, 0.4 × 0.6 × 0.31 m) |  | 5 / 6 | 46 m (24–50) | 40 m (26–50, 4 of 6) | 30 m (10–40, 5 of 6) | 52 / 1 / 0 % | 4 |
| on the bed between the rails | 0.3 × 0.3 × 0.1 m | 0 / 6 | — | — | — | 0 / 0 % | 6 |
|  | 0.3 m cube | 1 / 6 | 9 m | — | 10 m (10–10, 1 of 6) | 1 / 0 % | 0 |
|  | dog-sized 0.6 × 0.3 × 0.45 m | 1 / 6 | 50 m | 50 m, 1 of 6 | 40 m (40–40, 1 of 6) | 15 / 1 % | 2 |
| person lying, 0.5 × 1.8 × 0.35 m | across the rails, on the rail heads (start 150 m) | 6 / 6 | 64 m (54–112) | 68 m (58–83) | 60 m (40–70) | 99 / 30 / 1 % | 10 |
|  | on the measured (deep) bed, across | 0 / 6 | — | — | — | 0 % | 0 |
|  | same, along | 0 / 6 | — | — | — | 0 % | 0 |
|  | shallow bed, top 0.15 m above the rail head, across | 6 / 6 | 49 m (47–52) | 53 m (50–56) | 50 m (40–50) | 99 % | 0 |
|  | same, along | 6 / 6 | 50 m (48–52) | 54 m (52–56) | 50 m (50–50) | 100 % | 0 |
|  | top 0.10 m above the rail head, across | 6 / 6 | 42 m (30–47) | 46 m (32–50) | 40 m (30–40) | 82 % | 0 |
|  | same, along | 6 / 6 | 46 m (42–50) | 48 m (45–54) | 40 m (40–50, 4 of 6) | 91 % | 0 |
|  | top 0.05 m above the rail head, across | 6 / 6 | 17 m (10–24) | 17 m (16–25, 5 of 6) | 10 m (10–20) | 25 % | 0 |
|  | same, along | 6 / 6 | 29 m (11–43) | 39 m (22–47, 4 of 6) | 25 m (10–40) | 50 % | 0 |

Reading (what differs from round 2). A person on straight track: first confirmed at **148 m**
(unchanged), held in ≥ 90 % of the frames from **149 m** (round 2: 135 m; the approach through the
3.4 s recording hole of `new_data_169` no longer collapses to 22 m) and in every 10 m band from
**115 m** (unchanged; per approach 20–160 m). With a train speed the crate is held from 79 m
(round 2: 89 m, 5 of 6 approaches; now 6 of 6). At station stops the crate is held from 97 m
(round 2: 80 m), and the confirmed detections away from the objects rise from 75 / 58 / 51 to
111 / 91 / 81 (the stations' own false alarms, held). Small objects on a rail head: first at
42 m (the 10 cm box) and 49 m (the 30 cm cube), held from 45 m and 53 m.

**Round 2 (v0.6.2, 23.09)** — what the criteria review asked for: small objects, objects on
a rail head, lateral positions to the envelope edge, 7 approaches in curves and 6 at station
stops, and the **sustained range** next to the first hit: the largest distance D from which the
object is detected in ≥ 90 % of the frames in which it returns a point, all the way in (≥ 5
frames) — a lenient measure: the misses may bunch at its far end. The strict one next to it:
every 10 m band from the train out to D detected in ≥ 90 % of its frames (straight, median of
6: person **115 m**, crate 95 m, trolley 70 m; with a train speed person 105 m, crate 70 m,
trolley 110 m). The v0.6.2 configuration (0.5 s confirmation), no speed given unless said; 6 sequences
per object unless said; raw summaries in
[`experiments_v0.6.2_setF.json`](experiments_v0.6.2_setF.json).

| set | object | detected | first confirmed, median (per sequence) | sustained ≥ 90 %, median (per sequence) | frame recall 0–50 / 50–100 / 100–150 / 150–200 m |
|---|---|---|---|---|---|
| straight, \|lateral\| ≤ 0.6 m | person 0.4 × 0.5 × 1.7 m | 6 / 6 | **148 m** (110, 146, 146, 149, 162, 169) | **135 m** (22, 92, 120, 150, 162, 176) | 96 / 94 / 67 / 7 % |
| | trolley 0.6 × 1.0 m | 6 / 6 | 144 m (85–154) | 115 m (22–118) | 96 / 88 / 27 / 3 % |
| | crate 1.0 m | 6 / 6 | 111 m (79–156) | 117 m (22–129) | 96 / 92 / 26 / 1 % |
| | cable 3 cm hanging to 1.0 m above the rail head | 6 / 6 | 95 m (13–108) | 53 m (19–98, 4 of 6) | 74 / 59 / 6 / 0 % |
| | box 0.5 m in the bed | 1 / 6 | 52 m | 56 m | 16 / 2 / 0 / 0 % |
| same, **train speed given** (5-frame accumulation) | person | 6 / 6 | **167 m** (143–188) | 151 m (22–190) | 96 / 83 / 58 / 34 % |
| | trolley | 6 / 6 | 175 m (110–194) | 122 m (22–186) | 96 / 84 / 41 / 42 % |
| | crate 1.0 m | 6 / 6 | 182 m (142–201) | 89 m (22–170, 5 of 6) | 94 / 71 / 55 / 38 % |
| to the envelope edge, \|lateral\| ≤ 1.0 m | person | 6 / 6 | 138 m (108–161) | 115 m (16–164) | 94 / 91 / 56 / 3 % |
| | crate 1.0 m | 6 / 6 | 116 m (83–151) | 118 m (22–129) | 95 / 91 / 22 / 1 % |
| | trolley | 6 / 6 | 116 m (101–157) | 95 m (22–120, 4 of 6) | 85 / 83 / 24 / 1 % |
| | cable hanging to 0.2 m above the rail head | 3 / 6 | 132 m (108–135) | 64 m (1 of 6) | 24 / 18 / 13 / 0 % |
| curves R ≈ 350 m (7 approaches) | person | **6 / 7** | 78 m (58–86) | 85 m (61–94) | 100 / 50 / 0 / 0 % |
| | crate 1.0 m | 6 / 7 | 68 m (47–89) | 68 m (48–95, 4 of 7) | 87 / 35 / 0 / 0 % |
| | trolley | 6 / 7 | 68 m (51–89) | 73 m (24–97) | 92 / 39 / 0 / 0 % |
| station stops (6) | person | 6 / 6 | 113 m (89–144) | 122 m (77–127, 5 of 6) | 93 / 85 / 29 / 0 % |
| | crate 1.0 m | 6 / 6 | 102 m (79–144) | 80 m (61–94, 3 of 6) | 76 / 73 / 10 / 0 % |
| | dog-sized box 0.6 × 0.3 × 0.45 m on the bed | 1 / 6 | 41 m | — | 2 / 0 / 0 / 0 % |
| small objects on a rail head | 0.3 × 0.3 × 0.1 m | **6 / 6** | 42 m (41–48) | 45 m (33–48) | 84 / 0 / 0 % |
| | 0.3 m cube | **6 / 6** | 44 m (42–50) | 47 m (44–50) | 87 / 1 / 0 % |
| across a rail (replica of the organizers' object, 0.4 × 0.6 × 0.31 m) | | 5 / 6 | 46 m (24–50) | 32 m (26–50, 4 of 6) | 48 / 1 / 0 % |
| on the bed between the rails | 0.3 × 0.3 × 0.1 m | 0 / 6 | — | — | 0 % |
| | 0.3 m cube | 1 / 6 | 9 m | — | 1 % |
| | dog-sized 0.6 × 0.3 × 0.45 m | 1 / 6 | 50 m | 42 m | 13 / 1 % |
| person lying, 0.5 × 1.8 × 0.35 m (added 23.09 after the second review) | across the rails, on the rail heads | 6 / 6 | 61 m (50–111) | 65 m (54–68, 4 of 6) | 90 / 20 / 2 % |
| | in the central drainage trough (0.57–0.60 m below the rail head in these tunnels: the body stays below it) | 0–1 / 6 | — | — | 0 % |
| | on a shallow bed, top 0.15 m above the rail head, **across** the track: v0.6.2 → with the 2.2 m width cap | 2 / 6 → **6 / 6** | 41 → **49 m** (47–52) | — → **53 m** (50–56) | 3 → 98 % (0–50 m) |
| | same, **along** the track | 6 / 6 | 50 m (48–52) | 54 m (52–56) | 100 % (0–50 m) |
| | across, top 0.10 m / 0.05 m above the rail head (2.2 m cap) | 6 / 6, 6 / 6 | 42 m / 17 m | 43 m / 17 m (4 of 6) | 79 % / 24 % (0–50 m) |

Reading. (1) **A person on straight track is first confirmed at ~148 m, held in ≥ 90 % of the
frames from ~135 m and in every 10 m band from ~115 m** (medians of 6; runs of up to 7
consecutive missed frames occur inside the lenient range); v0.6.1 first hit 150 m — the 0.5 s
confirmation costs ~3 m there and ~10 m with a train speed (167 against 177 m). In one sequence
out of six both sustained measures collapse to ~20 m: the recording has a 3.4 s hole there
(`new_data_169`, frames 14 → 15), the object jumps ~65 m closer, the detector resets its scene
and needs 0.5 s to confirm again (a review found it; the sequence is kept as it is, a control
recording can have such holes too) — the first-hit median hides such dropouts,
which is why all three are reported.
(2) **Curves: 6 of 7 approaches** detected (round 1: 1 of 2), first at 58–86 m and sustained
from 61–94 m — the sightline past the inner wall of an R ≈ 350 m curve (≈ √(8·R·w) = 80–110 m).
(3) **Station stops**: a person 6 / 6 from 113 m; the stations carry the ride's own false alarms
(75, 58 and 51 confirmed detections away from the objects in these 18 sequences of ~110
frames — the platform-edge and platform-end structures of §0a). (4) **Small objects on a rail
head** — a 30 × 30 × 10 cm box and a 30 cm cube — are found in 6 of 6 approaches from 42–44 m
and held from 45–47 m; the replica of the organizers' object lying across a rail in 5 of 6, from
46 m. (5) **The same objects on the bed between the rails are below the envelope**: measured under
these placements (files 46–172, 20–50 m), the bed lies 0.26–0.34 m below the rail head half a metre
off the axis and the central drainage trough 0.57–0.60 m (the track model's `rail_offset`: 0.35–0.38 m),
so a 10 cm box, a 30 cm cube and even a 45 cm dog-sized box stay below the envelope floor (0.12 m
above the rail head) or barely reach the rail-head plane — not reported by the default policy (ALGORITHM.md §3.3b, §6),
which a line with a clean bed can switch (`lowobj.min_top: -1`, `min_point_top: -1`). An attempt
to exempt low clusters centred between the rails from the track-hardware rule changed nothing
(no candidate reaches the corridor) and was not kept. (6) **A person lying on the track** (the review's case, 0.5 × 1.8 × 0.35 m, placed by
`far_range_eval.py` with the bed depth fixed; shallow-bed runs with `local_bed_z` replaced by
"rail level − depth"): across the rail heads the corridor stage sees it (6 / 6, from ~60 m); on
these tunnels' deep bed the whole body is below the rail head and not reported (policy); where
the bed is shallow it straddles the envelope floor and the straddle stage finds it, across the
track only since the width cap follows the envelope (§0) — from ~50 m with its top 0.15 m above
the rail head, from ~17 m when only 5 cm of it rise above the rail head. No false detection in
these 60 sequences. A body lying across the track rests on the bed beside the trough, 0.26–0.34 m
below the rail head, so the 0.25 and 0.30 m rows are the realistic case in these tunnels: found in
6 of 6 approaches, but only from ~42 m (top 0.10 m) and ~17 m (top 0.05 m). (7) Off-axis objects to the envelope edge
lose ~10 m of first detection (the edge margin grows with range); a 3 cm cable near the edge is
found in 3 of 6.

**Round 1 (v0.6.1, 22.09).** Straight sections (files 46, 68, 98, 140, 168, 172; 17–21 m/s), v0.6.1:

| object | sequences detected | first confirmed detection: per sequence (m) | median | recall 0–50 / 50–100 / 100–150 / 150–200 / 200–250 m |
|---|---|---|---|---|
| person 0.4 × 0.5 × 1.7 m | 6 / 6 | 110, 146, 149, 152, 166, 169 | **150 m** | 97 % / 94 % / 68 % / 10 % / 0 % |
| trolley 0.6 × 1.0 m | 6 / 6 | 85, 142, 145, 146, 153, 171 | 146 m | 97 % / 88 % / 28 % / 3 % / 0 % |
| crate 1.0 m | 6 / 6 | 79, 108, 110, 112, 145, 156 | 111 m | 97 % / 92 % / 26 % / 1 % / 0 % |
| cable 3 cm hanging to 1.0 m above the rail head | 6 / 6 | 16, 59, 94, 96, 103, 112 | 95 m | 83 % / 63 % / 7 % / 0 % / 0 % |
| box 0.5 m standing in the bed | 2 / 6 | 52, 57 | 55 m | 15 % / 2 % / 0 % / 0 % / 0 % |

Curves (files 129 and 176, R ≈ 350 m): person first confirmed at 82 m and crate at 74 m in one
of the two sequences, nothing beyond ~100 m — the inner wall hides the track beyond
√(8·R·w) ≈ 80–110 m and the corridor is trusted only to 60–120 m there; the organizers accept
detection at the visible limit in a curve (Q&A fact 14).

Reading. (1) A person is confirmed at 146–169 m on straight track in 5 of 6 sequences with no
speed input; the 150–200 m bin holds 3–10 returns per frame and is where the single-frame
pipeline ends (10 % of those frames). (2) Beyond ~200 m nothing is detected, as the sensor
physics predicts: no return of the whole ride lies beyond 210 m. (3) A trolley is
confirmed at 85–171 m (median 146 m), a 1 m crate at 79–156 m (the crate is 1 m tall, closer to
`far_min_height` = 0.6 m after the far bed error than a person). (4) **A 0.5 m box standing in
the bed is borderline by construction**: beside the central drainage trough the bed lies
0.26–0.34 m below the rail head (round 2, reading 5), so the box top is 0.15–0.25 m above the rail head — at the envelope's
bottom (0.12 m) — and it is reported only in the frames where it reaches into the envelope
(2 of 6 sequences, 50–60 m); on a rail head the same box is found (the low-object stage,
`tests/test_envelope.py`). (5) A 3 cm cable hanging into the envelope is detected at 59–112 m
(the beam-footprint model of the injector, DATASET.md, makes it 5–11 cm wide at that range; a
real cable's echo strength is the open question). (6) **Confirmed gauge detections away from
the object: 39 of the 3 060 injected frames (1.3 %), none in the curves.** 10 are the object's
own cluster merged with bed returns in front of it and reported 3–7 m short (outside the
max(2 m, 3 %) match window: a localisation error, counted against us); 10 are the background's
own false alarms (the same start of file 98 run with *no* object confirms 6 frames of 2 m tall
fixtures at 134–158 m; files 68, 168 and 172 give none); 19 are a structure 30–65 m *beyond*
the object that alarms only with the object present (file 98 at 105–165 m, file 168 at 94 m).
Mechanism of those 19 (traced on file 98): where the real bed no longer returns (beyond ~90 m)
the base of the object fills a bed bin, the bed fit extends from ~80 to ~107 m, the wall band
above it shifts and the far curvature moves by ~2.5·10⁻⁵ m⁻¹ — 0.3 m at 150 m, enough to bring
an edge fixture inside the 0.15 m/100 m margin. The object itself is confirmed in the same
frames, so the train's decision (STOP at the object) does not change; a bed bin that is
narrower than the bed (an object, not the track) should not extend the fit — noted in
ALGORITHM.md §6. (7) **Sensitivity to the mount tilt.** The same set run with the v0.6
calibration (a 5-frame tilt frozen at the start of each sequence: up to ±1.6° of spurious roll
and ±0.4° of pitch on this level rig) gave a person median of 165 m, crate 127 m, trolley
121 m, box 0.5 m 4 / 6: far-field numbers move by ±15–30 m with a few tenths of a degree of
pitch (0.3° is 0.8 m of height at 150 m). The v0.6.1 numbers above are the ones with the
physically right (level) mount.

**What the far-field rule and a train speed add** (paired v0.6.1 runs of set F: the same 30
sequences, the same random draws; `far_range_eval.py --far-min-height 0` = the v0.5
behaviour, `--given-speed` = the ride's per-file train speed handed to the detector, which then
merges 5 frames beyond 40 m — what the node does when `speed_topic` / `odom_topic` /
`ego_speed_mps` is set):

| object (6 sequences each) | far rule off (v0.5) | **shipped, no speed** | shipped + speed given |
|---|---|---|---|
| person: first confirmed, median (range) | 106 m (83–110) | **150 m** (110–169) | **177 m** (150–192) |
| trolley | 105 m (85–110) | 146 m (85–171) | 190 m (144–205) |
| crate 1 m | 106 m (79–110) | 111 m (79–156) | 183 m (110–192) |
| 3 cm hanging cable | 92 m (16–112) | 95 m (16–112) | 107 m (65–110) |
| box 0.5 m in the bed | 55 m, 2 / 6 | 55 m, 2 / 6 | 110 m, 4 / 6 |
| person, frame recall 50–100 / 100–150 / 150–200 m | 94 / 13 / 0 % | 94 / 68 / 10 % | 86 / 62 / 44 % |
| trolley, frame recall 50–100 / 100–150 / 150–200 m | 88 / 11 / 0 % | 88 / 28 / 3 % | 67 / 55 / 51 % |
| confirmed detections away from the object (3 060 frames) | 12 | 39 | 21 |
| **the 20-minute ride without objects**: alarm frames / events | — | 289 / 82 | **274 / 75** |

Reading. The far-field rule is what takes a person from the height-reference limit (~106 m) to
~150 m without any speed. A train speed adds the rest of the sensor's reach — first
confirmation at 150–205 m for a person, a crate and a trolley, half of the 150–200 m frames —
and a 0.5 m box from ~110 m, **with fewer false alarms, not more**: on the whole ride (every
frame, `eval_real.py --given-speed`) 274 / 75 against 289 / 82, and 21 against 39 off-object
frames in set F — merged clouds are denser and steadier than single frames. It costs
mid-range frames (the merged cluster of an object is longer than the object when the speed is
off by a fraction of a m/s — the ride's speed is a per-file average here, not odometry — and
some frames leave the 3 % match window). Nothing is detected beyond ~205 m in any variant: the
sensor returns nothing there. The organizers said the trains may have no odometry (Q&A fact 6),
so the shipped numbers are the no-speed column; with an odometry or speed topic the node takes
the third column automatically.

## 3. Timing (4-core sandbox, Python, every frame; the i7-9700E bench is still owed)

**v0.6.3 (23.09, the idle sandbox, `resense bench --npy <recording>`, every frame, recordings
back to back, `OMP_NUM_THREADS=1`)** — a review measured the v0.6.2 code 25–33 % slower than the
v0.6 figures below still quoted in the README — in part the mount calibration measuring every
frame of its first 20 s (bisected by the review), in part the stages added since v0.6 (not
broken down); v0.6.3 measures the calibration only every 10th frame:

| recording (every frame) | **v0.6.3** mean / p95 / max | track / corridor / cluster means |
|---|---|---|
| `roundT_doubleT` (189 k points, moving) | **50.2 / 63.4 / 76.1 ms** | 27.4 / 12.6 / 10.0 |
| `doubleT_obstacle` (347 k points, 360°) | **63.6 / 77.8 / 119.2 ms** | 39.9 / 16.7 / 6.7 |
| `doubleT_platform` | **53.7 / 75.2 / 115.1 ms** | 23.9 / 11.1 / 18.4 |
| `roundT_pressureGate_roundT` | **45.6 / 57.1 / 83.1 ms** | 26.6 / 11.7 / 7.3 |
| `roundT_squareT_pressureGate_squareT` | **43.9 / 55.8 / 73.8 ms** | 26.6 / 11.3 / 5.9 |
| `squareT_platform_squareT_switch` | **42.3 / 52.8 / 81.2 ms** | 23.5 / 10.5 / 8.1 |
| `new_data` frames 2550–3149 | **43.4 / 57.8 / 87.5 ms** | 22.3 / 10.2 / 10.8 |

p95 stays inside the 100 ms frame period on every recording; through ROS the node adds ~20–25 ms
per 360° frame (§3b), which is where the 360° recording reaches the frame period on this sandbox.
Re-measured on 24.09 on another idle 4-core sandbox, the current code and v0.6.3 back to back:
36.5–52.2 against 35.1–57.4 ms mean (p95 50.3–67.1 against 46.3–75.4 ms), −9…+6 % per recording —
no regression ("Re-measurement" at the top; that sandbox is faster, so the table above stays the
quoted figure).

**v0.6 (22.09, the idle sandbox, nothing else running; `resense bench --npy <recording>`,
every frame, recordings back to back; the load of 1–3 is the bench's own BLAS threads).**
`total` is the whole `Detector.process` — mount calibration, track model, corridor and the
low-object stage, clustering, tracking, health:

| recording (every frame) | **v0.6** mean / p95 / max | track / corridor / cluster means | v0.5 mean / p95 (below) |
|---|---|---|---|
| `roundT_doubleT` (189 k points, moving) | **45.3 / 55.9 / 93.4 ms** | 26.8 / 11.6 / 6.7 | 43.0 / 50.9 |
| `doubleT_obstacle` (347 k points, 360°) | **57.9 / 69.1 / 109.6 ms** | 37.1 / 16.4 / 4.3 | 54.9 / 59.6 |
| `doubleT_platform` | **42.2 / 52.5 / 100.7 ms** | 22.9 / 10.2 / 8.9 | 83.3 / 170.8 |
| `roundT_pressureGate_roundT` | **43.0 / 52.8 / 86.7 ms** | 26.6 / 11.6 / 4.7 | 43.4 / 52.6 |
| `roundT_squareT_pressureGate_squareT` | **43.4 / 53.1 / 84.6 ms** | 27.2 / 12.2 / 3.8 | 42.3 / 54.2 |
| `squareT_platform_squareT_switch` | **43.4 / 52.2 / 81.2 ms** | 27.4 / 11.9 / 4.0 | 84.3 / 111.6 |
| `new_data` frames 2550–3149 (files 50–61: approach, station, departure) | **44.0 / 58.1 / 91.4 ms** | 26.0 / 12.1 / 5.7 | — |

p95 is inside the 100 ms frame period on **every** recording now, the platform bags included.
The v0.6 additions cost 2–5 ms mean on the tunnel bags (the corridor stage, 7 → 12 ms, now
holds the bed template and the low-object candidates; the calibration runs on the first
frames only). The platform bags got twice as fast (83 → 42 ms mean, p95 171 → 53 ms): the
2.1 m envelope keeps the platform edge out of the corridor, so DBSCAN no longer sees 15–20 k
candidates per frame. The maxima (81–110 ms) are single frames (the cold first fit, the
calibration frames).

**CPU and memory** (23.09, the same machine, frames loaded one at a time, `Detector.process` only):
`roundT_doubleT` 47 ms of CPU per frame, `doubleT_obstacle` 65 ms — **one core, 47–65 % of it at
10 Hz** — and 160–180 MB resident. With the library defaults the BLAS threads of numpy kept 3.9
cores busy on the 347 k-point frames (250 ms of CPU per frame) for no speed-up (64 vs 65 ms wall
time); the image therefore sets `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`. The ROS node adds ~20–25 ms per 360° frame (message conversion, decode, publishing; §3b); the jury's i7-9700E (8
faster cores) is not measured.

**v0.5 (history).**

Where the v0.5 time went before the cost work (cProfile over frames 100–114 of
`roundT_doubleT`, load 4.6): the rail-slab profiles called `np.percentile` once per 5 cm bin
(6 208 calls per 14 frames, 49 ms per frame), the bed height was evaluated six times per frame
on the whole cloud (13 ms), and the polygon test ran on all 190 k in-range points (14 ms).
After vectorising the per-bin percentile (one sort per profile, exact linear interpolation),
computing the bed height and the corridor coordinates once per frame and prefiltering the
polygon test by its bounding box, the same frames took: track 81 → 31 ms, corridor 16 → 7,
egomotion 9 → 7 (now off by default), cluster 6, total 112 → 52 ms.

**Back-to-back bench on the idle machine** (`resense bench --npy /data/cache/<bag>`,
every frame, commit 9b56bdf (merged as 82815e9); the v0.3 switches are the config of §1b; load before each run
in the table; the i7-9700E has 8 faster cores):

| bag (every frame, quiet 4-core sandbox, load < 1, runs back to back on 22.09) | v0.3 code (f2c57e5) mean / p95 / max | **v0.5 final** mean / p95 / max | v0.5 stage means |
|---|---|---|---|
| `roundT_doubleT` (189 k points, moving) | 56.4 / 70.6 / 83.2 ms | **43.0 / 50.9 / 87.7 ms** | track 28.8, corridor 6.7, cluster 7.2, tracking 0.3 |
| `doubleT_obstacle` (347 k points, 360°, stationary) | 70.7 / 75.9 / 92.7 ms | **54.9 / 59.6 / 79.7 ms** | track 38.1, corridor 11.5, cluster 5.0, tracking 0.4 |
| `doubleT_platform` | (v0.3 run of 21.09 under load: 79 / 132) | 83.3 / 170.8 / 196.3 ms | the platform approach: tens of thousands of candidates in the cluster stage, as in v0.3 |
| `roundT_pressureGate_roundT` | (56 / 89) | 43.4 / 52.6 / 71.6 ms | |
| `roundT_squareT_pressureGate_squareT` | (61 / 101) | 42.3 / 54.2 / 98.0 ms | |
| `squareT_platform_squareT_switch` | (83 / 131) | 84.3 / 111.6 / 151.3 ms | |

The vectorised bed / wall binning and the polygon bounding-box prefilter pay for the rail-slab
yaw and the bed verification (each ~3–4 ms mean, ~10 ms p95 in the track stage, reviewer's
attribution runs); the reviewer's pairs under load 4–7 gave the same picture (v0.3 code 83.7 /
120.8 vs v0.5 69.1 / 98.2 on `roundT_doubleT`). With a given speed the accumulation adds the
merged-cloud clustering (+12 ms mean on `roundT_doubleT` at load 8, reviewer's run). The frame
period is 100 ms: p95 is inside it on the tunnel bags and above it on the two platform bags on
this machine, where the node drops frames rather than queueing; the jury's i7-9700E (8 faster
cores) has not been measured (P1).

Per-stage means of the same runs are in the table; the platform bags remain the expensive
ones because their corridor holds 15–20 k candidates per frame (DBSCAN 45–70 ms in v0.3 and
v0.5 alike). The frame period is 100 ms; the ROS node adds message conversion, decode and publishing (~20–25 ms at 360°, §3b), and
drops frames rather than queueing, so the node's dropped-frame counter is the number to watch
on the bench.

### 3b. The ROS 2 node in Docker on real recordings (23.09, v0.6.2)

**Setup.** A Docker daemon runs in this sandbox (4 vCPU, 16 GB), so the organizers' procedure
was run for the first time on real frames: `docker build` of `docker/Dockerfile` (in the sandbox
with the session proxy's CA added after `FROM`, nothing else changed), the node started as
`docker run --net=host --ipc=host resense` (the image's default command), the recordings played
by `ros2 bag play --delay 3` from **a second container** (standing in for the host console), and
`/resense/status` recorded by a third one. The original bags were no longer on disk; they were
rebuilt from the frame cache by `scripts/cache_to_bag.py` — same topic, `frame_id`, PointCloud2
layout (`point_step` 26, empty dual-return slots, scan order) and receive times; coordinates
carry the cache's 5 mm quantisation. Scored by `scripts/check_dry_run.py`.

**What the first run found.** The node received **5 of the 201 clouds** of `doubleT_obstacle`:
a 360° cloud is ~10 MB, ~160 UDP fragments, and the node's best-effort subscription loses a
whole message with any fragment; it then reset its scene on every "hole" and confirmed nothing.
`ros2 bag play` publishes these recordings reliable (every original `metadata.yaml` records
`reliability: 1`, [`evidence/bag_metadata/`](evidence/bag_metadata/)); a reliable reader received
174+ of 201 in the same setup. v0.6.2 adds `input_reliability` (default `auto`: subscribe reliable, and match
the publishers within a second — best-effort when a publisher is, e.g. a live sensor-data
driver, to which a reliable reader would get nothing). The CI smoke test had not caught it: its
synthetic clouds are a third of the size.

**What a review found next.** With the player run **as a normal user** — the organizers play the
bag from their host console — the node received nothing at all: with `ipc=host`, Fast DDS puts
the node's shared-memory segments in `/dev/shm` as root-owned 0644 files the player cannot
write. (`umask 0000` in the container does not help: Fast DDS sets the mode.) The image now runs
Fast DDS over UDP only (`docker/fastdds_udp.xml`, `FASTRTPS_DEFAULT_PROFILES_FILE`); on the
10 MB clouds this measured the same rate and latency as shared memory. `scripts/console_test.sh`
(node container, player as uid 1000 in another container, status recorded by a third) checks it
in CI on the two synthetic bags. The node also publishes `FAULT` / `NO_INPUT` while no frame
has arrived yet instead of staying silent.

| run (v0.6.2 image) | frames processed | fps (2 s windows) | latency decode + detect mean / p95 | detector stage mean | result |
|---|---|---|---|---|---|
| `dry_run.sh` `roundT_doubleT` (120° window, `/lidar_points` + `hesai_lidar`), node and player in one container, root | 237 of 252 | 10.0 | 65 / 76 ms | 53 ms | 2 alarm frames at 128.3–130.2 m — the same frames as the offline evaluation (§0) |
| `dry_run.sh` `doubleT_obstacle` (360°, `/sensing/lidar/hesai128/pointcloud` + `lidar_livox`), one container, root | 103–134 of 201 | 7–9 in steady state (6.8–8.3 in the stored log), lower at the start | 96–99 / 112–130 ms | 74–76 ms | obstacle 55.9–56.6 m, 88–118 alarm frames |
| **`console_test.sh`**, player **uid 1000** in its own container, UDP profile: `roundT_doubleT` then `doubleT_obstacle` into the same running node | 351 of 453 | 8.3–10 in steady state | 82 / 102 ms | 65 ms | input switched, detector restarted; 131 alarm frames: the person and the object at 56.1–56.5 m and the 2 known frames at 128–130 m of `roundT_doubleT` |
| `console_test.sh` on the two synthetic bags (the CI step) | 72 of 80 | 5 (bag at 0.5×) | 65 / 78 ms | 53 ms | PASS |
| CI smoke test (`scripts/smoke_test.sh`, one container) | 76 of 80 | 5 (bag at 0.5×) | 64 / 76 ms | 52 ms | PASS |

**The first seconds of a 360° recording are not seen.** Through ROS the first cloud of
`doubleT_obstacle` arrives, then the next one 2–5 s later in recording time: a bare rclpy
subscriber doing nothing receives the same sequence (the first reliable 10 MB sample is
delivered ~4.5 s late, the samples in between are superseded in the keep-last-1 history), so it
is the transport's start-up with the recorded reliable QoS, not the detector. Each such hole
resets the scene. The first STOP of the person came at 5.7–9.2 s of recording time through ROS
against 1.1 s offline; on the 120° recording the start-up hole is 0.9 s in our run and 2.0–2.7 s in a review's runs
(`--delay 3` does not remove it). A player started well
before the frames matter, or a live sensor that is already streaming, does not have it; the
organizers' short control recordings may.

**Resources of the node container** (`docker stats` every ~0.5 s during the `doubleT_obstacle`
replay by a uid-1000 player): **~100 % of one core while frames arrive (median of the busy
samples; max 102 %), 186 MB** — at 360° the node is compute-bound on this sandbox. The detector
stage costs the same in the image (Python 3.10, numpy 1.26) as on the host (74 vs 68 ms on the
first 100 frames of `doubleT_obstacle`); the ROS path adds ~20–25 ms per 360° frame (message
conversion, decode — `pointcloud2_to_arrays`, 40 → 9 ms in v0.6.2 — and publishing the markers
and the corridor cloud). The node skips frames instead of lagging, as designed (keep-last 1):
over a whole 360° recording it processes 103–142 of 201 frames (the start-up hole included),
7–10 fps in steady state; the 120° recordings run at the full 10 Hz. Captures, node logs and
the checker output: [`evidence/docker_2026-09-23/`](evidence/docker_2026-09-23/). The jury's
i7-9700E (8 cores, higher clock) has not been measured.

**With RViz, on screen** ([`video/docker_chain_rviz.mp4`](video/docker_chain_rviz.mp4), 69 s,
image built from the current tree). The node container started with `rviz:=true` on a virtual
display (Xvfb, software OpenGL, no GPU), `ros2 topic echo /resense/decision` in a second
container, the bag played as uid 1000 from a third — every command on screen is the one that
ran. The bag played at 0.5×: RViz renders the 360° cloud in software at 6–10 fps on the same 4
vCPU. Node log ([`evidence/docker_2026-09-23/rviz_chain_node.log`](evidence/docker_2026-09-23/rviz_chain_node.log)):
`FAULT` (no input) until the first cloud; a 1.1 s start-up hole (the transport stall above);
OBSTACLE at 55.7–56.3 m from its frame 11 to 177; the last frames alternate STOP with CAUTION
(the object missed in that frame, advisory tracks at 11.6 m and beyond 139 m — the
`console_test` capture ends the same way, and offline the object is missed in 8 of its 126
frames); `FAULT` / `STALE` 0.5 s after the bag ended. 5 fps (the input rate at 0.5×), latency
mean 104–122 ms, p95 116–150 ms with RViz on the same cores, 15 of 201 clouds skipped. The
recording found one more transport defect: **the shipped RViz config subscribed the raw clouds
best-effort**, so during `ros2 bag play` it would have shown almost none of them (the node's own
first-run failure); it now subscribes reliable, like the node (`rviz/resense.rviz`).

## 4. What we learned / hard cases

1. **Sensor mounts differ between bags** (bed 1.5 m vs 2.0 m below the sensor, axis 0.05–0.25 m
   right of the sensor axis) → any fixed calibration fails; the rail-ridge self-calibration is
   stable to ±0.05 m frame to frame, provided the profile is built in the coordinates of the
   previous axis (in absolute Y the ridges smear in curves, §1b).
2. **Curves**: the v0.3 axis applied half the measured curvature and took its yaw from a free
   quadratic through the walls (§1b finding 1): the corridor drifted into the outer wall /
   column row at 50–130 m in the three curve bags, which is where the columns and wall
   segments came from. The rails give the yaw, the walls the curvature; at tunnel-type
   transitions (walls diverge) the parallel side wins and the corridor is trusted to 60 m
   only.
3. **Height reference beyond the bed fit** (§1b finding 2): the extrapolated bed is 0.3–0.65 m
   off at 85–105 m in the platform bags; the roof and the far rails then enter the polygon.
   Trust it 20 m beyond the fit and as far as the side structures verify it; do not classify
   low or elevated clusters beyond. It still does not *correct* the bed, so the far bins of
   set S are limited by the same reference (§2c).
4. **Platform stop + switch bag** was 504 of the 1 001 v0.3 false-alarm frames: two roof
   strips (700 frames between them), the hall's end wall at 72–78 m, and switch parts at
   147.5 m, all seen by a stopped train for 40 s. v0.5 leaves 56 frames / 18 events there, 50 of them the platform-end structure at 82.9 m (see §1): the curvature beyond a platform comes from the hall walls, which follow the platform rather than the track curving into the tunnel, so the corridor at 80–90 m is 0.5–0.8 m off — a station-curvature limitation (ALGORITHM.md §6.2), not a shape signature.
5. **Corridor-edge structures** at 1.5–1.6 m from the axis are 0.1–0.2 m outside the 1.40 m
   gauge (ALGORITHM.md §6.1): the strict decision needs a centimetre-accurate axis there, or a
   margin that grows with range; the crossing person of `doubleT_obstacle` leaves the gauge
   through exactly that band (label margins of ±0.25 m in frames 70–76), so every margin costs
   borderline frames of a real object.
6. **Small objects**: anything below rail head + 12 cm inside the rails and low/narrow hardware
   (< 0.35 m top, < 0.4 m wide) is filtered — a 20 cm object on the sleepers is invisible by
   design; revisit with the extended dataset.
7. **Point budget** is the physical limit: 0.5 m object = 7 pts @100 m, 1.6 pts @200 m.
8. **Injected objects beyond ~80 m are often fully occluded** because the injector places
   them on the per-frame extrapolated bed, which lies under the real bed there (§2c): the
   far bins of set S measure the injector as much as the detector.

## 5. Next experiments (owner in PLAN.md)

- **Injector placement on the local bed** (P4, `resense/synthetic.py`): place the object's
  base on the 5th–20th percentile of Z of the real returns within ±1 m of the axis and ±5 m
  of the placement (fall back to the model where fewer than ~10 such points exist), and write
  the height offset used into the gt row; re-run §2c;
- **bed correction from the side-structure base** (P3): use `z_base(X) − offset_ref` as
  `z_floor(X)` beyond the fit where the side base is continuous, then re-measure the far bins
  and the 147.5 m switch structures;
- **persistence 0.5 s** as the default once the P4 tests use `tracking.confirm_hits` /
  `confirm_time_s` generically (§1b option table gives the numbers);
- **bed-trough centre vs wall axis** at stations (design in v0.4, not implemented): a second
  lateral axis where the walls are far;
- ego-speed estimator: the tracks cue is silent below 1 m/s by design; the profile cue is
  silent on 40–60 % of the moving frames — a bed profile with the ring stripes removed, or the
  organizers' speed / odometry (the reliable path);
- extended dataset with real obstacles → calibrate dropout / intensity in `inject`, real
  recall by range and class, false alarms per km, FP taxonomy per scene type with the label
  tool;
- GOST 23961-80 gauge polygon from the drawings (ALGORITHM.md §3.2); platform notch; overhead
  policy;
- timing on the i7-9700E bench; Numba for the DBSCAN stage on the platform bags (15–20 k
  candidates per frame) if needed.

## 6. Mount calibration on real frames (v0.6.1)

`scripts/calib_check.py --npy <recording>`: a whole recording (201–260 frames, so that the
20-second final window completes), re-mounted by known rotations (the cloud rotated as a
sensor mounted that way would see it), a fresh detector over it. The residual is measured
against the correction found on the recording *as it is* — a rig may be tilted itself, which
is not an error — and split into tilt (roll + pitch) and yaw. Mount yaw below
`calibration.min_yaw_deg` (3°) is left to the per-frame track model by design, so the 2° of the
combined case stays in the yaw column.

| re-mount | `roundT_doubleT` (frames 0–251) tilt / yaw residual | `roundT_squareT_pressureGate_squareT` (100–359) | `doubleT_obstacle` (0–200, 360°) |
|---|---|---|---|
| as recorded: the rig's own correction | none (`identity`) | none (`identity`) | roll +3.02°, pitch −0.88° |
| roll +3° | 0.36° / 0 | 0.19° / 0 | 0.04° / 0 |
| pitch −4° | 0.26° / 0 | 0.34° / 0 | 0.07° / 0.21° |
| roll −2°, pitch 3°, yaw 2° | 0.32° / 2.09° (by design) | 0.49° / 2.09° | 0.04° / 2.26° |
| upside down | 0.00° — orientation found | 0.00° — found | 0.03° — found |
| forward = `+x` (the ROS convention) | 0.00° — found | 0.00° — found | 0.03° — found |
| mounted backwards | 0.00° — found | 0.00° — found | 0.03° — found |
| on its side (spin axis horizontal) | **not supported** (83°; 80° before v0.6.3) | **not supported** (89°; 90°) | **not supported** (84°) |

Reading. (1) Every upright or inverted mount is found from the data on all three recordings
and the tilt is recovered to 0.0–0.5° (median 0.2°: < 1 cm at the edge of the 1.05 m envelope).
(2) The `doubleT_obstacle` rig is rolled by 3.0° (its right rail head is 8 cm above the left
over 4–30 m of straight, stationary track) — corrected after half a second by the provisional
stage and confirmed by the final one; the two moving rigs are level within 0.5°.
(3) The first version searched all 24 axis-aligned orientations: on
`roundT_squareT_pressureGate_squareT` the upside-down, `+x`-forward and backwards mounts
adopted "left = ±z" (83° off, status `ok`) — the flat side wall of the square tunnel with two
cable trays on it passed for the bed with a rail pair and scored higher than the real track.
A spinning LiDAR is mounted with its spin axis vertical, so the default search is now the 8
orientations that keep it vertical (`calibration.keep_up_axis`, `tests/test_calibration.py`).
(4) The same wall is why a sensor that really is mounted on its side cannot be recognised
from the geometry (the configured mapping "passes" on the wall and the detector then alarms):
such a mount must be set with `sensor.forward/left/up` (launch arguments `sensor_forward` /
`sensor_left` / `sensor_up`); ALGORITHM.md §6. (We tried the ring structure as a physical cue
for the spin axis and dropped it: a real sensor always spins about its own z, so its rings say
nothing about how it is mounted.)

**Why the tilt needs 20 s on a moving train** (`scripts/mount_survey.py --npy new_data`: the
calibrator's roll measurement on every 5th frame of the 20-minute ride with the correction
off). The per-frame roll has a median of **−0.09°** and a 10–90 % range of −1.0…+0.7° — on
straight track (|k| < 2·10⁻⁴: −0.9…+0.6°) as in curves (−1.1…+0.8°): cant transitions, the
body's lean and the rail geometry itself. Neighbouring frames see the same stretch of rail, so
the error of a median depends on the time it spans more than on the count:

| window a fresh calibration freezes | median error | p90 | max |
|---|---|---|---|
| 5 consecutive frames (v0.6) | 0.37° | 1.01° | 2.20° |
| 20 observations every 10 frames (20 s, **v0.6.1 default**) | 0.24° | 0.53° | 1.02° |
| 20 observations every 20 frames (40 s) | 0.19° | 0.42° | 0.84° |

With v0.6 the eight parallel pieces of the ride evaluation froze eight different "mount
rolls" (−0.97…+1.63°) for one sensor, and the drift monitor (an EMA of single checks against
1°) then flagged 5 482 of the 11 271 frames — `CAUTION` on half of the ride for nothing. v0.6.1:
a provisional correction after 5 frames only above 2.5° (a clearly tilted rig such as
`doubleT_obstacle`), the final one from the 20-s window above 0.5°, and the drift monitor on the
median of the last 10 checks (50 s) against 1.5° (ALGORITHM.md §2b). The v0.6 table (25 frames,
5-frame median) had tilt residuals of 0.0–0.8°.

## 7. Recognition methods tried, side by side

The task statement allows any approach; these are the ones we built and measured (numbers from
the sections named; "real" = the organizers' frames, "set F" = objects ray-cast into the moving
ride, 30 sequences × 110 frames, straight track, no speed unless said).

| # | method | what it is | measured | verdict |
|---|---|---|---|---|
| 1 | rectangle corridor + DBSCAN (v0.0) | fixed box ahead of the sensor, raw clustering | 149 alarm frames of 231 sampled empty frames; DBSCAN up to 1.4 s on dense near points (§1) | replaced by 2 |
| 2 | **normal-tunnel geometry** (v0.3 → v0.5) | per-frame bed and rail fit, axis from the rails, curvature from the walls, gauge polygon, range-scaled voxel DBSCAN, infrastructure signatures, persistence in time | empty bags 1 001 → 96 alarm frames at 10 Hz; the real person 66/71 (§1, §1b) | **the core** |
| 3 | multi-frame accumulation with a LiDAR-only speed estimate (v0.4) | merge 5 frames beyond 40 m, motion-compensated by a speed estimated from the tunnel texture | synthetic tunnel: person 189 vs 178 m; real empty bags 119 / 30 vs 88 / 27 (more false alarms), no change on the real person (§1b, §2b) | estimator off; accumulation kept for a given speed |
| 4 | **accumulation with the ride's train speed given**, on a moving real background (v0.6) | 5 frames merged beyond 40 m, motion-compensated with the given speed | set F: person 150 → **177 m** median, trolley 146 → 190 m (max 205 m), crate 111 → 183 m, 0.5 m box 2 → 4 of 6; the whole ride 289 / 82 → **274 / 75** false alarm frames / events (§2d) | on whenever the node gets a speed (odometry / speed topic / parameter); the organizers' trains may have none |
| 5 | bed-anomaly low-object stage (v0.6a) | every bump > 7 cm above a learned bed cross-section inside the envelope | ride 1 482 events / 20 min (inductors, drain covers, cable crossings) (§1d) | rejected |
| 6 | rail-level low-object stage (v0.6f) | a low cluster whose top reaches the rail head | object on the rail 170 / 185 frames; ride 734 events (guard rails, joints, fastenings) (§1d) | option for a line known to be clean |
| 7 | **per-point rail-head rule + 0.5 s** (v0.6, shipped) | every low candidate ≥ 3 cm above the rail head, 5 hits | ride 18 low events; 10 cm box on a rail head 10–25 m (synthetic tunnel); real object 2 / 185 by its own detection (§1d) | shipped in v0.6–v0.6.1 |
| 7b | **straddle clustering** (v0.6.2, shipped) | bed anomalies and the corridor points just above the envelope floor clustered together; top ≥ 0.10 m above the rail head, ≥ 0.35 m across, ≤ 0.8 m along the track | real object 2 → **121 / 185**, 118 of the 126 frames after the person leaves; +1 event on the five bags and on the ride; 30 cm objects on a rail head 6 / 6 from 42–44 m (set F round 2); without the shape rule +49 ride events (§0, §2d) | shipped; the thresholds sit close to the one real object (top 0.11–0.16 m, 0.38–0.50 m across) |
| 7c | **confirmation 0.5 s; no far alarm without rails** (v0.6.2, shipped) | 5 frames instead of 3; clusters beyond 40 m advisory in frames without the rail pair | false events: five bags 31 → 20, ride 83 → 47; the real person unchanged; a person 3 m later on straight track, 10 m later with a speed (§0, §2d) | shipped |
| 8 | **far-field rule** (v0.6, shipped) | beyond the height reference, tall (≥ 0.6 m), short (≤ 3 m), grounded clusters alarm to the trusted axis range | set F, rule off → on: person first confirmed 106 → **150 m** median, trolley 105 → 146 m, crate 106 → 111 m; off-object detections 12 → 39 of 3 060 frames (§2d) | shipped |
| 9 | learned second opinion (v0.6 experiment) | gradient-boosted trees on the descriptors of the geometric candidates (positives: set-F objects; negatives: every candidate on empty data) | held-out ride part + unseen sequences: AUC 0.976–0.990; 83–95 % of false candidates removed at 97 % object recall; intensity is an injector artefact (§8) | not shipped: no real positives; ready as a re-weighting |
| 10 | considered, not built | a trained 3D detector (PointPillars / CenterPoint: no real positives, ~0–3 % AP beyond 100 m in the rail literature), change detection against a map (needs localisation and repeated rides; "a map of the given tunnels will not fully work" — Q&A), a range-image anomaly model (fires on cables, signs, wet patches; needs the same gauge and persistence) | RESEARCH.md §0 | — |

## 8. A learned second opinion on the geometric candidates (experiment, not shipped)

Question: can a small classifier on cluster descriptors remove the geometric pipeline's false
candidates without losing objects? `scripts/ml_dataset.py` records every single-frame
candidate the pipeline places in the envelope (or demotes by a signature): **negatives** = all
of them on the five empty bags and on every second split file of the ride (5 042 rows — every
one is infrastructure or noise), **positives** = the candidates that match an object ray-cast
into consecutive ride frames (set-F injection, 12 files × 5 kinds, 2 049 rows). 14 descriptors
(distance, lateral, box size, voxel / raw point counts, visibility ratio, height span,
intensity, low-object flag, demoted flag, share of points inside the envelope).
`scripts/ml_second_opinion.py` trains gradient-boosted trees (scikit-learn
`HistGradientBoostingClassifier`, 300 iterations, class-balanced) on the five bags + the first
60 % of the ride and the first half of the object sequences, and tests on **the last 40 % of
the ride and the other half of the sequences** (never seen).

| descriptors | AUC (test) | false candidates removed at 99 / 97 / 95 % object recall | objects kept beyond 150 m (at 97 %) |
|---|---|---|---|
| all 14 | 0.990 | 74 / **95** / 98 % | 82 % |
| without intensity | 0.988 | 81 / **91** / 95 % | 84 % |
| without intensity and the point counts (n_vox, n_raw, visibility) | 0.976 | 67 / **83** / 89 % | 81 % |

**Leakage check.** Permutation importance puts *intensity* first by a factor of eight (AUC drop
0.136) — but the intensity of an injected object is drawn from the injector's reflectivity
catalogue, and its point budget from the injector's dropout model: the classifier can learn
"injected vs real" from them. Without them the trees still separate the two on shape and
place alone (width, length, the demoted flag, the envelope share, the lateral offset: AUC
0.976, 83 % of the false candidates removed at 97 % recall), which is the honest number.

**Why it is not shipped.** Every positive is synthetic (our five object models); a real object
of another shape (a bag, a fallen panel, a tool box) is outside what the trees have seen, and
the negatives come from the same seven recordings the geometry was tuned on. As a veto it
would trade an explainable rule set for a learned boundary with no real positives behind it
— the opposite of what a safety function needs. The use we see: a confidence re-weighting of
tracks (never a veto inside 60 m) once the organizers' real obstacles exist to train and test
on; the dataset and training scripts are ready for that.

