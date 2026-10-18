# B3 / B8: Pandar ↔ Falcon in one running detector, and Falcon frame time — 18.10

> **Observation only.** Development data, not G3, not a J1 result. No detector code was changed.
> Owner: P4. Backlog: N2 task 1 (the two-bag switch in one node) is P1's launch work; this is the
> measurement under it. B8 is the Falcon per-frame time.

## Question

The jury may play a Pandar bag and then the Falcon bag (or the reverse) into the same running node.
Does the second lidar start cleanly? In particular: no stale scene state, no sensor orientation or
mount calibration carried over from the other lidar, and no extra false STOP at the switch?

## How

The judge's node replica (`../rejudge_2026-10-16/scripts/judge_runner.py`, unchanged) with several
`--bag` = **one detector**, in order ([run_b3.sh](run_b3.sh)). Each version ran four times, one run
after another so timings do not compete:

| run | input |
|---|---|
| `pandar` | `doubleT_obstacle` alone (201 frames, Pandar128, `/lidar_points`, `lidar_livox`, a real obstacle) |
| `falcon` | `falcon_test_second_dark` prefix alone (985 frames, t = 0–98 s, `/iv_points`, `seyond`) |
| `p2f` | Pandar, then Falcon, one detector |
| `f2p` | Falcon, then Pandar, one detector |

[compare_b3.py](compare_b3.py) compares each half of a switch run with the same bag run alone, frame
by frame, on every field except wall-clock timing.

Data: the Pandar bag is from the organizers' zip; the Falcon prefix is the first 4.5 GB of the split
(same 985 frames as on 17.10, [`prefix_bag.py`](../extended_data_2026-10-17/scripts/prefix_bag.py)).
SHA-256 of both bags in [SHA256SUMS](SHA256SUMS). Linux runtime of the P4 protocol,
`OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`. Checkouts: 1.1.0 (`492e407` tree) and 707ea9c.

## Result

| | 1.1.0 | 707ea9c |
|---|---|---|
| what happens at the switch (both orders) | `new_input`: a fresh detector | same |
| Falcon part after Pandar vs. Falcon alone | **0 of 985 frames differ** | 0 |
| Pandar part after Falcon vs. Pandar alone | 0 decisions differ; 8 frames differ in health `level` only (see below) | **0 of 201 frames differ** |
| Falcon start-up | frame 0 `FAULT` (view blocked), orientation adopted from frame 1, mount `ok` at frame 192 | same |
| Pandar start-up after the Falcon | `GO`, mount `pending`, as when alone | same |
| decisions, switch runs | GO 16, CAUTION 975, STOP 194, FAULT 1 = the sum of the two bags alone | same |

**The switch is a clean fresh start in both directions, on both versions.** Nothing of the first
lidar (orientation, mount calibration, tracks, health) reaches the second. The rule in the real
node is the same as in the replica: another topic or another `frame_id` calls `start_new_input`,
"a fresh detector (scene state and mount calibration start over)"
(`ros2_ws/src/resense_ros/resense_ros/detector_node.py`, 1.1.0, lines 680–721). The Pandar and the
Falcon differ in both topic and `frame_id`.

**The 8 health differences, checked:** on 1.1.0, Pandar frames 10–17 of the `pandar` run alone carry
"latency p95 201 … 109 ms over the 100 ms budget" (health `level` warn). In both switch runs they do
not. The decision level stays `ok`, and every decision is equal. The same frames differ in `p2f`
too, where they come *before* the switch, so the switch is not the cause. 1.1.0's latency monitor
reads wall-clock time, and that stand-alone run was the first to read the 4.8 GB bag from a cold
disk. On 707ea9c, which has no such monitor, all frames are equal.

**Reproducible:** the Falcon-alone run on 1.1.0 equals the 17.10 run of the same prefix, decision
for decision (985 / 985; [extended data README](../extended_data_2026-10-17/README.md)).

**Not covered here:**
* The live node's topic discovery and timing: the default `input_topic` lists `/lidar_points` and the
  Hesai topic. `/iv_points` is found by discovery once the active input is silent for
  `input_switch_timeout`. That is the Docker / launch measurement (P1, N4).
* A switch that keeps the same topic **and** `frame_id`, with a 1–30 s gap. Only that case resets
  the scene but keeps the mount calibration. It cannot happen with these two bags.

## B8: frame time per sensor (this container, one core)

From the stand-alone runs, frame 0 excluded (first-call costs). `decode_ms` = node decode of the
CDR message; `detect_ms` = detector.

| | points per frame (median) | decode p50 / p95 / max ms | detect p50 / p95 / max ms | frames over 100 ms |
|---|---:|---|---|---:|
| Pandar128, 1.1.0 | 340,723 | 19.5 / 26.9 / 98.3 | 29.8 / 41.5 / 58.1 | 0 |
| Pandar128, 707ea9c | 340,723 | 18.4 / 24.2 / 43.5 | 28.3 / 40.3 / 52.7 | 0 |
| **Falcon, 1.1.0** | **94,929** | **2.3 / 2.9 / 11.4** | **14.4 / 19.6 / 54.6** | **0** |
| Falcon, 707ea9c | 94,929 | 2.4 / 3.2 / 8.1 | 14.3 / 19.7 / 52.8 | 0 |

The Falcon frame costs about a third of a Pandar frame (≈ 17 ms vs. ≈ 50 ms, decode + detect,
p50). The Falcon publishes at 10 Hz (4,443 frames in 444 s), so the 100 ms budget is met with a
wide margin. These are this container's times. The jury's machine and the Docker node add
transport and scheduling, measured separately (J1 Docker chain).

## Files

`<version>/compare.json` (all comparisons, the first frames after each switch, timings),
`<version>/*.meta.json` (runner meta: frames, resets, wall / CPU time, peak RSS),
[b3_runs.tar.xz](b3_runs.tar.xz) (every per-frame record and CSV, SHA-256 in `SHA256SUMS`).
