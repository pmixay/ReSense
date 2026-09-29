# 28 September candidate screen — available recordings only

**Scope:** local diagnostic of the existing `new_data` (11,271 frames, no obstacles)
and `cloud_with_fake_obj` (1,510 frames). Not the six-bag Linux quality screen or a
release/acceptance decision. Source detector: `df24c18`; starting experimental tree:
`3ba4521`. The audited source and candidate-default captures were semantically identical
on all 12,781 frames, ignoring only clock-driven latency health text/levels (faults,
decision levels, monitored/clear distances, model state and detection details are checked).

## Paired Windows replay

Set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to `1`. Use the same
Python/NumPy backend, four workers, original cache receive stamps, eight independent ride
chunks and a single set O chunk. Run from the repository root:

```powershell
$env:OMP_NUM_THREADS='1'; $env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
& 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv\Scripts\python.exe' -m scripts.eval_real --cache 'D:\Datasets\ReSense' --out 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\candidate_defaults_v2' --bags 'new_data,cloud_with_fake_obj' --jobs 4 --chunks 8
& 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv\Scripts\python.exe' -m scripts.eval_real --cache 'D:\Datasets\ReSense' --out 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\fresh_stop_v1' --bags 'new_data,cloud_with_fake_obj' --jobs 4 --chunks 8 --set 'tracking.fresh_stop_evidence=true'
& 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv\Scripts\python.exe' -m scripts.eval_real --cache 'D:\Datasets\ReSense' --out 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\local_support_v1' --bags 'new_data,cloud_with_fake_obj' --jobs 4 --chunks 8 --set 'lowobj.local_support_enabled=true'
```

Do not overwrite the named outputs without recording code/config/cache hashes: the local
reports refer to these exact captures. The independent `source/` output was recorded from
`df24c18`, with its command and provenance in `manifest.json`. The eight pieces model
separate scene resets; do not join track IDs or STOP episodes across boundaries.

Verify captures with `scripts/analyze_quality_candidates.py`, which checks nine required
pieces, frame identity/order/stamps against SHA-256-audited cache manifests, per-piece
summary consistency and finite metrics; computes STOP frames, track events and episodes,
per-object first/sustained STOP and missed intervals, overclaim, monitored/clear range,
and latency. Example (repeat for each independently enabled candidate):

```powershell
& 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv\Scripts\python.exe' scripts/analyze_quality_candidates.py --reference 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\source' --candidate 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\candidate_defaults_v2' --audit-dir 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement' --labels 'labels/cloud_with_fake_obj.json' --out 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\quality_candidate_defaults_v2.json' --require-parity
& 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv\Scripts\python.exe' scripts/analyze_quality_candidates.py --reference 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\base' --candidate 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\fresh_stop_v1' --audit-dir 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement' --labels 'labels/cloud_with_fake_obj.json' --out 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\quality_fresh_stop_v1.json'
```

Only the defaults-versus-source comparison uses `--require-parity`; a candidate should
change some semantic frames. A zero process exit **does not mean acceptance**: inspect
`input_validation_passed`, `semantic_difference_frames`, `node_decision_difference_frames`,
per-object and per-piece metrics. The report validates manifest hashes, not fresh raw cache
byte hashes; consult `audit.json` for the prior cache/DB3 audit.

## Screen result and next gate

| Variant | Ride false STOP frames/events/episodes | Set O STOP frames/events | Ride total p95 (Windows NumPy) | Decision |
|---|---:|---:|---:|---|
| Current defaults | 130 / 32 / 31 | 447 / 9 | 116.8 ms | Matches source decisions and model outputs. |
| Low local support only | 130 / 32 / 31 | 447 / 9 | 606.7 ms | Rejected: no STOP benefit, large cost. |
| Fresh STOP onset only | 117 / 27 / 26 | 447 / 9 | 104.8 ms | Opt-in candidate; positive holdout needed. |

These measurements neither reach the proposed ≤10 ride false-event target nor support a
combined-profile claim. No safe far-structure rule survived the geometry counterexamples
documented in [EXPERIMENT_FAR_STRUCTURE.md](EXPERIMENT_FAR_STRUCTURE.md). Set O objects
retain per-object first/sustained STOP under the tracking candidate; do not replace that
check with aggregate 447/9 parity. A new positive obstacle appearing for one strict-gauge
hit or flickering across the boundary could be delayed by the onset candidate.

As a limited independent positive stress, a separate 102-frame split cache was decoded
from real `new_data_46.db3` and `new_data_47.db3` under
`C:\Users\alikh\AppData\Local\Temp\opencode\fresh-stop-positive-stress\split_cache`.
Paired `scripts.far_range_eval` runs (80 consecutive frames per file, seed 0 at centre,
seed 19 at the edge, start 150 m, `legacy` placement) used `configs/default.yaml` and
`configs/experimental_fresh_stop_evidence.yaml`. Both configurations produced exactly
the same per-object first/sustained distances and per-bin hits on the measured cases:
two centre persons, two cables, two edge persons, two centre planks, two edge 0.3 m
boxes and two edge rail objects. Centre planks were missed 2/2 by **both**; small
edge objects were only detected 1/2, near 13–15 m. Synthetic objects on moving real
backgrounds are useful counterexamples and no-regression probes, not surveyed holdouts.
The individual paired JSON results and their hashes of config, speed reference and
receive-stamp selection remain in the temporary measurement directory.

Before any default change, obtain and run the six missing short organizer recordings and
the full Linux `quality_screen.py` gate on source-matched defaults and each independent
candidate; inspect its `gate.json`, `acceptance.json`, `history.json` and per-stage outputs,
including held-out/history stress, first/sustained distances and per-bin misses for every
obstacle (person, edge, small and far), five empty-bag event/episode counts, GO/monitoring
overclaims and native/node latency. Do not grant missing-data waivers or infer ring
independence from set O's fabricated ring 0. New route/scene-labelled positives are needed
for a genuine independent holdout. A large false-alarm gain is acceptable only if no
gated recall, STOP distance or monitoring metric regresses.
