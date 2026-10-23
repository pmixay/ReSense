# Original `metadata.yaml` of the six organizer recordings

> **Purpose:** reference copies of the organizers' rosbag2 `metadata.yaml` files, used to prove that a downloaded bag is the original and to show the recorded QoS (reliable).
> **Audience:** team, jury, anyone preparing the data · **Owner:** lane not recorded in the folder or the docs · **Language:** EN
> **Last verified:** 2026-10-22: the six files exist and the numbers below were read from them; the `cmp` checks quoted in section 3 were not re-run (dataset not available) ·
> **Status:** current (reference data, unchanged by any run)

## 1. What was run, when, by whom

Nothing was run: these are copies of files shipped inside the organizers' bags (`rosbag2_bagfile_information`, version 5, sqlite3 storage).
Import date: 2026-10-16, squash commit `44b462e`. The date the copies were first committed is not recorded in the folder; the documents below show
them already in use on 25.09 (`../dry_run_2026-09-25/original_bags.txt`). Who copied them: lane not recorded.

## 2. Result: what the files say

From the files: `reliability: 1` and `durability: 2` in `offered_qos_profiles` of the one topic of every recording. This is why `ros2 bag play` publishes reliable
and why the node subscribes reliable by default (`docs/archive/EXPERIMENTS_log_2026-09.md` line 3022, `docs/ARCHITECTURE.md` (the `input_reliability: auto` paragraph)).
The enum meaning (1 = reliable, 2 = volatile) is the ROS 2 convention, not stated in the files: unverified here.

| recording | topic | `message_count` (top level) | `duration` (ns) |
|---|---|---:|---:|
| `doubleT_obstacle` | `/sensing/lidar/hesai128/pointcloud` | 201 | 20392030296 |
| `doubleT_platform` | `/lidar_points` | 345 | 34419566186 |
| `roundT_doubleT` | `/lidar_points` | 252 | 25071970644 |
| `roundT_pressureGate_roundT` | `/lidar_points` | 268 | 26698780195 |
| `roundT_squareT_pressureGate_squareT` | `/lidar_points` | 545 | 55377499942 |
| `squareT_platform_squareT_switch` | `/lidar_points` | 877 | 88207975932 |

All six: type `sensor_msgs/msg/PointCloud2`, one `.db3` file.

## 3. Supports

* `docs/VM_GUIDE.md` (the data section, a `cmp` loop; line number moves, another lane is editing the file): the `cmp` of a downloaded bag against `bag_metadata/<bag>_metadata.yaml` ("original" check).
* The same check in `../dry_run_2026-09-25/original_bags.txt`, `../vm_2026-09-28/data_recordings.txt`, `../p4_review_r3_h1_2026-10-20/README.md`, `../l16_exposure_2026-10-20/README.md`, `../rejudge_2026-09-26/README.txt` and scripts `../dry_run_2026-09-25_2/diag_host_fastdds/g_runs.sh`, `../vm_2026-09-28/scripts/r_data_a.sh`, `../p4_review_r3_h1_2026-10-20/scripts/prep_bags.sh`.
* `../f1_false_alarms_2026-10-19/scripts/stream_cache.py` (line 260) compares against these files while building the cache.
* `docs/evidence/README.md` section 2, last table row; `docs/README.md` (evidence table row).

## 4. Contents (6 files)

* `doubleT_obstacle_metadata.yaml`, `doubleT_platform_metadata.yaml`, `roundT_doubleT_metadata.yaml`, `roundT_pressureGate_roundT_metadata.yaml`, `roundT_squareT_pressureGate_squareT_metadata.yaml`, `squareT_platform_squareT_switch_metadata.yaml`: one per recording, named `<bag>_metadata.yaml`.

## 5. Caveats

* In three files the per-file `message_count` under `files:` differs from the top-level count: `doubleT_obstacle` 205 vs 201, `roundT_squareT_pressureGate_squareT` 555 vs 545, `squareT_platform_squareT_switch` 883 vs 877. The other three have equal numbers. Cause not investigated (the frame counts used by the detector are 201 and so on, per the top-level field); unverified.
* The files hold no data, only metadata. The set O recording `cloud_with_fake_obj` and the 20-minute ride are not covered here.
* Byte equality with the bags is a claim of the documents in section 3; this folder cannot show it without the dataset.
