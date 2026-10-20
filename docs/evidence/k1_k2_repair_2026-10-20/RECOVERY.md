# Restart recovery and deadline handoff — 20 October 2026

**K2/K1 stay off in 1.2.0.** Author branch: `fix/k1-k2-repair-20261020`.
The pre-restart committed checkpoint was `67abc93b`; production code remains
r5a `ead83747`. This recovery adds measurements, reproducible recovery tools
and documentation. Full acceptance, another independent reviewer and the
captain/P1 switch/reseal decision remain outstanding.

## Completed recovery

| work | recovered result |
|---|---|
| r4 targets | reused all 12 complete trace/plain pairs and seven complete controls; restarted only the combined crossing control from frame zero; 164 interrupted rows preserved |
| r5 marked bags | reused all 12 complete runs; scored/published three paired bags; 1,667 default-off rows identical; marker 19 still loses frame 259 |
| r5a marked / Set O follow-up | eight new exact-source candidate runs, completed reference rows reused with hashes; 3,177 default-off rows identical; no non-timing changes versus r5 in either mode; marker 19 still loses frame 259 |
| r5 Set O | preserved parent partials (935 and 840 rows) and original manifest; completed all four 1,510-row runs on the original immutable sources; retained raw SHA-256 checked before/after |
| r3/off X3 | reused the completed immutable run; audit passes all 40 cases /260 comparisons, no inside-object lost/gained frames; invalid mixed-HEAD report retained |
| six organizer bags | retained B decoding; verified/reused 226 platform NPZs against raw DB3, preserved truncated frame 226, wrote 119 missing platform frames; decoded all 268 C frames; all six decoded receipts complete |
| 20-minute ride | reused 217 validated splits; cached only 65, 75, 137, 157; complete source size/SHA-256 verified: 221 splits /11,271 frames |

Ride source SHA-256:
`8124b627a8a70516a4023db522849f1cadae711e7b152b0f701535a69dab99ec`
(17,078,961,996 compressed bytes). Completing intake is not a gate PASS.

## Durable receipts and reproduction

- [`recover_runs.py`](recover_runs.py): `targets` / `seto`, pinned Python 3.12;
  source hashes checked against the original manifest, exclusive lock, fresh
  attempt directories, atomic receipt writes and archived interrupted bytes.
- [`recover_six.py`](recover_six.py): checks retained raw and source ZIP hashes;
  valid surviving NPZ arrays must equal decoding of the verified source.
- [`run_followup.py`](run_followup.py): r5a-only measurements from immutable
  `/tmp/opencode/k1-k2-r5a`; verified complete r3 references are copied with
  their hashes and source receipt, rather than rerunning them.
- Runtime receipt/logs: `data/k1-k2/runs/recover-*.{json,log}`,
  each output's `recovery/` directories, `data/k1-k2/six-intake.json`,
  `data/k1-k2/cache/new_data/intake_manifest.json`.
- [Recovery archive](recovery-receipts.tar.xz) and
  [byte-verification manifest](recovery-receipts-package.json) preserve 56
  artifacts, including Set O interrupted bytes, intake receipts and failed logs.
- Long commands run under named `resense-k1k2-*` user services with logs on
  the repository filesystem. An OpenCode restart no longer destroys the
  subprocess or its only log. A host restart still requires artifact validation.

Execution incidents are retained: the first six-bag helper lacked
`RESENSE_REPO` and failed on import; its second attempt rejected the truncated
legacy NPZ. The corrected helper preserves that file and regenerates only the
missing frame. The first r5a launcher lacked `PYTHONPATH` and failed on import;
the corrected launch has an explicit absolute path. None is a completed run.

## Remaining acceptance

R5a marked / Set O follow-ups are complete. The strict
parent/off/enabled gate, final-source X3 and K1/K2/B6 rows, Falcon near/height
and original-frame losses, crossing/weak-object admission and prolonged stale
trust remain open. Data intake is now available for the strict gate.
The final candidate has not passed acceptance and the old integrity seal is
not renewed. The historical P4 review cannot serve as independent review of
this session's author repairs.

The deadline handoff documents the separate Falcon clear-distance finding as a
[known limit](../falcon_clear_limit_2026-10-20/README.md). That choice does not
accept the separate experimental Falcon repair branch.
