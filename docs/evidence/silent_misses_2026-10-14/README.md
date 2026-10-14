# Silent misses of 13.10, fixed and integrated: the free-top column test and the structure cut (14.10)

> **Purpose:** the record of the integration branch `final/silent-misses`. It holds the fixes for the judge's silent
> misses 1 (a pole in the envelope demoted as a column) and 2 (an object against the wall on a curve dropped with
> it), and the fixes of the review of 14.10 evening (the structure cut's tolerance 0.8 → 1.3 m, one free-top spare
> counts as a column, the rule wiring). The record covers the full regression gate of the current code, the 27 range
> probes against the sealed detector and the 13.10 combination, the review's wall-anchored probes and robustness
> replays, how the two fixes interact, an A/B timing, the tests and what is still open.
> **Audience:** team, the reviewer of the reseal · **Owner:** P1 · **Language:** EN ·
> **Status:** dated record, 2026-10-14 (the review fixes the same evening); **not resealed**
> (`scripts/detector_freeze.py verify` fails until the reseal)

## Scope

Branch `final/silent-misses`, from `claude/eloquent-volta-qcxq9d` `707ea9c`. That commit is the sealed detector
of 29.09 (`v1.0.0`) plus the [judgement of 13.10](../judgement_2026-10-13/README.md).

