# H1: free-top hardening, continuation of 15.10

**Code under test:** `42108ac` on `r3/column`, based on `a188a2d` of
`final/silent-misses`. **Status:** candidate, not gated or independently reviewed.
This README describes inherited measurements separately from the continuation.

## Change

The WIP makes an empty-ring claim depend on the frame's observed ring geometry,
checks channel ordering, shares an azimuth cache within a frame, and checks the
local vault before exempting objects taller than the 3.0 m envelope cut. A
non-returning band above a real column must not become evidence of a free top.

## Inherited measurements (the original agent session)

These JSONs were committed with the WIP. They have not yet been reproduced by
the continuation on Windows; their timing is not a Windows measurement.

| check | sealed 1.0.0 | candidate of 14.10 | WIP `42108ac` |
|---|---:|---:|---:|
| ride piece 1, dark band: STOP frames / episodes | 14 / 3 | 30 / 6 | 23 / 5 |
| ride piece 3, dark band: STOP frames / episodes | 2 / 1 | 13 / 3 | 7 / 3 |
| A pole on the axis: matching STOP frames | 82 | 157 | 157 |

Sources: [`ride_darkband.json`](ride_darkband.json), [`probes.json`](probes.json).
The piece-3 candidate count is **13**, as recorded in the JSON and the 14.10
review, not an inference from the WIP commit's abbreviated message.

[`battery.json`](battery.json) contains the S/B dropout, pitch and slow-replay
battery. [`ride_pieces.json`](ride_pieces.json) contains plain pieces 1 and 3.
[`vault_heights.json`](vault_heights.json) contains the tall-object probes.
The scratch drivers in [`scripts/`](scripts/) retain their original sandbox
paths; adapt them outside the detector before running.

## Pre-registered continuation acceptance

1. Reproduce the complete S/B battery of `scripts/batch_spare.sh.txt` against
   the sealed code, with identical seeds. Require no decision changes.
2. Replay gate-faithful ride pieces 1 and 3, plain and with `DARKBAND=0.6`,
   on the sealed code, the 14.10 candidate and this WIP. The dark-band STOP
   frames must improve over 14.10 with no increase in episodes; plain replays
   must match the seal. Keep the residual excess over the seal explicit.
3. Re-run the column pole/post probes of `scripts/run_probes.sh.txt` with
   node-decoded A/B/C/S backgrounds and the same ICP odometry for all codes.
   Require the A-axis pole to retain 157 matching STOP frames and no loss
   versus the 14.10 candidate in the existing pole/post cases.
4. Run the affected native/column/structure tests with Open3D available and
   no skips. Run the full regression gate on the committed WIP, no overrides
   and no `--allow`, against `../results/regression_baseline_2026-09-29_shell_off.json`.
5. Record code identity, native status, cache provenance, commands and exit
   codes for every new run. A missing/failed check does not constitute PASS.

Only a passing candidate is offered to P1 for H3; otherwise leave the branch
unintegrated. Independent safety review remains H4 (P4).
