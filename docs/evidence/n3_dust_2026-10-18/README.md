# N3 dust stress — development evidence

No physical dust recording was present in the two new deliveries. The generator is a deterministic volumetric-return and ray-attenuation stress, not a calibrated model of airborne dust. Thresholds and acceptance were registered before measurement in [the protocol](../lidar_adaptation_2026-10-18/PROTOCOL.md).

The immutable reference is `9b92df5` (sealed 1.1.0 core). Each complete recording runs clean, low, medium and high with a fresh detector, all original timestamps, fixed seed20261018 and fixed cloud placement from the clean rail reference. Raw results, source/cache hashes and per-object hit rows accompany each summary. Timings are under concurrent load and do not establish throughput.

## Complete baseline levels so far

| Recording | Density | STOP frames | STOP episodes | GO frames | Degraded frames | Empty acceptance |
|---|---|---:|---:|---:|---:|---|
| doubleT_platform | clean | 0 | 0 | 144 | 9 | reference |
| doubleT_platform | low | 4 | 1 | 120 | 6 | PASS |
| doubleT_platform | medium | 167 | 25 | 60 | 32 | FAIL |
| doubleT_platform | high | 20 | 3 | 210 | 21 | FAIL |
| roundT_doubleT | clean | 0 | 0 | 83 | 0 | reference |
| roundT_doubleT | low | 0 | 0 | 72 | 0 | PASS |
| roundT_doubleT | medium | 171 | 25 | 21 | 0 | FAIL |
| roundT_doubleT | high | 13 | 3 | 168 | 9 | FAIL |
| roundT_pressureGate_roundT | clean | 2 | 1 | 150 | 0 | reference |
| roundT_pressureGate_roundT | low | 3 | 1 | 150 | 0 | PASS |

This table contains only completed levels; the full baseline and fixed-placement Set F battery are still running. A missing row is not a pass.

## Rejected suppression experiments

1. The post-tracker prototype reduced medium-density empty-platform STOP frames167→62 but fragmented alarms into33 episodes versus25 baseline. It is rejected. The original probe and report remain available.
2. The pre-tracker candidate `406ffaa` protects strong echoes, up to three distinct returns, thin lines/planes, held evidence and objects outside the observed clutter volume. Medium:167→11 false STOP frames and25→4 episodes; high:20→18 frames and3→2 episodes. Both exceed the registered maximum of one extra episode versus clean. It is rejected for runtime activation.

The remaining medium alarms include real strong far background at104–110m admitted by perturbed geometry, a mixed strong cluster around32m, and two-/three-return hanging shapes. Independent review found that suppressing those sparse shapes could also suppress real cables. We retain the failure instead of relaxing their protections. Dark-positive controls set original labeled object returns to intensity1; their results remain separate from the original intensity baseline.

## Health-only follow-up

The high-density pre-tracker experiment marked all345 first-platform frames degraded. One medium-density frame still reported GO because its trusted axis shrank to20m and the six-station observer stopped looking. `da8c3ce` separates broad observed-volume health from trusted-range cluster qualification. `scripts/dust_battery.py --health-only` changes health/range reporting only and leaves clusters, confirmation and STOP evidence unchanged. It is a measured experiment, not an enabled production dust classifier. Falcon intensity units are not assumed to match the Pandar stress ceiling5.

The complete health-only platform check now covers **1,035 frames** (clean, medium and high). [Independent parity](health_only_platform/independent_parity.json) finds identical input augmentation, detections, warnings, obstacle flags, nearest distance and track geometry on every frame, with no lost or added STOP. Medium and high each produce **345/345 degraded frames, zero GO and zero nonzero clear range**. Clean retains its 144 GO and nine already degraded frames. False STOP episodes remain25/3, so this improvement in visibility reporting does **not** pass the dust false-alarm criterion.

## Reproduce

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_CORETYPE=Haswell \
  python scripts/dust_battery.py --cache /home/resense/data/decoded \
  --detector-root /home/resense/data/n2/baseline_9b92df5 --out /tmp/dust-baseline
```

For the frozen Set F placement bank and identical objects across densities, see [SET_F_PROTOCOL.md](SET_F_PROTOCOL.md). No organizer message was sent by this task. Physical-data validation, a passing false-STOP criterion and any production activation remain distinct from implementing the harness.
