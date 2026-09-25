# Changelog

> **Purpose:** what changed in ReSense, one entry per version or merge, newest first; the numbers
> are those measured when the change landed.
> **Audience:** jury (spec §5 "как менялось качество"), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-25 against `79109f5` · **Status:** current

Versions are the team's labels. The package metadata (`pyproject.toml`) says 0.1.0 up to PR #4,
0.6.3 from PR #5 (`1210580`) and 1.0.0 from `65a5305` (25.09). A pushed tag `v1.0.0-rcN` /
`v1.0.0` would be released by `.github/workflows/release.yml`; no tag or release is planned now
(deferred by the captain on 25.09: the system is still in development;
[`docs/CAPTAIN.md`](docs/CAPTAIN.md) §5). Results: [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md);
counts are "alarm frames / events (/ STOP episodes)" at full rate unless said. "Five bags" = the
five obstacle-free recordings (2 287 frames); "ride" = the 20-minute recording `new_data` (11 271
frames, 13 km, no obstacles).

## Unreleased (in development; package version 1.0.0)

Package version 1.0.0 (no tag or release yet: deferred, 25.09; detector v0.6.3 with the long
overhead rule on, node v0.6.4). Tests: 235 → 416 (+28 native kernels, +3 speed evaluation
helpers, +23 regression gate, +3 DBSCAN exactness, +5 late candidates, +53 release tooling, +5
overview video, 2 of them in the image, which has no `docs/`, +5 drop accounting and socket
buffers, +21 `load_image.sh`, +11 `check_no_network.py`, +4 `tracking.column_hold`, +20 DDS
transport, 19 of them in the image) in `tests/`, 13 in `web/demo`.

- **Dashboard shortcuts after a click, phone gutter (25.09, review of PR #12):** since `46a04bb`
  the page's key handler ignored every key while a button or link had the focus, so after a
  click on «Демо» or ▶ the arrow keys did nothing, and on a view tab Space did nothing, until a
  click on empty space. Now
  only text entry (`input`, `select`, `textarea`, contenteditable, `role=textbox`) keeps every
  key; a focused button or link keeps only Space (its own click, so play/pause never fires
  twice); a view tab leaves Space to play/pause and keeps its own ←/→ (they switch the view, not
  the frame). At phone width the page gutter is 16 px like the header (was 14 px).
  `web/README.md`: roslib is bundled (it still said CDN), the report button is «Скачать отчёт».
  Web tests 11 → 13.
- **Correction of the "stock Fast DDS" host-console finding (25.09 evening):** the second team
  VM's host had no Fast DDS RMW (`ros-humble-ros-base` and `ros-humble-rmw-cyclonedds-cpp` in one apt
  call install none), so its "Fast DDS" host players, which delivered 0–1 of the 201 360° clouds at
  `rmem_max` 212992, were CycloneDDS. A genuine stock Fast DDS player passed at 212992 on the first
  and third team VMs, over UDP and in shm mode (EXPERIMENTS §3b, `evidence/dry_run_2026-09-25_3/`);
  README step 0 stays (CycloneDDS needs it, Fast DDS does not mind); VM_GUIDE §1 now installs
  `ros-humble-rmw-fastrtps-cpp` explicitly and checks the loaded RMW.
- **Opt-in shared-memory transport, `RESENSE_DDS=shm` (25.09, default off):** built after a host
  player on the second team VM delivered 0–1 of the 201 360° clouds over UDP at Ubuntu's `rmem_max`
  212992; that player turned out to be CycloneDDS (entry above). `docker run … -e RESENSE_DDS=shm` (with `--ipc=host`): the
  entrypoint switches to shared memory + UDPv4 (`docker/dds_transport.sh`,
  `docker/fastdds_shm_udp.xml`) and starts `docker/fastdds_shm_share.py`, which sets the node's own
  Fast DDS port and data segments in `/dev/shm` to 0666: Fast DDS 2.6 creates them 0644 (Boost's
  default, then `fchmod`) with no option to change it, and a player of another uid must open them
  read-write, with no UDP fallback once it sees shared-memory locators of its own host. Falls back
  to UDP with a WARN without `--ipc=host`; an invalid value means UDP; one INFO line names the mode.
  The default (UDP only) is unchanged. CI: `NODE_DDS=shm scripts/console_test.sh` with the stock
  uid-1000 player (asserts the mode line, the 0666 segments and that each play mapped a root-owned
  port of the node) and with the image's UDP-only player. The VM run that decides the default:
  [`docs/VM_GUIDE.md`](docs/VM_GUIDE.md) §4.6. +20 tests (`tests/test_dds_transport.py`).