| commit | what | taken from |
|---|---|---|
| `203321b` | the column signature spares a pole whose top is seen free (`cluster.column_free_max_top` 2.95, `column_free_min_core` 0.5, `column_free_min_returns` 2) | `fix/column-geom` `bd96568` + `final/column` `5551c61` |
| `5fce816` | a cluster that the oversize split refused is cut along its wall surface (`cluster.structure_cut_tol` 0.8, `structure_cut_max_spread` 0.12, `structure_cut_min_fit` 0.8, `structure_cut_min_points` 8) | `fix/oversize-link` `bc05638` (the judge's finalist P2) + `final/oversize` `d8f5770` |
| `2e17ac3` | this folder for the 13.10 combination, the evidence index row | — |
| `14f83dd` | the review fixes (§7): `cluster.structure_cut_tol` 0.8 → **1.3**; `tracking.column_free_min_spares` **2** (one free-top spare is the column the column rule made of it); a structure-cut part removes a low object only as an obstacle; channel ids out of the ring table's order are no empty-ring evidence; the tests the review asked for | the review of 14.10 |
| this commit | this folder brought to `14f83dd`, the CHANGELOG | — |

Sections 1, 2, 4, 6 and 7 were measured on code `14f83dd` (the `code.commit` of [`gate.json`](gate.json)). Sections 3
and 5 are the measurements of the 13.10 combination `5fce816` and say so. For every run:

- the code under test was first on `PYTHONPATH`, and every script asserted that `resense.__file__` lies in it (the
  worktree, or a byte-identical snapshot of its tracked files for the probes and replays);
- the native kernels were loaded (`native (_resense_native.cpython-313…)`);
- `configs/default.yaml` was used as committed; it is byte-identical to the ROS copy (`scripts/sync_params.sh --check`).

The machine had 4 vCPU, Python 3.13 and one BLAS thread per process, and ran one job of this work at a time under
`nice`. The caches were the gate cache (`/tmp/claude-0/fixdata/cache`) and the judge's decoded caches A
(`roundT_squareT_pressureGate_squareT`), B (`roundT_doubleT`), C (`roundT_pressureGate_roundT`) and S / D
(`squareT_platform_squareT_switch`).

## What changed

**Silent miss 1, the column rule** (`resense/clustering.py` `top_is_free`, `_corridor_cluster`; `resense/detector.py`
hands the frame's cloud and channel ids to the corridor clustering; `resense/tracking.py`).

- A column continues up to the vault; an object standing in the envelope ends inside it.
- The column signature no longer demotes a cluster that meets all three of these conditions:
  - at least half of its voxels are inside the strict envelope;
  - its top is at most 2.95 m;
  - its top is seen free. Over the cluster's azimuth span, the first ring above the top that returns has nothing
    at the top's range, and either a ring in between returned nothing or more of that ring's returns lie beyond
    the top than nearer.
- The ring in between is read from the frame's channel ids. The ring table is the fallback only for a frame without
  ids (set O carries 0 for every return); ids that are not in the table's order are no empty-ring evidence (14.10).
- 14.10: such a spared cluster (`Cluster.spared`) is believed only when the track it continues had another spared hit
  among its last 10 hits. Alone, it is the column the column rule made of it (reason `column`, zone `warning`), so the
  column hold, the zone vote and `explained_run` see what they saw before 13.10 (`Tracker._uncorroborated_spare`,
  `tracking.column_free_min_spares` 2).
- Every other rule still applies.

**Silent miss 2, the oversize drop on curves** (`resense/clustering.py` `_split_part`, `_off_structure_parts`,
`_surface_fit`; `find_clusters`; `resense/detector.py`).

- On the C curve, the lagging far axis lays the wall across the envelope. A person-size box there merges with
  the wall into a cluster longer than `max_extent`. The 25.09 split refused that cluster and it was dropped whole.
- Now, only when the split refused the cluster, a robust smooth surface y(x, h) is fitted to it:
  - no fit is made without a strict-gauge point;
  - nothing is cut along a surface steeper than 45° to the track.
- Points at least **1.3 m** (0.8 m on 13.10) in front of the surface, as seen from the sensor, are linked again. 1.3 m
  is more than the equipment fixed to the wall stands in front of it (0.8-1.2 m) and more than C's wall stands outside
  the strict envelope (it stands about 2.25-2.3 m from the axis where the axis is trusted, 1.05 m half width).
- Parts at most 3 m long, with strict-gauge points and at least 8 voxels, go through every rule (`Cluster.cut`). A
  cut part removes a low object it overlaps only when it is itself an obstacle, as straddling and wall-kept clusters.

**The merge.** Both fixes changed the call of `_corridor_cluster` in `find_clusters`, and that was the only
conflict. The column fix had added `frame_xyz` and `frame_ring`; the structure cut reuses the same arguments for each
cut part. As a result, a cut part goes through exactly the same `_corridor_cluster` as any cluster, with the free-top
test included (`tests/test_structure_cut.py::test_a_cut_part_meets_the_column_rule_and_its_free_top_test`).
`config.py` and both YAML files changed in different sections, and the YAML files stay byte-identical. `CHANGELOG.md`
has one entry per fix under `[Unreleased] — detector candidate final/silent-misses`, and one for the review fixes.

## 1. Full regression gate of the current code (`14f83dd`)

`scripts/regression_gate.py --jobs 2` against
[`regression_baseline_2026-09-29_shell_off.json`](../results/regression_baseline_2026-09-29_shell_off.json), run from
the worktree at the committed `14f83dd` (`uncommitted_detector_changes: []`): exit 0, **GATE PASS**. The result is in
[`gate.json`](gate.json).

- 0 gated rows are better and 0 worse.
- 208 rows are the same: all 208 non-latency rows, 145 of them gated.
- The 16 latency rows changed; they are information only (another machine).

Frame by frame, all 15 gate outputs are identical to the sealed detector's gate on this machine
(`/tmp/claude-0/fixwork/gate_head/work`): 0 differing obstacle or advisory flags, 0 differing detection or warning
counts, and 0 frames whose detections and warnings differ in distance, zone or reason
([`gate_frames_vs_sealed.txt`](gate_frames_vs_sealed.txt)).

| gated set | rows (all the same as the baseline) |
|---|---|
| five obstacle-free recordings, alarm events / STOP episodes | `doubleT_platform` 1 / 1, `roundT_doubleT` 0 / 0, `roundT_pressureGate_roundT` 0 / 0, `roundT_squareT_pressureGate_squareT` 0 / 0, `squareT_platform_squareT_switch` 7 / 11; together 8 events / 12 episodes |
| the ride (`new_data`, 11 271 frames, 8 pieces) | alarm events 27, STOP episodes 30 |
| `doubleT_obstacle` | labelled hits `object_on_rail` 129, `person_crossing` 61, `object_on_rail_from_frame_75` 126; fp events 0; first alarm frame 8 |
| set O, inside objects (STOP frames / first STOP m / held from m) | big_center 208 / 98.0 / 98.7, small_center 32 / 55.8 / 60.8, small_on_rail 23 / 42.7 / 46.2, small_edge_inside 18 / 35.0 / 38.7, big_edge_inside 7 / 18.3 / 10.3, big_above 56 / 111.4 / 123.6, long_low_on_rails 52 / 87.2 / 95.9, thin_hanging 15 / 30.1 / 31.8 (411 of 801 visible) |
| set O, outside and background | false STOP small_outside_near 0, big_outside 6; background 0 frames / 0 track ids |
| set F straight (detected / first median m / false) | person 6/6 / 151.0 / 6, box1.0 6/6 / 123.9 / 12, box0.5 2/6 / 64.4 / 0, trolley 6/6 / 151.4 / 5, cable 6/6 / 98.9 / 0 |

Information rows, all the same: alarm frames (ride 126, the five obstacle-free recordings 39, `doubleT_obstacle` 193,
`squareT_platform_squareT_switch` 37, `doubleT_platform` 2), advisory frames (`doubleT_obstacle` 91,
`doubleT_platform` 182, `roundT_doubleT` 173, `roundT_pressureGate_roundT` 107, `roundT_squareT_pressureGate_squareT`
146, `squareT_platform_squareT_switch` 398), set O per-object advisory frames, set F recall bins and sustained medians.
Gate latency, mean / p95 ms (information only): the ride 34.5 / 49.8, C 32.2 / 42.2 (the 13.10 combination alone on
this machine: 33.6 / 49.3 and 29.3 / 40.7). `ride.health` ok / warn 11 074 / 197 (it includes the latency warning, so
it follows the machine's load; not a gate row, no decision depends on it).

Earlier gates kept here: [`gate_5fce816.json`](gate_5fce816.json) (the 13.10 combination: PASS, every gate frame
identical to the sealed detector, [`gate_frames_vs_sealed_5fce816.txt`](gate_frames_vs_sealed_5fce816.txt)),
[`gate_final_column.json`](gate_final_column.json) (`5551c61`, PASS) and
[`gate_final_oversize.json`](gate_final_oversize.json) (PASS).

## 2. Range probes: sealed, the 13.10 combination and now

These are the judge's range tests (`scripts/range_test.py`), the yawed ones through
`/tmp/claude-0/fixwork/judge_oversize/rt_wrap.py`, through the node replica on real backgrounds, one at a time, with
observation-only hooks ([`scripts/review_hooks.py.txt`](scripts/review_hooks.py.txt)). Each cell gives first STOP m /
held-from m · STOP frames / visible frames. The judge places the object on the detector's own baseline axis.

- **sealed**: the sealed detector's run (the judge's `baseline_out`, the investigators' or the finalizers' sealed
  bases; the paths are in [`review_probes.json`](review_probes.json)).
- **13.10**: the 13.10 combination `5fce816` ([`probes_summary.json`](probes_summary.json)).
- **now**: `14f83dd`.
- **frames worse**: frames whose object hit (a STOP matching the object) is lost, plus frames that turn to GO.

Windows: A `--start 150 --end 340 --d0 230`; C `--start 0 --d0 230`; B `--start 50 --d0 230`; S `--start 360 --end 620`;
D = the S cache with `--start 100 --end 420 --d0 230`.

| probe | sealed | 13.10 (`5fce816`) | now (`14f83dd`) | now G / C / S | frames worse than sealed | frames worse than 13.10 |
|---|---|---|---|---|---:|---:|
| A pole 0.3 × 0.3 × 2.8 m, axis | 218.4 / – · 82/177 | 218.4 / 225.9 · 157/177 | **218.4 / 225.9 · 157/177** | 5 / 15 / 157 | 0 | 0 lost STOP, 0 new GO |
| A pole, +0.7 m | – / – · 0/176 | 198.2 / 201.1 · 136/176 | **190.1 / 191.2 · 128/176** | 6 / 42 / 128 | 0 | 8 lost STOP, 0 new GO |
| A pole, −0.7 m | – / – · 0/181 | 193.2 / 196.2 · 133/181 | **192.2 / 195.2 · 132/181** | 4 / 45 / 132 | 0 | 1 lost STOP, 0 new GO |
| A post 0.5 × 0.5 × 2.5 m, axis | 218.4 / – · 56/185 | 218.4 / 220.9 · 157/185 | **218.4 / 220.9 · 157/185** | 5 / 23 / 157 | 0 | 0 lost STOP, 0 new GO |
| A post, +0.7 m | 184.9 / – · 30/185 | 199.2 / 214.1 · 150/185 | **192.2 / 202.1 · 138/185** | 4 / 43 / 138 | 0 | 12 lost STOP, 0 new GO |
| A pole, axis, `--dropout` | 196.2 / – · 67/176 | 196.2 / 209.6 · 143/176 | **196.2 / 209.6 · 143/176** | 19 / 14 / 143 | 0 | 0 lost STOP, 0 new GO |
| A pole, +0.7 m, `--dropout` | 196.2 / – · 11/175 | 196.2 / 197.2 · 133/175 | **196.2 / 175.3 · 126/175** | 17 / 32 / 126 | 0 | 7 lost STOP, 0 new GO |
| A person box 0.5 × 0.5 × 1.75 m | 218.4 / 221.8 · 158/185 | 218.4 / 221.8 · 158/185 | **218.4 / 221.8 · 158/185** | 5 / 22 / 158 | 0 | 0 lost STOP, 0 new GO |
| S (standing train) pole +0.7 m, d0 60 | – / – · 0/260 | 60.0 / 60.0 · 255/260 | **60.0 / 60.0 · 255/260** | 0 / 5 / 255 | 0 | 0 lost STOP, 0 new GO |
| S pole +0.7 m, d0 100 | – / – · 0/260 | – / – · 0/260 | **– / – · 0/260** | 18 / 240 / 2 | 0 | 0 lost STOP, 0 new GO |
| B pole, axis | – / – · 0/111 | 51.8 / 57.1 · 28/111 | **51.8 / 57.1 · 28/111** | 9 / 74 / 28 | 0 | 0 lost STOP, 0 new GO |
| B pole, +0.7 m | – / – · 0/119 | 50.0 / 55.3 · 27/119 | **48.3 / 51.8 · 26/119** | 5 / 88 / 26 | 0 | 1 lost STOP, 0 new GO |
| C pole, axis | – / – · 0/150 | 87.2 / 93.1 · 56/150 | **78.4 / 82.8 · 50/150** | 38 / 62 / 50 | 0 | 6 lost STOP, 1 new GO |
| C pole, +0.7 m | – / – · 0/151 | 63.6 / 66.6 · 40/151 | **63.6 / 66.6 · 40/151** | 51 / 60 / 40 | 0 | 0 lost STOP, 0 new GO |
| C person 0.5 × 0.5 × 1.75 m | 73.9 / 81.3 · 49/153 | 90.2 / 99.0 · 60/153 | **82.8 / 91.6 · 55/153** | 42 / 56 / 55 | 0 | 5 lost STOP, 2 new GO |
| C 1 m cube | 73.9 / 81.3 · 49/153 | 96.1 / 106.5 · 64/153 | **85.7 / 94.6 · 57/153** | 46 / 50 / 57 | 0 | 7 lost STOP, 0 new GO |
| C 0.5 m cube | 75.4 / 82.8 · 50/151 | 82.8 / 91.6 · 55/151 | **75.4 / 82.8 · 50/151** | 55 / 46 / 50 | 0 | 5 lost STOP, 5 new GO |
| C person, +0.5 m | 69.5 / 76.9 · 46/153 | 84.2 / 93.1 · 56/153 | **72.5 / 79.8 · 48/153** | 45 / 60 / 48 | 0 | 8 lost STOP, 6 new GO |
| C person, −0.5 m | 193.5 / 91.6 · 57/153 | 193.5 / 112.4 · 70/153 | **193.5 / 99.0 · 62/153** | 39 / 52 / 62 | 0 | 8 lost STOP, 0 new GO |
| C person, +0.7 m (wall side) | 68.1 / 75.4 · 45/153 | 72.5 / 79.8 · 48/153 | **68.1 / 75.4 · 45/153** | 50 / 58 / 45 | 0 | 3 lost STOP, 3 new GO |
| C person, −0.7 m | 85.7 / 94.6 · 57/153 | 109.4 / 121.3 · 73/153 | **96.1 / 106.5 · 64/153** | 38 / 51 / 64 | 0 | 9 lost STOP, 0 new GO |
| C person, `--dropout` | 73.9 / 81.3 · 49/147 | 90.2 / 99.0 · 60/147 | **82.8 / 91.6 · 55/147** | 50 / 42 / 55 | 0 | 5 lost STOP, 2 new GO |
| C person yawed +20° | 72.5 / 79.8 · 48/153 | 93.1 / 102.0 · 62/153 | **85.7 / 94.6 · 57/153** | 41 / 55 / 57 | 0 | 5 lost STOP, 1 new GO |
| C person yawed −20° | 72.5 / 79.8 · 48/153 | 88.7 / 97.5 · 59/153 | **85.7 / 94.6 · 57/153** | 40 / 56 / 57 | 0 | 2 lost STOP, 0 new GO |
| C 1 m cube yawed +20° | 71.0 / 78.4 · 47/153 | 97.5 / 106.5 · 64/153 | **85.7 / 93.1 · 56/153** | 49 / 48 / 56 | 0 | 8 lost STOP, 0 new GO |
| B person | 51.8 / 57.1 · 28/119 | 51.8 / 57.1 · 28/119 | **51.8 / 57.1 · 28/119** | 11 / 80 / 28 | 0 | 0 lost STOP, 0 new GO |
| D person (squareT switch) | 105.8 / – · 165/318 | 105.8 / – · 165/318 | **105.8 / – · 165/318** | 14 / 130 / 174 | 0 | 0 lost STOP, 0 new GO |

**No probe has a frame worse than the sealed detector.** Against the 13.10 combination:

- **The column probes** lose STOP frames only at 160-200 m, and only off the axis: the A pole at +0.7 m 136 → 128
  (first STOP 198.2 → 190.1 m), the post at +0.7 m 150 → 138, with `--dropout` 133 → 126, at −0.7 m 133 → 132, B
  +0.7 m 27 → 26. Every bin within 150 m is unchanged (A pole +0.7 m: 3-30 m 18/18 · 30-60 21/21 · 60-100 27/27 ·
  100-150 39/39 · 150-200 23/44). The cause is the spare rule: the first spared hit of a track is a column hit, and
  `explained_run` (5) then waits for clean hits; far off the axis the pole's column-shaped hits alternate between
  the test not asked (core share under 0.5) and spared. The poles on the axis are unchanged (157, 157, 143).
- **The curve probes** keep part of the 13.10 gain: the C person first STOP 73.9 sealed → 90.2 (13.10) → 82.8 m now,
  STOP frames 49 → 60 → 55; the 1 m cube 49 → 64 → 57; −0.7 m 57 → 73 → 64; yawed ±20° 48 → 62 / 59 → 57 / 57. The
  0.5 m cube (50) and the person on the wall side (+0.7 m, 45) are back at the sealed numbers: they never stand 1.3 m
  clear of the wall. The C pole on the axis, the gain of the two fixes together, goes 56 → 50 STOP frames. The A, B
  and D persons, the S pole and the C pole off the axis are unchanged frame by frame.
- The judge places the box on the detector's axis, which on C lags 1.3-2.2 m toward the outer wall at 80-120 m: there
  the box stands 0.8-1.8 m in front of the fitted wall, as deep as the review's false-STOP objects. What 1.3 m gave up
  is the part of the 13.10 gain where the box was less than 1.3 m from the wall (§7).

Per-probe summaries, bins and frame comparisons: [`review_probes.json`](review_probes.json).

## 3. Interaction of the two fixes (measured on `5fce816`)

This census is the 13.10 combination's, with the cut at 0.8 m. At 1.3 m the cut keeps fewer parts: on the review's
wall-anchored probes 0-4 instead of 0-26 per probe (§7.1), on the plain and perturbed replays of §4 and the ride pieces
of §7.3 the counts are given there. The wiring the census relied on is now under test: a cut part is asked the
free-top test when the column shape fits
(`tests/test_structure_cut.py::test_a_cut_part_meets_the_column_rule_and_its_free_top_test`). Below, "§2" and "§4"
mean the 13.10 probes and replays, kept in [`probes_summary.json`](probes_summary.json) and [`replays_summary.json`](replays_summary.json).

The structure cut creates new corridor parts, and in the combined code they meet the column rule and its free-top
exemption like any cluster. This is the reason for the integration stage. To measure it,
[`scripts/interact_hooks.py.txt`](scripts/interact_hooks.py.txt) monkeypatches the combined detector in a scratch
process; no repository file is edited. It wraps `_off_structure_parts`, `_corridor_cluster`, `_advisory_reason`,
`top_is_free` and `Detector.process`. For every corridor cluster that is a cut part, is column-shaped, or was given
to `top_is_free`, it records:

- **column-shaped**: the geometric condition of the column rule, whatever rule fires first;
- **reaches the column rule**: the reason by shape alone is `column`;
- **spared**: the free-top test turned that into another verdict;
- the cluster's final verdict.

The wrappers return the original results, and the extra calls are pure. This was checked: the instrumented plain
replays equal the judge's baselines in every field (§4), and the instrumented ride pieces equal `final/column`'s ride
pieces in every decision (8 / 8 pieces, 0 changed, 126 STOP frames / 30 episodes).

The census covered:

- the whole ride in the gate's 8 pieces (the gate's frame loop; fresh detector per piece, cache stamps);
- the four judge backgrounds A, B, C and S through the node replica (`probe.py`);
- the 8 robustness replays of §4;
- the 27 probes of §2.

| run | cut parts kept | column-shaped | reach the column rule | spared by the free-top test | free-top tests on other clusters (spared) | decisions changed |
|---|---:|---:|---:|---:|---|---|
| ride, 8 pieces, 11 271 frames | 3 | 2 | 0 | 0 | 622 (8) | 0 |
| A, B, C, S plain | 0 | 0 | 0 | 0 | A 0, B 63 (0), C 0, S 2 (0) | 0 |
| A / C `--pitch 2`, `--drop 0.3`, `--dedup`, `--every 2` | C drop30 1, C 5 Hz 1, others 0 | 0 | 0 | 0 | 0 | 0 |
| 27 probes | 125, all on C (2-17 per probe in 13 probes) | 0 | 0 | 0 | 1 179 (956) | C pole on the axis +13 STOP frames (§2), otherwise 0 |

Across every run there are **130 cut parts and only 2 of them are column-shaped. Neither reaches the column rule,
so the free-top test never ruled on a cut part.**

- **The ride's crossover posts, k4720-4729.** The 2 column-shaped cut parts are the posts at k4725, cut out of a
  96-193 m wall cluster of 235 voxels:
  - 117.2 m: lateral −0.46, 0.61 × 0.38 × 2.58 m, top 2.82 m, 17 voxels;
  - 147.2 m: lateral −0.91, 0.15 × 0.52 × 2.33 m, top 2.88 m, 13 voxels.

  Both are `beyond_axis`: in that frame the axis is trusted only to 60 m, and `beyond_axis` comes before the column
  rule in `_advisory_reason`. They stay advisory, as on `final/oversize`. The 117.2 m post has all 17 voxels strict
  and its top under 2.95 m, so the free-top test would be asked if the axis were trusted that far (residual 7). The
  147.2 m post has 5 of 13 voxels strict, under the 0.5 core share, so the test would not be asked. The nearer posts of the same crossover at
  83-92 m (k4720-4729, H 2.6-2.8 m, 32-37 voxels, not cut parts) are `column` or `beyond_axis` as before. Where
  the free-top test was asked about them (k4720, k4722) it answered "not free". At k4724, k4726 and k4728 the top
  is 2.97-2.98 m, above 2.95, and at k4729 the core share is under 0.5, so the test is not asked.
- **The third ride cut part** is not column-shaped: k8334, 85.2 m, lateral 0.43, 0.11 × 0.15 × 1.10 m, **8 voxels,
  exactly the bar**. It is a single-frame gauge candidate, never confirmed, and changes no decision. `final/oversize`
  alone produces the same part in the same piece (run here with `scripts/ov_piece.py.txt`; its pieces 3 and 5 make
  decisions identical to the combination), so it comes from the structure cut, not from the combination.
- **The A / C pressure-gate structures, 105-155 m.**
  - On C the cut keeps no part on any replay.
  - On A no part is cut even with the bar at 0. The one column-shaped gauge cluster there is k107: 125.4 m,
    lateral −1.01, 3.07 × 0.69 × 2.57 m, top 2.72 m, 3 of 10 voxels in the strict envelope. It is not a cut part.
    Its core share of 0.3 is under `column_free_min_core` 0.5, so the free-top test is not asked and it stays
    `column`, as sealed.
  - The other column-shaped clusters at 120-132 m on A are `warning` zone and outside the envelope.
- **The bar margin.** [`scripts/interact_hooks_loose.py.txt`](scripts/interact_hooks_loose.py.txt) also describes
  the parts that `structure_cut_min_points` 8 removed, with every rule and the free-top test included; the detector
  never sees them. They had 3-7 voxels:

  | run | parts the bar removed | would-be gauge candidates | column-shaped |
  |---|---:|---:|---:|
  | the ride | 42 | 8 | 0 |
  | C | 10 | 5 (two of them at 107-109 m: 0.44-0.45 m tall, 3-5 voxels) | 0 |
  | B | 3 | 1 | 0 |
  | A | 0 | 0 | 0 |
  | S | 0 | 0 | 0 |

  Even without the bar, the column exemption would have had nothing to spare on these data. The bar's job is the
  plain gauge candidates.

Records and counts per run: [`interaction_summary.json`](interaction_summary.json).

## 4. Robustness replays (`14f83dd`)

Whole recordings through the node replica ([`scripts/review_jrep.py.txt`](scripts/review_jrep.py.txt), the judge's
`judge_runner.NodeReplica` with `range_test.run_frame`), hooks installed. The plain replays are compared with the
judge's `baseline_out` (the sealed detector replayed from the bags); each perturbed replay with the sealed detector
(the main checkout `707ea9c`, read only) under the same perturbation and seed.

| replay | frames | STOP frames / episodes / CAUTION, base → now | decisions changed | other fields changed (dets, warns) | free-top tests (spared) | cut parts |
|---|---:|---|---:|---:|---|---:|
| A plain | 545 | 0 / 0 / 191 → 0 / 0 / 191 | 0 | 0 | 0 (0) | 0 |
| B plain | 252 | 0 / 0 / 169 → 0 / 0 / 169 | 0 | 0 | 63 (0) | 0 |
| C plain | 268 | 2 / 1 / 116 → 2 / 1 / 116 | 0 | 0 | 0 (0) | 0 |
| S plain | 877 | 11 / 3 / 446 → 11 / 3 / 446 | 0 | 0 | 2 (0) | 0 |
| C `--pitch 2` | 268 | 0 / 0 / 114 → 0 / 0 / 114 | 0 | 0 | 0 (0) | 0 |
| A `--pitch 2` | 545 | 0 / 0 / 193 → 0 / 0 / 193 | 0 | 0 | 0 (0) | 0 |
| C `--drop 0.3` | 268 | 0 / 0 / 99 → 0 / 0 / 99 | 0 | 0 | 0 (0) | 0 |
| A `--drop 0.3` | 545 | 0 / 0 / 172 → 0 / 0 / 172 | 0 | 0 | 0 (0) | 0 |
| C `--every 2` (5 Hz) | 134 | 0 / 0 / 60 → 0 / 0 / 60 | 0 | 0 | 0 (0) | 0 |
| C `--dedup` | 268 | 2 / 1 / 100 → 2 / 1 / 100 | 0 | 0 | 0 (0) | 0 |

The review's seeded dropout, pitch and slow-train replays of S and B are in §7.2: every one identical to the sealed
detector in its decisions. The 13.10 replays of `5fce816` (A / C with `--pitch 2`, `--drop 0.3`, `--dedup`,
`--every 2` through `probe.py`) are kept in [`replays_summary.json`](replays_summary.json).

## 5. Timing (A/B on the same frames, measured on `5fce816`)

The review fixes change no per-frame work: the tolerance only changes which points of a fitted cluster are linked
again, and the tracker checks the spare history of a matched spared cluster (622 free-top tests on the whole ride).
The gate latency of `14f83dd` (§1) is in the range of the earlier gates on this machine.

[`scripts/timing_ab.py.txt`](scripts/timing_ab.py.txt) timed `Detector.process` wall time on the same frames, one
process per run, with a fresh detector; frame loading was not timed. Sealed (the main checkout `707ea9c`) and
combined (`5fce816`) runs were interleaved three times on the otherwise idle machine, with the native kernels in
both ([`timing_ab.json`](timing_ab.json)).

| frames | sealed mean (3 runs) | combined mean (3 runs) | difference | p95 sealed / combined |
|---|---|---|---:|---|
| ride k4247-5026 (780; the crossover included) | 38.7 / 39.1 / 40.3 | 37.1 / 40.4 / 41.5 | +0.3 ms | 61.0 / 61.6 |
| C, all 268 | 31.5 / 37.2 / 34.1 | 34.4 / 35.7 / 34.4 | +0.6 ms | 47.1 / 47.1 |

The difference is inside the run-to-run spread (±3 ms). It agrees with the direct measurements:

- `top_is_free`: 1.15 s over the 11 271 ride frames, 622 calls, 0.1 ms per frame;
- the structure cut: 0.43 ms per ride frame (final/oversize census).

## 6. Tests and lint (`14f83dd` and this commit)

- `pytest -q -rs tests`, with the worktree pinned and asserted: **1303 passed**, 8 deselected (their data caches are
  not on this machine), 6 subtests passed, 0 skipped. That is the 13.10 suite's 1297 plus 6 new tests:
  `tests/test_column_free_top.py` (the uncorroborated spare, the detector's channel-id wiring, ids out of the table's
  order) and `tests/test_structure_cut.py` (the advisory-band face stays dropped at 1.3 m, a cut part meets the column
  rule and its free-top test, a demoted cut part keeps a low object); the wall-fixture assertion and the tolerance
  tests were rewritten, and `test_free_standing_post_is_a_stop` expects the STOP one frame after confirmation.
- The CI lint step, verbatim (`ruff 0.15.8 check --exclude docs/evidence/cycle_2026-09-28/complete_timing/default/run_gate.py .`): all checks passed.
- `scripts/sync_params.sh --check`: the parameter files are in sync.
- `scripts/detector_freeze.py verify`: **FAIL, as expected** (`configs/default.yaml`, `resense/clustering.py`,
  `resense/config.py`, `resense/detector.py`, `resense/tracking.py` and the ROS `detector.yaml` changed). The reseal
  is left to the orchestrator after review.
- This commit changes comments only in `configs/default.yaml` (and its ROS copy), `resense/config.py`,
  `resense/clustering.py` and the tests' docstrings against `14f83dd` (the C wall's distance from the axis given as
  2.25-2.3 m, the detector's own measurement; the mast 1.2 m proud 2 STOP frames): the parsed YAML and the ASTs
  without docstrings are identical, so the gate of §1 holds for it.
- Not run: the CI steps that need Docker / ROS (the image's suite, the node smoke tests, the offline build) and the
  web prototype jobs.

## 7. The review of 14.10 and its fixes (`14f83dd`)

The safety review and the adversarial review of 14.10 evening checked the 13.10 combination with wall-anchored
ray-cast boxes, seeded robustness replays and code mutations. Their findings and what `14f83dd` did with each:

| finding (severity) | what was done | evidence |
|---|---|---|
| The structure cut gave false STOPs for objects standing 0.95-1.2 m in front of C's outer wall: outside the envelope (the detector itself reports the 1.0 m person at lateral 1.24-1.32 m, CAUTION, where the axis is trusted), but the lagging far axis placed the parts it carved out inside (high) | `cluster.structure_cut_tol` 0.8 → 1.3 m; the review's option (a), cut parts beyond where the wall enters the strict envelope made advisory, measured and **not taken** (worse than sealed); its option (c), the wall-anchored probes, is §7.1 | §7.1, [`review_sweep.json`](review_sweep.json), [`review_wallbox.json`](review_wallbox.json) |
| One free-top spare at the standing train with 20-30 % point dropout broke the hold on a platform-edge track: a new STOP episode in 4 of 10 runs (medium) | `tracking.column_free_min_spares` 2: an isolated spare is the column the column rule made of it | §7.2, [`review_replays.json`](review_replays.json) |
| `roundT_doubleT` pitched −2°: one new STOP frame through one spare (low) | the same rule | §7.2 |
| A dark band right above a column's top makes most real columns read as free: new STOP episodes on ride pieces 1 and 3 (plausible, a what-if) | partly: an isolated spare is a column now; a band dark in most frames gives repeated spares, which are believed. Not taken: "beyond" returns on the top's own rays for tracks with column hits (the prototype's cost: 12 pole frames at 60-150 m) | §7.3 |
| The cut truncates columns standing 0.8 m or more off the round wall, so the column rule never applies (low) | with 1.3 m the 1.0 m column gives no part (0 STOP frames, as sealed; dark top too); a column 1.3 m or more off C's wall stands inside the strict envelope, an obstacle either way | §7.1 |
| `test_structure_alone_and_what_stays_dropped` passed for the wrong reason: its wall fixture had 4 voxels, under the 8-voxel bar (low) | the fixture has 28 voxels; the test checks it stays dropped at the tolerance with the bar off and is carved out at a smaller tolerance | `tests/test_structure_cut.py` |
| No test covered the detector handing `frame_ring` to the clustering, nor a cut part's free-top test (low) | `test_detector_hands_the_frame_and_its_channel_ids_to_the_corridor_clustering` (a spy on the corridor call), `test_a_cut_part_meets_the_column_rule_and_its_free_top_test` | `tests/test_column_free_top.py`, `tests/test_structure_cut.py` |
| The ring-table fallback is the Pandar128's: a 64-ring sensor, or ids numbered bottom-up, reads an occluded column as free (low) | partly: ids present but not in the table's order are no empty-ring evidence (only the returns beyond the top); one id for the whole window (set O) is still no ids, read through the table. A different sensor without ids remains (§8) | `test_channel_ids_out_of_the_tables_order_are_no_empty_ring_evidence` |
| A demoted cut part could remove a low object it overlaps (plausible) | a cut part (`Cluster.cut`) counts as a duplicate only when it is itself an obstacle, as straddling and wall-kept clusters | `test_a_demoted_cut_part_does_not_remove_a_low_object` |
| `top_is_free` scans the whole frame per call, about 1.3 ms (plausible, latency only) | not changed: 622 calls in 11 271 ride frames (0.06 per frame, 0.1 ms per frame); a per-frame azimuth table costs one `arctan2` over ~184 k points, about two calls' worth, on every frame that asks at all | — |

### 7.1 The tolerance: the review's wall-anchored probes and the judge's C probes

The review's probes ([`scripts/review_wallbox_rt.py.txt`](scripts/review_wallbox_rt.py.txt)) place a world-static box
D m proud of C's outer wall: its face nearest the track D m from the wall seen in the frame at 0.5-2.2 m height, yawed
parallel to it. At 56-70 m, where the axis is trusted, the detector itself reports the face of the box 1.0 m proud at
lateral 1.24-1.32 m (zone `warning`, CAUTION): the wall stands about 2.25-2.3 m from the axis, and with the strict
envelope 1.05 m wide on each side a box 0.95-1.1 m proud of the wall is outside it, 1.2 m proud at its edge. At 79-100 m
the lagging axis moves the wall to 0.6-1.5 m from the axis, and the same box reads at lateral −0.34..+0.76. STOP frames
attributable to the object (a STOP detection matching it), sealed → 13.10 (0.8 m) → now (1.3 m; the review's sealed and
13.10 runs, [`review_wallbox.json`](review_wallbox.json)):

| probe (C unless B) | STOP frames sealed → 13.10 → now | first STOP 13.10 → now (m) | now G / C / S while visible (sealed) | cut parts 13.10 → now |
|---|---|---|---|---|
| person-size box 0.5 × 0.5 × 1.75 m, 0.8 m proud | 0 → 0 → **0** | – → – | 80 / 41 / 0 (80 / 41 / 0) | 1 → 0 |
| the same, 0.9 m | 0 → 0 → **0** | – → – | 63 / 56 / 2 (63 / 56 / 2) | 2 → 0 |
| the same, 1.0 m | 0 → 21 → **0** | 100.5 → – | 53 / 66 / 2 (53 / 66 / 2) | 16 → 0 |
| the same, 1.0 m, `--dropout` | 0 → 21 → **0** | 100.5 → – | 53 / 66 / 2 (53 / 66 / 2) | 16 → 0 |
| the same, 1.1 m | 0 → 15 → **0** | 102.0 → – | 52 / 67 / 2 (52 / 67 / 2) | 19 → 0 |
| mast 0.3 × 0.3 × 2.6 m, 0.9 m | 0 → 0 → **0** | – → – | 78 / 41 / 2 (78 / 41 / 2) | 7 → 0 |
| the mast, 1.0 m | 0 → 9 → **0** | 90.2 → – | 81 / 38 / 2 (81 / 38 / 2) | 12 → 0 |
| the mast, 1.2 m (at the envelope edge) | 0 → 27 → **2** | 102.0 → 68.1 | 73 / 44 / 4 (77 / 42 / 2) | 26 → 4 |
| sign post 0.1 × 0.1 × 2.4 m with a 0.6 m board, 0.95 m | 0 → 5 → **0** | 84.2 → – | 57 / 27 / 2 (57 / 27 / 2) | 7 → 0 |
| column 0.4 × 0.4 m to the vault, 1.0 m | 0 → 8 → **0** | 94.6 → – | 91 / 30 / 0 (91 / 30 / 0) | 12 → 0 |
| the column, its face above 2.6 m dark | 0 → 7 → **0** | 90.2 → – | 79 / 40 / 2 (79 / 40 / 2) | 12 → 0 |
| cabinet 0.6 × 0.9 × 1.8 m flat to the wall, 0.9 m | 0 → 0 → **0** | – → – | 68 / 53 / 0 (68 / 53 / 0) | 0 → 0 |
| cabinet 0.6 × 1.0 × 1.8 m, 1.0 m | 0 → 0 → **0** | – → – | 56 / 63 / 2 (56 / 63 / 2) | 2 → 0 |
| free-standing box 0.6 × 0.5 × 1.8 m, 0.85 m | 0 → 0 → **0** | – → – | 73 / 46 / 2 (73 / 46 / 2) | 0 → 0 |
| tall cabinet 0.6 × 0.6 × 2.5 m, 1.0 m | 0 → 0 → **0** | – → – | 80 / 39 / 2 (80 / 39 / 2) | 0 → 0 |
| person on the axis, cabinet 1.0 m proud 1.5 m behind it | 44 → 44 → **44** | 66.6 → 66.6 | 47 / 62 / 44 (47 / 62 / 44) | 0 → 0 |
| person on the axis, the cabinet 1.5 m in front of it | 45 → 45 → **45** | 68.1 → 68.1 | 48 / 60 / 45 (48 / 60 / 45) | 0 → 0 |
| person on the axis, mast 1.0 m proud 1.5 m behind it | 42 → 42 → **42** | 63.6 → 63.6 | 55 / 56 / 42 (55 / 56 / 42) | 1 → 1 |
| person-size box 1.0 m proud, +y wall (B) | 0 → 0 → **0** | – → – | 13 / 45 / 0 (13 / 45 / 0) | 0 → 0 |
| the same, −y side (B) | 0 → 0 → **0** | – → – | 3 / 64 / 0 (3 / 64 / 0) | 0 → 0 |

The sweep ([`review_sweep.json`](review_sweep.json); the 13.10 code with only `structure_cut_tol` changed, one run at a
time) shows what each tolerance gives on the judge's C probes and on the review's boxes:

| probe: first STOP m · STOP frames | sealed | 0.8 (13.10) | 1.0 | 1.2 | **1.3** | 1.3 + option (a) |
|---|---|---|---|---|---|---|
| C person | 73.9 · 49 | 90.2 · 60 | 87.2 · 58 | 84.2 · 56 | **82.8 · 55** | 71.0 · 47 |
| C 1 m cube | 73.9 · 49 | 96.1 · 64 | 90.2 · 60 | 85.7 · 57 | **85.7 · 57** | 72.5 · 48 |
| C 0.5 m cube | 75.4 · 50 | 82.8 · 55 | 78.4 · 52 | 75.4 · 50 | **75.4 · 50** | – |
| C person +0.5 m | 69.5 · 46 | 84.2 · 56 | 75.4 · 50 | 72.5 · 48 | **72.5 · 48** | 72.5 · 48 |
| C person −0.5 m | held 91.6 · 57 | held 112.4 · 70 | held 109.4 · 68 | held 105.0 · 65 | **held 99.0 · 62** | held 90.2 · 56 |
| C person −0.7 m | 85.7 · 57 | 109.4 · 73 | 102.0 · 68 | 99.0 · 66 | **96.1 · 64** | 84.2 · 56 |
| box 1.0 m proud: STOP frames (cut parts) | 0 | 21 STOP (16 parts) | 0 STOP (1 part) | 0 STOP (0 parts) | **0 STOP (0 parts)** | 0 STOP (0 parts) |
| box 1.1 m proud: STOP frames (cut parts) | 0 | 15 STOP (19 parts) | 0 STOP (2 parts) | 0 STOP (0 parts) | **0 STOP (0 parts)** | – |
| mast 1.0 m proud: STOP frames (cut parts) | 0 | 9 STOP (12 parts) | 0 STOP (2 parts) | 0 STOP (0 parts) | **0 STOP (0 parts)** | – |
| sign post 0.95 m proud: STOP frames (cut parts) | 0 | 5 STOP (7 parts) | 0 STOP (3 parts) | 0 STOP (0 parts) | **0 STOP (0 parts)** | – |
| column 1.0 m proud: STOP frames (cut parts) | 0 | 8 STOP (12 parts) | 0 STOP (0 parts) | 0 STOP (0 parts) | **0 STOP (0 parts)** | – |
| mast 1.2 m proud (envelope edge): STOP frames (cut parts) | 0 | 27 STOP (26 parts) | 19 STOP (17 parts) | 8 STOP (5 parts) | **3 STOP (4 parts)** | 1 STOP (4 parts) |

- At 1.0 m the boxes 0.95-1.1 m proud give no STOP frame but still 1-3 single-frame parts each. 1.2 m removes every
  part of them, with 0.1 m to spare over the 1.1 m box; 1.3 m leaves 0.2 m (the mast 1.2 m proud still gives parts at
  1.3 m: the fitted surface lies ~0.1 m behind the wall the probe measures) and is more than C's wall stands outside
  the strict envelope (1.2-1.25 m). The mast 1.2 m proud, at the envelope edge (the detector reports it at lateral
  1.03-1.11 m at 60-68 m), keeps 2-3 STOP frames at 68 m.
- Every other wall-anchored probe decides exactly as the sealed detector while the object is visible (the table's last
  but one column), and the person on the axis with a cabinet or a mast behind or in front of it keeps its 42-45 STOP
  frames.
- **Option (a) rejected.** Cut parts beyond the nearest point where the wall surface itself lies inside the strict
  envelope (a wall cannot be there: the axis is wrong) described with the axis trusted only to there, so `beyond_axis`
  advisory. Their advisory hits enter the object's track, and its zone vote holds the STOP back once the object
  separates from the wall: at 1.3 m the C person 73.9 / 81.3 / 49 sealed → 71.0 / 78.4 / 47, the 1 m cube 49 → 48,
  −0.5 m 57 → 56, −0.7 m 57 → 56. That is worse than the sealed detector, so it was not taken.

### 7.2 One spare is a column: the review's robustness replays

The review's seeded replays ([`scripts/review_jrep.py.txt`](scripts/review_jrep.py.txt), the judge's node replica over
the whole recording, the same seeds for both codes; the sealed and 13.10 runs are the review's own,
`/tmp/claude-0/fixwork/safety_review/out/*_s.jsonl` and `*_w.jsonl`). STOP frames / episodes, sealed → 13.10 → now:

| replay | frames | STOP frames sealed → 13.10 → now | STOP episodes sealed → 13.10 → now | decisions differing from sealed | free-top tests (spared) |
|---|---:|---|---|---:|---|
| S 30 % dropout, seed 2 | 877 | 55 → 66 → **55** | 10 → 11 → **10** | 0 | 4 (1) |
| S 30 % dropout, seed 3 | 877 | 51 → 53 → **51** | 13 → 14 → **13** | 0 | 4 (1) |
| S 30 % dropout, seed 5 | 877 | 84 → 89 → **84** | 20 → 20 → **20** | 0 | 1 (1) |
| S 20 % dropout, seed 3 | 877 | 44 → 48 → **44** | 11 → 12 → **11** | 0 | 3 (1) |
| B pitch −2° | 252 | 0 → 1 → **0** | 0 → 1 → **0** | 0 | 61 (1) |
| B 30 % dropout, seed 1 | 252 | 0 → 0 → **0** | 0 → 0 → **0** | 0 | 78 (1) |
| B 30 % dropout, seed 2 | 252 | 0 → 0 → **0** | 0 → 0 → **0** | 0 | 76 (3) |
| B 30 % dropout, seed 3 | 252 | 0 → 0 → **0** | 0 → 0 → **0** | 0 | 83 (7) |
| S 30 % dropout, seed 1 | 877 | 56 → 56 → **56** | 12 → 12 → **12** | 0 | 3 (0) |
| S 30 % dropout, seed 4 | 877 | 48 → 48 → **48** | 14 → 14 → **14** | 0 | 3 (0) |
| S 30 % dropout, seed 6 | 877 | 39 → 39 → **39** | 14 → 14 → **14** | 0 | 3 (1) |
| S 20 % dropout, seed 1 | 877 | 37 → 37 → **37** | 8 → 8 → **8** | 0 | 2 (0) |
| S 20 % dropout, seed 2 | 877 | 51 → 51 → **51** | 13 → 13 → **13** | 0 | 5 (2) |
| S 20 % dropout, seed 4 | 877 | 30 → 30 → **30** | 6 → 6 → **6** | 0 | 1 (0) |
| S 10 % dropout, seed 1 | 877 | 40 → 40 → **40** | 11 → 11 → **11** | 0 | 1 (0) |
| S 10 % dropout, seed 2 | 877 | 64 → 64 → **64** | 8 → 8 → **8** | 0 | 6 (1) |
| S 10 % dropout, seed 3 | 877 | 48 → 48 → **48** | 10 → 10 → **10** | 0 | 1 (0) |
| S 10 % dropout, seed 4 | 877 | 42 → 42 → **42** | 9 → 9 → **9** | 0 | 2 (1) |
| B ×3 slower, 20 % dropout, seed 1 | 756 | 0 → 0 → **0** | 0 → 0 → **0** | 0 | 218 (3) |
| B ×3 slower, 20 % dropout, seed 2 | 756 | 2 → 2 → **2** | 1 → 1 → **1** | 0 | 180 (3) |

Every run is identical to the sealed detector frame by frame in its decisions. On the standing train (seed 2 of 30 %)
the platform-edge track (82.6-85 m, lateral 0.34-1.06 m, 2.58 × 0.43 × 2.77 m) had its first column-shaped hit, at
k343, spared: a gauge hit, so its zone vote passed and no `explained_run` held it, STOP for 11 frames. Now that hit is
the column it was before 13.10 ([`scripts/review_dbg_track.py.txt`](scripts/review_dbg_track.py.txt) prints the
track's histories).

The cost is in §2: the off-axis pole and post lose 1-12 STOP frames at 160-200 m, none within 150 m, and a fresh pole
confirms one frame later (`tests/test_late_candidates.py::test_free_standing_post_is_a_stop`).

### 7.3 The dark band and the ride pieces with dropout

The review's what-if (its hooks with `DARKBAND` 0.6, here in [`scripts/review_hooks.py.txt`](scripts/review_hooks.py.txt)):
right before each free-top test the column's own returns in the 0.6° above the cluster's top are deleted, the rays
beside it kept. Gate-faithful replays of ride pieces 1 and 3 of 8 and of the restart segment R4 (stems
`new_data_52_ / 54_ / 55_`, reset on stamp holes), a fresh detector each ([`scripts/review_grun.py.txt`](scripts/review_grun.py.txt)),
against the sealed detector's plain run; and the same pieces with 30 % point dropout against the sealed detector
with the same seed:

| run | frames | STOP frames / episodes, sealed → 13.10 → now | decisions differing from sealed | free-top tests (spared) | cut parts |
|---|---:|---|---:|---|---:|
| R4 (restart segment), dark band | 153 | 49 / 4 → 53 / 4 → **49 / 4** | 0 | 51 (31) | 0 |
| ride piece 1/8, dark band | 1409 | 14 / 3 → 34 / 9 → **30 / 6** | 16 | 180 (153) | 0 |
| ride piece 3/8, dark band | 1409 | 2 / 1 → 19 / 5 → **13 / 3** | 11 | 171 (142) | 0 |
| ride piece 1/8, 30 % dropout, seed 1 | 1409 | 6 / 3 → 6 / 3 → **6 / 3** | 0 | 98 (4) | 0 |
| ride piece 1/8, 30 %, seed 2 | 1409 | 9 / 3 → 9 / 3 → **9 / 3** | 0 | 90 (8) | 0 |
| ride piece 3/8, 30 %, seed 1 | 1409 | 0 / 0 → 0 / 0 → **0 / 0** | 0 | 195 (18) | 0 |
| R4, 30 %, seed 1 | 153 | 57 / 6 → 57 / 6 → **57 / 6** | 0 | 66 (3) | 0 |

- R4 is back at the sealed decisions: its spares were isolated.
- On pieces 1 and 3 the band makes most tops read free in consecutive frames (153 of 180 and 142 of 171 tests): the
  spares corroborate each other and are believed. Of the review's new STOP frames 4 of 20 and 6 of 17 are gone; 16 and
  11 remain (piece 1: 122-129 m and 33-37 m; piece 3: 96-140 m; lateral 0-1.2 m). The what-if removes about 1 m of
  a column's face at 100 m in every frame; whether real columns have such a face is not known from the data
  (residual 5).
- With 30 % dropout every piece decides as the sealed detector; no structure-cut part was kept on any of these runs.

## 8. Residuals

1. **C 118-150 m, the axis-lag band (judge problem 4, untouched).** On the C curve the detector's far axis lags
   1.3-2.2 m while `axis_valid` claims 143-221 m. The box placed on that axis sits 0.2-0.8 m from the wall there, as
   deep as wall equipment. The person stays 0/34 STOP frames at 100-150 m on the axis and at ±0.5 / ±0.7 m, and GO
   remains at 118-150 m. B and C beyond about 60 m (the poles, B person 28/119) have the same cause.
2. **The structure cut separates only objects at least 1.3 m clear of the wall.** On C that is where the strict
   envelope begins (the wall 2.25-2.3 m from the axis); nearer the wall nothing is cut (the C person on the wall side
   and the 0.5 m cube are back at the sealed numbers). A wall standing more than ~2.35 m from the axis, on a curve
   whose far axis lags, can still have an object 1.3 m or more in front of it, outside the envelope, placed inside it:
   none such was found on the recordings, and the review's boxes on C all stay at 0 except the mast 1.2 m proud at the
   envelope edge (2 frames at 68 m).
3. **Not one decision on the recordings changed, and the gain is measured on synthetic objects only.** Every gain is a
   judge ray-cast on real backgrounds.
4. **Far off-axis band of the pole.** At +0.7 m: 150-200 m 23/44 and 200-260 m 0/27 (13.10: 31/44). At −0.7 m:
   100-150 m 29/39, 150-200 m 37/45, 200-260 m 0/31. The causes: the strict envelope's edge margin and the 0.5
   core-share guard (13.10), and now the first spared hit counted as a column with `explained_run` after it.
5. **The free-top test's limits.**
   - Objects taller than 2.95 m (a 3.2 m pole, a ladder) still get the column rule.
   - A column whose face just above the cluster top returns nothing reads as free; isolated such frames are columns
     now (§7.2), a face dark in most frames is believed (§7.3).
   - Frames without channel ids (set O) fall back to the ring table, which is wrong under a real mount tilt and for
     another sensor. The recordings and probes all have a level mount and the Pandar128's ids; the id path is proven
     on synthetic casts (`tests/test_column_free_top.py`).
6. **The structure cut's blind spots.** No gain within 1.3 m of the wall; none for an edge line plus a face beyond 30
   m; the bar costs a few metres of first-STOP range; the slope guard covers dy/dx only; the narrow trigger (only
   clusters the split refused) leaves a split-accepted, rule-dropped part near a wall dropped.
7. **The interaction was censused on `5fce816` (§3).** With 1.3 m the cut keeps fewer parts; a cut part 0.25-1 m wide,
   at least 2.2 m tall, inside the trusted axis range, with at least half its voxels strict and its top at most 2.95 m
   would be given to the free-top test ([the wiring test](../../../tests/test_structure_cut.py)); on the data none was.
8. **S at d0 100, pole +0.7 m:** 0 of 260 before and after, and also with the column rule off. Still undiagnosed.
9. **Not run:** set F with a pole; tilted range probes with the pole; the judge's continuous whole-ride replay through
   the node (only the gate's 8 pieces, pieces 1 and 3 and the restart segment R4 also with dropout or the dark
   band); the Docker / ROS node.
10. **Not resealed.** `docs/DETECTOR_FREEZE.md` and the manifest still describe the 29.09 sources. The reseal, and the
    ALGORITHM / EXPERIMENTS / SCORECARD rows for the two rules, follow review.

## Files

| file | what |
|---|---|
| [`gate.json`](gate.json) | the full regression gate of `14f83dd` (PASS) |
| [`gate_frames_vs_sealed.txt`](gate_frames_vs_sealed.txt) | its 15 work outputs against the sealed detector's gate on this machine, frame by frame |
| [`review_probes.json`](review_probes.json) | the 27 range probes: sealed, `5fce816` and `14f83dd` summaries, frames worse than each |
| [`review_wallbox.json`](review_wallbox.json) | the review's wall-anchored probes: the review's sealed and `5fce816` runs, `14f83dd` |
| [`review_sweep.json`](review_sweep.json) | the `structure_cut_tol` sweep 0.8 / 1.0 / 1.2 / 1.3 and the rejected option (a) |
| [`review_replays.json`](review_replays.json) | the plain and perturbed replays of `14f83dd`: A / B / C / S plain, A / C pitch / dropout / 5 Hz / dedup, the review's S / B battery, the ride pieces (dark band, dropout) |
| [`gate_5fce816.json`](gate_5fce816.json), [`gate_frames_vs_sealed_5fce816.txt`](gate_frames_vs_sealed_5fce816.txt) | the gate of the 13.10 combination (PASS) and its frame comparison |
| [`gate_final_column.json`](gate_final_column.json), [`gate_final_oversize.json`](gate_final_oversize.json) | each finalizer's gate (PASS) |
| [`probes_summary.json`](probes_summary.json) | the 13.10 probes: sealed, finalizer and `5fce816` summaries, bins, frame-decision differences |
| [`interaction_summary.json`](interaction_summary.json) | the interaction census of `5fce816` per run, the column-shaped cut parts, the k4720-4729 and 105-155 m windows, the bar-margin census, the C pole split |
| [`replays_summary.json`](replays_summary.json) | the plain and robustness replays of `5fce816` against their bases |
| [`timing_ab.json`](timing_ab.json) | the interleaved A/B timing of `5fce816` |
| [`scripts/`](scripts) | the scratch scripts (`.py.txt`, `.sh.txt`; paths are this machine's). 13.10: the hooks, the census drivers and summaries, the probe and replay drivers, the timing. `review_*`: the review fixes' hooks (observation + `CFG` overrides for the sweep), the probe and replay drivers (`review_jrep`, `review_wallbox_rt` and `review_grun` are the review's own scripts with these hooks), the chains, the gate frame comparison, the table builders, the comment-only check (`review_ast_same`) |
