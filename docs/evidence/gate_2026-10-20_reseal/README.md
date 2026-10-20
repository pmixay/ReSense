# Regression gate for the 1.2.0 reseal (2026-10-20)

Full gate (`scripts/regression_gate.py --cache /data/cache --jobs 4`, no `--allow`, no `--set`) on
commit `6bb643045eeb68563fdeae8381a76fafb7f65ca0` (detector files identical to the working tree),
against `docs/evidence/results/regression_baseline_2026-09-29_shell_off.json`.

* Files: `gate_6bb6430.json` (the gate JSON the seal cites), `gate_table.txt` (the printed table).
* Result: `GATE PASS`, exit 0: 0 gated metrics worse, 0 missing, 8 better, 190 same, 26 informational
  rows changed (latency rows are never gated). Better: `doubleT_platform` alarm events and STOP
  episodes 1 -> 0; ride alarm events 27 -> 18 and STOP episodes 30 -> 24; set O `thin_hanging`
  STOP frames 15 -> 18, first STOP 30.1 -> 35.1 m, held from 31.8 -> 40.0 m.
* Data: six recordings, set O, the 20-minute ride (221 splits, 11 271 frames; archive size and
  SHA-256 verified at intake by `scripts/cache_extended_ride.py`), set F straight (needs open3d).
* Environment: Python 3.13, open3d 0.20.0, native kernels rebuilt, `OPENBLAS_CORETYPE=Haswell
  OMP_NUM_THREADS=1`.

Checked independently of the gate: alarm frames and STOP episodes recounted from the per-frame
results of the six recordings and the ride with a separate loop; all equal the gate's values
(ride 102 / 24, `squareT_platform` 37 / 11, `doubleT_obstacle` 193 / 1; the counter finds the non-zero
cases, so the zeros elsewhere are real). `detector_freeze.py verify` fails after a one-line edit to
a sealed file and passes after restoring it.

Not done here, so not claimed: the P4 review of the 19.10 switches, X3 on this commit, the full
Falcon record. An earlier attempt on the same commit ran without set F (open3d was missing), failed
the gate with 15 missing set F rows and was discarded.

Manifest: `docs/evidence/detector_freeze_2026-10-20_1.2.0_reseal.json` (`DEFAULT_MANIFEST` points to it).
