# Changelog

> **Purpose:** what changed in ReSense, one entry per version or merge, newest first; the numbers
> are those measured when the change landed.
> **Audience:** jury (spec §5 "как менялось качество"), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-28: the 28.09 entries against the node captures, `docker/Dockerfile` and the committed per-frame outputs; "Dated status notes" moved verbatim from the README; the 27.09 entries against the quality-cycle record (older entries record their own date) · **Status:** current

Versions are the team's labels. The package metadata (`pyproject.toml`) says 0.1.0 up to PR #4,
0.6.3 from PR #5 (`1210580`) and 1.0.0 from `65a5305` (25.09). A pushed tag `v1.0.0-rcN` /
`v1.0.0` would be released by `.github/workflows/release.yml`; releases were deferred by the
captain on 25.09 (the system was still in development), and the `v1.0.0` release is now scheduled
for 28.09 21:00 Moscow time, not yet published ([`docs/CAPTAIN.md`](docs/CAPTAIN.md) §5). Results: [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md);
counts are "alarm frames / events (/ STOP episodes)" at full rate unless said. "Five bags" = the
five obstacle-free recordings (2 287 frames); "ride" = the 20-minute recording `new_data` (11 271
frames, 13 km, no obstacles).

## Unreleased (package version 1.0.0; `v1.0.0` scheduled for 28.09 21:00 Moscow time)

- **Documentation corrected after the fresh re-judgement of 28.09 (P1; detector sealed, unchanged):**
  the GO at `doubleT_obstacle` frame 111 (and CAUTION at 117, 197) that every node capture of the
  full recording shows is documented as a limitation of the frozen detector: a confirmed low track
  missed two frames in a row is released by `tracking.hold_misses` 1 (`docs/ALGORITHM.md` §6,
  `docs/ARCHITECTURE.md` "Known limitations"); the rail object is quoted as 123 of 126 on the raw
  recording and through the node, 125 of 126 on the frame cache. The learned opinion's delay is
  stated as 10 processed frames (~1 s at 10 Hz, ~2 s at 5 Hz, longer in a catch-up), not "≤ 1 s".
  The end-to-end latency is given over current results and over all frame results with the
  start-up (p95 at 360° 243–455 ms cached, 418 ms cold; `e2e_all_frames.py`), and the disputed
  "before" baseline with judge A's figures. Judge A's per-frame outputs of the sealed detector
  (six recordings, set O offline and through the node, two ride segments, set F) are added with
  their provenance and a recompute script (`docs/evidence/judge_outputs_2026-09-28/`): five empty
  recordings 8 events / 23 alarm frames / 7 STOP episodes on the raw recordings (11 / 40 / 13 on
  the cache), set O 414 of 801 (411), the outside box 7 false STOP frames (6; judge A's matcher 9).
  The ground truth's dependence on the team's own tools is stated (EVALUATION §1). The
  placement study is called a sensitivity study, not a held-out gain. DECISIONS rows 18–27 (27.09
  and 28.09). The README is cut
  to the jury path, what to look at, current results, build / run / bag / parameters and the
  documentation table; its dated paragraphs moved here ("Dated status notes").
- **The image's default command runs the node for recorded bags (28.09, `d359a06`):**
  `ros2 launch resense_ros detector.launch.py freshness_mode:=replay` (the input's age from its
  publication by the player); before, a bare `docker run resense` + `ros2 bag play` gave `FAULT` on
  every message of a clear recorded bag (both judges of 28.09). The node's own default stays
  `live`, for a live LiDAR on a train; CI's offline runtime-image step starts the node with the
  bare default command; a test pins the command and the node default.
- **The node's input path and end-to-end latency (28.09, P1; detector unchanged):** the input
  clouds are taken as serialized bytes (`raw_input`, default true) and read by
  `resense_ros/fastcloud.py` instead of rclpy's message conversion (12.5 ms median, 32 ms p95 per
  24 MB 360° cloud, paid again for every queued frame the start-up catch-up skips); a message
  neither can read is logged and dropped; organized clouds with row padding are packed before the
  (unchanged) decode; the decision topics go out before the status JSON; the RViz markers and the
  corridor cloud are built only while something subscribes. The detector's input is byte-identical
  on all 453 frames of both original recordings (`scripts/check_fast_input.py`, now also in CI).
  End to end (the player's publication → the result), p95 at 360° on a 4-vCPU 2.1 GHz sandbox: an
  independent judge's 5 alternating pairs 113 → 102 ms cached and 137 → 118 ms cold (the team's
  2 pairs 120–127 → 93–97); decode + detect unchanged; CI runner cold 60 ms at 360°, 37 ms at 120°.
  These cover the current results; over every frame result, start-up included, p95 at 360° went
  1.2–2.1 s → 0.24–0.46 s in the team's captures (EXPERIMENTS §3d).
  The status `node` object adds `decode_ms`, `detect_ms`, `cpu_cores` and `rss_peak_mb`;
  `check_dry_run.py` prints the end-to-end latency and CPU (`--max-p95-e2e`);
  `play_bag.sh` waits for the node and the listener instead of fixed sleeps; CI runs the original
  bags and uploads the image archive for the working branch too; a test pins every node
  parameter to a launch argument with the same default
  ([evidence](docs/evidence/node_input_2026-09-28/README.md), EXPERIMENTS §3d).
- **CI in two stages, four jobs (28.09):** a push ran seven `ci.yml` jobs, and a push to `main`
  that touched the cold-bag pins also ran `dataset-cache.yml`. Now stage 1 `checks` (ruff, the
  parameter copy, the detector seal: the former `lint` and `params-in-sync`) gates stage 2:
  `pytest` (the suite plus the former `web` job's dashboard tests on the same install; the
  zero-skip check now covers `web/demo` too), `docker` and `offline-build`. `docker` takes over the
  former `dataset` job's cache restore / one-download seeding, and drops what `offline-build`
  already proves on the jury's runtime archive (its own `docker save` / `rmi` / `load` round trip
  and `--internal` network playback); its two in-image smoke tests are one, with
  `--network none`. `dataset-cache.yml` keeps its schedule and manual run but no longer runs on a
  push (it raced `ci.yml` for the one Google Drive download). Every action moved to its Node 24
  release (`checkout@v7`, `setup-python@v7`, `cache/restore|save@v6`, `upload-artifact@v7`),
  which ends the Node 20 deprecation warning on every job.
