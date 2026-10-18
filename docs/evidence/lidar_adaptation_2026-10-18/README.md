# LiDAR adaptation — integration record, 18 October 2026

Work continues on `work/n5-labels-c2-acceptance`. At the captain's request, the temporary
`work/lidar-n2-n4-n1-n3-n6` branch was deleted locally and remotely while preserving its work.
Remote `main` was fetched again and remains `3b7d7aa7cbbf238c21f84330497697da131b7cb9`, already
an ancestor of this branch. This is development integration, not a release. The captain's
standalone map remains `/home/resense/P1_work_map_2026-10-17.md`, outside this repository.

## Work other members can use

| Dependency | Delivered | Remaining acceptance |
|---|---|---|
| P2 display/demo | Shared bounded gauge/status contract; complete 2,308-frame display replay; 140/140-frame same-node Pandar→actual-Falcon check; measured software RViz at rate 0.5; operator commands | Far-range display coverage cost is explicit; hosted CI/release remain deferred |
| P4 evaluation | Complete verified Falcon cache, reviewed raw target associations, immutable comparison harnesses and all N6 control captures | Full default gate, X3 and Falcon proxy gate |
| P1 integration | Explicit sensor profiles, orientation readiness guard and bounded startup history replay | Final gate, independent review and new source seal |
| Release | Branch work and local validation | Captain's hosted CI/quota repair and later release decision |

## Current result by card

| Card | Implemented and measured | Limit or regression |
|---|---|---|
| [N2 Falcon](../n2_falcon_2026-10-18/README.md) | All 4,443 frames verified; explicit ROS/native profiles agree throughout; automatic mapping matches after initial unconfirmed FAULT. Eight supported automatic orientations retain all 193 real-obstacle STOP frames, first at frame 8. | Reviewed person first STOP improves about 124.67→127.07 m, while static 115 m structure STOP associations increase 13→29. No surveyed corridor truth resolves those static alarms. Deduplication/channel thinning and the Falcon sampling proxy lose STOP rows; these are retained regressions. |
| [N4 playback](../n1_n4_2026-10-18/HOWTO.md) | Conservative-profile Docker/Humble DDS and native PTY controls pass: 40/40 Pandar then 100/100 actual Falcon frames in one node; pause/resume, rate 0.5→0.4, reset/expiry and no inherited STOP. Known `/iv_points` is subscribed before playback. | Actual Falcon has null small-target coverage/zero qualified clear range. Hosted CI is not claimed. Failed schema and 94/100 discovery attempts are preserved before the corrected strict-count pass. |
| [N1 gauge](../n1_n4_2026-10-18/README.md) | Shared rail-relative box, supported extent, bounded 0.25 m 3D lag, explicit invalid hold and RViz lifetime. All 2,308 immutable replay frames pass visible-edge jitter/bounds/result-preservation checks; no GO/STOP outline disappears. 83 real-browser checks and actual software RViz pass. | Median displayed/support ranges are Set O 86/130.15 m, person 139/151 m, curve 52/141.9 m and platform 45/120 m. Only 11/251 curve pairs show the 120 m edge; hidden far geometry is not claimed accurate. |
| [N3 dust](../n3_dust_2026-10-18/README.md) | Deterministic return/attenuation generator, frozen-placement Set F harness, paired stress measurements and rejected filter evidence. Health-only platform experiment preserves every STOP and marks all medium/high frames degraded. | False-STOP acceptance fails. No physical dust sample or calibrated dust classifier; no suppression/health classifier enabled in production. Remaining complete battery results pending. |
| [N6 platform person](../n6_platform_2026-10-18/README.md) | Candidate improves first STOP 44.01→51.12 m, retains all original matched STOP rows and passes ten control-recording comparisons. Exact source attribution is recorded. | Default remains **off**: 60 m target unmet, nine added uncertain-box STOP rows widen false-alarm bound 0–38→0–47, and inserted-object occlusion hides contradictory farther rail evidence. Narrower-band follow-up was rejected by the raw geometry check. |

Falcon's ROS input is `+x` forward, `+y` left, `+z` up; the manual-native profile is separate.
There is no ring field, and about 2.1% of returns carry second-return flags. The original raw
recording reaches 509.97 m; the default runtime crop remains 250 m. Falcon small-object density
is uncalibrated, so the approved conservative C2 policy keeps its small-object-qualified clear
range at zero. It never borrows the Pandar density prior.

## Immutable integration source and validation

