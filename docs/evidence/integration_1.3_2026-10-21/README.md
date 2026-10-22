# Integration 1.3 (21–22.10): phases 1 and 2, version 1.3.0, reseal

> **Integration agent** of the captain's session, on the user's decisions of 21–22.10. Branch `claude/integration-1.3`.
> **Control:** a fresh detached worktree of v1.2.0 `3b73bbe`, run on the same data in every row. G3 (held-out) not
> touched. No tag, release, PR or push to `main`.
> **Trees measured** (each a detached worktree with its own native build; `resense.__file__` checked per run):
>
> | name | commit | content |
> |---|---|---|
> | ctl | `3b73bbe` | v1.2.0 |
> | k2 | `944acc7` | + K2 union r3, switched on |
> | preg2 | `79f132b` | + Falcon clear distance |
> | comb | `fae6dbc` | + track opinion 1.3 and the phase-1 evidence branches (phase-1 tree) |
> | nofix | `754d28e` | + far range rev 2, merged, **without** the save/restore fix |
> | **fin** | **`671ac9e`** | + the save/restore fix (`36c6cc4`) + F1a evidence: **the measured detector tree** |
> | rel | `ed67d25` | `fin` + node `clear_range_policy` default, two YAML comments, version 1.3.0: **the sealed commit** |
>
> `git diff 671ac9e ed67d25 -- resense native configs ros2_ws/src/resense_ros/config setup.py pyproject.toml` = the
> version string and two YAML comment lines; the release gate on `ed67d25` is the seal's evidence (§6).

## 1. What was merged and how (`git merge --no-ff`, first parent = this branch)

| commit | what | conflicts / notes |
|---|---|---|
| `fbaded6` | `claude/k1-k2-1.3` @ `67051c5` (K2 union r3, detector `b88d759`, off) | none |
| `944acc7` | **K2 union on**: both YAMLs changed by exactly `k1_k2_2026-10-21/cand_eval_commit.patch` (byte for byte, index hashes included); the four class defaults in `resense/config.py` set to the same values | 9 tests, not 2: see below |
| `09d01e8` | `claude/falcon-clear-distance-1.3` @ `16efbcc` (`clear_lost_bed`, `clear_round_down` on) | none |
| `79f132b` | review F3: the `clear_lost_bed` comment's frame range; `325b2e5` later names both Falcon paths (manual 52 rows 4359-4410, `falcon_ros` 50 rows 4361-4410, measured §3) | — |
| `a02bb5b` | `claude/track-opinion-1.3` @ `73708f4` (`tracking.doubt_falcon`, default true) | none |
| `fd40c5f` `ddbe98a` `62c40ce` `fae6dbc` | evidence only: `falcon-ros-demo-1.3` @ `1faf99a`, `x2-ledger-1.3` @ `bfd3fa5` (adds `scripts/false_stop_ledger.py` + its test), `k1-k2-review-1.3` @ `adaeb78`, `falcon-clear-distance-review-1.3` @ `f9f70c4` | none; `git diff HEAD^1 HEAD -- resense native configs ros2_ws` empty for each |
| `cf262b9` | review F2: set O figure in `docs/ARCHITECTURE.md` / `ALGORITHM.md` re-measured (§3) | — |
| `754d28e` | `claude/falcon-far-range-1.3` @ `aec8b69` (far range rev 2, detector `c431b2e`), after its review's **ACCEPT WITH CONDITIONS** of `500a839` | **`resense/detector.py`**: clear distance's `bed_conflict` block and far range's report cap / lag block were added at the same place; independent (neither reads what the other writes): both kept, bed block first |
| `175d1f4` | `claude/falcon-far-range-review-1.3` @ `500a839` (evidence only; built on rev 1 `ff59349`, which is an ancestor of the lane head, and changes no code beyond it) | none |
| `36c6cc4` | **integration fix** (semantic conflict, no textual one): K2's `_curve_clusters` runs `_corridor` with `_far_axis` None, which resets the far-range state `_corridor` writes (`_union_shift`, `_far_report_cap`); `_far_report_cap` is read afterwards by the health stage. Both now in the saved / restored tuple. Test `test_union_curve_pass_keeps_the_far_range_state_of_the_frame` fails on `754d28e`, passes here. Effect measured in §2 | — |
| `671ac9e` | F1a as evidence only: `docs/evidence/f1a_bounded_2026-10-21` from `claude/f1a-bounded-1.3` @ `6cc7445`, `f1a_bounded_review_2026-10-21` from `claude/f1a-bounded-review-1.3` @ `15c3d0f`; **no F1a detector code**, its switch stays off | — |
| `bae1355` | **node `clear_range_policy` default `conservative`** (user decision 22.10): `detector_node.py`, `detector.launch.py`, `scripts/play_bag.sh`, tests (§4) | — |
| `2a64cfe` | the stale "K2 held off" comments in both YAMLs (comment only, `sync_params.sh --check` passes) | — |
| `ed67d25` | version 1.3.0 in the four declarations | — |