- **`tracking.column_hold` 2: the `roundT_doubleT` dry-run alarm (`fce04aa`, `d117c8c`, 25.09,
  delegated by the captain):** the VM dry run of 25.09 failed `--expect-clear --max-alarm-frames 2`
  on `roundT_doubleT` with 3 alarm frames at 111–115 m in all 10 ROS captures. Replayed offline
  (new `scripts/replay_node_frames.py`, the frames the node processed): a column 0.3–1.1 m off the
  far axis, tracked from 149 to 101 m, demoted as `column` in the frames that show more than 2.2 m
  of it and in the gauge in the others; the "2 known frames at 128–130 m" were the same column seen
  from the cache (1 cm coordinates), not the catch-up. New `tracking.column_hold`: a track demoted as
  a column in that many of its last 10 hits stays advisory. Pre-registered 3 / 2 / 1, the highest
  keeping every capture at ≤ 2 alarm frames and passing the gate chosen: 3 fails the gate (ride STOP
  episodes 39 → 40), 2 passes with 7 gated rows better: `roundT_doubleT` 2 / 1 / 1 → 0 / 0 / 0, five
  bags 60 / 14 / 17 → 58 / 13 / 16, ride 197 / 46 / 39 → 187 / 46 / 39, set F straight false
  detections 56 → 35; `doubleT_obstacle`, set O and set F detections identical; the captures keep at
  most 1 alarm frame (the trackside frame at 53 m). Cost: a person who stood in front of a column for
  ≥ 2 frames and steps onto the axis is a STOP 8 frames after the step instead of 4. New gate
  baseline `docs/evidence/results/regression_baseline_2026-09-25_ride_column.json`.
  [`column_hold_2026-09-25.json`](docs/evidence/results/column_hold_2026-09-25.json),
  [EXPERIMENTS §3a](docs/EXPERIMENTS.md).

- **P4: SCORECARD #13 robustness measured (`b26dc16`, 25.09, P4):** `scripts/robustness_check.py`
  replays the six bags at 5 Hz and with a +3° roll / pitch re-mount before calibration: the five
  empty bags go from 13 false events as recorded to 13 / 16 / 17 (`roundT_doubleT` 0 → 3 / 2 / 1;
  frames recorded for P3); a `tracking.zone_min_fraction` 0.7 trial was rejected (it cost
  `doubleT_obstacle` 2 labelled hits and delayed its first alarm 11 → 13); frames 804–1 509 of
  `cloud_with_fake_obj` (706, not used for tuning) give 0 false frames. Fix open.
  [`scorecard13_2026-09-25.json`](docs/evidence/results/scorecard13_2026-09-25.json), [EXPERIMENTS
  §1g](docs/EXPERIMENTS.md).
- **Long overhead rule only above 1.6 m (`3bf6324`, `0bb1ba3`, 25.09, code review, approved by the
  captain):** the along-track branch of the `floating` signature skipped the
  `signature_min_lateral` guard, so a cable tray, duct or pipe fallen onto the axis and hanging
  0.7–1.9 m above the rail (e.g. 4.0 × 0.3 × 0.5 m at 60 m) was advisory instead of a STOP. New
  `cluster.floating_long_min_bottom` 1.6: the branch needs the cluster's lowest point above it.
  Pre-registered 2.0 / 1.8 / 1.6 m, the highest keeping every gain chosen: 2.0 and 1.8 m bring back
  the ride event at 105–110 m (bottom 1.68–1.92 m; ride 197 / 46 / 39 → 204 / 47 / 39 and
  202 / 47 / 40); 1.6 m is identical frame by frame on the six recordings, the ride, set O and set F
  straight, so `regression_baseline_2026-09-25_ride.json` stays the baseline. A long cluster near
  the axis with its bottom above 1.6 m stays advisory (ALGORITHM §6). +2 tests in
  `tests/test_late_candidates.py` (the classification; the box end to end on the ray-cast tunnel).
  [`long_rule_bottom_2026-09-25.json`](docs/evidence/results/long_rule_bottom_2026-09-25.json),
  [EXPERIMENTS §1f](docs/EXPERIMENTS.md).
