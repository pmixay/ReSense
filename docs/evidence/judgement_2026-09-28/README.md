# Independent judgement, 28.09 evening: raw material

> **Purpose:** what the judgement in [`../../SCORECARD.md`](../../SCORECARD.md) ran, on what, with
> which scripts, and the outputs it scored, so every figure there can be recomputed.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN · **Status:** dated record, 2026-09-28

## What was judged and where

* Commit `464f5bc` (`main`; CI run 36424461052 green): the detector sealed on 27.09
  (`scripts/detector_freeze.py verify` PASS, 31 files) and the node of 28.09.
* A 4-vCPU cloud sandbox, 15 GB RAM, Linux 6.18, Docker 29.3, Python 3.11 for the offline runs.
  Nothing else ran during the jury-chain runs; the offline and range runs shared the CPU (no
  timing is taken from them).
* The runtime image from `docker/Dockerfile`, built in 79 s from a clean checkout. The sandbox
  reaches the internet only through a proxy: the build added the proxy's CA, apt over https (ROS
  packages from the OSUOSL mirror of packages.ros.org) and the base image from `mirror.gcr.io`
  (Docker Hub answered 429). The image content is otherwise the Dockerfile's:
  [`scripts/Dockerfile.sandbox.diff`](scripts/Dockerfile.sandbox.diff),
  [`raw/docker_build_excerpt.txt`](raw/docker_build_excerpt.txt) (native kernels compiled).
* Data from the organizers' links: `Датасет.zip` (sha256 `e2316680…68be`, as pinned in
  `scripts/cold_bags.sha256`; both cold bags verified by `scripts/fetch_cold_bags.sh`),
  `cloud_with_fake_obj.zst` (Yandex Disk) and `new_data.zst` (17.08 GB, Yandex Disk, streamed).
  Disk allowed only part of the data at a time, so bags were extracted one or two at a time
  ([`scripts/extract_bags.py`](scripts/extract_bags.py)) and the ride was streamed split by split.

## Runs and outputs

| run | script | output | summary |
|---|---|---|---|
| tests, lint, parameter copy, seal | `pytest`, `ruff`, `scripts/sync_params.sh --check`, `scripts/detector_freeze.py verify` | [`raw/pytest_summary.txt`](raw/pytest_summary.txt) | 753 passed, 1 deselected, 6 subtests |
| jury chain, 11 runs: the node with the image's default command, a player as uid 1000 from the same image, the judge's listener, all `--net=host` | [`scripts/run_chain.sh`](scripts/run_chain.sh), [`scripts/batch1.sh`](scripts/batch1.sh), [`scripts/listener.py`](scripts/listener.py) | [`raw/chain/<run>/`](raw/chain) (listener JSONL, node log) | [`chain_runs.json`](chain_runs.json) by [`scripts/analyze.py`](scripts/analyze.py) with [`raw/bag_stamps.json.gz`](raw/bag_stamps.json.gz) ([`scripts/bag_stamps.py`](scripts/bag_stamps.py)) |
| detector offline on every frame of the six recordings and set O (`resense run --bag`, default config) | `resense run` | [`raw/offline/*.jsonl.gz`](raw/offline) | [`offline_summary.json`](offline_summary.json) by [`scripts/score_bag.py`](scripts/score_bag.py); [`setO.json`](setO.json) by [`scripts/score_setO.py`](scripts/score_setO.py) |
| the 20-minute ride, detector reset at every split (the splits leave the archive in random order) | [`scripts/ride_producer.py`](scripts/ride_producer.py), [`scripts/ride_consumer.py`](scripts/ride_consumer.py) | [`raw/ride.jsonl.gz`](raw/ride.jsonl.gz) | [`ride_summary.json`](ride_summary.json) by [`scripts/score_ride.py`](scripts/score_ride.py) |
| a real person pasted into the other tunnels: 5 recordings × 3 windows × 6 ranges | [`scripts/transplant.py`](scripts/transplant.py), [`scripts/tp_batch.sh`](scripts/tp_batch.sh), [`scripts/transplant_debug.py`](scripts/transplant_debug.py) | [`raw/transplant/*.json`](raw/transplant) | [`transplant.json`](transplant.json) by [`scripts/transplant_summary.py`](scripts/transplant_summary.py) |

Run names in `raw/chain/`: `obst_*` = `doubleT_obstacle`, `clear_*` = `roundT_doubleT`; `warm` = bag in
the page cache, `cold` = caches dropped before the run; `plain*` = the organizers' literal
`ros2 bag play <bag>` (Humble defaults, no `--delay`, no `--read-ahead-queue-size`);
`plain3_nolisten` = the same without the listener's cloud subscription.

## Method notes and limits

* **End-to-end latency** = the listener receives an input cloud (raw bytes, keyed by its header
  stamp) → the listener receives `/resense/status` with the same stamp. Both on the same host and
  clock; the listener's own receive path is the node's (UDP loopback). "Current" = the status's
  `freshness.reason` is `current`.
* **Set O matching:** a STOP detection counts for an object when its distance lies within 3 m of
  the object's box along the track; "inside" = frames whose label row has points inside the
  envelope (`n_in_envelope` > 0) and is plausible. The labels are P4's, extracted from the points the
  organizers appended.
* **Range test:** the person of `doubleT_obstacle` (bag frames 20–49) is cut with its label box in
  the configured vehicle frame, expressed relative to its front, the detector's track axis and rail
  head, and pasted at 60–200 m on the detector's own axis of each target frame, thinned to
  (55.5 / r)² of its points. No occlusion shadow is cut; the person stays at a fixed distance ahead
  (as in `doubleT_obstacle`, where the train stands). Each window: 60 warm-up frames, 30 test frames;
  the control is the same window without the person (0 STOP frames in all 15).
* **Ride:** each 51-frame split is processed after a detector reset (the mount calibration is
  kept), so a STOP needs its confirmation inside the split; this undercounts events that would
  straddle a split boundary and adds a warm-up in each split. The distance per split is not known;
  per-km figures use the recording's 13.0 km.
* Paths in the scripts are the sandbox's (`/home/user/data`, overridable with `DATA`, `RIDE`,
  `OUTDIR`, `LABELS`).