**Not merged in phase 1, as instructed:** `claude/f1a-bounded-review-1.3` and `claude/falcon-far-range-review-1.3` (at
the time `f0f3b8d`) carried their lanes' detector code. The far-range review came in with phase 2; F1a stays evidence only.

**Tests changed by the switch-on (more than the two the K2 review names).** The K2 author evaluated with the YAMLs on and
the class defaults off. With the class defaults on too (code and both YAMLs must agree), 9 tests failed: the two
default-pinning tests (now pin the 1.3 values) and seven tests that build their variant from `DetectorConfig()` (the
v5 tests of `test_k1_k2_axis.py` through their all-off base `OFF`, and `test_late_candidates.py::test_k2_variant_b_in_the_station_scene`):
they now set `axis_joint_union=False` explicitly and keep testing the variant they name.

## 2. Result table: the final tree against v1.2.0, and against each lane's own claims

Each lane step is compared with the tree before it, so every changed row is attributed (`rows_diff.py`: every field
except timing and machine-speed latency messages; `stop_diff.py`: STOP frames lost / new, episodes).

| row | v1.2.0 | final | lane claim | holds? | attribution |
|---|---|---|---|---|---|
| **Full regression gate, no `--allow`** (seal baseline 29.09) | PASS | **PASS** (`fin`, and `rel` §6) | K2, far range: PASS | yes | — |
| **X3 paired**, fresh v1.2.0 reference, 40 cases / 260 comparisons | MEASURED | **PASS, 0 changed**; per frame 0 STOP frames lost or gained, 0 changed frames (planted loss found) | K2: 0 / 260 (author only; never re-run before) | **yes** | — |
| Ride events / STOP episodes / STOP frames | 23 / 26 / 111 | **25 / 29 / 119** | K2: same, new frames piece 2 1066-1069, 1071-1072, 1317-1318 | yes, same frames | K2 (ctl→k2); no other lane changes a ride decision |
| **Five empty recordings**, STOP episodes / frames | 11 / 37 | **11 / 37** | K2: 11 → 11 | yes | — |
| Set O STOP frames / episodes | 450 / 8 | 450 / 8 | identical | yes | — |
| Pandar gate rows, decision / detection / warning (15,269) | — | 8 changed, all ride piece 2 above (K2); 0 STOP frames lost on any recording | — | — | K2; clear distance lowers only `clear` (3,142 values, 0 raised); track opinion and far range: 0 rows |
| Falcon manual: person STOP frames lost (of 1,360) | — | **0** | K2: 0 | yes | — |
| Falcon manual: first person STOP | 2972, 124.84 m | **2958, 126.36 m** | K2: same | yes | K2 |
| Falcon manual: STOP episodes (false) | 7 (2) | 12 (2) | K2: 7 → 12, splits inside the person | yes | K2; far range is off on the manual path (fin = comb, 0 rows) |
| Falcon `falcon_ros`: person STOP frames (lane labels) | 1,369 | **1,520**, 0 lost | far range: 1,520 | yes | K2 +29 (comb), far range +112 |
| Falcon `falcon_ros`: first / held person STOP | 127.1 m / — | **150.5 m (frame 2756) / 129.4 m (2927)** | far range review: 150.5 / 129.4 | yes | far range |
| Falcon `falcon_ros`: STOP episodes (false) | 8 (3) | **13 (0)** | far range review: 13 (0) | yes | far range: the 3 false episodes (frames 25-28, 125, 2312-2314) are the only "lost" STOP frames |
| Falcon `falcon_ros`: GO with the person inside the reported clear / monitored range | 0 / 0 | **0 / 0** | far range: 0 new | yes | **without the fix (`754d28e`): 0 / 4**, and 728 rows with a larger clear / monitored range |
| Falcon 6-start table (`falcon_ros`, far-range review's `evalrows.py` / `person_frames.py`) | first 123.4-127.3, held 114.4-123.0 m, false 1-3 per start, 1 GO-in at start 2400 | first 150.4-150.5, held **129.4-135.6 m**, false 0 (1 at start 1800), GO-in 0 | review: held 129.4-135.5 | yes; held +0.1-0.3 m farther at starts 600 / 1200 / 2100 (earlier, not a loss) | far range (+K2) |
| Falcon clear distance: `lost_bed` rows → clear 0 | — | manual **52, 4359-4410** (35 CAUTION, 17 STOP, 0 GO); `falcon_ros` **50, 4361-4410** (28 / 22 / 0) | 52, 4359-4410 | yes (manual); `falcon_ros` not claimed | clear distance |
| Falcon clear lowered / raised (comb vs ctl) | — | 1,006 / 0, both paths; STOP rows with clear beyond the nearest STOP detection 575 → 0 (manual), 570 → 0 (ros) | 1,006 / 0, 575 → 0 | yes | clear distance |
| Falcon residual 4411-4414 | — | manual 20.3 / 18.5 / 16.6 / 40.0 m, unchanged | 4 residual frames | yes | not fixed by the lane, as it states |
| Marked bags, STOP frames | 126 / 185 / 142 | identical; every marked object the same frames and first STOP | K2: identical | yes | — |
| Marked bags, other decisions | — | tunnels 191-193 GO → CAUTION (warnings at 118-124 m, 6.7-7.2 m lateral) | K2 review: same 3 | yes | K2 |
| K2 range jobs at the **control's** placement (37) | — | 36 identical; **D_cube05 loses frame 330** | K2 review: same (accepted delay, train standing) | yes | K2 |
| K2 range jobs at the **final tree's** placement | — | 0 frames lost in any job; B person 46.49 → 71.19 m, C person 76.89 / 84.25 → 94.58 / 104.98 m, B cube05 50.03 → 71.19, C cube05 75.42 → 90.15, `S_person_100` 248 → 255 | K2 review: same | yes | K2 |
| K2 range jobs at own placement (the judge harness moves the object with the published track) | — | drops D_cube03 83 → 0, S_cube05_100 94 → 32, S_person_150 90 → 0, C_cube1 85.72 / 94.58 → 84.25 / 91.63, B_cube03 41.19 → 39.42 m | K2 review finding 1: same | yes | placement, not detector (0 at the same placement) |
| Track opinion identity (preg2 vs comb), every non-timing field | — | gate 15,269 rows 0; Falcon 2 × 4,443 0; ride 0; marked bags 1,667 0 | identical at defaults | **yes, in the combination** | — |
| Full test suite | 2,541 on `comb` | **2,551 passed** on `fin`, 1 failed: `test_rail_start.py::…standing_fresh_start_do_not_stop` | — | — | **fails identically on v1.2.0** (same assertion and values; it needs the ride cache): pre-existing |
| Set O "clear past an object in the gauge" (review F2) | **282 / 605, 68 GO** | **99 / 605, 43 GO**; > 1 m: 67 (39 GO) in both | docs said 300 / 605, 68 GO (the 28.09 detector) | docs corrected | clear distance (sub-metre) |

**False-alarm budget** (user's terms: at most +11 STOP episodes over Falcon + the ride + the five empty recordings,
each attributed): ride **+3** (K2: piece 2 frames 1066-1072 → 2 episodes, 1317-1318 → 1; traced in the K2 review,
finding 3); five empty **+0**; Falcon manual **+5** and `falcon_ros` **+5**, every one inside the person's own STOP
sequence (false episodes 2 → 2 and 3 → 0). Attributed false episodes: **+3 on the ride, −3 on `falcon_ros`**; counted
literally per path: +8 (ride + one Falcon path). Inside +11 either way. **Lost or delayed true STOP:** none, except the
accepted K2 delay (D_cube05 frame 330, one frame, train standing).

**Combination changes beyond the lanes' own claims:** (1) the K2 / far-range state interaction, fixed (`36c6cc4`, rows
above); (2) the `falcon_ros` `lost_bed` run is 50 rows 4361-4410 (the lane measured the manual path); (3) on the ride K2
raises the diagnostic `health.candidate_distance` once (piece 2 frame 1071, 104.1 → 118.5 m, a K2 new STOP frame) while
`clear_distance` stays 104.1 m; (4) the 6-start held STOP is 0.1-0.3 m farther than the far-range review's rev-2 rows at
three starts. No `clear_distance` is raised anywhere.

