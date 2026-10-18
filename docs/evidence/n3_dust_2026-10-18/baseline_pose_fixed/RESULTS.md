# Complete seven-recording dust baseline

All seven recordings completed all four levels: **15,992 processed frames**.
Source Python hashes, raw gzip hashes, exact frame sequence/timestamps and decision counts
were verified before this report. Every object association was independently reconstructed.
The immutable detector is `9b92df5`; all densities use seed 20261018.

| Empty recording | Level | STOP frames / episodes | CAUTION | GO | Degraded | Extra episodes | Acceptance |
|---|---|---:|---:|---:|---:|---:|---|
| doubleT_platform | clean | 0 / 0 | 201 | 144 | 9 | — | reference |
| doubleT_platform | low | 4 / 1 | 221 | 120 | 6 | 1 | PASS |
| doubleT_platform | medium | 167 / 25 | 118 | 60 | 32 | 25 | FAIL |
| doubleT_platform | high | 20 / 3 | 115 | 210 | 21 | 3 | FAIL |
| roundT_doubleT | clean | 0 / 0 | 169 | 83 | 0 | — | reference |
| roundT_doubleT | low | 0 / 0 | 180 | 72 | 0 | 0 | PASS |
| roundT_doubleT | medium | 171 / 25 | 60 | 21 | 0 | 25 | FAIL |
| roundT_doubleT | high | 13 / 3 | 71 | 168 | 9 | 3 | FAIL |
| roundT_pressureGate_roundT | clean | 2 / 1 | 116 | 150 | 0 | — | reference |
| roundT_pressureGate_roundT | low | 3 / 1 | 115 | 150 | 0 | 0 | PASS |
| roundT_pressureGate_roundT | medium | 148 / 22 | 87 | 33 | 0 | 21 | FAIL |
| roundT_pressureGate_roundT | high | 2 / 1 | 92 | 174 | 64 | 0 | PASS |
| roundT_squareT_pressureGate_squareT | clean | 0 / 0 | 191 | 354 | 0 | — | reference |
| roundT_squareT_pressureGate_squareT | low | 0 / 0 | 189 | 356 | 0 | 0 | PASS |
| roundT_squareT_pressureGate_squareT | medium | 323 / 58 | 154 | 68 | 0 | 58 | FAIL |
| roundT_squareT_pressureGate_squareT | high | 66 / 13 | 150 | 329 | 76 | 13 | FAIL |
| squareT_platform_squareT_switch | clean | 11 / 3 | 446 | 420 | 0 | — | reference |
| squareT_platform_squareT_switch | low | 67 / 12 | 393 | 417 | 0 | 9 | FAIL |
| squareT_platform_squareT_switch | medium | 624 / 71 | 165 | 88 | 0 | 68 | FAIL |
| squareT_platform_squareT_switch | high | 33 / 12 | 618 | 226 | 26 | 9 | FAIL |

Each empty-bag level may add at most one STOP episode relative to its own clean recording.
An episode is a consecutive run of STOP frames, never joined across recordings.

| Positive recording | Level | STOP | CAUTION | GO | Degraded |
|---|---|---:|---:|---:|---:|
| doubleT_obstacle | clean | 193 | 0 | 8 | 0 |
| doubleT_obstacle | low | 170 | 12 | 19 | 0 |
| doubleT_obstacle | medium | 133 | 19 | 49 | 0 |
| doubleT_obstacle | high | 20 | 18 | 163 | 0 |
| cloud_with_fake_obj | clean | 452 | 320 | 736 | 15 |
| cloud_with_fake_obj | low | 447 | 325 | 737 | 15 |
| cloud_with_fake_obj | medium | 1090 | 264 | 155 | 208 |
| cloud_with_fake_obj | high | 173 | 487 | 849 | 233 |

Low-density crossing first-range criterion (at least 90% of clean): **PASS**, ratio **1.0**.
Per-frame STOP retention is reported separately; a preserved first range does not imply preserved later detections.

