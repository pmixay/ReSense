# Selected default: startup replay remains opt-in

The captain selected the previous default after the replay4 experiment lost 13 existing
Falcon STOP frames, including four associated with the person. Source
`cecab1b696b8c2e101207601acd8faed96c8bfb8` sets `orientation_replay_frames=0` in the class
and both synchronized YAML files. Explicit sensor profiles, the orientation-readiness
guard and bounded opt-in replay remain available. No acceptance criterion was relaxed.

[Source identity](runtime_identity.json) binds all 38 detector/configuration/build files,
the immutable checkout, the live tree and Git. The source digest is
`5eae5197cc6497b029665a19e85b28fb217e934d8a80928cba6c1d2c5ad51700`.
N6 rail-axis extension is off; the experimental dust observer is not called by the detector.

## Completed checks

| Check | Result | Evidence |
|---|---|---|
| Full host suite | 1,906 tests and 12 subtests pass; seven unavailable historical-fixture tests deselected | [Receipt](core_receipt.json), [JUnit](junit-core.xml) |
| Installed Docker image and real DDS | 40 Pandar + 100 actual Falcon inputs; all frame payloads match; pause/rate/profile reset verified | [Independent review](INDEPENDENT_DDS_REVIEW.md) |
| Full default gate | 18,329 rows; no overrides, waivers, missing gated rows or gated regressions | [Gate](gate.json), [execution](gate_execution_manifest.json) |
| Independent ordinary/Set F review | 15,269 ordinary rows retain all 805 STOP frames and 51 intervals; all 3,060 Set F scoring/placement rows match | [Boundary review](independent_gate_boundaries.json), [field review](gate_independent_review.json) |
| Full actual Falcon comparison | All 4,443 shared non-timing outputs match the fresh runtime-matched control; all 1,372 STOP frames and eight intervals retained | [Falcon review](../../n2_falcon_2026-10-18/falcon_default_off/README.md) |
| X3 robustness battery | All 40 cases / 29,765 rows / 260 checks pass; all 6,284 STOP frames and 204 intervals retained | [Complete raw comparison](X3_REVIEW.md) |

The [joint independent verdict](INDEPENDENT_ACCEPTANCE.md) and subsequent
[actual manifest review](MANIFEST_REVIEW.md) accept the
[38-file selected-source seal](../../detector_freeze_2026-10-18_lidar.json).
The built-in integrity verifier and 12 freeze tests plus six subtests pass. Earlier replay4
results retain their source identities and cannot substitute for the selected-default checks.

## Scope and retained limitations

The full gate uses the registered shell-off baseline and a separate same-runtime native
`9b92df5` control. All 208 non-latency comparisons match that control. Its 16 latency
comparisons improve under different concurrent load; they establish no speed improvement.
The only ordinary serialized additions are orientation-confirmed diagnostics. Legacy Set F
rows omit complete detections, so independent hit reassignment is not claimed.

The Falcon comparison retains the first failed exact-coefficient comparison against an
older capture. A fresh control with the same Haswell BLAS dispatch matches exactly without
tolerance. Every decision and STOP interval already matched the historical capture.

The Docker image is `resense:lidar-cecab1b`, ID
`sha256:eb53df868b1614937dcacda6dca2e37d32746a70b81f1dde030b8b2bc6b0ae02`.
Independent review checks the installed package from outside the source directory and
all 43 image-provenance files. Frame payload equality covers every non-timing field;
non-frame equality covers the documented selected safety transitions, not every watchdog
diagnostic or publication frequency. Playback tests use explicit sensor profiles and the
conservative range policy, separate from full automatic-orientation Falcon acceptance.

The one-CPU host's software-RViz demonstration at rate 0.5 and its display-coverage cost
remain separately identified [N1/N4 measurements](../../n1_n4_2026-10-18/README.md).
No 2/4/8-core or universal 10 Hz throughput is inferred. The complete Falcon sampling proxy
fails acceptance; corrected dust stresses also expose failures. N6 does not reach its
60 m target and remains off. No physical-dust validation, surveyed Falcon ground truth,
release, tag or deployment is claimed.

The current gate raw bytes are retained in [the archive](raw/gate.tar.gz) with the
[verified member manifest](raw/gate_manifest.json). The unchanged native control is in
the [earlier paired archive](../raw/gate_control_and_7b.tar.gz); its manifest identifies
control and rejected replay4 candidate members separately. Originals remain on the machine.
