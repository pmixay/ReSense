# FAQ

**Does ReSense need a GPU, a map or the train's speed?**
No. It runs on one CPU core, rebuilds the tunnel model from every frame and works without a speed.
A speed, if given (`ego_speed_mps`, `speed_topic` or `odom_topic`), enables frame accumulation at
range.

**Does it need training data or object classes?**
No. Geometry decides what is inside the envelope. A small learned model only delays a doubtful far
STOP by a bounded amount; it cannot veto one.

**What counts as an obstacle?**
Anything at least 30 × 30 × 10 cm inside the organizers' 2.1 × 3.0 m train envelope, including
things hanging into it such as a broken cable. An object lying on the bed between the rails below
the envelope floor is not an obstacle (the organizers' answer); one on a rail is.

**Which topic and frame does it expect?**
Either of the organizers' pairs (`/lidar_points` in `hesai_lidar`, or
`/sensing/lidar/hesai128/pointcloud` in `lidar_livox`) or any other `PointCloud2` topic it
discovers. The sensor mount is calibrated from the data.

**Can I play several bags without restarting the node?**
Yes. A new topic, frame id or a stamp jump of more than 30 s starts a fresh detector.

**Is `GO` safe to drive on?**
`GO` means no obstacle was detected. It is not an authorization to move a train. Software consumers
should read the freshness fields of `/resense/status` and expire results with their own timer.

**How far does it see?**
The Hesai Pandar128 in these recordings returns nothing beyond about 210 m. Detection range depends
on the object's size and position; the measured figures, real and synthetic, are in
[`docs/EXPERIMENTS.md`](https://github.com/pmixay/ReSense/blob/main/docs/EXPERIMENTS.md) and the
README summary, each with its date and the data it was measured on.

**Can I upload a bag to the website and get results?**
Not today. The hosted dashboard replays results (a `results.jsonl` or a `/resense/status`
capture); it has no server that could run the detector on an uploaded bag. Process the bag locally
(`resense run --bag … --out results.jsonl`, or `scripts/dry_run.sh`) and load the file. See
[Web dashboard](visualisation/web-dashboard.md).

**Is there a public download of the Docker image?**
Not yet: no GitHub release has been published. The archive of every `main` commit is a CI artifact
(GitHub login needed), and `scripts/export_image.sh` makes one on any machine with Docker and
internet.