| Object | Level | Temporal first STOP m: any / inside | Inside / outside / unknown matches | Lost clean inside / outside / unknown |
|---|---|---|---|---|
| doubleT_obstacle: person_crossing | clean | 55.51 / 55.51 | 61 / 6 / 0 | reference |
| doubleT_obstacle: person_crossing | low | 55.51 / 55.51 | 61 / 5 / 0 | 0 / 1 / 0 |
| doubleT_obstacle: person_crossing | medium | none / none | 0 / 0 / 0 | 61 / 6 / 0 |
| doubleT_obstacle: person_crossing | high | none / none | 0 / 0 / 0 | 61 / 6 / 0 |
| doubleT_obstacle: object_on_rail | clean | 56.13 / 56.13 | 128 / 0 / 0 | reference |
| doubleT_obstacle: object_on_rail | low | 56.11 / 56.11 | 104 / 0 / 0 | 24 / 0 / 0 |
| doubleT_obstacle: object_on_rail | medium | none / none | 0 / 0 / 0 | 128 / 0 / 0 |
| doubleT_obstacle: object_on_rail | high | none / none | 0 / 0 / 0 | 128 / 0 / 0 |
| doubleT_obstacle: person_walkway | clean | none / none | 0 / 0 / 0 | reference |
| doubleT_obstacle: person_walkway | low | none / none | 0 / 0 / 0 | 0 / 0 / 0 |
| doubleT_obstacle: person_walkway | medium | none / none | 0 / 0 / 0 | 0 / 0 / 0 |
| doubleT_obstacle: person_walkway | high | none / none | 0 / 0 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: big_center | clean | 98.16 / 98.16 | 209 / 0 / 0 | reference |
| cloud_with_fake_obj: big_center | low | 98.16 / 98.16 | 209 / 0 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: big_center | medium | 98.16 / 98.16 | 167 / 0 / 0 | 42 / 0 / 0 |
| cloud_with_fake_obj: big_center | high | 62.17 / 62.17 | 2 / 0 / 0 | 207 / 0 / 0 |
| cloud_with_fake_obj: small_on_rail | clean | 47.96 / 47.96 | 26 / 0 / 0 | reference |
| cloud_with_fake_obj: small_on_rail | low | 44.42 / 44.42 | 24 / 0 / 0 | 2 / 0 / 0 |
| cloud_with_fake_obj: small_on_rail | medium | 30.21 / 30.21 | 16 / 0 / 0 | 10 / 0 / 0 |
| cloud_with_fake_obj: small_on_rail | high | none / none | 0 / 0 / 0 | 26 / 0 / 0 |
| cloud_with_fake_obj: small_center | clean | 55.84 / 55.84 | 32 / 0 / 0 | reference |
| cloud_with_fake_obj: small_center | low | 57.49 / 57.49 | 33 / 0 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: small_center | medium | 23.84 / 23.84 | 13 / 0 / 0 | 19 / 0 / 0 |
| cloud_with_fake_obj: small_center | high | none / none | 0 / 0 / 0 | 32 / 0 / 0 |
| cloud_with_fake_obj: small_edge_inside | clean | 34.97 / 34.97 | 18 / 0 / 0 | reference |
| cloud_with_fake_obj: small_edge_inside | low | 34.97 / 34.97 | 18 / 0 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: small_edge_inside | medium | 18.25 / 18.25 | 9 / 0 / 0 | 9 / 0 / 0 |
| cloud_with_fake_obj: small_edge_inside | high | none / none | 0 / 0 / 0 | 18 / 0 / 0 |
| cloud_with_fake_obj: small_outside_near | clean | none / none | 0 / 0 / 0 | reference |
| cloud_with_fake_obj: small_outside_near | low | none / none | 0 / 0 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: small_outside_near | medium | 38.76 / none | 0 / 8 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: small_outside_near | high | none / none | 0 / 0 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: big_edge_inside | clean | 18.26 / 18.26 | 7 / 0 / 0 | reference |
| cloud_with_fake_obj: big_edge_inside | low | 18.26 / 18.26 | 2 / 0 / 0 | 5 / 0 / 0 |
| cloud_with_fake_obj: big_edge_inside | medium | 10.27 / 10.27 | 5 / 0 / 0 | 2 / 0 / 0 |
| cloud_with_fake_obj: big_edge_inside | high | none / none | 0 / 0 / 0 | 7 / 0 / 0 |
| cloud_with_fake_obj: big_outside | clean | 142.29 / none | 0 / 7 / 0 | reference |
| cloud_with_fake_obj: big_outside | low | 142.29 / none | 0 / 7 / 0 | 0 / 1 / 0 |
| cloud_with_fake_obj: big_outside | medium | none / none | 0 / 0 / 0 | 0 / 7 / 0 |
| cloud_with_fake_obj: big_outside | high | none / none | 0 / 0 / 0 | 0 / 7 / 0 |
| cloud_with_fake_obj: big_above | clean | 111.42 / 111.42 | 56 / 0 / 0 | reference |
| cloud_with_fake_obj: big_above | low | 111.42 / 111.42 | 56 / 0 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: big_above | medium | 111.42 / 111.42 | 40 / 0 / 0 | 16 / 0 / 0 |
| cloud_with_fake_obj: big_above | high | 101.32 / 101.32 | 8 / 0 / 0 | 48 / 0 / 0 |
| cloud_with_fake_obj: long_low_on_rails | clean | 88.97 / 88.97 | 53 / 0 / 0 | reference |
| cloud_with_fake_obj: long_low_on_rails | low | 90.75 / 90.75 | 52 / 0 / 0 | 2 / 0 / 0 |
| cloud_with_fake_obj: long_low_on_rails | medium | 88.97 / 88.97 | 31 / 0 / 0 | 22 / 0 / 0 |
| cloud_with_fake_obj: long_low_on_rails | high | none / none | 0 / 0 / 0 | 53 / 0 / 0 |
| cloud_with_fake_obj: thin_hanging | clean | 30.12 / 30.12 | 15 / 0 / 0 | reference |
| cloud_with_fake_obj: thin_hanging | low | 30.12 / 30.12 | 15 / 0 / 0 | 0 / 0 / 0 |
| cloud_with_fake_obj: thin_hanging | medium | 20.13 / 20.13 | 9 / 0 / 0 | 6 / 0 / 0 |
| cloud_with_fake_obj: thin_hanging | high | none / none | 0 / 0 / 0 | 15 / 0 / 0 |

Gauge relation comes from each individual label row, including the crossing person changing relation.
Outside associations are never silently counted as inside positives. Every exact lost/new row,
unmatched detection frame and first-range ratio remains in [verified_complete.json](verified_complete.json).

| High-density recording | GO without degradation | Degraded / all frames |
|---|---:|---:|
| doubleT_platform | 210 | 21 / 345 |
| roundT_doubleT | 168 | 9 / 252 |
| roundT_pressureGate_roundT | 174 | 64 / 268 |
| roundT_squareT_pressureGate_squareT | 329 | 76 / 545 |
| squareT_platform_squareT_switch | 226 | 26 / 877 |
| doubleT_obstacle | 163 | 0 / 201 |
| cloud_with_fake_obj | 849 | 233 / 1510 |

High density is required to be explicitly degraded rather than silently GO. The table preserves
every failure; STOP under high density by itself is not proof that visibility health was recognized.
The corrected captures include source, native-library, configuration and helper hashes
at start and after each completed level; the verifier checks those immutable dependencies.
These are fixed synthetic stresses, not calibrated physical dust. Timing shared a single-CPU
host and includes recorded pauses, so it does not establish throughput.
