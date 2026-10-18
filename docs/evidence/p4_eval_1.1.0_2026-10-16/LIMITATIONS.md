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

## D. Added 17–18.10: the extended data, the second lidar, the gauge (observation, development data)

Measured by P4 on 1.1.0 **and** 707ea9c with the same node replica and runtime. All decisions and all track-model
metrics are identical between the two versions. The one difference is the range the node *reports* (L10, L14).
None of these rows is a held-out result.

| # | limitation | measurement | source |
|---|---|---|---|
| L10 | **The gauge does not follow curves.** The fitted curvature is 2–4× too small on a curve of radius ≈ 400 m, so far ahead the gauge runs off the outside of the curve, inside the range the detector trusts and reports | `roundT_doubleT`: walls (raw points) and ICP agree on curvature −0.0023 … −0.0027 /m; detector −0.0006 … −0.0011. Axis off the driven path by **1.8 m at 90 m, 7.4 m at 135 m** (median); **40 % of the reported range is > 1.05 m off** (both versions). Smaller elsewhere: `squareT_platform_squareT_switch` 0.66 / 2.5 m, `synthetic_tunnels` 0.37 / 2.9 m at 90 / 135 m | [B6](../gauge_stability_2026-10-18/README.md) |
| L11 | **Where no wall runs parallel to the track (platform halls), the trusted axis range falls to 45 m and the heading can follow a converging wall** | synthetic person (`synthetic_platform`): visible from 249.5 m, a candidate from ~200 m, demoted `beyond_axis` until inside 45 m, **first STOP 44.0 m** (147 / 147 demoted rows checked from snapshots; branch traced: no boundary → `rails_range[1] + axis_valid_margin` = 45 m). `doubleT_platform`: heading follows a wall converging at 2° (8–25 m). `synthetic_platform`: 40 % of the reported range > 1.05 m off | [A5](../synthetic_labels_2026-10-17/README.md), [B6](../gauge_stability_2026-10-18/README.md) |
| L12 | **On the Falcon (second lidar) the node is in CAUTION almost all the time at a standing train in an empty tunnel** | whole recording, one detector: CAUTION **99 % (0–98 s), 99.8 % (98–241 s)** from two static warnings at 105.6 m and 115 m; false STOP 4 frames on the 115 m object; a probable false STOP of 8 frames on a floor patch at 9.4 m at the end (cause unverified). A person walking in the track is a STOP from 121–125 m (warning from 139 m), held to 6 m: correct | [B2](../falcon_full_2026-10-18/README.md), [extended data](../extended_data_2026-10-17/README.md) |
| L13 | **Thresholds are tuned on doubled Pandar points** (dual-return copies); single-return sensors such as the Falcon get half the evidence per ray | *cited*: judge de-duplication 13.10, doubleT_obstacle STOP 193 → 189, platform CAUTION 51 % → 11 %; reproduced in X3 (`dedup` 189) | [Falcon README](../../sensor/falcon_prime/README.md) F4, X3 |
| L14 | **The gauge edge flickers at 80–120 m** more than the proposed display target (N1) | Set O, motion-compensated frame-to-frame edge change p90: **0.04 / 0.13 / 0.30 m** at 40 / 80 / 120 m (N1 target ≤ 0.05 / 0.08 / 0.15 m). The trusted range halves and recovers within 1 s 0–22 times per recording; no frame is without a gauge | [B6](../gauge_stability_2026-10-18/README.md) |
| L16 | **A lidar mounted on its side (rolled 90°) can pass the mount check on a tunnel wall and then STOP almost all the time; STOP is not held back while the mount is `pending`.** Sideways mounts are outside the 8-candidate search (incl. the Falcon manual's native frame, which needs launch parameters) | 24-orientation battery, both versions: the 8 upright / inverted mounts adopt correctly at frame 1. 8 sideways mounts are never found (`CAUTION` throughout on an empty recording). 8 rolled mounts end `ok` with the wrong orientation: **395–509 of 545 frames STOP** on an empty moving recording | [B4](../orientation_2026-10-18/README.md) |
| L15 | **Dust / suspension is not measured** | the organizers' 16.10 data contain none (exact difference on `synthetic_platform` 0–314; heuristic elsewhere) | [extended data](../extended_data_2026-10-17/README.md) |

Positive, for balance: 1.1.0's shorter **reported** range (the `wall_drift` cut of 15.10) is the more truthful one on
every recording where it differs from v1.0.0. The share of the reported range with the axis > 1.05 m off falls, for
example 12.5 % → 2.2 % (`roundT_pressureGate_roundT`) and 3.0 % → 1.6 % (Set O). A Pandar ↔ Falcon switch inside one
node is a clean fresh start in both directions (B3), and a Falcon frame costs ≈ 17 ms (B8).

| # | evaluation limitation (added 17–18.10) |
|---|---|
| E9 | **The new synthetic recordings are scored only where exact labels exist:** `synthetic_platform` frames 0–314 (real scans = Set O 1195–1509). Platform 315–385, `synthetic_switch` and `synthetic_tunnels` have no source scan in any organizer recording (full 20-minute ride searched, positive control 252 / 252). Their STOPs are unscored. The intensity-1 marker is not a substitute: it found 57 % of the inserted points and about 12 false objects per frame. |
| E10 | **The 16.10 synthetic objects are not static** (they approach ≈ 12.5 m/s faster than the train, in 0.8–3 m steps; Set O's objects are static, ICP-checked). The edge box `obj01` lies 9 cm inside the gauge, so its intent is uncertain: its 38 STOP rows are hits only if the organizers meant "inside". Both questions are with the organizers. |
| E11 | **The Falcon is one recording**, replayed through the node replica (not the Docker node). Timing is this container's. |
| E12 | **The gauge truth (B6) is the path the train drives next (ICP).** It was validated three ways on a curve. Recordings where the train stands (`doubleT_obstacle`, most of `squareT_platform_squareT_switch`) give no off-track numbers. The 8–25 m bin is a detector metric, not a check of the truth. |
