# LiDAR adaptation — integration record, 18 October 2026

Work continues on `work/n5-labels-c2-acceptance`. At the captain's request, the temporary
`work/lidar-n2-n4-n1-n3-n6` branch was deleted locally and remotely while preserving its work.
Remote `main` was fetched again and remains `3b7d7aa7cbbf238c21f84330497697da131b7cb9`, already
an ancestor of this branch. This is development integration, not a release. The captain's
standalone map remains `/home/resense/P1_work_map_2026-10-17.md`, outside this repository.

## Work other members can use

| Dependency | Delivered | Remaining acceptance |
|---|---|---|
| P2 display/demo | Shared bounded gauge/status contract, software RViz, interactive same-node profile switch, operator commands | Final combined-source display and isolated transport/performance results |
| P4 evaluation | Complete verified Falcon cache, reviewed raw target associations, immutable comparison harnesses and all N6 control captures | Full default gate, X3 and Falcon proxy gate |
| P1 integration | Explicit sensor profiles, orientation readiness guard and bounded startup history replay | Final gate, independent review and new source seal |
| Release | Branch work and local validation | Captain's hosted CI/quota repair and later release decision |

## Current result by card

| Card | Implemented and measured | Limit or regression |
|---|---|---|
| [N2 Falcon](../n2_falcon_2026-10-18/README.md) | All 4,443 frames verified; explicit ROS/native profiles agree throughout; automatic mapping matches after initial unconfirmed FAULT. Eight supported automatic orientations retain all 193 real-obstacle STOP frames, first at frame 8. | Reviewed person first STOP improves about 124.67→127.07 m, while static 115 m structure STOP associations increase 13→29. No surveyed corridor truth resolves those static alarms. Deduplication/channel thinning and the Falcon sampling proxy lose STOP rows; these are retained regressions. |
| [N4 playback](../n1_n4_2026-10-18/HOWTO.md) | Keyboard pause/rate changes and Pandar→Falcon switch verified over actual Docker/Humble DDS; no inherited STOP after reset. | Final conservative-profile and real Falcon transport run pending. Hosted CI is not claimed. |
| [N1 gauge](../n1_n4_2026-10-18/README.md) | Shared rail-relative box, supported extent, bounded 3D smoothing lag, explicit invalid hold and RViz marker lifetime. 83 real-browser checks passed. | Smoothing reduces far-range availability; coverage is reported alongside jitter. Final immutable-source display replay and isolated RViz run pending. |
| [N3 dust](../n3_dust_2026-10-18/README.md) | Deterministic return/attenuation generator, frozen-placement Set F harness, paired stress measurements and rejected filter evidence. Health-only platform experiment preserves every STOP and marks all medium/high frames degraded. | False-STOP acceptance fails. No physical dust sample or calibrated dust classifier; no suppression/health classifier enabled in production. Remaining complete battery results pending. |
| [N6 platform person](../n6_platform_2026-10-18/README.md) | Candidate improves first STOP 44.01→51.12 m, retains all original matched STOP rows and passes ten control-recording comparisons. Exact source attribution is recorded. | Default remains **off**: 60 m target unmet, nine added uncertain-box STOP rows widen false-alarm bound 0–38→0–47, and inserted-object occlusion hides contradictory farther rail evidence. Narrower-band follow-up was rejected by the raw geometry check. |

Falcon's ROS input is `+x` forward, `+y` left, `+z` up; the manual-native profile is separate.
There is no ring field, and about 2.1% of returns carry second-return flags. The original raw
recording reaches 509.97 m; the default runtime crop remains 250 m. Falcon small-object density
is uncalibrated, so the approved conservative C2 policy keeps its small-object-qualified clear
range at zero. It never borrows the Pandar density prior.

## Immutable integration source and validation

Runtime/configuration are frozen at `f5ff15f`, exported as a detached Git worktree at
`/home/resense/data/final_lidar_f5ff15f`. Orientation history is enabled with a four-frame/32 MiB
budget. N6 remains off and dust classification remains experimental. Subsequent evidence and
test-only commits do not change those runtime files. The [registered protocol](PROTOCOL.md)
predates candidate measurements and retains failed hypotheses.

The first full host suite reports **1,875 passed, five failed, eight unavailable-fixture
deselections and 12 subtests passed**. Four failures were limited to new clock/diagnostic
contracts in tests; the narrow test-only fixes passed all 51 affected tests. The unchanged
150 ms synthetic p95 limit measured 289.8 ms under concurrent load and requires an isolated
rerun. It has not been waived. The original test report is retained.

The full default gate and final X3 are pending. X3 uses the existing complete 1.1.0 baseline:
[reference preparation](x3_reference_preparation.json) reproduces every archived hash for all
3,133 source frames by changing ZIP container headers only, with no array/compressed-stream
changes, and revalidates all 40 archived raw entries. The live caches are unchanged.
No incomplete or failing run can establish a new detector seal.

## Hardware and measurement scope

This machine exposes **one CPU and approximately 4 GB RAM**. Quality replays share the machine;
their wall times and latency-health warnings do not establish throughput. Isolated Docker/DDS
and software-RViz measurements are reported separately, with playback rate, freshness and
drops. No 2-, 4- or 8-core throughput is inferred from this host.

The two deliveries and all tuning here are development data. Reviewed annotations retain
unknown gauge membership and sparse support; no organizer truth, held-out score or physical
dust robustness is invented. No organizer message or release was sent by this task.
