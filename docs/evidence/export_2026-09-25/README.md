# Image export on the first team VM (25.09, code 7290873)

> **Purpose:** raw output of the runtime-image archive export and the load check on the first team
> VM, with the size and sha256 of the archive that the offline rehearsal of the same day loaded.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: every number below read from the named file in this folder; the
> links checked with `test -e`; nothing re-run (the VM is gone, the archive is not committed) ·
> **Status:** historical (the archive is of `0.6.3-7290873`; superseded by `export_2026-09-25_2/`
> and `export_2026-09-28/`)

## 1. What was run, and when

* `scripts/vm/run_plan.sh export` (the VM kit of 25.09, since removed from the repository, see
  [`VM_GUIDE.md`](../../VM_GUIDE.md) §4.5 for the current procedure) on the first team VM:
  8 vCPU = 4 physical cores, Ubuntu 22.04.5, Docker 29.8.1 (`meta.txt`).
* Run date: 2026-09-25, 09:43:59 to 09:53:09 UTC (`meta.txt`, `result.txt`). Code commit
  `72908737f2f8d1caf2b513f730abd930c8dac20d` (short `7290873`, `meta.txt`), clean worktree.
  No `--ref`: the image is tagged `0.6.3-7290873` (`notes.txt`).
* Date in git: this folder entered the repository with a later merge, so the git date is not the
  run date. Lane: not recorded in the folder or the docs.

## 2. Result

`export: PASS (… 550 s, commit 7290873, 8 vCPU)`; `export_image` PASS in 532 s and `load_check` PASS
in 18 s (`result.txt`, `steps.tsv`). Archive `resense-image-0.6.3-7290873.tar.gz`: 475489127 bytes,
sha256 `98be33db…0ed84` (full value in `archive.txt` and the `.sha256` file); 2075079161 bytes
unpacked (`archive.txt`). `load_check.txt`: the sha256 matched, `docker load` restored the images,
and the loaded image ran with `--network none`.

## 3. What it supports

* [`vm_2026-09-25/summary.md`](../vm_2026-09-25/summary.md) row "export" points here for size and
  sha256 (CAPTAIN actions 14b / 16 and §5).
* The archive is the one loaded in [`offline_2026-09-25/`](../offline_2026-09-25/README.md)
  (`load_image.txt` there repeats the same sha256).
* [`archive/EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) line 3148 cites this folder
  ("loaded in 29 s after every image was deleted"; the 29 s is `offline_2026-09-25/result.txt`, not
  this folder).
* No DECISIONS, BACKLOG or SCORECARD row names this folder (grep, 2026-10-22).

## 4. Contents (10 files)

| file | what |
|---|---|
| `archive.txt` | name, bytes, sha256, commit, unpacked bytes, Docker version, original path |
| `resense-image-0.6.3-7290873.tar.gz.sha256` | the sha256 line only (the archive itself is not committed) |
| `result.txt`, `steps.tsv` | PASS lines and per-step exit codes and seconds |
| `highlights.txt`, `notes.txt` | short extracts of the above |
| `meta.txt` | machine and commit facts |
| `export_image.txt` | build log of `scripts/export_image.sh` (Docker build output, long) |
| `load_check.txt` | sha256 check, `docker load`, offline smoke test |
| `run_log.txt` | the whole run log (meta + both steps) |

## 5. Caveats

* Superseded: the archive is `0.6.3-7290873`, not a release; later archives are
  [`export_2026-09-25_2/`](../export_2026-09-25_2/README.md) (`76bf24e`) and
  [`export_2026-09-28/`](../export_2026-09-28/README.md) (`464f5bc`).
* Paths in the files (`/home/mdm/...`) are the VM's; they do not exist in the repository.
