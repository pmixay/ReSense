# B4 prospective release acceptance — 2026-10-18

This protocol is committed before the release-candidate implementation and
release measurements. The earlier author protocol existed on disk but was not
committed before exploratory measurements. Those historical experiments remain
in `../b4_orientation_fix_2026-10-18/`; this document does not retroactively
preregister them. User has now authorized the ordered candidate / X3 / P4 /
P1 reseal / main integration workflow. Any blocking finding stops integration.

## Fixed inputs and acceptance

* Base: `3b7d7aa`; sealed reference checkout `1b88016`, with identical 36
  sealed files. Original six bags, Set O and full ride; reuse verified intake.
* Preserve the historical B4 protocol's criteria and 24-rotation ordering.
  Rerun all four baseline/candidate × empty/positive combinations on original
  float32 node-decoded caches. No wrong accepted mapping, no empty STOP, no GO
  before orientation confirmation, no lost matched positive STOP frames against
  the appropriate same-rotation or correctly oriented control.
* Resolve P4 B1: retain every orientation-voting observation eligible under
  `obs_spacing`, including `obs_spacing=1`; retain the elapsed frame-period
  cadence. Add a state-level test varying spacing, periods and time_cadence.
  Repeat P4's real `doubleT_obstacle` short-window reproduction:
  `frames=5`, `obs_spacing=1`, `provisional_min_deg=10`. Identity and recovered
  rotation 4 must preserve matched frame 8 and first STOP at frame 8.
* Resolve P4 N2's stronger-than-code evidence claim: require at least three
  resolved cone offsets, separated by >=0.005 in unit-ray coordinates (the
  existing overall minimum span remains 0.01). Two cone planes with three IDs
  must not supply an axis. This does not change the documented gravity/late-ring
  limitations. Do not expand the claim to Falcon or physical horizontal mounts.
* Run all affected tests including calibration, reseed, health, cadence,
  monitoring, timing, native kernels and gate/X3 validation. Run pinned CI lint,
  ROS parameter sync and diff checks. Preserve failures; do not waive them.
* Run full gate on exact committed candidate, and a fresh same-runtime sealed
  reference gate, default config, four workers, no overrides/allow-list,
  historical `regression_baseline_2026-09-29_shell_off.json`. Require exit 0,
  all 208 non-latency rows equal, 18,329 frames complete. Retain raw outputs and
  compare per-frame non-timing detector outputs, especially matched STOPs on
  real positive, Set O and Set F. Additive false orientation-conflict fields may
  be normalized explicitly; do not normalize decisions or object geometry.
* X3: standing `scripts/robustness_battery.py`, four full float32 caches, ten
  variants each, two workers, unchanged judge scripts. First measure sealed
  1.1.0 baseline; compare candidate against that complete raw-validated baseline.
  No more than +1 false STOP episode or 2 lost matched positive STOP rows per
  object/recording, with external/unmatched episodes separate. No overrides.
  Historical 1.0.0 judge reproduction is descriptive, not a 1.1.0 acceptance
  reference. Full gate and X3 run serially to avoid timing interference.
* Separate AI reviewer P4 must review the exact resulting source and per-frame
  evidence and explicitly close B1/B2 before P1 reseal. Retain its earlier
  blocking report and identify AI review accurately.
* P1: retain package 1.1.0 for this bugfix candidate, create a new seal from the
  accepted committed gate using the existing freeze tool, switch DEFAULT_MANIFEST,
  review the seal and verify it in clean checkout before/after native build.
  Version changes would require another committed-candidate gate.
* Commit accepted evidence, update current freeze/status documentation, run CI
  checks, integrate only the accepted branch into up-to-date main and push.

## Runtime / provenance

Python `/tmp/opencode/resense-b4-venv/bin/python`; NumPy 1.26.4; pinned ruff
0.15.8; native binary SHA-256
`67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394` on both sides.
`OPENBLAS_CORETYPE=Haswell`, OpenBLAS/OMP/MKL/NUMEXPR threads 1; task-local
EGL/OpenGL libraries in `LD_LIBRARY_PATH`. Explicit checkout import identity.
Record command, commit, source/config/input/runner hashes, native identity and
exit code for each acceptance run. Never replace historical author receipts
with new-source results. Archive fresh raw outputs and checksum them.
