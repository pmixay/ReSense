# P4 independent review of the 1.2.0 candidate, 18.10

Candidate: `work/n5-labels-c2-acceptance` at **`0bbc6ed`** (measured detector source `e9d8fc6`; seal
`b85a9306…`, 38 files). Baseline: sealed 1.1.0 (`main` `3b7d7aa`). Runtime of the P4 protocol
(`OPENBLAS_CORETYPE=Haswell`, one thread); native library built from the unchanged `native/`. No detector code
touched. This is the P4 review P1 asked for; it is **not** a release, a J1 score or a G3 run.

**Result: no blocking finding.** With the default configuration the candidate makes the same decisions and detections as
1.1.0 on everything run here; the only intended change (no GO before the orientation is confirmed) shows where
expected. Three should-fix items and the open limitations are below.

## What was run

| check | how | result |
|---|---|---|
| seal | `detector_freeze.py verify`; every manifest hash re-computed from the git blobs of `0bbc6ed`; every tracked detector file is in the manifest | **PASS**, 38 / 38 files match, none missing |
| X3 robustness battery | `robustness_battery.py -j 2 --reference` the 1.1.0 Linux battery ([battery_1.2.0.json](battery_1.2.0.json)) | **PASS**, 40 / 40 cases. Beyond the driver: all **29,765** processed rows equal 1.1.0 in every field except wall-clock timing and latency messages. Positive control: the same row comparison flags all 40 entries between the Haswell and Prescott-kernel 707ea9c runs |
| new recordings (`run_new_recordings.sh`) | full run from a fresh work folder; Falcon and switch inputs downloaded and decoded fresh | **28 PASS, 0 DIFF, 0 MISSING** ([new_recordings_compare.txt](new_recordings_compare.txt)) |
| explicit sideways mounts (P1's launch axes) | independent script ([explicit_mount.py](explicit_mount.py)): P4's remount transform, then `sensor.forward/left/up` as in P1's launch commands, full recordings | Corrected cloud equals the upright one (max difference **0.0 m**). Cases 4 and 5 equal the upright run on **every frame** of both recordings (545 empty: 0 STOP; 201 obstacle: 193 STOP) in decision, detection count and mount status ([summary](explicit_mount_summary.json)). The distance field was not compared (the script read a wrong attribute name) |
| code review of the 1.1.0 → 1.2.0 diff | fresh-context agent: code reading, 332 focused unit tests, an A/B run of both versions on synthetic frames | no blocking finding; findings below |

Raw rows of X3 and the explicit-mount runs: [x3_raw_1.2.0.tar.xz](x3_raw_1.2.0.tar.xz) ([SHA256SUMS](SHA256SUMS)).

## Findings

**Should fix (not blocking):**
1. **The node's `keep_up_axis` launch parameter always overrides the config file** (`detector_node.py:329`, again
   at `:808`; new in 1.2.0, confirmed in source). A custom config with `keep_up_axis: false` is silently searched over 8
   orientations instead of 24. No effect with the default YAML.
2. **`/resense/reset_input` is always on and clears the STOP latch** (`detector_node.py:459, 754–793`). It only
   works while the input is silent and the queue is empty, and the published state becomes FAULT, not GO; but "STOP
   held" is lost during that silence. Switching `sensor_profile` at runtime uses the same path.
3. **The orientation guard runs by default and keeps the clear range at 0 until rails are observed**
   (`health.py:215–227`). That is conservative, but it is a real default change in health level and clear distance:
   "no change against 1.1.0" holds for detections and decisions on the recordings measured, not for every field in
   every case. Should be in the CHANGELOG.

**Notes:** opt-in replay replaces the detector's whole state on the adoption frame (`detector.py:289`); bounds
(≤ 4 frames, 32 MiB) are enforced as documented. The opt-in N6 extension widens the claimed clear range and needs
its own acceptance before use. Dust modules are not imported by the detector or node.

## Still open (not fixed by 1.2.0)

* **L16 automatic sideways mounts:** without explicit axes, rolled mounts still give 395–509 false STOP frames on the
  empty recording, and one case turns 6 real STOP frames into CAUTION. Our earlier suggested fixes would not work
  (corrected in [B4](../orientation_2026-10-18/README.md)). Explicit axes are a workaround for known mounts only.
* **L10 / K1 curve axis bias**, N3 dust robustness, N6 platform person below 60 m: unchanged.

## Not covered by this review

* The **regression gate** was not re-run by P4: this container has no ride cache. P1's fresh 18,329-row gate on
  `e9d8fc6` is their evidence, not ours.
* The **real ROS node, Docker image and DDS** (rclpy is not installed here); P4's harness uses the judge's node replica.
* The opt-in profiles (conservative clear range, replay, Falcon profiles, N6) on real data.
* G3: not run, by rule.
