# Registered control-import and witness-schema corrections

The corrected affected probes in `run-003` all passed: 58 boundary cases,
3,024 health combinations, 128 spare histories and 1,024 actual-Track cap cases.

Two independent `run-002` tasks require narrow follow-up:

1. The sealed-control process failed at import because that source deliberately
   has no new `wall_drift_range` / `FrameRays` symbols. Extract the unchanged
   owned `freeze`, `scene` and `scenes` function ASTs into a minimal runner with
   imports common to both versions. Run **only the missing control** scenes and
   compare them against the retained target-on/off results. No scene parameter,
   frame or detector setting changes.
2. The H3 auditor successfully authenticated/recounted all frames and reached
   its final witness equality assertion. `diagnose_witness.py` established that
   the compact promotion witness intentionally omits **only `points_idx`**;
   all common candidate fields are exactly equal, and the complete 49 raw
   indices remain in the capture. Compare its exact descriptor projection and
   separately assert the index count equals `n_raw`; keep the raw witness in the
   independent report. No numerical tolerance or result changes are allowed.

Retain the initial failed logs, dependent comparison failure and all existing
source/scripts. `run-004` records these follow-ups with exact commands and another
36-file before/after identity check. Same image and original Linux volume.
