# Captain Board, 16–28.09 (archived)

> **Purpose:** the captain's dated board as it stood on 28.09 before the independent judgement of
> 28.09 evening: the delegated-work notes, the criteria checklist C1–C25, the action list, the
> completion list, the release notes and the analysis of 24.09. Kept as history; the scores of the
> earlier judgements are removed. The current board is [`../CAPTAIN.md`](../CAPTAIN.md), the current
> judgement [`../SCORECARD.md`](../SCORECARD.md).
> **Audience:** team · **Owner:** P1 · **Language:** EN · **Status:** archived 2026-09-28, not maintained

## Current delegated work — 28.09

**28.09, P1 lane (8.3 speed on the node side, CI, Docker, docs):** the node reads its input clouds
from their serialized bytes (`resense_ros/fastcloud.py`; the detector's input byte-identical on all
453 frames of both original recordings), publishes the decision first and builds the visualisation
only for subscribers. End to end through ROS (player publication → result), p95 at 360° on a 4-vCPU
sandbox: 113 → 102 ms cached, 137 → 118 ms cold (an independent judge's 5 pairs); CI runner cold
60 / 37 ms at 360° / 120°. The node reports `decode_ms`, `detect_ms`, `cpu_cores` and
`rss_peak_mb`; `play_bag.sh` waits for readiness;
CI runs the original bags and uploads the image archive for this working branch
([evidence](../evidence/node_input_2026-09-28/README.md), EXPERIMENTS §3d). The detector seal is
unchanged. **Decided 28.09:** the
image's default command runs the node with `freshness_mode:=replay` for recorded bags (`d359a06`;
the node's own default stays `live`); the GO at `doubleT_obstacle` frame 111 (the rail object missed
twice in a row, `hold_misses` 1) is a documented limitation, the detector stays sealed
([ARCHITECTURE «Known limitations»](../ARCHITECTURE.md#limitations-of-the-sealed-2709-detector-verified-2809)); judge A's
per-frame outputs of the sealed detector are added
([evidence](../evidence/judge_outputs_2026-09-28/README.md)); the documents were corrected for both
judges' findings (DECISIONS rows 18–27). Open: the team slides (P2 / team), the release (§5).

## Delegated work — 26.09 night (dated)

**27.09 integration:** the P1/P2 completion branch is integrated, with startup cadence,
dashboard reconnect handling and remote-viewer checks. Completed experiment histories are
retained without enabling rejected detector variants. The [integration record](BRANCH_INTEGRATION_2026-09-27.md)
maps the source branches and validation; the earlier `d480b13` archive below is dated delivery evidence.

**27.09 operating procedure:** the captain's follow-up request adopts the proven ten-message
rosbag2 read-ahead limit for the jury command, dry run, and demo players. The first follow-up
CI attempts were blocked before playback by Google Drive's quota page. After the quota reset,
[run 36313880352](https://github.com/pmixay/ReSense/actions/runs/36313880352) passed all six jobs
on playback commit `5a27c66`: the archive and both original bags matched their recorded hashes,
both cold replays passed, and the verified archive entered the Actions cache. The 360° bag's
first STOP was fail-safe while stale; its first current STOP and end of catch-up were at +13.6 s,
near the 15 s acceptance cap. [Current receipt](../evidence/p1_p2_supported_playback_2026-09-27/README.md).
The later [seven-job run 36319767736](../evidence/p1_p2_supported_playback_2026-09-27/cached_bags_run_36319767736/README.md)
also passed: the new dataset job downloaded and verified both original bags, saved them to Actions
cache, and Docker restored them without downloading. Both cold replays passed; the obstacle bag's
first current STOP and end of catch-up were at +2.6 s in this run. The two startup times are
separate measurements, not a detector change.
C5/C7 and action 21 are closed **for this supported procedure**. Humble's 1,000-message default
remains unsupported for cold whole-bag bursts. PR #12 is merged into `main`; detector quality,
release publication, and physical rehearsal remain open.

**Latest user decision: release publication is on hold.** No release tag has been created or
pushed. The user asked for a deeper review of system weaknesses and whether detector development
should continue before a final freeze, then authorized the work. The [completed quality cycle](QUALITY_CYCLE_2026-09-26.md) records
the measured weaknesses, candidate decisions and unmet acceptance conditions. Keep the sealed baseline and its evidence; do not publish
an RC or treat it as final quality acceptance. Review priorities are detection coverage, envelope
uncertainty, false alarms, output freshness and independent evaluation.

The main branch retains `_ride_p3d` detector behavior and its default configuration; the source
manifest is in [DETECTOR_FREEZE.md](../DETECTOR_FREEZE.md). M1, A1, D1 and T1 were rejected. M2 passes its
offline comparison but remains unmerged because the combined runtime trial fails. The original
near-escalation threshold remains 10 and the axis union stays off. Q1 remains unanswered.

Node and dashboard freshness controls are implemented: explicit live/replay clocks, bounded age,
invalid-range suppression, consumer expiry and held STOP. All 15 functional checks pass. The
combined candidate passes cold, warm, bounded-load and stock Fast DDS switch checks, with zero
post-settle message loss in every capture. **Standalone clear fails with one raw detector STOP
at 53 m against the registered zero-alarm limit.** Exact raw-sequence replay reproduces the
failure in both P3d and M2. The completed diagnosis identifies a trust increase after boundary
loss and a merged fragment that changes the column's apparent width. T1 removes the two traced
false STOPs but fails its range-retention gates (50% and 93.4%, versus the required 95%); it is
rejected. The failed combined-image archive remains a review artifact, not accepted detector evidence.

The earlier P3d core plus freshness delivery code, `d480b1330491da838d6fb4996e34e37b3c060915`, passes
all six jobs in [CI run 36275557220](https://github.com/pmixay/ReSense/actions/runs/36275557220).
The loaded runtime archive passes explicit replay/freshness checks and asserts that native
kernels are available and enabled. These synthetic CI checks do not close the original-bag
clear failure. Download, checksum, offline loading and local source/native verification of
this exact CI archive pass ([receipts](../evidence/results/quality_delivery_2026-09-26/README.md)).
Public publication remains on hold (§4); the combined M2 archive has different source.

P4 traced the exact target points and histories of all 45 ride false events; 14 causes remain
unresolved. P3 traced all organizer-object frames and all 72 placement cases. M2 preserves all
146 enforced gate metrics and all original placement results; its combined code passes 668 tests
and six subtests. Its monitoring change still leaves 36 GO diagnostic overclaims and adds no
detection recall. The public presentation retains the earlier dated detector evidence. The
supplied names/nicks/school and four individual portraits are in a local private preview; city,
team-formation details, group photo/contact details and human rehearsals remain pending. 
Earlier tables below retain their dated evidence; this section and §4 govern current status.

## 1. Role and dates

P1 is the system analyst and ROS 2 / integration developer ([`PLAN.md`](../PLAN.md)): the jury chain
`docker load` (or `docker build`) `→ docker run → ros2 bag play → /resense/decision`, the
evaluation protocol, liaison with the organizers ([`QUESTIONS.md`](../QUESTIONS.md),
[`organizers/answers.md`](../organizers/answers.md)), merges, the submission (sent by the captain
personally with all its links, 25.09) and the pitch; in the criteria: 8.3 (node side), 8.5 (CI,
Docker, docs), 8.6, the §7 deliverables and 8.8. Dates (organizers' README): upload by 29.09 23:59
(target 18:00), technical expertise 30.09–14.10, pitch 23.10.


## 2. Criteria board (25.09)

Statuses as of 25.09 ~13:30 UTC on the PR #12 head (the morning's merges up to `79109f5`; then
the VM run of `ead8502` (PR #13: dry run, bench, gate, export, offline rehearsal on a 4-core team
VM) and its fixes (`5be4143` drops and socket buffers, `d117c8c` `tracking.column_hold`), the code
review's fixes (`0bb1ba3` long-rule bottom, `1fc127f` gate, `163f34b` sha256, `ade8a97` IPv6,
`f9498a3` VM guide)), checked against the repository and CI: every push of PR #12 green, last run
36133233507 (`afa5ae1`). GitHub at 13:30 UTC: 0 tags, 0 releases, 1 open PR (#12), the repository
public. HUMAN = only a person can close
it. The captain's decisions of 25.09 (§9) are applied: no tags or releases now (the system is still
in development), the submission is his own, deployment and the presentation come later. HANDLED =
done by the captain personally (counted as done); DEFERRED = put off by the captain; LATER = team
work after development.

| # | criterion (spec) | status | evidence / gap |
|---|---|---|---|
| C1 | image builds from scratch, no manual steps (§3.3.1, §7.2, 8.6) | DONE | `docker/Dockerfile`: pip pinned, non-editable install checked from `/`. CI run 36123184213 (`79109f5`): the `docker` job builds the image; the `offline-build` job builds the runtime image `--no-cache` from `git archive HEAD` (1.34 GiB). Gap: apt and the base image unpinned (accepted); the stand has no internet, so the image goes as an archive (C25) |
| C2 | `docker run` starts the node with no arguments, either topic / frame pair (answers §1 #2) | DONE | default command (since 28.09, `d359a06`) `ros2 launch resense_ros detector.launch.py freshness_mode:=replay`, for recorded bags (before: without the argument, and the clear recorded bag gave `FAULT` on all 319 decision messages, judge A 28.09; the node's own default stays `live`, for a live LiDAR); topic auto-discovery; CI (run 36123184213) starts it with no arguments and switches between both pairs ("input switched … detector restarted"), also from the runtime archive (`offline-build`); `tests/test_node.py` |
| C3 | every parameter a launch argument; mount configurable (Q&A fact 7) | DONE | `launch/detector.launch.py`: 31 launch arguments, the node declares exactly those plus `config_file` (checked by script 25.09), plus `bag:=`, `rviz:=`, `loop:=`, `rate:=`, `delay:=` |
| C4 | organizers' console path: `ros2 bag play` by a normal user on the host | DONE (decided 25.09 for the captain) | CI plays as uid 1000 from our image twice: with the image's UDP profile and with stock Fast DDS (`PLAYER_DDS=stock` in `scripts/console_test.sh`: no XML profile, shared memory + UDPv4, a stock uid-1000 listener), green on every run since 36112092652 (`rmw_fastrtps_cpp`, fastrtps 2.6.12); the node announces no shared-memory locators, so stock clients reach it over UDP. **A real host console, 25.09** (team VM, stock ROS 2 Humble from apt on Ubuntu 22.04, the player and `ros2 topic echo` as uid 1000, code `7290873`, [`evidence/dry_run_2026-09-25/`](../evidence/dry_run_2026-09-25), EXPERIMENTS §3b): `rmw_fastrtps_cpp`, no profile, **PASS** (both recordings into one node, 137 `STOP`, 55.7 m). A player on `rmw_cyclonedds_cpp` delivered none of the 360° clouds at Ubuntu's `net.core.rmem_max` 212992 and all of them at 32 MiB (`diag_cyclonedds_buffers/`); fixed as far as the image can (`5be4143`): the UDP profile asks for a 32 MiB receive buffer (the kernel caps it at `rmem_max`, so nothing changes on a stock host), the node logs one WARN below 32 MiB naming `sudo sysctl -w net.core.rmem_max=33554432`, README / ARCHITECTURE / [`VM_GUIDE.md`](../VM_GUIDE.md) §4.2 say so. Only a jury console configured for CycloneDDS needs the host setting; the confirmation run is in VM_GUIDE §4.0. **Re-run 25.09 afternoon on a second team VM** (4 physical cores, code `76bf24e`, [`evidence/dry_run_2026-09-25_2/`](../evidence/dry_run_2026-09-25_2), EXPERIMENTS §3b): the stock player in Docker (`PLAYER_DDS=stock`) PASS and the CycloneDDS host console at `rmem_max` 32 MiB PASS (144 `STOP`), and a host console labelled "stock Fast DDS" failed at 212992 (5 of 5) and passed at 32 MiB, as did the offline README jury console (6 of 201); **corrected 25.09 evening: those players were CycloneDDS** (the host had no Fast DDS RMW: `ros-base` and `rmw-cyclonedds-cpp` in one apt call install none; [`diag_host_fastdds/README.txt`](../evidence/dry_run_2026-09-25_2/diag_host_fastdds/README.txt)). **Third team VM, 25.09 evening** (code `d4b396e`, the player's RMW checked in `/proc/<pid>/maps`, [`evidence/dry_run_2026-09-25_3/`](../evidence/dry_run_2026-09-25_3), EXPERIMENTS §3b): a genuine stock Fast DDS player (fastrtps 2.6.12) PASS at 212992 over UDP (2 of 2) and in shm mode (2 of 2, over `/dev/shm`), PASS with README step 0; CycloneDDS PASS at 32 MiB, FAIL at 212992. So only a CycloneDDS console needs step 0. Covered in the jury instructions since this revision: README «Кратко для жюри» starts with step 0 `sudo sysctl -w net.core.rmem_max=33554432` (lasts until a reboot; the node's WARN names it too). The opt-in shared-memory mode (`RESENSE_DDS=shm`) passes [`VM_GUIDE.md`](../VM_GUIDE.md) §4.6 (third VM), but it was built for a Fast DDS failure that turned out to be CycloneDDS, and a CycloneDDS player cannot use it; flipping the default is the captain's call. **Decided 25.09** (the captain delegated it): DONE on the jury instructions: step 0 raises the host buffer, the node's WARN names it, both proven on the VM (32 MiB: every cloud, both players); the shared-memory mode stays an improvement, not a condition |
| C5 | start of a played bag not lost (8.3, 8.6) | DONE for supported read-ahead 10; Humble default 1000 remains unsupported on cold whole-bag bursts | v0.6.4 catch-up (`input_queue_depth` 40, `catchup_step` 0.3); CI on the synthetic bags: 39–40 frames in the first 5 s, first STOP at +1.9 s (every playback step). With the original bags on the team VM (25.09, raw captures committed, [`evidence/dry_run_2026-09-25/`](../evidence/dry_run_2026-09-25)): `doubleT_obstacle` first STOP at +1.6 s through ROS although its first cloud reached the node 5.7–6.5 s after the player's clock started (the player's preload); the catch-up was back on the newest frame at +7.7–7.9 s (EXPERIMENTS §3a). Since `5be4143` the status reports the catch-up's own skips (`node.catchup_skipped`, `node.catchup`). Cold CI runs 362745 and 362776 failed; read-ahead 1 delivered no input and was cancelled. Run 362814 passes both cold originals with `BAG_READ_AHEAD_QUEUE_SIZE=10`: `doubleT_obstacle` 201/201 messages, STOP +1.1 s at 55.5–56.6 m, 78 ms p95, catch-up settle +8.8 s, and zero source messages unprocessed; `roundT_doubleT` 252 messages, zero alarms, 48 ms p95, and zero source messages unprocessed. The first obstacle STOP is fail-safe while source freshness is stale; current results follow catch-up. Four obstacle-bag gaps are in the recording itself. The default read-ahead 1000 still produces stale output. The supported jury and dry-run procedure now uses read-ahead 10; the 1,000-message burst remains a documented limitation |
| C6 | acceptance script asserting the result | DONE | `scripts/dry_run.sh` + `scripts/check_dry_run.py` (`--distance 50:62 --max-p95-latency 100 --max-dropped 0`); `IMAGE_TAR` / `OFFLINE` (offline stand) and `DOCKER_ARGS`; `scripts/bench_8core.sh` runs it on both bags, native and numpy. First used with the original bags on the team VM, 25.09 (C7). Since `5be4143` drops count after the settle point (the later of 5 s and the end of the start-up catch-up, at most 15 s) and, with `--bag` (which `dry_run.sh` passes), against the recording's own messages, so its holes are not drops; `scripts/replay_node_frames.py` (`fce04aa`) replays offline the frames a node capture processed. Gap: it needs the dataset, so CI runs `check_dry_run.py` only on the synthetic bags |
| C7 | clean-machine dry run with the original bags (§7.2) | DONE for supported read-ahead 10 (both original cold-bag checks pass); the jury stand remains unavailable | **Re-run 26.09 evening by the re-judgement** on a fresh 4-core sandbox (image from `docker/Dockerfile` at `be5f5fc`, the organizers' original bags, [`evidence/rejudge_2026-09-26/`](../evidence/rejudge_2026-09-26)): `OFFLINE=1 dry_run.sh` PASS on both bags and the stock Fast DDS uid-1000 console PASS — **with the bag in the page cache**. With the page cache dropped, `doubleT_obstacle` initially failed because the player sent a whole overdue recording burst; subsequent cold attempts 362745/362776 failed and read-ahead 1 was inconclusive. Current-source run 362814 passes both originals cold using read-ahead 10: obstacle bag 201/201 messages, STOP +1.1 s at 55.5–56.6 m, 78 ms p95, 0 of 113 post-catch-up source messages unprocessed; clear bag 0 alarm frames, 48 ms p95, 0 of 201 post-settle messages unprocessed. The source has four obstacle-bag gaps. Default read-ahead 1000 still produces stale output; the supported procedure now uses 10 and does not cover an unbounded overdue burst. Before: **Run 25.09 on a clean team VM** (8 vCPU = 4 physical cores, `--no-cache` build, code `7290873`, [`evidence/dry_run_2026-09-25/`](../evidence/dry_run_2026-09-25), [`evidence/vm_2026-09-25/summary.md`](../evidence/vm_2026-09-25/summary.md), EXPERIMENTS §3a / §3b): console tests and the stock host console PASS; `dry_run.sh` failed two criteria, both root-caused and fixed the same day. (1) `doubleT_obstacle`, "20 frames dropped after 5 s" (person 55.7–56.5 m, p95 69 ms, 10 fps): 16 were the node's own start-up catch-up skips (back on the newest frame at +7.7–7.9 s, after the player's 5.7–6.5 s preload) and 4 are missing from the recording itself (same stamps in every run; its receive times jump 0.2 and 0.4 s): no frame was lost by the node; the checker counts after the catch-up and against the bag since `5be4143`. (2) `roundT_doubleT`, 3 alarm frames at 111–115 m (2 allowed) in all 10 VM captures: one column at 101–149 m that is a `column` in the frames showing > 2.2 m of it and inside the gauge in those showing 1.6–2.2 m; `tracking.column_hold` 2 (pre-registered 3 / 2 / 1, `d117c8c`) keeps such a track advisory: ≤ 1 alarm frame left on every capture (the 53 m trackside frame, 3 of 10), gate PASS. **Confirmed 25.09 afternoon** on a second clean team VM (4 physical cores, the `--no-cache` build its first build, code `76bf24e`, the original bags; [`evidence/dry_run_2026-09-25_2/`](../evidence/dry_run_2026-09-25_2), EXPERIMENTS §3b): `doubleT_obstacle` PASS (person 55.5–56.5 m, p95 70 ms, 10 fps, the catch-up back on the newest frame at +6.9 s, the 4 drops after it are the 4 frames missing from the recording, 0 of its messages not processed); `roundT_doubleT` PASS (0 alarm frames; `replay_node_frames.py`: node 0, replay 0); both PASS again offline from the archive (C25). The organizers' stand is not available before the upload |
| C8 | timing on an 8-core analogue of the i7-9700E (8.3; the stand is not available before the upload, [`organizers/answers.md`](../organizers/answers.md) §6) | DONE (the captain, 25.09) | **Closed on the 4-core run** (the captain: "if 4 core ran matched expectations it will run even better or similar on 8 core"): team VM, 8 vCPU = 4 physical cores (Xeon Icelake 2.0 GHz), half the cores of the i7-9700E (8 cores, 2.6–4.4 GHz); `scripts/bench_8core.sh`, [`evidence/bench_2026-09-25/`](../evidence/bench_2026-09-25), EXPERIMENTS §3a: `dry_obstacle_native` 10 fps, p95 70 ms, max 98 ms (limit 100 ms); its 20 drops after 5 s were no losses of the node (16 start-up catch-up skips, 4 frames missing from the recording itself; C7), and the checker counts that way since `5be4143`; both console tests PASS; offline node path at 360° 43.4 ms native. Numpy 8.3 fps, p95 118 ms, not the shipped path (the image builds the C++ kernels). The VM re-run of [`VM_GUIDE.md`](../VM_GUIDE.md) §4.0 (C7) repeats the bench as a confirmation; an 8-core run is not required. Confirmed 25.09 afternoon (second VM, 4 physical cores, `76bf24e`, [`evidence/bench_2026-09-25_2/`](../evidence/bench_2026-09-25_2), EXPERIMENTS §3a): `dry_obstacle_native` PASS (9.8 fps, p95 73 ms), `dry_clear_native` PASS, both console tests PASS; numpy 8.3 fps, p95 119 ms (FAIL, not the shipped path) |
| C9 | README per §5 (description, build, run, bag processing, parameters) | DONE | [`../README.md`](../../README.md), restructured 28.09 for the jury (judge A): what it is, the jury commands (step 1 `docker load` of the image archive), what to look at, current results labelled real / synthetic and in-sample / held out, how a bag is processed, build / run, node and config parameters, the documentation table; dated history moved to [`CHANGELOG.md`](../../CHANGELOG.md) "Dated status notes"; before: verified 25.09 against `79109f5` |
| C10 | architecture and algorithm descriptions (§5) | DONE | [`ARCHITECTURE.md`](../ARCHITECTURE.md) ("Native kernels", "GPU: evaluated, not used", "Deployment without internet" with the `offline-build` playback and "Release"), [`ALGORITHM.md`](../ALGORITHM.md) (§3.3: the long overhead rule on, short signatures tried and not shipped) |
| C11 | evaluation protocol (stream C) | DONE | [`EVALUATION.md`](../EVALUATION.md), sets S / E / R / O / F / H; §3 step 6 is the regression gate (`scripts/regression_gate.py`), its baseline with the ride and set F straight since 25.09 |
| C12 | submission package (§7.2): handled by the captain personally (links sent by the captain; SUBMISSION.md removed 25.09) | HANDLED | decided 25.09: the captain sends the submission himself with all its links; `docs/SUBMISSION.md` was removed the same day (its last text, with the deliverables table, the cover message draft and the upload checks: `git show 1945c04:docs/SUBMISSION.md`). What stays current in the repository instead: the jury commands (README "Кратко для жюри"), the documentation table of spec §5 / §7 (README "Documentation required by the organizers"), the dry-run procedure (README "Acceptance test and CI", `scripts/dry_run.sh`, [`VM_GUIDE.md`](../VM_GUIDE.md)) and the offline delivery ([`ARCHITECTURE.md`](../ARCHITECTURE.md) "Deployment without internet"). Nothing left for the agents |
| C13 | release tag and upload package (§7.2) | SCHEDULED: `v1.0.0` on 28.09 21:00 Moscow time, not yet published (§5); DEFERRED from 25.09 to 28.09 | 25.09–27.09: no tag or release was planned (the captain: the system was still in development; §5). The release pipeline exists and is proven only up to CI; it has never run (0 tags): version 1.0.0 in `pyproject.toml`, `resense/__init__.py`, `package.xml` and `setup.py` (`tests/test_release.py` keeps them equal); `.github/workflows/release.yml`: a pushed `v1.0.0-rcN` / `v1.0.0` tag (any other name publishes nothing) would get its tests run, the runtime archive built (gzip -6), the image removed and loaded back, both smoke bags played through the loaded image (internal network and the jury's `--net=host` form), and a GitHub release (a pre-release for `-rc`) with `resense-image-<tag>.tar.gz`, its `.sha256` and `SHA256SUMS`, downloaded again and its sum checked; fallback `scripts/release.sh`, check `scripts/verify_release.sh <tag>`. What is proven: the tooling's logic (`tests/test_release.py`, no Docker) and every Docker step, each a copy of a green `ci.yml` step; the archive itself is built, loaded and played through on every push by CI's `offline-build` (C25). Inert until a tag is pushed. A rehearsal archive without a release (team VM, 25.09, the kit's export step, `7290873`, gzip -6, `--no-cache`, 532 s): 475 489 127 bytes (0.44 GiB; 2 075 079 161 unpacked), sha256 `98be33db23417a88fcb001d0bc7515f151d9e9e41957e163953f63794510ed84`, `load_image.sh` PASS ([`evidence/export_2026-09-25/`](../evidence/export_2026-09-25)); again on the second VM (`76bf24e`, `scripts/export_image.sh` as VM_GUIDE §4.5): `resense-image-1.0.0.tar.gz`, 475 515 293 bytes (2 075 228 485 unpacked), sha256 `262598a56536d898bf78b2e4ab89107c8bcb5f1e89caaceeb6dbd1bacdba7615`, `load_image.sh` PASS ([`evidence/export_2026-09-25_2/`](../evidence/export_2026-09-25_2)) |
| C14 | intermediate submission (§7.1) | DONE (resolved: not held) | decided 25.09: no separate intermediate upload in the organizers' timeline; the §7.1 content (Dockerfile, prototype, description, mini-demo, first experiments) is in the repository ([`organizers/answers.md`](../organizers/answers.md) §4). Evidence: the organizers' timeline ([`organizers/README_organizers.md`](../organizers/README_organizers.md) "Ключевые этапы конкурса") lists only «Приём заявок \| до 14 сентября», «Разработка решений \| 15–29 сентября», «Техническая экспертиза \| 30 сентября – 14 октября», «Презентация проектов \| 23 октября», «Церемония награждения \| 30 октября»; spec §7.1 («7.1. Промежуточная сдача», `technical_specification_case05.txt` lines 184–193) gives the content but no date, form or place; the Q&A of 22.09 does not mention it |
| C15 | liaison: questions sent, answers applied (8.7) | DONE (the captain, 25.09) | answers of 22–24.09 recorded, and the statements of 25.09 from the captain's oral reports: no stand access before the upload (`organizers/answers.md` §6), no internet on the test machine (§7), the upload form takes links with no size limit and **Q3 answered: the 30 × 30 × 10 cm object on the bed between the rails is not an obstacle** (§8; QUESTIONS "Answered"). Q1–Q2 (24.09, edge reference and #8): **sent by the captain (25.09)**; their answers go to `organizers/answers.md` when they arrive |
| C16 | main green, every PR reviewed, captain merges | DONE (the captain, 25.09) · merge open | **26.09 evening (re-judgement):** `main` is at `6962519` (the revert of PR #14, 25.09), 233 commits behind the branch; [pmixay/ReSense#12](https://github.com/pmixay/ReSense/pull/12) is open, mergeable (`clean`) and green on every push (run 36248096431 on `be5f5fc`, then this pass's push); merging it, or naming the branch commit in the upload, is the captain's. Before: `main` was green at `5de0844` (PR #11, run 36104815305). The branch → `main` PR [pmixay/ReSense#12](https://github.com/pmixay/ReSense/pull/12) counts as reviewed (the captain, 25.09): the code review of 25.09 (14 findings: 5 fixed by the captain's order — long-rule bottom `0bb1ba3`, gate missing metrics `1fc127f`, VM kit to instructions `f9498a3`, sha256 case `163f34b`, IPv6 probes `ade8a97` — the dashboard keyboard regression left to P2 in a PR comment, the rest minor) and CI green on every push (last run 36136831743 on `1eddfea`, all six jobs), mergeable; the captain merges it when he chooses. P2, P3 and P4 will not review it: the lane-owner review is lifted (the captain, 25.09); the code review stands, and the dashboard regression it found is fixed by an agent on the captain's order. Branch protection dropped by the captain (not needed, §6). History: PR #11 was merged by its author 3.5 min after opening with 0 reviews; PR #13 (the VM evidence) by its author |
| C17 | one parameter source, lint, tests in CI (8.5) | DONE | **26.09 evening (re-judgement, measured):** 587 tests in `tests/` (585 passed + 1 deselected without the ride cache on the host, 0 skipped; the ride test passed once the ride was cached; +1 this pass: the video's ride card against the gate baseline), 13 in `web/demo` + `check_dashboard.py` PASS in headless Chromium, `ruff` clean, parameter files in sync. Before: 396 tests in `tests/` (green on the native and numpy paths) + 11 in `web/demo`; CI green on every push of PR #12 (run 36133233507 on `afa5ae1`: `pytest` with "no test may have been skipped", `web`, `lint` (ruff 0.15.8), `params-in-sync`, `docker` (the tests in the image, which has no `docs/`), `offline-build` (a gate since 25.09: the runtime archive loaded, rebuilt offline from its cache, both synthetic bags played through the loaded runtime image on an internal network)) |
| C18 | demo chain on screen (§4) | DONE | `video/docker_chain_rviz.mp4` (69 s), `scripts/run_demo.sh` |
| C19 | live remote demo (§4) | PARTIAL · HUMAN | runbook in README (RViz screen share, Foxglove on port 8765); **the live protocol is checked** (P2, PR #16, `674325a`): `web/demo/check_foxglove_live.py` against a live `foxglove_bridge` with `roundT_doubleT` on 25.09, all 11 layout topics advertised, messages on decision, status, corridor points and markers. Left, human: the visual import of the layout in Foxglove and a rehearsal from a second laptop (with the deployment; action 15) |
| C20 | video of the algorithm (§5, §7.2) | DONE | **Rebuilt 26.09 evening** (re-judgement pass, P2's lane): the ride card «46 за 13 км» → «45» (now tested against the newest gate baseline, `tests/test_overview_video.py`), the subtitles say that 3,5 на км is in-sample and 148 m our synthetic, the deck pages it cuts in come from the rebuilt PDF; 2:50, 20.6 MB. Before: `video/resense_overview.mp4` (25.09, `798a28f`; closing card «релиз v1.0.0», `5a15c7c`): 2:50, 1920×1080 H.264, 20.6 MB, no audio track; the script's seven blocks and shot list, Russian subtitles burned in (≤ 2 lines) and as `video/resense_overview.ru.srt` with the same timings, every number marked as in the deck; built by `scripts/make_overview_video.py`; 5 source clips, all silent. Later, with the presentation (team, the captain 25.09): the optional voice-over, muxed on without re-encoding, and a rebuild (action 13): its ride card (3,6 на км, 47 за 13 км) predates the 25.09 rule decision (now 46, 3.5 per km), and its closing card names «релиз v1.0.0», which is deferred (C13) |
| C21 | pitch: team slides 2–4, captain slides, rehearsal (8.8) | LATER (team) · public deck done | **26.09 evening:** the public deck and PDF rebuilt on `_ride_p3d` (the box at the envelope top 51 of 124, continuous from 101 m; the edge objects «лишь 2 и 6 кадров» on every slide and note instead of «пропущен»; 587 tests), checked by `web/demo/test_web.py` against the newest baseline; left: only the human items (1) the private deck, (3) the rehearsals, (4) the optional voice-over below. Before: the presentation is made by the team with the captain. **P2, PR #16 (`674325a`, 26.09):** `scripts/build_deck.py --team` refuses a private build with a missing name, nick or photo and checks that no `<…>` is left; `docs/presentation/team.example.json`; the rehearsal scenario in PRESENTATION «Репетиции питча»; a new-UI clip `video/dashboard_current.mp4` (11.7 s, the real `doubleT_obstacle` replay, STOP near 55.5 m). **Left at that update:** (1) the private deck and slide-2 data (formed, study, city; action 8); (2) the deck and video numbers after the detector freeze (action 13); (3) two in-person rehearsals; (4) optional voice-over. **Updated on the P1/P2 follow-through:** the user supplied four individual portraits and names/nicks/school; the local private preview is built, with city/team-formation details and the group-photo slot pending. |
| C22 | decision: train speed | DONE (measured 24.09) | organizers' fact: no odometry in the recordings, some trains have none (Q&A fact 6). Team decision: ship the no-speed path; a given speed is honoured; the LiDAR-only estimator is accurate (median error 0.06–0.08 m/s) but buys nothing on the organizers' check, so it stays opt-in (EXPERIMENTS §9) |
| C23 | decision: GPU / stand software | DONE (evaluated 24.09) | CPU-only, the image installs no CUDA ([`organizers/test_stand_software.md`](../organizers/test_stand_software.md)); GPU evaluated and not used ([`ARCHITECTURE.md`](../ARCHITECTURE.md) "GPU: evaluated, not used"); of the CPU savings that study found, the cKDTree DBSCAN shipped 25.09, the forward crop did not (no gain on the native path) |
| C24 | captain docs current (CAPTAIN, PLAN) | DONE | **refreshed 26.09 evening** with the re-judgement (SCORECARD §0): C7, C16, C17, C20, C21, actions 13, 19–22, §4, §9; before: refreshed 25.09 ~13:30 UTC: the VM run of `ead8502` and its fixes (drops, `column_hold`, CycloneDDS buffers), the review fixes (long-rule bottom, gate, VM guide, sha256, IPv6), C4–C8 / C16 / C17 / C25 rewritten; earlier the same day against `79109f5`, then the captain's decisions of 25.09 (no releases now, the submission his, deployment and the presentation later; `docs/SUBMISSION.md` removed) |
| C25 | runs on the offline stand: the test machine has no internet ([`organizers/answers.md`](../organizers/answers.md) §7, 25.09) | DONE | tooling: `export_image.sh`, `load_image.sh`, `check_no_network.py`, `dry_run.sh` `IMAGE_TAR` / `OFFLINE`, roslib bundled; no network use in the node, launch file, entrypoint or compose (audit). CI on every push: the `docker` job's `docker save` → `docker rmi` → `docker load` keeps the layers, the smoke test passes with `--network none`, node and a uid-1000 player pass on an `--internal` network (tools image); the `offline-build` job (a gate since `abbbc08`, 25.09; the offline rebuild passed on all four runs made with continue-on-error: 36109782167, 36112092652, 36113989932, 36116178404) makes the runtime archive as for the release (521 317 060 bytes, 0.49 GiB at gzip -1, 1.34 GiB unpacked, base image included, run 36123184213), removes every image and loads it, (1) rebuilds it with `docker build --cache-from` with Docker Hub blocked, all 18 steps from the cache, and (2) plays both synthetic bags through **the runtime image as loaded from the archive** (checked: the built layers, its version and commit labels, no open3d / rosbags, rosbag2 with sqlite3) on an `--internal` network: node on the default command, a uid-1000 player of the same image, `check_dry_run.py --expect-obstacle --expect-inputs 2`. Green on `5a15c7c` (run 36122640174, the first) and on `79109f5` (run 36123184213: 78 status messages, 42 alarm frames at 44.9–59.9 m, both recordings, PASS). Upload: the form takes links, no size limit (action 1b); the submission is the captain's (C12). **Rehearsed 25.09 on a team VM** (the kit's offline step, [`evidence/offline_2026-09-25/`](../evidence/offline_2026-09-25), EXPERIMENTS §3b): outbound traffic blocked, every image deleted, a rehearsal archive (C13) loaded in 29 s and the original bags played through the runtime image: the README jury commands from the host console PASS (134 `STOP`, 55.7–56.5 m); `OFFLINE=1 dry_run.sh` failed the same two criteria as online (drops after 5 s, 3 alarm frames on `roundT_doubleT`), both fixed since (C7); only the kit's own probes were blocked; `check_no_network.py` probes IPv6 too since `ade8a97`. The offline re-run with the fixes (25.09 afternoon, second VM, VM_GUIDE §5 with no host allowed out, [`evidence/offline_2026-09-25_2/`](../evidence/offline_2026-09-25_2)): the block checked on IPv4 and IPv6, a new SSH login worked during it, every `resense` image deleted, the archive of `export_2026-09-25_2` loaded; `IMAGE_TAR=… OFFLINE=1 dry_run.sh` PASS on both bags (the §4.1 criteria); the README jury console from the host FAIL (6 of 201 clouds: the host buffer finding of C4); restored after 4 min. Left, tracked elsewhere: the releases, deferred (C13). Cosmetic: `load_image.sh` prints the Ubuntu base's version label ('22.04') for an image exported with `SKIP_BUILD=1`. Offline rehearsal on the VM: [`VM_GUIDE.md`](../VM_GUIDE.md) §5 |

21 DONE + 1 HANDLED = 22 of 25 done · 1 PARTIAL (C19) · 0 NOT DONE · 1 DEFERRED (C13) · 1 LATER
(C21) · 0 UNKNOWN. Open: the remote-demo rehearsal (C19, with the deployment); deferred by the
captain: the releases (C13, later); later, by the team: the pitch (C21). The captain's decisions of
~16:00 UTC closed C4 (jury step 0), C15 (Q1–Q2 sent), actions 1, 2 and 3b.

**Progress 25.09:** criteria done 22 of 25 (board of 24.09: 13 of 24; the independent check at
08:05 UTC: 12 of 25; this board at 08:35 UTC: 16). New since 08:35: C12 and C14 (the organizers'
answers of 25.09), C20 (the captioned overview video), C25 (the runtime image played from the
archive in CI); C13 NOT DONE → PARTIAL (version 1.0.0 and the release workflow). Then the
captain's decisions of 25.09: C12 DONE → HANDLED (the submission is his), C13 PARTIAL → DEFERRED
(no releases now), C21 PARTIAL → LATER (the presentation). Actions: done 9 of 21 (1b, 4, 5, 6, 9,
10, 10b, 11, 12; at 08:35 UTC: 7; at 08:05 UTC: 1 of 20); deferred or handled by the captain 3
(14, 14b, 16); later, with the deployment or the presentation, 5 (7, 8, 13 for the deck and the
video, 15, 17); open now 4, all human (1, 2, 3, 3b). **Since 10:30 UTC** (the VM run and the
code review): C7 and C8 NOT DONE → PARTIAL (run on the VM with the original bags; every failure
root-caused and fixed, a confirmation re-run left); C4, C5, C6, C25 keep DONE with the VM's
evidence; no criterion is left for the agents. **Then the captain's decisions of ~13:40 UTC:** C16
PARTIAL → DONE (PR #12 counts as reviewed by the code review of 25.09 and green CI; branch
protection dropped), C8 PARTIAL → DONE (the 4-core run is enough: the stand has twice the cores);
action 3b done (the merge click is the captain's), action 1 without branch protection.

## 3. Next actions to 29.09

| # | date | action | owner (H = human captain only; A = agent, captain merges) | priority |
|---|---|---|---|---|
| 1 | 24.09 | ~~read the upload form, settle the intermediate stage~~ done 25.09 (1b, C14); ~~branch protection on `main`~~ dropped by the captain (25.09: not needed); ~~announce the §6 merge rules~~ done (the captain, 25.09: the team was told) | H | done |
| 1b | 25.09 | ~~upload form limit~~ done 25.09 (organizers, [`organizers/answers.md`](../organizers/answers.md) §8): the form takes **links**, **no size limit**; the submission and its links are the captain's own (25.09, C12) | H | done |
| 2 | 24.09 | ~~Q3 (bed object)~~ answered 25.09: not an obstacle ([`organizers/answers.md`](../organizers/answers.md) §8, QUESTIONS "Answered"); ~~send Q1–Q2~~ **sent by the captain (25.09)**; file the answers in `organizers/answers.md` when they come | H | done (answers pending) |
| 3 | 25.09 12:00 | ~~frame caches and harness to P3 / P4~~ not needed (the captain, 25.09: the captain and the agents hold the caches and run the gate themselves); the ride was streamed on the dev VM (split by split as in [`VM_GUIDE.md`](../VM_GUIDE.md) §2.3, 221 of 221 split files) and on both team VMs | P1 | done |
| 3b | 25.09 | ~~prove the Docker build with the C++ kernels~~ done (CI since run 36058665640). ~~the branch → `main` PR, reviewed~~ done 25.09: [pmixay/ReSense#12](https://github.com/pmixay/ReSense/pull/12), reviewed by the code review of 25.09 and CI green on every push (the captain: counts as the review, C16); the merge is not a blocker (the captain, 25.09: merging it to `main` completes it), no tag after it (releases deferred, C13) | A opens, H merges | done |
| 4 | 25.09 12:00 | ~~stop the verification loop~~ done 25.09: numbers live in EXPERIMENTS "Current results" + raw JSON; re-measuring is one command, `scripts/regression_gate.py` (baseline `docs/evidence/results/regression_baseline_2026-09-25_ride.json` since the rules decision), run only when `resense/`, `configs/` or the node change | P1 (A) | must |
| 5 | 25.09 | ~~CI step with a stock-Fast-DDS player~~ done 25.09 (`fbef12b`), green on every run since 36112092652 | A | should |
| 6 | 25.09 18:00 | ~~regression gate: one command, one JSON~~ done 25.09 (A for P4): `scripts/regression_gate.py`, `tests/test_regression_gate.py`; the baseline with the ride and set F straight done on the dev VM (25.09, `regression_baseline_2026-09-25_ride.json`, 394 s at `--jobs 3`); the 8-core run is timing only (action 7). The rule stays: the gate on every P3 PR within 2 h | P4 | must |
| 7 | later (deployment) | 8-core bench (stands in for the i7 stand): kit done (`8242c3e`, A); a first run on a 4-core team VM on 25.09 (EXPERIMENTS §3a, [`evidence/bench_2026-09-25/`](../evidence/bench_2026-09-25)): native p95 70 ms, its drops explained and the checker fixed (C7, C8); **C8 closed on this 4-core run** (the captain, 25.09: no 8-core run needed); the re-run with the deployment repeats it as a confirmation ([`VM_GUIDE.md`](../VM_GUIDE.md) §4.0): a person or an agent on the VM, `scripts/bench_8core.sh <bags>/doubleT_obstacle <bags>/roundT_doubleT` (~10–25 min; [`VM_GUIDE.md`](../VM_GUIDE.md) §4.3); commit `docs/evidence/bench_<date>/` as written; `summary.txt` numbers into EXPERIMENTS §3. Confirmation run 25.09 afternoon: [`evidence/bench_2026-09-25_2/`](../evidence/bench_2026-09-25_2) (EXPERIMENTS §3a) | H (VM agent) | should, when deploying |
| 8 | later (presentation) | The four portraits and supplied names/nicks/school are present in this checkout’s ignored private folder, and a 16-slide private preview has been built. City and team formation remain pending and the group-photo slot is empty. When those details arrive, update the private JSON, rebuild with `--team`, and let the captain share the final deck privately (C12) | H + all, P2 builds | must, before the pitch |
| 9 | 26.09 | ~~narrated 2–3 min video~~ done 25.09: the captioned 2:50 `docs/video/resense_overview.mp4` + `resense_overview.ru.srt` (`scripts/make_overview_video.py`, `798a28f`, `5a15c7c`); the optional voice-over (read against the .srt and muxed on, PRESENTATION «Сборка ролика») comes later with the presentation (team); the new-UI dashboard clip is done (`video/dashboard_current.mp4`, P2, PR #16) | H voice (optional) | could |
| 10 | 26.09 | ~~deck refresh and rebuild~~ done 25.09 (`16d2a07`): pptx and pdf, 16 slides (its counts: action 13) | P2 (A) | should |
| 10b | 25.09 | ~~the `web` CI job red at `8932f3a`~~ done 25.09: the expected slide count follows the deck (16); P2 informed by this row | A | must |
| 11 | 26.09 20:00 | ~~go / no-go on late changes~~ done 25.09 (A, delegated): the ride streamed on the dev VM (11 271 frames); criteria pre-registered; long overhead rule GO and shipped (`935eecf`: ride 47 → 46 events, five bags 20 → 14, set O / set F unchanged); short signatures NO-GO (ride STOP episodes +6 > +5); new baseline `regression_baseline_2026-09-25_ride.json`; EXPERIMENTS §1f. Reproduced on a second machine (team VM, 25.09, [`evidence/gate_2026-09-25/`](../evidence/gate_2026-09-25)): the four runs of `rules_decision_2026-09-25.json` value for value; also `lowobj.near_enabled: true` with the ride: 2 416 / 528 / 294, FAIL 21 rows (stays off) | H decides, P3 / P4 measure | done |
| 12 | 26.09 | ~~decide on the saved-image release asset~~ decided 25.09: the image archive is a must, not insurance (no internet on the stand, C25, ARCHITECTURE "Deployment without internet") | H | done |
| 13 | 26.09 | ~~public consistency pass and artifacts against the gate baseline~~ done 26.09 evening on `_ride_p3d` (re-judgement pass): deck, PDF, 2:50 video and `.srt` rebuilt (the box at the envelope top 51 of 124, the edge objects «лишь 2 и 6 кадров» everywhere, ride 45, 587 tests); tests now tie the deck and the video's ride card to the newest baseline, so a new baseline without a rebuild fails CI. Private team-deck data stay with the team (action 8) | P2 (A) | done |
| 14 | — | ~~tag `v1.0.0-rc1` by 27.09~~ **deferred by the captain (25.09): the system is still in development; deployment later.** No tag is pushed and none is planned now. Version 1.0.0 stays (`65a5305`); `.github/workflows/release.yml` and the release scripts stay, inert until a tag is pushed (C13, §5) | H | deferred |
| 14b | — | ~~check the rc1 release~~ **deferred by the captain (25.09)** with action 14; the image archive for the later deployment can be made without a release (`scripts/export_image.sh`, [`VM_GUIDE.md`](../VM_GUIDE.md) §4.5) | H (+ VM agent) | deferred |
| 15 | later (deployment) | **offline** dry run with the original bags on the 8-core stand-in (the stand is not available), network disconnected: **belongs to the later deployment** (the captain, 25.09). An archive of `scripts/export_image.sh`, `IMAGE_TAR=… OFFLINE=1 ./scripts/dry_run.sh` on both bags, then the README jury commands by hand from a normal user's host console (stock ROS 2 if installed), logs to `docs/evidence/dry_run_<date>/`; remote demo from a second laptop; procedure: README "Acceptance test and CI"; on the VM: [`VM_GUIDE.md`](../VM_GUIDE.md) §4.1 (dry run), §4.2 (host console), §5 (offline rehearsal). Rehearsed 25.09 on a 4-core team VM (EXPERIMENTS §3b: the jury console PASS offline; `dry_run.sh` FAIL on drops and on 3 alarm frames of `roundT_doubleT`, both fixed the same day: C7); the confirmation re-run of [`VM_GUIDE.md`](../VM_GUIDE.md) §4.0 ran 25.09 afternoon (EXPERIMENTS §3b): the dry runs PASS online and offline; the host Fast DDS console FAIL at the default `rmem_max` (C4) | H (VM agent) | must, when deploying |
| 16 | 29.09 | ~~final tag `v1.0.0` on `main`, release~~ **deferred by the captain (25.09)**; the upload with all its links is **handled by the captain personally** (C12) | H | handled by the captain |
| 17 | 30.09–23.10 | answer the organizers daily during the expertise; pitch on 23.10 after two rehearsals (fallback demo `video/docker_chain_rviz.mp4`); the presentation is made later by the team (C21) | H (+P2) | must |
| 18 | 26.09 20:00 | **detector / config freeze** (§6): the P3 work of 25–26.09 is merged (`f46a669` round 1, `8de3a92` round 2, `208152d` the items of 26.09, `wf15/range` the range item of 8.2 (the STOP keep B10 with the 10 s cap), each after a safety review; gate PASS, baseline `regression_baseline_2026-09-26_ride_p3d.json`); the captain declares the freeze, after it only blocker fixes touch `resense/` or `configs/` | H | must |
| 19 | 27.09 20:00 | ~~consistency pass after `_ride_p3d`~~ done 26.09 evening (re-judgement): the claims two independent judges found wrong or stale are fixed (SCORECARD §0.4: README DDS step, DECISIONS rows 15 and 17, ALGORITHM §3.5 rules of 26.09 and set O limits, ARCHITECTURE test count, PRESENTATION, CHANGELOG, the deck and the video); **the docs freeze is the captain's to declare** | A; H for freeze | done; freeze pending |
| 20 | 28.09 | ~~deck, PDF and video rebuilt~~ done (action 13); left for the captain: the final image archive from the frozen commit (the CI artifact `resense-image-1.0.0-<sha>` of its `ci` run, with its `.sha256`; or `scripts/export_image.sh`), a public link to it that opens logged out (a CI artifact needs a GitHub login), and the exact final tested commit named in the upload (PR #12 merged on 27.09) | H | must, before the upload |
| 21 | before the freeze or after it as a blocker | **Startup-only backlog correction: both original bags pass cold with read-ahead 10.** Run 362814 on commit `43b6793` reports obstacle `doubleT_obstacle`: 201 statuses, STOP +1.1 s at 55.5–56.6 m, p95 78 ms, freshness PASS, 0 of 113 post-catch-up source messages unprocessed; the four source-recording gaps are excluded. Clear `roundT_doubleT`: 252 statuses, zero alarms, p95 48 ms, freshness PASS, 0 of 201 post-settle source messages unprocessed. The first STOP is fail-safe while the source is stale; current results follow startup catch-up. Default read-ahead 1000 still produces stale output; action 21 is DONE for the adopted ten-message playback procedure, which does not support an unbounded overdue burst. Earlier 85/201 and 91/201 failures plus the read-ahead-1 cancellation remain in the evidence history. | A; original-bag cold CI complete, procedure adopted | done for the supported procedure |
| 22 | 27.09 | **settle the envelope-edge reference** with the organizers (Q1 of [`QUESTIONS.md`](../QUESTIONS.md), sent 25.09, no answer yet): their objects are placed from the sensor axis (−0.24° to the rails), ReSense measures from the rails, so the two edge objects STOP only at 5–10 m and the outside box gets 6 false STOP frames from 142 m; without an answer, the limitation stays stated (README, ALGORITHM §6) | H | should |
| 23 | 26.09 evening | **P3 / P4 completion pass** (the captain: complete all P3 and P4 work; EXPERIMENTS §1p): every cache rebuilt on another fresh machine, the strict gate with the ride and set F PASS with every row the same; P4's candidate B (`tracking.near_escalate_voxels` 8) passes the full gate and every acceptance check, changing only set O #4 (2 → 3 STOP frames, first STOP 7.1 m): **eligible, not shipped; the captain decides at the freeze** (ship = the config in three places + the baseline re-cut from the B gate run, no headline number moves); the union with the review fixes passes the full gate (#4 2 → 9) and stays off pending Q1 (action 22); +3° pitch measured per event, no candidate; the census on the head: no STOP within 10 m | H decides; A did the runs | should |

## 4. Current completion and remaining actions

**28.09:** the 27.09 detector is sealed ([`DETECTOR_FREEZE.md`](../DETECTOR_FREEZE.md)) and stays
frozen; since then only the node, the image and the documents changed. The `v1.0.0` release is scheduled for 28.09 21:00 Moscow time and is not yet
published (§5). The paragraph below is the dated state of 26.09.

(26.09) The [P3d baseline seal](../DETECTOR_FREEZE.md) and candidate-B decision are complete. The seal
records unchanged detector behavior and a fresh full gate; **final quality acceptance remains
on hold**. The completed quality cycle accepted the freshness controls but no replacement
detector. Its combined M2/node image fails the standalone clear-bag zero-alarm criterion.
Earlier startup and cold/warm measurements remain in their dated evidence packets; they do
not replace this later failure or establish acceptance of the current root image.

- [x] 28.09: the freshness default decided: the image's default command runs the node with
  `freshness_mode:=replay` for recorded bags (`d359a06`); the node's own default stays `live`
  (DECISIONS row 25).
- [x] 28.09: the detector stays frozen; the GO at `doubleT_obstacle` frame 111 is documented as a
  limitation ([ARCHITECTURE «Known limitations»](../ARCHITECTURE.md#limitations-of-the-sealed-2709-detector-verified-2809)),
  not fixed; the sealed detector's per-frame outputs of judge A are added
  ([evidence](../evidence/judge_outputs_2026-09-28/README.md)).
- [x] Preserve the baseline seal and fresh strict gate: all 146 enforced metrics in 199 comparison rows pass.
- [x] Complete P4's 72-case experiment, all 45 false-target traces, missed-object diagnosis,
  exact clear-failure attribution and independent re-judgement. M1, A1, D1 and T1 are rejected;
  M2 passes offline checks but remains unaccepted and unmerged after the combined runtime failure.
- [x] Implement and test node/dashboard freshness, startup handling and original-header message grading.
  The P1/P2 cadence correction also passes all 47 node tests; its original-bag cold replay is an
  open acceptance item below.
- [x] Refresh the public deck/PDF/video against their dated P3d evidence; correct health banners
  and monitored-range wording. Private team content and human rehearsals remain below.
- [x] Exact code revision `d480b1330491da838d6fb4996e34e37b3c060915`: all six jobs pass in
  [CI run 36275557220](https://github.com/pmixay/ReSense/actions/runs/36275557220), including
  loaded runtime native-kernel assertions and synthetic replay with required freshness.
- [x] P1/P2 local checks: 667 passed, one `new_data` cache test deselected, 6 subtests; all 16
  Chromium tests and the 60-frame dashboard smoke check pass. Run 362745's two-container viewer
  outage/recovery test passed. Its cold-bag check failed before the cadence correction: 85/201
  frames processed and 84 messages remained after +5 s ([retained evidence](../evidence/p1_p2_completion_2026-09-26/cold_bag_failed_run_36274548282)).
- [x] Run both original bags cold on the current source with read-ahead 10. Run 362814 passed the
  obstacle and clear criteria; preserved outputs are in
  [`evidence/p1_p2_completion_2026-09-26/cold_bags_passed_run_36281462241/`](../evidence/p1_p2_completion_2026-09-26/cold_bags_passed_run_36281462241).
- [x] Adopt ten-message read-ahead as the supported operating procedure in the jury command,
  dry run, and demos. The [archive-cache run](../evidence/p1_p2_supported_playback_2026-09-27/README.md)
  passed six CI jobs and the [verified-bag cache run](../evidence/p1_p2_supported_playback_2026-09-27/cached_bags_run_36319767736/README.md)
  passed seven, each with both original cold bags; the ROS 2 default 1,000-message burst remains
  unsupported.
- [ ] Import the Foxglove layout and rehearse from a physical second viewing device; CI only
  simulates the separate viewer in a second container.
- [x] Download that CI runtime archive and verify checksum, offline loading, imported source
  hashes and enabled native kernels. The older local `latest` image is restored. This is a
  current-source review artifact; [verification receipts](../evidence/results/quality_delivery_2026-09-26/README.md)
  do not establish final detector acceptance.
- [ ] Close the remaining detector quality gates, including the clear-bag failure, sustained
  detection, false alarms and monitored-range overclaims; independently judge any accepted
  improvement.
- [ ] Release `v1.0.0` with the image archive: **scheduled for 28.09 21:00 Moscow time, not yet
  published**; then verify the public download logged out. A CI artifact requires GitHub login
  and does not complete this item.
- [x] PR #12 was merged into `main` on 27.09. Name the final tested commit in the upload.
- [ ] Obtain Q1/Q2 answers. Q1 is still unanswered; the envelope union shipped on 27.09
  (`gauge.reference` 3) takes its gains from the organizers' sensor-axis placement frame. No
  organizer answer is inferred from results on the tuning set.
- [ ] Finish the private deck after replacing the pending city and team-formation details; add a
  group photo if available. A 16-slide private preview with the four supplied portraits already
  exists in this checkout's ignored `docs/presentation/private/` folder and is not committed.
- [ ] The captain submits the repository, image/checksum, video and deck by 29.09 23:59 (target 18:00).
- [ ] People conduct two pitch rehearsals, the live remote demo and any voice-over; answer the
  organizers during the expertise 30.09–14.10. Documentation does not substitute for these actions.


## 5. Release and submission

**28.09:** the `v1.0.0` release is scheduled for 28.09 21:00 Moscow time; it is **not yet
published** at this writing. It follows `.github/workflows/release.yml` (C13). The rest of this
section is the dated record of 26.09–28.09, when no release was to be published.

(26.09) The user's instruction on 26.09 was **do not publish a release**. This supersedes the
release preparation earlier in the night. No release tag was created or pushed. CI artifacts
remain validation outputs. The prepared release workflow and native-runtime guard are retained
for later use, but publication requires the user's new authorization.

The sealed P3d version remains a reproducible baseline. Its known detection failures and lack of
untouched real-obstacle data prevent calling every criterion complete. The user confirmed no
additional untouched recording is available. Further detector work should use a preregistered
candidate and acceptance checks; replacing the seal requires a new complete gate and review.

The captain's personal submission remains separate: it requires the organizer upload portal,
all final links, approved team details and human confirmation that the form was submitted.

## 10. Why we slowed down (analysis of 24.09) and corrective rules

| # | root cause (ranked by effect on §8) | key numbers |
|---|---|---|
| 1 | P3 had no data, so the detector stopped improving after v0.6.3 (23.09) | 0 detector-output changes on 24.09; two opt-in paths landed off (near-bed 47 → 667 ride events, far-rail unmeasured); that push turned `main` red for 9 h 46 min |
| 2 | a verification loop replaced the improvement loop | 4 scorecards in 28 h; 107 / 20 reproduced 6 times on 24.09; set F straight run 3 times in 30 h; 1 of 28 commits after v0.6.3 moved a §8 metric, ~14 of 34 in the 19 h before |
| 3 | docs too big and duplicated: every change costs N edits | 5 893 md lines against 5 812 lines of product Python; 12:1 markdown to shipped-behaviour lines on 24.09; ~12 commits only propagated numbers |
| 4 | the captain is the bottleneck and works in other lanes | 63 of 77 commits (82 %) since 22.09 from the captain's sessions; P1 items 2–8 days old; 0 GitHub issues |
| 5 | late start, lost sprint | no push 16.09 18:41 → 20.09 20:12; human P2 / P3 / P4 first commits on days 9–10; no range lever replaced accumulation, which is off without a speed input |
| 6 | low-weight polish instead of owned deliverables | ~18 h on 4 dashboard restyles (not in the jury chain); narrated video, new-UI deck, set-O visual open |
| 7 | no merge discipline | 0 reviews; PRs merged 10–31 s after opening; direct pushes; `main` red twice (29.5 h, 9.8 h) and again since `537e220`; a repair by a non-author changed another owner's parameter |
| 8 | external: organizer input every day on 22–24.09 | absorbed correctly, at captain time |

| # | who | corrective action | by |
|---|---|---|---|
| 1 | P1 | stop the verification loop: one results source; no re-measure without a code change; no review until the freeze check (27.09 18:00) | 25.09 12:00 |
| 2 | P1 → P3 | data and harness to P3; no detector PR without their numbers | 25.09 12:00 |
| 3 | P3 | two detector PRs with numbers only: short-signature rule (ride ≤ ~50 events, five bags ≤ 22) and station / platform-end false STOPs (25 of 27 STOP episodes); near-bed and far-rail stay off | 26.09 20:00 |
| 4 | P4 | ~~own the regression gate (one command, one JSON, every P3 PR within 2 h); fix ride-data access with P1~~ lifted (the captain, 25.09: the captain and the agents run the gate on every detector change; the gate itself was built by an agent for P4) | 25.09 18:00 |
| 5 | P2 | freeze the UI; narrated video, new-UI dashboard clip, deck on the `docs/images/` captures, one set-O results visual | 26.09 20:00 |
| 6 | P1 | send Q1–Q2 (Q3 answered 25.09); stock-DDS CI step; photos by 25.09 18:00 and the private deck (later, with the presentation); 8-core timing (later, with the deployment); ~~rc1 tag on 27.09~~ deferred by the captain (25.09) | 25–27.09 |
| 7 | all | freeze-week merge rules (§6); remaining items as GitHub issues with owners | 25.09 morning |
| 8 | P1 | doc diet: one sprint numbering, current results on one screen, history archived, numbers in one place | 25.09 |

State on 25.09 ~10:30 UTC: 1 done (the gate is the single results check, §3 action 4); 2 closed
(not needed: the captain and the agents hold the data and run the gate, 25.09; action 3); 3 done by agents (both rules measured on the ride and decided: the long overhead rule
on, 10 of the 25 station STOP episodes gone; short signatures off; the 82.9 m platform end stays
open); 4 done by an agent for P4 (the gate and its baseline with the ride), P4's gate duty lifted (the captain, 25.09); 5 done by agents except
the new-UI clip (the captioned video, the deck); 6 partly (stock-DDS CI step, bench kit, version
1.0.0 and the release workflow done; confirming Q1–Q2 open; the photos go with the presentation and
the timing run with the deployment, both later; the rc1 tag deferred, 25.09); 7 not done (0 GitHub
issues: §3 is the tracker); 8 done.

