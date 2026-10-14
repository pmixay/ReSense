# Silent misses of 13.10, fixed and integrated: the free-top column test and the structure cut (14.10)

> **Purpose:** the record of the integration branch `final/silent-misses`. It holds the fixes for the judge's silent
> misses 1 (a pole in the envelope demoted as a column) and 2 (an object against the wall on a curve dropped with
> it). The record covers the full regression gate of the combined code, the combined range probes against each
> finalizer's numbers, how the two fixes interact, the robustness replays, an A/B timing, the tests and what is
> still open.
> **Audience:** team, the reviewer of the reseal · **Owner:** P1 · **Language:** EN ·
> **Status:** dated record, 2026-10-14; **not resealed** (`scripts/detector_freeze.py verify` fails until the reseal)

## Scope

Branch `final/silent-misses`, from `claude/eloquent-volta-qcxq9d` `707ea9c`. That commit is the sealed detector
of 29.09 (`v1.0.0`) plus the [judgement of 13.10](../judgement_2026-10-13/README.md).

| commit | what | taken from |
|---|---|---|
| `203321b` | the column signature spares a pole whose top is seen free (`cluster.column_free_max_top` 2.95, `column_free_min_core` 0.5, `column_free_min_returns` 2) | `fix/column-geom` `bd96568` + `final/column` `5551c61` |
| `5fce816` | a cluster that the oversize split refused is cut along its wall surface (`cluster.structure_cut_tol` 0.8, `structure_cut_max_spread` 0.12, `structure_cut_min_fit` 0.8, `structure_cut_min_points` 8) | `fix/oversize-link` `bc05638` (the judge's finalist P2) + `final/oversize` `d8f5770` |
| this commit | this folder, the evidence index row | — |

Everything below was measured on code `5fce816` (the `code.commit` of [`gate.json`](gate.json)):

- the worktree was first on `PYTHONPATH`, and every script asserted that `resense.__file__` lies in the worktree;
- the native kernels were loaded (`native (_resense_native.cpython-313…)`);
- `configs/default.yaml` was used as committed; it is byte-identical to the ROS copy (`scripts/sync_params.sh --check`).

The machine had 4 vCPU, Python 3.13 and one BLAS thread per process, and ran one job of this work at a time under
`nice`. The caches were the gate cache (`/tmp/claude-0/fixdata/cache`) and the judge's decoded caches A
(`roundT_squareT_pressureGate_squareT`), B (`roundT_doubleT`), C (`roundT_pressureGate_roundT`) and S / D
(`squareT_platform_squareT_switch`).

## What changed

**Silent miss 1, the column rule** (`resense/clustering.py` `top_is_free`, `_corridor_cluster`; `resense/detector.py`
hands the frame's cloud and channel ids to the corridor clustering).

- A column continues up to the vault; an object standing in the envelope ends inside it.
- The column signature no longer demotes a cluster that meets all three of these conditions:
  - at least half of its voxels are inside the strict envelope;
  - its top is at most 2.95 m;
  - its top is seen free. Over the cluster's azimuth span, the first ring above the top that returns has nothing
    at the top's range, and either a ring in between returned nothing or more of that ring's returns lie beyond
    the top than nearer.
- The ring in between is read from the frame's channel ids, with the ring table only as a fallback. Under a mount
  tilt the table puts the top at the wrong ring.
- Every other rule still applies.

**Silent miss 2, the oversize drop on curves** (`resense/clustering.py` `_split_part`, `_off_structure_parts`,
`_surface_fit`; `find_clusters`).

- On the C curve, the lagging far axis lays the wall across the envelope. A person-size box there merges with
  the wall into a cluster longer than `max_extent`. The 25.09 split refused that cluster and it was dropped whole.
- Now, only when the split refused the cluster, a robust smooth surface y(x, h) is fitted to it:
  - no fit is made without a strict-gauge point;
  - nothing is cut along a surface steeper than 45° to the track.
- Points at least 0.8 m in front of the surface, as seen from the sensor, are linked again.
- Parts at most 3 m long, with strict-gauge points and at least 8 voxels, go through every rule.

**The merge.** Both fixes changed the call of `_corridor_cluster` in `find_clusters`, and that was the only
conflict. The column fix had added `frame_xyz` and `frame_ring`; the structure cut had folded the arguments into a
`rest` tuple that it reuses for each cut part. The tuple now carries the frame cloud. As a result, a cut part goes
through exactly the same `_corridor_cluster` as any cluster, with the free-top test included: "every rule applied"
holds for both fixes at once. Everything else merged textually: `config.py` and both YAML files changed in
different sections, and the YAML files stay byte-identical. The combined tree is each branch plus exactly the other
branch's diff (the `git diff --stat` against either branch is the other fix's diff, line for line). `CHANGELOG.md`
has one entry per fix under `[Unreleased] — detector candidate final/silent-misses`.

## 1. Full regression gate of the combined code

`scripts/regression_gate.py --jobs 2` against
[`regression_baseline_2026-09-29_shell_off.json`](../results/regression_baseline_2026-09-29_shell_off.json): exit 0,
**GATE PASS**. The result is in [`gate.json`](gate.json).

- 0 gated rows are better and 0 worse.
- 209 rows are the same: all 208 non-latency rows (145 of them gated) and one latency row.
- The other 15 latency rows changed; they are information only (another machine).

Frame by frame, all 15 gate outputs are identical to the sealed detector's gate on this machine
(`/tmp/claude-0/fixwork/gate_head/work`). There are 0 differing obstacle or advisory flags and 0 differing detection
or warning counts ([`gate_frames_vs_sealed.txt`](gate_frames_vs_sealed.txt)).

| gated set | rows (all the same as the baseline) |
|---|---|
| five obstacle-free recordings, alarm events / STOP episodes | `doubleT_platform` 1 / 1, `roundT_doubleT` 0 / 0, `roundT_pressureGate_roundT` 0 / 0, `roundT_squareT_pressureGate_squareT` 0 / 0, `squareT_platform_squareT_switch` 7 / 11; together 8 events / 12 episodes |
| the ride (`new_data`, 11 271 frames, 8 pieces) | alarm events 27, STOP episodes 30 |
| `doubleT_obstacle` | labelled hits `object_on_rail` 129, `person_crossing` 61, `object_on_rail_from_frame_75` 126; fp events 0; first alarm frame 8 |
| set O, inside objects (STOP frames / first STOP m / held from m) | big_center 208 / 98.0 / 98.7, small_center 32 / 55.8 / 60.8, small_on_rail 23 / 42.7 / 46.2, small_edge_inside 18 / 35.0 / 38.7, big_edge_inside 7 / 18.3 / 10.3, big_above 56 / 111.4 / 123.6, long_low_on_rails 52 / 87.2 / 95.9, thin_hanging 15 / 30.1 / 31.8 (411 of 801 visible) |
| set O, outside and background | false STOP small_outside_near 0, big_outside 6; background 0 frames / 0 track ids |
| set F straight (detected / first median m / false) | person 6/6 / 151.0 / 6, box1.0 6/6 / 123.9 / 12, box0.5 2/6 / 64.4 / 0, trolley 6/6 / 151.4 / 5, cable 6/6 / 98.9 / 0 |

Information rows, all the same:

- Alarm frames: ride 126, the five obstacle-free recordings 39, `doubleT_obstacle` 193, `squareT_platform_squareT_switch` 37, `doubleT_platform` 2.
- Advisory frames: `doubleT_obstacle` 91, `doubleT_platform` 182, `roundT_doubleT` 173, `roundT_pressureGate_roundT` 107, `roundT_squareT_pressureGate_squareT` 146, `squareT_platform_squareT_switch` 398.
- Set O per-object advisory frames: small_edge_inside 7, small_outside_near 24, big_edge_inside 1, big_outside 43,
  big_above 6; 0 for the other five objects.
- Set F recall bins and sustained medians.

Each finalizer's gate is kept here too:

- [`gate_final_column.json`](gate_final_column.json): `5551c61`, PASS, 208 rows the same. This is the same file as
  `docs/evidence/results/gate_final_column_2026-10-14.json` on `final/column`, which this branch does not carry.
- [`gate_final_oversize.json`](gate_final_oversize.json): PASS, 208 rows the same. The final/oversize agent ran it
  on the working tree before its comment-only edits and checked that `d8f5770` has the same code (the AST without
  docstrings, and the parsed YAML).

`ride.health` differs between the four gates on this machine: ok / warn 11 077 / 194 for the sealed HEAD,
11 080 / 191 for final/column, 11 067 / 204 for final/oversize and 11 079 / 192 combined. These counts include the
latency warning of `resense/health.py`, so they follow the machine's load. They are not a gate row, and no decision
depends on them (`health.latency_affects_decision` is off).

Gate latency in ms, mean / p95 (information only):

| | the ride | C |
|---|---|---|
| sealed HEAD, 13.10 evening | 28.7 / 40.9 | 27.2 / 35.0 |
| final/column, under another agent's gate | 32.4 / 46.9 | 29.2 / 39.3 |
| final/oversize, under another agent's gate | 32.4 / 46.2 | 31.6 / 43.4 |
| combined, alone | 33.6 / 49.3 | 29.3 / 40.7 |

The same code measured A/B on the same frames shows only +0.3–0.6 ms (§5), so this gap is the machine, not the code.

## 2. Combined probes against each finalizer

These are the judge's range tests (`scripts/range_test.py`) through
`/tmp/claude-0/fixwork/judge_oversize/rt_wrap.py`. The wrapper also provides the yawed-box probes; with no yaw it
changes nothing. They ran through the node replica on real backgrounds, one at a time, with the observation-only
hooks of §3 installed. Each cell gives first STOP m / held-from m · STOP frames / visible frames.

- **sealed**: the sealed detector's run: the judge's `baseline_out`, the investigators' sealed runs, or the
  finalizers' own sealed bases.
- **finalizer**: that finalizer's own run of its final code.
- **frames differ**: frames whose decision differs from the finalizer's run.

Windows: A `--start 150 --end 340 --d0 230`; C `--start 0 --d0 230`; B `--start 50 --d0 230`; S `--start 360 --end 620`;
D = the S cache with `--start 100 --end 420 --d0 230`.

### Column probes (the gain of final/column)

| probe | sealed | `final/column` | combined | frames differ vs `final/column` | combined G / C / S |
|---|---|---|---|---:|---|
| A pole 0.3 × 0.3 × 2.8 m, axis | 218.4 / – · 82/177 | 218.4 / 225.9 · 157/177 | **218.4 / 225.9 · 157/177** | 0 | 5 / 15 / 157 |
| A pole, +0.7 m | – / – · 0/176 | 198.2 / 201.1 · 136/176 | **198.2 / 201.1 · 136/176** | 0 | 6 / 34 / 136 |
| A pole, −0.7 m | – / – · 0/181 | 193.2 / 196.2 · 133/181 | **193.2 / 196.2 · 133/181** | 0 | 4 / 44 / 133 |
| A post 0.5 × 0.5 × 2.5 m, axis | 218.4 / – · 56/185 | 218.4 / 220.9 · 157/185 | **218.4 / 220.9 · 157/185** | 0 | 5 / 23 / 157 |
| A post, +0.7 m | 184.9 / – · 30/185 | 199.2 / 214.1 · 150/185 | **199.2 / 214.1 · 150/185** | 0 | 4 / 31 / 150 |
| A pole, axis, `--dropout` | 196.2 / – · 67/176 | 196.2 / 209.6 · 143/176 | **196.2 / 209.6 · 143/176** | 0 | 19 / 14 / 143 |
| A pole, +0.7 m, `--dropout` | 196.2 / – · 11/175 | 196.2 / 197.2 · 133/175 | **196.2 / 197.2 · 133/175** | 0 | 17 / 25 / 133 |
| A person box 0.5 × 0.5 × 1.75 m | 218.4 / 221.8 · 158/185 | 218.4 / 221.8 · 158/185 | **218.4 / 221.8 · 158/185** | 0 | 5 / 22 / 158 |
| S (standing train) pole +0.7 m, d0 60 | – / – · 0/260 | 60.0 / 60.0 · 255/260 | **60.0 / 60.0 · 255/260** | 0 | 0 / 5 / 255 |
| S pole +0.7 m, d0 100 | – / – · 0/260 | – / – · 0/260 | **– / – · 0/260** | 0 | 18 / 240 / 2 |
| B pole, axis | – / – · 0/111 | 51.8 / 57.1 · 28/111 | **51.8 / 57.1 · 28/111** | 0 | 9 / 74 / 28 |
| B pole, +0.7 m | – / – · 0/119 | 50.0 / 55.3 · 27/119 | **50.0 / 55.3 · 27/119** | 0 | 5 / 87 / 27 |
| C pole, axis | – / – · 0/150 | 68.1 / 71.0 · 43/150 | **87.2 / 93.1 · 56/150** | 13 (all CAUTION / GO → STOP) | 37 / 57 / 56 |
| C pole, +0.7 m | – / – · 0/151 | 63.6 / 66.6 · 40/151 | **63.6 / 66.6 · 40/151** | 0 | 51 / 60 / 40 |

Per-bin STOP frames are unchanged from final/column. On A, the pole at +0.7 m gets 3-30 m 18/18 · 30-60 21/21 ·
60-100 27/27 · 100-150 39/39 · 150-200 31/44 · 200-260 0/27.

The one difference is a gain from the two fixes together: **the C pole on the axis**. The pole merges with the wall
at 69.5-93 m. The structure cut alone (final/oversize, run here) gives it 10 STOP frames (first STOP 87.2 m, never
held). The free-top test alone gives 43 (first STOP 68.1 m). The union is 53. The combination gives 56, held from
93.1 m: the 3 extra frames, at 69.5-72.5 m, continue the track that the cut parts started
([`interaction_summary.json`](interaction_summary.json) → `C_pole_gain_split`). The cut parts there are 0.18-0.20 m
wide near the axis, under `column_min_width` 0.25, so the column rule does not apply to them.

### Curve probes (the gain of final/oversize)

| probe | sealed | `final/oversize` | combined | frames differ vs `final/oversize` | combined G / C / S |
|---|---|---|---|---:|---|
| C person 0.5 × 0.5 × 1.75 m | 73.9 / 81.3 · 49/153 | 90.2 / 99.0 · 60/153 | **90.2 / 99.0 · 60/153** | 0 | 40 / 53 / 60 |
| C 1 m cube | 73.9 / 81.3 · 49/153 | 96.1 / 106.5 · 64/153 | **96.1 / 106.5 · 64/153** | 0 | 46 / 43 / 64 |
| C 0.5 m cube | 75.4 / 82.8 · 50/151 | 82.8 / 91.6 · 55/151 | **82.8 / 91.6 · 55/151** | 0 | 50 / 46 / 55 |
| C person, +0.5 m | 69.5 / 76.9 · 46/153 | 84.2 / 93.1 · 56/153 | **84.2 / 93.1 · 56/153** | 0 | 39 / 58 / 56 |
| C person, −0.5 m | 193.5 / 91.6 · 57/153 | 193.5 / 112.4 · 70/153 | **193.5 / 112.4 · 70/153** | 0 | 39 / 44 / 70 |
| C person, +0.7 m (wall side) | 68.1 / 75.4 · 45/153 | 72.5 / 79.8 · 48/153 | **72.5 / 79.8 · 48/153** | 0 | 47 / 58 / 48 |
| C person, −0.7 m | 85.7 / 94.6 · 57/153 | 109.4 / 121.3 · 73/153 | **109.4 / 121.3 · 73/153** | 0 | 38 / 42 / 73 |
| C person, `--dropout` | 73.9 / 81.3 · 49/147 | 90.2 / 99.0 · 60/147 | **90.2 / 99.0 · 60/147** | 0 | 48 / 39 / 60 |
| C person yawed +20° | 72.5 / 79.8 · 48/153 | 93.1 / 102.0 · 62/153 | **93.1 / 102.0 · 62/153** | 0 | 40 / 51 / 62 |
| C person yawed −20° | 72.5 / 79.8 · 48/153 | 88.7 / 97.5 · 59/153 | **88.7 / 97.5 · 59/153** | 0 | 40 / 54 / 59 |
| C 1 m cube yawed +20° | 71.0 / 78.4 · 47/153 | 97.5 / 106.5 · 64/153 | **97.5 / 106.5 · 64/153** | 0 | 49 / 40 / 64 |
| B person | 51.8 / 57.1 · 28/119 | 51.8 / 57.1 · 28/119 | **51.8 / 57.1 · 28/119** | 0 | 11 / 80 / 28 |
| A person | 218.4 / 221.8 · 158/185 | 218.4 / 221.8 · 158/185 | **218.4 / 221.8 · 158/185** | 0 | 5 / 22 / 158 |
| D person (squareT switch) | 105.8 / – · 165/318 | 105.8 / – · 165/318 | **105.8 / – · 165/318** | 0 | 14 / 130 / 174 |

On C the person's 60-100 m bin goes 10/27 sealed → 21/27, and the 100-150 m bin stays 0/34: 2/34 at −0.5 m, 7/34 at
−0.7 m.

**Result: the combination loses nothing either fix gained.** On 26 of 27 probes the combined decisions are identical
frame by frame to the finalizer's own run. On the 27th, the C pole on the axis, the combination is better in 13
frames. No probe has a frame that loses a STOP or turns to GO against the finalizer. The per-probe numbers, bins
and file paths are in [`probes_summary.json`](probes_summary.json).

## 3. Interaction of the two fixes

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

## 4. Robustness replays

Whole recordings went through the node replica (`docs/evidence/judgement_2026-10-13/scripts/probe.py`), with the
hooks installed. The bases:

- A: the judge's `baseline_out/probe`, the sealed detector;
- C pitch / drop: the final/oversize agent's sealed runs;
- C dedup / 5 Hz: run here with the sealed main checkout, read only.

| replay | frames | STOP frames / episodes / CAUTION, sealed → combined | decisions changed | other fields changed (dets, warns, nearest, clear) |
|---|---:|---|---:|---|
| A plain | 545 | 0 / 0 / 191 → 0 / 0 / 191 | 0 | 0 |
| B plain | 252 | 0 / 0 / 169 → 0 / 0 / 169 | 0 | 0 |
| C plain | 268 | 2 / 1 / 116 → 2 / 1 / 116 | 0 | 0 |
| S plain | 877 | 11 / 3 / 446 → 11 / 3 / 446 | 0 | 0 |
| A `--pitch 2` | 545 | 0 / 0 / 193 → 0 / 0 / 193 | 0 | 0 |
| A `--drop 0.3` | 545 | 0 / 0 / 172 → 0 / 0 / 172 | 0 | 0 |
| A `--dedup` | 545 | 0 / 0 / 200 → 0 / 0 / 200 | 0 | 0 |
| A `--every 2` (5 Hz) | 273 | 0 / 0 / 114 → 0 / 0 / 114 | 0 | 0 |
| C `--pitch 2` | 268 | 0 / 0 / 114 → 0 / 0 / 114 | 0 | 0 |
| C `--drop 0.3` | 268 | 0 / 0 / 99 → 0 / 0 / 99 | 0 | 1: k68 clear 144.0 → 100.2 m, still GO |
| C `--dedup` | 268 | 2 / 1 / 100 → 2 / 1 / 100 | 0 | 0 |
| C `--every 2` (5 Hz) | 134 | 0 / 0 / 60 → 0 / 0 / 60 | 0 | 1: k62 clear 151.0 → 110.0 m, still GO |

The two clear-distance changes are single-frame structure-cut parts that the tracker never confirmed. Neither is
column-shaped and the free-top test is not asked, so they are the structure cut's own thin margin, not the
combination. On C `--drop 0.3`, k68 is the part final/oversize already reported: 11 voxels, 100.2 m, lateral 0.98,
and the combined run is identical to final/oversize's in every field. **C `--every 2` is new**: frame 62, 9 voxels
(one over the bar), 110.0 m, lateral 0.92, 1.05 m tall. Per-frame comparison:
[`replays_summary.json`](replays_summary.json).

## 5. Timing (A/B on the same frames)

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

## 6. Tests and lint

- `pytest -q -rs tests`, with the worktree pinned and asserted: **1297 passed**, 8 deselected (their data caches are
  not on this machine), 6 subtests passed, 5 warnings, 0 skipped, in 202 s. That is the sealed suite's 1284, plus
  5 tests from final/column (`tests/test_column_free_top.py` 4, `test_free_standing_post_is_a_stop` in
  `tests/test_late_candidates.py` 1; 1289 on that branch), plus 8 from final/oversize (`tests/test_structure_cut.py`;
  1292 on that branch).
- The CI lint step, verbatim (`ruff 0.15.8 check --exclude docs/evidence/cycle_2026-09-28/complete_timing/default/run_gate.py .`): all checks passed.
- `scripts/sync_params.sh --check`: the parameter files are in sync.
- `scripts/detector_freeze.py verify`: **FAIL, as expected**. It reports `configs/default.yaml`,
  `resense/clustering.py`, `resense/config.py`, `resense/detector.py` and the ROS `detector.yaml` as changed. The
  reseal is left to the orchestrator after review.
- Not run: the CI steps that need Docker / ROS (the image's suite, the node smoke tests, the offline build) and the
  web prototype jobs.

## 7. Residuals

1. **C 118-150 m, the axis-lag band (judge problem 4, untouched).** On the C curve the detector's far axis lags
   1.3-2.2 m while `axis_valid` claims 143-221 m. The box placed on that axis sits 0.2-0.6 m from the wall, as deep
   as wall equipment. The person stays 0/34 STOP frames at 100-150 m (2/34 at −0.5 m, 7/34 at −0.7 m), and GO
   remains at 118-150 m. B and C beyond about 60 m (the poles, B person 28/119) have the same cause.
2. **The structure cut's thin margin.** The largest false part on the plain recordings has 7 voxels against the bar
   of 8. The combined gate pieces also keep an 8-voxel single-frame gauge part on the ride (k8334, 85.2 m, §3). On
   C, single-frame parts appear with `--drop 0.3` (11 voxels) and `--every 2` (9 voxels, new here). None was
   confirmed; the tracker's confirmation is the remaining protection. `structure_cut_tol` 0.8 lies inside the
   0.8-1.2 m depth of wall equipment.
3. **Not one decision on the recordings changed, and the gain is measured on synthetic objects only.** Every gain
   is a judge ray-cast on real backgrounds.
4. **Far off-axis band of the pole.**
   - At +0.7 m: 150-200 m 31/44 and 200-260 m 0/27.
   - At −0.7 m: 100-150 m 29/39, 150-200 m 38/45 and 200-260 m 0/31.

   The cause is the strict envelope's edge margin and the 0.5 core-share guard, not the free-top test. With the
   column rule off, the pole at +0.7 m reaches only 38/44 at 150-200 m.
5. **The free-top test's limits.**
   - Objects taller than 2.95 m (a 3.2 m pole, a ladder) still get the column rule.
   - A column whose face just above the cluster top returns nothing reads as free.
   - Frames without channel ids (set O) fall back to the ring table, which is wrong under a real mount tilt. The
     recordings and probes all have a level mount, so the id path is proven only on synthetic tilted casts
     (`tests/test_column_free_top.py`).
6. **The structure cut's blind spots.**
   - No gain within 0.8 m of the wall (C person +0.7 m: 68.1 → 72.5 m only).
   - None for an edge line plus a face beyond 30 m.
   - The bar costs 4-6 m of first-STOP range on the cubes and on the yawed −20° person.
   - The slope guard covers dy/dx only.
   - The narrow trigger (only clusters the split refused) leaves a split-accepted, rule-dropped part near a wall
     dropped.
7. **The interaction is clean on these data only.** No cut part reached the column rule here, so the free-top
   test has never ruled on one. A cut part 0.25-1 m wide, at least 2.2 m tall, inside the trusted axis range, with
   at least half its voxels strict and its top at most 2.95 m, would be spared if its top is seen free. That is
   the intended behaviour for a pole against a wall, but it has not been exercised. The ride's crossover post at
   117.2 m (k4725; 17 strict voxels, top 2.82 m) would reach the rule, and be given to the free-top test, if the
   axis were trusted beyond the 60 m of that frame. A fix of residual 1 must therefore re-run this census.
8. **S at d0 100, pole +0.7 m:** 0 of 260 before and after, and also with the column rule off. It is still
   undiagnosed (the cluster is mostly missing near the pole).
9. **Not run:**
   - set F with a pole;
   - yawed or tilted range probes with the pole;
   - the judge's continuous whole-ride replay through the node (only the gate's 8 pieces);
   - the Docker / ROS node.
10. **Not resealed.** `docs/DETECTOR_FREEZE.md` and the manifest still describe the 29.09 sources. The reseal, and
    the ALGORITHM / EXPERIMENTS / SCORECARD rows for the two rules, follow review.

## Files

| file | what |
|---|---|
| [`gate.json`](gate.json) | the full regression gate of `5fce816` (PASS) |
| [`gate_frames_vs_sealed.txt`](gate_frames_vs_sealed.txt) | its 15 work outputs against the sealed detector's gate on this machine, frame by frame |
| [`gate_final_column.json`](gate_final_column.json), [`gate_final_oversize.json`](gate_final_oversize.json) | each finalizer's gate (PASS) |
| [`probes_summary.json`](probes_summary.json) | the 27 combined probes: sealed, finalizer and combined summaries, bins, frame-decision differences |
| [`interaction_summary.json`](interaction_summary.json) | the interaction census per run, the column-shaped cut parts, the k4720-4729 and 105-155 m windows, the bar-margin census, the C pole split |
| [`replays_summary.json`](replays_summary.json) | the plain and robustness replays against their bases |
| [`timing_ab.json`](timing_ab.json) | the interleaved A/B timing |
| [`scripts/`](scripts) | the scratch scripts (`.py.txt`, `.sh.txt`; paths are this machine's): the hooks, the census drivers and summaries, the probe and replay drivers, the timing |
