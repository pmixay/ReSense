# Falcon demo bag through real ROS 2 (21.10): `ros2 bag play` into the node, measured

**Result: PASS for the pitch path, with two findings.** The 432-frame Falcon demo bag opens with `ros2 bag info`, plays with
`ros2 bag play` at rate 1.0 and 0.5 into the 1.2.0 node (profile `falcon_ros`), every frame is processed (432/432, 0 dropped), results are
fresh (age about 6 ms from input arrival to status), the first STOP on the person comes 23.2 s after the player command at rate 1.0
(limit 30 s) and 42.9 s at rate 0.5. **Finding 1:** the live run is not the offline cold replay of the record: its first STOP is earlier
(frame 2916, 130.48 m, 19.7 s of bag time; the record says frame 2950, 127.18 m, 23.1 s) and 24 of 432 decisions differ from that replay.
**Finding 2:** the Pandar `doubleT_obstacle` bag through the same literal command does not show S1's stale results on this build.
Machine: the team's bridge server (4 vCPU, 15 GB RAM). Nothing in `resense/`, `native/`, `configs/`, `ros2_ws/` was changed.

## What was done
1. Bag: rebuilt from the organizers' link with `scripts/make_falcon_demo_bag.py ... --first-frame 2719 --last-frame 3150` (4.5 min, 0 messages lost;
   `raw/bag_build_receipt.json`). `sha256sum -c BAG_SHA256SUMS`: both files OK (`falcon_demo_0.db3` b2c4a826...5735, `metadata.yaml` 542c7549...4119).
   `ros2 bag info` in the image: sqlite3, 43.1008 s, 432 messages, `/iv_points` `sensor_msgs/msg/PointCloud2` CDR.
2. Image: `docker build -t resense:falcon-demo-1.3 -f docker/Dockerfile .` from branch `claude/falcon-ros-demo-1.3` (source = release v1.2.0 detector bytes:
   `python3 scripts/detector_freeze.py verify` PASS, 40 files, digest 6d091081...). The build worked (ros:humble-ros-base-jammy base, no fallback needed);
   it prints `resense 1.2.0 ... native (_resense_native...so)`. Image size 2.68 GB on disk (1.03 GB content). Build tail: `raw/docker_build_tail.log`.
3. Trials (`scripts/trial.sh`): one node container (`ros2 launch resense_ros detector.launch.py freshness_mode:=replay clear_range_policy:=POLICY`),
   `reset_replay.py --profile falcon_ros` (what `play_bag.sh` does), a passive recorder container (`scripts/recorder.py`: arrival wall time of every
   `/iv_points` header and of `/resense/status`, `decision`, `nearest_distance`, `clear_distance`, `obstacle_detected`, `warning`, `latency_ms`, `fps`),
   then the literal player `ros2 bag play /data/bag --rate R --delay 3 --read-ahead-queue-size 10 --disable-keyboard-controls` as uid 1000. Host networking,
   DDS domain 87 (so nothing else on the host could see it), UDP-only Fast DDS profile of the image. `docker stats` sampled each ~2 s.
   Seven Falcon trials: rate 1.0 and 0.5, policy `conservative` and `legacy` (the `play_bag.sh` default), repeats, and one rate-1.0 control with the
   recorder's `/iv_points` subscription switched off.
4. Analysis (`scripts/analyze.py`, `scripts/extra_checks.py`, `scripts/analyze_generic.py`): frames matched by header stamp to the offline cold-start
   replay (`falcon_demo_bag_2026-10-20/out/coldstart.jsonl.xz`) and to the whole-recording record (`l16_acceptance_2026-10-20/.../l16.jsonl.xz`).

## Falcon result table (per trial; all 432 frames; `summaries/*.json`)
Age = arrival of the status message minus arrival of the same input frame (same host clock); the node's own `source_age_s` is in the JSON (median 0.015 s, max 0.043 s).
RSS = the node's `rss_peak_mb` / peak `docker stats` memory of the node container. "since cmd" = seconds after the `docker run ... ros2 bag play` command
(3 s of that is the player's `--delay 3` plus container start), "since 1st in" = after the first `/iv_points` message arrived.

| trial | processed | first STOP: frame / distance / bag time | since cmd / since 1st in (s) | differ from offline cold replay | age median / max (s) | dropped | RSS MB | fresh results |
|---|---|---|---|---|---|---|---|---|
| r10_cons | 432/432 | 2916 / 130.48 m / 19.7 s | 23.19 / 19.6 | 24 | 0.0057 / 0.0326 | 0 | 154.3 / 115.6 | 431 |
| r10_cons_b (repeat) | 432/432 | 2916 / 130.48 m / 19.7 s | 23.19 / 19.6 | 24 | 0.0061 / 0.0234 | 0 | 154.3 / 115.6 | 431 |
| r10_legacy | 432/432 | 2916 / 130.48 m / 19.7 s | 23.24 / 19.6 | 24 | 0.0055 / 0.0327 | 0 | 154.2 / 122.1 | 431 |
| r10_cons_nosub (control, no input subscriber) | 432/432 | 2916 / 130.48 m / 19.7 s | 23.25 / - | 24 | - | 0 | 154.3 / 117.4 | 431 |
| r05_cons | 432/432 | 2916 / 130.48 m / 19.7 s | 42.88 / 39.21 | 24 | 0.0057 / 0.0238 | 0 | 153.9 / 118.4 | 431 |
| r05_cons_b (repeat) | 432/432 | 2916 / 130.48 m / 19.7 s | 42.89 / 39.21 | 24 | 0.0054 / 0.0269 | 0 | 154.6 / 115.5 | 431 |
| r05_legacy | 432/432 | 2916 / 130.48 m / 19.7 s | 42.89 / 39.22 | 24 | 0.0056 / 0.0170 | 0 | 154.6 / 118.1 | 431 |

The one non-fresh result is the first frame (FAULT, `epoch_unconfirmed`, as designed). The node's `frames` counter in the last frame status reads 431 (it counts
before the frame being published); 432 distinct frame statuses were received. `node.log` and `player.log` of every trial are in `raw/trials_raw.tar.xz`.