- **The captain's decisions (25.09):** no tags or releases now, the system is still in
  development: `.github/workflows/release.yml` and the release scripts stay, inert until a tag is
  pushed, and every plan item that scheduled a tag or a release is deferred. The submission is
  handled by the captain personally with all its links: `docs/SUBMISSION.md` removed, its links
  replaced (the jury commands in the README, the dry-run procedure in README "Acceptance test and
  CI", `scripts/dry_run.sh` and the VM brief (now `docs/VM_GUIDE.md`), the offline delivery in ARCHITECTURE
  "Deployment without internet"). Deployment (image archive, clean-machine and offline dry run on
  the 8-core stand-in) and the presentation (deck, team slides, video voice-over) come later.
  [`docs/CAPTAIN.md`](docs/CAPTAIN.md) C12, C13, C21, §9.
- **VM kit reduced to instructions (25.09, the captain):** `scripts/vm/` removed (`setup_vm.sh`,
  `fetch_data.sh`, `run_plan.sh`, `lib.sh`, `stream_cache.py`; the code review had found the
  feature branch built in as the default clone target). Its brief is now
  [`docs/VM_GUIDE.md`](docs/VM_GUIDE.md): plain commands of the repository's tools with variables
  the reader sets, the ride streamed split by split (`curl | zstd | tar --to-command` into
  `scripts/cache_frames.py`, one split file on disk at a time), the offline rehearsal as steps with
  the restore armed first (IPv4 and IPv6, never saved). [`docs/CAPTAIN.md`](docs/CAPTAIN.md) §9.
