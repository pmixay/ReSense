# Changelog

> **Purpose:** what changed in ReSense, newest first, readable in two minutes. The entries as they stood before the clean-up of
> 19.10, with every measurement, are in [`docs/archive/CHANGELOG_history_2026-10-19.md`](docs/archive/CHANGELOG_history_2026-10-19.md);
> the full dated history of 15–29.09 in [`docs/archive/CHANGELOG_2026-09.md`](docs/archive/CHANGELOG_2026-09.md).
> **Audience:** jury (spec §5 "как менялось качество"), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-20, ~19:00 MSK: [1.2.0] state and the 20.10 entries against git (`main` `8453458`), GitHub (PRs #43–#47,
> CI runs, releases) and `python3 scripts/detector_freeze.py verify` (PASS); the 19.10 entries against `DECISIONS.md` rows 35–44;
> the older sections against the archived text they were cut from (checked 19.10).

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), loosely; versions up to v0.6.4 are team labels; package 1.0.0
dates from 25.09. **The published release is v1.0.0 only.** 1.1.0 (sealed 16.10) was not released and will not be (captain,
19.10); **1.2.0 is the next release and is not released**: the detector seal passes `verify` since the R3 reseal of 20.10. Figures are the team's, measured when a change landed (detector figures on the 1 cm frame cache). Current results:
[`README.md`](README.md), [`docs/SCORECARD.md`](docs/SCORECARD.md). "Set O" = the organizers' synthetic objects; "ride" = the
20-minute, 13 km recording `new_data`.

## [1.2.0] — unreleased: LiDAR integration candidate of 18.10, the integration of 19.10 and the work of 20.10

**State, 20.10 evening (`main` `8453458`).** All four version declarations are 1.2.0. `python3 scripts/detector_freeze.py verify`
**PASSES** (40 files, R3 integrity reseal on the measured `0a472d6`; it is an integrity seal, not an acceptance). CI on `main` was
green at `5d83c5b` (run #667) and `f56ad5e` (#669), all five jobs; run #680 on `8453458` (PR #47) failed in the web job's browser
suite (22 of 75 end-to-end tests; four jobs green), so `main` is red since the UI merge.
PRs #43, #44, #45 and #47 are merged, #46 (P4's review of H′ and the Falcon clear-distance model) is open. **Not released:**
release, tag and demo image wait for a final source, the last commit before the code stop 20.10 23:59 MSK (captain, 20.10); then
the reseal, P4's independent acceptance of the final bundle, the image and the tag. Not a J1 score, not a G3 run
([`docs/BACKLOG.md`](docs/BACKLOG.md) "Current plan"). (State of 19.10 evening, kept for the record: `verify` failed with 2 added
and 11 changed files until the reseal; CI was red.)

### 20.10 — R3 B2/B3 completion

- Accumulated cable clusters can confirm from current-frame footprint, height and distinct
  strict-gauge voxels; historical/duplicate returns cannot supply that evidence. Directed
  speed-known approach: first STOP76 →78 m. Preserve the organizers' moving-in-gauge rule:
  a resolved co-moving cable is a real obstacle, even when static-world ego-veto is ready first.
- Full gate PASS without waivers:208 non-timing metrics and18,329 ordinary/Set F rows unchanged.
  Fresh paired X3:40 cases /29,765 rows /260 comparisons; whole Falcon4,443 rows unchanged.
  E6 retains86.25/61.28 m; hanging Set O float32 retains48.19 m (compact gate35.1 m).
- Merged with main `5d83c5b`;448 affected tests pass. Full pytest2386 passed +17 subtests,
  one inherited proxy-hook failure reproduced on both sources, eight external-data deselections.
  Raw evidence and an integrity reseal supplied; independent final-bundle review remains open.
  [Evidence](docs/evidence/r3_completion_2026-10-20/README.md).

### 20.10 — K2 v5c (off) and P4's data run, PRs #43, #44, #45

- **PR #43:** K2 v5c (`track.axis_joint_reach_dual`, **off by default**; K2 itself stays held off, `DECISIONS.md` row 44), the
  corrected Falcon re-score (first person STOP 122.27 m, 37 person frames without STOP, not 112.97 m / 158), P4's reviews of the
  19.10 integration and the N5 marker supplement. With every K2 switch off, `8c2bf51` equals `a5b0ede` on 180 synthetic rows,
  all 15,269 gate rows and all 4,443 Falcon rows. **PR #44:** P4's re-check on `8c2bf51` and on the F1a repair's synthetic scenes.
- **PR #45**, the data run on the organizers' data: no real start is near the L16 open-air FAULT (lowest above-sensor share
  28.3 %, T1); K2 v5c fails its registered Falcon and marked-bag rows as scored and only set O `small_center` fails the gate
  (T2), the tunnels cube is an edge object (T3); F1a made 163 low clusters weak on set O and the ride, none a real object above
  the rails as far as the pictures show (T4); acceptance runs of the F1a and L16 repairs (below). It decides nothing: the F1a ride
  cost and K2 stay with the captain. [K2 v5c](docs/evidence/k2_v5c_2026-10-20/README.md),
  [T1](docs/evidence/l16_exposure_2026-10-20/README.md), [T4](docs/evidence/f1a_exposure_2026-10-20/README.md),
  [F1a acceptance](docs/evidence/f1a_acceptance_2026-10-20/README.md), [L16 acceptance](docs/evidence/l16_acceptance_2026-10-20/README.md).

