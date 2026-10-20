# F1a fix acceptance: P3's B1 repair on `main` `99dab01` (20.10)

> **For:** P3 and the captain · **From:** P4 data session of 20.10 (handoff T4, second part,
> [`../p4_handoff_2026-10-20/HANDOFF.md`](../p4_handoff_2026-10-20/HANDOFF.md)) · **Detector code:** not touched ·
> **Candidate:** `main` `99dab01` (P3's repair `f07f4b8`, merged; committed source, clean tree) · **Reference:**
> `main` `8c2bf51`, the tree of the F1a exposure ([`../f1a_exposure_2026-10-20/README.md`](../f1a_exposure_2026-10-20/README.md)),
> whose gate rows equal P3's starting main `a5b0ede` ([`../k2_v5c_2026-10-20/README.md`](../k2_v5c_2026-10-20/README.md) §6, row ID) ·
> environment as there (`OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, Python 3.12, numpy 1.26.4).

## Answer

1. **The gate passes against the seal baseline** (8 gated rows better, none worse). **Against `8c2bf51` two gated
   rows are worse:** ride alarm events **18 → 23**, ride STOP episodes **24 → 26** (alarm frames 102 → 111), and
   `doubleT_platform` gains 2 advisory frames. This is P3's own "fresh gate against exact starting main" result
   ([`../f1a_b1_2026-10-20/README.md`](../f1a_b1_2026-10-20/README.md)), reproduced here on committed source.
2. **Unchanged, every non-timing field of every row:** set O (1,510 rows), `doubleT_obstacle`, the other four
   recordings, ride pieces 3 and 6; set F (every sequence, `setF_straight.json`); Falcon, all 4,443 rows (1,364 STOP rows on each
   side; the track models byte-identical).
3. **Every changed decision is traced** (16 frames: 9 new STOP frames, 4 new advisory frames, 3 advisory frames gone;
   table below). Each comes from a low cluster that the old rule made weak and the repair lets through (a *flip*),
   either as a hit of the reporting track or through an association that the flip changed. All 9 new STOP frames stand
   on **rail-head fragments** and on tracker chains through them; the pictures show no object above the rail head in
   any flipped hit (the ride has no ground truth).
4. **Why:** the repair rejects **108** of the **206** low clusters the old rule rejects on set O, `doubleT_platform`
   and the ride (98 flips), and rejects **no** cluster the old rule accepts (0 of 408 checked). **94 of the 98 flips
   lie on a rail** (|lateral| 0.6–1.0 m); **79** flip because of the new top, 11 because of the new reference, 6 by
   either, 2 only by both. On a fragment lying on a rail, the footprint box the new top is read from contains the
   rail head's own returns above the low-stage floor, and the new top is the highest of them: a median 0.04 m
   (interquartile 0.03–0.06 m) above the rail line, whose median is the reference; the margin is 0.01 m. P3 reports
   that the repair fixes B1 on its checks (not rerun here); on the recordings it gives up about half of F1a's
   rail-fragment rejections, and the ride's cost comes from that.
5. **X3 on committed source passes:** 0 of 260 comparisons fail against `8c2bf51`'s X3, and in all 40 cases every
   row's decision, detections and warnings are equal (P3's author X3 on dirty source said the same of its STOP rows).
   One row differs outside them: a health field ([X3](#x3)).

## The changed frames

Gate pieces (the ride in 8 pieces, a fresh detector each; continuous ride row = piece × 1,409 + row). Track ids are the
candidate run's. "Flipped hit": a matched cluster the old rule makes weak and the repair does not.

| frames | change | track | lineage (trace, every hit) | flipped hits: what they are |
|---|---|---|---|---|
| ride 1: 1259–1261 (2668–2670) | 3 STOP | 288 | 6 hits from row 1250; the 6th, at 1259, is flipped and makes it STOP; it then continues on a 3.4 × 0.7 × 0.6 m cluster at the right gauge edge (lateral +1.06; the old run's track 288 held it too, unreported) | right rail at 42.1 m; new top one return 0.13 m above the rail line, other returns along that rail reach 0.19–0.20 m ([`png/ride1_track288.png`](out/png/ride1_track288.png)) |
| ride 1: 1265 (2674) | 1 STOP | 288 | its last hit (1264) is a left-rail cluster both rules accept: 1.9 m across the track from the previous one | none in this frame |
| ride 1: 1266–1267 (2675–2676) | 2 STOP | 305 | 5 hits from row 1261, **4 flipped** | rail fragments alternating right (26.3, 26.1 m) and left (25.6, 24.3 m); new tops single rail-head returns 0.02–0.04 m above the line, one by a 3 mm lower reference ([`png/ride1_track305.png`](out/png/ride1_track305.png)) |
| ride 4: 80 (5716) | 1 STOP (new episode) | 50 | 5 hits at 48.8, 46.2, 41.9, 35.8, 28.6 m in rows 72–79, STOP at 21.8 m: steps of 4–7 m per frame where static warnings close at 1.0–1.8 m per frame, so different clusters chained; the flipped hit (row 76) keeps it alive; its row-77 hit is the cluster that started the old run's track 60 | right rail at 45.6 m, by the reference (0.062 vs 0.079) ([`png/ride4_track50.png`](out/png/ride4_track50.png)) |
| ride 7: 621–622 (10484–10485) | 2 advisory | 202 | 6 hits both rules accept; in the old run they split between tracks 202 and 203, because here a flipped cluster at row 619 (50.05 m, lateral +0.65) gave 203 a hit and moved its prediction | |
| ride 7: 623–624 (10486–10487) | 2 STOP (new episode) | 202 | the 7th hit, at 623, is flipped and makes it STOP | right rail at 47.6 m, new top 0.09 m above the line, independent reference 0.04 m lower ([`png/ride7_track202.png`](out/png/ride7_track202.png)) |
| `doubleT_platform` 36–37 | 2 advisory | 44 | 3 hits on clusters that are not low, on the right (vehicle Y +0.75 to +1.0), the 4th a flipped left-rail fragment (row 35, Y −0.99), the 5th a scan line at the track centre | left rail at 35.3 m ([`png/platform_track44.png`](out/png/platform_track44.png)) |
| ride 2: 1342 | advisory gone | old 578 | the old run's 5th hit; here a track born at row 1340 from a flipped left-rail fragment (36.3 m) takes that cluster, 1.9 m across the track | |
| ride 4: 83–84 | advisory gone | old 60 | its first cluster (row 77) went to track 50 above | |

STOP episodes 24 → 26 are ride 4's and ride 7's new episodes (ride 1's episode starts 3 frames earlier and ends 3 later);
alarm events 18 → 23 are tracks 288, 305 (ride 1), 50 (ride 4), 202 (ride 7) and a second id on ride 4's existing
episode at row 265. P3's continuous replay ([`../f1a_b1_2026-10-20/README.md`](../f1a_b1_2026-10-20/README.md)) has the
ride 1 rows, ride 7's two frames earlier (10484–10485) and an episode at 4153 that the pieces do not have; it has none
at 5709–5717, where the pieces (a fresh detector 80 frames earlier) have ride 4's at 5716. Both are true of their replay.

## The flips

From [`out/summary.txt`](out/summary.txt) (A: old rule; D: repair):

| | checked | old rule rejects | repair rejects | flips | on a rail | new top − old reference on rail flips (median) |
|---|---|---|---|---|---|---|
| set O | 11 | 0 | 0 | 0 | | |
| `doubleT_platform` | 58 | 43 | 27 | 16 | 16 | 0.044 m (0.029–0.062) |
| ride (8 pieces) | 339 | 163 | 81 | 82 | 78 | 0.041 m (interquartile 0.029–0.064) |
| all | 408 | 206 | 108 | 98 | 94 | |

The flips by distance: 21 at 3.0–4.4 m (the rail head just ahead of the vehicle; none of them is in the lineage of a
changed decision), 26 at 20–30 m, 38 at 30–40 m, 11 at 40–50 m, 2 at 50–55 m.
Information for P3, not a proposal: counting the footprint's returns at or above the repaired reference + margin
([`out/flips_footprint_count.txt`](out/flips_footprint_count.txt)) does not separate these from an object by itself:
69 of the 77 flips at 20–55 m have 0–4 such returns and 8 have 6–13; the 21 near-range ones have 6–164 (a dense rail
head). Counted as the cloud holds them: most returns of these recordings appear twice in it (in one dump 4,250 rows,
2,282 distinct points).

## How it was checked

| check | method | result |
|---|---|---|
| gate | `regression_gate.py` on the clean `99dab01` tree, seal baseline, `--jobs 4`; rows against the `8c2bf51` gate JSON ([`scripts/gate_diff.py`](scripts/gate_diff.py)) and per frame against its work files | as in the answer ([`out/gate_rows.txt`](out/gate_rows.txt), [`out/identity_gate_8c2bf51_vs_99dab01.txt`](out/identity_gate_8c2bf51_vs_99dab01.txt), [`out/gatework_f1a.tar.xz`](out/gatework_f1a.tar.xz)); P3's numbers reproduced exactly |
| Falcon | the whole stream through `falcon_trace.py` on each tree, compared on every non-timing field | 4,443 rows, 0 differ; track models byte-identical ([`out/falcon_identity.txt`](out/falcon_identity.txt)) |
| the trace does not change the run | [`scripts/f1a_fix_trace.py`](scripts/f1a_fix_trace.py) (the gate's own replay, `rail_reference_check` and `Tracker.update` wrapped read-only) against the plain gate rows (`cmp_frames.py`) | candidate 13,126 rows (set O, `doubleT_platform`, 8 ride pieces), reference 5,635 rows (ride 1, 2, 4, 7): **0 differ**; 383 / 143 differ only in the latency health level ([`out/identity_trace_vs_gate.txt`](out/identity_trace_vs_gate.txt), [`out/identity_trace_old_vs_gate.txt`](out/identity_trace_old_vs_gate.txt)) |
| the recomputed rules are the detector's | for every checked cluster, the tree's rule recomputed from the same arrays against what `rail_reference_check` returned | candidate 408 / 408, reference (`8c2bf51`) 296 / 296 |
| positive control for the old rule | the old rule recomputed on the candidate's states against the clusters the `8c2bf51` detector made weak (T4's record, an independent run) | 163 = 163, every (frame, distance, lateral) equal ([`out/positive_control_A_vs_T4.txt`](out/positive_control_A_vs_T4.txt)) |
| no new rejection | clusters the repair rejects and the old rule accepts | 0 of 408 (P3's claim on 250 states, here on every frame of set O, `doubleT_platform` and the ride) |
| lineage, every changed frame | the matched clusters of each reporting track up to the frame, on both trees (`.tracks.ndjson`) | the table above ([`out/summary.txt`](out/summary.txt) §2, [`out/lineage_detail.txt`](out/lineage_detail.txt), [`out/lineage_old.txt`](out/lineage_old.txt)) |
| labels by looking | every flipped hit of every new STOP / advisory track drawn: top view and side view, the footprint, both references and both tops ([`scripts/f1a_fix_plot.py`](scripts/f1a_fix_plot.py)) | every flipped hit lies on a rail line at rail-head height; above the threshold in its footprint are one or two distinct returns on that rail line, 0.01–0.13 m above the reference (each held twice in the cloud), except ride 7 row 623, whose repaired reference is the independent one, 0.04 m lower, with ten entries 0.03–0.13 m above it; nothing else rises in any footprint |
| physical plausibility | track 50's steps against static warnings in the same frames (track 42: 108.1 → 103.4 m in rows 70–73); the ride's speed estimate where present (ride 1: 13.9–15.4 m/s; ride 7: 16.0–17.0 m/s) | track 50 moves 3–5 times faster than a static object: a chain of clusters, not one object; tracks 288, 44 and 592 jump 1.9 m across the track |

Not checked: what the gauge-edge clusters of tracks 288 (lateral +1.06, 0.6 m tall) and 50 (21.8 m, lateral +1.23)
physically are (no ground truth; they did not STOP in the old run); P3's synthetic B1 cases and continuous replay (not
rerun); any variant of the repair.

## X3

`robustness_battery.py` (the standing battery, unchanged judge probe, `-j 2`) on the clean `99dab01` tree, MEASURED,
exit 0 ([`out/x3_f1a.json`](out/x3_f1a.json)), compared with the `8c2bf51` run of the same battery
([`../k2_v5c_2026-10-20/runs/data_8c2bf51/x3/x3_off.json`](../k2_v5c_2026-10-20/runs/data_8c2bf51/x3/x3_off.json)) by
[`scripts/x3_compare.py`](scripts/x3_compare.py): the battery's own `compare_metrics` (its tolerances) per case, and
the raw probe records frame by frame ([`out/x3_compare.txt`](out/x3_compare.txt)).

| | result |
|---|---|
| battery comparison | **0 failed of 260** |
| raw records, decision + detections + warnings | equal in **40 of 40** cases, every row; STOP rows equal in every case |
| raw records, any other non-timing field | the latency health level / message (1,711 / 1,738 rows), and one `clear` value: set O under +2° roll, row 202, 26.6 → 4.8 m, both runs STOP on the same object at 26.6 m with the same advisory at 4.2 m (a candidate near 4.8 m caps the clear distance; consistent with a near low cluster no longer weak, not traced: the battery's probe is not instrumented) |
| positive control | the same comparison of variant B against `8c2bf51` finds B's 6 recorded failures exactly and 0 of 40 cases equal ([`out/x3_compare_positive_control_B.txt`](out/x3_compare_positive_control_B.txt)) |

X3's four bags are `squareT_platform_squareT_switch`, `doubleT_obstacle`, `roundT_squareT_pressureGate_squareT` and
set O; the ride and `doubleT_platform`, where every change of the gate is, are not in the battery. The raw probe records of
both runs are in [`out/x3_raw_8c2bf51_99dab01.tar.xz`](out/x3_raw_8c2bf51_99dab01.tar.xz) (unpack to `/home/user/out/x3/`,
the summaries' `raw_path`; each summary carries their sha256).

## Files and reproduce

`out/`: the gate JSON and per-frame rows, the X3 summary and raw records, the summaries named above, `png/`,
`trace_fix_records.tar.xz` (the
candidate's per-cluster and per-track records, and the dumps of the 98 flipped clusters) and `trace_old_records.tar.xz`
(the reference's records).

```
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
S=docs/evidence/f1a_acceptance_2026-10-20/scripts
RESENSE_REPO=<99dab01 tree> PYTHONPATH=<99dab01 tree> python $S/f1a_fix_trace.py <cache> <trace> --jobs 2
RESENSE_REPO=<8c2bf51 tree> PYTHONPATH=<8c2bf51 tree> python $S/f1a_fix_trace.py <cache> <trace old> --names new_data --pieces 1,2,4,7
python docs/evidence/integration_2026-10-19/scripts/cmp_frames.py <trace> <gate work 99dab01>   # identity
python -I $S/f1a_fix_summary.py <trace> <gate work 8c2bf51> <gate work 99dab01>
python $S/f1a_fix_plot.py <trace> <png> new_data_1 305 1267
RESENSE_REPO=<99dab01 tree> python -I $S/x3_compare.py <x3 8c2bf51.json> <x3 99dab01.json>
```
