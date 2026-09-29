# Oracle source-motion accumulation: first conditional study

**No production change or measured STOP gain.** All 44 registered frames (295–338) were
processed with one worker. This uses oracle source-relative motion and rounded historical
geometry, not real odometry or a current sequential detector replay. The physical union
in this first study contains **known source points only**. It does not establish performance
when translated raw background returns accompany them.

Protocol committed before execution: `34de51a`,
[`ORACLE_ACCUMULATION_PROTOCOL_2026-09-28.md`](../../../ORACLE_ACCUMULATION_PROTOCOL_2026-09-28.md).
Raw source identities come from organizer message delimiters and exact five-field
quantized cache matching; all organizer groups are removed in paired background controls.
Source motion comes exclusively from original source X minima and recorded timestamps.
All input message/cache/code hashes and historical geometry are retained in `results.json.gz`.

## Results with the bounded physical neighbor graph

These are surviving **gauge candidates before tracking**, not STOP frames. Counts above
70 m and above 100 m use the current source's original nearest X. Every denominator is
the same preserved sequence (34 frames above 70 m, 15 above 100 m).

| Window | Source-only physical union: >70 / >100 m | Production buffer: >70 / >100 m | Pure-source production candidates >70 m | Paired-background gauge candidates |
|---:|---:|---:|---:|---:|
| 1 | 1 / 0 | 1 / 0 | 1 | 0 |
| 2 | 14 / 0 | 9 / 0 | 6 | 0 |
| 3 | 17 / 5 | 12 / 0 | 6 | 0 |
| 4 | 11 / 6 | 12 / 0 | 6 | 0 |
| 5 | 14 / 3 | 9 / 0 | 4 | 1 |

“Pure source” means no background returns belong to that surviving cluster. Merely touching
source points is weaker evidence: some mixed candidates pass shape/count tests partly
because background points are present. All per-cluster contamination and contributing
source-frame identities are in the output and summary.

With the original graph the production buffer has 1/0/1/1 source-candidate frames above
70 m for windows 2/3/4/5. The source-only results are identical between graph variants.
Thus long background connections remain a major loss after accumulation.

## What limits the result

- Three physically shifted source frames produce candidates at 113.1, 110.1, 108.6,
  107.1 and 101.0 m under unchanged count/shape rules. At frame 303 this is five raw
  source points, three occupied voxels and three strict voxels across three source frames.
- The production buffer has **zero strict source voxels** at frames 301, 303 and 309,
  despite source-only physical alignment having three. Historical strict flags and
  track-coordinate re-embedding are different from current physical membership; this
  experiment does not isolate those two causes. A paired full-return translation study
  with held/recomputed flags is the next diagnostic.
- Larger windows do not reliably help. For physical source-only windows 3/4/5, the
  scaled strict-count bar is met in 34/36/36 frames, but only 26/16/23 frames produce
  source gauge candidates after shape and other tests. For production bounded windows
  3/4/5, those figures are 21/20/19 versus 21/19/14. Mixed background support explains
  why these are not simple nested counts. No count threshold was reduced.
- At frame 310, five-frame bounded accumulation creates a background-only gauge
  candidate at 92.3 m (8 voxels, 3 strict voxels; size 3.64 × 0.80 × 1.47 m), after
  fallback to current-frame points. All one-frame controls had zero gauge candidates.
  This blocks a clean-improvement claim for that variant even before tracker testing.
- Maximum absolute oracle X alignment residual across the five-frame windows is
  0.593 m. The output preserves residuals, source-frame support and physical XYZ spans.
  This scalar X motion is neither perfect registration nor surveyed vehicle motion.

## Reproduce

```bash
python scripts/diagnose_oracle_accumulation.py \
  --db /data/fake-positive/cloud_with_fake_obj/cloud_with_fake_obj_0.db3 \
  --cache /cycle/cache/cloud_with_fake_obj \
  --out out/oracle_accumulation/results.json.gz
python scripts/summarize_oracle_accumulation.py out/oracle_accumulation/results.json.gz \
  --out out/oracle_accumulation/summary.json
```

Four new tests check the fixed motion fit and bounded DBSCAN graph; all pass. The earlier
four range-observer tests also pass. Ruff passes for both observers and tests. No broad
detector replay or false-STOP validation was performed.
