# Requirements

## To run the detector (the jury path)

| what | why |
|---|---|
| Linux x86-64 host with **Docker** | the image is `ros:humble-ros-base-jammy` (Ubuntu 22.04) plus ReSense; nothing else is installed on the host |
| the image: an archive `resense-image-<version>.tar.gz`, or internet to build it | [Get the Docker image](get-the-image.md) |
| a ROS 2 bag (rosbag2, sqlite3 or MCAP storage) with a `sensor_msgs/PointCloud2` topic | [Get the data](../guides/data.md) |
| **CPU only**, one core per node at 10 Hz | no GPU, no CUDA; the image uses single-threaded BLAS on purpose |
| `sudo` once for `sysctl net.core.rmem_max` | the UDP receive buffer for 24 MB 360° clouds when the player uses CycloneDDS ([Troubleshooting](../troubleshooting.md#no-frames-arrive-from-a-360-degree-bag)) |

Optional:

* **ROS 2 Humble on the host** to play the bag and echo topics from a normal console. Without it,
  the player runs from the same image (`scripts/play_bag.sh` does that for you).
* **X11** for RViz on the same machine, or any second laptop with Foxglove for a remote view.
* Memory: the node's peak RSS on a 360° bag is a few hundred MB; the player reads the bag from
  disk, so a warm page cache helps on the very first play of a large bag.

No internet is needed at run time: the node, the launch file and the entrypoint make no network
calls, and the dashboard's JavaScript dependencies are bundled.

## To develop (no ROS needed)

| what | why |
|---|---|
| Python ≥ 3.10 | `pip install -e ".[dev]"` |
| a C++ compiler (optional) | the native kernels in `native/`; without one the numpy path is used, same output |
| `open3d` (in `[dev]`) | synthetic obstacle injection and the tests that ray-cast; tests skip without it |
| the dataset | only for real-data evaluation; unit tests and CI make their own small synthetic bags |

See [Setup, tests and CI](../development/setup-and-ci.md).