### 20.10 — CI and image

- CI runs again: all five jobs passed on `main` at `5d83c5b` and `f56ad5e`. Workflow changes: read-only token, job timeouts, Node 24
  for the web job, superseded runs cancelled except on `main` and `claude/*`, no artifact upload in the release workflow (the
  repository is out of artifact storage), lint relaxed for one-off evidence scripts. The Dockerfile copies the fixtures the in-image
  tests read (including the open-air scene). No detector, config or ROS file changed.

### 20.10 — L16/S3 open-air startup repair and measured T1 exposure

- Reproduce P4 A1 on merged main `8c2bf51`, then reject a ground half-space as signed-forward
  evidence with the bounded forward-cone guard. Preserve channel/rail evidence, real conflicts,
  numeric application and the ≤60,000-point orientation-search budget.
- Original analytic open-air scene: **450 FAULT →450 GO**; tunnel unchanged, all **446 matched
  positive rows retained**. **242 affected tests pass.** T1 independently decodes120 raw CDR
  frames /12 original starts: no A1 exposure, known analytic A1 positive control detected.
- Paired recordings/prefixes: **140 cases /27,580 rows per side**, non-timing results and orientation
  state equal. Both original gates/X3 pass. Final merge `afbf9fc` includes current F1a main:
  fresh gate PASS without waivers, standard X3 PASS (40 cases /29,765 rows), whole4,443-row
  Falcon retained, **489 affected tests pass** (one external-path deselection). Its gate equals
  F1a's published raw run, including that repair's documented ride false-alarm cost.
  Full pytest has2,340 passed, three failures; paired diagnosis and146-node-test reruns are
  retained without an all-green claim.
  Final-bundle review/reseal remain separate. [Evidence](docs/evidence/l16_open_air_2026-10-20/README.md).

### 20.10 — F1a B1 repair (`f07f4b8`, merged with PR #43 at `060bde7`)

- Both B1 mechanisms (the fragmented object's self-reference and P4's capped-top miss): independent rail support that excludes
  low-cluster footprints (`lowobj.local_rail_exclude_low`) and the observed full-footprint top. P4's raised-rail box regains its 8
  STOP rows. Gate against the seal baseline **PASS** without exceptions; set F and the 4,443 Falcon rows equal to starting main;
  X3 40 cases / 29,765 rows with identical STOP rows.
