# X1 — range attribution: which rule or tracker hold costs each visible non-STOP frame (16.10)

BACKLOG card X1, protocol [§C](../p4_eval_1.1.0_2026-10-16/PROTOCOL.md) with amendment 1 (OpenBLAS
`Haswell`). Harness [`scripts/range_attrib.py`](../../../scripts/range_attrib.py) at `e1ec3e3`
(SHA-256 `05e0771b…`) for **all** results here; runner [run_x1.sh](run_x1.sh); tables built by
[make_report.py](make_report.py). Runtime as in [the P4 report](../p4_eval_1.1.0_2026-10-16/README.md).
Observation only: no detector or judge file was changed.

## Result

| check | 707ea9c | 1.1.0 |
|---|---|---|
| judge outputs with hooks on = hooks off (`verify`; all rows and fields, probe timing excluded) | 11 / 11 | 11 / 11 |
| BACKLOG control numbers, A_cube05: first STOP / held / STOP frames | **135.06 / 83.37 / 66** | same |
| BACKLOG control numbers, S_person_100: STOP frames | **82** | same |
| visible non-STOP rows / with exactly one cause / `unclassified` | 1,316 / 1,316 / **0** | 1,316 / 1,316 / **0** |
| cause from the branches recorded in the tracker = reconstruction from its state | 1,316 / 1,316 | 1,316 / 1,316 |
| sampled label check: frames re-checked / confirmed / **wrong labels** | 64 / 64 / **0** | 64 / 64 / **0** |

The control numbers reproduce the judge's 13.10 summaries exactly, with ICP odometry recomputed here
(judge `icp_odometry.py`, hashes in [icp_SHA256SUMS](icp_SHA256SUMS)). The two versions attribute
identically except **2 rows** of C_cube05 (frame 97 at 84.3 m: 707ea9c `drop:oversize_split_refused`,
1.1.0 `track:confirm_hits`; frame 99 at 81.3 m: `track:confirm_hits` → `track:confirm_time`). Their
STOP frames, first STOP and held-from distances are equal in every case.

## Cause → frames per distance bin (1.1.0, all 11 cases)

| cause | 3–30 | 30–60 | 60–100 | 100–150 | 150–200 | 200–260 | total |
|---|---:|---:|---:|---:|---:|---:|---:|
| no_blob | 0 | 8 | 68 | 106 | 149 | 117 | 448 |
| drop:oversize_split_refused | 0 | 1 | 75 | 100 | 45 | 1 | 222 |
| drop:infra_wall_segment | 0 | 0 | 18 | 40 | 80 | 0 | 138 |
| track:confirm_hits | 0 | 17 | 33 | 32 | 12 | 5 | 99 |
| drop:min_points | 0 | 1 | 34 | 22 | 0 | 0 | 57 |
| demoted:beyond_axis | 0 | 0 | 13 | 31 | 9 | 2 | 55 |
| track:confirm_time | 0 | 5 | 27 | 19 | 3 | 0 | 54 |
| track:explained_run | 0 | 0 | 18 | 15 | 0 | 0 | 33 |
| drop:infra_hardware | 0 | 0 | 13 | 16 | 1 | 0 | 30 |
| track:column_hold | 0 | 0 | 7 | 23 | 0 | 0 | 30 |
| demoted:beyond_height_ref | 0 | 0 | 0 | 12 | 8 | 0 | 20 |
| track:hit_fraction | 0 | 0 | 11 | 8 | 0 | 1 | 20 |
| track:zone_vote | 0 | 4 | 4 | 12 | 0 | 0 | 20 |
| thin_scanline_only | 0 | 0 | 0 | 9 | 7 | 2 | 18 |
| weak_far_only | 0 | 0 | 12 | 5 | 0 | 0 | 17 |
| demoted:column | 0 | 0 | 6 | 10 | 0 | 0 | 16 |
| track:confidence | 0 | 0 | 3 | 7 | 2 | 0 | 12 |
| track:approach_block | 0 | 0 | 7 | 4 | 0 | 0 | 11 |
| drop:low_narrow | 0 | 6 | 0 | 0 | 0 | 0 | 6 |
| demoted:wall_face | 0 | 0 | 0 | 3 | 0 | 0 | 3 |
| outside_strict_gauge | 0 | 0 | 1 | 2 | 0 | 0 | 3 |
| stop_off_object | 0 | 0 | 1 | 1 | 0 | 0 | 2 |
| track:doubt | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| drop:infra_linear_side | 0 | 0 | 0 | 1 | 0 | 0 | 1 |

