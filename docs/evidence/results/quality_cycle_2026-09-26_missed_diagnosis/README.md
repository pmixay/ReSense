# Frozen detector: missed-object tracing

No detector behavior changed in this diagnosis. The observer follows explicit organizer
return identities through the production pipeline, recording point survival, cluster return
conditions and track histories. It does not approximate the filters with a separate classifier.

- [Summary and all 54 overclaim frames](summary.json).
- [Set O trace](seto_trace.json.gz): all 1,510 cache outputs match the frozen replay exactly
  for detections, warnings, range, track/mount geometry and candidate/corridor counts.
  [Run log](seto_trace.txt).
- [Novel-placement trace](novel_trace.json.gz): every decision matches the previous 72-case
  run, including all 544 target matches. [Run log](novel_trace.txt).
- Observer: `scripts/trace_detector_stages.py`; runner: `scripts/trace_object_failures.py`.
  Five focused tests cover parity, exact source attribution, duplicate multiplicity, missing
  returns and recording actual rejection conditions. Instrumented timings are not scored.

## Findings

1. **Sparse returns disappear before tracking.** Set O frame 303 has two cube returns at
   110.12 m inside the current nominal polygon. Both leave the strict core after its confidence
   margin. They join a 22.99 m background cluster; its oversized strict part is rejected.
   There is no candidate or track to cap the reported 133.6 m range, and the decision is GO.
2. **Clipping can destroy measured shape.** At frame 616 the top box has 42 source returns
   spanning 1.77 m in Z. The corridor keeps a five-point row with zero Z span and four strict
   voxels. Production preserves it as a thin continuation candidate, but it starts no track
   and contributes no range cap. At frame 688 the plank similarly has eight flat returns,
   six strict voxels, and no report. These are observed pipeline decisions, not proposed fixes.
3. **Geometry dominates the edge examples.** Of 83 visible small-edge frames, 67 have no point
   inside the current fitted nominal polygon and four more lose all strict points after the
   margin. Ten retain a floating-demoted cluster; two STOP. The large-edge object has 116/125
   frames outside that fitted nominal polygon, one margin exclusion, two unconfirmed gauge
   frames and six STOPs. This does not settle the physical rail/sensor-reference question.
4. **All 54 cache range overclaims are accounted for:** 46 GO, six CAUTION, two STOP. The cube
   contributes 30, rail cube four, small edge four, large edge two, top box seven, plank seven.
   The detailed rows retain overlapping later failures rather than implying one universal cause.

## Novel placement: interpret the model comparison carefully

| Source shape | Visible frames | Any point inside current fitted nominal polygon | Matched |
|---|---:|---:|---:|
| Small center |702|562|230|
| Small on rail |646|455|211|
| Large above |612|216|58|
| Thin hanging |498|194|45|

These membership counts use the evaluated detector's own fitted geometry. They are **not**
surveyed envelope labels or proof that the transplant lies outside the true train envelope.
Placement height, target-background geometry and model error can all contribute. The original
72 cases and denominators remain unchanged; none is excluded or re-scored here.

Raw organizer source returns are matched to the cache using XYZ, intensity and ring after the
same quantization and range filtering as production. The summary records changes at the range
boundary and any indistinguishable duplicate copies. No approximate spatial matching supplies
target identities. Source hashes and executed observer/runner hashes are inside each trace.

## Reproduce

From this checkout, use the project venv and native library built from the sealed source:

```bash
python scripts/trace_object_failures.py seto --bag DATA/cloud_with_fake_obj --cache DATA/cache \
  --baseline FROZEN_WORK/cloud_with_fake_obj.jsonl --out seto_trace.json.gz
python scripts/trace_object_failures.py novel \
  --plan docs/evidence/results/p4_novel_plan_2026-09-26.json \
  --source DATA/organizer_objects --cache DATA/cache \
  --baseline docs/evidence/results/p4_novel_results_2026-09-26.json --out novel_trace.json.gz
```

The novel plan rejects changed detector/evaluator inputs. After a candidate changes detector
code, reproduce this diagnostic on the sealed baseline checkout.
