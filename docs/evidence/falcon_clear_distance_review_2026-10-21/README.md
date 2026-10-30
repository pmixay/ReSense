# Independent review: Falcon clear-distance fix (`claude/falcon-clear-distance-1.3`, head `16efbcc`, detector commit `d85e265`)

Reviewer branch `claude/falcon-clear-distance-review-1.3`. Control = tag `v1.2.0` = `3b73bbe`. The author's control is `6ee469c`;
`git diff v1.2.0 6ee469c -- resense configs ros2_ws native` is empty, so the detector bytes are the same.
No file under `resense/ native/ configs/ ros2_ws/` was changed. The held-out G3 set was not touched.

## Verdict: ACCEPT WITH CONDITIONS

The change does what the author says on every check I could run. Only `clear_distance` moves, and it only goes down. The Falcon
defect drops from 38 frames to the 4 the author names. The two ON switches are sound as designed. I could NOT re-run the
detector on the Falcon raw stream or the Pandar recordings (network, below), so the end-to-end replays are checked on the author's
committed raw outputs, not regenerated. Conditions:
1. C1: the captain updates the docs / BACKLOG wording (see F2, F3) and reseals; `detector_freeze verify` fails on this branch by design.
2. C2: someone with data access re-runs the Falcon replay once on the sealed commit (reproducer R1) before release. This review cannot
   substitute for it.
3. C3: F1 below is read and accepted (a deliberate semantic of `clear = 0` with a confirmed obstacle, no health message).

## Findings, ranked

| # | severity | finding | reproducer |
|---|---|---|---|
| F1 | medium (design, not a bug) | `lost_bed` reports `clear_distance = 0` with no health message and no level change. In 52 Falcon rows: 35 CAUTION (no obstacle) and 17 STOP at 5.7-7.8 m. `level` stays `ok` and `messages` stay empty, so a consumer sees CAUTION or GO-like health with clear 0 and no reason. If a lost bed ever coincides with decision GO, `clear = 0` appears with GO (0 such rows in 4,443 Falcon + 15,269 Pandar rows, but nothing prevents it). The `level >= 2` precedent also sets FAULT; this does not. | R3 |
| F2 | low (docs) | Documented meaning agrees in the "lost track model -> 0" sentence (ALGORITHM §4b, Russian text, line ~601), but the same section defines clear as "metres to the nearest confirmed obstacle, otherwise the monitored range". With `lost_bed` the value is 0 *below* a confirmed obstacle at 6 m. Also `docs/ARCHITECTURE.md:453` and `ALGORITHM.md:832` quote "clear extends past an object in 300 of 605 frames (set O)": those counts are not re-measured on the new defaults, round-down changes 283 set-O rows. | grep |
| F3 | low (comment) | `resense/config.py` (the `clear_lost_bed` comment) says "on the Falcon 52 frames (4361-4410)". The measured run is 4359-4410 (52 rows). The count is right, the frame range in the comment is wrong. | `scripts/bed_margin.py` -> `out/bed_margin.txt` |
| F4 | low / coverage | "0 `lost_bed` rows of 15,269 Pandar frames" evaluates the criterion only where the mount calibration is final: **12,277 of 15,269** frames (80 %). `doubleT_obstacle` 11 of 201, `roundT_doubleT` 62 of 252, `roundT_pressureGate_roundT` 78 of 268, `doubleT_platform` 141 of 345 frames are evaluated. For the rest the rule cannot fire (and cannot protect: on the Falcon the first 192 frames are likewise unprotected). Margin where it is evaluated: max excess -0.52 m (set O), -0.59 m (ride), i.e. >= 0.5 m inside the tolerance everywhere (see Q2). Falcon outside the run: max -0.138 m (frame 4411), 22 rows within 0.3 m of firing, so the Falcon itself is nearer the line than any Pandar frame. | `out/bed_margin.txt` |
| F5 | informational | The criterion evaluates the model at X = 5..30 m, but `floor_range` of the bed can start at 12-16 m (frames 4394, 4401), so X = 5-10 m are linear extrapolations. This is the same convention as H'; the margin data above says it does not matter on Pandar. Not tested: a valid model on a steeper-than-6.7 % ramp or a very short visibility range. | -- |
| F6 | informational | Residual: Falcon frames 4411-4414 still report clear 20.3 / 18.5 / 16.6 / 40.0 m with an object nearer than `gauge.range_min`; also 4415-4424 report 40.0 m (the committed `person_check` lists 4415, 4416, 4421 as overstating). The README counts 4 against P4's 38, and says so; the later frames are mentioned only in the person-check table. Not fixed, as stated. | R2 |

