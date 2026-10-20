# T4: F1a exposure on set O and the ride (20.10)

> **For:** P3 (sizing the fix of review B1) and Pavel · **From:** P4 data session of 20.10 (handoff T4,
> [`../p4_handoff_2026-10-20/HANDOFF.md`](../p4_handoff_2026-10-20/HANDOFF.md)) · **Detector code:** not touched ·
> **Tree:** `main` `8c2bf51`, committed defaults (F1a on) · environment as in
> [`../k2_v5c_2026-10-20/README.md`](../k2_v5c_2026-10-20/README.md) §6.

## Answer

Review B1: a plain low cluster's top is capped below the envelope floor (0.12 m), so where the frame's rail line reads
≥ 0.11 m above the model's plane, F1a makes every plain low cluster weak. Over set O (1,510 frames) and the whole ride
(11,271 frames), F1a makes **163** low clusters weak; **114** of them have a rail reference ≥ 0.11 m, **all on the ride,
none on set O** (no F1a-weak cluster at all on set O). They form 101 episodes (consecutive frames, distance within 3 m),
91 of them a single frame, 7 of two and 3 of three frames, at 3.0–58.1 m; each is at most 0.10 m tall with its top ≤ 0.12 m.

| where | clusters | what the pictures show |
|---|---|---|
| on a rail, \|lateral\| 0.6–1.0 m | 108 | the rail head itself: the cluster's returns lie on the rail line in the top view and at rail-head height on the rail in the cross-section (e.g. [`ep06`](out/png/ep06_new_data_52_0017.png) 31.4 m, [`ep38`](out/png/ep38_new_data_55_0016.png) 3.0 m, the rail profile) |
| track centre, \|lateral\| < 0.4 m | 5 | one scan line across the centre at or just below rail-head level, 0.35–0.45 m above the bed, each in a single frame ([`ep20`](out/png/ep20_new_data_52_0019.png) 41.2 m, [`ep50`](out/png/ep50_new_data_81_0021.png) 42.3 m, [`ep52`](out/png/ep52_new_data_81_0021.png) 48.2 m, 1.1 m across the whole gauge, [`ep87`](out/png/ep87_new_data_111_0050.png) 40.5 m); one beside a structure ([`ep90`](out/png/ep90_new_data_115_0013.png) 17.7 m) |
| other | 1 | [`ep94`](out/png/ep94_new_data_205_0022.png) 39.2 m, lateral 0.56 m, next to the right rail |

So on the recordings F1a's weak clusters are rail fragments and track-level surfaces; **no real object above the rails
is among them**, as far as the pictures show (the ride has no ground truth; the five centre ones are consistent with
centre-of-track equipment or a crossing surface flush with the rails, and do not repeat in the next frame as a static
object would). The exposure B1 describes, a genuine low object on a frame whose rail line reads high, does not occur
here because no genuine low object is on the ride or in set O at those frames; the condition itself (reference
≥ 0.11 m) is common on the ride: 114 of 163, 70 % of F1a's weak clusters.

P3's fix (top over the cluster's own footprint including the returns above the floor) is not committed yet; its gate +
Falcon measurement is still to run.

## How it was checked

| check | method | result |
|---|---|---|
| the trace does not change the run | [`scripts/t4_trace.py`](scripts/t4_trace.py) runs the gate's own replay (`eval_real.run_piece`, the gate's pieces, stamps and config) with `Detector._rail_reference` wrapped read-only; its per-frame rows against the plain gate run of the same commit (`cmp_frames.py`) | 12,781 rows (set O and 8 ride pieces), **0 differ**; 467 differ only in the latency health level (the traced run is slower) ([`out/identity_traced_vs_gate.txt`](out/identity_traced_vs_gate.txt)) |
| the recorded clusters are F1a's | the wrapper records exactly the clusters `_rail_reference` adds to `_low_height` in that frame, and recomputes the reference with `lowobj.local_rail_reference` on the same returns as the detector (`low_free_mask` when `local_rail_exclude_low`) | 163 clusters, every one with a reference (none `None`); every top below reference + 0.01 m |
| labels | every one of the 101 episodes rendered ([`scripts/t4_summary.py`](scripts/t4_summary.py): top view coloured by height, cross-section with the reference); class from lateral, checked by eye on all centre / other cases and on rail cases at 3, 26–41 and 58 m | as tabulated |

Not checked: what the five centre lines physically are (no ground truth on the ride); the fix itself.

## Files and reproduce

`out/f1a_weak_clusters.jsonl.xz` (all 163: frame stem, distance, lateral, top, reference, size, voxels, centroid),
`out/summary.txt` (the episode table), `out/png/` (a selection; every episode is drawn by the script).

```
export RESENSE_REPO=$PWD PYTHONPATH=$PWD OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python docs/evidence/f1a_exposure_2026-10-20/scripts/t4_trace.py <cache> <out> --jobs 2
python docs/evidence/integration_2026-10-19/scripts/cmp_frames.py <gate work of the same commit> <out>   # identity
python docs/evidence/f1a_exposure_2026-10-20/scripts/t4_summary.py <out> <out>/png
```
