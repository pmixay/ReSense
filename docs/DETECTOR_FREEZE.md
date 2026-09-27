# Detector seal — 27 September 2026 (replaces the P3d seal of 26.09)

**Current decision:** the detector of the [27.09 quality cycle](QUALITY_CYCLE_2026-09-27.md) is the
reference. Its seal [`detector_freeze_2026-09-27.json`](evidence/detector_freeze_2026-09-27.json)
covers 31 files (the learned track opinion `resense/models/track_opinion.json` included) against
the full gate [`regression_gate_2026-09-27_quality.json`](evidence/results/regression_gate_2026-09-27_quality.json)
of `25498c1`: PASS against the P3d baseline with no waiver, missing row or worse gated metric,
on the default parameters without overrides. That gate is the new regression baseline
([`regression_baseline_2026-09-27_quality.json`](evidence/results/regression_baseline_2026-09-27_quality.json)).
`python scripts/detector_freeze.py verify` (CI job `params-in-sync`) checks the new seal. No release
tag has been created or pushed.

## The P3d seal of 26 September (dated record)

**Earlier baseline decision:** preserve the validated detector and default configuration.
Detector behavior remains that of `fa18832`; the acceptance
baseline is [`regression_baseline_2026-09-26_ride_p3d.json`](evidence/results/regression_baseline_2026-09-26_ride_p3d.json).
Further authorized candidates use isolated worktrees and must pass acceptance before integration.

The [manifest](evidence/detector_freeze_2026-09-26.json) identifies every frozen file by SHA256,
the measured source commit, the complete validation record and its hash. It covers `resense/`,
`native/`, `configs/`, the ROS config copy and detector build inputs. Generated binaries and Python
caches are excluded. Node transport, launch, Docker and documentation have separate checks.
This is a detector freeze; it does not declare the submission or deployment complete.

## Acceptance and provenance

The [current full gate](evidence/results/regression_gate_2026-09-26_comment_correction.json) passed on this
machine without `--allow`: all six recordings, 1,510 organizer-object frames, all 11,271 ride
frames and set F straight are present. Every gated row equals `_ride_p3d`; only informational
latency rows differ. The measured commit is `cc834fc`; the seal generator verifies every sealed
file against that commit. The earlier [second-machine gate](evidence/results/regression_gate_2026-09-26_head_fresh_machine.json)
remains as an independent reproduction. Creating or verifying the manifest itself does not
replay data; the linked fresh gate did.

This refresh corrects unsupported clearance claims in comments and docstrings only. Executable
syntax trees and all configuration values are unchanged. Source digest is now
`5d9a20861f66bb2c085d91c8a03a26710e6a1455d02c156102f6d9fdedff5fa6`.
The [earlier seal](evidence/detector_freeze_2026-09-26_before_comment_correction.json) and its
[original gate](evidence/results/regression_gate_2026-09-26_freeze.json) remain preserved.
[Refresh evidence](evidence/results/quality_comment_baseline_2026-09-26/README.md).
This is an integrity record for the unchanged P3d behavior; final quality acceptance remains on hold.

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

For an authorized replacement: describe the defect and its acceptance test, review the patch,
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

The current provisional independent combined score is 64/100; the 75-point target is not met. Set O edge objects STOP only at 5–10 m;
the ride has 45 false events and has no real obstacles. There is no unseen-route recall result.
`clear_distance` estimates the monitored region capped by detected candidates; it can extend
past objects that do not form a cluster. It must not be described as a guarantee of empty track.
For the current evidence and output contract, use `STOP` and `nearest_distance`, with the health
and warning outputs; see [the current SCORECARD](SCORECARD.md#freeze-review-26-september-night).

The node startup fix passes fresh idle cold/warm and stock-console checks; see
[evidence](evidence/freeze_2026-09-26/README.md). The public image archive, final CI and submission
remain separate work.
Q1/Q2 answers, private team information and the human pitch are external dependencies.