- **Cost against starting main on the ride:** alarm events **18 → 23**, STOP episodes **24 → 26**. P4's acceptance run (PR #45)
  reproduces both numbers and traces all 16 changed decisions to rail-head fragments and tracker chains through them. The
  trade-off is **not decided** (captain). [Evidence](docs/evidence/f1a_b1_2026-10-20/README.md),
  [P4's acceptance](docs/evidence/f1a_acceptance_2026-10-20/README.md).

### 20.10 — R3 sustained-range population diagnosis and reporting repair

- Fresh R3-off/on Set F replay: **30 sequences /3,060 rows per side**, no lost matched hit,
  nine added cable hits, no false-detection increase. The conditional median **34.2 ->17.8 m**
  drops because sustained coverage grows **2/6 ->4/6**; the original-success cohort stays
  **19.0 /49.5 m**, with two new successes at 16.6 /16.4 m. The aggregate concern is resolved.
- Gate reports retain per-sequence evidence, success coverage and fixed-cohort diagnostics.
  `scripts/set_f_comparison.py` independently compares raw paired runs and detects lost hits/successes.
  The old scalar values, all 208 non-timing gate metrics and all gating bits are preserved;
  detector/config source is unchanged. **51 affected tests pass.** P4's other R3 findings and
  final acceptance/reseal remain open. [Evidence](docs/evidence/r3_sustained_2026-10-20/README.md).

### 20.10 — H1 partial improvement, overall OPEN

- **Publish the retained positive collision core as a partial H1 improvement**, explicitly authorized by the user for
  main integration before overall H1 closure. Current-frame support, fresh raw rail anchors and geometric consistency
  can exempt a tall narrow body from the column signature; uninterrupted ordinary confirmation can suspend only its
  column hold. The withdrawn free-top experiment remains off (`column_free_max_top=0`).
- A-axis, an injected object in real scans: **82 ->114/177** matched visible rows, **63 still unmatched**. All 32 physical
  stationary scenes match every post-confirmation scan; three left137 m cases improve **1/14 ->10/14**. Nominal moving
  physical scenes at 22 m/s have continuous STOP from **130.8 /135.2 m**; **0/280** outside-control false STOPs. These
  are development/injection/simulation results, not a real-world detection-range or stopping guarantee.
- Merged source `0f02b28` includes remote main `0acb18c`: full original gate PASS, all **208 non-timing metrics equal**
  the published main integration gate; critical A/C/cable probes retained, all 4,443 Falcon frames checked. Fresh
  combined-tree X3: **PASS, 40 cases /29,765 rows**. Full pytest: **2,276 passed +17 subtests**, one inherited
  proxy-hook message assertion failure, eight external-data deselections. No all-green-suite claim.
- **H1 remains OPEN.** Corrected a longitudinal ICP alias (raw reflector supports 1.343 m rather than 0.335 m), but
  six reconstructions, long-baseline checks and separate validation landmark tracks do not establish a validated far
  rail axis. Independent review/reseal remain pending. No rejected trajectory is installed or credited as truth.
  [Publication record](docs/evidence/h1_partial_integration_2026-10-20/README.md),
  [retained repair](docs/evidence/h1_reference_2026-10-19/README.md),
  [merged-source/reference checks](docs/evidence/h1_trajectory_2026-10-19/README.md).

### 19.10

- **Four agent lanes merged** with `main` (P3's L16/S3 and R3) into one integration branch: K1/K2 gauge, F1 false alarms, Falcon
  long range, N3 dust. With every new switch off the full gate per frame (15,269 rows, set F equal) and the whole Falcon recording
  (4,443 frames) are identical to `aec88d2` / `main`; the same comparator finds the 2,716 changed rows of F1's switched-on
  candidate ([evidence](docs/evidence/integration_2026-10-19/README.md); [`DECISIONS.md`](docs/DECISIONS.md) row 40).
- **Switches decided by the captain** (row 41). **On:** F1a local rail reference (`lowobj.local_rail_margin` 0.01; review finding B1
  accepted), H′ mount cross-check (`cluster.mount_cross_tol` 0.5; removes the 8 false STOP frames on the Falcon tunnel ceiling, 0
  gate rows change), R3, L16/S3, the Falcon clear-distance model (it acts only in the ROS node's non-default `clear_range_policy`
  `conservative` / `small_candidate`), K2 joint axis fit (variant B was switched on that evening, row 43, and **held off again
  later that evening after the Falcon run, row 44**; it is off in 1.2.0). **Off:** S2 settle, Falcon far range (`farrange`:
  person STOP 146 m instead of 127 m, but no gain on injected targets and rule 5.1(b) fails; no 300 m claim), the dust guard
  (fails its own acceptance).
- **P3: L16/S3 and R3** (in `main`; author checks PASS, P4 review pending). L16: ring-free directional orientation, S3: the
  orientation search samples once to ≤ 60,000 points ([evidence](docs/evidence/l16_s3_2026-10-19/README.md)). R3: confirmation of
  thin cables from consecutive current-frame evidence; set O hanging 5 cm object first STOP 30.1 → 35.1 m, standing 5 cm cable
  59.78 → 86.25 m on the node replica; the set F cable sustained-median row 34.2 → 17.8 m is worse. H1 (tall narrow objects):
  cause reproduced, still OPEN ([evidence](docs/evidence/r3_h1_2026-10-19/README.md)).
- **P4 accepted the merged B4 source `0779db7`** (no blocking finding; should-fix items S1–S4 carried over, none introduced by the
  merge; [review](docs/evidence/p4_review_b4_merged_2026-10-19/README.md)). A release still needs CI, a tag and an image.
- **Organizers' answers** (in part; [`answers.md`](docs/organizers/answers.md) §12): everything inside the gauge is an obstacle,
  objects may move, the new synthetic bags have markers and an object order (`obstacles.md`) and dust in every bag. Checked:
  markers equal `obstacles.md` 24/24 and our N5 labels in 1,672 of 1,684 rows (one cube of `synthetic_tunnels` missed); their dust
  gives no STOP or CAUTION on 1.1.0 ([evidence](docs/evidence/synth_markers_2026-10-19/README.md)).
- **Independent check of `aec88d2` on the second lidar** ([evidence](docs/evidence/falcon_head_check_2026-10-19/README.md)): the
  whole Falcon recording (4,443 frames) gives the same decisions as the committed 1.1.0 run; orientation adopted at frame 1, pitch
  −2.39° (independent bed fit −2.37°); the walking person: first warning 139–156 m, first STOP ~125 m, STOP on every frame from
  100 m to 20 m; 12 false STOP frames; CAUTION 69 %; no bed return beyond ~150 m. Re-derived: the curve axis is 3.6× too straight on
  `roundT_doubleT`. Full suite 1,969 passed on `aec88d2`.

### 18.10 (candidate)

Continues on `det/b4-orientation` after merging main and P4; the four version declarations change together
([candidate acceptance record](docs/evidence/version_1.2.0_2026-10-18/PLAN.md)).

- B4 channel-axis orientation checks and observation cadence retain main's readiness guard and obstacle STOP priority. Committed
  merged source `0779db7` passes fresh paired full gates, X3 and 24-mount sweeps; empty-recording false STOPs fall to zero across
  all 24 tested mounts; sideways positive cases retain the matched detections ([evidence and limits](docs/evidence/b4_merge_reseal_2026-10-18/README.md)).
- Falcon ROS/native sensor profiles and explicit orientation readiness (unconfirmed GO is held at CAUTION). Startup orientation
  replay stays **opt-in**: enabling it lost 13 prior Falcon STOP frames, four of them person-associated.
- Interactive replay pause/rate controls and Pandar/Falcon profile reset; a shared bounded gauge display with explicit stale/invalid
  state ([N1/N4](docs/evidence/n1_n4_2026-10-18/README.md)).
- N5 team labels for all 1,667 new synthetic frame keys; C2's explicit conservative-range profile (measured coverage loss approved
  by the captain); Falcon has no calibrated small-target prior and claims zero qualified clear range.
- Selected-default evidence: full gate 18,329 rows, X3 40 cases / 29,765 rows / 260 checks, all 4,443 Falcon frames
  ([results](docs/evidence/lidar_adaptation_2026-10-18/README.md)). Dust measurements complete, robustness acceptance fails; N6's
  candidate (51.12 m, below 60 m) fails review. Both production experiments stay off. Open: L16 coverage beyond the tested scope,
  curve-axis bias (L10/K2), inherited tall-object misses, the Windows Set O frame 332 provenance gap.

## [1.1.0] — sealed 16.10, not released (captain, 19.10; its content is part of 1.2.0)

H5 DONE at `5211565` (numerical core unchanged from the reviewed `c9aea87`): full gate PASS, 208/208 non-latency rows identical,
146 gated rows passed, 18,329 frames without non-latency change ([H5](docs/evidence/integration_2026-10-16/h5/README.md)); seal
[`detector_freeze_2026-10-16_1.1.0.json`](docs/evidence/detector_freeze_2026-10-16_1.1.0.json), 36 files. Retained: the
structure-surface cut with H2's 0.1° azimuth bar; the monitored/clear-range cap at wall drift; shared C1 v1 (v2 offline FAIL: 30.46 %
CAUTION, 19 lost alerts); E2 offline rebuild (local PASS). **H1 DROPPED** after H4 (`cluster.column_free_max_top=0`; A-axis 82/177,
C-person 82.77 m / 55 STOP frames; the inherited tall-object miss stays OPEN, 8.1). S1 FAILED, runtime removed. Independent H4 of
`707ea9c..c9aea87` accepted, no new medium-or-higher finding ([checkpoint](docs/evidence/integration_2026-10-16/README.md)). Not
released: no tag or archive, no J1 score.

