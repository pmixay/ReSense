# Changelog

> **Purpose:** what changed in ReSense, newest first, readable in two minutes; the full dated
> history with every measurement: [`docs/archive/CHANGELOG_2026-09.md`](docs/archive/CHANGELOG_2026-09.md).
> **Audience:** jury (spec §5 "как менялось качество"), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-29 night (`fe27068`, seal `7464d80`, before the merge into `main`): each section against the archived
> changelog, the 29.09 node change against the node source and launch file, the rules of 29.09
> evening and the shell switch-off against `configs/default.yaml`, the seal manifest and `gate_table.md`; every relative link;
> 2026-09-29: the web prototype entry against `webapp/`, `scripts/run_webapp.sh` and `.github/workflows/ci.yml` of PR #31 ·
> **Updated:** 2026-10-16: selected-scope H3/withdrawal/independent H4 at `c9aea87`, final H5
> at `5211565` and verified 1.1.0 seal below; 2026-10-18: the LiDAR branch is now an
> unreleased 1.2.0 candidate. Hosted CI, P4 final candidate approval and release remain pending.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), loosely; versions up to v0.6.4
are team labels; package 1.0.0 dates from 25.09. `main` now contains the merged **1.2.0** candidate (PR #37);
`det/b4-orientation` integrates B4 and P4 work. The selected next J1 source remains
pinned sealed **1.1.0 `3b7d7aa`**, not the moving main branch.
The published release remains v1.0.0. Figures are the team's, measured when a change
landed (detector figures on the 1 cm frame cache). Current results: [`README.md`](README.md),
[`docs/SCORECARD.md`](docs/SCORECARD.md). "Set O" = the organizers' synthetic objects; "ride" = the
20-minute, 13 km recording `new_data`.

## [1.2.0] — unreleased LiDAR integration candidate, 18.10

This candidate continues on `det/b4-orientation` after merging main and P4; the
previous `work/n5-labels-c2-acceptance` is merged into main. It is not a new release
or a completed P4/J1 judgement. The four version declarations change together. A fresh gate on
the committed version and its source identity are recorded in the
[candidate acceptance record](docs/evidence/version_1.2.0_2026-10-18/PLAN.md).

- B4 channel-axis orientation checks and observation cadence now retain main's readiness
  guard and obstacle STOP priority. Committed merged source `0779db7` passes fresh paired
  full gates, X3 and 24-mount sweeps with the same native build. Empty-recording false STOPs
  fall to zero across all 24 tested mounts; newly recovered sideways positive cases retain
  the correctly oriented control's matched detections. [Evidence and limits](docs/evidence/b4_merge_reseal_2026-10-18/README.md).
  A new candidate seal passes before and after native compilation in a clean checkout.
  Physical horizontal scanners, missing/late channel evidence and P4 S1–S4 remain open;
  final P4 review of the merged source is pending.
- Falcon ROS/native sensor profiles and explicit orientation readiness; unconfirmed GO is
  held at CAUTION. Startup orientation replay remains **opt-in**: enabling it lost 13 prior
  Falcon STOP frames, including four person-associated frames, so it is not the default.
- Interactive replay pause/rate controls and Pandar/Falcon profile reset; a shared bounded
  gauge display with explicit stale/invalid state. Node/DDS and display evidence are separate
  from P4's judge-node replica checks.
- N5 team labels cover all 1,667 new synthetic frame keys, retaining annotation uncertainty.
  C2's explicit conservative-range profile uses the captain-approved measured coverage loss;
  Falcon has no calibrated small-target density prior and claims zero qualified clear range.
- Selected-default evidence before this version-only bump: full gate 18,329 rows, X3 40 cases
  / 29,765 rows / 260 checks, and all 4,443 Falcon frames preserve their compared STOP outputs.
  [Results and exact source identities](docs/evidence/lidar_adaptation_2026-10-18/README.md).
- Dust measurements are complete but robustness acceptance fails. N6's candidate reaches
  51.12 m, below 60 m, and fails farther-geometry review. Both production experiments remain
  off. L16 coverage beyond the tested B4 channel-evidence scope, curve-axis bias (L10/K2), inherited tall-object
  misses and the historical Windows Set O frame 332 provenance gap remain unresolved.

P4's development check of `b423562` is not final approval of this version. P1 owns integration
and sealing; P3 owns further detector changes. The same orientation/axis areas must enter one
reviewed integration before a later release. Hosted CI is still blocked by account billing;
no release date or new score is asserted.

## [1.1.0] — sealed 16.10, unreleased (E1 tag/archive pending)

**H5 DONE:** final measured source `5211565`, numerical core unchanged from reviewed `c9aea87`;
replacement H3, withdrawal probes, independent H4 and final version-bumped gate/seal complete.
**H6 PENDING:** actual complete CI/main acceptance. No v1.1.0 E1 tag/archive or new J1 score.
[Integration checkpoint](docs/evidence/integration_2026-10-16/README.md) links the committed
reports and preserves the old H3 PASS / original H4 BLOCKED verdicts.

- [Final H5](docs/evidence/integration_2026-10-16/h5/README.md): all four declarations committed
  at **1.1.0** in `52115654417a660669b8dddfce447692c1d782cc` before measurement. Full gate
  **PASS**, exit 0, **208/208 non-latency rows identical**, same **146 gated rows passed**,
  no overrides/waivers; all **18,329 raw/serialized frames** have zero non-latency changes
  against reviewed `c9aea87`. No new gated gain or detector timing improvement is claimed.
- [Current seal](docs/evidence/detector_freeze_2026-10-16_1.1.0.json): measured `5211565`,
  source/evidence commit `21e1d61`, seal commit `d6319c2`; **36 frozen files**, source digest
  `db3f588df59184ad703436996f72bd94a91eca91dfcfe4a02655fcdd4397d751`.
  [Committed-seal proof](docs/evidence/integration_2026-10-16/h5/seal_verify/completion.json)
  retained at `ec81e78`: explicit new-manifest verification **PASS** in a clean LF Linux checkout
  before and after native rebuild. Default-pointer integration is parent-owned.
- Retained: structure-surface cut with H2's physical 0.1° azimuth bar; monitored/clear-range
  cap at wall drift; shared C1 v1 with strict raw flag/health validation; E2 offline rebuild;
  P4 evaluation tools/evidence and P2 docs/pitch preparation.
- H1 **DROP after H4**: `cluster.column_free_max_top=0` in class/YAML/ROS defaults (`795a243`).
  Original H1 left 9+5 dark excess STOP frames and an inherited tall miss; the zero-dark author
  attempt lost A-axis 157 → 139/177 and other positives. No column fix or 157-frame shipping
  gain is claimed. [Measured withdrawal](docs/evidence/integration_2026-10-16/h4_fixes/columns/WITHDRAWAL_RESULTS.md)
  (`829b243`, source `c9aea87`): A-axis **82/177**, exact sealed scored frame set; C-person
  **82.77 m / 55 STOP frames** retained. Entire dark pieces 1/3: **14/2 STOP frames**, zero
  extra/lost STOPs and zero free-top/observer calls. Author units **260 passed**, **6 existing
  external-data deselections**, no failures/errors/skips; inherited High tall miss **OPEN, 8.1**.
- [Replacement H3](docs/evidence/integration_2026-10-16/h3_selected/README.md) (`5282d6f`):
  exact committed `c9aea87`, clean Linux/native full gate **PASS**, exit 0, no overrides/waivers;
  **208/208 non-latency rows identical**, **146 gated rows passed**. All **18,329 raw/serialized
  frames** compared to same-runtime sealed `707ea9c`; no unexplained change or gated gain.
  Only the range cap/additive fields and registered timing telemetry differ.
- [Fresh independent H4](docs/evidence/integration_2026-10-16/h4_selected/README.md) (`70072f1`):
  revised difference `707ea9c..c9aea87` **ACCEPTED**, no supported **NEW medium-or-higher** finding.
  **306 passed**, zero failures/skips/deselections; **36 H2 angular/voxel boundary cases**,
  **1,344 paired Tracker updates per source**. Inherited High 8.1 remains OPEN; the original
  enabled-H1 H4 remains BLOCKED and attempt 08 remains rejected.
- S1 **FAIL, runtime removed**: queue 40, startup step 0, lag 20 s, original freshness retained.
  C1 runtime accepts only v1; v2 is **offline experimental, FAIL** (30.46% CAUTION, 19 lost
  labelled object-frame alerts).
- E2 local clean offline rebuild **PASS**; new release-workflow check awaits a new tag.
  H0 baseline **PASS**; X3 **40-case v1.0.0 baseline**, not new-candidate acceptance;
  G3 **spec only**, no held-out result.
- O1 prepared, **not dispatched**, no organizer reply. J1 and PT1 numerical claims remain
  explicitly v1.0.0. Verified branch archive is prepared; main merge/retirement remain pending.
- Documentation consolidated after P1/P2 merge conflicts; one exact duplicate 09.10 upload
  entry removed; DECISIONS retains the historical rows and records the 16.10 scope/dispositions.
  P4 intake aliases corrected with a dated note (**B = roundT_doubleT**, **C = roundT_pressureGate_roundT**),
  full names/data unchanged; original handoff publication links pinned to commit SHAs.

## [Unreleased] — P2 documentation and pitch preparation (15.10)

- D1 pass 1: current SCORECARD and captain table now cite the 13.10 v1.0.0 judgement (66/100),
  with earlier reviews dated; release/tag, merged prototype, current shell-off baseline, ownership,
  dual-return sensitivity and cache-vs-node range claims corrected. Decision-log rows preserved.
- PT1 pass 1: rebuilt the 16-slide named PPTX and PDF, moved detail into speaker notes, added
  `build_deck.py --audit` and a build-time word budget (≤80/slide, ≤1,100 total, including chart labels).
  Final range-by-geometry graph, release numbers, video cards and P1 sign-off wait for O1/J1;
  C1 display, PT2 and S5 dependencies are tracked in [`web/P2_STATUS.md`](web/P2_STATUS.md).

## Historical unreleased detector candidate `final/silent-misses` (14–15.10; not resealed)

**Historical measurements below, not the selected 1.1.0 shipping claim.** H4 later blocked
the column/free-top path; it is disabled by `795a243`. H2 and the range cap remain selected,
with replacement H3/probes and revised-scope H4 complete at `c9aea87`; H5 later sealed 1.1.0
from `5211565` (H6 and E1 pending).
See the [16.10 checkpoint](docs/evidence/integration_2026-10-16/README.md).

The two fixes below together, and the fixes of the review of 14.10 evening:
[`silent_misses_2026-10-14`](docs/evidence/silent_misses_2026-10-14/README.md). The full regression gate of the current
code (`14f83dd`) passes with every gate frame identical to the sealed detector. No frame of the 27 judge range probes is
worse than the sealed detector; the review's false STOPs next to the wall and its dropout / pitch replays are back at
the sealed numbers frame by frame.

### Fixed — the monitored range stops where the axis leaves the track at a curve entry (`track.axis_wall_drift`, 15.10)

- The judge's problem 4 and the GO that stayed of silent miss 2 (13.10): entering a curve (C =
  `roundT_pressureGate_roundT`, frames 57-117) the fitted axis lags the track by 1.0-2.4 m at 100 m while the trusted
  axis range stays 119-151 m, so an object on the track at 100-150 m never enters the corridor and the decision is GO
  with `clear_distance` past it. Cause, measured: both tunnel walls are fitted and averaged by fit quality; the inner
  wall is smooth (rms 0.03-0.14 m vs 0.12-0.21) but seen only to 56-96 m, where the transition's curvature is still
  small, so it carries 3-10x the weight; even the outer wall alone, a quadratic held to the rails' tangent, cannot follow
  a curvature that grows with the distance (−0.0008 vs about −0.0014 needed at frame 86). The outer wall's far part,
  once it has crossed the lagging axis, is counted on the inner side (the walls are split by the sign of the lateral)
  and lengthens that side's reach (the trusted range); removing it moves the averaged curvature by at most 0.9e-4
  (frames 57-90) / 1.8e-4 (91-117), i.e. 0.4 / 0.9 m at 100 m of the 1.0-2.4 m: a part of the lag, not its main
  cause. The rate limit never binds.
