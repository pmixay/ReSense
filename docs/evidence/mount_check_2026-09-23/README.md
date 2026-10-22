# Mount calibration on re-mounted recordings, v0.6.2 against v0.6.3, 23 September

> **Purpose:** the raw output of `scripts/calib_check.py` on three recordings, each re-mounted by known
> rotations, before (v0.6.2) and after (v0.6.3): does the detector find the mount and how much tilt is left.
> **Audience:** team, jury · **Owner:** P1 (runs, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: the tilt / yaw residuals of the v0.6.3 files and the side-mount rows of both versions compared with the table of log §6;
the other columns (status, orientation, flag, seconds) read but not checked against any document ·
> **Status:** dated record

## 1. What was run, when

* `scripts/calib_check.py --npy <recording>`: a whole recording re-mounted by eight known rotations, a fresh
  detector over each ([EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §6, opening paragraph).
* Run date 23.09 from [`../README.md`](../README.md) section 2 (line 150); the files carry no date, machine or commit.
  The folder was committed on 2026-09-24 (`dfdebe5`), which is the commit date. Code: the labels `v062` / `v063` only;
  the log gives `c1c2b6a` for v0.6.3 (not resolvable in this checkout, unverified). Lane: not recorded in the folder or the docs.
* Which recording is which is not written in the files. The mapping `obs` = `doubleT_obstacle`, `rdt` = `roundT_doubleT`,
  `rsq` = `roundT_squareT_pressureGate_squareT` is inferred from the numbers: the log §6 table has the same residuals
  column by column (for example `obs` "as recorded" roll +3.02, pitch -0.88).

## 2. Result

On v0.6.3 every upright, inverted, +x-forward and backwards mount is found on all three recordings; the tilt residual is
0.00 to 0.49 deg (largest: `v063_rsq.txt`, "roll -2 pitch 3 yaw 2", tilt 0.49). The side mount (spin axis horizontal)
is not recovered: residual 83.03 deg in `v063_rdt.txt`, 88.54 in `v063_rsq.txt`, 84.33 in `v063_obs.txt`
(v0.6.2: 79.89, 90.00, 84.33 in the `v062_*` files). Each file takes 14.7-17.5 s per row in v0.6.3 except the side mount (27.6-43.9 s).

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §6 "Mount calibration on real frames": the table there
  (residual per re-mount, "83 deg; 80 deg before v0.6.3" and so on) matches these files on every cell I compared.
* The log does not cite the folder by name; the link is the index row only. No row of `DECISIONS.md`, `BACKLOG.md`,
  `SCORECARD.md`, `VM_GUIDE.md` or `CHANGELOG.md` names it.

## 4. Contents (6 files, 8 rows each)

* `v062_obs.txt`, `v062_rdt.txt`, `v062_rsq.txt`: v0.6.2 code.
* `v063_obs.txt`, `v063_rdt.txt`, `v063_rsq.txt`: v0.6.3 code.
* Columns per row: re-mount name, status (`ok`, `identity`, `provisional`), residual deg (tilt, yaw), recovered roll / pitch / yaw,
  orientation found, an `obstacle True/False` flag, seconds.

## 5. Caveats

* The `obstacle` flag is not defined in the folder. Unverified reading: whether the detector alarmed during the re-mounted run.
  On that reading `v062_obs.txt` shows `False` on 4 of 8 rows (as recorded, roll +3, pitch -4, combined) although that
  recording holds the object, and `v063_obs.txt` shows `True` on all 8. The log does not discuss this difference; it is reported, not explained.
* The side-mount rows are "provisional" or "ok" with a residual of 80-90 deg: the mount is not found, as log §6 says
  ("not supported"). The status word `ok` on `v063_rdt.txt` and `v063_rsq.txt` for that row must not be read as success.
* Log §6 describes the first version as v0.6.1 in its heading; these files are v0.6.2 and v0.6.3.
