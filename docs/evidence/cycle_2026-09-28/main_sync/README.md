# Combined node and health validation, 28.09

Measured source **75ef4e2**, sealed detector digest `c0273a13…`, immutable image
`sha256:f7ae11b87e187448ac25166983438e7304617b2eb85505564b38ed647dc2ec50`.
One local warm-disk run per recording, 1x playback, read-ahead 10, startup step 0,
warm-up enabled. Both registered checks passed. This is not a cold-start or target-hardware
measurement, and it does not establish a speedup over earlier unpaired captures.

## Scope and identity

The detector, effective configuration, native binary and package versions match the earlier
health candidate `ef71c9d`; the node, launch defaults, fast decoder and checker have changed.
The node's new 0.2 s startup thinning stays opt-in. The imported node and fastcloud, installed
launch/configuration/checkers and enabled native library were independently checked inside
the immutable image after capture: [installed verification](installed_verification.json).
The actual fast decoder and reference arrays match byte for byte on **453/453** original
frames ([report](fast_input.json)); timing columns there measure deserialization/parsing only.

The [strict audit summary](audit/summary.json) binds source, protocol, execution, image and
capture hashes. Every original header is present once, in order: **201/201** positive and
**252/252** clear. Twenty exposed non-timing fields and nine unaffected health fields are
exactly equal at all 453 frames to the earlier health candidate. Timing, freshness policy
outputs and health fields overwritten by freshness are excluded explicitly in the summary.

## Current results and timing

| Recording | Current / all | Decode p95 | Detect p95 | Decode+detect p95 | Current E2E p95 | All-frame E2E p95 | Pace |
|---|---:|---:|---:|---:|---:|---:|---:|
| Positive | 172 / 201 | 25.22 ms | 64.43 ms | 86.95 ms | 114.392 ms | 490.086 ms | 1.02788x |
| Clear | 248 / 252 | 19.595 ms | 47.052 ms | 59.7895 ms | 72.950 ms | 75.010 ms | 1.00981x |

E2E is the status evaluation time minus the player's publication timestamp. Pace uses the
first and last processed evaluation clocks. These captures have one recording each, complete
ordered headers and finite, positive, strictly progressing evaluation clocks. Component p95
values are not additive. Full timing distributions and per-frame rows remain in the audits.
Positive invalid reasons: one epoch_unconfirmed, three queue_stale, ten source_stale and
fifteen catchup. Clear: one epoch_unconfirmed and three catchup. Both freshness contracts pass;
the clear recording has zero STOPs. The positive node counter's four drops are the recording's
four missing nominal slots, not missing stored messages. Both runs intentionally skip zero frames.

## Raw and fresh targets

All visible in-gauge labels from all original frames remain in the denominator. Fresh matches
require an actual detector STOP, not held, and a strict current result. Frame indices are zero-based;
sustained onset means five consecutive original source frames.

| Target | Raw | Fresh | First / sustained raw STOP | First / sustained fresh STOP | Fresh missed intervals |
|---|---:|---:|---:|---:|---|
| Person | 61 / 61 | 40 / 61 | 8 / 8 | 29 / 29 | 8–28 |
| Rail object | 128 / 185 | 128 / 185 | 73 / 73 | 73 / 73 | 1–11, 27–72 |
| Rail object from frame 75 | 126 / 126 | 126 / 126 | — | — | none |

Raw matches are unchanged. The earlier unpaired `ef71c9d` capture had 49/61 fresh person
matches and first/sustained onset at 16/18, so this run does **not** demonstrate fresh-person
recall or onset parity. Full fresh availability remains open despite complete source coverage.

## Provenance and archive

[Preflight](preflight.json), [protocol](runtime_protocol.json), [execution plan](execution_plan.json),
[execution](execution.json), [build](build.json), [image identity](image_identity.json), and
[transport regression](transport_fix.json) are preserved without rewriting.
The [P3 handoff](https://github.com/pmixay/ReSense/pull/24#issuecomment-5877703539) and
[exact-source CI run](https://github.com/pmixay/ReSense/actions/runs/36477865858) are recorded
in preflight. Frozen observer/runner/checker scripts use `.py.txt`; logs use `.txt`; status
captures use deterministic gzip. `manifest.json` maps every original external file to its
archive path with raw and stored bytes and SHA-256. The original source bags stay external.

## Exact-source CI

The [CI archive](ci/README.md) preserves all four green jobs at 75ef4e2 and both original
cold-bag captures. The positive replay ran at 0.78194x, so the original cold CI pass does not
establish full-rate playback. CI fresh person recall is 48/61, with first/sustained onset
9/11. The CI and local results retain their separate clocks, hardware and measurement scope.

A follow-up CI change adds separate warm-cache positive and clear runs after the existing cold
checks and decoder parity. They require 201/252 frames, zero post-settle drops, at least 0.9x
playback and processing p95 at most 100 ms; the clear run permits zero STOPs. These new gates
were not part of the green 75ef4e2 run.