The corrected detector/configuration are frozen at `7b7b02c`, exported as a detached worktree at
`/home/resense/data/final_lidar_7b7b02c`. Orientation history is enabled with a four-frame/32 MiB
budget. N6 remains off and dust classification remains experimental. The final node/launch
intake correction is `00ee76f`: pre-subscribe known `/iv_points` and require exact bag frame
counts in the integration harness. Initial display/transport and full-host results used core
`f5ff15f`. Accepted actual Falcon transport uses image `3ddf27362e5d`; matched headless/RViz
measurements use the preceding `a018d39a2369` image with the same f5 detector and gauge implementation.
The corrected-core image `acbd890efa86` also passes the strict 140-frame check. Independent
comparison preserves every semantic frame payload and reset transition against `3ddf27362e5d`;
only measured time/resource values are excluded. Its 100 actual Falcon frames separately match
the full offline explicit-ROS capture. The [corrected-image evidence](../n1_n4_2026-10-18/final_core_7b7b02c/payload_comparison.json)
retains exact image/source identities and every comparison field.
The [source/image receipt](../n1_n4_2026-10-18/final_core_f5ff15f/node_intake_followup.json)
keeps these phases distinct. The [registered protocol](PROTOCOL.md)
predates candidate measurements and retains failed hypotheses.

Independent review subsequently found that copied nested metadata can occupy more memory than
its input containers. Correction `7b7b02c` reserves that growth, charges separately copied aliases
independently, and checks actual retained storage before accepting a buffer entry. The original
reproduction is rejected before copying; 149 affected tests pass. Independent ordinary-input
checks preserve saved obstacle/Falcon arrays and replay behavior exactly. The earlier f5 gate
was interrupted and preserved; a fresh full default gate and X3 run measure corrected source.
The [source identity](runtime_identity_metadata_fixed.json) records all 38 files and verifies
the same enabled native library. Earlier source/image captures are not relabeled as this revision.

The first full host suite reports **1,875 passed, five failed, eight unavailable-fixture
deselections and 12 subtests passed**. Four failures were limited to new clock/diagnostic
contracts in tests; the narrow test-only fixes passed all 51 affected tests. The unchanged
150 ms synthetic p95 limit measured 289.8 ms under concurrent load, then passed at 10.4 ms
with quality jobs paused; it was not waived. The quiet full host suite before the metadata correction passed
**1,884 tests plus 12 subtests**, with seven unavailable historical-fixture deselections,
in 108.57 s, exit 0. The full node suite separately passed all 146 tests after the intake
correction. [Final JUnit](junit-core-final.xml) and [source/command receipt](core_final_receipt.json)
retain the tested scope; the original failed report remains available.

After the metadata correction, the complete quiet suite passes **1,890 tests plus 12 subtests**,
with the same seven unavailable historical-fixture deselections, in 108.20 s, exit 0.
See [corrected-source JUnit](junit-core-metadata-final.xml), [command/source receipt](core_metadata_final_receipt.json)
and the [second isolated window](isolated_window_metadata_fixed.json). All quality jobs resumed afterward.

The N1 replay wrapper returned external SIGTERM/exit143 when collected, while all four
reports and complete gzip streams were present. Independent artifact validation confirms
all 2,308 frame rows, hashes and numeric checks; the wrapper status is disclosed and is not
represented as exit0. Replay wall times include an intentional pause and are not benchmarks.

The full default gate and final X3 are pending. X3 uses the existing complete 1.1.0 baseline:
[reference preparation](x3_reference_preparation.json) reproduces every archived hash for all
3,133 source frames by changing ZIP container headers only, with no array/compressed-stream
changes, and revalidates all 40 archived raw entries. The live caches are unchanged.
No incomplete or failing run can establish a new detector seal.

## Hardware and measurement scope

This machine exposes **one CPU and approximately 4 GB RAM**. Quality replays share the machine;
their wall times and latency-health warnings do not establish throughput. Isolated Docker/DDS
and software-RViz measurements are reported separately. At rate 0.5, the same 70 curve frames
arrived in both headless and software-RViz runs: 69 fresh plus the expected initial epoch
fault, with zero drops/catch-up skips. Every corresponding decision, detection, warning,
track, clear range and gauge field was identical. Node latency p95 rose 54.5→99.8 ms;
source-age p95 rose 61.8→132.3 ms (RViz maximum 239.4 ms, below the 500 ms freshness limit).
Detector-container mean CPU rose 0.16→0.67 cores and peak memory 156→478 MiB, excluding
player/observer/Xvfb/capture. These are single local runs with quality jobs paused. The
[unedited actual screenshot](../n1_n4_2026-10-18/final_core_f5ff15f/curve_rviz_rate_05/curve_rviz.png)
and [matched comparison](../n1_n4_2026-10-18/final_core_f5ff15f/headless_vs_rviz.json) are retained.
Rate 0.5 is demonstrated; no 10 Hz or 2-, 4- or 8-core throughput is inferred from this host.

The two deliveries and all tuning here are development data. Reviewed annotations retain
unknown gauge membership and sparse support; no organizer truth, held-out score or physical
dust robustness is invented. No organizer message or release was sent by this task.
