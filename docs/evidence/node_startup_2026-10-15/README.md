# S1 node start-up: implementation notes and real-Docker acceptance (15.10 to 16.10)

> **Purpose:** the S1 candidate (freshness-first start-up catch-up and bounded pending memory), its
> registered Docker acceptance protocol, and the two measured matrices on the original bags, both FAIL.
> **Audience:** reviewers of the runtime selection, P1/P2 · **Owner:** P1 (`S1.md` header "Owner: P1") ·
> **Language:** EN
> **Last verified:** 2026-10-22: numbers checked against the named files, links resolve ·
> **Status:** historical; S1 not accepted and removed from the runtime (DECISIONS.md row 33)

## 1. What was run, when, by whom

* Lane P1, worktree `rs-p1-start` on a Windows machine with Docker Desktop / WSL2 (`DOCKER_PROTOCOL.md`,
  `docker/README.md`); branch name omitted. `S1.md` is dated 2026-10-15; original base `d0d17bb`,
  original S1 commit `a14ddd1`.
* Matrix 1, Windows bind mount: report titled 2026-10-15, node/launch commit
  `1eed357a82ac4bd8b5a33ff8d3902c8190b2edec` (`docker/README.md`).
* Matrix 2, Linux volume, warm cache: folder named 2026-10-16, README title says 2026-10-15; the raw root
  name carries `20261016`, so the exact day is unverified. Source `62d055f92a1628a3e8c1da8798887d9bb147b93d`
  (`docker/linux_volume_2026-10-16/README.md`), before the later decode-failure accounting fix
  (`../p1_start_2026-10-15/README.md`).
* Git: all files came in with import commit `44b462e` (2026-10-16), an import date, not the run date.

## 2. Result

Both matrices: **Acceptance FAIL**, 12/12 playback executions finished, strict evidence complete **false**;
no baseline measured, no improvement claim (both `docker/README.md` and `docker/linux_volume_2026-10-16/README.md`,
`summary.json` `improvement_claim_allowed`). Linux-volume medians (`docker/linux_volume_2026-10-16/README.md`):
360 degree README fresh 85 of 201 (target >= 180), README STOP 147 (>= 185), README first-STOP lag 2.163 s
(<= 1.2 s), 120 degree literal FAULT 16 (<= 10); literal fresh fraction 0.005 (>= 0.8). Windows-bind medians
(`docker/README.md`): README fresh 0 (>= 180), README STOP 190 (>= 185, pass), literal fresh fraction 0.000.

## 3. Supports

* [`DECISIONS.md`](../../DECISIONS.md) row 33: S1 FAIL, "16.10 S1 снят с runtime", published queue 40, startup step 0, lag 20 s kept.
* [`ARCHITECTURE.md`](../../ARCHITECTURE.md) (paragraph at about line 151) states S1 failed on the original bags.
* [`BACKLOG.md`](../../BACKLOG.md) line 255 (S1 listed as a failed, closed card) and line 592 (literal `ros2 bag play` gives stale results);
  [`CHANGELOG.md`](../../../CHANGELOG.md) line 296 ("S1 FAILED, runtime removed").
* [`../integration_2026-10-16/runtime_selection.md`](../integration_2026-10-16/runtime_selection.md) and
  [`../p1_start_2026-10-15/README.md`](../p1_start_2026-10-15/README.md) (P1 summary of both matrices).

## 4. Contents (70 files)

* `S1.md`: implementation notes, parameters, review corrections, status "not accepted".
* `DOCKER_PROTOCOL.md`: registered matrix (4 conditions x 3 repeats), scoring and targets.
* `docker_tools/` (8 files): driver pieces, listener, chain analysis, report publisher, bag-volume helper.
* `docker/` (9 files + `selected/`): Windows-bind matrix: `README.md`, `summary.json`, `manifest.json`,
  `condition_medians.json`, `runtime_observations.json`, `launch.json`, `cleanup.json`, hash indexes.
  `docker/selected/` (16 files): receipts and log excerpts of the first repetition of each condition.
* `docker/linux_volume_2026-10-16/` (11 files + `builds/` 4 files + `selected/` 20 files): the same set for the
  Linux-volume matrix, plus `bags_volume_verification.json`, `volume_stage.json`, and build receipts
  for two image builds.

## 5. Caveats

* **Not accepted, superseded by the runtime selection** above: neither matrix supports a speed or memory claim.
* The Linux-volume numbers measure `62d055f`, not later S1 code (`../p1_start_2026-10-15/README.md`).
* Full raw playback outputs live outside the repository (paths under a Windows scratch directory are named in
  the READMEs); only excerpts, receipts and hash indexes are here, so the medians cannot be recomputed from this folder.
* Run on Docker Desktop with 12 logical host CPUs, 4-CPU container quota; not an exact four-vCPU host (both READMEs).
