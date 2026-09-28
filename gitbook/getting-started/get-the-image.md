# Get the Docker image

There are three ways, depending on whether the machine has internet.

## 1. Load a prepared archive (no internet needed)

The organizers' test stand has no internet, so the image is delivered as one gzip archive with its
checksum next to it:

```bash
sha256sum -c resense-image-<version>.tar.gz.sha256   # optional: check it
docker load -i resense-image-<version>.tar.gz        # tags resense:<version> and resense:latest
```

`scripts/load_image.sh <archive>` does the checksum, the load and a first start of the image with
`--network none` in one step.

**Where the archive comes from:**

* **CI artifact** — every green push to `main` produces one. On GitHub: *Actions* → the `ci` run of
  the commit (job `offline-build` green) → *Artifacts* → `resense-image-<version>-<commit>` (a zip
  holding the `.tar.gz` and its `.sha256`; kept 30 days; downloading needs a GitHub login).
* **Export it yourself** on any machine with internet and Docker:

  ```bash
  scripts/export_image.sh          # builds from HEAD with --no-cache → dist/resense-image-<version>.tar.gz + .sha256
  ```

  `SKIP_BUILD=1 SOURCE_IMAGE=resense:latest scripts/export_image.sh` saves an image you already
  have instead of building.

* **GitHub release** — once one is published, its *Assets* hold the archive and its `.sha256`;
  `scripts/verify_release.sh <tag>` downloads it into `dist/` and checks it. The README's jury
  section says whether a release is out yet.

## 2. Build it (internet needed)

```bash
docker build -t resense -f docker/Dockerfile .    # or ./scripts/build.sh
```

The build pulls `ros:humble-ros-base-jammy`, installs the ROS packages with apt and exactly pinned
Python packages with pip, and compiles the optional C++ kernels. Useful variants:

```bash
PULL=1 ./scripts/build.sh          # refresh the ros:humble base first (an old cached one fails apt-get update)
WITH_TOOLS=1 ./scripts/build.sh    # + rosbags / matplotlib / open3d / pytest: the image CI tests with
```

## 3. Rebuild offline from a loaded archive (best effort)

After step 1, in a checkout of the same commit, every layer can come from the archive's cache:

```bash
chmod -R u+rwX,go+rX,go-w . && docker build --cache-from resense:<version> -t resense -f docker/Dockerfile .
```

If it fails, the image from step 1 is untouched and works. Details: [Stand without
internet](../guides/offline-stand.md).

## What is inside

The runtime image holds only what the node needs: ROS 2 Humble (`ros-base`), rosbag2 with the
sqlite3 and MCAP plugins, RViz, `foxglove_bridge`, the `resense` package with its pinned numpy /
scipy / scikit-learn / pyyaml, the compiled C++ kernels, and the ROS package `resense_ros`. It does
**not** contain the offline bag reader (`rosbags`), Open3D or the test suite; those come with
`WITH_TOOLS=1`.

Default command: `ros2 launch resense_ros detector.launch.py freshness_mode:=replay`, the node with
topic auto-discovery, set up for recorded bags. On a train with a live LiDAR pass
`freshness_mode:=live` (the node's own default) instead.