- **Detector quality cycle of 27.09 (the user's four problems, ML allowed; sealed, reviewed):**
  five parallel experiments on one shared screen (`scripts/quality_screen.py`: the gate against P3d,
  the monitoring / overclaim diagnostics and the new processing-history stress
  `scripts/history_stress.py`), merged and switched on: the envelope near the train as the union
  of the rails' and the sensor-axis envelope within 60 m on straight track (`gauge.reference` 3),
  a learned track opinion that may delay a doubtful STOP by at most 10 processed frames in a
  track's life (~1 s at 10 Hz, ~2 s at 5 Hz),
  never within 25 m or for a standing body within 40 m (`tracking.doubt_*`, gradient-boosted trees
  in `resense/models/`, retrained on the shipped detector, grouped held-out AUC 0.975, a 2× margin
  on its threshold), monitored-range caps from persistent sparse
  evidence and supported scan lines (`health.clear_cap_thin`, `clear_cap_persist`), the along-track
  association gate and the column body width (`tracking.gate_along_only`,
  `cluster.column_width_trim`), and far evidence for approaching tracks, advisory otherwise
  (`tracking.thin_far_min_distance`, `cluster.weak_min_points`). Two independent judges reviewed the
  first version (`8b74cd0`) and found a one-sided envelope shift, a far-evidence rule
  that could hide a track and an unbounded opinion delay (set O #6 held at 28.7 m); `65c5a5b` fixes
  all three. A second round found the opinion withholding over a missed frame inside its 25 m bound
  and asked for a measured held-out figure; `352ca13` fixes the bound, retrains the opinion with a
  margin and measures it on ride pieces each model never saw (`scripts/opinion_crossfit.py`: 43
  events without the opinion → 37 held out), and adds `scripts/play_bag.sh` (one command: load,
  node, play, print the decision changes). Full gate PASS against P3d, no waiver: ride 183 / 45 / 38
  → 130 / 32 / 31 in-sample (37 events held out), five bags 58 / 13 / 16 → 40 / 11 / 13, set O edge cube first STOP 5.2 → 35.0 m (2 → 18 frames), edge box
  track from 28.7 m, box at the envelope top 101.3 → 111.4 m, plank 82.2 → 87.2 m, set O inside STOP
  frames 384 → 411, background 3 → 0, the person crossing 58 → 61 of 61 from frame 8 (from the
  envelope reference), GO overclaims 46 → 16, the captured clear-run STOP gone from every captured
  node history, history stress 78 → 55 STOP events. The ride / history gains are mostly the
  in-sample opinion (ablations in the record); set F's 1 m box trades −2 / +5 frames at 50–100 /
  100–150 m (now printed per bin by the gate). New seal `detector_freeze_2026-09-27.json`, new
  baseline `regression_baseline_2026-09-27_quality.json`
  ([`docs/QUALITY_CYCLE_2026-09-27.md`](docs/QUALITY_CYCLE_2026-09-27.md)).
- **CI dataset cache (27.09):** the cold-disk check restores the two verified original bags
  from the Actions cache (job `dataset`: lookup only on a hit, one download from Google Drive on a
  miss, checksums pinned in `scripts/cold_bags.sha256`); `dataset-cache.yml` keeps the default
  branch's entry warm. The Drive quota no longer turns CI red.

- **P3d reference seal and remaining integration (26.09 night, delegated by the user):**
  sealed the existing `_ride_p3d` detector and defaults as the reproducible reference with a
  source/evidence SHA256 manifest and CI integrity check. Final freeze and release remain on hold.
  Candidate B is not shipped; the envelope union stays off pending Q1.
  The node now allows 20 s only for a new recording's initial catch-up, then returns to the
  existing 5 s backlog limit. The bag acceptance checker matches each message's header timestamp,
  fixing false loss reports from receive-clock drift. P4 completed 72 preregistered object/background combinations:
  45 with any match, 544/2,458 visible frames, zero paired-control matches; no tuning followed.
  All 45 ride false events have scene reviews. Refreshed full gate: 146 enforced metrics across 199
  comparison rows unchanged, no waivers ([quality cycle](docs/QUALITY_CYCLE_2026-09-26.md)).
  The 25.09 original-bag replay and stock DDS check passed, but a fresh cold-cache replay on 26.09
  failed its message-count criterion; its logs are retained below. The full-data run on the second
  machine passed 621 tests and 6 subtests; this checkout's cadence-preserving follow-up passes
  667 tests and 6 subtests, with one ride-cache test deselected because `/data/cache/new_data` is
  unavailable. Dashboard FAULT/CAUTION banners and estimated-range
  wording are corrected; live freshness validation, no-data overlays, and reconnect guards have
  16 passing Chromium tests. CI now has branch-scoped cold-bag and remote-viewer outage /
  recovery checks; current-source cold checks of both original bags now pass with ten-message
  read-ahead, while the default 1,000-message prefetch remains stale pending the captain's
  operating-procedure decision. Deck and PDF rebuilt;
  the video remains the previously verified `_ride_p3d` build. Independent scores and remaining quality
  gaps are in SCORECARD; these changes do not claim improved detector recall.


- **Re-judgement and the P1 / P2 completion pass (26.09 evening):** two independent judges
  re-scored the integrated head (`be5f5fc`) against spec §8 without trusting the documents, one
  from the code and the committed evidence, one by re-running everything on a fresh 4-core machine
  with the organizers' data downloaded again ([`docs/SCORECARD.md`](docs/SCORECARD.md) §0,
  [`docs/evidence/rejudge_2026-09-26/`](docs/evidence/rejudge_2026-09-26/)). Measured: 587 tests
  green, the full regression gate with the ride and set F straight against `_ride_p3d`, set O from
  the float bag (387 / 7 / 1), the jury chain offline on the original bags and the organizers'
  console with a stock Fast DDS uid-1000 player (PASS with the bag in the page cache). **New
  finding:** from a cold disk the 360° `doubleT_obstacle` FAILS the dry run (34 of 201 frames
  processed, first STOP +15.5 s): the player sends the whole overdue recording at once and the
  catch-up's 1.0–1.4 s steps reset the scene; README jury step 3 now reads the bag first, the node
  fix is the captain's decision ([`docs/CAPTAIN.md`](docs/CAPTAIN.md) action 21). **P2:** the deck,
  PDF, video and `.srt` rebuilt on `_ride_p3d` (the box at the envelope top 51 of 124, continuous
  from 101 m; the edge objects «лишь 2 и 6 кадров» on every slide and note instead of «пропущен»;
  the video's ride card 46 → 45; the subtitles say that 3.5 per km is in-sample and 148 m our
  synthetic; 555 → 587 tests); `web/demo/test_web.py` and `tests/test_overview_video.py` (+1 test)
  now tie them to the newest gate baseline. **P1:** the claims the judges found wrong or stale
  fixed (README's "stock Fast DDS 0–1 of 201", ALGORITHM §3.5 without the rules of 26.09 and its
  set O limits, DECISIONS row 15 "none shipped" although `lowobj.rail_start_within` is on, a row 17
  for the near-field and STOP-keep rules, ARCHITECTURE's test count, PRESENTATION's "6 из 8"); the
  captain board, PLAN and the documentation index brought to this state. No detector or config
  change. The deck and video of `e5f0f02` (26.09 morning, on `_ride_p3c`: 45 ride events, 8 of 8,
  555 tests) had no entry of their own. **Second round** after judge B re-checked the first commit
  (10 of 17 claims fixed, 4 partly, 3 not, 5 new): the timing on the deck, the video and in README /
  EXPERIMENTS is now the shipped C++ path (23–31 ms per frame, p95 ≤ 42 ms; the numpy 42–64 ms of
  23.09 kept only as history), the set F person's "held from 149 m" artefact replaced by the band
  figure, «3,5 на км» labelled in-sample on every slide, the slide 13 title qualified, ALGORITHM §4
  names its exceptions, the drop-criterion change disclosed next to the bench PASS, the stamps file
  of the through-ROS grade committed; the catch-up variants for CAPTAIN action 21 measured
  (`catchup_max_lag:=20`: no scene resets cold, PASS warm). Final: 62.5 / 100.

- **P1/P2 follow-through on the working branch (26.09):** the detector now grants a bounded
  20-second allowance only to the first backlog of a new recording, then returns to its normal
  5-second live-stall limit. Unit tests cover a cold whole-recording burst, an isolated first
  cloud, repeated recordings, and expiration of the startup allowance; run 362814 passes both
  original-bag cold checks with ten-message rosbag2 read-ahead: 201 obstacle statuses, first STOP
  +1.1 s, 78 ms p95, zero source messages unprocessed after catch-up; 252 clear-bag statuses, zero
  alarms, 48 ms p95, and zero source messages unprocessed. Default 1,000-message prefetch remains
  stale pending the captain's operating-procedure decision. Earlier 91/201 and no-input/cancelled attempts remain recorded. The
  dashboard now treats `FAULT` as unavailable, clears the
  estimated monitoring range on fault or stale input, ignores malformed or decision-less live
  messages, and overlays the live panels until the first current result and on disconnect or
  freshness expiry. Its user-facing
  range label says that the distance is estimated. The updated team history uses supplied project
  facts and leaves personal claims out. Browser-backed checks: 16 passed in Chromium. Branch CI
  run 362814 passed the isolated two-container Foxglove pause/recovery test and both cold original-
  bag replays with read-ahead 10. The default 1,000-message read-ahead still gives stale output;
  C5/C7 await the captain's operating-procedure decision. The run retains the bag hashes and replay
  logs; raw downloads are removed. Four member headshots are in the ignored private presentation
  folder; city, team formation, group photo and the physical second-device rehearsal remain pending.

- **P2 public presentation and P4 consistency pass (26.09):** rebuilt the 16-slide public PPTX
  and PDF and the 2:50 overview MP4/SRT against the committed `_ride_p3b` regression baseline:
  13 false events on five empty bags, 46 / 3.5 per km on the ride, 125/126 rail-object frames,
  STOP for 6/8 organizers' objects (five held), and 492 tests. The 5 cm hanging object is shown
  from 30 m; the edge box remains a miss. The offline jury chain now says `docker load`, and the
  video no longer claims a release tag. The P4 audit keeps its dated 24.09 measurements; the
  25.09 claim of zero alarms in the set O empty suffix is qualified because the current gate
  records a background STOP at frame 1131. Fresh original-bag and quantized-cache replays both confirm 1 false STOP frame / 1 event
  in the 706-frame suffix (EXPERIMENTS §1g, `seto_suffix_2026-09-26.json`).

Package version 1.0.0 (no tag or release yet: deferred, 25.09; detector v0.6.3 with the long
overhead rule on, node v0.6.4). Tests: 235 → 587 (+28 native kernels, +3 speed evaluation
helpers, +23 regression gate, +3 DBSCAN exactness, +5 late candidates, +53 release tooling, +5
overview video, 2 of them in the image, which has no `docs/`, +5 drop accounting and socket
buffers, +21 `load_image.sh`, +11 `check_no_network.py`, +4 `tracking.column_hold`, +20 DDS
transport, 19 of them in the image, +4 rail shadow, +3 the far-support rule, +5
`cluster.far_axis_both_sides`, +3 far bed bins, +5 the rail-shadow review fixes, +4 the
free-hanging exemption of `floating`, +4 thin hanging objects, +5 `health.clear_cap`, +6 the rate
and re-mount flags, +1 the rail-lock guard of the hanging stage, +13 the review fixes of the
round-2 items, +17 their re-review, +6 latency out of the decision, +8 the start-up census, +27
the rail-start rule, +12 the near escalation, +8 the sensor-axis envelope, +8 the P3 items of 26.09
combined and their safety review, +28 the STOP keep and its cap, +3 P4's sustained set O gates, +1 the video's ride card against the gate baseline) in `tests/`, 16 in `web/demo`.

- **STOP keep against shape signatures and scan lines (26.09, P3 range; shipped, round 2).**
  `tracking.stop_keep_signature` true, `tracking.stop_keep_thin` 1, `tracking.stop_keep_min_voxels`
  10, `tracking.stop_keep_max_s` 10 s. A track that was a STOP in the previous frame keeps its zone vote when its cluster is demoted
  only by a shape signature, and a scan line inside the envelope (flatter than `min_height`) may
  continue it; either needs ≥ 10 strict voxels, the near escalation's bar, and acts only within
  10 s of sensor time of the track's last clean hit (the safety review's cap, non-blocking review).
  Neither starts or confirms a track (reason `stop_hold`). Investigation first: on set O, physics limits four objects
  (≤ 4 returns a frame where missed), the height reference two; nothing moves a first STOP. Set O
  box at the envelope top 22 → 51 STOP frames (advisory 27 → 6), continuous from its first STOP at
  101.3 m (from 23.9 m before); inside STOP frames 355 → 384. No first STOP moves: set O still has
  one STOP frame beyond 100 m; the gain is a hold. Gate PASS against `_ride_p3c`: the ride (183 / 45 /
  38, frame by frame), five bags, `doubleT_obstacle` and set F straight identical. Round 1 (no bar)
  failed its pre-registered ride rule (alarm frames 183 → 192); round 2 was written after it, so
  its ride result is in-sample. Off: output identical to `208152d`. New gate baseline
  `docs/evidence/results/regression_baseline_2026-09-26_ride_p3d.json` (the final defaults with the cap and
  P4's set O metrics, `fa18832`; per frame identical to the B10 run).
  +28 tests.
  [`p3_range_2026-09-26.json`](docs/evidence/results/p3_range_2026-09-26.json),
  [EXPERIMENTS §1o](docs/EXPERIMENTS.md).

- **The P3 items of 26.09 combined; new gate baseline `_ride_p3c` (26.09, P3 integrator).**
  `wf14/rail-start`, `wf14/near-escalation` and `wf14/edge-axis` merged on `00143b0`
  (`wf14/integrate-p3`), then their safety review: the rail-start rule needs the band's line
  ≥ 0.06 m above the model's rail plane (`lowobj.rail_start_min_ref`); the near escalation skips
  `beyond_axis` / `beyond_height_ref`; the wall keep counts the rails' envelope, and a blob it kept
  that another rule demotes no longer hides a low or hanging object; `gauge.axis_union` 0 (blocking:
  an object touching a long edge line was dropped; the oversize split falls back to the rails' part).
  Gate PASS against `_p3b`, 7 rows better, none worse: ride 187 / 46 / 39 → 183 / 45 / 38; set O
  inside STOP frames 337 → 355, 8 of 8 objects; five bags, `doubleT_obstacle` and set F straight
  identical. With every new flag off the output is identical to `bd67fb0`. New baseline
  `docs/evidence/results/regression_baseline_2026-09-26_ride_p3c.json`. +8 tests.
  [`p3_integration_2026-09-26.json`](docs/evidence/results/p3_integration_2026-09-26.json),
  [EXPERIMENTS §1n](docs/EXPERIMENTS.md).

- **Rail heads ahead of a standing train at a fresh start (26.09, P3): `lowobj.rail_start_within`
  4 m, on.** Fixes the open finding of the start-up census: from the gate's piece-2 cut a fresh
  detector STOPped at 2.9–3.1 m on the rail heads. A `low` cluster under 4 m that reaches a rail
  line, is at most 0.45 m wide and rises at most 0.05 m above the rail head's own returns along
  the track is rail geometry. A low track on it that was never matched at ≥ 4 m is not newly
  reported. The finding's 4 STOP frames → 0. The blind-zone cases of rule c still STOP on the same
  frames: all 40 ray-cast cases (30 × 30 × 10 cm object, objects across a rail, 0.5 m box;
  3.0–3.9 m ahead; standing or slow train) identical. Gate PASS against `_p3b`: ride 46 → 45 events (187 / 39 → 183 / 38), every other row the same. Off (0): output identical to
  `bd67fb0`; baseline not re-cut. +27 tests.
  [`p3_rail_start_2026-09-26.json`](docs/evidence/results/p3_rail_start_2026-09-26.json),
  [EXPERIMENTS §1k](docs/EXPERIMENTS.md).

- **Near-field escalation (26.09, P3; judge B action 6): shipped.** Within 35 m, a track whose
  last 5 hits each had ≥ 10 voxels inside the strict envelope is a STOP, whatever demoted it
  (`tracking.near_escalate_*`; reason `near_envelope`). A column never counts. Also, a tall
  cluster at the corridor side with ≥ 10 strict voxels within 20 m is no longer dropped as a wall
  (`cluster.wall_keep_*`). Set O: the box at the envelope top 12 → 22 STOP frames (from 23.9 m),
  the edge box 0 → 6 (from 10.3 m), the edge cube 0 → 2; inside STOP frames 337 → 355, 8 of 8
  inside objects STOP. #5, #7 and the background are unchanged. Gate PASS, 5 rows better. The
  ride (187 / 46 / 39), the five bags, `doubleT_obstacle` and set F are identical. Pre-registered
  candidate A plus D; B and C not run. Baseline not re-cut (the integrator will). +12 tests.
  [`p3_near_escalation_2026-09-26.json`](docs/evidence/results/p3_near_escalation_2026-09-26.json),
  [EXPERIMENTS §1l](docs/EXPERIMENTS.md).

- **The envelope also measured from the sensor axis (26.09, P3; judge A, action 7): A passed its
  gate, not shipped after the safety review (`gauge.axis_union` 0).** The organizers place their edge tests from the sensor axis, which runs
  at −0.24° to the rails in set O. Measured from it, the four edge tests are exactly their intent:
  #4 and #6 inside in 74 / 93 frames, #5 and #7 in none; from the rails 16 / 8 and 98 / 58. Now a
  point is also inside when it is inside the envelope measured from the sensor axis. This applies
  only within 50 m, on straight track (|curvature| ≤ 2e-4 /m), with the rail pair locked and the
  two axes ≤ 0.30 m apart. Pre-registered A / B / B2:
  - A (the union) passes the gate: 2 gated rows better, none worse; set F on gentle curves is
    identical. #6 gains 1 STOP frame (0 → 1, 14.3 m). It is a track confirmed on three gauge hits
    of the box and reported on an edge-line fragment 2.4 m in front of it. Nothing else changes.
  - B (the corridor coordinate re-measured) loses a plank STOP frame.
  - B2 (A, and the shape rules read the nearer axis) STOPs on #6 from 30.65 m (7 frames
    credited), but the ride gets 187 / 46 / 39 → 189 / 49 / 39.

  #4 stays advisory (`floating`) under every variant. The safety review blocked A: the union can
  take in a long line at the corridor edge beside an object, and the oversize split then dropped
  both (ray-cast 19 → 6 STOP frames). The split now falls back to the rails' own part (19 → 19);
  A, B and B2 stay off. Tests +8 (`tests/test_edge_axis.py`). EXPERIMENTS §1m,
  [`p3_edge_axis_2026-09-26.json`](docs/evidence/results/p3_edge_axis_2026-09-26.json).

- **The image archive as a CI download (26.09, P1):** on a push to `claude/nifty-pascal-lzgl78` or
  `main`, when every step passed, the `offline-build` job uploads the runtime archive it made,
  loaded, rebuilt offline and played through as the run artifact
  `resense-image-<version>-<short commit>` (`actions/upload-artifact@v4`, 30 days, not
  re-compressed): the `.tar.gz` named after the commit and its `.sha256` in the form
  `scripts/load_image.sh` and `sha256sum -c` read, checked against the sum `load_image.sh`
  verified. The stand has no internet; the archive of the frozen commit no longer needs a machine
  with Docker. [ARCHITECTURE](docs/ARCHITECTURE.md) "Deployment without internet", README
  «Кратко для жюри».

- **Docs after the re-judgement of 26.09 (P1):** README «Кратко для жюри» as a one-page guide (the
  four decisions as a table, the topics to score, RViz from the image in one line, where the
  archive comes from); [`docs/DECISIONS.md`](docs/DECISIONS.md), the 16 key decisions on one page;
  the claims the judges found stale or overstated corrected: the README header (`bd67fb0`,
  package 1.0.0), hanging objects (the hanging stage covers groups ≤ 0.5 m within 0.8 m of the
  axis, ≤ 60 m, with a rail lock; ALGORITHM §6), the ~200 m range (no STOP beyond ~101 m on the
  organizers' objects), the start-up skips (39–53 frames by design, none lost in transport after
  the start-up), set O (6 of 8 objects with a STOP, 5 of them held), the ride's 3.5 per km
  (in-sample), 500 tests.

- **Start-up of a fresh bag (26.09, P3 / P4): census; three rules tried, none shipped.** A
  judge's fresh start at ride piece 2 STOPped at 2.9–3.1 m. The cause: the rail heads 3.0–3.6 m
  ahead of a standing train, above a young model's rail plane. Census of the first 4 s of 221 ride
  bags, 8 gate pieces and 7 recordings (`scripts/startup_census.py`): 18 of 221 bags STOP (35
  events), but the warm detector STOPs more on the same frames. These are the ride's ordinary
  false alarms, not caused by the start. Three rules were pre-registered:
  - a (low advisory while the calibration is pending) fails the ray-cast check;
  - b (a minimum model age) fails it too: a real low object 20 / 40 m ahead is not STOPped /
    STOPped 12 frames late;
  - c (`tracking.low_min_seen_distance` 4 m) passed: census 41 → 40, gate PASS, ride 46 → 45
    events.

  c was then reverted: it opens a blind zone. A 30 × 30 × 10 cm object, or an object across a
  rail, 3.0–3.9 m ahead of a standing train (or falling there) never STOPs with it; it STOPs from
  its 5th frame without it. All three flags are off. Default output identical to `11c50a7` on the
  six recordings and set O; the `_p3b` baseline stands. +8 tests.
  [`p3_startup_2026-09-26.json`](docs/evidence/results/p3_startup_2026-09-26.json),
  [EXPERIMENTS §1j](docs/EXPERIMENTS.md).

- **Latency out of the decision (26.09, P1):** a latency p95 over the 100 ms budget no longer
  turns `GO` into `CAUTION` on `/resense/decision`; it stays a health warning (`level` warn, its
  message and `latency_p95_ms` in `/resense/health` and the status JSON). The health output has a
  new `decision_level`, the level without the latency warning, which the node's decision,
  `scripts/score_clear_distance.py` and the dashboard read; `health.latency_affects_decision:
  true` restores v0.6. `STOP`, `FAULT` (input errors, processing errors, the watchdog) and every
  other warning are unchanged. Both judges of 26.09 and the judgement of 24.09: on a loaded
  machine the latency warning was on 875 of 1 510 set O frames (690 `CAUTION`), at 24.09 on 97 %
  of the frames, which read as a false-alarm storm. Gate on the six recordings and set O (no
  ride: `--allow 'ride.*' --allow 'set_F_straight.*'`) against `_p3b`: PASS, every gated row the
  same, only the informational latency rows moved. On that run (load average ~7) the latency
  warning was on 2 242 of the 2 287 frames of the five obstacle-free recordings: `CAUTION` 2 189
  → 980 frames (27–69 % per recording), set O 891 → 393; `STOP` and `FAULT` frames identical in
  every recording. README (jury section): `CAUTION` is advisory, the alarm is `STOP` /
  `/resense/obstacle_detected`. +6 tests.

- **Re-review of the safety fixes (26.09, P3):** a match on the change frame ended the
  `tracking.reseed_hold` of a STOP, so a loss starting one frame after a calibration change got
  only the 1-frame `hold_misses`. The hold is now a fixed window of 5 frames from the change,
  matched or not (6 at 10 Hz when the track model is re-seeded: its warm-up); a ray-cast test
  guards the rotation sign of the model and the tracks; `scripts/robustness_check.py` imports its
  own checkout. Pre-registered (addendum 3); gate PASS, the gate, the stress check and the
  reviewer's sweep identical to `10e2707` frame by frame (baseline `_p3b` unchanged). +17 tests.
  [`p3_round2_review_fixes_2026-09-26.json`](docs/evidence/results/p3_round2_review_fixes_2026-09-26.json),
  [EXPERIMENTS §1i](docs/EXPERIMENTS.md).

- **Safety review of the round-2 items: calibration changes keep a confirmed STOP; the refinement
  off (26.09, P3, delegated by the captain):** the review of `17a850d` found that every refinement
  of the provisional tilt re-seeded the track model from nothing and lost a confirmed STOP on
  `doubleT_obstacle` (5 Hz, rig +2° / +2°: frames 102 and 104 with `clear_distance` 151 / 163 m),
  that the refinement flapped, and that a hanging cluster yielded to an advisory one (a cable
  demoted as `floating`: no STOP). Pre-registered (00:25 UTC, two addenda before their runs). On
  now: a change up to 1° rotates the track model instead of re-seeding it
  (`calibration.reseed_keep_max_deg`), a STOP is held through any change and only STOPs are kept
  through a change above 1° (`tracking.reseed_hold` 5), `clear_distance` is capped at a lost
  reported track (`health.clear_cap_lost`), a hanging cluster yields only to an obstacle
  (`cluster.hanging_yield_gauge_only`), and the input rate counts in-burst stamp intervals. No
  refinement variant passed the reviewer's sweep (a refined tilt loses frame 182 at 5 Hz with the
  rig at (0, −1.5°)), so `calibration.refine_min_deg` is 0 (off); it gives up the refinement's
  stress gain: +3° roll 11 / 13 → 14 / 16, +3° pitch 16 / 17 → 17 / 18 events / STOP episodes (no
  worse than `17a850d` with the refinement off; 5 Hz 10 / 10 unchanged). Full gate: PASS against
  `_ride_p3` (6 better, none worse), every decision, detection and track model identical to
  `17a850d` in all 15 269 frames; `clear_distance` shorter in 398 frames (ride median 123.0 → 122.6
  m, set O overclaim 67 → 60 of 505). `regression_baseline_2026-09-25_ride_p3b.json` re-cut on the
  final commit. +13 tests.
  [`p3_round2_review_fixes_2026-09-26.json`](docs/evidence/results/p3_round2_review_fixes_2026-09-26.json),
  [EXPERIMENTS §1i](docs/EXPERIMENTS.md).