## Earlier work, 14–15.10 (not resealed; superseded by 1.1.0)

- D1 pass 1 (15.10): SCORECARD and captain table cite the 13.10 v1.0.0 judgement (66/100); PT1 pass 1: the 16-slide PPTX/PDF with
  detail in the notes, `build_deck.py --audit` and a word budget (≤80/slide, ≤1,100 total).
- Candidate `final/silent-misses` (historical measurements; H4 later blocked the column/free-top path). Entries kept for their
  anchors; full text in the [archive](docs/archive/CHANGELOG_history_2026-10-19.md):

### Fixed — the monitored range stops where the axis leaves the track at a curve entry (`track.axis_wall_drift`, 15.10)

- Judge's problem 4 (13.10): entering a curve (C = `roundT_pressureGate_roundT`) the fitted axis lags the track by 1.0–2.4 m at 100 m
  while the trusted axis range stays 119–151 m, so an object at 100–150 m never enters the corridor and the decision is GO. The
  monitored range (`monitored_range`, `clear_distance`) now ends where a near tunnel wall has come 0.8 m nearer the axis; the
  corridor and every decision are unchanged. Cost: range capped in 13.8 % of the ride's frames. Weighting the walls by how far each
  is seen failed three full gates and was not shipped. Others of that candidate: the structure cut (`cluster.structure_cut_tol`
  1.3 m), the pole-in-the-envelope rule (`cluster.column_free_max_top`, later dropped with H1), review fixes of 14.10.