No finding of the kind the task asked about was found: neither switch can raise `clear`, and neither touches decision, detections,
warnings, nearest or health level (Q1).

## Q1. Diff, line by line (`git diff 6ee469c d85e265 -- resense configs ros2_ws native`, 4 code files + 2 identical YAML)

* `health.py`: `bed_off_mount_plane` is pure (`rail_z(xs)` reads, nothing is written; `tol <= 0` returns False). In `HealthMonitor.update` the new block comes
  **after** `monitored`, `clear` (min with obstacle, min with candidate) are computed and before the `out` dict. It assigns only `clear`
  and the trace `last_clear_rule`. Every other output field (`level`, `decision_level`, `messages`, `monitored_range`, ...) is computed above it. `lock_lost` is the old condition
  bound to a name (same truth value, the flag call is unchanged).
* Branches: `lost_model` (default OFF) -> 0; `lost_bed` -> 0; `round_down` -> `floor(clear*10)/10`. Each result is <= the old `clear` (0 <= anything >= 0;
  `floor(c*10)/10 <= c` up to 1e-15, and the output is `round(.,1)`). `clear` is never raised. `clear` is >= 0 so `-0.0` cannot occur.
* `detector.py`: the `bed_conflict` bool is computed only with `clear_lost_bed` on and a final calibration (`ok` / `identity`, finite height); it is passed to `health.update` and used nowhere else.
  It does not feed the decision, the clusters or the tracker (grep of `bed_conflict` in `resense/`: 4 hits, all in the diff).
* Defaults: `clear_lost_bed` and `clear_round_down` are True in `HealthConfig` and in both YAML files (identical files; a test checks the equality).
* Consumers of `clear_distance` (grep over `resense/`, `ros2_ws/`, `scripts/`, `webapp/`): `decision_policy.candidate_ranges` only lowers it (`min`, `floor`);
  `detector_node` publishes it; `check_dry_run` only requires 0 on invalid frames; `webapp envelopeSpan` draws the verified span up to the obstacle regardless of clear (cosmetic: with clear 0 and no obstacle no portals are drawn).
  No consumer was found that treats `clear == 0` as a decision input.
* Semantics: see F1/F2. Soundness of the bed-lost condition: Q2.

## Q2. Is the bed-lost condition sound?

* It is the H' criterion (`mount_cross_tol` 0.5 m + `mount_cross_grade` 0.05 * X, X = 5..30 m) applied to the bed. A grade of 5 % at 30 m is allowed 2.0 m, at 5 m 0.75 m.
  A curve changes the lateral model, not `rail_z`; a platform does not move the rail head. Real pitch of +-1.5 deg is 0.13 m at 5 m, 0.8 m at 30 m: inside.