- The monitored range (health `monitored_range` and `clear_distance`) now ends where a near tunnel wall, followed
  outward from the rail range where it is parallel to the rails, has come 0.8 m nearer the axis (two bins in a row;
  a faster step is a structure edge and moves the reference). On C the axis is 0.7-1.1 m off the wall-referenced track
  there. The output names it (`health.wall_drift`, `track.wall_drift`, only in such a frame). The corridor and every
  decision are unchanged.
- Judge C range probes (frames where the decision is GO, the object visible and the range past it): person on the
  axis 26 → 10, 1 m cube 27 → 7, 0.5 m cube 27 → 7, the person on the wall-referenced track 26 → 4; none is left
  within 142 m (the rest: 142-156 m before the drift is measurable, and 178-186 m on the straight). STOP frames, A and B
  identical. Cost: the ride's range is capped in 13.8 % of its frames (median 94 m; 3.8 % of the range), C 50 %
  (its two curve entries), A 20 %, S 5 %, B 3 %, `doubleT_platform` and `doubleT_obstacle` none. Capping the corridor
  there too (`beyond_axis`, CAUTION) was measured and not taken: C's person 55 → 43 STOP frames, first STOP 82.8 →
  65.1 m. The full regression gate passes on this code: every decision of every gate frame is the sealed detector's;
  only `monitored_range` / `clear_distance` / `wall_drift` differ (2 321 of 15 269 frames; and in 2 ride frames the
  latency warning of the machine's timing, not a decision input).
- Not shipped — the axis itself (15.10; local branch `r3/axis-B-trial`). Weighting the two walls also by how far each
  is seen continuously (span ratio ** 4, gaps up to 16 m) puts C's axis on the wall-referenced track (100 m: median
  1.39 → 0.42-0.56 m, max 2.41 → 0.71-1.05 m) and the judge's person placed on that track goes 47 → 64-74 STOP frames
  (first STOP 71.0 → 96-111 m). Three versions failed the full gate: on every two-wall frame (ride 27 → 33 events, a
  false STOP on `roundT_doubleT` from its double-track tunnel's far wall), only for two near walls with the farther
  one curving more (ride 27 → 36, the station +1), and only after a frame with a wall drift as well (ride 27 → 34, C
  +1 event at 56 m). Each moves the axis on frames the false-alarm rules were screened with; not tuned further on the
  same recordings.

### Fixed — the review of 14.10 (`14f83dd`)

- The structure cut placed objects standing 0.95-1.2 m in front of C's outer wall — outside the envelope, where the
  detector's trusted near axis reports them (lateral 1.24-1.32 m, CAUTION) — inside it, through the lagging far axis:
  false STOPs for a person-size box 1.0 / 1.1 m from the wall 0 → 21 / 15 frames, a sign post 0 → 5, a 2.6 m mast
  0 → 9, a column 0 → 8. `cluster.structure_cut_tol` 0.8 → 1.3 m (more than the wall equipment, 0.8-1.2 m, and more
  than C's wall stands outside the strict envelope): all 0 again. The C gains shrink but stay above sealed: person
  first STOP 73.9 → 82.8 m (13.10: 90.2), STOP frames 49 → 55 (60). Making the parts beyond the wall's entry into the
  envelope advisory instead was measured and rejected: worse than sealed (person 49 → 47 frames).
- One free-top spare broke a column hold: the standing train with 20-30 % point dropout gained 2-11 STOP frames and a
  STOP episode in three of four seeds, `roundT_doubleT` pitched −2° one STOP frame. `tracking.column_free_min_spares`
  2: a spared cluster is believed only when its track had another spared hit in its last 10 hits; alone it is the
  column it was before 13.10. Every such replay is now identical to the sealed detector; the off-axis pole loses
  1-12 STOP frames at 160-200 m (A, +0.7 m: 136 → 128 of 176), none within 150 m.
- A demoted structure-cut part no longer removes a low object it overlaps; channel ids out of the ring table's order
  are no empty-ring evidence for the free-top test; tests for the rule wiring (the detector's channel ids, a cut
  part's free-top test) and a wall-fixture test that now pins the tolerance, not the voxel bar.

### Fixed — a pole standing in the envelope is not a column (`cluster.column_free_max_top`, 13.10 / 14.10)

- The judge's silent miss 1 of 13.10 ([`judgement_2026-10-13`](docs/evidence/judgement_2026-10-13/README.md)): a
  0.3 × 0.3 × 2.8 m pole inside the envelope was demoted as a column — CAUTION from ~70 m to 5 m on the axis, never a
  STOP 0.7 m off it. A column continues up to the vault, an object standing in the envelope ends inside it: the column
  signature no longer demotes a cluster at least half inside the strict envelope, its top at most 2.95 m, whose top is
  seen free (`clustering.top_is_free`: the first ring above the top that returns has nothing at the top's range, and
  either a ring in between returned nothing — read from the frame's channel ids, the ring table only without them — or
  more of its returns lie beyond the top than nearer). Every other rule still applies.
- Judge range test on A: the pole 82 → 157 STOP frames of 177 on the axis, 0 → 136 / 133 at ±0.7 m (with `--dropout`
  67 → 143 and 11 → 133), the 0.5 m post 56 → 157 and 30 → 150; the person box unchanged frame by frame. After the
  review (one spare is a column, above): the same on the axis, ±0.7 m 128 / 132, `--dropout` +0.7 m 126, the post
  +0.7 m 138; the losses are all at 160-200 m. The full
  regression gate passes with every gate frame identical to the sealed detector (ride, five obstacle-free recordings,
  `doubleT_obstacle`, set O); the four judge recordings and A / S with `--pitch 2` and `--drop 0.3` are unchanged.

### Fixed — an object against the wall on a curve is not dropped with it (`cluster.structure_cut_tol`, 13.10 / 14.10)

- The judge's silent miss 2 of 13.10: on the curve of `roundT_pressureGate_roundT` the lagging far axis lays the tunnel
  wall across the envelope at 70-150 m; a person-size box there touches the wall, the two make one cluster longer than
  `max_extent`, the 25.09 split refuses it and it was dropped whole (GO at 75-87 m). A cluster the split refused is now
  cut along the smooth surface it lies on (`clustering._off_structure_parts`: a robust fit y(x, h), not fitted without a
  strict-gauge point, not cut along a surface steeper than 45° to the track); its points at least 1.3 m (0.8 m on
  13.10, see the review above) in front of the surface are linked again, and parts at most 3 m long with strict-gauge points and at least 8 voxels
  (`structure_cut_min_points`) go through every rule. A cluster whose split part was accepted keeps the split's verdict.
- Judge range test on C, first STOP sealed → 13.10 → 14.10: person 73.9 → 90.2 → 82.8 m (`--dropout` the same; yawed
  ±20° 72.5 → 93.1 / 88.7 → 85.7 / 85.7; lateral +0.5 69.5 → 84.3 → 72.5, −0.7 85.7 → 109.4 → 96.1), 1 m cube 73.9 →
  96.1 → 85.7 m, 0.5 m cube 75.4 → 82.8 → 75.4 m; B, A and D persons unchanged. Not fixed: C 100-150 m stays 0 / 34
  STOP frames with GO at 118-150 m (the axis puts the box within 0.2-0.8 m of the wall there, judge problem 4), no
  gain within 1.3 m of the wall. The full regression gate passes with every gated and information row identical.

## [Unreleased] — web prototype (PR #31; outside the `v1.0.0` release)

[PR #31](https://github.com/pmixay/ReSense/pull/31) merged as `317eabf`; the prototype is in `main`
and outside the runtime image and release v1.0.0.

### Changed — resumable uploads for big recordings, faster processing (`webapp/`, 09.10)

- Uploads are resumable and checked ([`webapp/API.md`](webapp/API.md), «Recordings»): a file over 8 MiB goes up in
  8 MiB chunks, four requests at a time, in any order; every chunk carries the CRC-32 of its raw bytes and is
  flushed to disk before it counts, so a dropped connection, a closed tab or a server restart loses at most the
  chunks in flight. `GET /api/uploads/{id}` says what is missing; after a reload the page offers the unfinished
  upload and continues it once the same file is picked again (another file asks before replacing it).
  Unfinished uploads are kept 72 h after their last write (`RESENSE_WEB_UPLOAD_TTL_H`).
- Compression on the wire: chunks are gzipped in Web Workers when that is faster than the link (adaptive: off on a
  fast LAN, re-checked as data and link change). The synthetic lidar bags deflate to ≈ 0.65 of their size: a
  333 MB demo bag through the page over an emulated 100 Mbit/s link took 18.6 s (17.9 MB/s) where the raw bytes
  need 26.7 s, so the 25 GB / 100 Mbit/s case goes from ≈ 36 to ≈ 25 min (real bags may deflate differently).
- Upload card: bytes, speed, time left (10 s average), the compression saved, «докачка» when resumed; pause /
  continue / cancel buttons; automatic retries with backoff when the connection is gone («нет связи · повтор
  через N с», at once when the browser is online again); a full server disk pauses with its message; the
  browser asks before the page is left mid-upload; a second tab shows the upload as running there and offers
  neither to continue nor to delete it. Главная shows the same state. The staging area of a failed upload is
  removed only when it cannot become a recording; otherwise «Повторить» continues it.
- A request body that sends nothing for 60 s ends with 408, so a connection that died without a FIN / RST
  cannot keep an upload busy (finalize refused) for ever; the client retries 409 instead of giving up.
- Finalize runs in the background with its stage (unpacking a zip shows its percentage): a 25 GB zip no longer
  holds one HTTP request for minutes; a repeated call joins the running one.
- Processing: the worker reads and decodes the next frames in a background thread while the detector works
  (18–21 → 23–24 frames/s on the 10 s demo bag, same results).
- Fixed: occasional 502 from the reverse proxy. uvicorn closed idle connections after its default 5 s while Caddy
  keeps idle upstream connections 2 min, so a request could go out on a connection the backend was just closing
  (the page polls every 5 s, exactly on that boundary). Caddy replays a GET that hits it, but not a POST / PUT /
  DELETE: reproduced through Caddy 2.6.2, 19 of 150 POSTs sent at the boundary got 502 («connection reset by
  peer», «broken pipe», «EOF»). The backend now keeps idle connections 130 s (`RESENSE_WEB_KEEPALIVE_S`,
  `--timeout-keep-alive`), longer than the proxy, which therefore always closes first.
- Fixed: deleting an upload while it was being finalized removed the files under the unpacking (now 409) and a
  late file PUT could land in a finalized upload; an interrupted unpacking could be taken for input; a recording
  could be orphaned when registering it failed; a folder of upper-case `.NPY` frames was counted but processed
  as zero frames.

### Added — the web prototype for the jury (`webapp/`, 29.09)

- A multi-page web site with a Russian UI in the «Линия» design ([`webapp/README.md`](webapp/README.md)): FastAPI
  backend `resense-web` ([`webapp/backend`](webapp/backend/README.md)), React + TypeScript + Vite frontend
  ([`webapp/frontend`](webapp/frontend/README.md)), the HTTP contract [`webapp/API.md`](webapp/API.md). Live at
  https://resense.arbuz.lol/; locally one command, no ROS or Docker: `scripts/run_webapp.sh` → http://localhost:8080 (the API and the built site on one port; first
  run with internet: `--install`; Python ≥ 3.10, Node.js 20.19+ / 22.12+ only to build the frontend).
- Inputs: a rosbag2 bag (a `.zip` of its folder, `.db3` + `metadata.yaml`, `.mcap`), a `results.jsonl` from
  `resense run --out` (decisions recomputed, no point clouds), cached `.npy` / `.npz` frames; files and folders by
  drag-and-drop, a server folder registered in place, and synthetic demo recordings (three tunnel scenarios,
  labelled synthetic; optimistic: the approach demo's first STOP comes at ≈ 130 m, which is not a measured range).
- Pages: Главная, Загрузка, Очередь, Прогоны, Прогон (KPIs, per-frame decisions against labels, distance chart,
  events, the score against labels, downloads), a fullscreen 3D Плеер from the cab (point cloud, the 2.1 × 3.0 m
  envelope, detections, HUD tiles, a scrubber coloured by decision), Сравнение of 2–4 runs, Прямой эфир (the node
  through rosbridge, or a replay of a run), Параметры (the sealed «Стандарт 1.0» and user presets of 20 tunable
  parameters), О системе.
- The detector and the runtime image are unchanged: a worker process runs the same sealed `resense.Detector`,
  one job at a time, with the ROS node's per-frame decision rule; the image does not contain `webapp/`. The
  single-page dashboard [`web/index.html`](web/index.html) stays as it is.
- Tests: 149 backend (pytest), 278 frontend (vitest), 44 browser end-to-end (Playwright, [`webapp/e2e`](webapp/e2e/README.md),
  ≈ 6 min); new CI job `webapp` after `checks` in [`.github/workflows/ci.yml`](.github/workflows/ci.yml), which
  fails if a backend or browser test is skipped.
- Known limits: 60 fps playback not measured (headless SwiftShader only); the live mode tested against a
  rosbridge stand-in only; no authentication and one server process — a local stand.

## [1.0.0] — released 29.09

**Release status:** [v1.0.0](https://github.com/pmixay/ReSense/releases/tag/v1.0.0) points to
`5d6e9b5`; archive `resense-image-v1.0.0.tar.gz` (477,449,541 bytes), `.sha256` and
`SHA256SUMS` published. The judge verified checksum/offline launch on 13.10. The entries
below retain the dated development measurements that led to this release.

### Changed — shell rule off after the safety review (29.09 night; resealed at `fe27068`)

- `cluster.shell_min_top` 2.3 → 0 (`a5455b3`: the code default, `configs/default.yaml` and the ROS copy): the
  `shell` signature switched on in PR #29 is off again the same night. An independent safety review of the three
  rules below (29.09 evening; [`docs/evidence/safety_review_2026-09-29/`](docs/evidence/safety_review_2026-09-29/README.md),
  its first rows reproduced by the coordinator) found that it reads a floor-standing cluster's own top as
  the tunnel lining whenever the object continues above the 3.0 m envelope top, which the corridor clips. Synthetic
  tunnel, ray-cast, train at 22 m/s: the catalogue hanging cable `cable_low` (0.03 m, down to 0.2 m above the rail
  head — the case the organizers called very important, [QA session](docs/organizers/QA_session.md) fact 3) got its
  first STOP at 21.0 m with the rule on and at 73.8 m with it off; a 0.1 m floor-to-vault pole 36.4 m vs 104.6 m; a
  3.6 m-tall box like the rear of a standing train at 60 / 90 / 150 m was CAUTION instead of STOP. Alone the rule had
  bought little: ride events / STOP episodes 32 / 31 → 31 / 29. Re-enabling it would need an exemption for objects
  that cross the envelope top.
- The deck (`docs/presentation/`, P2's version with the team's photos and names) and the overview video
  (`docs/video/resense_overview.mp4`, 3:00, the jury's arc, a synthetic Russian voice-over; script and a shot list
  for the team's own recording in [`docs/video/README.md`](docs/video/README.md)) carry the final gate's numbers;
  [`docs/REQUIREMENTS_MAP.md`](docs/REQUIREMENTS_MAP.md) maps every requirement of the spec to the repository.
  1 284 tests pass on the final branch (plus 6 subtests; 8 need local data caches) and 74 dashboard tests.
- `tracking.explained_run` 5 and `tracking.ego_veto_min_speed` 4 m/s stay on: the review found them non-blocking,
  with limits now in [`docs/ALGORITHM.md`](docs/ALGORITHM.md) §6. `explained_run` delays a new STOP by at most 10
  hits (~1 s, ~22 m at 22 m/s) after an infrastructure-demoted hit. The ego veto blocks STOP onset beyond 25 m for an
  object receding faster than ~0.65 × the train speed, and must only be fed a measured speed (the LiDAR estimate, the
  default, or `speed_topic` / `odom_topic`): with a constant `ego_speed_mps` a standing train would veto a static
  person beyond 25 m. The launch file's docstring no longer suggests `ego_speed_mps:=22`.
- Full regression gate of the shell-off detector (`7464d80`) against the gate of the seal `3eeb106`
  ([`docs/evidence/cycle_2026-09-29/shell_off/`](docs/evidence/cycle_2026-09-29/shell_off/README.md)): PASS, no
  waivers, 6 gated metrics better, none worse. Five empty recordings STOP episodes / events / alarm frames
  13 / 11 / 40 → 12 / 8 / 39 (as with the three rules); ride 31 / 32 / 130 → 30 / 27 / 126 (2.3 episodes and
  2.1 events per km; with the three rules 28 / 26 / 123); set F false detections box1.0 12 (6 with the three
  rules), cable 3 → 0; set O, set F first detections and `doubleT_obstacle` identical. Removing `shell` from the
  three rules cost ride events / episodes 26 / 28 → 27 / 30 and box1.0 false detections 6 → 12, and gives the
  hanging cable back its STOP from 73.8 m instead of 21.0 m (synthetic). New seal
  `docs/evidence/detector_freeze_2026-09-29_shell_off.json`: 36 files measured at `7464d80`, source `075a20df…`,
  committed in `fe27068`; `1e2ed82`'s seal is kept as superseded ([`docs/DETECTOR_FREEZE.md`](docs/DETECTOR_FREEZE.md)).
- The approach, stated plainly: the three ideas came from other teams' open case 05 solutions, were rewritten here,
  passed the full gate, and one of them was then removed by our own safety review.

### Changed — three false-alarm rules from other teams on by default (29.09 evening; resealed at `1e2ed82`)

- `tracking.explained_run` 5, `explained_reasons` column, overhead, retro, shell (after Tactical-Inventor's
  gauge processor): a track with fixed infrastructure in its recent history needs 5 consecutive clean
  strict-gauge hits before a new STOP; a blocked track stays advisory, near escalation wins.
- `cluster.shell_min_top` 2.3 m (after TunnelGuard): a far tall floor-standing cluster that continues into the
  lining is infrastructure (reason `shell`).
- `tracking.ego_veto_min_speed` 4 m/s (after TunnelGuard): while the train moves, a track whose distance does
  not fall with the travel starts no STOP; the tracker integrates the LiDAR speed estimate (median of the
  last five, coasting through three unknown frames).
- Full regression gate on all organizer recordings (downloaded and cached this session; the sealed gate
  reproduced exactly): PASS, 7 gated metrics better, none worse. Ride 32 / 31 → 26 / 28 events / STOP
  episodes, five empty recordings 11 / 13 → 8 / 12, set F false detections box1.0 12 → 6, cable 3 → 0; set O,
  set F first detections and `doubleT_obstacle` identical. 1 279 tests pass on `7532a6b` (plus 6 subtests; 8
  deselected, they need local data caches; 74 dashboard tests). New seal
  `docs/evidence/detector_freeze_2026-09-29_competitor_rules.json` (at `1e2ed82`, comments only since `f67e4fb`, which
  makes the LiDAR speed estimate 4.3 -> 1.3 ms per frame with identical counts; the veto now costs +2.1 ms mean, +2.4 ms p95 on 360°
  frames and +1.7 / +1.6 ms on 120° frames, down from +7 / +8.5 ms on 360°).
- Measured and not shipped (every candidate's full gate: [`gate_table.md`](docs/evidence/cycle_2026-09-29/competitor_rules/gate_table.md)):
  `lowobj.min_top` 0.08 (loses the organizers' 10 cm box on a rail at 10-50 m in the ray-cast tunnel; the test now
  covers 25 and 50 m), the clean run with range demotions or shape signatures, `fresh_stop_evidence`, a quadratic
  edge margin (`gauge.edge_margin_per_100m2`, opt-in), far ring rails.
- No independent safety review of the three rules yet (done the same night: `shell` switched off, see the entry
  above). Known limits
  ([`docs/ALGORITHM.md`](docs/ALGORITHM.md) §6): a track beyond 25 m that moves with the train starts
  no STOP while the train runs at ≥ 4 m/s (and the veto trusts the LiDAR speed estimate); a new STOP
  next to known infrastructure waits for up to 5 clean hits; in the ray-cast synthetic tunnel a wide
  object taller than the envelope (3.1–3.6 m, like rolling stock) standing on the track at 60–150 m is
  CAUTION instead of STOP (`shell`; one-off check during the documentation audit, not committed). The
  range test that pastes a person at a fixed distance ahead of a moving train is what the veto blocks,
  so that test is not valid for moving windows with the veto on.

### Added — far rail evidence from ring crossings, opt-in (29.09; fails the gate, stays off; in the seal of `1e2ed82`)

- `scripts/screen_competitor_rules.py` applies a rule ported from another team's repository as a post-filter on the
  sealed detector's saved STOP detections and reports the false alarms it removes against the true detections it
  takes (empty recordings, `doubleT_obstacle`, set O with the independent judge's matcher, the ride's residual false
  events). It first reproduces the published `setO.json` exactly and refuses to run if it does not. Tests:
  `tests/test_screen_competitor_rules.py` (two read the committed judgement outputs and carry `realdata`).
- Result (evidence `docs/evidence/results/competitor_rule_screen_2026-09-29.json`): TunnelGuard's gravity rule would cut set O's
  `big_center` from 208 to 87 STOP frames (rejected); its shape rule removes 2 of 7 false episodes on the empty
  recordings for 10 m of range on the low board (not adopted); promoting centred `beyond_axis` /
  `beyond_height_ref` advisories would turn 325 advisories on the empty recordings into STOPs for 3 gains, all
  beyond 225 m (not adopted).
- The one idea that passed the filter is implemented and **off by default**: far rail evidence from single LiDAR ring
  crossings (`resense/farrails.py`, an idea of another team's repository, written from its description) as the
  evidence source of the disabled far-rail check (`track.rails_far_check_enabled` + new `track.rails_far_rings`;
  profile `configs/experimental_far_rail_rings.yaml`; `scripts/far_rail_yield.py` measures it on the recordings).
  With the flags off the per-frame output is bit-identical to `main`. On the ray-cast tunnel it corrects a wall bend
  that the rails contradict (axis 2.7 m off at 60 m -> 0.004 m) where the slab path does not; nothing is measured on
  real data at the time; measured later the same day on the recordings, it fails the gate (stations reach 34-47 m on
  real rails and a new low STOP at 3 m on `doubleT_platform`) and stays off.

### Changed — the experimental line is merged into `main` (29.09, PR #27)

- `catchup_startup_step` now defaults to **0**: every frame of a recording's first backlog is
  processed. The 5 Hz thinning added in the node change below (0.2) is an explicit option. The
  start-up figures below were measured with 0.2; with the default 0 the start-up is not measured.
- `tracking.thin_far_min_voxels` 4 → 3 (resealed): the full gate has 202 metrics unchanged and two
  synthetic Set F 0.5 m box metrics better; on the ride 5 of 11,271 frames went GO → CAUTION and no
  STOP frame changed ([`thin_far_threshold.md`](docs/evidence/cycle_2026-09-29/thin_far_threshold.md)).
- Opt-in experiments, all off by default and outside the score: cross-ring sparse evidence
  (`cluster.weak_min_rings`, `tracking.far_min_ring_count`), provenance-aware STOP onset
  (`tracking.fresh_stop_evidence`) and bed / rail low-object support (`lowobj.local_support_*`);
  their profiles are `configs/experimental_*.yaml`.
- The single GO at `doubleT_obstacle` frame 111 (and the CAUTION at 117 and 197) is closed:
  `tracking.stop_keep_low_s` = 0.3 continues an already reported low STOP on returns that miss the
  height threshold by at most `lowobj.straddle_keep_height_margin` = 0.03 m, and cannot start a track.
  STOP on 193 of 201 frames with no gap, offline on the raw recording and through the node in Docker
  in CI; the 27.09 detector gives 190 and the three gaps, and `stop_keep_low_s` = 0 brings them back.
  Tuned on this one recording. Evidence:
  [`docs/evidence/frame111_2026-09-29/`](docs/evidence/frame111_2026-09-29/README.md).
- Tests: 1,225 pass; 8 are deselected because they need data caches.

### Changed — health sector counts (29.09; resealed)

- `resense.health._sector_counts` counts `values >= edge` per edge instead of a per-value binary
  search. It compares a float32 cloud with float32 thresholds (the smallest float32 at least each
  edge), which gives the same counts as `np.histogram`. Randomised and edge-case tests cover this.
- It is the fastest counter in all 12 measured cells (NumPy 1.26 / 2.4, AVX-512 on / off, 127–890 k
  points). At 381 k points on the image's NumPy 1.26 without AVX-512 it takes 0.54 ms, against
  2.89 ms for the sealed search and 17.3 ms for `np.histogram`.
- Validation:
  - the full native gate on this change and on the unmodified source, both exit 0, all 207 compared
    metrics unchanged, no waivers;
  - 15 269 frames and set F's 3 060 rows identical outside timing;
  - 33 stress histories with no STOP change;
  - an independent review.
- A first variant was rejected at its speed step. The seal was replaced; the evidence is in
  [`health_compare_counts`](docs/evidence/cycle_2026-09-29/health_compare_counts/README.md).

### Changed — detector timing contract (28.09)

- `timing_ms.total` now includes health monitoring and result construction; `stages` retains the
  earlier interval. The health monitor consumes the previous complete call and publishes its
  one-frame sample age. Direct numeric health callers retain their existing semantics.
- Full native gate: all 208 non-latency comparison metrics unchanged, no waivers. Exact comparison:
  15,269 recorded frames and 30 set F cases / 3,060 rows with no non-timing output changes or
  invalid timing contracts. This fixes instrumentation; it claims no execution speed gain.
- Validation and captures: [`complete timing evidence`](docs/evidence/cycle_2026-09-28/complete_timing/default/README.md).

### Changed — ROS node (29.09; the detector is sealed and unchanged)

- **Faster, bit-identical decode:** `resense_ros/fastcloud.decode` returns the same arrays byte for
  byte as `resense.pointcloud.pointcloud2_to_arrays` (one x/y/z copy, one index gather): median
  20.3 → 16.6 ms at 360°, 7.4 → 4.8 ms at 120°; identical on both original bags (453 frames).
- **Start-up catch-up at 5 Hz** (the default of this change; since the merge of PR #27 the default
  is 0 and 0.2 is explicit): a recording's first backlog (the player's start-up burst, short
  ones included) is worked through `catchup_startup_step` = 0.2 s apart (every other 10 Hz frame,
  the rate the detector is validated on); a lone frame is processed at once; `0` = every frame.
- **Warm-up** (`warmup`, default true): before logging "listening", the node runs the decode and a
  throwaway detector on three synthetic frames (~0.7 s), so the first real frame costs what the
  next ones do (decode + detect ~31 + 42 ms instead of 49 + 72 ms).
- **Clean exit on Ctrl+C** (`rclpy.try_shutdown()`); launch used to report exit code 1.
- Two new node parameters, both launch arguments: `catchup_startup_step` (0.2 when added; 0 since
  the merge of PR #27), `warmup` (true); every other parameter unchanged.
- **Measured** with `catchup_startup_step` 0.2 (A/B through the jury chain against the image of 28.09,
  [`docs/evidence/node_startup_2026-09-29/`](docs/evidence/node_startup_2026-09-29/README.md)): at
  360° the results of the first 3 s are 38–105 ms old instead of 312–325 ms (median; 120–300
  instead of 829–1029 ms from a cold page cache), all results p95 212–344 instead of 410–447 ms,
  the first STOP 0.8–1.0 s after the first cloud; decisions identical.
- `scripts/check_dry_run.py` also prints the end-to-end latency over all results (start-up
  included) and the playback pace; `--min-playback-rate` fails a player slower than real time.

### Changed — documentation (29.09)

- README compacted to the jury path: run, what to look at, results, build / run / parameters; its
  results table of 28.09 moved verbatim to the archived changelog's "Dated status notes".
- `docs/EXPERIMENTS.md` compacted to the current results; the full experiment log (cited as
  "EXPERIMENTS §N") moved verbatim to
  [`docs/archive/EXPERIMENTS_log_2026-09.md`](docs/archive/EXPERIMENTS_log_2026-09.md).
- Dated records (quality cycles of 26–27.09, P4 audit notes, branch integration, next detector
  work, this file's full history) moved to [`docs/archive/`](docs/archive/README.md).
- The pitch and the overview video (deck, voice-over, defence on 23.10) are owned by P2.
- P2's branch `claude/amazing-fermi-t67v8g` merged: dense slides 5 and 15 simplified, the public
  PPTX / PDF and the overview MP4 rebuilt with the same claims; the demo runbook
  [`web/DEMO_HANDOFF.md`](web/DEMO_HANDOFF.md); the full P2 check on the rebuilt files 83 passed, 0 skipped.
- [`docs/SCORECARD.md`](docs/SCORECARD.md): the independent judgement of 28.09 evening only.

## 2026-09-28 — jury path: image default command, node input path, CI

- The image's default command is `ros2 launch resense_ros detector.launch.py freshness_mode:=replay`
  (input age from its publication by the player): a bare `docker run` + `ros2 bag play` gave
  `FAULT` on every message before. The node's own default stays `live`, for a LiDAR on a train.
- Input clouds read from their serialized bytes (`raw_input`) by `resense_ros/fastcloud.py`, not
  rclpy's conversion; the detector's input byte-identical on both original bags (checked in CI).
- RViz markers and the corridor cloud are built only while watched; the status reports
  `decode_ms`, `detect_ms`, `cpu_cores`, `rss_peak_mb`; `check_dry_run.py` prints end-to-end latency.
- CI in two stages: `checks` (ruff, parameter copy, detector seal) gates the three other jobs.
- Russian user guide on [GitBook](https://resense.gitbook.io/resense-docs/) (source `gitbook/`).
- Documented limitation of the sealed detector: one GO at `doubleT_obstacle` frame 111 (the rail
  object missed two frames in a row; [ARCHITECTURE](docs/ARCHITECTURE.md)). Closed on 29.09, see
  the merge entry above.

## 2026-09-27 — detector quality cycle; the submitted detector, sealed

- Envelope near the train (within 60 m, straight track): the union of the envelope measured from
  the rails and from the sensor axis, the frame the organizers place objects in (`gauge.reference`).
- Learned track opinion (`resense/models/`): may delay a doubtful STOP by at most 10 processed
  frames in a track's life, never within 25 m or for a standing body within 40 m; never a veto.
- Monitored-range caps from persistent sparse evidence; along-track association gate and column
  body width; far evidence for approaching tracks, advisory otherwise.
- Ride 32 events / 31 STOP episodes in-sample, 37 events (2.8 per km) on ride pieces the opinion
  never saw (43 without it); set O edge cube first STOP 5.2 → 35 m
  ([record](docs/archive/QUALITY_CYCLE_2026-09-27.md): gains per mechanism, caveats).
- Sealed after two independent review rounds and their fixes: manifest checked in CI by
  `scripts/detector_freeze.py` ([`docs/DETECTOR_FREEZE.md`](docs/DETECTOR_FREEZE.md)).
- `scripts/play_bag.sh`: load, node, play, print the decision changes in one command.

## 2026-09-26 — P3d detector and freshness controls

- Near-field escalation within 35 m and the wall keep: all 8 in-envelope set O objects STOP.
- STOP keep: a STOP track demoted only by a shape signature keeps its vote for at most 10 s.
- Rail heads ahead of a standing train at a fresh start no longer STOP; a calibration change keeps
  a confirmed STOP; `clear_distance` is capped at a lost reported track.
- Latency out of the decision: a p95 over 100 ms stays a health warning instead of turning GO into
  CAUTION (`health.latency_affects_decision: true` restores it).
- Freshness controls: the node reports source age and validity, holds an outstanding STOP until a
  fresh valid result, gives `FAULT` on stale input (`freshness_mode` live / replay); the dashboard
  expires stale status locally ([record](docs/archive/QUALITY_CYCLE_2026-09-26.md)).
- Start-up: a new recording's first backlog may lag up to 20 s (`catchup_startup_max_lag`), later
  stalls 5 s; CI's `offline-build` job uploads the image archive as a run artifact.

## 2026-09-25 — package version 1.0.0: offline delivery, C++ kernels, regression gate

- Offline delivery (the test stand has no internet): `scripts/export_image.sh` /
  `scripts/load_image.sh` (image archive + `.sha256`), `dry_run.sh` with `IMAGE_TAR=` and
  `OFFLINE=1`; CI rebuilds from the archive with Docker Hub blocked and plays bags through it.
- Release workflow: a pushed `v1.0.0-rcN` / `v1.0.0` tag builds, proves and publishes the archive.
- Optional C++ kernels (`native/`, merged 24.09; `RESENSE_NATIVE=0` forces numpy): identical
  output, 38–57 % less detector time; DBSCAN on scipy's cKDTree with scikit-learn's exact labels.
- `scripts/regression_gate.py`: six recordings, set O, ride and set F in one command; exit 1 on a
  gated regression.
- Station false alarms: the long overhead rule (only above 1.6 m) and `tracking.column_hold` 2,
  both decided on the ride with the gate ([`docs/DECISIONS.md`](docs/DECISIONS.md)).
- Organizers' objects: rail-shadow rules for a large near object, a thin-hanging-object stage,
  the free-hanging exemption of `floating`, a conservative `clear_distance`.
- 5 Hz input and ±3° re-mount robustness; opt-in shared-memory DDS (`RESENSE_DDS=shm`); a stock
  Fast DDS player in CI; the 2:50 overview video with Russian subtitles (`docs/video/`).

## v0.6.4 — 2026-09-24 (PR #10) and the rest of 24.09

- Node: 40-frame input queue, a backlog worked through one frame per `catchup_step` = 0.3 s of
  recording: first STOP on `doubleT_obstacle` at 1.59 s instead of 4.02 s.
- Node: `FAULT` publishes a complete snapshot (no obstacle, markers cleared), no stale STOP stays.
- Evaluation (PR #9): set O labelled exactly and graded per object, set S placed on the local bed,
  set F anchored placement; a LiDAR-only train-speed estimate measured and left off.
- Dashboard (PRs #6–#8, 23–24.09): Russian UI in the Metro style, cab view, built-in demo.

## v0.6.3, v0.6.2 — 2026-09-23 (PR #5)

- v0.6.3: a reported obstacle is held over one missed frame (`tracking.hold_misses` 1).
- v0.6.3: mount calibration every 10th frame, tilt applied from 0.75°; low-object width cap 2.2 m
  (a person lying across the track is kept); CI lint job (ruff).
- v0.6.2: objects straddling the envelope floor are clustered whole (the organizers' object on the
  rail 2 → 121 of 185 frames); confirmation 0.5 s; beyond 40 m without a rail pair: advisory.
- v0.6.2 node: reliable subscription, Fast DDS over UDP only in the image, `FAULT` / `NO_INPUT`
  before the first frame, cloud decoding 40 → 9 ms.

## v0.6.1, v0.6 — 2026-09-22/23 (PR #5)

- v0.6: the organizers' envelope, 2.1 × 3.0 m from 0.12 m above the rail head, for the strict
  decision, with a 0.35 m advisory zone; hanging cables near the axis are obstacles.
- v0.6: low-object stage at the rail heads, far-field rule for tall grounded objects, mount
  auto-calibration, health monitor, `GO / CAUTION / STOP / FAULT`, verified-clear distance.
- v0.6.1: mount tilt from the median of 20 observations (health warnings 42 % → 1.4 % of frames);
  node: either topic / frame pair, input switching and a detector restart per recording.

## v0.5, v0.4 — 2026-09-21/22 (PR #4)

- v0.5: track axis yaw from the rails, curvature from the walls; height reference trusted 20 m
  beyond the bed fit; persistence in seconds.
- v0.5: five infrastructure signatures (column, elevated, floating, edge, wall face); alarm frames
  on the five obstacle-free recordings 1 001 (v0.3) → 96.
- v0.4: ego-speed estimate and 5-frame accumulation beyond 40 m, verified bed extrapolation,
  retro-reflector rule, lateral smear guard.

## v0.0–v0.3 — 2026-09-15 (PR #1); tooling 16–21.09 (PRs #2–#3)

- v0.0 box corridor and raw DBSCAN → v0.1 rail self-calibration, range-normalised DBSCAN.
- v0.2 wall-based yaw and curvature → v0.3 nearer-boundary rule, 1.4 m gauge, structure filters.
- 16–21.09 (no detector change): node latency / FPS topics, parameter sync check, Docker CI job,
  dry-run script and checker, headless demo, launch arguments.
