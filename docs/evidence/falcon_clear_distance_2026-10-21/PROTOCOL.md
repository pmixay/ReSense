# Protocol: Falcon clear distance (registered before any run of the candidate)

Lane branch `claude/falcon-clear-distance-1.3`, from `6ee469c` (detector bytes equal to v1.2.0: `detector_freeze.py verify`
PASS, digest `6d091081…`). Defect: P4's review of 20.10 (`docs/evidence/p4_review_h_mount_falcon_2026-10-20/README.md`,
section (b), findings 1 and 2). Written and committed together with the acceptance tests `tests/test_clear_lost_model.py`,
which fail on v1.2.0 (12 of 13; the 13th, "only lowers", is a safety property that holds trivially without the
switches). What was done before this commit: the v1.2.0 control run of the Falcon recording and its diagnosis (below);
no run of any candidate.

## Defect, as reproduced on the control (v1.2.0, `6ee469c`, the whole Falcon recording, 4,443 frames)

* The control equals the committed shipped record `l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz` in every
  non-timing field of all 4,443 rows.
* Finding 1: in frames 4373-4414 the track model has no rail pair (`rail_score` < `rails_min_score` 0.05 in all 42 frames,
  rail lock 0 % of the last 20 frames, the monitor's own warning "rail pair found in 0 % of the last 20 frames: track
  model on its prior"). The bed model wanders (`rail_z` 3 m over the mount plane at frame 4396), the person-like cluster
  (0.2-1.6 m over the mount plane) is 1-2.8 m *below* the modelled bed, so it is no corridor candidate; `clear_distance`
  is the monitored range or an unrelated candidate cap. 39 non-STOP frames carry `clear` > 0 (P4 counts 38: frame 4379's
  4.7 m is not beyond the nearest return).
* Finding 2: 575 STOP frames of the detector's own `clear_distance` exceed the nearest STOP detection by up to 0.05 m
  (the node's conservative path, min(·, 48.2 m): 145 of them, as P4 found).

## Documented meaning

`docs/ALGORITHM.md` §4b: `clear_distance` is the metres estimated free: to the nearest confirmed obstacle, otherwise the
monitored range; "a blinded sensor, a **lost track model** or an invalid input make it equal to 0". The code implements
this for health errors and unconfirmed orientation, not for a lost rail pair. The fix therefore reports **0 (unknown)**,
not the distance of the nearest return: with the bed lost there is no frame in which a "return in the corridor" is
defined (the corridor is cut from the bed model), and a 0 is the documented value and never beyond any return.
It is also the established convention of a health error (`level` 2: clear 0 even with a confirmed obstacle).

## Switches (`HealthConfig`, both default **False** until the final commit; class default = `configs/default.yaml` =
`ros2_ws/src/resense_ros/config/detector.yaml`)

* `clear_lost_model`: when the monitor's "track model on its prior" condition holds (`lock_window` history of at least 5
  frames, rail pair found in < `min_lock_rate` of them), `clear_distance` = 0. `monitored_range`, `level`, `messages`,
  detections, warnings, decision unchanged.
* `clear_round_down`: when `clear_distance` is computed with a confirmed obstacle distance or a candidate distance,
  it is rounded down to 0.1 m (`floor`), not to nearest.

Both only lower `clear_distance`. The rule that fired is kept in `HealthMonitor.last_clear_rule`
(`"lost_model"`, `"round_down_obstacle"`, `"round_down_candidate"`, `""`): a trace, not a reconstruction.

## Pre-registered criteria (a switch is turned on by default in the final commit only if every criterion that applies
to it passes; otherwise it stays off and the failing rows are reported)

Control for every paired comparison: a fresh run of the unmodified v1.2.0 tree (`git worktree` of `6ee469c`, native build,
`detector_freeze.py verify` PASS, `resense.__file__` checked), the same cache and the same script.

Falcon (both switches on, ROS-node replica, whole recording, 4,443 rows):

* F1. Every field of the judge record other than `clear` and the timings (decision, obstacle, warning, nearest,
  level, dlevel, msgs, monitored, rail_lock, dets, warns, n_points, track_center, curv, mount, ego) is identical to the control
  in all 4,443 rows; the node path's decision (policy conservative and small_candidate, sensor model falcon_prime) is
  identical in all 4,443 rows.
* F2. `clear` differs from the control only in rows where `last_clear_rule` is non-empty; in every changed row
  new <= old; in `lost_model` rows new = 0; in `round_down_*` rows old - new is 0.0 or 0.1 (a rounding, not a rule).
  Every changed row is listed (`out/clear_changes_*.tsv`).
* F3 (`clear_lost_model`). The 39 control rows 4373-4414 (non-STOP, `clear` > 0) have `clear` = 0, and so does the node
  path (both policies). Checked against the raw points: for these rows the nearest return in the lateral corridor
  (|Y| < 0.9 m) 0.2-1.6 m above the mount plane is computed from the dumped clouds without the track model.
* F4 (`clear_round_down`, and the node path). In every row with a STOP detection `clear` <= the smallest detection
  distance (as recorded, 0.01 m): 0 violations of the 575 (detector) and 145 (node, conservative) of the control.
* F5. Positive controls: the same scripts count 575 / 145 / 39 on the control; `last_clear_rule` is non-empty on
  exactly the rows whose `clear` changed (not "at least").

Pandar (six recordings, set O, ride, set F; the cache of VM_GUIDE §2):

* G1. Full regression gate without `--allow`, against `regression_baseline_2026-09-29_shell_off.json`, with the
  switches on (`--set`, then at the final commit by default): exit 0, every gated metric the same or better.
* G2. Paired per-row diff against the control run (same cache, same script, `eval_real` per-frame rows): every
  non-`clear` field of every row is identical; every changed `clear` is lower; every changed row has the rule
  recorded by `last_clear_rule`; counts per rule and recording are listed. Sample check of changed `clear` values
  against raw points: for every recording the first 10, last 10 and 10 random changed rows of each rule (all of them
  if fewer than 30).
* G3 (cost, `clear_lost_model`). On each of the five obstacle-free recordings and the ride the median `clear`
  falls by no more than 1.0 % and the lost-model rows are no more than 3 % of the frames; set O and the
  doubleT_obstacle STOP frames are unaffected in decision/detections (G2). If G3 fails for a recording, the switch stays off.

X3 (`scripts/robustness_battery.py`, protocol `docs/evidence/p4_start_2026-10-15/PROTOCOL.md`):

* X1. Paired run of the candidate against a fresh control (the battery's own `--reference` comparison): PASS; the
  comparison of all 260 rows has 0 differences in STOP frames, episodes and first-STOP figures (stricter than the
  battery's tolerance, because the change must not touch the decision). No commit during the run.

Open and not claimed by this lane: the `monitored_range`; the unconfirmed object that is not STOP (item 6 of the task is a
finding for the detector owner only); that the person-like object is a person (no surveyed ground truth).