Per case and version: [x1_tables.md](x1_tables.md); every row: `<version>/<case>.attrib.json`;
judge summaries: `<version>/<case>.judge_summary.json`; everything: [x1_summary.json](x1_summary.json).

Reading for P3 (an attribution, not a design decision):
* **Beyond ~100 m the object mostly never forms a corridor blob** (`no_blob`, 372 of 448 rows are
  ≥ 100 m; e.g. A_cube03 has 1–4 visible returns at 100–200 m). Its returns either fail candidate
  extraction or are DBSCAN noise; the harness does not split these two (see limits).
* **Merging with structure is the largest rule cost at 60–200 m**: the object's returns join an
  oversize cluster whose split is refused (222), a wall-segment-shaped cluster (138), or, less
  often, hardware / linear-side shapes. S_person_150 alone has 97 `infra_wall_segment` rows.
* **Tracker holds are second** and concentrate at 30–150 m: confirmation (`confirm_hits` 99,
  `confirm_time` 54, `hit_fraction` 20, `confidence` 12), then the 29.09 `explained_run` (33) and
  `column_hold` (30), both on the standing-train S cases, plus `approach_block` (11) and `zone_vote` (20).
* Axis / height far-field demotions (`beyond_axis` 55, `beyond_height_ref` 20) sit at 60–200 m.

## How a cause is assigned (one per row)

The precedence, applied to the frame's state *after* the detector ran, is:
1. A **clean gauge cluster** physically on the object → its matched track. The track cause comes from what
   ran **inside `Tracker.update`**: a `sys.settrace` on `Tracker.update`, `_qualifies`, `_carried_along`,
   `_fresh_stop_ok` and the `Track.zone / rule_zone / vote_zone` properties records which gate lines
   executed for that track (`q = False`, `fresh_blocked = …`, `t.reported = …`, with their guarding
   `if`), the exact `_qualifies` inputs and result, and which `return` of the zone properties fired.
   When several `_qualifies` clauses are false, the first in the code's own expression order is named
   (hits, confidence, misses, span, hit fraction). The old reconstruction from the post-update track
   state is stored beside it (`recon_cause`); they agree on every row.
2. Else a **demoted / advisory cluster** on the object → `demoted:<reason>` or `outside_strict_gauge`.
3. Else a **thin / weak cluster** handed to the tracker only → its reported track's cause, or
   `thin_scanline_only` / `weak_far_only`.
4. Else a **dropped blob** on the object → the rule whose `return` actually fired in `_corridor_cluster`
   / `_low_cluster` / `_is_infrastructure` (a `sys.setprofile` return tracer; named from the guarding
   condition's source text, so 707ea9c and 1.1.0 read the same).
5. Else `no_blob`.

"On the object" means the bbox **physically overlaps the object box ± 0.5 m** in X and Y. The judge's
distance tolerance (max(2 m, 3 %) + L/2) is used only to decide whether a STOP report matches.

## Label double check (requested 16.10)

`range_attrib.py check` takes up to 3 rows per cause, spread round-robin over cases and evenly within a
case (fewer when a cause has fewer distinct rows: `demoted:column` 2 of 16, `track:column_hold` 2 of 30,
`stop_off_object` 2, `outside_strict_gauge` 2, `track:doubt` 1, `drop:infra_linear_side` 1). It re-runs
those cases with the sampled frames' **full snapshots** (every blob with its firing-return locals and
the config object the call used, every cluster, every track with its branch record) and requires:
(a) the re-run gives the same cause, (b) traced = reconstructed, and (c) an independent re-evaluation:

