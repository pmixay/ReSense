# B2: the whole Falcon recording through one detector — 18.10

> **Observation only.** Development data, not G3, not a J1 result. No detector code was changed. Owner: P4.
> Backlog N2 task 2: "read the unseen 257 s of `falcon_test`". On 17.10 only t = 0–98 s (prefix) and 241–329 s
> (window) were seen, each by its own fresh detector ([extended data README](../extended_data_2026-10-17/README.md)).

## How

`scripts/stream_falcon.py` reads the 20.3 GB sqlite split once, straight from the organizers' link (zstd → tar →
bytes). It recovers every PointCloud2 message from its overflow chain in a rolling buffer
(the method of `window_bag.py`) and feeds the messages, in timestamp order, to **one** node replica
(`judge_runner.NodeReplica`, unchanged), as a jury playing the whole bag would. Nothing is stored but the
per-frame records. 1.1.0 (`492e407` tree), `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`.

## Checks (not taken on trust)

| check | result |
|---|---|
| Positive control: the recovery on a local bag (the 985-frame prefix) against sqlite's own read | **985 / 985 messages, same timestamps, byte-identical blobs**, 0 lost |
| Whole recording | 4,443 / 4,443 messages found and complete, **0 lost**, 0 duplicates, timestamps in order, largest gap 0.11 s, 444.2 s, **no detector reset** |
| Known answer: the first 985 frames vs. the 17.10 prefix run (same data, same fresh detector) | **all 985 decisions equal**. 10 frames (10–19) differ only in the wall-clock health line "latency p95 … ms over the 100 ms budget" while the stream started, as in B3 |
| Coverage of the 17.10 window | all 874 bag times of the 241–329 s window are in the full run |
| Repeat | a second stream (with frame dumps) gives the same records |
| Object identity | raw points of 14 dumped frames plotted ([pictures/](pictures/)); the object's track, size and speed checked (below); the train's stillness checked from the static warning (115.1 m, p5–p95 spread 0.17 m) |

## Result (one detector, the whole recording)

| part of the recording | frames | decisions | CAUTION | STOP episodes |
|---|---:|---|---:|---|
| 0–98 s (seen 17.10) | 985 | FAULT 1, GO 8, CAUTION 975, STOP 1 | 99 % | 1 frame at 115.0 m (the static object, lateral +0.9) |
| **98–241 s (unseen until now)** | 1,427 | CAUTION 1,424, STOP 3 | **99.8 %** | 3 frames at 115.1 m (same static object) |
| 241–329 s (seen 17.10) | 874 | CAUTION 604, STOP 270 | 69 % | the walking person from 297 s (4 episodes, 124.8 → 99.8 m) |
| **329–444 s (unseen until now)** | 1,157 | STOP 1,098, CAUTION 59 | 5 % | the person, 1,087 frames continuously (99.8 m → 6 m); 3 frames at 6.0 m (the person); **8 frames at 9.4 m: probable false STOP** |

**What the unseen parts show:**

1. **98–241 s is like the start:** a standing train in an empty tunnel, in `CAUTION` 99.8 % of the time from the
   two static warnings at 105.6 m and 115 m, with one short false `STOP` (3 frames) on the 115 m object. The
   jury-visible problem of N2 holds for the whole first four minutes.
2. **A person walks along the track to the train.** The person first appears as a warning at **139.4 m**
   (284 s, lateral −1.29 m: at the gauge edge) and becomes a `STOP` at **121–125 m** (297–300 s) as they move in toward
   the centre. The `STOP` is then held while they come from 125 m to 6 m in front of the sensor (437 s), at
   0.3–1.3 m/s (slower at 330–380 s), along the track centre (lateral about −0.35 m). In the raw points it is a
   0.5–0.8 m wide column standing on the track floor, about 1.7 m tall ([frame 3800](pictures/frame_03800.png), 79 m;
   [frame 4200](pictures/frame_04200.png), 28 m; [frame 4370](pictures/frame_04370.png), 7 m). On a person in the
   track, these `STOP`s are the right answer.
3. **One probable false STOP at the very end:** 8 frames at 439–440 s on a flat patch 9.4 m ahead (detector size
   1.25 × 2.79 × 0.11 m, on the floor), after the person has gone out of view in the sensor's near blind zone
   ([frame 4400](pictures/frame_04400.png)). No object is visible there. The cause (for example the near floor
   blocked by the person a moment before) is **unverified**.

**False `STOP`s on the whole recording, one detector:** 4 frames on the static 115 m object (16 and 231 s) and
8 frames on the floor patch at 9.4 m. **True `STOP`s:** the walking person, 1,360 frames (1,372 STOP frames in all, minus these 12), from 125 m.

## Corrections to the 17.10 report

* The person does **not** "turn back" at ~97 m: the 17.10 window ended at 329 s. The full run shows the
  person keep approaching to 6 m.
* Window frames 640–641 (at 115.2 m) were attributed to the static 115 m object. Their lateral is −0.30 m, the person's
  side, while the static object sits at +0.7 … +1.3 m. They are the person passing 115 m.
* The window's false `STOP`s at 251–254 s (12 frames on the 115 m object) come from that run's fresh start at 241 s.
  The continuous run has none there.

## Files

[check_v110.json](check_v110.json) (all checks and the per-part summary, from [check_b2.py](check_b2.py)),
[falcon_full_v110.meta.json](falcon_full_v110.meta.json), [pictures/](pictures/) (from [plot_frames.py](plot_frames.py);
red = points in the STOP detections' boxes, the column above them up to the ceiling included), and
[falcon_full_runs.tar.xz](falcon_full_runs.tar.xz) (per-frame records of both streams; SHA-256 in `SHA256SUMS`).

```
RESENSE_REPO=<1.1.0> PYTHONPATH=<1.1.0>:<1.1.0>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
  python scripts/stream_falcon.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out falcon_full_v110 [--dump 3800,4200]
python docs/evidence/falcon_full_2026-10-18/check_b2.py falcon_full_v110.jsonl <17.10 prefix .jsonl> <17.10 window .jsonl> check.json
```
