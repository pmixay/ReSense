# The ROS 2 node in Docker on real recordings, 23 September

> **Purpose:** the first runs of the organizers' procedure (Docker image, `ros2 bag play`, `/resense/status`) on real
> frames: node logs, status captures and checker output for four runs and the RViz chain.
> **Audience:** team, jury · **Owner:** P1 (runs, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: `checks.txt` read in full; message counts of the four status captures counted with a script;
> the numbers below compared with the table of log §3b; the node logs read ·
> **Status:** dated record, superseded by the VM runs of 25.09 and 28.09 (see section 5)

## 1. What was run, when

* Node log time stamps show 2026-09-23 (UTC): `obstacle_node.log` 10:43, `clear_node.log` 10:46, `ct_smoke_node.log` 11:23,
  `ct_real_node.log` 11:24, `rviz_chain_node.log` 11:51. The git date (`1210580`, 2026-09-23, "v0.6.3 ... (#5)") is a PR merge date;
  it agrees with the run date here.
* Code: the log calls the first three runs the "v0.6.2 image" and the RViz run "image built from the current tree"; the index
  says v0.6.2 and v0.6.3 ([`../README.md`](../README.md) line 151). No SHA is recorded in the folder. Lane: not recorded in the folder or the docs.
* Four checker runs (`checks.txt`): `clear` = `dry_run.sh` on `roundT_doubleT`, `obstacle` = `dry_run.sh` on `doubleT_obstacle`
  (node and player in one container, root); `ct_smoke` = `console_test.sh` on the two synthetic bags; `ct_real` = `console_test.sh`
  on `roundT_doubleT` then `doubleT_obstacle`, player as uid 1000 ([EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3b "Setup").

## 2. Result

* `checks.txt`: `clear` PASS (237 status messages, 2 alarm frames at 128.3-130.2 m, latency mean 65 / p95 76 ms);
  `obstacle` FAIL (103 messages, 88 alarm frames at 56.1-56.2 m, p95 130 ms, 86 dropped input frames);
  `ct_smoke` PASS (72 messages, p95 78 ms); `ct_real` FAIL on one criterion only (351 messages, 131 alarm frames, p95 102 ms,
  "2 of 131 reported distances outside 50..62 m (e.g. 130.2 m)", the two frames of `roundT_doubleT` the log calls known).
* `ct_real_docker_stats.txt`: 14 samples; highest CPU sample 101.60 % of one core, memory 186.5 MiB while busy (102.2 MiB idle).
* `rviz_chain_node.log`: OBSTACLE at 55.7-56.3 m from frame 11 to frame 177, 15 dropped, latency mean 104-122 ms.

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3b: first table (rows 1-5), "Resources of the node container", "With RViz"; it
  cites the folder at its end of the resource paragraph and for `rviz_chain_node.log`.
* [`docs/images/README.md`](../../images/README.md) (cab view on real data) uses `obstacle_status.jsonl.gz`; the presentation manifest hashes it
  ([`presentation_2026-09-26/manifest.json`](../presentation_2026-09-26/manifest.json)).
* The [RViz video](../../video/docker_chain_rviz.mp4) is linked from the index row; its source run is `rviz_chain_node.log`.
* No row of `DECISIONS.md`, `BACKLOG.md`, `SCORECARD.md`, `VM_GUIDE.md` or `CHANGELOG.md` names the folder.

## 4. Contents (11 files)

* `checks.txt`: checker output of the four runs.
* `clear_node.log`, `obstacle_node.log`, `ct_smoke_node.log`, `ct_real_node.log`: node logs (21, 19, 17, 38 lines).
* `clear_status.jsonl.gz` (237 records), `obstacle_status.jsonl.gz` (103), `ct_smoke_status.jsonl.gz` (72), `ct_real_status.jsonl.gz` (351):
  `/resense/status` captures; records are separated by `---` lines, so the line counts are about twice the record counts.
* `ct_real_docker_stats.txt`: `docker stats` samples of the node container during `ct_real`.
* `rviz_chain_node.log`: node log of the run with RViz on a virtual display.

## 5. Caveats

* The bags were rebuilt from the frame cache, not the originals (log §3b "Setup"; the folder does not say so). Point counts in the node
  logs (for example 208324 and 381422) are those of the rebuilt bags. Coordinates carry the cache's 5 mm quantisation.
* The `obstacle` run FAILS its own checker (p95 130 ms, 86 drops); the log reports it as a result with "103-134 of 201" processed,
  not as a PASS. The 24.09 runs of v0.6.4 that the log tabulates are not committed (log: "team record, unverified").
* `ct_smoke`: `checks.txt` says fps 10.01; the log table says 5 fps (bag at 0.5x). Not resolved here.
* The input hole at the start of a played bag (v0.6.3) is visible in `obstacle_node.log` ("4.0 s hole", "2.0 s hole") and
  was fixed in v0.6.4; later runs are in [`dry_run_2026-09-25/`](../dry_run_2026-09-25/result.txt) and [`bench_2026-09-28/`](../bench_2026-09-28/summary.txt).
