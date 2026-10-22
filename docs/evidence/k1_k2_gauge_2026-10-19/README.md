# K1 / K2 gauge stability on curves: P3 lane versions v1 to v5, reviews, P4 package (19.10)

> **Purpose:** the record of the K1 (gauge stability at standstill) and K2 (curve axis) lane of 19.10: the
> pre-registered protocol, five candidate versions with their full gate/X3/probe rows, two independent reviews, and the
> package handed to P4 after K2 was switched on and then held off.
> **Audience:** jury, P2/P3 (later K1/K2 work), captain · **Owner:** P3 lane for the code and measurements;
> `P4_PACKAGE.md` is the handoff to P4 · **Language:** EN
> **Last verified:** 2026-10-22: links resolve; `SHA256SUMS` checked (100 of 105 entries read OK, see section 5);
> gate-failure counts below re-read in the `gate_*.txt` files · **Status:** historical; K1/K2 stay off in 1.2.0 and
> later K2 work supersedes v3 to v5 (section 5)

## 1. What was run, when, by whom

* Lane P3, 19.10, base `aec88d2`, branch name omitted. Versions: v1 (`4068f0d`, failed), v3 `83c8894`, v4 `7dbdd64`
  (stopped, `HANDOFF.md` ~13:55 UTC), v5 `a82c86a` (time-boxed, 16:15 to 18:55 UTC, `V5.md`; measured against
  `b2c523a`). The protocol is `PROTOCOL.md` (revisions 1 to 4, committed before the candidate measurements).
* Reviews of 19.10 by fresh subagents: `REVIEW.md` (code `aec88d2..f07f5dd`, v2) and `REVIEW_v3.md` (v3).
* `P4_PACKAGE.md`: handoff to P4 after the captain's K2 decisions of 19.10 evening (DECISIONS rows 43, 44); a
  5-line "20.10 correction" was added by P4 (commit `8c2bf51`, 2026-10-20). The rest of the folder came with
  squash commit `0acb18c` (2026-10-19, "(#42)").
* Environment: `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, numpy 1.26.4, shared 4-vCPU container (`HANDOFF.md`, `V5.md`).

## 2. Result

* v3 (`REPORT.md`): "Ship OFF"; fails the full gate and 10 of 17 primary rows; curve axis error at 80 to 120 m down 2 to 7 times.
  Gate failures, counted in the gate texts: v3 12 gated metrics worse (`results/gate/gate_cand3.txt`), v4 19 (`results/v4/gate_cand4.txt`),
  v5a 12 (`results/v5/gate_v5a.txt`), v5b 8 (`results/v5/gate_v5b.txt`); the same table is `results/v5/gate_table.md`.
* v5b was the least-bad variant, "switch on v5b" with the gate exception for set O `small_center` first STOP 55.8 to 52.5 m
  (`V5.md` section 1, `results/v5/gate_table.md`). X3: 10 of 260 comparisons worse (`V5.md`, `results/v5/x3_summary.txt`).
* Held off the same evening because the whole Falcon recording showed the person stopped later (DECISIONS row 44 quotes first STOP
  124.8 to 113.0 m and 158 of 1,360 person STOP frames lost). The `P4_PACKAGE.md` correction re-scored this to 122.27 m and 37 frames.

## 3. Supports

* [`DECISIONS.md`](../../DECISIONS.md) rows 43 (K2 variant B on) and 44 (K2 held off); [`CAPTAIN.md`](../../CAPTAIN.md) lines 177 to 178;
  [`BACKLOG.md`](../../BACKLOG.md) K1/K2 rows at lines 165, 192, 400 ("off in 1.2.0"); [`integration_2026-10-19`](../integration_2026-10-19/README.md).
* Folder front page: [`../README.md`](../README.md) line 37 (the four agent lanes of 19.10).

## 4. Contents (102 files)

* `PROTOCOL.md`, `REPORT.md` (v3), `V5.md`, `HANDOFF.md` (stopped v4), `REVIEW.md`, `REVIEW_v3.md`, `P4_PACKAGE.md`, `SHA256SUMS` (105 entries).
* `results/` (56): gate/X3/probe/B6/Falcon rows per version (`gate/`, `v1/`, `v4/`, `v5/` with 24 files, `b6/`, `k15/`, `k2wall/`, `range/`,
  `falcon/`), two config patches, `x3_base.json`, `x3_cand3.json`, `raw_v3.tar.xz`, `v5/raw_v5.tar.xz` (per-frame raw data), `sq450_topview.png`.
* `scripts/` (9) and `scripts/v5/` (23): analysis, table and driver scripts; `tools/` (6): copies of the judge/range tools used.

## 5. Caveats

* **Superseded.** K2 later work: [k2_v5c_2026-10-20](../k2_v5c_2026-10-20/README.md) (v5c, the correction above), the repair record
  [k1_k2_repair_2026-10-20](../k1_k2_repair_2026-10-20/README.md), reviews [k1_k2_review_2026-10-20](../k1_k2_review_2026-10-20/README.md) and
  [k1_k2_review_2026-10-21](../k1_k2_review_2026-10-21/README.md), and [k1_k2_2026-10-21](../k1_k2_2026-10-21/README.md)
  (switch `track.axis_joint_union` "stays OFF"). `BACKLOG.md` line 165: K2/K1 off in 1.2.0.
* **Discrepancy with a doc (not fixed):** DECISIONS row 44 still quotes 113.0 m and 158 frames, which `P4_PACKAGE.md` and
  `k2_v5c_2026-10-20/README.md` (lines 24 to 25) call overstated by the scorer's lateral match.
* **Missing files:** `SHA256SUMS` lists `results/k2wall/k2_1_base_cand3.jsonl` and `results/ride/ride_episodes.jsonl`, absent here
  (3 other missing entries are `.pyc` files). The helper scripts in `/opt/work/` named in `HANDOFF.md` are not in the repository.
* v5 numbers are against `b2c523a` with all switches off; the decision-row figures on the integration commit were measured elsewhere (row 43).
* Data (Google Drive, Yandex) is external; nothing was rerun for this README, all figures are copied.
