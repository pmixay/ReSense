# Detector freeze — 26 September 2026

**Decision: freeze the validated detector and default configuration.** The user delegated the
captain's decision on 26 September. Detector behavior remains that of `fa18832`; the acceptance
baseline is [`regression_baseline_2026-09-26_ride_p3d.json`](evidence/results/regression_baseline_2026-09-26_ride_p3d.json).
Only blocker fixes may change the frozen sources after this decision.

The [manifest](evidence/detector_freeze_2026-09-26.json) identifies every frozen file by SHA256,
the measured source commit, the complete validation record and its hash. It covers `resense/`,
`native/`, `configs/`, the ROS config copy and detector build inputs. Generated binaries and Python
caches are excluded. Node transport, launch, Docker and documentation have separate checks.
This is a detector freeze; it does not declare the submission or deployment complete.

## Acceptance and provenance

The committed [full gate on the second machine](evidence/results/regression_gate_2026-09-26_head_fresh_machine.json)
passed without `--allow`: all six recordings, the organizers' object recording, all 11,271 ride
frames and set F straight are present. Every gated row equals the baseline. Its measured commit
is `53b75d4c377d89a8051eb2ff9a7de4d135f8bb8b`; the seal generator verifies that every current frozen
file has exactly the bytes of that measured commit. Reusing this record is an integrity and
provenance check, **not a new replay of the data**. A subsequent fresh full run can replace the
manifest's validation reference once it passes.

The default configuration file SHA256 is
`c7ca5ad4f332b7025f66ab0addeb21025daf23a36aca4dbcc2d49fe5b8831f40`;
the effective configuration SHA256 is
`d2c8ab8d70954956d71c50cdc074962a3037e7ea2bc0e09568663ab34af53d6e`.

| Pending detector choice | Final decision | Evidence and reason |
|---|---|---|
| P4 candidate B: near escalation 10 → 8 voxels | Do not ship; retain 10 | [Full gate](evidence/results/regression_gate_2026-09-26_p4_candidate_B_full.json) and stress checks pass. The gain is one STOP frame at 7.1 m on edge object #4. That small gain does not justify lowering the threshold for every demoted track before the freeze. |
| Envelope union | Keep `gauge.axis_union: 0` | [Full gate](evidence/results/regression_gate_2026-09-26_axis_union_fixed_full.json) passes, but Q1 on the reference axis is unanswered and the shape review of union clusters remains open. |
| Candidates A and C | Rejected | Neither improves its target on the default detector; [P4 decision record](evidence/results/p4_p3d_candidate_decisions_2026-09-26.json). |
| Further platform-axis and remount changes | Defer detector research | Measured limitations remain in [EXPERIMENTS §5](EXPERIMENTS.md#5-open-experiments). No additional bounded candidate passed the required acceptance checks. |

## Verify or replace the seal

From the repository root, with Python 3.10 or later:

```bash
python scripts/detector_freeze.py verify
```

This requires no data cache, third-party Python packages or Git checkout. It fails if a source file
is added, changed or removed, a config copy differs, or the baseline or validation record changes.
It does not execute the regression gate. Review of the manifest remains required: checksums do
not prevent someone from deliberately replacing both a file and its recorded hash.

For an authorized blocker fix: describe the defect and its acceptance test, review the patch,
run the affected tests, commit the detector, then run the complete strict regression gate and
create and review the replacement seal. The gate must name a commit with no uncommitted detector
changes and use the default config without overrides. For example:

```bash
python scripts/regression_gate.py --cache /path/to/cache --jobs 3 \
  --baseline docs/evidence/results/regression_baseline_2026-09-26_ride_p3d.json \
  --out docs/evidence/results/regression_gate_frozen.json
python scripts/detector_freeze.py create \
  --evidence docs/evidence/results/regression_gate_frozen.json
python scripts/detector_freeze.py verify
```

## Limits retained at the freeze

The score of record remains 62.5/100 until re-judgement. Set O edge objects STOP only at 5–10 m;
the ride has 45 false events and has no real obstacles. There is no unseen-route recall result.
`clear_distance` estimates the monitored region capped by detected candidates; it can extend
past objects that do not form a cluster. It must not be described as a guarantee of empty track.
For the current evidence and output contract, use `STOP` and `nearest_distance`, with the health
and warning outputs; see [SCORECARD §0](SCORECARD.md#0-re-judgement-of-2609-evening-integrated-head-be5f5fc-625--100).

The cold-burst node issue, public image archive, final CI and submission remain separate work.
Q1/Q2 answers, private team information and the human pitch are external dependencies.
