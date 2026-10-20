# Regression gate for the 1.2.0 reseal with F1a and L16 (2026-10-20)

Full gate (`scripts/regression_gate.py --cache /data/cache --jobs 4`, no `--allow`, no `--set`) on
commit `cc6226e591bc788d273ee02eb2bb5f78fee4103f` (main's F1a rail-reference repair and L16 open-air
repair merged into the branch; detector files identical to the working tree) against
`docs/evidence/results/regression_baseline_2026-09-29_shell_off.json`. It replaces
`../gate_2026-10-20_reseal/` (commit `6bb6430`), whose sealed files main changed afterwards.

* Files: `gate_cc6226e.json` (the gate JSON the seal cites), `gate_table.txt` (the printed table).
* Result: `GATE PASS`, exit 0: 0 gated metrics worse, 0 missing, 8 better, 191 same, 25 informational
  rows changed (latency rows are never gated). The 8 better rows are the same as on `6bb6430`:
  `doubleT_platform` alarm events and STOP episodes, ride alarm events and STOP episodes, set O
  `thin_hanging` (STOP frames, first STOP, held from, 0-50 m bin).
* Ride: 111 alarm frames and 26 STOP episodes (on `6bb6430`: 102 and 24; baseline 126 alarm frames,
  30 STOP episodes). This is the ride trade-off main's F1a commit records; the gated rows still pass.
* Data and environment as in `../gate_2026-10-20_reseal/README.md` (six recordings, set O, the ride with
  its verified intake, set F straight; Python 3.13, open3d 0.20.0, native kernels rebuilt).

Checked independently of the gate: alarm frames and STOP episodes recounted from the per-frame results
of the six recordings and the ride with a separate loop; all equal the gate's values (ride 111 / 26,
`squareT_platform` 37 / 11, `doubleT_obstacle` 193 / 1, the other four 0 / 0).
`detector_freeze.py verify` fails after a one-line edit to a sealed file and passes after restoring it.

Not done here, so not claimed: the P4 review of what is enabled, X3 on this commit, the full Falcon
record. Manifest: `docs/evidence/detector_freeze_2026-10-20_1.2.0_f1a_l16.json` (`DEFAULT_MANIFEST`).