## 3. The clear-distance doc figure (review F2)

Definition reproduced from the 28.09 table: set O frames where a plausible labelled object has points in the strict
envelope (`n_in_envelope > 0`), and `clear_distance` lies beyond its near face. It gives exactly 605 frames and 68 GO on
v1.2.0, but 282 frames (the "300" was the 28.09 detector). Combined: 99 (43 GO); more than 1 m past: 67 (39 GO) in both.
`docs/ARCHITECTURE.md` and `docs/ALGORITHM.md` corrected; the same stale sentence remains in `docs/EXPERIMENTS.md` and
`gitbook/reference/results.md` (not named in the task; for the docs pass). Script `scripts/clear_past_object.py`,
output `out/clear_past_object_setO.txt`.

## 4. The node's range policy (user decision 22.10)

`clear_range_policy` now defaults to `conservative`; `clear_range_policy:=legacy` restores the old range. Checked on the
final tree by replaying the node's own path (`evaluate_decision`, then `candidate_ranges` with the small-target cap):

| data | `range_sensor_model` | decision differs | detections / warnings / flags changed | clear lowered | raised | → 0 |
|---|---|---|---|---|---|---|
| Falcon manual path, 4,443 | unknown (manual profile) | 0 | 0 | 4,390 | 0 | **4,390** |
| Falcon `falcon_ros`, 4,443 | falcon_prime | 0 | 0 | 4,050 | 0 | 0 |
| Pandar gate rows (six recordings, set O, ride), 15,269 | unknown | 0 | 0 | 15,257 | 0 | **15,257** |
| same | pandar128 | 0 | 0 | 12,047 | 0 | 1 |

