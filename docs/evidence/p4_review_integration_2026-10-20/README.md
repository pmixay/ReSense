# P4 review of the 19.10 integration: the identity proof (20.10)

> **Purpose:** P4's independent check of the identity claims in
> [`integration_2026-10-19/README.md`](../integration_2026-10-19/README.md) (§2 and the `4cf8e27` table): that the
> merge changes nothing while the new switches are off, and that the final commit `4cf8e27` behaves as `11bb1ab`.
> **Owner:** P4 · **Status:** done for what the repository holds · **Detector code:** not touched (committed run
> files re-read; synthetic scenes run read-only on worktrees of `11bb1ab` and `4cf8e27`).

## Result in short

1. **Every claim that the committed files allow re-deriving holds.** The Falcon identities and the positive control
   were re-derived per frame with a comparator written here, the gate summaries agree leaf by leaf, the gate's config
   is the committed `default.yaml`, X3 has 0 failed comparisons, and `main` carries `4cf8e27`'s detector code.
2. **Three claims rest on outputs that are not committed** and can only be checked indirectly here: the per-frame gate
   identity of `4cf8e27` with `11bb1ab` (and of `b2c523a` with `aec88d2`), the Falcon identity of `4cf8e27` with
   `11bb1ab`, and the per-frame marked-bag identity of `4cf8e27` with 1.1.0. Their summaries agree, and the code
   between `11bb1ab` and `4cf8e27` gives identical output on 180 synthetic frames with K2 off. Not more.
3. **The health `ok`/`warn` counts that differ between gate runs are the latency warning**, not the detector: they
   follow the run's speed, and the decision does not read them.
4. **Open finding (X3):** set O's unmatched STOP episodes are +1 in 7 of the 10 `cloud_with_fake_obj` perturbations
   against `aec88d2` (within the tolerance of 1). Which switch adds it is not attributed.

## Checks

| claim | how checked here | result |
|---|---|---|
| Falcon: merged `b2c523a` = `main` `6be817a` | [`cmp_falcon_indep.py`](scripts/cmp_falcon_indep.py) on the committed records, every field except `decode_ms`/`detect_ms`/`total_ms` | **0 of 4,443 rows differ** (the files differ only in timing: `detect_ms` in 4,433 rows) |
| Falcon: both vs `aec88d2`, one health message | same | 1 row (frame 0), field `msgs` only; 0 decisions |
| Falcon: `main` vs `11bb1ab`, H′ removes 8 STOPs | same | 8 rows, frames 4394–4401, fields `decision`, `dets`, `nearest`, `obstacle`, `warning`, `warns` |
| positive control of the comparator | `11bb1ab` vs K2 variant B `c9e8daa` | 4,442 rows differ, 622 decisions |
| gate: `b2c523a` = `aec88d2` | [`cmp_gate_summary.py`](scripts/cmp_gate_summary.py): every leaf of the two summaries except latency, run metadata and code/config identity | 578 leaves, **4 differ, all health `ok`/`warn`** (`doubleT_platform`, ride). Consistent with "0 rows differ, 101 latency level only"; the per-frame files are not committed |
| gate: `4cf8e27` = `11bb1ab` | same | 578 leaves, **6 differ, all health `ok`/`warn`** (`roundT_squareT_pressureGate_squareT`, `squareT_platform_squareT_switch`, ride). Consistent; per-frame files not committed, and `runs/comparisons.txt` has no entry for this pair |
| positive control of the summary comparison | `b2c523a` vs `3535947` off (R3 on) | 24 leaves differ, among them 4 gated rows (`thin_hanging`) and set F cable recall |
| the health differences are latency | `resense/health.py:203`: `level` includes "latency p95 over budget", which `decision_level` leaves out (`health.latency_affects_decision: false`); ride `warn` against each run's speed (below); the committed per-frame comparison of `3535947` off vs H′ | ride `warn` 195–248 on the runs with `new_data` p95 52–58 ms, 1,346–1,526 on the two runs with p95 88 ms; off vs H′: 0 rows differ, 1,436 latency level only |
| the gate ran the committed configuration | `config.file_sha256` of each gate summary vs `sha256` of `git show <commit>:configs/default.yaml` | equal for `4cf8e27` (`f3f0d4b5…`, also `main`'s), `11bb1ab`, `b2c523a` and `cf58128` (the last with B's four overrides in `config.set`) |
| `4cf8e27` behaves as `11bb1ab` with K2 off | the diff between them is `track.py` (+112), `config.py`, both parameter files: the new K2 v5/v5b switches, off. [`synthetic_identity.py`](../k2_v5c_2026-10-20/scripts/synthetic_identity.py) on worktrees of both: 18 synthetic scenes × 10 frames (entry curve, station, person 25–158 m), every field of the result and the track | **0 of 180 rows differ**; positive control: variant B differs from off in 180 rows; a repeat run of `4cf8e27` equals the earlier one (0 differ) |
| `main` = `4cf8e27` in detector code | `git diff --stat 4cf8e27 origin/main -- resense native configs ros2_ws scripts setup.py pyproject.toml` | empty (the 6 changed files are evidence documents) |
| X3 on `4cf8e27`: PASS, 0 failed | recounted from [`x3_final_4cf8e27.json`](../integration_2026-10-19/runs/x3_final_4cf8e27.json) | 40 cases, 260 comparisons, 0 failed; 27 moved: set O positive STOP frames (10), the hanging cable's inside STOP rows (10), **unmatched STOP episodes +1 (7)** |
| marked bags: `4cf8e27` = 1.1.0 | the committed `marked_bags_4cf8e27/final_<bag>_stops.txt` vs `synth_markers_2026-10-19/out/<bag>_stops_v110.txt` | **byte-identical, 3 of 3 bags**. Summary level only: the per-frame records of `4cf8e27` on these bags are not committed, so "only the clear distance differs on 4 frames" is not re-derived |