Against the acceptance in section 7 of the bag README: `ros2 bag info` opens it - yes. STOP on the person not later than 30 s from the start of playback at
rate 1.0 - yes (23.2 s; the STOP the record expects, frame 2950, 127.18 m, arrives at 26.6 s). First line `profile=falcon_ros` - every frame status carries
`sensor_profile: falcon_ros` (432/432; `play_bag.sh`'s own listener line was not run, see below). FAULT only on the first frame - yes (1 FAULT, frame 2719).
At rate 0.5 the STOP at frame 2950 arrives at 49.7 s (the README predicted ~49 s) and the first STOP at 42.9 s: that does not pass the 30 s rule, as the README said.

### Comparison with the offline records
* Decisions: live 1 FAULT / 7 GO / 271 CAUTION / 153 STOP; offline cold replay 1 / 9 / 275 / 147; whole-recording record on the same frames 0 / 0 / 297 / 135.
* 24 frames differ from the offline cold replay (2723-2724, 2909-2910, 2913-2914, 2916-2919, 2953, 2956-2957, 2990-2992, 3003, 3007-3008, 3039, 3058, 3107, 3126-3127);
  38 differ from the whole-recording record. Positive control: the same matching reproduces the README's 32 differing frames between the cold replay and the record.
* STOP runs (frame ranges). Live: 2916-2919, 2950-2953, 2956-2957, 2981-3002, 3009-3039, 3059-3125, 3128-3150. Offline cold replay: 2950-2952, 2981-2989, 2993-3003, 3007-3038,
  3058-3106, 3108-3150. So the live run adds a short STOP at 2916-2919 and 2956-2957, starts the later runs 0-2 frames late (3009 vs 3007, 3059 vs 3058, 3128 vs 3108: 20 frames), and has
  two CAUTION frames (3126-3127) before the last run.
* The earlier first STOP is the walking person: for all 57 live STOP frames up to frame 3033 the nearest distance is within 2.58 m of the person's line fitted on the
  whole-recording record (`scripts/person_track.py`, 1.13 m/s; at frame 2916 the line gives 130.9 m, the node 130.48 m; tolerance in that script 3.5 m).
  Distances fall 130.48 -> 127.18 m over frames 2916 -> 2950, 0.97 m/s: a person's walking pace. So these are not false STOPs on a structure.
* Instrumentation does not change results: the decision/distance sequence (432 frames) is identical across all seven trials, with and without the recorder's input
  subscription, at both rates, with both clear-range policies.
* Why live differs from the cold replay (not investigated): the decisions in the replay come from `coldstart_compare.py` on a different code path (offline, no DDS), the node
  here runs its ROS frame path. The results are bit-stable in the node, so it is not timing noise. Whether to change the README's expected first STOP (2950 / 127.18 m)
  to 2916 / 130.48 m is for the captain; the proposal is in the bag README section 7.

## S1 re-check, Pandar `doubleT_obstacle` (201 frames, 20.4 s, 360 degree clouds of ~24 MB)
Bag from the organizers' archive via `scripts/unpack_dataset.py`; sha256 05f1d7f7...c5ad9 equals `scripts/cold_bags.sha256`, `metadata.yaml` equals the committed original.
Same literal player command, same node, bag read into the page cache first (`cat *.db3 > /dev/null`, as the guides say). Host `net.core.rmem_max` was 212992 (the node warns about it; I did not change host sysctls).

| trial | frames with a result | fresh | node source age median / p95 / max (s) | dropped (node) | STOP frames | RSS MB (node peak / container peak) |
|---|---|---|---|---|---|---|
| pandar128, rate 1.0 | 201/201 | 191 (7 `catchup`, 2 `queue_stale`, 1 first frame) | 0.048 / 0.149 / 0.459 | 4 | 193 | 421 / 292 |
| manual (the literal default profile), rate 1.0 | 201/201 | 192 | 0.050 / 0.116 / 0.365 | 4 | 193 | 441 / 286 |
| pandar128, rate 0.5 | 200/201 | 198 | 0.092 / 0.105 / 0.134 | 4 | 192 | 239 / 221 |

S1 reported, for the literal player on this bag: 146/201 processed, 0 fresh, age median 7.33 s / max 10.51 s, RSS 3,357 MB. On this build and machine: 201/201, 191-198 fresh,
age max 0.46 s, RSS 0.4 GB. The 4 dropped frames are the 4 frames the recording itself is missing (VM_GUIDE). **S1's failure does not reproduce here.** What this does not show:
which change fixed it, whether a cold disk (bag not in cache), a different machine or a CycloneDDS player brings it back, and the 200/201 at rate 0.5 (one frame without a status, not looked into).
The recorder saw only 182 of 201 clouds (its own extra best-effort subscription, at the low `rmem_max`); the node itself got all of them, so the age numbers above are the node's own
`source_age_s`; the recorder's arrival difference on the 182 frames it saw is median 0.028 s, max 0.12 s (rate 1.0). At rate 0.5 the recorder saw 116 clouds.

## Not verified
* `scripts/play_bag.sh` itself, `run_demo.sh`, RViz and the gauge/box were not run. `play_bag.sh` raises `net.core.rmem_max` with `sysctl` as root, a change of the host's kernel
  settings that this task was not allowed to make; `trial.sh` runs the same docker commands (node, `reset_replay.py`, player) without it. Its printed line `profile=falcon_ros` is therefore not observed
  (the same fact is in every status message).
* Pandar with a cold disk cache; Falcon from a cold cache; any machine other than the bridge server; a player other than the image's stock Fast DDS one; the live (non-replay) freshness mode.
* The cause of the 24-frame difference to the offline replay (above), and the 200/201 at Pandar rate 0.5.
* Results are from one host with an otherwise idle CPU; no load test.

## What failed on the way
* A first draft of my wait loop used `pgrep -f` on a pattern that appears in its own command (the trap named in CLAUDE.md); replaced by reading the logs. No trial was affected.
* Nothing in the trials failed. The cloud agent's attempt (previous version of this README) was blocked before any measurement.

## The exact working demo commands (what was run; `BAG`, `IMAGE` as below; from the repository root)
```bash
BAG=<dir>/FALCON_DEMO_BAG IMAGE=resense:falcon-demo-1.3
docker build -t $IMAGE -f docker/Dockerfile .
(cd $BAG && sha256sum -c $OLDPWD/docs/evidence/falcon_demo_bag_2026-10-20/BAG_SHA256SUMS)
docker run --rm -v $BAG:/data/bag:ro $IMAGE ros2 bag info /data/bag
# the jury-style run (needs rmem_max >= 33554432 on the host: sudo sysctl -w net.core.rmem_max=33554432; Falcon clouds were fine without it here)
IMAGE=$IMAGE PLAYER_USER=1000:1000 scripts/play_bag.sh --rate 1.0 --clear-range-policy conservative --sensor-profile falcon_ros $BAG
# what was measured (no sysctl, separate DDS domain, recorder):
docs/evidence/falcon_ros_demo_2026-10-21/scripts/trial.sh LABEL 1.0 $BAG falcon_ros conservative $IMAGE $OUTDIR     # 0.5 for the slow run
python3 docs/evidence/falcon_ros_demo_2026-10-21/scripts/analyze.py $OUTDIR/LABEL docs/evidence/falcon_demo_bag_2026-10-20/out/coldstart.jsonl.xz
# Pandar:  IN_TOPIC=/sensing/lidar/hesai128/pointcloud ... trial.sh LABEL 1.0 <doubleT_obstacle dir> pandar128 legacy $IMAGE $OUTDIR; analyze_generic.py $OUTDIR/LABEL 201
```
Expected for the Falcon bag at rate 1.0: FAULT on frame 2719 only, CAUTION until the mount is confirmed (~19 s), STOP appears at ~23 s after the player command
(130.5 m, 4 frames), then STOP at frame 2950 (127.18 m, ~26.6 s), continuous STOP runs from frame 2981 (123.8 m, ~29.7 s), last STOP 105.7 m at frame 3128.
The images built here (`resense:falcon-demo-1.3`, 2.68 GB) stay on the machine for the 23.10 demo; the containers were removed.

## Files
`scripts/` (trial.sh, recorder.py, analyze.py, analyze_generic.py, extra_checks.py), `summaries/` (one JSON per trial, `extra_checks.txt`),
`raw/trials_raw.tar.xz` (events.jsonl, node.log, player.log, docker stats, times for every trial), `raw/bag_build_receipt.json`, `raw/bag_build.log.xz`,
`raw/docker_build_tail.log`, `raw/person_track.json`.
