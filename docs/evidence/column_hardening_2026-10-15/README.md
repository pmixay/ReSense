# H1: free-top hardening, continuation of 15.10

**Code under test:** `42108ac` on `r3/column`, based on `a188a2d` of
`final/silent-misses`. **Status:** full gate PASS in the continuation; independent H4 review pending.
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

## Continuation results (15.10, Windows)

Measured code commit **`a2660af`**: detector bytes in Git are the WIP `42108ac`;
`a2660af` added this acceptance README only. Native kernels were rebuilt with
MSVC x64 `/O2 /std:c++17 /fp:strict`; Python 3.11, Open3D 0.20. Source/cache
identities and commands: [`continuation/provenance.json`](continuation/provenance.json).
These are new local measurements, not a relabelling of the inherited JSONs.

* **Full gate PASS, exit 0, no overrides or waivers:**
  [`continuation/gate.json`](continuation/gate.json), against the published
  `regression_baseline_2026-09-29_shell_off.json`. The local control run on
  `final/silent-misses` (`264f5b2`, documentation-only continuation of `d0d17bb`)
  first reproduced the same baseline without failing rows.
* **15,269 frames / 15 work outputs:** no changed `obstacle`, `warning`,
  `detections`, `warnings`, `nearest_distance`, `clear_distance`,
  `n_candidates` or `track` against that local control
  ([`frame_diff.json`](continuation/frame_diff.json)). Timing/latency health
  telemetry is not an output-equality claim. Set F is also covered by the gate.
* **Dark band reproduced exactly:** piece 1, 30/6 -> 23/5 STOP frames/episodes;
  piece 3, 13/3 -> 7/3. Plain pieces remain 14/3 and 2/1, as the seal
  ([`darkband.json`](continuation/darkband.json)). The residual excess over the
  seal under the dark-band what-if remains 9 and 5 STOP frames.
* **20 S/B stress cases:** zero decision differences and equal STOP counts
  against the sealed detector ([`battery.json`](continuation/battery.json)).
  Three warning descriptors do differ: `reason: column` -> `reason: ""` at
  S drop20 seed2 frame 344, B drop30 seed3 frame 168, and B slow3 seed1 frame
  482. Each remains CAUTION; distances, shapes and confidence are unchanged.
  Exact differences: [`descriptor_diff.json`](continuation/descriptor_diff.json).
  This is an explicit H4 review item, not byte-identical warning metadata.
* **15 pole/post controls:** no lost matching STOP and no new GO versus
  14.10; the A-axis pole retains **157/177**, first STOP 218.38 m
  ([`probes.json`](continuation/probes.json)). Six extra 3.2/3.6 m pole probes
  also lose no STOP ([`tall_probes.json`](continuation/tall_probes.json)).
* **Affected tests:** `RESENSE_REQUIRE_SYNTHETIC=1 python -m pytest -q
  tests/test_native.py tests/test_column_free_top.py tests/test_structure_cut.py`
  -> **51 passed, zero skipped**.

P3 measurements are complete. P1's H3 integration and P4's independent H4
review are the next acceptance steps; the current detector seal is unchanged.
