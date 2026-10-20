# P4 review of the two switches that are on: R3 cable confirmation and H1 positive collision core (20.10)

> **For:** Pavel (captain) and P3 · **From:** P4 evaluation session of 20.10 · **Step:** the independent safety review of
> [`DETECTOR_FREEZE.md`](../../DETECTOR_FREEZE.md) step 3, for the two switches the seal lists as on and not reviewed by P4 ·
> **Detector code:** not touched (`resense/`, `native/`, `configs/`, the ROS package); every switch is toggled by `--set` overrides
> only · **G3:** not touched · environment: Python 3.12.3, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, open3d 0.19.0 (only for the
> ICP odometry of the A-axis probe), native kernels built per worktree (`_resense_native.so` sha256 `67fa0887…`, equal to the shipped
> run's), `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`.

## Which source this is about, and what changed under it

The task named detector 1.2.0 sealed on `cc6226e` (detector bytes equal to `5fa865b`; `git diff 5fa865b cc6226e -- resense native
configs ros2_ws` is empty, checked). **That seal has been superseded while this review was running.** `main` now holds PR #45 and
P3's R3 completion `0a472d6` ("Confirm R3 cables from current accumulated-frame support"), which changes `resense/clustering.py`
(+22) and `resense/tracking.py` (+55 −18) and is sealed in `detector_freeze_2026-10-20_1.2.0_r3.json` (`DEFAULT_MANIFEST`,
`detector_freeze.py verify` PASS on this branch). Main `f56ad5e` and `0a472d6` have identical detector bytes (checked).

So this folder has two parts: **§1–§4 review `cc6226e`** (the source the shipped runs of the L16 acceptance measured; the switch-off runs
are new, everything else is reused or reproduced), and **§5 repeats the switch-off runs on the new main** because R3 is one of the two
switches.

## 1. Answer

| switch | claim (BACKLOG "Current detector switches") | result on `cc6226e` |
|---|---|---|
| **R3** cable confirmation (`tracking.cable_confirm_time_s` 0.3) | Set F cable sustained median 34.2 → 17.8 m is explained by coverage 2/6 → 4/6, no lost hits | **Reproduced and recounted independently.** 9 cable hits added, 0 lost, other four kinds identical, false detections unchanged, coverage 2/6 → 4/6, median 34.2 → 17.8 m, the baseline-success cohort 34.2 → 34.2 m. Across the whole gate (15,269 rows), X3 (40 cases, 29,765 rows) and the whole Falcon (4,443 rows) switching R3 on **loses no STOP row** and adds 3 (gate) / 40 (X3, the same cable in 10 variants) STOP rows, all on set O's labelled `thin_hanging` cable except one unlabelled row per case (§2.3). |
| B2 (R3's fast path starts a STOP before the ego-motion veto has its hits) | 0 → 16–17 STOP frames at 37 m | **Still reproduces on `cc6226e` and on the new main**, frame for frame. Whether the STOP is *false* is a labelling question P3 disputes (§2.4); P4 leaves it to the captain. |
| B3 (the cable shortcut never fires on accumulated clusters) | open | **Open on `cc6226e`** (speed given: `cable_kind` 0 on 33 accumulated track-frames, first STOP 76.0 m with and without R3). **Fixed on the new main**: 78.0 m with R3, `cable_kind` set on the accumulated track (§5). |
| **H1** positive collision core (`cluster.column_core_margin` 0.02) | A-axis 82 → 114/177; the inherited High is OPEN; 63 misses | **Reproduced exactly:** 114/177 with H1 on, 82/177 with it off, 63 misses (58 CAUTION, 5 GO). H1 loses no STOP anywhere and adds 32 matched STOP frames on the A-axis probe. **On the real data it never fires:** no cluster has the core flag in any of the 15,269 gate frames, so gate, set F, X3 and the whole Falcon are identical with H1 off in every non-timing field. The benefit is measured on injected objects only; no real tall narrow object exists in the data (§3). |

## 2. R3

### 2.1 Runs (switch off by `--set tracking.cable_confirm_time_s=0`)

| run | result | file |
|---|---|---|
| gate, R3 off, full gate with ride and set F, seal baseline | PASS (4 gated rows better than the baseline; the shipped run, R3 on, has 8) | [`out/runs/gate_r3off.json`](out/runs/gate_r3off.json), [`gatework_r3off.tar.xz`](out/runs/gatework_r3off.tar.xz) |
| per frame, R3 off vs shipped (`cmp_frames.py`) | 15,269 rows; **3 differ** (set O 786–788); 925 differ only in the latency health level | §2.2 |
| set F, R3 off → on (repo comparator `set_f_comparison.py` **and** [`scripts/setf_recount.py`](scripts/setf_recount.py)) | cable: held90 2/6 → 4/6, median 34.2 → 17.8 m, 9 hits added, **0 lost**, cohort 34.2 → 34.2; person, box1.0, box0.5, trolley: 0 / 0, medians equal | [`out/setF_recount_r3.txt`](out/setF_recount_r3.txt), [`out/setF_r3_off_to_on.json`](out/setF_r3_off_to_on.json) |
| X3, R3 off, 40 cases, compared both ways | on vs off: **0 of 260 fail**; 30 of 40 cases equal in every row's decision, detections and warnings, the other 10 (all set O) differ in 40 STOP rows added, 0 lost | [`out/x3_compare_r3off_to_shipped_on.txt`](out/x3_compare_r3off_to_shipped_on.txt), [`out/x3_rows_r3off_to_on.txt`](out/x3_rows_r3off_to_on.txt) |
| whole Falcon, R3 off (4,443 rows, one stream of the published file) | **0 rows differ** from the shipped record in any non-timing field; track models equal | [`out/falcon_shipped_vs_r3off.txt`](out/falcon_shipped_vs_r3off.txt) |

### 2.2 Every changed frame, with the rule that fired

Read-only trace ([`scripts/switch_trace.py`](scripts/switch_trace.py)): the gate's own replay with `find_clusters` and `Tracker.update`
wrapped; after each update every matched track is recorded with its R3 state and the tracker's own `_qualifies` evaluated with R3
on and with R3 off. **The rule is recorded, not reconstructed.** Over the whole gate (15,269 frames, 15 files) the verdict
`_qualifies(R3 on) != _qualifies(R3 off)` occurs on **exactly 3 track-frames, the 3 rows that differ**
([`out/trace_stats_gate.txt`](out/trace_stats_gate.txt)); the fast path is armed (`cable_kind` > 0) on 19 track-frames in all, 15 of
them on set O's cable and 4 on the ride, where it never changes a verdict.

| where | rows | change | what the trace says |
|---|---|---|---|
| gate, set O | 786, 787, 788 | 3 × GO → STOP, track 339, 35.08 / 33.43 / 31.77 m, lateral 0.15, kind `hanging` | hanging fast path (`cable_kind` 2): qualified at 2 / 3 / 4 hits (0.20 / 0.30 / 0.40 s); the standard path qualifies only at row 789 (5 hits, 0.50 s) ([`out/trace_setO_786_788.txt`](out/trace_setO_786_788.txt)) |
| X3, set O, 10 variants | 776–779, 786–790 (40 rows in all) | GO / CAUTION → STOP | the same track 339 chain (e.g. nominal 778, 779, 786–788); 33 of the 40 rows match a label of `thin_hanging` by the battery's own matcher; 7 do not (row 779, §2.3) |
| X3, set O, 14 rows | 780, 781 in 7 variants | decision GO in both; reported `clear` distance 173 m → 44.9 / 43.3 m | the held cable limits the clear distance to the cable's own distance (label at 781: 43.3 m) |
| set F (`far_range_eval`), cable | 9 injected-cable hits | miss → hit | the tall-cable fast path (`cable_kind` 1): track qualified at 3–5 hits (0.30–0.50 s) with R3, not yet without ([`out/setf_trace_added_hits.txt`](out/setf_trace_added_hits.txt)); 17–43 returns on the object, distances 14.5–73.9 m |

Pictures ([`out/png/setO_786_788_r3_on.png`](out/png/setO_786_788_r3_on.png), [`…_off.png`](out/png/setO_786_788_r3_off.png)): the same
three returns, a vertical line 2.7–3.6 m above the rail head at lateral +0.15 m, in both runs; with R3 on the track is red (STOP),
with R3 off it is the same cluster as a track that has not qualified yet.

### 2.3 Does it lose a STOP on a real object? Is the added STOP real?

* **Lost:** none. Gate 0 rows (STOP in the R3-off run and not in the shipped one); X3 0 of 29,765 rows; Falcon 0; set F 0 hits (the
  swapped comparison finds the 9 as lost, which is the positive control: [`out/setF_recount_r3_swapped_control.txt`](out/setF_recount_r3_swapped_control.txt)).
* **Added:** set O row 786–788 lie on the labelled `thin_hanging` cable (label distance 35.08 / 33.43 / 31.77 m, lateral 0.17 / 0.15 / 0.15;
  `in_gauge` true, `plausible` true). First STOP 35.1 m instead of 30.1 m (gate JSON: `first_stop_m`, `stop_frames` 18 vs 15).
* **One unlabelled STOP:** X3 row 779 (7 of the 10 variants). The labels have no entry for 779 (the object returned no point there), but the
  detection is on the labelled object's own track: label distances 53.09, 51.46, 49.83, 48.19 m step by 1.63 m, and the detection at 779
  is 46.56 m (the extrapolation is 46.55 m); lateral 0.20. The battery counts it as an unmatched STOP frame, inside its tolerance.
* **Physical plausibility:** the step of 1.6 m per frame is 16–17 m/s at 10 Hz, inside the ride's range (the A-axis probe's ICP gives a
  median 13.1 m/s; F1a acceptance quotes 14–17 m/s); a 3 cm cable at 35 m returning 3–4 points is what the sensor gives
  (labels: `n_points` 4, 5, 4).

### 2.4 B2 and B3

[`scripts/b2_yaml.py`](scripts/b2_yaml.py) is the shipping review's [`r3_veto.py`](../p4_review_shipping_2026-10-20/scripts/r3_veto.py)
unchanged, run with the shipped YAML (class defaults give the same numbers: [`out/b2_r3_veto_37m.txt`](out/b2_r3_veto_37m.txt)).

| target (carried along at 15 m/s) | R3 on | R3 off | veto |
|---|---|---|---|
| tall, 37 m | STOP frames 2–17 | none | "carried along" from frame 3 |
| hanging, 37 m | STOP frames 1–17 | none | same |
| hanging, 30 m | 1–17 | none | same |
| tall, 30 m | 2–17 | 4–17 | the veto does not hold it without R3 either |
| control: static, approached from 47 m, tall | STOP at frame 2 (R3) vs 4 | — | — |

So B2 **reproduces on `cc6226e`** exactly as the shipping review tabulated it (0 → 16–17 STOP frames at 37 m). What it means is a
**labelling disagreement, not a measurement disagreement:** P3's [R3 completion](../r3_completion_2026-10-20/README.md) argues that a thin
target that keeps a constant distance in the gauge is an obstacle ("everything that falls in the train's gauge is an obstacle, objects
may move", [organizers' answers §12](../../organizers/answers.md)), so the early STOP is correct and the veto's later hold would be a
miss. That reading is supported by the organizers' words as relayed; against it stands the veto's own purpose (a track that does not
close with the travel is not a static object). P4 does not decide it. Exposure on data: R3's fast path is armed on 19 gate track-frames
and changes a verdict on 3, all on set O's labelled cable; the ride has none.

[`scripts/b3_accum.py`](scripts/b3_accum.py): a 3 cm vertical target approached at 10 m/s from 80 m, R3 on / off.

| | speed unknown | speed given |
|---|---|---|
| `cc6226e`, R3 on | first STOP 78.0 m, 41 STOP frames, `cable_kind` set on all 41 track-frames (the cluster is the current frame's) | **76.0 m**, 47 frames; the track's cluster is accumulated on 33 track-frames (frames 1–40), `cable_kind` 0 on all 33, set only on the 16 current-only ones |
| `cc6226e`, R3 off | 76.0 m, 35 frames | 76.0 m, 47 frames |

**B3 is open on the sealed source** (identical numbers to the review's reviewer-only scene: 78.0 vs 76.0 m, 76.0 in both with the speed
given). It is an improvement lost, not a regression.

## 3. H1

### 3.1 Runs (switch off by `--set cluster.column_core_margin=0`)

| run | result | file |
|---|---|---|
| gate, H1 off | PASS; per frame vs shipped: **0 of 15,269 rows differ** (817 latency-level only); every non-health row of the gate JSON equal; set F equal apart from placement float noise (§4) | [`out/gate_json_diff_h1off.txt`](out/gate_json_diff_h1off.txt), [`out/identity_gate_shipped_vs_h1off.txt`](out/identity_gate_shipped_vs_h1off.txt) |
| X3, H1 off | **40 of 40 cases equal** in every row's decision, detections and warnings; 0 of 260 fail; no other non-timing field differs | [`out/x3_compare_shipped_vs_h1off.txt`](out/x3_compare_shipped_vs_h1off.txt) |
| whole Falcon, H1 off | **0 of 4,443 rows differ**; track models equal | [`out/falcon_shipped_vs_h1off.txt`](out/falcon_shipped_vs_h1off.txt) |
| A-axis probe (the author's arguments: the judge's `range_test.py`, 0.3 × 0.3 × 2.8 m, start 150, d0 230, end 340, on `roundT_squareT_pressureGate_squareT`) | H1 on **114/177**, H1 off **82/177**; the committed E-candidate rows (`h1_reference_2026-10-19`) equal the final-source H1-on rows in every hit and decision | [`out/aaxis/`](out/aaxis/) |

### 3.2 Why every real-data comparison is identical: H1 never fires there

The trace marks every cluster that `find_clusters` returns with `collision_core`. In the gate (six recordings, set O, the ride in 8
pieces: 15,269 frames) there are **0 frames with a core cluster, 0 tracks with core hits, 0 track-frames where the column hold differs with and
without the core** ([`out/trace_stats_gate.txt`](out/trace_stats_gate.txt)); the traced Falcon run (4,443 frames, default config) records
no core and no armed cable track either. The positive control for this negative is the same hook on the A-axis probe: it records a core cluster
on the injected body in **48 of the 177 visible frames** (k 268, 270, 272–276, 278–303, 319–333; [`out/aaxis_trace_280_336.txt`](out/aaxis_trace_280_336.txt)). So "gate, X3 and Falcon pass with H1
on" is true but says nothing about H1 on a real object: **neither its benefit nor its harm has been exercised by a real tall narrow body**; the
only evidence is the injected one. (The Falcon trace is a copy of the verified wrapper; it has no positive control of its own.)

### 3.3 The 32 frames H1 adds, and the 63 it does not

H1 off → on turns CAUTION into STOP on 32 frames of the probe and loses none: k 285–305 (X 76.1 … 46.3 m) and k 324–334 (18.3 … 3.9 m).
The 63 misses with H1 on are in 7 runs: 12 (228 … 219 m), 2, 5, 1, 16 (157 … 139 m), 9 (127 … 117 m) and **18 frames at X 44.9 … 19.8 m, all CAUTION**
([`out/aaxis_miss_bins.txt`](out/aaxis_miss_bins.txt)); 58 CAUTION and 5 GO in all. The last run is the one that matters for braking
(3.0 s to 1.3 s before the body at 14.7 m/s). What the trace shows there ([`out/aaxis_trace_280_336.txt`](out/aaxis_trace_280_336.txt)):

* **k 304–318 (47.8 … 27.1 m):** the body's cluster is 2.4–2.6 m tall with **core flag 0** on all 15 frames; on 14 of them it is zone `warning`, reason `column`
  (k 305 is a `gauge` cluster without reason); the column hits among the track's last 10 hits rise from 1 to 10 (hold 2). The decision is CAUTION from k 306.
* **k 319–323 (25.6 … 19.8 m):** the cluster is `gauge`, no reason, **core flag 1** again, but the decision is still CAUTION. The recorded state is
  consistent with the column hold: column hits 9 … 5 of the last 10 (≥ the hold, 2), `core_ready` false until the 6th consecutive core hit (k 324, 18.3 m;
  the rule asks `confirm_hits` 3 and `confirm_time_s` 0.5 s of uninterrupted core, `tracking.py:727-733`). The STOP / advisory decision itself was not
  hooked, so the hold is read from its inputs, not observed. The five frames cost 7.4 m of the approach.
* The axis it is placed on is the baseline detector's own, not a surveyed one (the author states it); the picture
  ([`out/png/aaxis_h1_on_off.png`](out/png/aaxis_h1_on_off.png)) shows a solid 2.6 m body on the axis at 53.8, 38.9 and 21.2 m: STOP with H1 on /
  CAUTION with H1 off at 53.8 m, CAUTION in both at 38.9 and 21.2 m.

This is the open High finding as the author describes it ("63 misses, far-axis reference"). P4 reports it, does not fix it.

## 4. Checks

| check | method | result |
|---|---|---|
| inputs | sha256 of every archive against the published value; `unpack_dataset.py`, `cache_frames.py --every 1 --int16 --stamps`, `cache_decoded.py`; counts per VM_GUIDE §2.4; the six `metadata.yaml` against `bag_metadata/` | dataset.zip `e2316680…` = `scripts/cold_bags.sha256`; set O `d41c2fb2…` and ride `8124b627…` (intake manifest: size and sha256 verified, 221 splits, 11,271 frames); Falcon stream `90dea27d…`, 6,758,209,772 bytes; counts 201 / 345 / 252 / 268 / 545 / 877 / 1,510 / 11,271; metadata original on all six; the battery's own reference check (payload sha256 of the four decoded caches, labels, protocol) accepts them against the shipped run, which is a hash identity |
| source | `git diff 5fa865b cc6226e -- resense native configs ros2_ws`; `_resense_native.so`, `configs/default.yaml` sha256; run workers' `evidence` | empty; both equal to the shipped run's |
| **environment control** | the same gate, X3 and Falcon with **no override** on `cc6226e` against the shipped L16 runs | gate 15,269 rows, **0 differ**; X3 **40 of 40 cases equal, 0 of 260 fail**; Falcon 4,443 rows, **0 differ** (`out/identity_gate_shipped_vs_default.txt`, `out/x3_compare_shipped_vs_default.txt`, `out/falcon_shipped_vs_default.txt`) |
| positive control, gate comparator | `gate_frames.py` / `cmp_frames.py` on `8c2bf51` (K2-off gate rows) vs shipped | **16 changed decisions, 9 new STOP frames, 2,087 differing rows**: the F1a acceptance's numbers ([`out/gate_frames_positive_control_8c2bf51_vs_shipped.txt`](out/gate_frames_positive_control_8c2bf51_vs_shipped.txt)) |
| positive control, Falcon comparator | `falcon_cmp.py` on K2 off vs v5c-15 (committed K2 records) | 4,442 rows differ, 14 STOP lost / 18 added: finds the known difference ([`out/falcon_positive_control_k2off_vs_v5c15.txt`](out/falcon_positive_control_k2off_vs_v5c15.txt)); K2 off vs shipped: 0 differ |
| positive control, set F | the recount with the files swapped | finds the 9 hits as lost |
| positive control, X3 | `x3_compare.py` R3-off candidate against the shipped reference | finds the 14 failures (= what R3 gains), and the same files swapped 0 |
| positive control, H1 | A-axis with H1 off | 82/177, the author's base; 32 frames differ |
| instrumentation does not change results | traced gate vs shipped gate rows; traced set F report vs shipped; traced Falcon vs plain; traced A-axis vs plain | 0 of 15,269 rows differ; hits and per-kind summary equal; 0 of 4,443; summary and every row equal |
| independent recount | `setf_recount.py` recomputes hits and held90 from the raw rows by sorted-distance integer counts, not from the comparator or the evaluator's summary | equals the evaluator's summary and the repo comparator in every kind |
| labels | every changed gate row, every added X3 STOP row matched to a label with the battery's matcher; the one unmatched row explained from the label trajectory | §2.3 |
| by looking | pictures of set O 785 / 786 / 788 with R3 on and off, and of A-axis k 300 / 310 / 322 with H1 on and off (raw returns, track clusters coloured) | they show what the numbers say (§2.2, §3.3) |
| physical plausibility | step per frame, track speed, return counts, heights | §2.3; A-axis body 2.4–2.7 m tall, ≤ 0.3 m wide, on the axis |
| set F placement noise | the shipped set F vs the **no-override re-run** | 929 `gt_vehicle_y_m` values differ by ≤ 7.3e-9 m (a numerical difference of the baseline track placement, seen with no override too); nothing else differs apart from the config hash and wall time ([`out/setF_placement_noise.txt`](out/setF_placement_noise.txt)); `cmp_frames.py` reports `setF_straight_equal: false` because of it |
| lint | `ruff 0.15.8 check` on `scripts/` with the evidence ruleset | pass |

## 5. The same runs on the new main (`f56ad5e`, detector bytes of `0a472d6`)

NEWMAIN_PLACEHOLDER

## 6. What is not verified

* **Real objects for H1.** No cluster in the data has the core flag (§3.2). The A-axis object is injected, placed on the baseline
  detector's axis, not a surveyed track; C-person (55/153), E6 (34/59), the physical replay (32 stationary + 280 outside + 12 moving cases) and the
  author's 0/280 outside controls were **not rerun**.
* **R3 on a real moving target:** there is none in the data; B2 is a synthetic scene.
* **The Falcon switch trace** (zero records) has no positive control of its own; the claim "neither switch is exercised on Falcon" rests on
  it plus the identity of the off-runs.
* **The seal's pending lines** ("X3 and the whole Falcon on the last commit"): the no-override re-run above is exactly that for `cc6226e`
  (identical to the L16 acceptance's runs of `5fa865b`), but only the session that owns `DETECTOR_FREEZE.md` may record it; not edited here.
* The set F hits (9) and set O rows are attributed by trace; the injected-object scenes are on real moving backgrounds with legacy
  detector-axis placement: held90 is not continuous STOP range or braking sufficiency.
* Not run: the full pytest suite; the Docker image; G3.

## 7. For P3 and the captain

See the report in the pull request; in short: (1) the seal moved to `0a472d6`, any older claim on `cc6226e` is for the superseded seal;
(2) B2 is a labelling decision; (3) B3 is closed by `0a472d6` on the synthetic scene; (4) H1 is untested on real data and the 18-frame
CAUTION run at 44.9–19.8 m is the part of the open High that matters.

## 8. Files and reproduce

`scripts/`: `runs.sh` (gate and X3 per switch), `falcon_tee.sh` (one Falcon stream, three runs), `x3_override/sitecustomize.py` (X3 switch
override through the battery's `--resource-adapter`, since the battery has no `--set`; a no-op without `P4_X3_SET`), `switch_trace.py`,
`falcon_switch_trace.py`, `hooks_runpy.py`, `setf_trace.py` (read-only hooks), `gate_frames.py`, `x3_rows.py`, `falcon_cmp.py`, `setf_recount.py`,
`trace_stats.py`, `trace_rows.py`, `b2_yaml.py`, `b3_accum.py`, `aaxis*.sh`, `plot_frame.py`, `plot_aaxis.py`, the data preparation scripts. `out/`: every
output named above; the gate work directories, X3 raw records (their summaries name `/home/user/p4r/runs/…` as `raw_path`; unpack the
archives there), Falcon records, A-axis rows.

```
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=<tree>
S=docs/evidence/p4_review_r3_h1_2026-10-20/scripts
python scripts/regression_gate.py --cache <cache> --jobs 2 --work <w> --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json \
   --out <gate.json> --set tracking.cable_confirm_time_s=0          # or --set cluster.column_core_margin=0
P4_X3_SET="cluster.column_core_margin=0" python scripts/robustness_battery.py --repo <tree> --cache <decoded> --out <x3.json> -j 2 \
   --reference <shipped x3_l16.json> --resource-adapter $S/x3_override
python docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py <falcon_test.zst stream> --out <prefix> --set <override>
python docs/evidence/integration_2026-10-19/scripts/cmp_frames.py <shipped gate work> <work>
python $S/falcon_cmp.py <shipped falcon prefix> <prefix>;  python $S/gate_frames.py <shipped work> <work>
RESENSE_REPO=<tree> python -I $S/x3_rows.py <x3 a.json> <x3 b.json> labels/cloud_with_fake_obj.json
python $S/setf_recount.py <setF a> <setF b>;  python $S/trace_stats.py <trace dir> <shipped work>
```
