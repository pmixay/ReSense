# Current-source runtime delivery verification

**PASS for delivery verification. Final detector quality acceptance remains on hold.**

The archive was built from `d480b1330491da838d6fb4996e34e37b3c060915`, containing the
P3d detector and implemented freshness controls. It does not contain M2 or T1.
All six jobs passed in [CI run 36275557220](https://github.com/pmixay/ReSense/actions/runs/36275557220).
Later commits update documentation and these receipts; the runtime source remains unchanged.

## Archive identity and checks

- [CI artifact download](https://github.com/pmixay/ReSense/actions/runs/36275557220/artifacts/10917252513):
  `resense-image-1.0.0-d480b13` (GitHub login required; expires 26 October 2026).
- Archive SHA-256: `385167aa23582ec965347ea75a39d855cd430d533b0a94389dab96042d2f3c73`.
- Loaded image: `sha256:4f79c1e3ece269d1187d03eaa7d74ef060f1ea7727cce69c71e3d661988754cd`.
- Local review tag: `resense:review-d480b13`.
- GitHub ZIP digest and contained archive checksum match. Offline loading succeeds.
- OCI revision/version match the source commit and package version 1.0.0.
- With `--network none`, ten source files match their Git blobs, including the installed
  detector package, actually imported ROS node, native source, configuration and harness files.
  Native kernels are available and enabled.
- The previous `resense:latest` image was restored and remains separately tagged.

The check finished at 22:43:06 UTC on 26 September 2026. The downloaded archive remains outside
Git under `/home/resense/validation/quality_cycle/current_source_ci/d480b1330491da838d6fb4996e34e37b3c060915/`.
No Git tag, GitHub release or PR merge is part of this verification.

This is separate from the failed combined M2/node original-bag experiment. Synthetic CI
replay and successful packaging do not resolve the clear-bag false STOP, late edge detection,
diagnostic range overclaims or weak generalization evidence. The internal combined score stays
64/100; see [the quality report](../../../QUALITY_CYCLE_2026-09-26.md).

## Receipts

- [Exact-source CI status](ci_status.json)
- [Download and checksum](download_receipt.json)
- [Offline image identity and restoration](offline_receipt.json)
- [Installed/imported source and native checks](native_source_receipt.json)
- [Expected source hashes](source_expected.json)
- [Earlier documentation-only follow-up](documentation_followup_receipt.json)
- [Offline load log](offline_load.log)
- [Executed verification helper](review_ci_artifact.py.txt)
- [Evidence hashes](manifest.json)