* `drop:*`: no surviving cluster physically on the object, and the named rule's expression is
  **re-evaluated from the recorded sizes / heights / laterals with the config the call actually
  used**, and it is the *first* true rule in order (for infrastructure, all five rules are listed).
* `demoted:*` / `outside_strict_gauge`: no clean cluster on the object, and a final cluster with that
  reason (or fewer strict voxels than the gauge bar).
* `track:*`: the matched track's post-update state (not the trace) satisfies the rule against the
  tracker config, e.g. `hits < confirm_hits`, `span_s < confirm_time_s`, `sum(column_hist) ≥ column_hold`,
  vote below `zone_min_fraction`, `withheld`, `fresh_blocked` with an explained history.
* `no_blob`: no blob in the frame physically overlaps the object (the nearest blob's distance is recorded).
* every sample: no matching gauge STOP report exists.

Results per cause and version are in [check_707ea9c.json](check_707ea9c.json) / [check_1.1.0.json](check_1.1.0.json)
(each sample with its evidence) and at the end of [x1_tables.md](x1_tables.md): **64 frames checked per
version across all 24 causes, 64 confirmed, 0 wrong labels, 64 re-runs reproduce the cause, 64 traced =
reconstructed.** I also read the evidence of every 1.1.0 sample. For example, B_person frame 147 is
`confirm_time` with a 0.49996 s span against 0.5 s, and D_cube05 frame 144's refused oversize blob ends
exactly at the object's front face (173.69 m).

**Wrong labels found and fixed during the check (before this result):**

| run | problem | how found | fix | rows affected |
|---|---|---|---|---|
| 2 | 7 rows/version `unclassified:not_qualified` | `table` refuses unclassified | track floats were rounded to 0.01 (0.49996 s read as 0.5 s); keep exact values | 7 |
| 3 | `drop:low_narrow` 0/3 confirmed | first check | checker gap, label right: a low-object stage (straddle / near) calls `_low_cluster` with its own `low_cfg` (min_width 0.35 vs the default 0.15); the check now re-evaluates with the recorded config of the call | 0 |
| 3 | `track:approach_block` 0/3, `explained_run` 2/3 | first check | checker gap: the track was continued by a thin / weak cluster (precedence step 3) | 0 |
| 4 | **attribution to structures short of the object** | my review of the second check's samples (0 automated failures): a bed scan ending at 183.9 m credited for an object at 189.1 m | the judge's distance tolerance had been used as the "on the object" test; now physical overlap | **76 / 1,316 per version relabelled** (e.g. 22 `oversize_split_refused` → `min_points`, 9 → `no_blob`, 9 the reverse, 8 → `infra_hardware`, 6 `outside_strict_gauge` → `no_blob`) |

Runs 1–4 are superseded and not used; their outputs stay external.

## Limits

* `no_blob` does not say whether the returns were removed before clustering (corridor / height
  candidates) or were DBSCAN noise. That would need a hook in candidate extraction.
* One cause per row, by the precedence above. A frame can have several simultaneous blockers
  (e.g. A_cube05 frame 252 fails both `confidence` 0.55 and `hit_fraction` 0.4); the first in code order is named.
* Range objects are ray-cast into real frames (judge method); Set O uses the organizers' objects (frames
  300–340 small_center, 760–790 thin_hanging; 60 visible rows, 6 STOP).
* ICP odometry from open3d is not bit-reproducible run to run (~1e-14 m); the hashed files used are fixed.

External raw outputs (run 5, check re-runs, ICP) are indexed in [raw_sha256.json](raw_sha256.json) and archived in [../p4_eval_1.1.0_2026-10-16/raw/](../p4_eval_1.1.0_2026-10-16/raw/README.md).
