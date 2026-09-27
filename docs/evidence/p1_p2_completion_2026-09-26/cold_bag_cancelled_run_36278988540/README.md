# Cold-bag run cancelled before input — 26 September 2026

GitHub Actions [run 36278988540](https://github.com/pmixay/ReSense/actions/runs/36278988540),
commit `adcd3b874ada88cf5a227f50e33afd6435beea0f`, downloaded the organizer archive and
verified its archive, metadata, and DB3 hashes. The Docker image opened the extracted
`doubleT_obstacle` bag with rosbag2 read-ahead set to one message, but the detector received no
LiDAR frames. Its captured status stream contains 1,380 watchdog snapshots, all `no_input`; the
bag player emitted no progress after opening the database. The run was cancelled after about
12 minutes because it had not reached the acceptance check.

This is an invalid replay setup, not a detector or cold-start result. The raw 4.8 GB database and
downloaded archive were removed by the task's cleanup trap. The next run uses a ten-message
read-ahead queue and a ten-minute CI step timeout. Other jobs in run 36278988540 passed, including
the full Python suite, browser checks, offline build, parameter sync, ROS transport checks, and
the simulated second-device viewer recovery.

The archived [`provenance.txt`](provenance.txt), [`node.log`](node.log), and compressed
[`status.jsonl.gz`](status.jsonl.gz) preserve the attempted setup and its no-input result.
