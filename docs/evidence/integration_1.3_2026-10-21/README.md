# Integration 1.3, phase 1 (21.10)

> **Integration agent** of the captain's session, on the user's decisions of 21.10. Branch `claude/integration-1.3`.
> **Measured tree:** `fae6dbc` (all phase-1 merges). Later commits on the branch change only evidence, docs and
> one comment line in `resense/config.py` (`git diff fae6dbc HEAD -- resense native configs ros2_ws` = comment only).
> **Control:** a fresh detached worktree of v1.2.0 `3b73bbe`. G3 (held-out) not touched. No tag, release or PR.
> `detector_freeze.py verify` fails on this branch (expected: `resense/` changed; reseal is phase 2).
> **Status: incomplete.** The regression gate, X3, the K2 range jobs and the five empty recordings are **not run**:
> they need the six Pandar recordings, and Google Drive answers "Quota exceeded" for `Датасет.zip` after the first
> 448 MB of 3.94 GB (ranged requests; full requests are refused at once) — the same block the K2 reviewer met.
> A ranged downloader retries every 3 min (`scripts/range_dl.sh`).

## 1. What was merged (in order, `git merge --no-ff`, first parent = this branch)

| commit | what | conflicts |
|---|---|---|
| `fbaded6` | merge `claude/k1-k2-1.3` @ `67051c5` (K2 union r3, detector `b88d759`, switch off) | none |
| `944acc7` | **K2 union on**: both YAMLs changed by exactly `k1_k2_2026-10-21/cand_eval_commit.patch` (`git diff` of the two files equals the patch byte for byte, index hashes included); the four class defaults in `resense/config.py` set to the same values (rule: code and both YAMLs agree; `sync_params.sh --check` passes) | — |
| `09d01e8` | merge `claude/falcon-clear-distance-1.3` @ `16efbcc` (`health.clear_lost_bed`, `clear_round_down` on) | none |
| `79f132b` | F3: `clear_lost_bed` comment, Falcon frame range 4361-4410 → 4359-4410 (52 rows) | — |
| `a02bb5b` | merge `claude/track-opinion-1.3` @ `73708f4` (`tracking.doubt_falcon`, default true; off-by-default model file) | none |
| `fd40c5f`, `ddbe98a`, `62c40ce`, `fae6dbc` | evidence only: `falcon-ros-demo-1.3` @ `1faf99a`, `x2-ledger-1.3` @ `bfd3fa5`, `k1-k2-review-1.3` @ `adaeb78`, `falcon-clear-distance-review-1.3` @ `f9f70c4` | none; `git diff HEAD^1 HEAD -- resense native configs ros2_ws` empty for each (x2-ledger adds `scripts/false_stop_ledger.py` and `tests/test_false_stop_ledger.py`) |
| `325b2e5` | the `clear_lost_bed` comment names both Falcon paths: manual 52 rows 4359-4410, `falcon_ros` 50 rows 4361-4410 (measured, §3) | — |
| `cf262b9` | F2: `docs/ARCHITECTURE.md`, `docs/ALGORITHM.md` set O figure re-measured (§3) | — |

**Not merged, stopped as instructed:** `claude/f1a-bounded-review-1.3` (`15c3d0f`) and
`claude/falcon-far-range-review-1.3` (`f0f3b8d`) carry their lanes' detector code (`lowobj.py` / `farline.py`,
`config.py`, both YAMLs; +102 / +207 lines under `resense/ configs/ ros2_ws/`), i.e. phase-2 lanes. Their evidence
comes in with phase 2. `claude/falcon-far-range-1.3` and `claude/f1a-bounded-1.3` not merged (phase 2).

**Tests changed by the switch-on (more than the two the K2 review names).** The K2 author evaluated with the YAMLs
on and the class defaults off. With the class defaults on too, 9 tests fail: the two default-pinning tests (now pin
the 1.3 values: `test_switches_default_in_code_and_both_parameter_files`, `test_union_default_on_in_code_and_both_parameter_files`),
six v5 tests of `test_k1_k2_axis.py` (their all-off base `OFF` now also sets `axis_joint_union=False`) and
`test_late_candidates.py::test_k2_variant_b_in_the_station_scene` (sets `axis_joint_union=False` explicitly). These
tests build their variant from `DetectorConfig()`; the change keeps them testing the variant they name, not the union.

## 2. Combined result against v1.2.0 and against each lane's own claims

Trees: **ctl** v1.2.0 `3b73bbe`; **k2** `944acc7` (K2 on); **preg2** `79f132b` (K2 + clear distance);
**comb** `fae6dbc` (all phase-1 lanes). Each step is compared with the one before it, so every changed row is
attributed to the lane that changed it.