Ride health against run speed (gate summaries):

| run | ride `warn` | `new_data` p95 (ms) | wall (s) |
|---|---:|---:|---:|
| `aec88d2` | 248 | 54.9 | 742 |
| `b2c523a` | 196 | 57.5 | 739 |
| `3535947` off | 1,346 | 88.0 | 807 |
| `3535947` H′ | 195 | 54.3 | 693 |
| `11bb1ab` | 1,526 | 88.7 | 792 |
| `4cf8e27` | 200 | 52.5 | 658 |

## Not verifiable from the repository

- the per-frame gate outputs of every integration commit (only summaries are committed);
- any Falcon run of `4cf8e27` (its identity with `11bb1ab` rests on the code diff and the synthetic check above);
- the per-frame marked-bag records of `4cf8e27`.

**Recommendation for the reseal:** commit the sealed commit's per-frame gate and Falcon outputs (xz) next to the
summaries, so that the identity claims of the seal can be re-derived by the reviewer and by J1.

## Reproduce

```
R=docs/evidence/integration_2026-10-19/runs; S=docs/evidence/p4_review_integration_2026-10-20/scripts
for f in $R/falcon_*.jsonl.xz; do xz -dc $f > <tmp>/$(basename ${f%.xz}); done
python -I $S/cmp_falcon_indep.py <tmp>/falcon_main_6be817a.jsonl <tmp>/falcon_off_b2c523a.jsonl   # and the other pairs above
python -I $S/cmp_gate_summary.py $R/gate_int_11bb1ab_final.json $R/gate_final_4cf8e27.json
git worktree add <wt_11bb1ab> 11bb1ab; git worktree add <wt_4cf8e27> 4cf8e27
OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 python -I docs/evidence/k2_v5c_2026-10-20/scripts/synthetic_identity.py <wt_11bb1ab> off > a.jsonl
OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 python -I docs/evidence/k2_v5c_2026-10-20/scripts/synthetic_identity.py <wt_4cf8e27> off > b.jsonl
```
