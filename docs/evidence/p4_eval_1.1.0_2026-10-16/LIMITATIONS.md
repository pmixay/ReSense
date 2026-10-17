# Confirmed technical limitations of 1.1.0 — P4 evaluation, 16.10

For P2's captions and for P1/P3. "Confirmed" means **measured by P4 on the sealed 1.1.0 detector** in
this evaluation (node path, Linux runtime of the [report](README.md)), unless the row says it is cited.
Every number is in [export/numbers.csv](export/numbers.csv) with its source and JSON pointer. All
results are **in-sample**: the recordings and the organizers' set O were used in development; G3 has
not run. 1.1.0 equals v1.0.0 in every X3 metric and every judge-pipeline decision measured here, so
each limitation below applies to both versions.

## A. Detector limitations (measured)

| # | limitation | measurement (1.1.0) | source |
|---|---|---|---|
| L1 | **Small objects far away mostly never form a cluster.** Beyond ~100 m a 0.3–0.5 m object gives a few returns per frame; most frames have no corridor blob on it at all | X1: 372 of 448 `no_blob` rows are at ≥ 100 m. Range test A_cube05 (0.5 m cube on the straight): STOP in 0 of 76 visible frames at 150–260 m, 15 / 38 at 100–150 m, held ≥ 90 % only from **83.4 m** (first STOP 135.1 m). 0.3 m cube: first STOP **44.9 m** | [X1](../range_attribution_2026-10-16/README.md) |
| L2 | **Merging with structure costs range at 60–200 m.** The object's returns join an oversize cluster whose split is refused, or a wall-segment shape, and are dropped with it | X1: 222 rows `oversize_split_refused`, 138 `infra_wall_segment` (97 of them in one case, S_person_150) | X1 |
| L3 | **Start-up confirmation delays every new STOP** (hits, 0.5 s, hit fraction, confidence) | X1: 185 rows (`confirm_hits` 99, `confirm_time` 54, `hit_fraction` 20, `confidence` 12). The 5 cm hanging cable (E6): 28 of its 30 non-STOP rows are confirmation | X1 |
| L4 | **At a standing train, infrastructure holds withhold STOP on a static object** (`explained_run`, `column_hold`) | person at 100 m ahead of the standing train (S_person_100): STOP in **82 of 260** visible frames; 67 rows are `column_hold` (29), `explained_run` (24) or `demoted:column` (14) | X1 |
| L5 | **Far-field axis / height trust demotes to CAUTION** (`beyond_axis`, `beyond_height_ref`) | X1: 55 + 20 rows at 60–200 m. B_person (roundT_doubleT): first STOP **51.8 m**, held from 57.1 m | X1 |
| L6 | **Set O small and edge objects confirm late** (node path) | first STOP: small_on_rail **48.0 m**, small_center **55.8 m**, small_edge_inside **35.0 m**, big_edge_inside **28.2 m**, thin_hanging **30.1 m**. Inside rows with STOP: big_edge_inside 15 / 125, small_edge_inside 18 / 83, thin_hanging 15 / 42 | X3 1.1.0 nominal |
| L7 | **False STOP and CAUTION on empty track** | five empty bags, judge pipeline: **4 episodes / 13 frames STOP**; **CAUTION 49.1 %** of frames (1,123 / 2,287). Set O: big_outside (outside the envelope by intent) STOP in 9 rows / 1 episode; 6 unmatched single STOP frames | J1 dry run (v1.0.0) and pre-release 1.1.0 (0 changed decisions); X3 |
| L8 | **Robustness to perturbations is partial** | squareT false-STOP episodes: nominal 3 → pitch −2° 7, roll +2° 7, 5 Hz 9, dropout 30 % 10–14. doubleT_obstacle STOP frames: 193 → 154 (dropout, judge seed 7), 95 / 101 at 5 Hz. roundT-squareT: 0 false episodes in all ten variants | X3 1.1.0 |
| L9 | **High narrow object can stay `column`** (High miss, OPEN 8.1) | *cited, not re-measured by P4*: H4 selected-scope review | [h4_selected](../integration_2026-10-16/h4_selected/README.md) |