| row | ctl (v1.2.0) | comb | lane claim | holds? | attribution |
|---|---|---|---|---|---|
| Full test suite | — | **2,541 passed**, 8 deselected | — | — | `test_rail_start.py::…standing_fresh_start_do_not_stop` (needs the ride) fails **identically on v1.2.0** (same assertion, same values): pre-existing, not the integration |
| Regression gate, no `--allow` | — | **NOT RUN** (six recordings missing) | K2: exit 0 | unverified | — |
| X3 paired | — | **NOT RUN** (decoded A, D, `doubleT_obstacle` missing; set O decoded is ready) | K2: 0 / 260 | unverified (neither the reviewer nor I re-ran it) | — |
| K2 range jobs (37) at the same placement | — | **NOT RUN** (A, B, C, D missing) | K2 review: 36/37 identical, D_cube05 frame 330 one frame later (accepted) | unverified | — |
| Ride events / STOP episodes / STOP frames | 23 / 26 / 111 | **25 / 29 / 119** | K2: 25 / 29 / 119, new frames piece 2 1066-1069, 1071-1072, 1317-1318 | **yes, same frames**; 0 STOP lost | all K2 (ctl→k2); clear distance and track opinion change no ride decision |
| Five empty recordings, STOP episodes | — | **NOT RUN** | K2: 11 → 11 | unverified | — |
| Set O STOP frames / episodes | 450 / 8 | 450 / 8, 0 lost, 0 new | K2: identical | yes | — |
| Falcon manual: person STOP frames lost (of 1,360) | — | **0** | K2: 0 | yes | — |
| Falcon manual: first person STOP | 2972, 124.84 m | **2958, 126.36 m** | K2: same | yes | K2 |
| Falcon manual: new STOP frames | — | 33, all at the control's person detection | K2: 33 | yes | K2 |
| Falcon manual: STOP episodes (outside the person) | 7 (2) | 12 (2) | K2: 7 → 12 (2 → 2) | yes | K2: +5 splits inside the person's sequence |
| Falcon `falcon_ros`: person STOP frames (lane labels) | 1,369 | 1,398, 0 lost | track opinion ctl: 1,369 / 127.1 m | yes (ctl) | K2: +29, all person |
| Falcon `falcon_ros`: first person STOP | 2950, 127.07 m | 2950, 127.07 m | — | — | — |
| Falcon `falcon_ros`: STOP episodes / false | 8 / 3 | 8 / 3 | track opinion: 3 → 3 | yes | — |
| Falcon clear: `lost_bed` rows → clear 0 | — | manual **52, 4359-4410** (35 CAUTION, 17 STOP, 0 GO); `falcon_ros` **50, 4361-4410** (28 / 22 / 0) | 52, 4359-4410, 35 / 17 | yes (manual); `falcon_ros` not claimed | clear distance (k2→preg2) |
| Falcon clear lowered / raised | — | 1,006 / 0 (both paths) | 1,006 / 0 | yes | clear distance; K2 lowers none on Falcon |
| Falcon STOP rows with clear beyond the nearest STOP detection | 575 (manual), 570 (ros) | 0, 0 | 575 → 0 | yes | clear distance |
| Falcon residual 4411-4414 | — | manual 20.3 / 18.5 / 16.6 / 40.0 m (unchanged) | 4 residual frames | yes | not fixed by the lane, as it states |
| Marked bags STOP frames | 126 / 185 / 142 | 126 / 185 / 142, every marked object the same frames and first STOP | K2: identical | yes | — |
| Marked bags, other decisions | — | tunnels 191-193 GO → CAUTION (warnings at 118-124 m, 6.7-7.2 m lateral) | K2 review: same 3 frames | yes | K2 |
| Track opinion identity (preg2 vs comb), every non-timing field | — | Falcon 2 × 4,443 rows **0 differ**; ride 11,271 **0**; marked bags 1,667 **0** | ID row: identical at defaults | **yes, on the combined tree** | — |
| Clear distance changes only `clear` (k2 vs preg2) | — | Falcon 0 other rows; ride 0 (1,890 clear/candidate values lowered, 0 raised); marked bags 0 (370 lowered) | only clear, only down | yes | — |
| Set O "clear past an object in the gauge" (F2) | **282 / 605, 68 GO** | **99 / 605, 43 GO**; > 1 m: 67 (39 GO) in both | docs said 300 / 605, 68 GO | docs corrected | clear distance (sub-metre: round-down / lost bed) |

