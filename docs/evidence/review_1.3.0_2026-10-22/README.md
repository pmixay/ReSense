# Independent final-bundle review: release 1.3.0 (22.10)

> **Reviewer:** a fresh Claude session dispatched by the captain's session on the user's request. I wrote none of the
> code under review and changed no file under `resense/`, `native/`, `configs/` or `ros2_ws/`. Nothing was run on the
> held-out G3 set. No tag, PR or push other than to `claude/review-1.3.0`.
> **Under review:** `claude/integration-1.3`, READY commit `a7b7005` ("READY FOR ACCEPTANCE: 1.3.0 sealed, measured
> commit ed67d25"). **Control:** v1.2.0 `3b73bbe`, a fresh detached worktree with its own native build.
> **Measured trees:** `int` = `2a64cfe` (branch head when I started; detector identical to `ed67d25` except the version
> string, see §4.1), `fin` = `ed67d25` (the sealed commit), `ready` = `a7b7005` (seal check), `rev1` = `0eb4dda` (far
> range revision 1, positive control only).
> **Environment:** Python 3.12.3 venv, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, open3d 0.19.0, rosbags 0.11.5;
> `scripts/build_native.sh` in every worktree; every run sets `RESENSE_REPO` / `PYTHONPATH` to its tree and
> `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, and records `resense.__file__` (`raw/*.which`).

## Verdict: **ACCEPT WITH CONDITIONS**

Under the user's terms (range and accuracy first; at most +11 STOP episodes over Falcon + the ride + the five empty
Pandar recordings, each attributed; a lost or delayed true STOP blocks, except the accepted D_cube05 frame 330 → 331)
the detector of 1.3.0 is releasable. Every release row I re-derived from fresh runs agrees with the integration's
claims, and every comparator I used found its positive control:

* **No true STOP lost or delayed** anywhere I looked: the full regression gate's 15,269 Pandar rows (six recordings,
  set O, the ride), X3 (40 cases, 29,765 frames: 0 decision changes at all), the whole Falcon recording on both paths,
  the 6-start Falcon table, the three marked bags, and a sample of 6 K2 range jobs (B, C × person / cube 0.5 / cube 1)
  at the same object placement (0 frames lost, first STOP B person 46.49 → 71.19 m, C person 76.89 → 94.58 m). The
  accepted D_cube05 delay was not re-run (D jobs not in my sample).
* **Range gain is real and on the person:** `falcon_ros` first person STOP 127.3 → 150.5 m, held STOP 123.0 → 129.4 m
  (114.4–123.0 → 129.4–135.6 m over 6 starts); manual path 124.9 → 126.4 m.
* **False alarms inside the bound:** ride +3 false episodes (all K2, piece 2), five empty +0, Falcon false episodes
  2 → 2 (manual) and 3 → 0 (`falcon_ros`). The Falcon STOP-episode count rises +5 on each path, all inside the
  person's own STOP sequence (every added frame is on the person).
* **The K2 × far-range interaction is clean on the sealed tree:** a state probe around every K2 curve pass (8,812
  calls on the full Falcon recording) finds **0** detector attributes changed by the pass; its planted leak is found
  300 / 300 times.
* **Seal:** `detector_freeze.py verify` PASS on `a7b7005`, the manifest names `ed67d25`, version 1.3.0 in all four
  declarations (`tests/test_release.py` 53 passed), both YAMLs equal the class defaults (`sync_params.sh --check`).

Conditions (none is a lost STOP; each is a decision or a statement that must be right before the release notes):

1. **N1 — record the node's new default range policy as a user decision, with its consequences stated (High).**
   `clear_range_policy` now defaults to `conservative`. Decisions are unchanged (0 of 4,443 × 2 Falcon frames and
   1,667 marked-bag frames), but the published clear distance becomes: **0 m on every frame** under the default
   `manual` profile / `range_sensor_model unknown` (the README's documented launch command; 559 GO frames out of 1,667 on
   the marked bags and 8 on Falcon publish "GO, clear 0"); **at most 88.7 m** with `pandar128`; and **at most 48.2 m on
   every Falcon `falcon_ros` frame** (median 102 → 48.2 m), so none of the far-range lane's 130–150 m gain is visible in
   the published clear distance. The `falcon_prime` small-target prior that produces the 48.2 m was **not part of the
   approved 17.10 C2 profile** (its README: "Falcon Prime and unknown profiles return `monitored_small: null`"; the
   Falcon raster entered the prior on 19.10, `0acb18c` / PR #42; v1.2.0 computes the same 48.2 m, but only behind the
   opt-in policy). The decision is not in `docs/DECISIONS.md` (rows 50–57 on
   `claude/p1-work-list-verification-o1hdlh`). The integration README §4 reports the `unknown` → 0 part; the Falcon
   48.2 m cap is not called out there. If the user wants it as is, record it; the alternative is `legacy` as default or
   `conservative` only with an explicit sensor model.
2. **Budget wording (Low).** State the count rule in the release notes: false episodes +3 (ride, K2); literal STOP
   episodes +8 counting the ride and one Falcon path, **+13 if both Falcon paths are summed** (10 of them person
   splits). The integration says "+8 … inside +11 either way"; it is inside +11 only if the Falcon recording counts once.

## 1. Findings (most severe first)

| # | severity | finding | reproducer |
|---|---|---|---|
| N1 | **High** (not blocking: no decision changes) | Node default `conservative`: published clear 0 under the default `manual` profile, ≤ 48.2 m on every Falcon `falcon_ros` frame (unapproved `falcon_prime` prior), ≤ 88.7 m on Pandar; not recorded in DECISIONS. See condition 1. | `scripts/node_policy_unknown.py` (one GO row, 180 m clear: legacy 180, pandar128 88.7, falcon_prime 48.2, unknown 0) → `out/node_policy_unknown.json`; `scripts/node_projection.py` on Falcon and marked-bag records → `out/node_projection.jsonl` |
| N2 | Low (statement) | The +11 budget holds only if the Falcon recording counts once (+8); summing both Falcon paths gives +13, all 10 Falcon additions being splits of the person's true STOP. | `out/falcon/score_{manual,ros}.json`, `out/gate/rows_ctl_int.txt` |
| N3 | Info (time) | Per-frame detector time on Falcon (trees run side by side on 4 vCPUs, not a clean benchmark): p50 19.6 → 27.4 ms (manual), 19.4 → 29.8 ms (`falcon_ros`), p95 32 → 44–48 ms; +40–54 % at p50, larger than the K2 review's Pandar +25–38 %. Reported, not gated. | `out/falcon/timing.txt` |
| N4 | Info (process) | In the `int` worktree `pip install -e` also built `resense/_resense_native.cpython-312-*.so` beside `build_native.sh`'s `_resense_native.so`; the loader takes the first in sorted order (the cpython one). Both come from the same source with the same flags (`setup.py` = `build_native.sh`), and the sealed tree `fin` (only `build_native.sh`) reproduces `int`'s rows exactly (§4.1), so no result depends on it. | `x3/int.json` (`evaluation.native_binaries`) |

No finding against the detector code. The interactions the lane reviews could not see (§3) were checked by code reading
and by measurement and are clean.

## 2. Re-derived release rows (fresh runs, control = fresh v1.2.0)

| row | v1.2.0 (mine) | 1.3.0 (mine) | integration's claim | holds? |
|---|---|---|---|---|
| Full regression gate, no `--allow`, baseline `regression_baseline_2026-09-29_shell_off.json` | PASS | **PASS**, exit 0 (8 gated better, 0 worse) | PASS | yes |
| Gate rows, STOP frames lost / delayed onsets (15,269 rows) | — | **0 / 0** on every recording and ride piece | 0 | yes |
| Ride STOP frames / episodes | 111 / 26 | **119 / 29**; new frames only piece 2: 1066–1069, 1071–1072, 1317–1318 | 25 / 29 / 119, same frames | yes |
| Ride added episodes, attribution | — | 3, all K2: the 1.3 tree with K2 switched back gives v1.2.0's 111 / 26 exactly (§4.3) | K2 | yes |
| Five empty recordings, STOP episodes / frames | 11 / 37 | **11 / 37** (only `squareT_platform_squareT_switch` has any) | 11 / 37 | yes |
| Set O STOP frames / episodes | 450 / 8 | 450 / 8, 0 lost, 0 new | identical | yes |
| `doubleT_obstacle` (labelled) STOP frames / episodes | 193 / 1 | 193 / 1, 0 lost | — | yes |
| **X3 paired**, fresh v1.2.0 reference | MEASURED | **PASS, 260 / 260 comparisons, 0 nonzero deltas; per frame 0 decision changes in 29,765 frames** | PASS, 0 changed | yes |
| Falcon manual: person STOP frames / first / held | 1,360 / 2972, 124.9 m / 3009, 120.5 m | **1,393 / 2958, 126.4 m / 2993, 122.4 m**; 0 lost, 0 delayed onsets, 33 new (all on the person) | 1,360 → 0 lost; 2958, 126.36 m | yes |
| Falcon manual: STOP episodes (false) | 7 (2) | 12 (2) | 7 (2) → 12 (2) | yes |
| Falcon `falcon_ros`: STOP frames / person STOP frames | 1,387 / 1,379 | **1,520 / 1,520**; 0 person frames lost; 141 new, all on the person | 1,520, 0 lost | yes |
| Falcon `falcon_ros`: first / held person STOP | 2950, 127.3 m / 2988, 123.0 m | **2756, 150.5 m / 2927, 129.4 m** | 150.5 / 129.4 | yes |
| Falcon `falcon_ros`: STOP episodes (false) | 8 (3) | **13 (0)**; the only v1.2.0 STOP frames 1.3.0 drops are the 3 false episodes (25–28, 125, 2312–2314) | 13 (0) | yes |
| Falcon GO with the person inside clear and monitored | 0 / 0 (both paths) | **0 / 0** | 0 | yes |
| Falcon: STOP rows with clear beyond the nearest STOP detection | 575 (manual), 570 (ros) | **0, 0** | 575 → 0, 570 → 0 | yes |
| Falcon: clear lowered / raised vs v1.2.0 | — | manual 1,006 / 0; `falcon_ros` 1,977 / 1,062 raised, 1,186 monitored raised (far range), with 0 GO-in-clear | 1,006 / 0 (clear-distance lane) | yes |
| Falcon `lost_bed` rows (clear 0) | — | manual 52 (4359–4410; plus frame 0 = 0 in both trees); `falcon_ros` 50 (4361–4410) | 52 / 50 | yes |
| Falcon 6-start table (`falcon_ros`, stop at 3300) | below | below | first 150.4–150.5, held 129.4–135.6, GO-in 0 | yes |
| Marked bags STOP frames | 126 / 185 / 142 | **126 / 185 / 142**, 0 lost, 0 new, 0 delayed onsets | identical | yes |
| Marked bags other decisions | — | tunnels 3 frames GO → CAUTION, nothing else | tunnels 191–193 | yes |
| Node, decisions under `conservative` vs `legacy` | — | 0 changed (Falcon 2 × 4,443, marked bags 3 × 2 models) | 0 | yes |
| Node, clear under `conservative` | — | never raised; manual/unknown → 0 on every frame; `falcon_ros` ≤ 48.2 m; pandar128 ≤ 88.7 m | 0 raised; unknown → 0 | yes; Falcon cap not stated (N1) |
| K2 range sample at the same placement (B, C × person / cube05 / cube1), first STOP X | B 46.49 / 50.03 / 53.57; C 76.89 / 75.42 / 81.3 m | **B 71.19 / 71.19 / 72.94; C 94.58 / 90.15 / 84.25 m; 0 frames lost in 6 jobs** | B person 46.49 → 71.19, C person 76.89 → 94.58, B cube05 50.03 → 71.19, C cube05 75.42 → 90.15; 0 lost | yes |

**6-start table** (`out/falcon/starts_table.txt`; first / held person STOP in m, STOP episodes (false), GO with the
person inside clear):

| start | v1.2.0 | 1.3.0 | lost person frames | delayed onsets | new STOP frames not on the person |
|---|---|---|---|---|---|
| 0 | 127.3 / 123.0, 8 (3), 0 | 150.5 / 129.4, 13 (0), 0 | 0 | 0 | 0 |
| 600 | 127.1 / 120.5, 9 (2), 0 | 150.4 / 135.5, 8 (0), 0 | 0 | 0 | 0 |
| 1200 | 127.3 / 114.4, 11 (3), 0 | 150.5 / 135.3, 7 (0), 0 | 0 | 0 | 0 |
| 1800 | 127.3 / 122.4, 9 (1), 0 | 150.5 / 129.4, 15 (1), 0 | 0 | 0 | 2704–2705 (the far-range review's R2-2: person merged with the wall) |
| 2100 | 124.0 / 122.3, 8 (2), 0 | 150.5 / 135.6, 8 (0), 0 | 0 | 0 | 0 |
| 2400 | 123.4 / 120.5, 7 (2), 1 | 150.5 / 132.2, 9 (0), 0 | 0 | 0 | 0 |

These equal the far-range review's rev-2 table; held STOP differs by 0.1–0.3 m at starts 600 / 1200 / 2100 (my held
rule: the first person-STOP frame from which ≥ 90 % of the next 30 frames are person-STOP), as the integration also
found. The starts run through `falcon_starts.py` (the node replica of `falcon_multi.py` with a start/stop window), not
the review's `scene_run.py`: an independent path that gives the same rows.

**False-alarm budget:** ride +3 false (K2: 1066–1069 at 116.2 m, lateral −1.18, where v1.2.0 already had a warning on
the same object; 1071–1072 at 104.1 m; 1317–1318 at 68.7 m, lateral −1.69, the K2 review's traced case), five empty
+0, Falcon false −0 (manual) / −3 (`falcon_ros`). Literal STOP episodes: +3 ride, +5 per Falcon path (N2).

## 3. The interactions the lane reviews could not see

**K2 × far range on Falcon curve frames (`36c6cc4`).** Code: `_curve_clusters` sets `self.track = curve`,
`self._far_axis = None`, then calls `_corridor` and `_cluster`. Between them they write `_dy_rail`, `_union_shift`,
`_far_report_cap` (`_corridor`) and `_low_height`, `_near_low`, `_thin` (`_cluster`); `_frame_hd` is written by the pass
itself. All nine are in the saved tuple and restored in `finally`. `_base_in` is written only on the same condition that
calls the pass; `_far_valid_hist`, the far tracker and the tracker are not touched by it. Measurement
(`scripts/curve_state_probe.py`): a wrapper fingerprints every detector attribute (pickle → SHA-1, so nested state
such as the tracker, the far tracker, the buffer and the health monitor is included) before and after every curve pass
on the whole Falcon recording, both paths: **8,812 passes, 29 of them adding a cluster, 0 with any attribute changed**
except the pass's own trace fields. Positive control: the same wrapper with a planted leak (`_far_report_cap` set inside
the pass, then undone): flagged in **300 / 300** passes. Instrumentation: the probed run equals the plain run in every
field of all 2 × 4,443 rows except `level` / `msgs` on 28 / 81 rows carrying a machine-speed latency message
(`decision_level` and decisions identical).

**Clear distance × far-range report cap × node policy.** Detector level: `health.update` takes `wall_drift` already
capped by `_far_report_cap` and by the 3-frame trusted-range history (A7 / A9 / A10); `clear_lost_bed` and
`clear_round_down` act after `monitored` / `clear` are formed and only lower `clear`. Measured: 0 STOP rows with clear
beyond the nearest STOP detection on both paths, 0 rows with clear beyond the nearest warning on `falcon_ros`, 0 GO
frames with the person inside clear at 6 starts and on both full paths. Node level: the conservative projection runs after
the decision (`detector_node.py`: `evaluate_decision` before `candidate_ranges`) and caps `clear` by the small-target
density limit, which dominates everything the far range adds on Falcon (N1).

**`doubt_falcon` × far-range tracks.** The default (`true`) keeps v1.2.0's behaviour (the shipped opinion model applied
whatever the sensor); `sensor_profiles.py` drops the model only under `falcon_prime` when it is set `false`. All Falcon
rows above ran with the default, so the far-range gain already includes the opinion; the opinion code's other change
(features appended by name) is identity at defaults (the integration's row; my Falcon and Pandar rows above are
consistent with it, but I did not run a separate opinion-off toggle).

## 4. What was checked and how

### 4.1 Trees and seal
* `git diff 2a64cfe ed67d25 -- resense native configs ros2_ws`: the version string in `resense/__init__.py`,
  `package.xml`, `setup.py` only. `git diff ed67d25 a7b7005 -- resense native configs ros2_ws`: empty.
* `fin` (`ed67d25`, only `build_native.sh`) re-run with `eval_real.py` on `doubleT_obstacle`,
  `roundT_pressureGate_roundT`, set O and the whole ride: **13,250 rows, 0 differ** from `int`'s gate rows in every field
  except timing and machine-speed latency messages (`out/fin_identity.txt`). The positive control for this comparison
  is the K2-off run below, which differs from `int` in exactly the 8 K2 frames.
* `a7b7005`: `detector_freeze.py verify` PASS (42 files, source `853a05b7…162d7d`); manifest
  `detector_freeze_2026-10-22_1.3.0.json` has `measured_commit` `ed67d25…`; `DEFAULT_MANIFEST` points to it;
  `sync_params.sh --check` "parameter files in sync"; `tests/test_release.py` 53 passed; version 1.3.0 in
  `pyproject.toml`, `resense/__init__.py`, `package.xml`, `setup.py`. On `ed67d25` itself `verify` fails (the manifest
  is added one commit later), as expected.

### 4.2 Data identity
`Датасет.zip` SHA-256 `e2316680…68be` (team storage), `doubleT_obstacle` / `roundT_doubleT` bag SHA-256 OK, frame counts
201 / 345 / 252 / 268 / 545 / 877; set O archive `d41c2fb2…96e9`, 1,510 frames; ride 221 splits, archive size and
SHA-256 `8124b627…99ec` verified by `cache_extended_ride.py`; Falcon stream `90dea27d…5611`, 6,758,209,772 bytes in both
streams; marked bags `04d176b4…8682760`.

### 4.3 Comparators, positive controls, attribution
* **Falcon** (`scripts/falcon_score.py`, mine; truth = the reviewed person anchors of `n2_falcon_2026-10-18`): v1.2.0
  reproduces the published figures (manual 1,360 / 2972 / 124.9 m; `falcon_ros` 1,387 STOP, 8 / 3, 127.3 m).
  Positive control: far range rev 1 (`0eb4dda`) from frame 0: **30 GO-with-person-inside-clear frames, 2660–2848**,
  exactly the far-range review's F1. An earlier version of my scorer mapped detection centres through
  `mount_rotation` and found 0 person frames on the manual path (whose rotation includes the axis swap); checked on
  frames 3000 / 3100 / 3500 that the vehicle-frame centre already matches the anchor, fixed, re-run; nothing from the
  faulty run is used.
* **Gate rows** (`scripts/gate_rows.py`, mine): run first on the integration's committed work dirs, it finds the known
  3 added ride episodes (positive control on a known non-zero), then on my fresh gate work dirs.
* **X3** (`scripts/x3_frames.py`, per frame over the battery's raw rows): planted loss of one STOP frame is found.
* **Marked bags** (`scripts/rec_cmp.py`, ctl vs candidate per frame): positive control v5c-15 (v1.2.0 with the v5c
  switches) on tunnels: 17 STOP frames lost, among them exactly the K2 review's object-19 frames 259–273 and 279.
* **K2 × far-range probe:** planted leak 300 / 300 (§3).
* **Node projection** (`scripts/node_projection.py`): the decision recomputed from each record equals the record's
  decision on all frames (0 of 4,443 × 2 and 1,667 × 2 differ), so the row passed to `candidate_ranges` is the node's.
* **Ride attribution to K2:** `int` with the four K2 switches set to their v1.2.0 values (`axis_joint_fit` false,
  `axis_joint_union` false, `axis_joint_min_curvature` 0, `axis_joint_range` true) on the whole ride: **111 STOP frames,
  26 episodes, identical STOP frames to v1.2.0**; against 1.3.0 it lacks exactly piece 2 frames 1066–1069, 1071–1072,
  1317–1318 (`out/ride_k2off.txt`). The +3 ride episodes are K2's and nothing else's.

### 4.4 K2 range sample
`scripts/range_prep.sh` (B, C decoded from the zip; ICP odometry computed here with the K1/K2 tools on v1.2.0) and
`scripts/range_sample.sh` (the judge's `range_test.py` of `k1_k2_gauge_2026-10-19/tools`, job arguments as
`prebuild_range.py`); `scripts/range_cmp.py` per frame → `out/range_sample.txt`.

| job | v1.2.0 at 1.3.0's placement: STOP frames, first / held X | 1.3.0: STOP frames, first / held X | lost | v1.2.0 own placement |
|---|---|---|---|---|
| B person | 25, 46.49 / 50.03 | 39, 71.19 / 78.19 | 0 | 28, 51.8 / 57.11 |
| B cube05 | 27, 50.03 / 55.34 | 39, 71.19 / 78.19 | 0 | 27, 50.03 / 55.34 |
| B cube1 | 29, 53.57 / 58.88 | 40, 72.94 / 79.94 | 0 | 27, 50.03 / 55.34 |
| C person | 51, 76.89 / 84.25 | 63, 94.58 / 104.98 | 0 | 55, 82.77 / 91.63 |
| C cube05 | 50, 75.42 / 82.77 | 60, 90.15 / 99.04 | 0 | 50, 75.42 / 82.77 |
| C cube1 | 53, 81.3 / 87.2 | 55, 84.25 / 91.63 | 0 | 57, 85.72 / 94.58 (2 frames, 96 and 150, not hit by 1.3.0 at its own placement) |

The same placement is by construction: the `ctlatfin` tag reads byte-identical copies of `fin`'s object-free baseline
files (SHA-256 listed in `out/range_sample.txt`). The rows equal the K2 review's same-placement rows. The own-placement
C_cube1 difference (85.72 → 84.25 m first STOP, frames 96 / 150) is the placement effect the K2 review reported as
finding 1 (the harness moves the object with each tree's published track); at the same placement 1.3.0 gains on it
(81.3 → 84.25 m). Positive control: a planted lost hit is reported (B_cube05 frame 165).

## 5. Not checked / unverified
* The ROS node itself (no ROS 2 in this container): its range path was replayed offline with its own
  `decision_policy` functions on detector records.
* The full 37-job K2 range matrix (only the 6 jobs of §4.4; A, D and S jobs, including the accepted D_cube05 delay, not re-run) and the K2 review's attacks; the far-range review's 82 scenes and matrices; B6.
* The full test suite (only `tests/test_release.py`); the integration reports 2,551 passed and one pre-existing failure.
* An opinion-off toggle on the final tree (identity taken from the integration).
* Timing on a quiet machine (N3 is side-by-side).

## 6. Reproduce
Worktrees: `git worktree add --detach /home/user/wt/<name> <commit>`, `scripts/build_native.sh` in each. Data:
`scripts/six.sh` (zip → zstd gate caches + decoded caches), `scripts/setO_ride.sh` (set O, ride intake). Runs:
`scripts/falcon_stream.sh` (one Falcon stream teed to several trees; `TREES="ctl:… int:… intp:…:probe"`; with
`MULTI=scripts/falcon_starts.py` and a start-window spec for the 6 starts), `scripts/gate.sh`, `scripts/x3.sh`,
`scripts/markers.sh`, `scripts/range_prep.sh` / `range_sample.sh`. Scoring: `falcon_score.py`, `gate_rows.py`,
`x3_frames.py`, `rec_cmp.py`, `node_projection.py`, `node_policy_unknown.py`. Raw records: `raw/` (xz).
