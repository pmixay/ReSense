Re-judgement of 26.09 (evening): the runs an independent judge made on the head of
claude/nifty-pascal-lzgl78 (be5f5fc, the detector of fa18832, config sha256 d2c8ab8d...) instead
of trusting the documents. Scores and reasons: docs/SCORECARD.md section 0.

Machine: a 4-core cloud sandbox (Intel Xeon @ 2.80 GHz, 4 cores, 1 thread each, 15 GiB RAM,
337 MB/s cold disk reads), Docker 29.3.1, no ROS on the host. Not the i7-9700E stand (8 cores),
not idle during the pytest run (the image build ran beside it).

Data: the organizers' originals, downloaded from their links on 26.09; the metadata.yaml of
doubleT_obstacle and roundT_doubleT equal to docs/evidence/bag_metadata/; the six recordings and
cloud_with_fake_obj cached with scripts/cache_frames.py --every 1 --int16 --stamps (2 488 and
1 510 frames), the ride new_data streamed split by split as docs/VM_GUIDE.md section 2.3.

Image: docker/Dockerfile unchanged, built with WITH_TOOLS=1 (as the CI docker job). Sandbox-only
deviation: the base image ros:humble-ros-base-jammy was pulled from mirror.gcr.io (Docker Hub
answered 429) and given one extra layer with this sandbox's TLS-proxy CA so that pip could reach
PyPI during the build. The node, the launch file and the entrypoint are the repository's.

Files
-----
pytest.txt                      python -m pytest -q -rs with RESENSE_REQUIRE_SYNTHETIC=1 on the host
                                (native path): 585 passed, 1 deselected (needs the ride cache), 0 skipped.
                                The deselected test was run again once the ride was cached (see below).
dry_obstacle*.txt, *_node_log.txt, *_status.jsonl.gz
                                SKIP_BUILD=1 OFFLINE=1 scripts/dry_run.sh <bags>/doubleT_obstacle
                                (node, player and recorder in one container with --network none):
  dry_obstacle                  host net.core.rmem_max 4 MiB, bag freshly unpacked: FAIL (53 status
                                messages, 25 frames not processed after the catch-up; first STOP +13.0 s)
  dry_obstacle_step0            README step 0 applied (rmem_max 32 MiB), page cache state unknown:
                                FAIL (32 status messages)
  dry_obstacle_warm             step 0, the bag in the page cache: PASS (139 status messages, 126 alarm
                                frames at 55.7-56.5 m, p95 81 ms, 9.97 fps, back on the newest frame
                                at +9.5 s, 0 of the recording's frames not processed after it)
  dry_obstacle_cold             step 0, page cache dropped (echo 3 > drop_caches): FAIL (34 status
                                messages, 94 frames not processed, first STOP +15.5 s). The node log
                                shows why: the player delivered its first frame ~29 s after the node
                                started and then the whole overdue recording back to back; the
                                catch-up dropped the frames more than catchup_max_lag (5 s) behind the
                                newest, so consecutive processed frames were 1.0-1.4 s of recording
                                apart and each such gap reset the scene (hole_reset_gap 1 s): no
                                track could be confirmed until the end.
dry_clear*                      the same (warm) on roundT_doubleT with --expect-clear: PASS (0 alarm
                                frames, p95 58 ms, 10.0 fps).
ct_stock*                       PLAYER_DDS=stock scripts/console_test.sh roundT_doubleT doubleT_obstacle
                                (node on the image's default command; a uid-1000 player and listener
                                from other containers with Humble's stock rmw_fastrtps_cpp, shared
                                memory on; --net=host): PASS, both recordings into one running node,
                                STOP at 55.7-56.5 m, the listener heard 128 STOP.
setO_raw_bag.jsonl.gz           resense run --bag cloud_with_fake_obj (the float bag, not the cache).
setO_raw_bag_score.txt          scripts/score_fake_objects.py on it: inside STOP frames 387 of 801
                                (the cache gives 384: 5 mm int16 quantisation), 7 false STOP frames
                                on the outside box #7, 1 background alarm frame.
setO_raw_bag_clear_distance.json scripts/score_clear_distance.py on it: clear_distance past an object
                                inside the envelope in 51 of 505 frames with the object's points in
                                the rail-referenced envelope (44 of them GO), 217 of 801 by the
                                organizers' placement; 154 GO frames with the clear distance past an
                                in-envelope object by the placement.
gate_result.json, gate_run.txt  scripts/regression_gate.py --cache <all caches> --jobs 4 --baseline
                                docs/evidence/results/regression_baseline_2026-09-26_ride_p3d.json
                                (six recordings, set O, the ride in 8 pieces, set F straight; 302 s):
                                GATE PASS, every gated row the same as the baseline; only the
                                informational latency rows differ (4 jobs on 4 cores).
pytest_ride_test.txt            tests/test_rail_start.py with the ride cached: 28 passed (the test the
                                host run deselected included).
bench_native.txt                resense bench --npy <cache> on the idle machine, OMP 1: detector per
                                frame, native path: 360 doubleT_obstacle 30.7 / p95 42.1 ms, 120
                                roundT_doubleT 25.8 / 37.1 ms, set O 22.7 / 32.8 ms; numpy path at
                                360: 78.3 / 95.5 ms.
ros_setO.txt, ros_setO_node_log.txt, ros_setO_status.jsonl.gz
                                set O played through the node: the jury's runtime image (WITH_TOOLS=0,
                                built here from docker/Dockerfile), SKIP_BUILD=1 OFFLINE=1
                                scripts/dry_run.sh <bags>/cloud_with_fake_obj --expect-obstacle
                                --min-frames 100 --max-p95-latency 100 --max-dropped 100000, the bag in
                                the page cache: PASS, 10 fps, p95 52 ms; 1 452 of 1 510 frames processed,
                                all 58 skipped ones in the start-up catch-up (frames 0-22, then every
                                second one up to 80).
setO_header_stamps.jsonl, node_to_frames.py
                                the bag's header stamps per frame index (read with rosbags) and the
                                script that maps the node's status (header stamps) onto frame indices:
                                python node_to_frames.py setO_header_stamps.jsonl <status.jsonl> <out>
ros_setO_score.txt, ros_setO_score.json
                                scripts/score_fake_objects.py on the mapped node output: every object as
                                the offline float-bag run except #1 (in view when the recording starts:
                                153 of its 155 processed frames, first STOP 94.6 m instead of 98.0 m) and
                                the outside box #7 (10 false STOP frames, offline 6-7); 0 background.