**False-alarm budget** (user's terms, +11 STOP episodes over Falcon + ride + five empty, each attributed): ride +3
(K2: piece 2 frames 1066-1072 → 2 episodes, 1317-1318 → 1; traced by the K2 review, finding 3); Falcon manual +5,
all splits inside the person's own STOP sequence (outside the person 2 → 2), `falcon_ros` +0; five empty: **not
measured here** (K2: 11 → 11). Booked: **+3 attributed false episodes, +8 counting the Falcon splits literally**,
of +11. No lost or delayed true STOP found in what was run; the accepted D_cube05 delay is in the range jobs, which
were not run.

**Combination changes beyond the lanes' own claims:** none in what was run. Two rows not claimed by any lane:
(1) the `falcon_ros` run of `lost_bed` rows is 50 rows 4361-4410, not the manual path's 52 (the original config
comment had the `falcon_ros` range); (2) on the ride K2 raises the diagnostic `health.candidate_distance` once
(piece 2 frame 1071, 104.1 → 118.5 m, a K2 new STOP frame) while `clear_distance` stays 104.1 m, bounded by the STOP
obstacle; no `clear_distance` is raised anywhere.

## 3. What was checked and how

* **Data identity.** Falcon stream SHA-256 `90dea27d…5611`, 6,758,209,772 bytes, both streams = the published
  value; marked-bag archive `04d176b4…8682760` = the intake value; ride 221 splits, archive size and SHA-256
  verified by `cache_extended_ride.py`; set O 1,510 frames.
* **Control reproduces history.** The control's manual Falcon record equals P4's committed record
  (`l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz`) in every shared field of all 4,443 rows (0 differ; the two
  extra keys `falcon_multi.py` writes skipped); control figures equal the published v1.2.0 ones (Falcon 1,360 /
  2972 / 124.84 m manual, 1,387 STOP / 8 / 3 / 127.1 m `falcon_ros`; ride 23 / 26 / 111; markers 126 / 185 / 142).
* **Comparators have positive controls.** `rows_diff.py --inject` plants one change: reported as exactly one extra
  differing row (Falcon, markers); the K2 review's `score_falcon.py` and its own v5c positive control are reused.
* **Every changed decision looked at.** Falcon manual: all 33 new STOP frames are at the control's detection /
  warning of the person (`score_falcon.py`: same object, ≤ 1.5 m); `falcon_ros`: all 29 new STOP frames are
  person-labelled by the track-opinion lane's labeller (`falcon_eval13.py`: person STOP frames 1,369 → 1,398, STOP
  frames 1,387 → 1,416); ride: the 8 new frames are the K2 review's traced frames; markers: the 3 tunnel frames
  printed.
* **Instrumentation.** Records come from plain runs (`falcon_multi.py`, `judge_runner_set.py` without overrides,
  `eval_real.py`); no traced run is used for a number.
* **Comparator limits.** Health `level` is not compared on rows that carry a machine-speed latency message (four
  trees ran at once; most marker rows, ~900 ride rows); the decision level and all other fields are.
* **Per-frame time** (reported, not gated): not measured cleanly here (trees shared 4 vCPUs); the K2 review's table
  (+25-38 % p50) stands.

## 4. What failed, what is unverified

* **Not run (data):** regression gate without `--allow`, X3 paired, K2 range jobs (same placement), five empty
  recordings, decoded caches for B6. Cause: Google Drive quota on `Датасет.zip`.
* `test_rail_start.py::test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop` fails on v1.2.0 and on
  the combined tree identically (pre-existing).
* Not touched: the same stale "300 of 605" sentence in `docs/EXPERIMENTS.md` and `gitbook/reference/results.md`
  (only ARCHITECTURE / ALGORITHM were named).
* The ROS display, the node graph, timing on a quiet machine.

## 5. Reproduce

Python 3.12 venv (numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, open3d 0.19.0, rosbags 0.11.5), native built per
tree, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `RESENSE_REPO` / `PYTHONPATH` per tree (each run checks
`resense.__file__`: `runs/falcon/*.which` equivalent in the logs). Trees: `git worktree add --detach <dir> <commit>`.

* Falcon: `scripts/falcon.sh` (ctl + comb) and `scripts/falcon2.sh` (k2 + preg2): one stream teed to
  `track_opinion_2026-10-21/scripts/falcon_multi.py` per tree with `runs/falcon/spec.json` (manual, `falcon_ros`).
* Marked bags: `scripts/markers.sh` (four trees, `k1_k2_2026-10-21/scripts/judge_runner_set.py`).
* Set O rows: `scripts/setO_rows.sh`; ride: `scripts/ride_intake.sh`, `scripts/ride_rows.sh` (`eval_real.py`, 8 pieces).
* All numbers above: `scripts/make_outputs.sh` → `out/falcon.txt`, `out/falcon_clear.txt`, `out/markers.txt`,
  `out/setO.txt`, `out/ride.txt` from `runs/` (xz, about 9 MB).