- **The P3 items of round 2 combined; new gate baseline (P3 integrator, 25.09, delegated by the
  captain):** the four items below merged (`wf10/p3-round2`) on top of the rail-shadow rules,
  with the two decisions of the captain's delegate (`health.clear_cap` on; the thin-hanging
  rail-lock guard on). Pre-registered (22:13 UTC, before any run on the merged code); the full
  gate of the final defaults (`30d0cac`, `--jobs 3`, 333 s) passes against
  `regression_baseline_2026-09-25_ride_p3.json` with 6 gated rows better and none worse: set O
  hanging 0.3 m cube 19 → 30 STOP frames, first STOP 34.0 → 52.5 m; 5 cm hanging object 0 → 15,
  first STOP 30.1 m (set O inside STOP frames 311 → 337 of 801, objects with a STOP 5 → 6 of 8,
  5 of them held: the 2 × 2 m box at the envelope top STOPs in 12 of its 124 frames);
  `doubleT_obstacle` 185 → 186 of 246 labelled hits (object on the rail 124 → 125 of 126 from
  frame 75), first alarm frame 11. Five bags 58 / 13 / 16, ride 187 / 46 / 39 and set F straight
  identical, decisions on the five bags and the ride identical frame by frame; no item interacts,
  nothing turned back off. `clear_distance` with the cap on the combined code: five bags median
  −5.5 %, ride −3.1 %, set O overclaim 147 → 67 object-frames, no decision changed. Stress check
  on the combined defaults equals the robustness branch: five bags 5 Hz 10 / 10, +3° roll 11 / 13,
  +3° pitch 16 / 17 events / STOP episodes. New gate baseline
  `docs/evidence/results/regression_baseline_2026-09-25_ride_p3b.json`.
  [`p3_round2_combined_2026-09-25.json`](docs/evidence/results/p3_round2_combined_2026-09-25.json),
  [EXPERIMENTS §1i](docs/EXPERIMENTS.md).