## [Unreleased] — web prototype (PR #31, `317eabf`; outside the `v1.0.0` release)

- **Added (29.09):** a multi-page Russian web site in the «Линия» design: FastAPI backend `resense-web`, React + TypeScript + Vite
  frontend, HTTP contract [`webapp/API.md`](webapp/API.md); live at https://resense.arbuz.lol/; locally `scripts/run_webapp.sh` →
  http://localhost:8080 (no ROS or Docker). Inputs: rosbag2, `results.jsonl`, cached frames, synthetic demos. Pages: upload, queue,
  runs, run (KPIs, decisions against labels), 3D player from the cab, comparison, live mode through rosbridge, parameters/presets.
  The same sealed `resense.Detector` runs in a worker; the image does not contain `webapp/`. Known limits: 60 fps not measured, live
  mode tested against a stand-in, no authentication.
- **Changed (20.10, PR #47, merged):** a reworked Player workspace (a modeled train-interior display, reference-based 3D view,
  pinned transport and telemetry) and a persistent live preview at https://resense.amdm.life/. Web-only: no file under
  `resense/`, `native/`, `configs/` or `ros2_ws/` differs from `f56ad5e`, the seal still passes, the release image does not contain
  `webapp/`. P2 reports 362 frontend, 179 backend and 81 dashboard tests and 75 browser cases in split batches (not one clean
  suite) on its host, and public checks of the preview ([README](docs/evidence/p2_2026-10-20/README.md),
  [PUBLISH](docs/evidence/p2_2026-10-20/PUBLISH.md)); `/deployment.json` at ~18:50 MSK named commit `432494f` of branch
  `ui-improvement` (deployed 18:23 MSK), a pre-merge build.
- **Changed (09.10):** resumable, checksummed uploads in 8 MiB chunks with adaptive gzip, retries and a second-tab guard; background
  finalize; a background read-ahead thread in processing; the 502 behind the reverse proxy fixed (idle keep-alive 130 s).
- Tests at 29.09: 149 backend, 278 frontend, 44 browser end-to-end; CI job `webapp` after `checks`.
  Full text: [archive](docs/archive/CHANGELOG_history_2026-10-19.md).

## [1.0.0] — released 29.09

