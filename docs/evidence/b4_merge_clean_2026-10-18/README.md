# Clean-checkout seal verification — 18 October 2026

The replacement 1.2.0 candidate seal at `e7cb270` passes in a fresh detached
checkout before and after building native code. The library actually loads;
the 38-file source fingerprint is unchanged. All 71 supporting references
also match both file hashes and the seal creator's committed Git blobs.

[Verification and exact commands](verification.json), [before](verify_before.log),
[build](native_build.log), [after](verify_after.log), [native loaded](native_loaded.log).
[Final checks](final_checks.json): 12 seal tests and six subtests pass, pinned
Ruff/archive policy passes, parameter files match, and the working seal passes.
[Measurement evidence](../b4_merge_reseal_2026-10-18/README.md) identifies the
measured source, raw recording results and remaining limits.

Later handoff documentation does not change the tested detector, manifest,
freeze verifier or hash-bound supporting evidence. Parent P4 reviews remain
attached to their original source commits; final review of the merged source
is pending. No release, tag, deployment or new J1 evaluation is claimed.