Monitored range: never raised. **Finding for the captain:** the conservative profile needs a sensor prior. With
`range_sensor_model` unknown, which is the default `manual` profile and the image's default command
(`ros2 launch resense_ros detector.launch.py freshness_mode:=replay`), the node reports **clear distance 0 on every
frame**. With `pandar128` the range is capped at 88.7 m (legacy median 119.1 m). Decisions are unaffected. The user's
rule ("only the reported range changes, never upward") holds; whether a constant 0 under the default launch is wanted
is the user's call. The new test `test_default_clear_range_policy_is_conservative_and_needs_a_sensor_prior` pins this.

## 5. What was checked and how

* **Data identity.** Six recordings: `Датасет.zip` SHA-256 `e2316680…68be` (first 450 MB from Google Drive, the rest
  from the team storage; the whole file verifies), frame counts 201 / 345 / 252 / 268 / 545 / 877 as VM_GUIDE §2.4,
  `doubleT_obstacle` and `roundT_doubleT` bag SHA-256 OK. Falcon stream `90dea27d…5611` in all four streams. Marked
  bags `04d176b4…8682760`. Ride 221 splits, archive size and SHA-256 verified. Set O 1,510 frames.
* **Controls reproduce history.** v1.2.0's Falcon manual record equals P4's committed record in every shared field of
  4,443 rows; gate ride 23 / 26 / 111, five empty 11; Falcon 1,360 / 2972 / 124.84 m (manual), 1,387 / 8 / 3 / 127.1 m
  (`falcon_ros`); 6-start rows equal the far-range review's; range control rows equal the K2 review's; ICP of A equals
  the committed P4 file in all 544 steps (max difference 0).