* Data: the bed margin on all 15,269 Pandar frames (12,277 evaluated, F4): max excess -0.52 m, so >= 0.5 m of headroom everywhere, including both platform recordings, the squareT switch, set O and the 8 ride pieces. `out/bed_margin.txt` (re-aggregated from the author's committed `bed_excess` trace, not from my own run).
* Positive control for the "never fires on Pandar" claim: the same criterion fires in the Falcon on exactly 52 contiguous rows 4359-4410, with excess 0.35-3.72 m
  (`out/bed_margin.txt`); the unit tests `test_clear_lost_bed.py` fire it on constructed beds +0.9, +2.0 m and a 12 % slope. I ran them: all pass.
* Not tested (unverified): a different mount height than the stored one (B4: a wrong height would give clear 0 for the whole run; conservative); a valid steep ramp; the Falcon without a ring field (the criterion does not use rings: it reads only the bed model and the calibrated height, so the missing ring field cannot trigger it; on the Falcon here the rule fired correctly).
* The clear 0 is still produced when the lock is good and the bed is good but only X = 5 m is off by > 0.75 m (e.g. a short-visibility extrapolation, F5). No such frame exists in the data; a tight limit.

## Q3. Independent re-derivation (what was checked and how)

R1/R2 need the Falcon raw stream (6.7 GB) and the Pandar recordings; the proxy of this container stopped the download (the Yandex storage host
failed the TLS handshake; I was refused further probing). So the raw-point replays (the Falcon cloud dump, `raw_check.py`) are **not re-run**. What I did instead, all with my own scripts
in `scripts/`:

| check | method | result |
|---|---|---|
| Falcon record, 4,443 rows | `cmp_records.py`: P4's shipped record (`l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz`, an independent source) vs the author's control vs the author's final, every field except timing | P4 == control in all fields; control vs final: **0 rows differ in any field other than `clear`; 1,006 `clear` lowered, 0 raised** (`out/cmp_records_falcon.txt`) |
| positive control of that comparator | one row (2000) of the final record gets `decision` / `dets` / `nearest` / `msgs` / `level` altered | each reported as exactly 1 differing row (row 2000) |
| Falcon frames 4356-4431, before/after | table printed from P4's record and the final record (`out/falcon_frames_4356_4431.txt`): 4359-4410 -> 0, 4411-4424 unchanged | 38 non-STOP frames of 4373-4414 with clear > 0 in control (matches P4); final: 4 remain (4411-4414). `lost_bed` rows == rows with `bed_excess > 0` (52 = 52, contiguous 4359-4410), decisions 35 CAUTION / 17 STOP / 0 GO |
| STOP clear > nearest, Falcon | recomputed from records | control 575 of 1,364 STOP rows, final 0 |
| node path | `*.c.jsonl.xz` (conservative and small_candidate) | control 145 -> final 0 in both policies; node decision == detector decision in all rows; node clear raised 0, lowered 224 |
| Pandar per-frame rows | `cmp_gate_rows.py` on `gate_rows_control` vs `gate_rows_final` (15,269 rows, 15 files): every key but `clear_distance` and timing | 143 rows differ, all in `health` of `new_data_1` / `new_data_4`: they carry or lack the machine-speed "latency p95 ... over the budget" message (86 messages only, 57 `level` + messages), every non-latency message and `decision_level` equal, `obstacle` equal; **1,553 `clear` lowered, 0 raised** (`out/cmp_gate_rows_pandar.txt`); positive control (one `n_points` +1) reported as 1 extra differing row |
| Pandar STOP vs clear | recomputed | 791 STOP rows with detections: control 257 beyond the nearest detection (max 0.05 m), final 0 |
| gate JSONs | flattened diff of control vs final | 33 leaf values differ: commit, config hashes, native build name, timings, `ride/health ok/warn` 11025/246 -> 11082/189 (= the 57 latency rows) |
| property fuzz | `fuzz_health.py`: 28,000 `HealthMonitor.update` calls, random cloud / lock / obstacle / candidate / `bed_conflict`, 7 switch combinations vs all-off | other fields differ: 0; clear raised: 0; clear above the 0.01 m-rounded obstacle with round-down: 0; round-down drop > 0.1: 0 (`out/fuzz_health.txt`). Positive controls: a monitor that flips `level` -> 28,000 flagged; one that adds 0.1 to clear -> 19,763 raised and 3,709 above obstacle flagged |
| tests | lane tests + `test_clear_cap.py` 22 passed; full suite `pytest tests`: **2,488 passed**, 8 deselected (the one test the author lists as failing, `test_rail_start...`, is skipped here: it needs `/data/cache/new_data`) | `out/pytest_full_branch.log` (needs `apt-get install libegl1` for open3d in this container) |
| looking at data | `person_trace_f4396.png` | the object (0.9-1.6 m over the plane, X 4.3 m, 0.5-0.9 m wide) sits far below the model rail head at +2 m; the model bed at the ceiling, as the handoff says |

## Q4. Residual frames and HANDOFF

* 4411-4414 (and 4415-4416, 4421): the bed model is back (`bed_excess` -0.14 .. -0.51), the object's returns are nearer than `gauge.range_min` 3.0 m; the committed `person_trace.tsv.xz` says 4411: 671 returns, 4416: 11. Not fixed by this lane, as the author states. At 0.08 m/frame the object leaves the 3 m range in about 6 frames. Reported honestly (README "Failed").
* HANDOFF trace: consistent with the committed data. `rail_score` is -1.0 for 4359-4414 in the x-trace (`n >= 0.05` in 4373-4414: 0 of 42); the model bed
  `floor_range` starts at 12-16 m and the bed is 0.35-3.7 m beyond the H' tolerance in 4359-4410; the H' cluster at 9.4-9.7 m (`height_conflict`, hmin 0.12-0.33 over the model bed, i.e. the ceiling) is a separate cluster, in 4394-4398 as the handoff says;
  the visible body part (nothing below 0.86 m over the plane at 4.3 m) matches the beam geometry (1.77 m - 4.3 m * tan 10-11.5 deg = 0.87-1.0 m). "Object only partly visible", "identity unverified" is the right caution. What I could not verify: the corridor-index counts (0 returns in the corridor, 4383-4398), which need the dumped clouds (not committed).
  The handoff's conclusion (the missing piece is use of the bed/mount disagreement in the corridor or a held bed) is a hypothesis, not a measured fix; this lane correctly changed no decision logic.

## What was not checked (unverified)

Re-running the detector on the Falcon (4,443 frames) or on any Pandar recording; X3 (40 cases, 29,765 rows; only the committed summary/diff was read, not re-derived); raw-point checks of changed rows (`raw_check.py`, `person_check.py` need the clouds); `gate` re-run;
the ROS graph itself; the held-out G3 set (by rule); any sensor other than the Pandar and the Falcon.

## Reproducers

```
R1 (needs data, author's scripts): scripts/cache_falcon_raw.py ... ; scripts/run_falcon.py <cache> --out OUT/cand (branch tree) and OUT/ctl (git worktree of v1.2.0); then
   python docs/evidence/falcon_clear_distance_review_2026-10-21/scripts/cmp_records.py OUT/ctl/<run>.jsonl.xz OUT/cand/<run>.jsonl.xz
R2: python scripts/cmp_records.py ../l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz ../falcon_clear_distance_2026-10-21/results/falcon/final_d85e265.jsonl.xz   (clear 1006 lowered, row 4411-4424 unchanged)
R3 (F1): in a Python shell with the venv: HealthMonitor(cfg with clear_lost_bed=True).update(xyz, {}, track, GaugeConfig(), 150.0, 0.05, None, obstacle_distance=6.2, bed_conflict=True)
   -> clear_distance 0.0, level "ok", messages [] (the author's tests/test_clear_lost_bed.py::test_a_confirmed_obstacle_does_not_keep_a_range_over_a_lost_bed asserts exactly this)
F3/F4: python scripts/bed_margin.py <trace_bed dir from results/pandar/trace_bed_diag_53fb331_with_bed_excess.tar.xz> <results/falcon/final_d85e265.x.jsonl.xz>
fuzz: RESENSE_REPO=<checkout> PYTHONPATH=<checkout> python scripts/fuzz_health.py 7 4000
Pandar rows: tar -xJf gate_rows_control_v1.2.0.tar.xz -C A; tar -xJf gate_rows_final_d85e265.tar.xz -C B; python scripts/cmp_gate_rows.py A/gate_ctl B/gate [--inject]
```
