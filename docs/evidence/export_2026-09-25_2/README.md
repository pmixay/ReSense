# Image archive record from the second team VM (25.09, code 76bf24e)

> **Purpose:** the size and sha256 of the runtime-image archive built on the second team VM
> (confirmation run of 25.09 afternoon), which the offline rehearsal of that VM loaded.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: the four lines of `archive.txt` read; the sha256 and byte count
> compared with `../offline_2026-09-25_2/dry_obstacle.txt`; nothing re-run · **Status:** historical
> (superseded by `export_2026-09-28/`)

## 1. What was run, and when

* The `export_image.sh` step of [`VM_GUIDE.md`](../../VM_GUIDE.md) §4.5 on the second team VM, code
  `76bf24ebac2d586f092b7c7493a5cb363fa1bdf1` (`archive.txt` line 3; `76bf24e`).
* Run date: 2026-09-25. The file listing in `archive.txt` is stamped `Sep 25 15:03`; the only other
  time evidence is the neighbouring runs of the same VM (offline 15:14 to 15:18,
  `../offline_2026-09-25_2/steps.txt`; gate JSON created 15:27:31, `../gate_2026-09-25_2/gate_76bf24e.json`).
  The archive is named `resense-image-1.0.0.tar.gz`, i.e. the version label is 1.0.0.
* The git date of this folder is a merge date, not the run date. Lane: not recorded in the
  folder or the docs.

## 2. Result

`archive.txt` records: `resense-image-1.0.0.tar.gz`, 475515293 bytes, sha256
`262598a5…7615`, an unlabelled number 2075228485 (probably the unpacked image size, unverified, by
analogy with `../export_2026-09-25/archive.txt`).
The folder has no PASS line and no load step: that the archive is good rests on
`../offline_2026-09-25_2/dry_obstacle.txt`, where the same sha256 and 475515293 bytes are
checked and loaded, with commit label `76bf24e…` on the loaded image.

## 3. What it supports

* [`archive/EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) line 3161 lists this
  folder in the confirmation re-run and quotes "475 515 293 bytes" (matches `archive.txt`).
* [`archive/CAPTAIN_board_2026-09-28.md`](../../archive/CAPTAIN_board_2026-09-28.md) C25 (offline stand).
* [`evidence/README.md`](../README.md) section 2 row for the second team VM (`76bf24e`) says the
  export "PASS"; this folder alone does not show it (see 2).

## 4. Contents (1 file)

| file | what |
|---|---|
| `archive.txt` | `ls -l` line, sha256 line, commit, one unlabelled byte count |

## 5. Caveats

* Only the record of the archive; no log of the export or load (the load is in the offline folder).
* Superseded by [`export_2026-09-28/`](../export_2026-09-28/README.md).