* **Positive controls.** `rows_diff.py --inject` (one planted change → exactly one extra row); X3 frames planted loss
  found; the K2 review's `score_falcon.py` reused; the save/restore test fails on the merge commit.
* **Every changed decision looked at:** Falcon new STOP frames at the person (manual: `score_falcon.py`, same object;
  `falcon_ros`: lane labels, person STOP frames = STOP frames); ride frames = the K2 review's traced frames; the 3
  tunnel frames printed; the lost `falcon_ros` STOP frames = the control's false episodes.
* **Instrumentation.** All numbers from plain runs (`regression_gate.py`, `eval_real.py`, `falcon_multi.py` /
  `node_policy_falcon.py` (records equal to `falcon_multi`'s, 0 differing rows), `judge_runner_set.py` without overrides,
  `scene_run.py --plain`, `robustness_battery.py`, `prebuild_range.py`).
* **Comparator limits.** Health `level` is not compared on rows carrying a machine-speed latency message (trees ran in
  parallel on 4 vCPUs); the decision level and all other fields are.
* **Per-frame time:** reported, not gated, and not measured cleanly here (shared 4 vCPUs, several trees at once); the K2
  review's table (+25-38 % at p50) stands.

## 6. Version and seal

Version 1.3.0 in `pyproject.toml`, `resense/__init__.py`, `resense_ros/package.xml`, `resense_ros/setup.py`
(`tests/test_release.py` 53 passed). Seal: see the section appended below once the release gate has run.

## 7. Not done / unverified

* The ROS node itself (rclpy) was not run; its range path was replayed with its own functions.
* B6 honesty, the display (`GaugeDisplay`), the K2 review's attacks and the far-range review's 82 scenes / matrices were
  not re-run on the final tree (their lanes' reviews ran them on the lane trees).
* `docs/EXPERIMENTS.md`, `gitbook/reference/results.md`: the stale set O sentence; the deck (`scripts/build_deck.py`)
  still shows 1.2.0.
* Timing on a quiet machine.

## 8. Reproduce

Python 3.12 venv (numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, open3d 0.19.0, rosbags 0.11.5), native built per
tree, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `RESENSE_REPO` / `PYTHONPATH` per tree. Trees:
`git worktree add --detach <dir> <commit>`. Data: VM_GUIDE §2 with zstd caches (`scripts/six.sh`, `scripts/zst_cache.py`;
ride `cache_extended_ride.py`). Scripts in `scripts/`: `gate4.sh` (gate per tree), `x3.sh`, `icp.sh`, `range.sh`
(own placement and both same-placement tags), `falcon.sh` / `falcon2.sh` / `falcon3.sh` (one stream per pair of trees,
`falcon_multi.py`), `starts.sh` + `starts_table.sh`, `markers.sh`, `ride_rows.sh`, `setO_rows.sh`, `falcon_node.sh`
(`node_policy_falcon.py`), `node_policy_rows.py`, `relgate.sh` (the seal's gate). Numbers: `scripts/make_outputs.sh` and
`out/*.txt` from `runs/` (xz).
