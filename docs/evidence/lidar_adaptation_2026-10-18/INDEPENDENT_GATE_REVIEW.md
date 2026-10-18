# Independent full-gate review — 18 October 2026

**PASS for the complete default regression gate on corrected core `7b7b02c9b535d2b03d053df1b309301b619269ad`. Final integration acceptance and a replacement seal still require the completed corrected-core X3 run.** The earlier `f5ff15f` X3 is retained evidence, not a substitute.

The author-independent audit reads the actual complete captures; it does not rerun a detector. [Reproduction script](review_gate_boundaries.py) and [machine-readable results](independent_gate_boundaries.json) record source, input and archive hashes, every per-piece STOP interval and every Set F hit interval. The separate [serialized-evidence review](gate_independent_review.json) reconstructs gate aggregates from raw rows and verifies source-frame/stamp completeness. An independently executed copy of that validator produced identical output.

## What passed

- All **38 frozen files** match the immutable measured checkout, Git blobs at `7b7b02c`, live source and runtime identity receipt. Source digest is `4d57add1f5e255d5aa4a645a2a390eb47204e64893a2b45d1ec6a2a6e1073993`. Candidate and fresh `9b92df5` control use the identical native library (`511f7766639f0ddab471a77263f7a343de19d0a8217dd7cd3a11635c8a7db2c8`) and unchanged six-file gate/evaluation harness.
- The measured effective configuration equals the canonical default and ROS configuration: orientation startup replay **4**, experimental rail-axis extension **off**. No parameter overrides, `--allow`, missing datasets or failed gated metrics. Original receive stamps and all eight ride pieces are retained.
- The historical gate independently reconstructs **208 identical metrics and 16 informational latency changes**, with no gated regression. The fresh same-runtime control comparison has **224 metrics: 209 identical, 5 improved latency and 10 worsened latency**, no failure; every non-latency metric is identical. No timing conclusion is drawn from concurrent, paused runs.
- All **15,269 ordinary rows** retain identical v1 decisions, detections, warnings, clear distance and monitored range. Every raw obstacle flag agrees with confirmed detection presence. All **805 STOP frames** and **51 per-piece STOP episodes** retain exact boundaries: zero additions, losses, delays or shortening. The only non-timing serialized additions are `health.orientation_confirmed` and `mount.orientation_confirmed`, both true in these normally oriented captures.
- All **30 Set F sequences / 3,060 scoring rows** retain exactly identical serialized placements, hit/false-positive assignments and hit spans (**1,064 hit rows**). Aggregate summaries are identical except measured `wall_s` (1084.0 versus 1085.6). Configuration identity changes as expected for the new startup parameter.
- All **39 durable archive members** were independently decompressed and checked against their recorded lengths and SHA256 values. Archive SHA256: `697a3636f1148a628db466c8103bd15640bc15c8ec5da73987a12de1093ccc08`.

| Capture | Frames | STOP frames, both runs | STOP episodes, both runs |
|---|---:|---:|---:|
| Real obstacle (`doubleT_obstacle`) | 201 | 193 | 1 |
| Set O | 1,510 | 447 | 8 |
| Five original empty recordings | 2,287 | 39 | 12 |
| Complete ride, eight reset pieces | 11,271 | 126 | 30 |

The real-obstacle first STOP remains **frame 8**. The receipt retains first/last positions and all interval boundaries for every separate capture/piece; ride alarms are not merged across detector resets.

## Limits and remaining requirements

This verifies serialized outputs rather than full-precision internal state. Set F omits full detection payloads, so independent reconstruction of its hit/false-positive association is impossible from these artifacts; stored assignments, placement and aggregate arithmetic were verified. Existing empty-recording alarms remain unchanged, not resolved.

Ordinary inputs already confirm orientation, so this gate cannot independently establish the transformed-startup behavior; the separately reviewed nine-case orientation battery and bounded-memory tests cover that path. The gate also does not exercise ROS freshness, the accepted opt-in C2 range projection, or graphics; their separately recorded integration checks retain their own image/source scope. This review does not accept dust suppression or the rejected N6 extension, and is not a release, deployment or physical-safety claim.

Wait for the actual **corrected `7b7b02c` 40-case X3 capture**, independent metric and STOP-boundary review, then review and verify the new seal. No acceptance threshold was changed here.

## Reproduce

After retaining/extracting the raw archive and restoring the named source checkouts:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/resense/.venv/bin/python \
  docs/evidence/lidar_adaptation_2026-10-18/review_gate_boundaries.py \
  --candidate-source /home/resense/data/final_lidar_7b7b02c \
  --reference-source /home/resense/data/control_lidar_9b92df5 \
  --candidate-work /home/resense/data/final_gate_work_7b7b02c \
  --reference-work docs/evidence/lidar_adaptation_2026-10-18/control_9b_native/work \
  --out /tmp/independent_gate_boundaries.json
```

The script checks the current frozen source against the measured commit; it will intentionally reject a later modified detector. It excludes only explicitly identified timing from Set F summaries and relies on the separately reviewed timing normalization for whole ordinary serialized-field comparison.
