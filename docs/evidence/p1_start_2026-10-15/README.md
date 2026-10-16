# P1 / P4 checkpoint: the 15–16 October work

**Recorded:** 16 October 2026. **P1 branch:** `p1/start-2026-10-15`, from
`final/silent-misses` `d0d17bb`. **P4 branch:** `p4/eval-start-2026-10-15`, from
`main` `3fdc879`. The user selected this computer and authorized parallel agents.

Calendar source: [`BACKLOG.md` on main](https://github.com/pmixay/ReSense/blob/main/docs/BACKLOG.md),
§4–§5. This checkpoint records implemented work and measured failures separately.

## P1: outcomes against the calendar

| Item | Work completed | Acceptance / remaining work |
|---|---|---|
| O1 | Three-question organizer message, rationale and pending-answer journal prepared; presentation timing remains an explicit five-minute assumption | **Not dispatched.** The captain must send [the message](../../QUESTIONS.md) and record the dated verbatim reply. No organizer permission is inferred |
| C1 semantics and shared module | Contract fixed in DECISIONS row 32; pure shared policy used by node, four scripts and backend; runtime/launch parameters, additive `caution_reason`, wheel dependency and source-origin checks | v1 stays default. **v2 rejected by the measured screen:** 30.46% empty-frame CAUTION versus ≤25%, 19 lost labelled object-frame alerts. Final-1.1.0/B/C acceptance remains open |
| S1 start | Adaptive startup step 0.2–0.3 s; 2.5 s startup lag; DDS and global Python queue caps 12; bounded metadata, explicit skip accounting, one-period freshness with all guards retained | Implementation and tests pass; **original-bag acceptance FAIL**, including the verified Linux-volume follow-up. S1 is not ready to ship |
| E2 | Offline clean source/native/ROS rebuild on the exact loaded image; non-root ROS directories; release-workflow check; changed/backdated-source stale-cache regression | **Local Docker acceptance PASS.** First E2 offline build 18.609 s; final integrated source rebuild 19.156 s. Tagged release workflow remains a future release check |

The C1 retained-alert counts are frame-level checks, not object-matched detection recall.
Its screen uses saved candidate-base outputs, not final-1.1.0 judge-path evidence.

### S1 real-bag measurements

Both four-condition × three-run matrices are retained, including incomplete runs.
The initial Windows-bind run had long I/O stalls. A subsequent Docker Linux volume was
verified against the original DB3/metadata hashes, and a pre-registered read-only hash
prefetch produced 25.246–31.523 s player times and zero starvation warnings. The numeric
acceptance still failed:

| Condition, Linux volume | Median | Required |
|---|---:|---:|
| 360° literal fresh | 1/201 | ≥80% of 201 |
| 360° literal source age p50 | 1.190 s | ≤0.5 s |
| 360° literal memory | 784.916 MB | ≤1,200 MB |
| 360° README fresh | 85/201 | ≥180/201 |
| 360° README STOP frames | 147 | ≥185 |
| 360° README first-STOP lag | 2.163 s | ≤1.2 s |
| 120° literal FAULT | 16 | ≤10 |
| 120° README fresh | 235/252 | ≥242/252 |

These are descriptive medians including repetitions whose strict completeness check failed;
both `passed` and `complete` are false. No favorable-run selection or threshold relaxation.
The chosen host has 12 logical CPUs, Docker RAM 6.698 GiB, four-core per-container quotas
and 6 GiB per-container limits; this is not an exact four-vCPU-host reproduction or a
same-runtime baseline comparison. No causal improvement claim is made.

The Linux-volume matrix measured `62d055f`, before the later decode-failure accounting
fix. The final unit suite covers that fix; the old numeric measurements are not relabelled
as measurements of newer code.

## P4: completed in the separate evaluation branch

| Item | Recorded result |
|---|---|
| H0 | Exact `707ea9c`, full gate exit 0 without waivers; **208/208 non-latency rows identical**; six bags, Set O and complete ride verified; 3,998 float32 node-decoded frames available |
| G3 specification | A separate non-tuning agent committed fixed **4 windows, 8 classes, 84 cases × 11 variants = 924 future replays**. Schema, deterministic generation and input metadata checks pass; **no held-out run performed** |
| X3 start / reusable baseline | Standing CLI, tests and acceptance rule; **40/40 cases, 29,765 frames, 18m16s**, all requested historical judge figures reproduced exactly on 1.0.0 |

H0/X3 used Windows-native Python on this user-selected computer, not a Linux team VM.
The G3 holdout is new synthetic placements/probes on previously used ride backgrounds,
not an independent real dataset. The registration discloses incidental legacy-summary
text exposure; its author neither wrote/tuned the detector nor ran these cases. Geometry-only
scene preparation and the single final-seal run belong to the later G3 execution stage.

P4 report: [`p4/eval-start-2026-10-15`](https://github.com/pmixay/ReSense/blob/p4/eval-start-2026-10-15/docs/evidence/p4_start_2026-10-15/README.md).
Data root: `C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/`.

## Verification and independent review

* [Final integrated Linux suite](integrated_linux_checks/FINAL_SOURCE.md):
  **1,601 passed, zero failed/errors/skipped**, ten existing missing-realdata deselections.
  Exact tested source `7d3d5a0`; clean native/ROS rebuild, installed package outside source,
  Open3D present, network disabled. Later test formatting is AST-equivalent.
* [Independent node/tool review](INDEPENDENT_REVIEW.md): all confirmed packaging,
  producer/consumer, raw-health/latch and skip-credit defects fixed and rechecked.
  This is separate from the detector's future H4 review.
* [Finalization](FINALIZATION.json) verifies the final formatting-only test delta,
  CI-scope Ruff, unchanged sealed inputs relative to the candidate base, the saved
  passing suite and explicitly failed S1/C1 verdicts. Historical failing lint receipts
  remain preserved; the final seven E701 formatting errors were corrected.
  The [pinned CI Ruff 0.15.8 check](CI_RUFF.md) also passes in Linux.

## Evidence map and next owners

* [S1 implementation](../node_startup_2026-10-15/S1.md),
  [Windows matrix](../node_startup_2026-10-15/docker/README.md),
  [Linux-volume matrix](../node_startup_2026-10-15/docker/linux_volume_2026-10-16/README.md).
* [C1 contract](../caution_policy_2026-10-15/CONTRACT.md),
  [rescore evidence](../caution_policy_2026-10-15/EVIDENCE.md),
  [standalone wheel check](../caution_policy_2026-10-15/PACKAGING_REVIEW.md).
* [E2 runtime / offline / mutation evidence](../offline_rebuild_2026-10-15/README.md).

Next: captain sends O1; finish S1 performance/freshness diagnosis and C1 acceptance;
P1/P4 carry out H3–H6 on their planned dates; X3 gets a 1.1.0 baseline once the seal exists;
another fresh agent performs the registered G3 final batch around 21.10. These start-work
results do not make S1/C1 accepted or substitute for combined detector acceptance/release.