- **Thin-hanging rail-lock guard: `cluster.hanging_needs_rails` on (25.09, round 2, the captain's
  delegate):** the hanging stage runs only on frames whose track model found the rail pair in the
  near range; 28 of the 29 groups it took on the ride were station column tops without one.
  Pre-registered (22:13 UTC, before its code) with the rule "set O's hanging object keeps 15 STOP
  frames from ≥ 30.1 m and the combined gate has no row worse than without it": both held (15
  from 30.1 m; the gate with and without it the same on all 107 rows, decisions identical in all
  15 068 frames). +1 test.
  [`p3_thin_hanging_2026-09-25.json`](docs/evidence/results/p3_thin_hanging_2026-09-25.json)
  (`addendum_rail_lock`), [EXPERIMENTS §1i](docs/EXPERIMENTS.md).
- **`health.clear_cap` on by default, candidate R1 (25.09, round 2, the captain's delegate):**
  shipped although it **missed** its pre-registered clutter limit: the five obstacle-free
  recordings' median `clear_distance` fell −5.5 % against a −5 % limit (by 0.5 pp), the ride −3.1 %
  with 1.49 % of its frames under 60 m; R1–R4 were designed after round 1. Shipped because it makes
  the verified-clear distance conservative (set O object-frames with a `clear_distance` past an
  in-envelope object 172 → 82) and changes no detection or decision. The status JSON's `health`
  gains `candidate_distance` (additive). Recorded as `decision` in
  [`p3_clear_distance_2026-09-25.json`](docs/evidence/results/p3_clear_distance_2026-09-25.json),
  EXPERIMENTS §1i.
- **5 Hz and ±3° re-mount robustness (25.09, P3, SCORECARD #13):** five new detector flags, on
  after the 10 Hz gate (PASS: ride, five bags, set O and set F straight identical;
  `doubleT_obstacle` 185 → 186 labelled hits): `calibration.time_cadence` (the calibration
  counts periods of the input rate: at 5 Hz its final never completed on the 25 s bags),
  `track.rates_per_period` and `track.walls_smoothing_per_period` (axis rate limits and yaw /
  curvature EMA per period: the 5 Hz axis lagged curves), `calibration.refine_min_deg` 0.5 (the
  spaced observations replace a provisional tilt taken on a canted stretch),
  `calibration.keep_within_deg` 0.25 (a confirming final does not re-seed the track model).
  `robustness_check.py`, five bags false events / STOP episodes: 5 Hz 13 / 17 → 10 / 10, +3° roll
  16 / 17 → 11 / 13, pitch 17 / 18 → 16 / 17; `roundT_doubleT` 3 / 2 / 1 → 0 / 1 / 0;
  `doubleT_obstacle` under stress unchanged. Tried, not shipped: `calibration.provisional_per_axis`
  (off). Tests 416 → 422 (EXPERIMENTS §1i).

- **Conservative `clear_distance`, tried and not shipped (25.09, SCORECARD §6 row 6):** the opt-in
  `health.clear_cap` (default false, output byte-identical) caps the verified-clear distance at
  the nearest unconfirmed or advisory cluster touching the envelope, columns excluded
  (`clear_cap_*` sub-parameters, `health.candidate_distance` in the status JSON when on); it
  changes no detection and no decision. Pre-registered (C0–C5, then R1–R4): set O overclaim
  172 → 82 object-frames, ride median clear distance 127.0 → 123.0 m, but the five
  obstacle-free recordings' median −5.5 % against the 5 % limit, so off on its branch (turned on
  afterwards by the captain's delegate, the entry above: it still did not pass). New
  `scripts/score_clear_distance.py`; evidence `docs/evidence/results/p3_clear_distance_2026-09-25.json`;
  EXPERIMENTS §1i.

- **Thin hanging objects (25.09 evening, P3, SCORECARD #11):** new stage
  `clustering.find_hanging`, on (`cluster.hanging_enabled`, `hanging_*`). It covers a thin object
  hanging from above that dips into the envelope near the axis with only 1–3 returns: those
  returns are linked to the object's part above the envelope top and reported as an obstacle.
  Pre-registered candidates A / B / C (20:53 UTC); A, the first, passed the regression gate
  (`--jobs 1`, the ride included). The organizers' 5 cm object in set O goes from `GO` in all
  42 visible frames to a STOP in 15 frames from 30.1 m (set O inside STOP frames 303 → 318, 6 of 8
  objects). Five bags 58 / 13 / 16, ride 187 / 46 / 39, `doubleT_obstacle`, the other set O
  objects and set F straight are the same. On the ride it takes 29 single-frame groups, 28 of
  them station column tops without a rail pair; none confirmed. Cost 0.5 ms a frame. Tests
  416 → 420 (`tests/test_thin_hanging.py`). EXPERIMENTS §1i,
  [`p3_thin_hanging_2026-09-25.json`](docs/evidence/results/p3_thin_hanging_2026-09-25.json).

- **Free-hanging exemption of `floating` (25.09, round 2, P3):** `cluster.floating_free_max_size`
  0.5 m (with `floating_free_max_dy` 0.95 m, `floating_free_max_top` 2.5 m): the `floating`
  signature no longer demotes a compact cluster hanging free inside the envelope. The organizers'
  0.3 m cube hanging 1.0–1.4 m up (set O #2) is a STOP from 52.5 m instead of 34.0 m (19 → 30 STOP
  frames); the six recordings and the ride are identical frame by frame, gate PASS. Pre-registered
  (A / B / C, A shipped): `docs/evidence/results/p3_signatures_2026-09-25.json`, EXPERIMENTS §1i.
  Tests +4 (`tests/test_floating_free.py`).
- **Review fixes of the rail-shadow rules (P3, 25.09):** a safety review found three faults.
  `cluster.gauge_distance` measured on the strict-gauge mask, the envelope shrunk by the axis
  margin (0.15 m per 100 m), so an object entering obliquely was reported beyond its entry (+0.4 /
  +0.8 / +1.2 m at 40 / 80 / 120 m; set O #7's false STOP 1.2–1.5 m too far): it now measures on
  the envelope widened by that margin, never beyond the entry. A held bed had no end (a 3.4° pitch
  step held it for good: a lasting false STOP): `track.floor_shadow_max_hold` 20 frames, then the
  rule is released until no shadow is found. The two shadow bins must be adjacent, and the face is
  the one nearest the shadow. Health counters `floor_shadow_frames` / `floor_held_frames` /
  `floor_released_frames` (additive). Pre-registered (19:47 UTC); the full gate (`b718a37`) passes
  against `regression_baseline_2026-09-25_ride_column.json` with the same 5 gated rows better and
  none worse; decisions and the track model identical in all 15 269 frames of the six recordings,
  set O and the ride, gauge distances only shorter (124 detection-frames); set O #1 unchanged (no
  STOP more than 1 m off); set F straight's 1 m box 10 → 12 false detections against the first
  `_ride_p3` cut (a STOP at 112–114 m reported 4 m short). `regression_baseline_2026-09-25_ride_p3.json`
  re-cut under the same name on `154db25`. +5 tests, each failing before the fix.
  [`p3_review_fixes_2026-09-25.json`](docs/evidence/results/p3_review_fixes_2026-09-25.json),
  [EXPERIMENTS §1h](docs/EXPERIMENTS.md).

- **The P3 items of 25.09 combined; new gate baseline (P3, 25.09, delegated by the captain):** the
  four items below merged (`wf7/p3`): the rail-shadow rules ship; `track.walls_min_far_support`,
  `cluster.far_axis_both_sides` and `track.floor_far_min_width` stay 0 (off). Pre-registered
  (19:03 UTC, before any run on the merged code); the full gate of the merged defaults (`c598cf6`,
  `--jobs 3`, 332 s) passes against `regression_baseline_2026-09-25_ride_column.json` with 5 gated
  rows better (set O 2 × 2 m box 207 → 208 and plank 42 → 49 STOP frames; set F straight false
  detections person 7 → 6, 1 m box 13 → 10, trolley 12 → 5), none worse, and equals the rail-shadow
  item's own gate on every row but latency; five bags 58 / 13 / 16, ride 187 / 46 / 39,
  `doubleT_obstacle` 185 of 246 from frame 11 unchanged; set O #1 wrong-distance STOP frames 12 → 0;
  per frame no set O inside object loses a matched-alarm or STOP frame. New gate baseline
  `docs/evidence/results/regression_baseline_2026-09-25_ride_p3.json`.
  [`p3_combined_2026-09-25.json`](docs/evidence/results/p3_combined_2026-09-25.json),
  [EXPERIMENTS §1h](docs/EXPERIMENTS.md).
- **Far bed bins that are an object's foot: `track.floor_far_min_width` (25.09, P3 `bed_bin`,
  default 0 = off, tried and not shipped):** an object standing beyond ~90 m, where the real bed no
  longer returns, fills a bed bin and extends the fit (ALGORITHM §6). The flag drops a bin at or
  beyond `floor_far_from` whose low points span less than the width with its face standing on
  them. Pre-registered (17:50 UTC) 1.1 m from 90 m with ≥ 2 / ≥ 3 standing points / width only:
  each fails on set F straight (false detections 35 → 43 / 36 / 27 with the trolley 12 → 21 / 18 /
  14; the crate's six file-98 detections this item is about do go in B) and on a set O row;
  station STOP episodes 15 → 9–10; the ride with A 187 / 46 / 39 → 171 / 45 / 40. With the flag
  off the full gate equals the baseline in every row but latency.
  [`p3_bed_bin_2026-09-25.json`](docs/evidence/results/p3_bed_bin_2026-09-25.json),
  [EXPERIMENTS §1h](docs/EXPERIMENTS.md).
- **The 147.5 m switch parts: tried, not shipped (25.09, P3; `cluster.far_axis_both_sides` 0 =
  off, output byte-identical):** the 4 switch-part STOP episodes of
  `squareT_platform_squareT_switch` are an axis error (a hall wall seen to 72–92 m sets a
  curvature that moves the far corridor 1.4–3.4 m at 147 m), not a height one. Pre-registered
  (`docs/evidence/results/p3_far_switch_2026-09-25.json`): `cluster.far_min_height` 0.8 / 0.9 /
  1.0 (episodes 4 → 1 / 1 / 0) cut set F straight's person 151.0 → 143.5 / 143.5 / 138.8 m and the
  trolley to 104.5–106.9 m; the new opt-in `cluster.far_axis_both_sides` (a far obstacle needs both
  tunnel boundaries to reach it) mode 1 loses 3–15 m of set F; mode 2 (bent frames only) passes the
  gate with 5 rows better (five bags 13 → 9 events, ride 46 → 42 events and 39 → 33 STOP episodes,
  set O and set F straight identical) but costs a person 1.9 m of median first confirmation on six
  gentle-curve approaches (124.1 → 122.2 m), so it stays off (EXPERIMENTS §1h).
- **The 82.9 m platform end: a far-support rule for the wall sides, tried, not shipped (`692feaf`,
  `1ae1952`, P3, 25.09, delegated by the captain):** the axis at the platform of `squareT_platform_squareT_switch` is
  ~0.8 m off at 83 m (curvature 2.5–4e-4 from a platform-side boundary joined to the hall end;
  EXPERIMENTS §1h). New opt-in `track.walls_min_far_support` (0 = off), with
  `walls_far_support_max_curvature` 2e-4 and `walls_far_support_frames` 1: a wall side whose bins
  beyond 30 m mostly lie off its own fit does not set the axis shape when the other side's do and
  say straight. Pre-registered in two rounds
  ([`p3_platform_end_2026-09-25.json`](docs/evidence/results/p3_platform_end_2026-09-25.json)):
  platform STOP episodes 15 → 1–10, but every candidate fails the gate or the per-frame
  no-new-event condition (set O `big_above` 12 → 11 STOP frames, `doubleT_platform` +1 event;
  0.6 × 10 frames: ride 46 → 50 events, 39 → 40 STOP episodes, one new event on an R ≈ 770 m
  curve). Flags off; output with them off identical to before. The far-rail check
  (`track.rails_far_check_enabled`) measured on the ride once: identical output on all 11 271
  frames (gate PASS, every row the same); it stays off.
- **The rail shadow of a large near object (P3, 25.09, delegated by the captain):** on set O the
  organizers' 2 × 2 m box at 26 → 9 m hid the bed behind it, the roof tilted the bed fit (rail head
  at 20 m 0.8–3.5 m off) and the STOP reported the bed at 3.0 m (frames 213–226); with a correct bed
  the box and a line at the corridor edge formed one cluster > 8 m that was dropped. Three rules, on:
  `track.floor_shadow_height` 1.0 (`floor_shadow_range` 30 m, `floor_shadow_min_bins` 5: the bed and
  the rail pair are fitted in front of the shadow or held), `cluster.oversize_split_max_length` 3.0
  (`oversize_split_max_distance` 30 m: the part inside the gauge of such a cluster is kept),
  `cluster.gauge_distance` true (the distance of the part inside the envelope). Set O #1 STOP frames
  with a wrong distance 12 → 0 (largest error 14.1 → 0.46 m), no STOP frame lost. Pre-registered;
  round 1 (40 m, split at any range) added false alarms on `doubleT_platform`, `roundT_doubleT` and
  set O #7, 35 m cost set O #8 one STOP frame; 30 m passes the gate with 5 rows better (#1 207 → 208,
  #9 42 → 49 STOP frames, set F straight false detections 35 → 24) and the ride, five bags,
  `doubleT_obstacle` and set F detections unchanged. +4 tests.
  [`p3_rail_shadow_2026-09-25.json`](docs/evidence/results/p3_rail_shadow_2026-09-25.json),
  [EXPERIMENTS §1h](docs/EXPERIMENTS.md).
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

## Dated status notes (moved from the README on 28.09)

The README was cut to the jury path on 28.09 (the independent judge A asked for it). These are its
dated paragraphs, verbatim, so that nothing they recorded is lost; the figures are those of their
dates, links are relative to the repository root as in the README. The current figures:
[`README.md`](README.md) "Current results". Notes on the 26.09–27.09 figures below: the object on the rail's "125 of 126"
is the replay of the 1 cm frame cache; on the raw recording (offline and through the node) it is
123 of 126, with a GO at frame 111 ([ARCHITECTURE «Known limitations»](docs/ARCHITECTURE.md#limitations-of-the-sealed-2709-detector-verified-2809)),
which the shortened output below leaves out; the learned opinion's "~1 s" is 10 processed frames
(~1 s at 10 Hz, ~2 s at 5 Hz, longer while the node catches up).

### From «Кратко для жюри»: the 26.09 cold-disk check and the output before the freshness controls

Проверка 26.09 со старым проигрыванием (4 ядра, без сети): `doubleT_obstacle` со
сброшенным кэшем страниц — нода обработала 34 кадра из 201, первый STOP через 15,5 с; тот же
прогон после `cat` — 139 кадров, STOP на 55,7–56,5 м
([`docs/evidence/rejudge_2026-09-26/`](docs/evidence/rejudge_2026-09-26/)). Повторный проигрыш
того же бэга уже идёт из памяти.

Исторический вывод на `doubleT_obstacle` до контроля свежести (сокращён; текущая нода
дополнительно проверяет возраст и удерживает STOP при потере входа):

```text
FAULT     # с 2 с после старта ноды, пока плеер загружает бэг (2,6–4 с): кадров ещё нет
GO        # первая секунда записи; CAUTION, когда человек подходит к габариту
STOP      # с 1,3–2,9 с записи (зависит от машины): человек на пути, затем предмет на рельсе, 55,5–56,6 м
CAUTION   # дважды по одному кадру в конце (предмет пропущен в кадре), затем снова STOP
FAULT     # через 0,5 с после конца бэга: входа нет, путь не контролируется
```

### Playback steps 3–4 of "How a bag is processed" with the 25–27.09 measurements

3. **Play the bag** (ReSense reads no bag files: it subscribes to what the player publishes) on the
   same `ROS_DOMAIN_ID` (default 0); `--delay 3` lets DDS discovery complete. CI plays it as uid
   1000 from a second container of the image, with the image's profile and with the stock Humble
   RMW (`rmw_fastrtps_cpp`, no XML profile, shared memory on: `PLAYER_DDS=stock
   scripts/console_test.sh`), as a host console does; stock clients reach the node over UDP
   because the node announces no shared-memory locators. A 360° recording played from a
   CycloneDDS console needs `net.core.rmem_max` ≥ 32 MiB on the host for its 24 MB clouds (jury
   step 0, `sudo sysctl -w net.core.rmem_max=33554432`): at Ubuntu's 212992 a CycloneDDS player
   delivered 0–1 of 201 of them, all at 32 MiB; a genuine stock Fast DDS player delivered every
   cloud at 212992 too (25.09, three team VMs; a run first recorded as "stock Fast DDS" was a
   CycloneDDS player, EXPERIMENTS §3b); the 120° clouds arrive either way; the node logs a WARN at
   start below 32 MiB. Optionally pre-read a 360° bag (`cat <bag>/*.db3 > /dev/null`) when memory
   allows; its clouds are 240 MB/s of recording, and from a cold disk the player can fall behind at the start
   (26.09 re-judgement: `doubleT_obstacle` with the page cache dropped, 337 MB/s cold reads: the
   node processed 34 of 201 frames, first `STOP` +15.5 s, FAIL; the same run with the bag in the
   page cache: 139 status messages, `STOP` at 55.7–56.5 m, PASS;
   [`docs/evidence/rejudge_2026-09-26/`](docs/evidence/rejudge_2026-09-26/)).
4. **Read the answer** ("What to look at"). Without step 3's queue limit, `ros2 bag play` (Humble)
   preloads up to 1 000 messages,
   all of a short recording, while its clock runs, then sends the overdue first seconds back to
   back: `FAULT` until then (2.6–4 s for 1.9 GB in the page cache, longer from a slow disk). On the
   P1/P2 follow-up, the first backlog preserves each observed input-period frame within the
   20 s startup cap; later live stalls use the normal 0.3 s sampling step and 5 s limit. The first
   cold-cache CI run failed before that correction (85/201 frames processed). An earlier 27.09 follow-up
   passed both original bags cold with explicit ten-message read-ahead; the obstacle stream became
   current at +8.8 s. The default 1,000-message read-ahead still failed freshness. See the
   [tested procedure and remaining limitation](docs/VM_GUIDE.md#41-dry-run-with-the-original-bags).
   The warm-cache 26.09 re-judgement reached real time in 3.4 s on `roundT_doubleT` and 9.5 s on
   the 360° `doubleT_obstacle`.

### The "Status (27.09)" block

**Status (27.09): package 1.0.0, the reviewed 27.09 detector, node v0.6.4**

The detector and defaults are those of the [27.09 quality cycle](docs/QUALITY_CYCLE_2026-09-27.md),
revised after two rounds of independent review and sealed ([`DETECTOR_FREEZE.md`](docs/DETECTOR_FREEZE.md));
node and dashboard freshness controls are implemented. No release is published (on hold by the
user's decision; the CI job `offline-build` makes the image archive of every commit).

**26.09 (dated record):** the P3d detector was sealed; the combined M2 / freshness candidate
produced one false STOP at 53 m in a clear-bag trial whose registered limit is zero and was not
merged ([the 26.09 record](docs/QUALITY_CYCLE_2026-09-26.md)). The [baseline source seal](docs/DETECTOR_FREEZE.md) and full gate reproduce all **146 gated values
(199 total comparison rows)**, with no missing rows or waivers. Earlier startup-fix measurements
pass original-bag idle cold/warm replays: first STOP +0.4 s after the first
processed cloud, decode+detect p95 36 ms, no recorded messages lost after catch-up settles.
The clear replay has zero alarms and p95 24 ms. Stock Fast DDS playback also passes; its clear
recording has one false alarm within the existing allowance of two. Startup still skips frames;
these timings exclude the player's disk preloading. [Raw evidence](docs/evidence/freeze_2026-09-26/README.md).

**Detector quality cycle of 27.09** ([record](docs/QUALITY_CYCLE_2026-09-27.md)): the four open
problems of 26.09 were attacked by five parallel experiments on one screen and the accepted
candidates switched on; two rounds of independent two-judge review found three safety regressions
and one violated bound, all fixed (`65c5a5b`, `352ca13`). Shipped: near the train the envelope is
the union of the rails' one and the one measured from the sensor axis (the frame the organizers
place objects in; no side is narrowed), a learned track opinion that may delay a doubtful STOP by
at most 10 frames (~1 s) in a track's life, never within 25 m or for a standing body within 40 m
(gradient-boosted trees retrained on the shipped detector, grouped held-out AUC 0.975, a 2× margin
on its threshold, never a veto), monitored-range caps from persistent sparse evidence, the
along-track association gate and the column body width, and far evidence for approaching tracks
(advisory, never hidden, otherwise). Full gate PASS against P3d, no waiver: ride false events /
STOP episodes 45 / 38 → **32 / 31** in-sample and **37 measured on ride pieces the opinion never
saw** (43 without it), five empty recordings 13 / 16 → 11 / 13, the organizers' edge cube first
STOP 5.2 → **35 m**, the edge box's track from 28.7 m (10.3 m), the box at the envelope top
101 → 111 m, set O inside STOP frames 384 → 411, GO overclaims 46 → 16, the captured
history-dependent clear-run STOP gone, history stress 78 → 55. **Where the gains come from** (one
mechanism off at a time): the ride / five-empty / history gains are mostly the learned opinion
(without it the ride keeps 43 / 35 and the history stress 75); the edge cube, edge box and the real
person's 3 extra frames need the envelope reference, i.e. the organizers' sensor-axis placement frame (without it 5.2 m and 58 of 61; the edge cube's 35 m also needs `floating_free_max_dy` 1.2, in a window bracketed by two set O objects); the set O range gains are far evidence. The
pre-registered placement of the
organizers' objects at new offsets on the empty recordings and the ride (not used for tuning):
matched frames 544 → **723** of 2 458, 45 of 72 cases, paired controls 0 (identical per case across the review fixes); with the reference switched off (the rails alone) 722 — the gain on new placements does not rest on the organizers' placement frame (a sensitivity study on seen shapes and backgrounds, not held-out recall). In-sample figures are marked as such in the record; the limits (the opinion's
threshold at the edge of the held-out positives, the reference's gains resting on the organizers'
placement frame while Q1 is open) are stated there.

**Criteria judgement:** the independent reviews and remaining gaps are in
[the scorecard](docs/SCORECARD.md). A fresh re-judgement of 28.09 (two new judges, the node input
path of 28.09) gives judge A 72.5 and judge B 62.5, combined **66.5/100** (Speed 8/10); the 27.09
quality cycle's third round, with other judges, gave 72 (round 2: 72, round 1: 67; 26.09: 64); the
requested 75/100 combined is not met. P4's preregistered
experiment (26.09) found the target in **45/72 cases and 544/2,458 visible frames** (27.09: 723),
with zero paired-control matches. This tests
synthetic combinations on seen backgrounds; it provides no real unseen-route recall result.
All 45 ride false targets now have exact point/history traces; 14 causes remain unresolved.
See [P4 audit](docs/P4_AUDIT.md), [experiments](docs/EXPERIMENTS.md) and
[decision history](docs/DECISIONS.md).

Since 24.09 (the 1.0.0 entry of [`CHANGELOG.md`](CHANGELOG.md)): optional C++ kernels (38–57 %
less detector time, identical output, built and tested in the CI image), DBSCAN on scipy's
cKDTree with scikit-learn's exact labels (1.3–2.6 ms less per frame, identical output), a
measured answer on the train speed (EXPERIMENTS §9), delivery as an image archive for the
offline stand, a CI step with a stock Fast DDS player, the long overhead rule for the station
false STOPs, the P3 rules of 25–26.09 for the organizers' objects (ALGORITHM §3.5), version
1.0.0 with a release workflow that publishes the image archive on a tag push, and a captioned
2:50 overview video. `scripts/regression_gate.py` re-checks the real-data rows, set O, the ride
and set F straight in one command. All current numbers:
[`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) "Current results" and §0.

**Earlier baseline checks (P3d, 26.09; dated):** 621 tests and 6 subtests passed, with no skips or
deselections; the full regression gate includes all six recordings, set O, the 11,271-frame ride
and set F straight. The five empty bags then had 13 false events / 16 STOP episodes, the ride
45 / 38; the person 58/61, rail object 125/126, and set O 384/801 visible in-envelope STOP frames;
edge objects STOPped only at 5–10 m (the 27.09 cycle changed all of these; see above). Prior measurements remain dated in
[EXPERIMENTS](docs/EXPERIMENTS.md) and [the evidence index](docs/evidence/README.md).

**Reproduced a second time the same evening** (the P3 / P4 completion pass, another fresh 4-vCPU
container, every cache rebuilt again from the organizers' links): the strict gate with the ride and
set F straight PASS with every gated row the same
([`regression_gate_2026-09-26_head_fresh_machine.json`](docs/evidence/results/regression_gate_2026-09-26_head_fresh_machine.json));
the rate / re-mount checks (5 Hz 10 / 10, +3° roll 14 / 16, +3° pitch 17 / 18 events / STOP
episodes) and the 221-start ride census (18 starts with a STOP, none within 10 m) value for value;
P4's candidate B (`tracking.near_escalate_voxels` 8) passes the full gate and every acceptance
check with only set O #4 changing (2 → 3 STOP frames). The baseline decision retains the threshold
at 10; candidate B is not shipped. The envelope union with its review fixes passes the full
gate too (#4 2 → 9) and stays off until the organizers answer Q1. Details: EXPERIMENTS §1p,
[`docs/P4_AUDIT.md`](docs/P4_AUDIT.md) "Completion on a second machine",
[`completion record`](docs/evidence/results/p4_completion_2026-09-26_evening.json); a third
judge's cross-check of the score: SCORECARD §0.7.

### What the organizers' answers changed (the full list)

What the organizers' answers changed ([`docs/organizers/answers.md`](docs/organizers/answers.md)):

* the strict decision uses **their train envelope, 2.1 × 3.0 m**; the wider v0.5 polygon is the
  advisory zone; objects **hanging** into it (broken cables) are obstacles; one that dips in with
  only a few returns is found by the hanging stage only for groups ≤ 0.5 m, within 0.8 m of the
  axis, out to 60 m and where the rails are locked (ALGORITHM §6);
* **low objects on a rail**, or straddling the envelope floor like their object, are found by a
  bed-anomaly stage; tall objects are reported out to the trusted axis range (~200 m on straight
  track; the tunnel returns nothing beyond ~210 m), but on the organizers' own objects no STOP
  comes beyond ~101 m (set O), and the 148–154 m person is our own synthetic;
* the **mount is found from the data** (orientation, roll, pitch). 24.09
  ([`mount_and_switch_qa.md`](docs/organizers/mount_and_switch_qa.md)): the test bags use the
  mounts of the provided ones, the LiDAR 1 075 mm above the rail head on the train's centreline,
  so the auto-calibration stays as a safeguard; glitches at switches (states unknown) will not
  count against a solution;
* every frame reports an **estimated monitored range** and input health. An object can be missed
  within that range; `GO` means no obstacle was detected.

### The headline results table as of 27.09 (the P3d history in each row)

Headline results (kinds and placement modes: [`docs/README.md`](docs/README.md) "Glossary"):

| metric | value | kind | date | source |
|---|---|---|---|---|
| false alarms, five obstacle-free bags (2 287 frames) | since 27.09: **11 events**, 40 alarm frames, 13 STOP episodes (in-sample: the track opinion's negatives include these recordings; without the opinion 13 events / 16 episodes); before: 13 events, 58 alarm frames, 16 STOP episodes (14 / 60 / 17 before `tracking.column_hold` 2, 20 / 107 / 27 before the long overhead rule of 25.09) | real | 25.09, 27.09 | EXPERIMENTS §1f, §3a; [QUALITY_CYCLE_2026-09-27](docs/QUALITY_CYCLE_2026-09-27.md) |
| false alarms, 20-minute 13 km ride (11 271 frames) | since the 27.09 cycle: **37 events, 2.8 per km, on ride pieces the learned opinion never saw** (measured: each pair of the ride's 8 pieces run with a model trained without them); in-sample 32 events, 2.5 per km, 130 alarm frames, 31 STOP episodes; without the opinion 43 events / 35 episodes; before 27.09: **45 events, 3.5 per km** (in-sample: the ride decided the rules of 25.09), 183 alarm frames, 38 STOP episodes (46 / 187 / 39 before `lowobj.rail_start_within` of 26.09, 46 / 197 / 39 before `tracking.column_hold` 2, 47 / 204 / 39 before the rule) | real | 25.09, 26.09 | EXPERIMENTS §1f, §3a, §1n |
| crossing person, `doubleT_obstacle` | since 27.09: STOP in **61 of 61** frames inside the envelope, from the first frame inside (frame 8), distance error ≤ 0.23 m — the gain is the envelope reference (the organizers' sensor-axis frame); from the rails alone 58 of 61 from frame 11 (0.3 s after entering), as before | real | 24.09, 27.09 | EXPERIMENTS §0; [QUALITY_CYCLE_2026-09-27](docs/QUALITY_CYCLE_2026-09-27.md) |
| object lying across the rail (0.45 × 0.6 × 0.3 m) | **125 of the 126** frames after the person leaves it (124 before `calibration.keep_within_deg`, 25.09 round 2) | real | 24.09, 25.09 | EXPERIMENTS §0, §1i |
| health warnings, `CAUTION` | warnings on 196 of 13 759 frames (1.4 %: stations, switches); `CAUTION` on 27–69 % of the frames of the empty bags, 42 % of the ride (re-measured 26.09 with the node's decision rule) | real | 24.09, 26.09 | EXPERIMENTS §0 |
| organizers' synthetic objects (set O, 1 510 frames) | since 27.09: STOP in **411 of 801** visible in-envelope object-frames, the edge cube from **35.0 m** (18 frames), the edge box's track from 28.7 m (the scorer, matching within 1 m of the 2 m box's centre, credits 7 frames from 18.3 m), the box at the envelope top from 111.4 m, the plank from 87.2 m, the floating cube from 55.8 m, 0 background frames, outside objects unchanged ([QUALITY_CYCLE_2026-09-27](docs/QUALITY_CYCLE_2026-09-27.md)); before 27.09: STOP for **8 of 8** in-envelope objects since the near escalation of 26.09 (6 of 8 before, 5 of them held; 5 of 8 before the hanging stage of 25.09): 2 × 2 m box from 98 m, plank across the rails 82 m, 0.3 m cubes from 43–53 m (the hanging one from 52.5 m since round 2 of 25.09, 34.0 m before), the 5 cm hanging object from 30.1 m (missed before 25.09), the 2 × 2 m box at the envelope top in **51 of 124 frames**, STOP on every frame from 101.3 m under the P3d STOP keep (the scorer's 90 % held-from field reads 111.4 m) (22 frames, held-from 23.9 m on P3c), the edge 2 × 2 m box from 10.3 m (6 frames), and the edge 0.3 m cube at 5.2 m (2 frames); STOP in **384 of 801** visible in-envelope object-frames, 6 false STOP frames on the outside 2 × 2 m box, 3 background alarm frames; set O has been inspected before and is not unseen validation | organizers' synthetic | 24.09, 25.09, 26.09 | [P4_AUDIT](docs/P4_AUDIT.md), EXPERIMENTS §1h, §1i, §1l, §1o |
| long range, straight track (set F) | the regression gate's current run (27.09 detector): person first confirmed at **151 m** median (6 of 6), trolley 151 m, 1 m crate 124 m, 3 cm hanging cable 99 m; **0.5 m box: 1 of 6** (18 of 110 frames within 50 m) — small objects low on the bed between the rails are a known blind spot (also the 0.3 m cubes of set O: STOP only from 43–56 m). The 24.09 script gave the person 148 m, in ≥ 90 % of the frames of every 10 m band from 115 m | synthetic, legacy | 24.09, 25.09, 27.09 | EXPERIMENTS §2d; [gate](docs/evidence/results/regression_gate_2026-09-27_quality.json) |
| long range with a given train speed | person 167 m, crate 182 m (held only from 79 m) | synthetic, legacy | 24.09 | EXPERIMENTS §2d |
| train speed | none is given (no odometry in the recordings); our LiDAR-only estimate is accurate (median error 0.06–0.08 m/s on 55–96 % of the moving frames), but even a perfect speed does not improve the organizers' check (no earlier first STOP, 6 → 17 false STOP frames on the box outside), so it stays off | real, organizers' synthetic | 24.09 | EXPERIMENTS §9 |
| curves, stations, low objects | R ≈ 350 m curves 6 of 7 from 58–86 m (sightline past the inner wall); station stops 6 of 6 from 113 m; 30 cm on a rail head 6 of 6 from 42–49 m; person lying across the rails 6 of 6 from ~64 m | synthetic, legacy | 24.09 | EXPERIMENTS §2d |
| sensor limit | no return beyond 210 m in any of the 13 759 frames: 300 m is beyond this sensor | real | 24.09 | EXPERIMENTS §2d |
| other mounts | upside down, `+x` forward, backwards found; tilt recovered to 0.0–0.5° on re-mounted frames of 3 recordings | real, re-mounted | 22–23.09 | EXPERIMENTS §6 |
| offline timing per frame | **the 27.09 detector, re-measured: 18.0–22.9 ms mean, p95 22.7–32.6 ms**, max 57 ms, on set O and three 120° / 360° recordings (one core, C++ kernels, idle 4-vCPU sandbox); **worst stretch: ride frames 5700–5900 (a dense station scene) 57 ms mean, p95 111 ms, max 143 ms** (clustering; P3d similar); the node's path without ROS transport (decode of the organizers' PointCloud2 layout, crop, rotation, detector) p95 32–48 ms, peak RSS 161–248 MB ([QUALITY_CYCLE_2026-09-27](docs/QUALITY_CYCLE_2026-09-27.md) "Speed"); 26.09 with the C++ kernels: 22.7–30.7 ms mean, p95 32.8–42.1 ms on set O and the 120° / 360° recordings (one core, idle 4-core machine, the re-judgement of 26.09; the numpy path there 78.3 / 95.5 ms at 360°); 23.09 on the numpy path: 42–64 ms mean, p95 53–78 ms on every recording (health monitor not included: 7–14 ms more); 24.09 on another idle VM 36.5–52.2 / 50.3–67.1 ms; the optional C++ kernels: −38…−57 %, identical output; DBSCAN on cKDTree (25.09): −1.3…−2.6 ms more on the native path | timing: sandbox | 23–25.09, 27.09 | EXPERIMENTS §3, ARCHITECTURE "Native kernels" |
| ROS node in Docker, end to end | since 28.09 (input read from its serialized bytes, visualisation built only when watched; decode and detector unchanged): input publication → result through DDS, p95 of the current results at 360° **~10–20 ms lower**: an independent judge's 5 alternating pairs on a 4-vCPU Xeon 2.1 GHz, median 113 → 102 ms with the recording cached, 137 → 118 ms from a cold disk (the team's 2 pairs: 120–127 → 93–97 ms); p95 **not reliably under the 100 ms frame period** there. 120°: 54–64 ms. CI runner, cold, 28.09: **60 ms at 360°, 37 ms at 120°** (an earlier run on another runner, 27.09: 126 / 49 ms; unpaired). Decode + detect unchanged (p95 ~75 ms at 360° on the sandbox); node process 0.4–0.8 cores, peak RSS 0.13–0.48 GB; 10 fps, no frames dropped after start-up; the detector's input byte-identical on all 453 frames. Before 28.09: 120°: 10 fps, p95 76 ms; 360°: 7–10 fps; ~100 % of one core, 186 MB (v0.6.3) | timing: sandbox, CI | 23–24.09, 28.09 | EXPERIMENTS §3b, §3d; [evidence](docs/evidence/node_input_2026-09-28/README.md) |

Set F uses legacy placement, which can flatter curves and envelope edges: P4's paired rerun found
0 matches beyond 100 m on seven curve / edge scenes in either mode, and on straight track a person
anchored on the near rails first at 154 m (legacy 150 m, 5 approaches; not surveyed ground truth).
Set S on 108 real empty frames: 22 / 67 bed placement, 30 / 68 legacy (small samples; the P3d
replay uses the same sample identities as the P3c run). Details:
[`p3d paired set S report`](docs/evidence/results/p4_p3d_setS_paired_2026-09-26.json).

### Acceptance test notes of 25–27.09

`scripts/dry_run.sh <bag>` builds with `--no-cache`, waits for the node before playing, captures
`/resense/status` and checks it (`scripts/check_dry_run.py`): on `doubleT_obstacle` the person in
50–62 m, p95 of decode + detect ≤ 100 ms, no frame of the recording left unprocessed after the
start-up; `--expect-clear --max-alarm-frames 2` on `roundT_doubleT` is the false-alarm half (the
allowance covers the trackside device at 48–54 m, 1 frame in 3 of the 10 ROS runs of 25.09; the
column at 101–149 m, 3 frames at 111–115 m from the original bag and 2 at 128–130 m from the cache,
is advisory since `tracking.column_hold`, EXPERIMENTS §3a); thresholds are arguments of
`scripts/check_dry_run.py`, the raw capture goes to `out/dry_run/` (`status.jsonl`, `node.log`).
The 23.09 rehearsal in the sandbox: EXPERIMENTS §3b.

**"After the start-up"** (25.09): `ros2 bag play` (Humble) preloads the bag with its clock running
and then sends the overdue first seconds back to back; the node works through that burst one frame
per 0.3 s of recording and skips the rest on purpose (`node.catchup_skipped`), at 360° on a 4-core
VM until +7.7–7.9 s: 39–53 frames of `doubleT_obstacle` skipped by design in the passing runs of
25.09, none lost in transport after the start-up (EXPERIMENTS §3a). So `--max-dropped` counts from
the later of `--settle-s` (5 s) and the frame on which the node is back on the newest one
(`node.catchup` false), at most `--max-settle-s` (15 s): a catch-up still running then fails, one
that never ends does not move the settle point at all.
`dry_run.sh` also passes `--bag`: the checker then counts the recording's own messages the node did
not process, so the 4 frames `doubleT_obstacle` itself lacks (at +14.0 and +16.9 s) are not drops.
The node's stamp-gap count `node.dropped_frames` is printed as before (EXPERIMENTS §3a).

**Cold-disk startup (26.09 night):** the final node grants a new recording up to 20 s of initial
backlog, preserves short queues, then restores the existing 5 s bound for later stalls. With
zero bag pages resident before playback, `doubleT_obstacle` PASSES: 148 processed frames,
143 alarm frames, first STOP +0.4 s, p95 36 ms and no post-settle recorded messages unprocessed.
Catch-up settles at +7.4 s of recording. Warm playback and the clear recording also pass.
The optional pre-read before jury step 3 can reduce disk delay; the supported cold playback uses
`--read-ahead-queue-size 10` for both original bags. The earlier cold run used the default queue.
[Evidence](docs/evidence/freeze_2026-09-26/README.md) retains the earlier failures. One additional
cold trial under two direct readers (127.4 MiB/s combined) also passes: p95 36.37 ms, first STOP
+0.7 s, no post-settle losses. This is a bounded workload, not a measured overload limit.

**Supported playback recheck, 27.09:** [archive-cache CI](docs/evidence/p1_p2_supported_playback_2026-09-27/README.md)
passed both original bags cold with the ten-message queue. The obstacle bag had 199 status
messages, STOP at 55.5–56.5 m and p95 76 ms; its first STOP was fail-safe while stale, and its
first current STOP followed catch-up at +13.6 s. All 63 source messages after catch-up were
processed. The clear bag had 252 statuses, zero alarms and p95 48 ms. The archive and database
hashes match the earlier verified recordings. This does not validate Humble's 1,000-message
default or an unbounded overdue burst.
[A later seven-job rerun](docs/evidence/p1_p2_supported_playback_2026-09-27/cached_bags_run_36319767736/README.md)
also passed after downloading, verifying and caching the two original bags: 201 obstacle statuses,
first current STOP and catch-up at +2.6 s, p95 47 ms; 252 clear statuses, zero alarms, p95 32 ms.
Both cold runs retain their separate timing and raw evidence.

### Release sentence and repository-layout rows of 25–26.09

`IMAGE_TAR=<archive> OFFLINE=1 ./scripts/dry_run.sh <bag>` is the same on real bags. A pushed
release tag (`v1.0.0-rcN`, `v1.0.0`) would run `.github/workflows/release.yml`: tests, the runtime
archive built, removed and loaded back, both bags through the loaded image (internal network and
`--net=host` with a stock player), then the GitHub release with the archive, its `.sha256` and
`SHA256SUMS`; no tag or release is planned now (deferred by the captain, 25.09: the system is still
in development). `scripts/bench_8core.sh` bundles the acceptance runs and the timing for the team's
8-core machine (the organizers' i7 stand is not available before the upload).

| [`tests/`](tests/) | The latest P1/P2-branch local run passed 667 core/tool tests and 6 subtests; one `new_data` cache test was deselected because `/data/cache/new_data` is absent ([P1/P2 receipt](docs/evidence/p1_p2_completion_2026-09-26/README.md); [quality-cycle test evidence](docs/evidence/results/quality_root_checks_2026-09-26/README.md)) |
| [`web/`](web/) | browser dashboard (offline replay; live via rosbridge, installed separately), Foxglove layout, label tool, 16 headless Chromium tests on the P1/P2 branch |

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