- **Script fixes (`1fc127f`, `163f34b`, `ade8a97`, 25.09, code review):** `regression_gate.py`
  fails a gated baseline metric missing in this run ("missing in this run", exit 1; `--allow
  'ride.*' --allow 'set_F_straight.*'` accepts a run without the ride on purpose), so a machine
  without `new_data` no longer passes the `_ride` baseline unchecked; `load_image.sh` normalises
  the expected sha256 (any case; Get-FileHash / certutil / sha256sum / BSD forms; no sum = exit
  2); `check_no_network.py` probes IPv6 (literals and each host's AAAA addresses) as well as IPv4
  and prints the result per family. +6 gate tests, `tests/test_load_image.py` (21),
  `tests/test_check_no_network.py` (11).
- **Drops of the 25.09 dry run explained; the node and the checker count them apart (25.09):** of
  the 20 frames "dropped after 5 s" on `doubleT_obstacle`, 16 were the start-up catch-up's own skips
  (it ran to +7.7–7.9 s after the player's preload) and 4 are frames the recording itself lacks.
  The status adds `node.catchup_skipped` and `node.catchup`; `scripts/check_dry_run.py` counts drops
  after the later of 5 s and the end of the start-up catch-up (at most 15 s, `--max-settle-s`) and,
  with `--bag` (passed by `dry_run.sh`), the recording's messages not processed. The node warns at
  start when `net.core.rmem_max` is below 32 MiB (a CycloneDDS player then delivers no 360° cloud),
  the image asks for 32 MiB receive buffers, and the ROS package defaults BLAS / OpenMP to one
  thread outside the image. No processed frame or decision changes.
  [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) §3a, §3b.
- **Long overhead rule on, short signatures off (`935eecf`, `48411f2`, 25.09, A for the
  captain):** decided on the 20-minute ride with the regression gate against pre-registered
  criteria
  ([`rules_decision_2026-09-25.json`](docs/evidence/results/rules_decision_2026-09-25.json)).
  `cluster.floating_long_min_length` 3.0: ride 204 / 47 / 39 → 197 / 46 / 39 (3.5 events per km),
  five bags 107 / 20 / 27 → 60 / 14 / 17; set O, `doubleT_obstacle` and set F straight identical.
  `cluster.short_signature_max_length` stays 0: +6 ride STOP episodes on top (limit +5) for +49
  set O STOP frames. New gate baseline with the ride and set F straight:
  `docs/evidence/results/regression_baseline_2026-09-25_ride.json`. The pinned default in
  `tests/test_late_candidates.py` follows the change. [EXPERIMENTS §1f](docs/EXPERIMENTS.md).
- **Overview video (`798a28f`, `5a15c7c`, 25.09, A for P2):** `docs/video/resense_overview.mp4`,
  2:50, 1920×1080 H.264 (yuv420p, 25 fps, faststart, no audio track, a chapter per block),
  20.6 MB: the seven blocks and shot list of PRESENTATION «Сценарий видео», a sidebar with each
  block's numbers marked real / our synthetic / organizers' synthetic, the narration burned in as
  Russian subtitles and written to `resense_overview.ru.srt` with the same timings for a later
  voice-over; the closing card names the release `v1.0.0`. `scripts/make_overview_video.py` holds
  the cut in one table and renders it with Pillow (Moscow Sans) and libx264;
  `tests/test_overview_video.py` keeps the table, the .srt and the ≤ 25 MB budget consistent.
- **CI: the release archive's runtime image plays bags (`abbbc08`, 25.09):** after the offline
  rebuild, the `offline-build` job makes the two synthetic bags on the runner and plays them
  through `resense:<version>` exactly as `load_image.sh` loaded it from the release archive
  (checked: the built layers, the version / commit labels, no open3d / rosbags, rosbag2 with
  sqlite3), on a `docker network create --internal` network: `check_no_network.py`, the node on
  its default command, a /resense/status recorder, a uid-1000 player of the same image,
  `check_dry_run.py --expect-obstacle --expect-inputs 2`. Until then every bag in CI went through
  the `WITH_TOOLS=1` image. `continue-on-error` removed: the job gates (the offline rebuild passed
  on all four runs made with it). First run green: 36122640174 (`5a15c7c`).
- **Version 1.0.0 and the release workflow (`65a5305`, `ee70f00`, `eabe0cc`, 25.09):** the four
  version declarations say 1.0.0 (kept equal by `tests/test_release.py`); the node's start line
  ends with `; resense 1.0.0`. `.github/workflows/release.yml`: a pushed `v1.0.0-rcN` / `v1.0.0`
  tag builds the runtime archive, proves it (removed, loaded back, both smoke bags through the
  loaded image with no internet and in the `--net=host` form) and publishes the GitHub release
  with the archive, `.sha256` and `SHA256SUMS`. Scripts: `release.sh` (manual),
  `publish_release.sh`, `verify_release.sh`, `internal_net_test.sh`, `release_meta.py`; any other
  tag name (`v1.0-rc1`, `v1.0-final`) publishes nothing.
- **Regression gate (`ca557cb` … `5017dec`, 25.09, A for P4):** `scripts/regression_gate.py`, one
  command and one JSON: the six recordings and set O, plus the ride and set F straight where
  cached. `--baseline` prints better / same / worse per metric and exits 1 on a gated regression;
  `--allow` covers intended trade-offs. Baseline
  `docs/evidence/results/regression_baseline_2026-09-25.json` is identical to the 24.09 numbers;
  the same code passes on the numpy path, `--set cluster.min_points=8` fails (it adds platform
  events). The merged `8932f3a` passes with every gated metric the same
  ([its JSON](docs/evidence/results/regression_gate_2026-09-25_8932f3a.json)).
  [EVALUATION §3 step 6](docs/EVALUATION.md).
- **DBSCAN on cKDTree (`508b04a`, 25.09, A for P3):** `resense.clustering.dbscan_labels`
  replaces scikit-learn's DBSCAN with exactly the same labels (9 240 real calls, random sets with
  distance ties, and the image's library versions); per-frame output identical on all 3 998
  cached frames, on both paths; −1.3…−2.6 ms per frame on the native path with the image's
  libraries. The in-detector forward crop and the bed-height reuse were measured and not shipped
  (no gain on the native path). [ARCHITECTURE "Native kernels"](docs/ARCHITECTURE.md).
- **Opt-in detector flags for the go / no-go of 26.09 (`fa99929`, `8631e4c`, 25.09):**
  `cluster.short_signature_max_length` (P3 / P4 short-signature rule; set O 303 → 352 inside STOP
  frames, five bags 107 / 20 / 27 → 113 / 22 / 29, gate FAIL on 5 rows) and
  `cluster.floating_long_min_length` (the overhead structure along the track at the platform;
  five bags → 60 / 14 / 17, set O unchanged, gate PASS). Both were merged 0 (off), default output
  identical (decided the same day on the ride: see the first entry). The far-rail check was
  measured: no effect on the six recordings and set O.
  [EXPERIMENTS §1f](docs/EXPERIMENTS.md).
- **Stock Fast DDS console in CI and the 8-core bench kit (`fbef12b`, `8242c3e`, 25.09):**
  `scripts/console_test.sh` takes `PLAYER_DDS=stock` (a uid-1000 player and listener with Humble's
  default `rmw_fastrtps_cpp`: no XML profile, shared memory on, their own segments in `/dev/shm`
  asserted, the listener must hear `STOP`) and `PLAYER_ENV`; a new CI docker step runs it, green on
  its first run (36112092652, `8932f3a`). The node announces no shared-memory locators, so stock
  clients reach it over UDP. `scripts/bench_8core.sh` (with `scripts/bench_summary.py`) records
  the build, the dry runs with the node native and numpy, the console tests, `docker stats` and
  the offline timing into `docs/evidence/bench_<date>/`; `dry_run.sh` takes `DOCKER_ARGS`,
  `check_dry_run.py` reads `*.gz` captures.
- **Deck and video script (`16d2a07`, `8e843d8`, 25.09, A in P2's lane):** the public deck rebuilt
  (16 slides: the organizers' objects, the anchored 154 m next to 150 m legacy in the same pairs,
  «~210 м — предел отражений в тоннеле», the real-data UI capture, C++ kernels / train speed /
  GPU; bar values shown in both charts); a 2–3 min narrated-video script with a shot list in
  [`docs/PRESENTATION.md`](docs/PRESENTATION.md); a new silent clip
  `docs/video/fake_objects_cab.mp4` (the organizers' 2 × 2 m box, STOP from 98 m on a moving
  train). The 17 team placeholders stay in the public build by design.
- **`main` green again (25.09):** PR #11 (merged 06:51 UTC, `5de0844`) brought the near-bed gate
  fix `7df1796` to `main`; CI run 36104815305 is green (`main` was red about 12 h). `main` is
  merged into this branch (`4f004d9`).

- **Offline delivery (25.09):** the test machine has no internet (organizers, 25.09,
  [`docs/organizers/answers.md`](docs/organizers/answers.md) §7), so `docker build` cannot run
  there. `scripts/export_image.sh` writes the runtime image as `dist/resense-image-<version>.tar.gz`
  + `.sha256` (built from `git archive HEAD`, OCI version / revision labels, BuildKit inline cache,
  the base image's tag inside); `scripts/load_image.sh` checks the sum, runs `docker load` and
  checks the image with `--network none`; `scripts/check_no_network.py` asserts that a container
  reaches nothing; `scripts/dry_run.sh` takes `IMAGE_TAR=<archive>` (load instead of build) and
  `OFFLINE=1` (node, player and recorder with `--network none`). README step 1 is now `docker load`
  (`docker build` with internet). CI: the docker job saves, removes and loads the built image and
  plays the synthetic bags through it with `--network none` and on an internal Docker network; the
  new job `offline-build` (best effort at first; a gate since `abbbc08`) rebuilds from the loaded
  archive with Docker Hub blocked. Run-time audit: no network use in the node, launch file,
  entrypoint or compose services; the dashboard's roslib (1.4.1, BSD) is bundled in
  `web/assets/vendor/` instead of loaded from a CDN. `dist/` is excluded from the Docker build
  context. The Dockerfile's layers are unchanged (a header comment only). [ARCHITECTURE
  "Deployment without internet"](docs/ARCHITECTURE.md).

- **Dashboard restyle (`46a04bb`, P2, 24.09):** dashboard and label tool in the Metro style
  (Moscow Sans from the supplied style archive, primary red `#E4000D`, styles in
  `web/assets/dashboard.css` / `label-tool.css`), `web/demo/capture_gallery.py` refreshes the
  `docs/images/` screenshots; 11 web tests.
- **Train-speed evaluation (`396755f`, `93c6eaa`, 24.09):** tooling and measurements, no detector
  change. `scripts/eval_real.py --nominal-stamps` (stamps snapped to the 10 Hz rotation, as the
  node's header clock) and `--speed-ref` (a per-frame reference speed handed in as odometry);
  `scripts/speed_reference.py` (frame-to-frame ICP reference), `speed_accuracy.py`,
  `speed_setf.py`, `speed_static_check.py`, `speed_timing.py`; 3 tests. The LiDAR-only estimator
  is accurate (median error 0.06–0.08 m/s, p90 ≤ 0.20 m/s on 55–96 % of the moving frames,
  +6.6–6.8 ms per frame), but even a perfect speed does not improve the organizers' check: five
  bags 103 / 18 → 111 / 16, no earlier first STOP on set O, 6 → 17 false STOP frames on the box
  outside. `accumulation.estimate_speed` stays `false`; a given speed is still honoured. Raw:
  [`experiments_2026-09-24_train_speed.json`](docs/evidence/results/experiments_2026-09-24_train_speed.json);
  [EXPERIMENTS §9](docs/EXPERIMENTS.md).
- **`cloud_with_fake_obj` corrected (24.09):** the organizers' objects stand still in the tunnel
  and the train drives forward ~2.0 km at 1.4–20 m/s; the docs had said the objects move on their
  own while the train backs up. Fixed in DATASET, P4_AUDIT, EXPERIMENTS §2e, QUESTIONS (Q1 lost
  the sentence built on it) and `scripts/label_fake_objects.py`.
- **C++ kernels (merge `d1a2d0c`, 24.09):** optional `native/resense_native.cpp`, a C ABI loaded
  with ctypes by `resense/_native.py`, built as an optional setuptools extension
  (`RESENSE_NATIVE=0` forces numpy): per-bin percentiles, the full-cloud passes of the track and
  corridor stages, the health visibility. Detector time −38…−57 % (`roundT_doubleT`
  62.4 → 33.5 ms, `doubleT_obstacle` 81.3 → 34.6 ms, p95 at 360° 107 → 51 ms; sandbox under load),
  0 differing frames of 3 998 real frames with numpy 1.26 and 2.4; 28 tests. DBSCAN, the mount
  rotation and the health azimuth histogram are not ported. The Docker build with the kernels is
  proven by CI run 36058665640 (`d1a2d0c`: in-image tests and both ROS smoke tests green).
  [ARCHITECTURE "Native kernels"](docs/ARCHITECTURE.md).
- **`7df1796` (merged `7415495`, 24.09): near-bed gate fix, on `main` through PR #11 (25.09).**
  `537e220` made the opt-in near-bed path miss the synthetic 30 × 30 × 10 cm bed box at 12–28 m
  (3 failing tests in `tests/test_envelope.py`): `near_min_points` 10 → 5,
  `near_min_length` 0.18 → 0.0, the other gates kept, the per-bin loop vectorised with identical
  output. Five bags with the path on: 459 / 107 / 72 (`4b5786b` gates 1 035 / 145 / 42, `537e220`
  141 / 28 / 33); defaults unchanged.
  [EXPERIMENTS §1e](docs/EXPERIMENTS.md).
- **`194b3e7` (24.09): criteria judgement and documentation revision.** New
  [`docs/SCORECARD.md`](docs/SCORECARD.md) (two independent judges, 60 / 100, judged at
  `4b5786b`); one format for every team-written document (header block, RU summary, dated
  numbers), [`docs/README.md`](docs/README.md) index, this changelog, `docs/archive/`,
  `docs/evidence/results/`; the separate review files removed (superseded by SCORECARD). Later on
  24.09: the train-speed and GPU studies (EXPERIMENTS §9,
  [ARCHITECTURE "GPU: evaluated, not used"](docs/ARCHITECTURE.md)).
- **`537e220` (24.09, P3):** the opt-in central near-bed path gets stricter gates
  (`lowobj.near_min_excess` 0.05, `near_max_width`, `near_min_length`, `near_min_height`,
  `near_min_bed_lateral_bins`, `near_min_points` 10). `lowobj.near_enabled` stays `false`; the new
  shipped key `lowobj.min_length` defaults to 0, so the default path is unchanged. It turned
  `main` red (the bed box, fixed by `7df1796` above).
- **`4b5786b` (PR #9, 24.09, P4):** evaluation, not detector: set S objects placed on the local bed
  (22 of 67 visible hits against 29 of 68 with the old height), tracker reset per injected
  sequence, event identity `(seq, track id)`, per-sequence time and distance, one-to-one matching,
  `--reflectivity`, separate random streams; set F `--placement-mode anchored` and
  `scripts/compare_setf.py` (straight track: person 154 m anchored against 150 m legacy); the
  organizers' `cloud_with_fake_obj` labelled exactly (`labels/cloud_with_fake_obj.json`) and graded
  per object (`scripts/score_fake_objects.py`: 2 × 2 m box from 98 m, plank from 82 m, 0.3 m cubes
  from 34–43 m); tests 199 → 235. Record: [`docs/P4_AUDIT.md`](docs/P4_AUDIT.md).
- **`41b7ae7` (24.09):** the organizers' experts' answers on the LiDAR mount and switches
  ([`docs/organizers/mount_and_switch_qa.md`](docs/organizers/mount_and_switch_qa.md)).

## v0.6.4 — 24.09 (`de98266`, PR #10)

- Node: the input holds 40 frames (`input_queue_depth`) and works through a backlog one frame every
  `catchup_step` = 0.3 s of recording, from the recording's first frame. Through ROS in Docker the
  first STOP on `doubleT_obstacle` comes at 1.59 s of recording time instead of 4.02 s, the largest
  gap in the first 5 s is 0.40 s instead of 2.07 s, no scene reset (1–2 per run before);
  `roundT_doubleT` 241 of 252 frames processed (223 before); ~0.25 GB more memory at 360°
  ([EXPERIMENTS §3b](docs/EXPERIMENTS.md); raw captures not committed).
- Every number re-measured on the current code: per-frame output identical to v0.6.3 on all
  13 759 real frames; set F round 3 on the moving ride.

## 24.09 (`a92625e`, direct push, P3)

- Node: `FAULT` publishes a complete snapshot (no obstacle, distance −1, no detections, markers
  cleared, health `error`), so no stale STOP stays latched.
- Two opt-in stages, both off: the central near-bed path (`lowobj.near_enabled`) and the
  station-wall axis check (`track.rails_far_check_enabled`). Output identical to v0.6.3 on all 13
  759 frames (re-measured in `de98266`).
- `scripts/far_range_eval.py --placement-mode independent`; `scripts/require_docker.sh`: the Docker
  scripts exit 3 without a daemon; `smoke_test.sh` runs only inside the image.

## Dashboard — 23–24.09 (PRs #6–#8, P2)

- `web/index.html`: Russian UI in the Moscow Transport style, flat cards, Montserrat bundled in
  `web/assets/fonts/`, cab view, built-in 60-frame demo, run-summary card, «Отчёт» report download,
  drag-and-drop replay; screenshots in [`docs/images/`](docs/images/README.md); 11 web tests.
- CI repair `36ed07c`: `lowobj.near_min_width` 0.25 → 0.24, web-test distance window 36–72 m.

## v0.6.3 — 23.09 (measured on `c1c2b6a`, merged in PR #5 as `1210580`)

- A reported obstacle is held over one missed frame (`tracking.hold_misses` 1): STOP episodes on
  the obstacle-free data 88 → 66, events unchanged.
- Mount calibration measures every 10th frame only and applies a tilt from 0.75° (was 0.5°).
- Low-object width cap 1.6 → 2.2 m (a person lying across the track is kept).
- Also in PR #5: `Detector.process` split into one method per stage (identical output on 2 930
  frames); CI `lint` job (ruff); the RViz layout subscribes the clouds reliable;
  `scripts/start_offsets.py`; dry-run checker `--settle-s`, `--obstacle-in`.
- Five bags 107 / 20 / 27; ride 204 / 47 / 39; person 58 of 61 frames from frame 11; object on the
  rail 124 of the 126 frames after the person leaves (127 of 185 by its own detection); timing
  42–64 ms mean, p95 53–78 ms (4-vCPU dev VM, 23.09).

## v0.6.2 — 23.09 (PR #5)

- Objects straddling the envelope floor are clustered whole (≥ 0.35 m across, ≤ 0.8 m along):
  the organizers' object on the rail 2 → 121 of 185 frames (118 of 126 after the person leaves).
- Confirmation 0.5 s instead of 0.3 s (`tracking.confirm_time_s`).
- Without a rail pair in the near range, clusters beyond 40 m are advisory (`gauge.no_rail_range`).
- Node: `input_reliability: auto` (reliable subscription); the image runs Fast DDS over UDP only;
  `FAULT` / `NO_INPUT` before the first frame; cloud decoding 40 → 9 ms.
- Five bags 81 / 20; ride 164 / 47 (3.6 per km).

## v0.6.1 — 22–23.09 (PR #5)

- Mount tilt from the median of 20 observations instead of the first 5 frames: health warnings on
  42 % → 1.4 % of the frames.
- Node (after the organizers' written answers of 23.09): either topic / frame pair, input switching
  between recordings, detector restart per recording (`input_switch_timeout`, `new_input_gap`,
  `hole_reset_gap`).
- Five bags 104 / 30; ride 289 / 82 (6.3 per km); person 58 of 61 frames from frame 11.

## v0.6 — 22.09 (PR #5)

- The organizers' Q&A answers: envelope 2.1 × 3.0 m from 0.12 m above the rail head with a 0.35 m
  advisory zone; low-object stage at the rail heads (`resense/lowobj.py`); hanging cables near the
  axis no longer demoted; far-field rule for tall grounded objects; mount auto-calibration
  (`resense/calibration.py`); health monitor, `GO / CAUTION / STOP / FAULT` on `/resense/decision`,
  verified-clear distance, `DiagnosticArray`, watchdog.
- Five bags 83 / 25; ride 258 / 74.

## v0.5 — 21–22.09 (PR #4, merged as `0267281`)

- Track axis yaw from the rails, curvature 1/R from the walls, rate limits and side-agreement caps;
  height reference trusted 20 m beyond the bed fit or as verified; five infrastructure signatures
  (column, elevated, floating, edge, wall face); persistence in seconds; the LiDAR-only speed
  estimator off by default.
- Five bags 1 001 / 192 (v0.3) → 96 / 32; person 66 of 71 labelled frames, first alarm frame 7.

## v0.4 — 21.09 (PR #4, branch commit `f4e311f`)

- Ego-speed estimate and 5-frame accumulation beyond 40 m, verified bed extrapolation,
  retro-reflector rule, lateral smear guard. Five bags 1 016 / 187.

## 16–21.09 (PRs #2–#3, `cd50f42`, `f2c57e5`) — no detector change

- Node latency / FPS topics and status, parameter sync check, Docker CI job, dry-run script and
  checker, headless demo, launch arguments, one data-path rule.

## v0.0–v0.3 — 15.09 (PR #1, `f64f881`)

- Day 1 on subsampled frames (231 frames of the five bags): v0.0 box corridor and raw DBSCAN, 149
  alarm frames → v0.1 rail self-calibration, voxelised range-normalised DBSCAN, 92 → v0.2
  wall-based yaw and curvature, 76 → v0.3 nearer-boundary rule, 1.4 m gauge, hardware / linear /
  wall filters, 67. At full rate (21.09) v0.3 gives 1 001 / 192.
