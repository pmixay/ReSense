# Independent H4 correctness review — PASS

**PASS for this registered scope: no supported remaining medium-or-higher
correctness finding.** The reviewer authored no production implementation.
New files are confined to this evidence folder. The separate reviewer's
clustering-positive/negative verdict is independent of this result.

## Source and execution provenance

- Registered target: `7cc640fb39698b1fe45bc6ab069eab68ad4ac6ae`.
- H3 measured core: `f8c088dc4f3243fbd15a3aae9be0459e8a0aa941`.
- Sealed control: `707ea9cda051369326fb9407c42488c1033dad76`.
- Shipping node reviewed at `d4850c5`, present unchanged in target.
- Published node baseline: `3fdc87957f5d09ff32573eabe6637924b91ea376`.
- Immutable image:
  `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`.
- Python 3.10.12, NumPy 1.26.4, installed Open3D 0.19.0; native enabled.
  Native binary SHA-256:
  `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
- Actual code imports: `/work/target/resense/…` and `/work/control/resense/…`;
  explicit per-process checkout `PYTHONPATH`, numerical threads 1.
  `run-001/imports.txt` retains interpreter/compiler/module paths and hashes.
- Adopted original container `resense-h4-correctness-20261016-01`, ID
  `bdb526cc93b7311e003edeeff9171291422d0cf154763b13e0343125e6a07714`.
  It completed successfully before continuation. All follow-ups reused its
  original Linux volume/checkouts/native builds. No duplicate setup or unit run.
- All **36 files per checkout** match H3 hashes, exact Git blobs and LF bytes
  before/after units and after each probe batch: **five paired inventories**.
  An additional comparison checks target's 36 blobs directly against H3's commit.
  The current integration HEAD's reviewed core/runtime has no diff from target.

Exact launch argv, full Docker inspect data, exit/OOM state and container logs
are retained. All containers/volumes remain available. No timing-speed claim.

## New independent measurements

| Check | Result |
|---|---|
| 22 explicit registered unit files, actual Open3D/native | **572 passed**, 0 failures, 0 skips |
| Signed/asymmetric/curved boundary tables | **58 passed** |
| Health min-cap matrix, unchanged default monitor | **3,024 passed**, including None/sentinel/negative/zero caps; 224 clear reductions |
| Spare-history truth table | **128 passed** |
| Actual `Track` column-held/current/lost clear-cap compatibility | **1,024 passed** |
| Default 10-hit history recovery | **13-hit sequence passed**, early column hold and eventual gauge release |
| Cached azimuth windows vs full exact scan, float32/float64 | **160 exact matches**, cache identity reused |
| Actual detector frame-coordinate wiring/lifecycle | **2 distinct frames**, nonfinite filtering and reset checked |
| Smoothed/rate-limited final-axis checks | **4 passed**, both signs, 1/3 periods; refused-fit bins and missing walls checked |
| Independent strict v1/node health/flag/freshness/latch matrix | **990 passed**; 683 STOP, 277 FAULT, 22 CAUTION, 8 GO |
| Published defaults and queue/clock/continuity ASTs | **39 defaults / 16 methods preserved**; three additive v1 parameters |
| Matched synthetic detector comparison | **96 frames × 3 executions**, 12 variants, **480 exact/min checks**, no failures |

Synthetic variants are straight, R900 constant curve, and a cubic transition
starting at 30 m, both turn signs, with unequal wall offsets and reaches,
with/without a near box. Target axis-on/off and sealed control use identical
clouds and stamps. Only the other newly added mechanisms are disabled for this
isolated comparison; those switches and the exact geometry are in the script.

All preexisting non-timing result values, candidate/detection descriptors,
processed-cloud hashes and corridor-membership hashes match exactly. The axis
cap produces **36 monitored reductions / 18 clear reductions**; the **24 STOP
frames** are identical in all three executions. Near boxes confirm in every
variant and remain at **21.0 m clear**. On the final transition frame in both
directions, monitored range is **157.9 → 102.0 m**, and analytic centerline error
at the cap-bin center is **0.914–0.965 m**. Settled straight/constant curves have
no cap. Constant curves have one conservative startup cap per variant while
the estimated axis converges; no geometry or decision changes result.

Primary results: `run-003/{boundaries,health,tracking}.json`,
`run-002/{cache,final_axis,node,ast}.json`, and
`run-004/scene_comparison.json`. `RESULTS.json` combines counts, identities and
per-variant measurements without replacing the underlying results.

## Retained H3 evidence independently authenticated and recounted

Authenticated **83 packaged hashes**, **152 relevant external hashes** and
**75 exact-copy / CRLF-normalization / lossless JSONL mappings**. The external
result-evidence root was mounted read-only; the point-cloud cache was not mounted.
No held-out G3 cases or protocol were read or executed.

Independent raw/serialized recount reproduces:

- **18,329 aligned frames**, including 3,060 retained Set F result rows.
- **2,422 finite drift annotations**, **2,131 monitored reductions**,
  **1,834 clear reductions**, no increases.
- **109,974 exact cap-equation checks**: three fields in both raw and serialized
  captures (H3's 54,987 figure counts one representation).
- **2,432,861 common raw numbers** compared; exactly **5,799 unequal**, all range
  fields. **25,706 candidates**, no `cut=true`, exactly six `spared=true`.
- Exact obstacle/warning/nearest/detection/geometry/corridor identity, apart from
  the explicitly traced candidate promotion below. Timing normalization is the
  registered H3 normalization; no other numeric tolerance is introduced.

### Unreported candidate promotion: explained, not a remaining finding

`new_data_1.jsonl`, row 1354, `new_data_54_0009`, candidate 8, **73.55999755859375 m**:
`reason: column → ""`, `zone: warning → gauge`. These are the only two preexisting
non-axis categorical changes. Every common descriptor matches the compact witness
exactly; the complete 49 raw point indices are retained in the independent report.

The prior spare history `[false,false,true,false]` satisfies the two-spare rule
(`resense/tracking.py:657–667`). Track 422 remains `column_held=true`, with
`column_hist=[true,false,true,false,false]`; its vote/rule/final zone stays warning
(`tracking.py:117–140`), and it remains unreported. The unchanged STOP flag is
false; clear remains 44.6 m. The actual-Track matrix independently exercises the
same property read by `clear_cap_distance` (`resense/detector.py:854–884`).
Thus candidate promotion does not imply a reported STOP promotion or range gain.

Full independent recount and witness: `run-004/evidence_audit.json`.
The retained 1,409-frame author replay is authenticated corroboration, not counted
as a newly performed independent replay.

## Implementation review conclusions

Reviewed complete `707ea9c..target` config/track/detector/health/tracking changes,
clustering interfaces, exact config-file synchronization and source-policy import
wiring. `reviewed-core-diff.txt` and `reviewed-runtime-diff.txt` retain the diffs.

- `track.py:490–545`: reference sign/near eligibility, inclusive offset/MAD
  limits, slope rejection, strict drift threshold, populated-bin continuity and
  structure-edge reference changes agree with the documented geometry. Sorted
  bins come from the extractor (`track.py:430–447`), including refused side fits.
- `track.py:1004–1022`: cap is measured against the final smoothed/rate-limited
  axis. No cap modifies the fitted axis or corridor. Missing current boundaries
  do not fabricate new drift evidence; a failed bed fit conservatively keeps its
  previous model through the existing prior-return path.
- `health.py:213–232`, `detector.py:307–329`: range min-cap wiring is additive,
  never increases clear/monitored, and leaves non-range/non-timing health fields
  and decision inputs unchanged. Hard input faults retain zero range.
- `detector.py:269–275,584–597`, `clustering.py:367–424`: coordinates are from
  this corrected/filtered frame; caches are call-local and reused within it.
  Historical candidate indices cannot index current rays (`clustering.py:1017`).
- `detector_node.py:976–1033,1175–1229`: strict raw validation precedes projection
  and latch release; malformed flags/health cannot release a STOP. Fresh valid
  non-STOP can release it. True obstacle precedence, zero invalid exposed ranges,
  shared v1 selection, and constructor/API v2 rejection all pass independently.
  The 16 published ASTs establish removal of S1 behavior from those shipping paths.
- `scripts/decision_policy_import.py:15–44`: source identity is checked before
  reuse; an unrelated installed policy/ROS overlay is not substituted. Rescorer
  metadata names/hashes the loaded policy. Existing registered suites passed.

**Findings requiring author fixes: none.** No implementation/version/seal changes
were made. The intentional pre-H5 version/seal state is outside this verdict.

## Preserved failed attempts and corrections

These are measurement-harness failures, not erased passing runs:

| Attempt | Preserved outcome / classification |
|---|---|
| Original `-01`, `run-001` | Completed units, exit 0; adopted intact |
| Launch `-02` | Exit 2 before Python; default entrypoint interpreted the script as shell |
| `-03`, `run-002` | Exit 1; unaffected probes and target scenes passed; initial serializer, fixture, control-import and witness-schema issues retained |
| `-04`, `run-003` | Exit 0; only three affected property checks repeated |
| `-05`, `run-004` | Exit 0; missing control, H3 schema projection and dependent comparison completed |

`CONTINUATION.md`, `FOLLOWUP_01.md`, `FOLLOWUP_02.md` register each correction
before execution. In particular the health fixture was corrected to exceed the
unchanged 20,000-point minimum, the history was extended beyond the unchanged
10-hit window, and the compact witness comparison excludes only its deliberately
omitted `points_idx` field while separately checking all 49 raw indices.
No failed geometry oracle was relaxed to turn a detector defect into a pass.
