# CI on exact combined source 75ef4e2

[Run 36477865858](https://github.com/pmixay/ReSense/actions/runs/36477865858):
all four jobs passed (`checks`, `pytest`, `docker`, `offline-build`). Downloaded only the
110,281-byte cold-bag artifact and API metadata. ZIP SHA-256
`eea14fc67a026af59d09b926692354ddad39824bf681280dd5d602d22a277c53`
matches the GitHub artifact digest. [Artifact manifest](artifact_manifest.json) checks every
extracted member; the parent archive manifest maps these files to their stored forms.

## Complete source-frame audit

Both recordings retain every original header exactly once in order: 201/201 positive and
252/252 clear. The strict audit uses the same frozen source labels and matcher as the local
run, including every visible in-gauge source label in the denominators. Both freshness
contracts pass; neither capture has a held STOP; the clear recording has zero STOPs.

| Capture | Current / all | Decode+detect p95 | Current E2E p95 | All-frame E2E p95 | Playback pace |
|---|---:|---:|---:|---:|---:|
| Cold positive | 176 / 201 | 44.53 ms | 83.783 ms | 135.942 ms | **0.78194x** |
| Cold clear | 243 / 252 | 30.029 ms | 35.199 ms | 36.461 ms | 1.02645x |

The cold CI checks do not request `--min-playback-rate`. Green CI therefore does **not**
establish full-rate cold playback: the positive capture is below the local 0.9x gate.
Its invalid results comprise five queue_stale, fifteen catchup, four epoch_unconfirmed and
one resumed_after_silence. Clear has one epoch_unconfirmed, two queue_stale and six catchup.

| Target | Raw matches | Fresh matches | First / sustained fresh STOP | Fresh missed intervals |
|---|---:|---:|---:|---|
| Person | 61 / 61 | 48 / 61 | 9 / 11 | 8, 10, 17, 42–51 |
| Rail object | 128 / 185 | 124 / 185 | 73 / 73 | 1–11, 27–72, 106, 150, 189, 199 |
| Rail object from frame 75 | 126 / 126 | 122 / 126 | — | 106, 150, 189, 199 |

Frame indices are zero-based; sustained means five consecutive source frames. Raw person onset
is frame 8 and raw rail onset is frame 73. These are separate raw and fresh availability results.

## Scope of source and output comparison

The artifact's provenance pins commit 75ef4e2 and the same original bag hashes. Its logs report
native kernels enabled; the fast-input report records actual fastcloud.decode parity with the
reference on all 453 frames. The artifact includes no immutable CI image ID or installed-file
and native-binary hash map. The local image's independent verification applies to the local run.

Nineteen exposed non-timing fields and nine unaffected health fields equal the local capture
exactly. Track coefficients differ in the last floating-point digits: maximum absolute difference
1.333e-15 (floor coefficients), 1.258e-16 (yaw), and 2.989e-18 (curvature). The exact differences
are retained in [summary.json](summary.json); no exact full-track equality is claimed across
machines. All target assignments are unchanged. Timings are not a paired speed comparison.

The [per-frame audits](audit/positive.json), [clear audit](audit/clear.json), raw captures, node
logs, fast-input output, API run/jobs/artifact responses and original ZIP are retained. The exact
auditor is the parent `audit/audit_fresh_capture.py.txt`; this summary's frozen observer is
`summarize.py.txt`.
