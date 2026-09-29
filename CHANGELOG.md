# Changelog

> **Purpose:** what changed in ReSense, newest first, readable in two minutes; the full dated
> history with every measurement: [`docs/archive/CHANGELOG_2026-09.md`](docs/archive/CHANGELOG_2026-09.md).
> **Audience:** jury (spec §5 "как менялось качество"), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-29: each section against the archived changelog, the 29.09 node
> change against the node source and launch file; every relative link · **Status:** current

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), loosely; versions up to v0.6.4
are team labels, the package is 1.0.0 since 25.09. Figures are the team's, measured when a change
landed (detector figures on the 1 cm frame cache). Current results: [`README.md`](README.md),
[`docs/SCORECARD.md`](docs/SCORECARD.md). "Set O" = the organizers' synthetic objects; "ride" = the
20-minute, 13 km recording `new_data`.

## [Unreleased] — package 1.0.0

**Release status:** no git tag and no GitHub release exist yet. When the tag `v1.0.0` is pushed,
[`.github/workflows/release.yml`](.github/workflows/release.yml) builds and proves the runtime image
archive and publishes it (`.tar.gz`, `.sha256`, `SHA256SUMS`) as the assets of the GitHub release
`v1.0.0`; until then: the CI artifact of a `main` run (GitHub login) or `scripts/export_image.sh`.

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

### Added — far rail evidence from ring crossings, opt-in (29.09; seal to be renewed after the gate)

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
