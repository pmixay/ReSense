# Image export and load on the team VM (28.09, code 464f5bc)

> **Purpose:** raw output of `export_image.sh` and `load_image.sh` in the full VM run of 28.09:
> the size and sha256 of the `resense-image-1.0.0.tar.gz` archive built from `464f5bc`, and the
> check that it loads and starts without a network.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from the named files; the byte count and sha256
> compared with `../offline_2026-09-28/steps.txt`; nothing re-run · **Status:** historical (the
> image of the detector that the 28.09 judgement measured; later seals have their own images)

## 1. What was run, and when

* VM_GUIDE §4.5 (`scripts/export_image.sh`, then `scripts/load_image.sh`) on the team VM of
  [`../vm_2026-09-28/`](../vm_2026-09-28/summary.md), code
  `464f5bc6b193ff3dcc4bd7d30b03745d8d260f6a` (`archive.txt`, `export.txt` "git archive of 464f5bc…").
* Run date: 2026-09-28; the step ran from 17:05:36 to 17:09:05 in the chain log
  (`../vm_2026-09-28/chain.txt`); `archive.txt` stamps the archive `Sep 28 17:08`.
* The git date of this folder is the merge date of the VM-run PR, not the run date. Lane: the
  summary says the run was made "by an agent over SSH" (`../vm_2026-09-28/summary.md`); which lane
  is not recorded.

## 2. Result

* Archive `resense-image-1.0.0.tar.gz`: 475947817 bytes, sha256 `1019cd3c…a9d8` (`archive.txt`;
  full value there and in `load.txt`). The README index quotes the same 475 947 817 bytes.
* `load.txt`: sha256 OK, `docker load` restored `resense:1.0.0`, `resense:latest` and the base image,
  version label `1.0.0`, commit label `464f5bc6…`, and the image ran with `--network none`
  (native kernels `_resense_native…so`, `detector_node` present); final line `PASS`.
* `archive.txt` also holds a bare number 2077147662 (unlabelled; probably the unpacked image size,
  unverified).

## 3. What it supports

* [`../vm_2026-09-28/summary.md`](../vm_2026-09-28/summary.md) table row "§4.5 export and load"
  (PASS, 475 947 817 bytes).
* [`../README.md`](../README.md) section 2 row for `export_2026-09-28/`.
* [`../../VM_GUIDE.md`](../../VM_GUIDE.md) §4.0 checklist row for §4.5 (evidence `export_<date>/archive.txt`).
* The same archive is loaded in [`../offline_2026-09-28/`](../offline_2026-09-28/README.md).
* No DECISIONS, BACKLOG or SCORECARD row names this folder (grep, 2026-10-22).

## 4. Contents (3 files)

| file | what |
|---|---|
| `archive.txt` | `ls -l` line, sha256, commit, one unlabelled byte count |
| `export.txt` | build and save log of `export_image.sh` (long Docker output) |
| `load.txt` | sha256 check, `docker load`, offline smoke test, `PASS` |

## 5. Caveats

* The image holds the detector of 27.09 (`464f5bc`), not a later seal.
* The archive itself is not committed; only its record.
* The sha256 differs from the two 25.09 archives, as expected (different code).
