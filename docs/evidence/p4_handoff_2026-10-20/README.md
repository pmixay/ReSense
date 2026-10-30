# P4 data handoff of 20.10: tasks that need the recordings, and the override runner

> **Purpose:** the written handoff from the P4 cloud session (no data access) to an agent that can
> download the recordings: data sources, four ordered tasks (T1 to T4) with criteria, and the small runner
> `judge_runner_set.py` used by later P4 measurements.
> **Audience:** the data-holding agent, P3, P2, captain · **Owner:** P4 (HANDOFF.md names "P4 (Pavel)") ·
> **Language:** EN
> **Last verified:** 2026-10-22: links and the cited rows checked, numbers below copied from the named files ·
> **Status:** historical instructions; T1, T2/T3 and T4 were executed later, see section 3. The handoff itself holds no measured results.

## 1. What was run, when, by whom

* Nothing was measured for this folder. `HANDOFF.md` says it comes from "the P4 cloud session of 20.10, which
  had no data access (proxy 403)", so its checks are on committed files and synthetic scenes only.
* Dates: first committed in `8c2bf51` (2026-10-20, PR #43 merge) and updated in `111d613` (2026-10-20, "re-check
  after PR #43 merged ... synthetic re-check of the F1a repair (#44)"). These are authoring dates, not import
  dates. Code stop in the text: 20.10 23:59 MSK (DECISIONS.md row 42).
* `scripts/judge_runner_set.py` (29 lines) wraps `judgement_2026-10-13/scripts/judge_runner.py` and applies
  `--set section.key=value` overrides to its `NodeReplica`. `HANDOFF.md` says it was "smoke-tested here without a bag,
  not yet run on one" (state at 20.10). Later runs that used it: `../p4_dust_markers_final_2026-10-20/README.md`
  and `../l16_exposure_2026-10-20/README.md` (not checked by me beyond the references).

## 2. Result

No measurement result. One checked statement: with every K2 switch off, `8c2bf51` equals `a5b0ede` on 180
synthetic frames (`HANDOFF.md`, section 0 "State"); "not yet checked on the recordings" (same place), so
unverified on real data. Data sizes in the table of section 1 of `HANDOFF.md` (3.7 GB, 17.1 GB, 1.75 GB, 6.76 GB,
2.53 GB) are quoted by the handoff, not rechecked.

## 3. Supports

* Tasks and where each was answered:
  T1 (L16/S3 open-air FAULT exposure): [l16_exposure_2026-10-20](../l16_exposure_2026-10-20/README.md) (answer: smallest
  share above the sensor in the first 10 frames is 28.3 %, cue fires below about 1.5 to 2 %) and
  [l16_acceptance_2026-10-20](../l16_acceptance_2026-10-20/README.md);
  T2/T3 (K2 v5c rows, tunnels cube): [k2_v5c_2026-10-20](../k2_v5c_2026-10-20/README.md);
  T4 (F1a exposure): [f1a_exposure_2026-10-20](../f1a_exposure_2026-10-20/README.md) and
  [f1a_acceptance_2026-10-20](../f1a_acceptance_2026-10-20/README.md).
* [`BACKLOG.md`](../../BACKLOG.md) links it as "[data handoff]" (line 102), and as "T2/T3 in handoff" in the K2/K1 cards (lines 165, 192, 410).
  `../k1_k2_repair_2026-10-20/PROTOCOL.md` item 2 points to it for obtaining the raw bags.

## 4. Contents (2 files)

* `HANDOFF.md`: state of `main`, data table, tasks T1 to T4, report format.
* `scripts/judge_runner_set.py`: the jury runner with config overrides, for evaluation of off-by-default switches without editing `configs/`.

## 5. Caveats

* The "State" paragraph of `HANDOFF.md` is a snapshot of 20.10 (main `8c2bf51`, later updated for the F1a repair at `f07f4b8`);
  `BACKLOG.md` line 654 pins the handoff at commit `972d19a`, which is not an object in this checkout, so whether that version equals this file is unverified.
* The Google Drive and Yandex links are external and were not opened; the dataset is not available to this checkout.
* K2/K1 work was transferred to P2 by the captain on 20.10 and decided off in 1.2.0 (`BACKLOG.md` line 165); T2/T3 are inputs only.
