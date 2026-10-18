# N3 dust stress — development evidence

No physical dust recording was present in the two new deliveries. The generator is a deterministic volumetric-return and ray-attenuation stress, not a calibrated model of airborne dust. Thresholds and acceptance were registered before measurement in [the protocol](../lidar_adaptation_2026-10-18/PROTOCOL.md).

**Coordinate correction, 18 October:** independent review found that the original regular harness mixed configured-frame points with calibrated rail height. The measurements below remain historical configured-box stresses; they do not satisfy the intended rail-relative placement contract. The partial Set F bank had no evaluated dust levels and lacked the common audited transform contract. Both earlier captures are preserved. Corrected measurements use the immutable harness `b9ad5f4` and fresh `*_pose_fixed` directories.

The corrected helper captures the actual last clean `MountCalibrator.apply` matrix, including identity shortcuts and startup replay. Attenuation and generated returns use those clean model axes and a flat height anchored at clean `rail_z(20 m)`. Only generated returns are transformed back; retained real XYZ, intensity and ring values are restored byte for byte. Every frame records its source and reference hashes, and the reference is never passed to the evaluated detector. This is not a graded or surveyed rail plane. Thirty focused tests passed, including real orientation adoption/replay and noncommuting rotations; a 32-frame baseline smoke completed all four levels.

The immutable detector reference is `9b92df5` (sealed 1.1.0 core). Each complete recording runs clean, low, medium and high with a fresh detector, all original timestamps and fixed seed 20261018. Corrected regular runs record harness, helper, generator, YAML and native-library identities at start/end. The seven-recording battery, dark baseline versus health-only controls, and all 30 fixed-placement Set F sequences are being rerun. Timings are under concurrent load and do not establish throughput.

## Superseded coordinate stress: completed levels

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

This historical table contains completed levels from the original coordinate convention. It is neither the complete seven-bag result nor corrected acceptance. The original regular run was stopped after four complete recordings and the fifth clean level; partial files are preserved separately. A missing row is not a pass.

## Historical suppression experiments, rejected

1. The post-tracker prototype reduced medium-density empty-platform STOP frames167→62 but fragmented alarms into33 episodes versus25 baseline. It is rejected. The original probe and report remain available.
2. The pre-tracker candidate `406ffaa` protects strong echoes, up to three distinct returns, thin lines/planes, held evidence and objects outside the observed clutter volume. Medium:167→11 false STOP frames and25→4 episodes; high:20→18 frames and3→2 episodes. Both exceed the registered maximum of one extra episode versus clean. It is rejected for runtime activation.

The remaining medium alarms include real strong far background at104–110m admitted by perturbed geometry, a mixed strong cluster around32m, and two-/three-return hanging shapes. Independent review found that suppressing those sparse shapes could also suppress real cables. We retain the failure instead of relaxing their protections. Dark-positive controls set original labeled object returns to intensity1; their results remain separate from the original intensity baseline.

## Historical health-only follow-up

The high-density pre-tracker experiment marked all345 first-platform frames degraded. One medium-density frame still reported GO because its trusted axis shrank to20m and the six-station observer stopped looking. `da8c3ce` separates broad observed-volume health from trusted-range cluster qualification. `scripts/dust_battery.py --health-only` changes health/range reporting only and leaves clusters, confirmation and STOP evidence unchanged. It is a measured experiment, not an enabled production dust classifier. Falcon intensity units are not assumed to match the Pandar stress ceiling5.

The earlier health-only platform check covers **1,035 frames** (clean, medium and high). [Independent parity](health_only_platform/independent_parity.json) finds identical input augmentation, detections, warnings, obstacle flags, nearest distance and track geometry on every frame, with no lost or added STOP. Medium and high each produce **345/345 degraded frames, zero GO and zero nonzero clear range**. Clean retains its 144 GO and nine already degraded frames. False STOP episodes remain25/3, so this visibility-reporting result did **not** pass the dust false-alarm criterion. It also uses the superseded coordinate convention; matched baseline and health-only controls are being repeated with the corrected reference before drawing current conclusions.

## Reproduce

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_CORETYPE=Haswell \
  python scripts/dust_battery.py --cache /home/resense/data/decoded \
  --detector-root /home/resense/data/n2/baseline_9b92df5 --out /tmp/dust-baseline
```

For the frozen Set F placement bank and identical objects across densities, see [SET_F_PROTOCOL.md](SET_F_PROTOCOL.md). No organizer message was sent by this task. Physical-data validation, a passing false-STOP criterion and any production activation remain distinct from implementing the harness.
