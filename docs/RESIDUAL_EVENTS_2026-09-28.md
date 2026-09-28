# Residual false STOP inventory — 28 September 2026

**Historical inventory:** these saved captures predate the remote detector updates merged after
`9aa1775`; see [integration provenance](RESIDUAL_REVIEW_2026-09-28.md#integration-provenance).

**The saved fresh-onset candidate leaves exactly 27 track events, 117 distinct STOP
frames and 26 STOP episodes across 11,271 ride frames.** There are 133 STOP
track-frames because several tracks overlap. These counts are recomputed from all
eight `fresh_stop_v1/new_data_*.jsonl` files; they are not copied from a summary.

| Capture / mapped support | Events | STOP frames | Episodes | Track-frames | Ordinary | Low | Missed | Off-gauge |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `base` / source trace | 32 | 130 | 31 | 149 | 78 | 19 | 39 | 13 |
| `candidate_defaults_v2` | 32 | 130 | 31 | 149 | — | — | — | — |
| `fresh_stop_v1` / matched source trace | **27** | **117** | **26** | **133** | **74** | **18** | **32** | **9** |

An event is a `(piece filename, track ID)` pair, not a physical object. An episode is
a contiguous run of node STOP frames within one piece; chunk resets are boundaries.
The organizers identify this ride as empty of obstacles. Individual return surfaces
have no surveyed identities: references to columns, bed, edges or attachment below
are geometric hypotheses, never physical labels established by this inventory.

## Provenance and mapping

The machine record is
[`evidence/results/residual_events_2026-09-28.json`](evidence/results/residual_events_2026-09-28.json).
The analyzer is [`../scripts/analyze_residual_events.py`](../scripts/analyze_residual_events.py).
Measurement root: `D:/Datasets/ReSense/cross_ring_2026-09-28_measurement`.

* Every base, candidate, captured-default and compressed trace-archive row is aligned
  to the audited manifest by chunk-local index, global frame ID and exact receive stamp.
  All 11,271 saved default outputs match `base` semantically, excluding runtime latency
  diagnostics only. This comparison does not execute the live working-tree detector.
* Source archives match `base` detections and track models on every frame. Every trace
  event's archive hash is checked; all baseline STOP memberships are checked against
  the source timeline. Candidate and base track models match on every frame.
* Every retained candidate detection equals its same-frame baseline detection, including
  ID and emitted fields. A fresh source cluster must also reproduce the rounded output
  distance, lateral position, centroid, size, voxel count, minimum height and kind.
  ID equality alone is insufficient. The source trace reports zero detection mismatches.
* Source `false_target_trace/trace.json` SHA-256:
  `ba9922128a61d3117407acaa0c682d8ae68ab899302ea635d327894f206ce1e8`.
  Audited ride manifest SHA-256:
  `fff62b753a8468c5910c851bf3d1055d8b4721adf11a9827308426916d9dc12c`.
  The JSON includes SHA-256 for every consumed capture, config, archive, source document,
  analyzer and mapped snapshot. Each event's raw onset cache is rehashed against the
  audited manifest. Other full-ride cache bytes are not rehashed here.
  The saved default configs omit `tracking.fresh_stop_evidence`; the machine diff
  reports that absence as `null`, not as an explicitly serialized `false`.
* Snapshots use the exact saved fresh target mask and verify `n_points_idx`; distinct
  XYZ counts are separate from occupied voxels. **51 fresh snapshots** map to retained
  candidate rows. Missed rows retain only the explicitly
  stale source cluster, with no snapshot, current support statistic or channel IDs.
* This establishes a bounded **source-default mapping**, not equality of hidden candidate
  tracker state or exact candidate point membership. The trace lacks candidate evidence
  history, tracker input-source flags, stored approach/thin history, low bed-template
  state and learned-opinion probabilities. Full source history is referenced by hashed
  input and event key; the last ten onset rows and all candidate STOP rows are retained.

Removed baseline identities: `1:295`, `2:586`, `4:210`, `5:146`, `6:250` (prefix
`new_data_`, suffix piece `.jsonl` understood). Among survivors, `5:358` starts at
**7944**, not the source onset **7943**; the latter's snapshot is never used as its
candidate onset. `6:331` retains **9263–9268** and loses **9271–9274** after the gap.
There are exactly **13 changed node STOP frames**, despite 16 removed track-frames.

## All 27 retained events

Global frame intervals are inclusive; the first interval starts at the candidate onset.
The JSON also contains piece-local intervals, receive stamps and base intervals.
**O/L/M/X** means fresh non-low with positive `n_gauge` / fresh low / missed /
fresh non-low with zero `n_gauge`. These descriptive classes are not reconstructed
`far_thin` or `stop_keep` provenance. Onsets comprise **18 ordinary and 9 low** events.

Onset geometry reports strict/all **trace voxels**, strict trace rings, and full-cluster
rail-relative height. Low ring counts are placeholders, shown as `n/a`; raw channels
can include outside support and are not independent sensors. **A/H** gives the derived
axis/height-reference range; slabs/lock and the full model, mount status, monitored range
and health are preserved per STOP row in JSON. A height-reference crossing alone does
not mean the ordinary far path was ineligible. With zero rail slabs, the separate
no-rail cap also applies (`4:209`: 40 m).

Approach is speed toward the sensor (m/s) / RMS distance residual (m), fitted to the
last five **matched source** hits using receive stamps. `P/F` indicates the saved
numeric rule, not a recorded candidate tracker decision. Negative speed is receding;
fewer than five hits is unavailable. Ordinary and low STOPs need not pass this rule.
At onset, nine fits pass, fifteen fail and three have insufficient matched history.

<!-- BEGIN GENERATED INVENTORY -->
| Event suffix | Candidate STOP frames (inclusive) | N | Onset; min–max m | O/L/M/X | Onset strict/all vox; rings; height m | Onset A/H m; slabs/lock | Approach v/RMS | Onset/history detail |
|---|---|---:|---|---|---|---|---|---|
| `0.jsonl:3` | 23–30 | 8 | 143.58; 137.94–143.58 | 7/0/0/1 | 8/8; 4; 0.523–1.483 | 159/130; 3/1 | 1.86/2.49 F | Ordinary four-ring onset beyond the height reference; prior axis/height demotions. |
| `0.jsonl:383` | 1378, 1393–1395 | 4 | 138.92; 121.96–138.92 | 4/0/0/0 | 5/5; 4; 0.875–2.767 | 193/110; 3/1 | 9.77/0.03 P | Compact vertical onset after column/axis/height history; two separated STOP runs. |
| `1.jsonl:74` | 1847 | 1 | 155.44; 155.44–155.44 | 1/0/0/0 | 10/11; 5; 1.010–2.768 | 171/160; 3/1 | 8.62/1.39 F | Long full target, but the earlier snapshot study found only 0.19 m strict along-X extent. |
| `1.jsonl:286` | 2668–2678 | 11 | 42.06; 31.87–42.06 | 4/3/4/0 | 5/5; n/a; 0.037–0.108 | 83/90; 3/1 | 20.44/0.54 F | Low-to-ordinary-to-low history; six hits in ten frames; only 6/10 matched at onset. |
| `1.jsonl:292` | 2671–2673, 2675–2676 | 5 | 32.66; 28.96–32.66 | 0/3/2/0 | 7/7; n/a; 0.033–0.066 | 115/85; 3/1 | -1.09/0.38 F | Five-hit low onset after one ordinary hit and one miss; shallow top below same-band reference. |
| `1.jsonl:298` | 2671–2673 | 3 | 82.54; 82.54–87.66 | 2/0/1/0 | 10/15; 2; 0.236–0.457 | 115/85; 3/1 | 18.02/2.59 F | 6.80 m full target but 0.09 m strict along-X extent in source snapshot study. |
| `1.jsonl:293` | 2673–2674 | 2 | 43.23; 41.83–43.23 | 2/0/0/0 | 4/8; 2; 0.121–0.615 | 197/135; 2/1 | -15.07/0.32 F | Distance increases 33.12 to 43.23 m before onset while low/ordinary support switches. |
| `1.jsonl:310` | 2675–2677 | 3 | 31.87; 31.87–33.65 | 2/0/1/0 | 21/25; 4; 0.121–0.638 | 193/100; 2/1 | 0.18/1.06 F | Four left-side low hits precede a broad ordinary fifth hit with 21 strict voxels. |
| `1.jsonl:306` | 2676–2677 | 2 | 28.61; 28.48–28.61 | 0/1/1/0 | 3/3; n/a; 0.038–0.052 | 120/150; 2/1 | -3.62/0.56 F | Five low hits with gaps; 3.8-5.2 cm onset height, below same-band reference. |
| `1.jsonl:377` | 2729–2730 | 2 | 105.10; 103.98–105.10 | 1/0/1/0 | 7/8; 4; 0.340–1.556 | 115/120; 3/1 | 10.93/0.02 P | Ordinary four-ring onset with a clean approaching fit after an axis-range interruption. |
| `2.jsonl:81` | 3060–3061 | 2 | 96.80; 96.80–96.80 | 1/0/1/0 | 5/5; 4; 1.997–2.856 | 155/127.5; 3/1 | -0.02/0.01 F | Nearly sensor-stationary elevated target; earlier floating demotions, ordinary onset. |
| `2.jsonl:570` | 4152–4155 | 4 | 31.53; 24.96–31.53 | 1/1/2/0 | 3/3; n/a; 0.045–0.053 | 181/92.5; 3/1 | 11.53/1.28 F | Warning edge, low, edge-demoted, low, low matched sequence; exactly 3/5 gauge votes. |
| `3.jsonl:266` | 5065–5066 | 2 | 136.07; 134.05–136.07 | 2/0/0/0 | 6/6; 5; 0.633–2.648 | 189/105; 3/1 | 20.33/0.05 P | Five-ring compact vertical onset; earlier column/height demotions; coherent approach. |
| `4.jsonl:36` | 5699–5704 | 6 | 111.73; 104.42–111.73 | 2/0/2/2 | 11/14; 7; 0.497–1.937 | 120/120; 3/1 | 14.55/0.02 P | Seven-ring strict onset while mount remains pending; later zero-strict continuation. |
| `4.jsonl:56` | 5714 | 1 | 35.36; 35.36–35.36 | 0/1/0/0 | 4/4; n/a; 0.038–0.063 | 147/180; 3/1 | -6.21/0.43 F | Low-warning-warning-low-low sequence, exactly 3/5 gauge votes; receding fitted distance. |
| `4.jsonl:58` | 5714–5717 | 4 | 36.26; 31.95–36.26 | 0/3/1/0 | 5/5; n/a; 0.030–0.030 | 147/180; 3/1 | 13.28/0.12 P | Approaching low onset: five voxels, 3 cm along-X span, zero raw vertical extent. |
| `4.jsonl:209` | 5901–5904 | 4 | 28.82; 27.65–28.82 | 0/3/1/0 | 7/7; n/a; 0.049–0.109 | 120/107.5; 0/0 | 2.23/0.01 P | Low onset with rail_slabs=0 and rail_lock=0; five coherent approaching hits within the 40 m cap. |
| `4.jsonl:513` | 6859–6864 | 6 | 43.31; 36.89–43.31 | 2/0/1/3 | 7/59; 2; 0.129–1.786 | 151/155; 3/1 | <5 hits | Large outside-left cluster; 7/59 strict voxels; four matches with two intervening misses. |
| `5.jsonl:113` | 7338–7343, 7347–7351 | 11 | 98.38; 80.08–98.38 | 9/0/2/0 | 5/6; 3; 0.544–1.011 | 120/125; 3/1 | 14.45/0.77 F | Three-ring ordinary edge onset; source five-hit approach residual is 0.77 m. |
| `5.jsonl:330` | 7859–7866, 7868–7869 | 10 | 47.65; 40.10–47.65 | 6/0/4/0 | 10/62; 3; 0.168–1.621 | 119/115; 3/1 | <5 hits | Four matches with two misses; 10/62 strict voxels; strict subset is long and low. |
| `5.jsonl:358` | 7944–7953 | 10 | 103.20; 94.56–103.20 | 7/0/1/2 | 6/10; 6; 0.153–1.754 | 119/120; 3/1 | 14.50/0.32 P | Candidate onset is 7944, one frame later than source; six strict rings, coherent approach. |
| `6.jsonl:331` | 9263–9268 | 6 | 109.59; 104.49–109.59 | 4/0/1/1 | 20/20; 9; 0.278–2.227 | 147/105; 3/1 | <5 hits | 20/20 strict voxels, nine rings, 1.95 m vertical body; candidate retains only the first run. |
| `6.jsonl:336` | 9284–9286 | 3 | 123.38; 120.83–123.38 | 2/0/1/0 | 9/9; 3; 0.301–0.871 | 135/125; 3/1 | 9.25/0.42 P | Compact transverse three-ring face; onset follows axis/height demotions and fits approach. |
| `6.jsonl:518` | 9786–9787, 9800–9809 | 12 | 124.52; 114.93–124.52 | 12/0/0/0 | 4/4; 2; 1.146–1.386 | 131/125; 3/1 | 0.82/0.32 F | Four-voxel two-ring elevated face; two STOP runs with prior floating and reference demotions. |
| `7.jsonl:204` | 10484–10487 | 4 | 50.93; 45.91–50.93 | 0/2/2/0 | 3/3; n/a; 0.033–0.116 | 115/115; 3/0.95 | 5.52/1.78 F | Six consecutive low hits; fifth span is 0.499922 s, sixth crosses confirmation time. |
| `7.jsonl:215` | 10506–10507 | 2 | 46.39; 44.42–46.39 | 0/1/1/0 | 4/4; n/a; 0.040–0.120 | 60/120; 3/1 | 14.03/0.46 P | Six hits in ten frames; one prior ordinary hit; coherent approach despite gaps. |
| `7.jsonl:264` | 10644–10646, 10648–10649 | 5 | 98.27; 95.66–98.27 | 3/0/2/0 | 7/8; 1; 0.199–0.409 | 225/122.5; 3/1 | 14.48/0.78 F | Ordinary single-strict-ring onset; raw channels include outside support; long low cluster. |
<!-- END GENERATED INVENTORY -->

## What most strongly follows for accuracy and retained range

**Investigate correspondence of local intruding support and its height/axis reference
across frames, while preserving localized bodies inside connected background.** The
inventory does not establish a safe blanket rejection threshold or a measured additional
event reduction. It separates three materially different problems:

1. **Mixed low/ordinary support and model-relative footprints.** The overlapping group
   `1:286/292/293/310/306` at frames 2668–2678 is the strongest compact investigation
   window. `:293` recedes from 33.12 to 43.23 m before STOP; `:310` changes from four
   left-side low hits to an ordinary cluster with 21 strict voxels; `:286` switches
   paths with gaps. `2:570` and `4:56` reach exactly three gauge votes in five matched
   hits through warning/low transitions. Record actual current-frame support correspondence,
   stage provenance, local reference movement and the votes they earn before assigning
   confirmation to one persistent intrusion. A same-stage-only vote or compulsory
   approaching fit would also suppress genuine low objects with flickering support.
   `4:58`, `4:209` and `7:215` already have coherent approaching low support, so approach
   is not a general false-alarm separator.
2. **Geometry must describe the intruding subset, not the entire connected component.**
   `6:331` begins with 20/20 strict voxels, nine rings and a 1.95 m vertical body.
   `1:298` is 6.80 m long overall but has only 0.09 m strict along-X extent; `1:74`
   similarly has 5.29 m full length versus 0.19 m strict extent. These known false
   events resemble valid compact positives. In contrast, `5:330` has a genuinely
   long, low strict strip (5.39 × 0.40 × 0.23 m), with much of its full height outside
   the gauge. The earlier [far-structure study](EXPERIMENT_FAR_STRUCTURE.md) measures
   these distinctions and shows that two farther ground positions can make `:331`
   look like a long structure under range-normalized connectivity.
   The [range/shape investigation](EXPERIMENT_RANGE_SHAPE_SUPPORT.md) independently
   found resolved synthetic person support lost after background connection at
   **114.8–77.7 m**, and cable support at **98.4 m**. A useful follow-up therefore
   needs local-body decomposition plus evidence of local protrusion or surface
   continuation using the effective current-frame reference/union mask. Whole-context
   size, PCA direction or verticality cannot safely veto the intrusion. Compactness
   alone cannot validate it either. The target-only positive rescue is oracle evidence,
   not an implemented selector or demonstrated detection gain.
3. **Continuation is separate from onset.** The 32 missed and 9 off-gauge retained
   track-frames are continuation diagnostics. All 27 first onsets have fresh ordinary
   or low support. Removing every such continuation row cannot erase any of those
   event identities; overlapping tracks also prevent translating 41 track-frames
   directly into 41 node frames. Holds preserve occluded/thin real objects, so deleting
   them is not a supported route to the event-count goal.

Two tempting directions are already contradicted by measured evidence:

* [Low local support](EXPERIMENT_LOW_LOCAL_SUPPORT.md) rejected 109 ride candidate
  entries across 27 frames but left **130/32/31** STOP frames/events/episodes unchanged;
  none of its 19 fresh low-supported STOP track-frames was removed. Its required
  four-quadrant evidence is not the trace's weaker same-band statistic. Runtime p95
  rose from 116.8 to 606.7 ms. Negative same-band excess in `1:292`/`:306` warrants
  reference diagnosis, not re-enabling or loosening that rejected filter.
* More rings, more persistence, mandatory approach, a hard trusted-range cap, global
  height/width thresholds or infrastructure vetoes would remove valid thin/distant
  support as well. `7:264` is an ordinary single-strict-ring event; raw outside
  channels do not turn it into multi-ring strict evidence. `6:518` is a four-voxel
  elevated face that shares the small hanging-object preservation mechanism.

Each JSON event includes its observed mechanism, investigation direction and a concrete
valid-obstacle suppression risk. None claims the fitted surface is a surveyed rail,
column or person. A later candidate needs paired accuracy/range evidence on these
negatives and resolved person/cable, thin cable/plank, small rail/edge and occlusion
positives. This inventory supplies the cases and provenance, not that future result.

## Reproduction and checks

From the repository root, in PowerShell (output parents already exist):

```powershell
$py = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe'
& $py -m scripts.analyze_residual_events --measurement 'D:/Datasets/ReSense/cross_ring_2026-09-28_measurement' --out 'docs/evidence/results/residual_events_2026-09-28.json' --markdown 'docs/RESIDUAL_EVENTS_2026-09-28.md'
& $py -m pytest -q tests/test_residual_events.py
ruff check scripts/analyze_residual_events.py tests/test_residual_events.py
```

`--table` prints the same generated inventory; `--inspect` prints compact event
diagnostics; `--near-history` prints the last ten source rows for near events.
Only the marked table is regenerated in this authored Markdown report. JSON output
is deterministic for identical input bytes and analyzer version.

Focused tests cover overlap versus node/episode counting, chunk-local ID resets,
invalid capture rejection, same-ID/wrong-frame/model/geometry joins, stale evidence,
exact snapshot masks/counts, approach fits, latency-only default parity, and the
recorded 27-event inventory including delayed onset and lost reacquisition. The
recorded verification is **19 passed (0.25 s); Ruff passed**. The analyzer imports
no detector/tracker and runs no replay. The coordinator subsequently reproduced this
inventory and verified the combined tree: **228 passed, 1 deselected, 6 subtests passed**;
repository-wide Ruff passed. The unfinished `evidence_coherence` candidate was rejected
and removed, resolving the earlier shared-tree integration issue. See
[the temporal investigation](EXPERIMENT_EVIDENCE_COHERENCE.md) and
[the coordinator closeout](RESIDUAL_REVIEW_2026-09-28.md).

Scope: the available saved ride captures only. Set O, synthetic positives and missing
short organizer bags are discussed through the linked investigations; they are not
replayed or newly scored here. No production accuracy, range, latency or acceptance
gain follows from this diagnostic alone.