[v1.0.0](https://github.com/pmixay/ReSense/releases/tag/v1.0.0) points to `5d6e9b5`; archive `resense-image-v1.0.0.tar.gz`
(477,449,541 bytes), `.sha256` and `SHA256SUMS` published; the judge verified checksum and offline launch on 13.10.

- **Shell rule off after the safety review (29.09 night; seal `fe27068`).** `cluster.shell_min_top` 2.3 → 0: the independent review
  ([evidence](docs/evidence/safety_review_2026-09-29/README.md)) found it read a floor-standing cluster's own top as the tunnel
  lining when the object continues above the 3.0 m envelope top. Synthetic tunnel, 22 m/s: the hanging cable `cable_low` first STOP
  21.0 m with the rule, 73.8 m without; a floor-to-vault pole 36.4 vs 104.6 m; a 3.6 m box like a standing train CAUTION instead of
  STOP. `tracking.explained_run` 5 and `tracking.ego_veto_min_speed` 4 m/s stay (non-blocking, limits in
  [`docs/ALGORITHM.md`](docs/ALGORITHM.md) §6; the veto must only be fed a measured speed). Full gate of `7464d80`: PASS, 6 gated
  metrics better, none worse; ride 31 / 32 / 130 → 30 / 27 / 126 episodes / events / alarm frames; five empty recordings 13 / 11 / 40 →
  12 / 8 / 39; set F box 1 m false detections 12, cable 3 → 0 ([gate](docs/evidence/cycle_2026-09-29/shell_off/README.md)). 1 284 tests
  passed on the final branch of 29.09 (as recorded then; 8 need local caches) and 74 dashboard tests.
- **Three false-alarm rules from other teams' open case 05 solutions (29.09 evening; seal `1e2ed82`).** `tracking.explained_run` 5,
  `cluster.shell_min_top` 2.3 (later off), `tracking.ego_veto_min_speed` 4 m/s; full gate PASS, 7 metrics better, none worse (ride
  32 / 31 → 26 / 28; five empty recordings 11 / 13 → 8 / 12). Five other candidates were measured and rejected (`lowobj.min_top`
  0.08, clean run with range demotions, `fresh_stop_evidence`, quadratic edge margin, far ring rails)
  ([gate table](docs/evidence/cycle_2026-09-29/competitor_rules/gate_table.md)). Far rail evidence from ring crossings
  (`track.rails_far_rings`) is implemented and **off**: it fails the gate (stations reach 34–47 m on real rails).
- **The experimental line merged into `main` (29.09, PR #27).** `catchup_startup_step` default 0 (every frame of the start-up
  backlog; 0.2 is explicit and was what the start-up figures were measured with); `tracking.thin_far_min_voxels` 4 → 3; opt-in
  experiments off by default (`cluster.weak_min_rings`, `tracking.far_min_ring_count`, `tracking.fresh_stop_evidence`,
  `lowobj.local_support_*`; `configs/experimental_*.yaml`); the single GO at `doubleT_obstacle` frame 111 closed by
  `tracking.stop_keep_low_s` 0.3 (STOP on 193 of 201 frames; tuned on this recording,
  [evidence](docs/evidence/frame111_2026-09-29/README.md)).
- **Health sector counts and the timing contract (28–29.09).** `resense.health._sector_counts` counts `values >= edge` (same counts,
  0.54 ms against 2.89 ms at 381 k points); `timing_ms.total` includes health and result construction. Full native gates: all
  non-latency metrics unchanged, no speed gain claimed.
- **ROS node (29.09; the detector sealed and unchanged).** Bit-identical faster decode (20.3 → 16.6 ms at 360°); a start-up
  catch-up (0.2 at the time, default 0 since PR #27: first 3 s results 38–105 ms old instead of 312–325 ms, with 0.2); a warm-up
  (`warmup`, default true); a clean exit on Ctrl+C; `check_dry_run.py` prints end-to-end latency and pace
  ([evidence](docs/evidence/node_startup_2026-09-29/README.md)).
- **Documentation (29.09).** README compacted to the jury path; EXPERIMENTS compacted (full log in
  [`docs/archive/EXPERIMENTS_log_2026-09.md`](docs/archive/EXPERIMENTS_log_2026-09.md)); dated records archived; the deck and the overview
  video carry the final gate's numbers; [`docs/REQUIREMENTS_MAP.md`](docs/REQUIREMENTS_MAP.md) maps every requirement of the spec.

## 15–28.09 (v0.0 – v0.6.4, package 1.0.0 from 25.09)

The dated entries 2026-09-28 (image default command, node input path, CI in two stages), 27.09 (the submitted detector sealed after
the quality cycle), 26.09 (P3d detector, freshness controls), 25.09 (offline delivery, C++ kernels, regression gate), v0.6.4 –
v0.0 (15–24.09) are word for word at the end of
[`docs/archive/CHANGELOG_history_2026-10-19.md`](docs/archive/CHANGELOG_history_2026-10-19.md); the longer dated history of the same
weeks is [`docs/archive/CHANGELOG_2026-09.md`](docs/archive/CHANGELOG_2026-09.md).