## B. Evaluation limitations (what the numbers can and cannot claim)

| # | limitation |
|---|---|
| E1 | **No held-out result.** Every number above is on development data. G3 (84 cases, 924 runs) is registered only; its single run is a separate future step on the final seal. |
| E2 | **J1 is not done on the release.** The judge score **66/100 is v1.0.0's**; the release J1 waits for H6/E1. The pre-release judge-pipeline rows are observations, not a score. |
| E3 | **X3 perturbation rows depend on the BLAS kernel.** With OpenBLAS's fallback kernels, an unchanged v1.0.0 changed 11 of 40 perturbed cases by a few STOP frames / one episode. Compare only within one runtime with `OPENBLAS_CORETYPE` pinned. Nominal rows did not move. |
| E4 | **Runtime is not the team VM.** Cloud container, 4 vCPU; timing (≈ 20 min per X3 battery) is informational. No latency claim comes from this evaluation. |
| E5 | **Ground truth is the team's own.** Labels of doubleT_obstacle and set O are made with team tools; set O and the range objects are synthetic (ray-cast); ICP odometry is not bit-reproducible (~1e-14 m). |
| E6 | **X1 attribution limits.** `no_blob` does not separate returns removed before clustering from DBSCAN noise; one cause per frame (first in code order). |
| E7 | **One input frame unexplained.** Windows H0 decoded cache of set O frame 332 differs from the Linux decode of the same archive; no measured effect. |
| E8 | **Gate path and node path differ.** The team's regression gate (compact16 cache) and the judge's node path give different hit counts and some first-STOP distances. Do not mix them in one chart. |

## C. Caption check: existing documentation vs 1.1.0 measurements

| document text | where | 1.1.0 node path (P4) | verdict |
|---|---|---|---|
| set O cubes 0.3 m on rail / centre: STOP from 48.0 / 55.8 m | README «Известные ограничения», ALGORITHM §6 | 47.96 / 55.84 m | **confirmed** |
| edge cube 35 m | README, ALGORITHM §6, ARCHITECTURE | 34.97 m | **confirmed** |
| hanging object 5 cm: 30 / 30.1 m | README, ALGORITHM §6 | 30.12 m | **confirmed** |
| 2 m edge box: **29 m** | ALGORITHM §6 (l. 720), ARCHITECTURE (l. 460), EXPERIMENTS (l. 117, 163, 279), REQUIREMENTS_MAP 8.2, SCORECARD (l. 276) | **28.21 m** | **update to 28 m** if the caption describes 1.1.0; 29 m is the 28.09 evaluation of the older detector |
| plank on rails: **87 m** | README result table, EXPERIMENTS (l. 163), REQUIREMENTS_MAP 8.2 | long_low_on_rails **88.97 m** | **update to 89 m** for 1.1.0 (87 m is the 28.09 older-detector value) |
| box at top of envelope: 111 / 111.5 m | README table, REQUIREMENTS_MAP 8.2 | big_above **111.42 m** | use **111.4 m** for 1.1.0 |
| 2 m box from its first appearance, 98 m | README table | big_center 98.16 m | **confirmed** |
| empty bags: 4 episodes / 13 frames (node path, 13.10) | SCORECARD / judge report | 4 / 13 on 1.1.0 pre-release | **confirmed** |
| CAUTION 43 % overall (13.10, incl. ride) | README | ride not re-run; five empty bags 49.1 % on both versions | **unchanged**; say "43 % incl. the ride (13.10)" or "49 % on the five empty recordings" |
| real person moved into 15 windows: stable STOP at 60 m in 11/15 … | README table, ALGORITHM §6, REQUIREMENTS_MAP | **not re-measured** (the ego veto makes that method inapplicable for moving-train windows, as the docs say) | keep its "28.09, older detector" label; do not present it as 1.1.0 |
| 1.1.0 fixes tall narrow objects | — | not claimed anywhere; L9 OPEN | **do not claim** |

P4 did not edit the shared documents. P1 / P3 own those files; this table is the proposed set of corrections.
