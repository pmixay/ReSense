# RViz

RViz shows the raw cloud, the points inside the envelope corridor, the corridor edges, the obstacle
boxes with their distance and a status text. It runs from the same image; the host needs an X11
display.

## Node with RViz

Instead of the plain node command:

```bash
xhost +local:docker && docker run --rm -it --net=host --ipc=host \
  -e DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix \
  resense ros2 launch resense_ros detector.launch.py rviz:=true freshness_mode:=replay
```

Then play the bag as in [Run on a bag](../getting-started/run-on-a-bag.md).

## Everything in one container

```bash
./scripts/run_demo.sh /data/for_hackathon/roundT_doubleT
```

Node, RViz and the player in one container (`bag:=`, `rviz:=true` of the launch file). The launch
file also takes `loop:=true`, `rate:=<factor>` and `delay:=<s>` for a continuous demo.

## With docker compose

```bash
xhost +local:docker
docker compose --profile viz up                 # detector + RViz + Foxglove bridge
docker compose --profile tools up player        # plays $RESENSE_BAG
```

## What you see

* **Fixed frame `resense_lidar`.** The node broadcasts a static identity transform from
  `resense_lidar` to the frame id of the input cloud, so the same layout works for every bag.
* **Two raw-cloud displays**, `/lidar_points` and `/sensing/lidar/hesai128/pointcloud`; the one the
  bag carries renders, the other stays grey with "No messages received". A bag with a third topic
  name needs one more display (*Add → PointCloud2 →* pick the topic); the node itself finds any
  `PointCloud2` topic, so detections and the corridor show up regardless.
* Colours: raw cloud by height in grey, corridor points orange, envelope obstacles red, advisory
  objects orange, corridor edges green, status text above the track.
* Saved views in the *Views* panel: *Top-down 150 m* and *Driver's seat*.

The layout file is `ros2_ws/src/resense_ros/rviz/resense.rviz`; a host with ROS 2 can open it
directly: `rviz2 -d ros2_ws/src/resense_ros/rviz/resense.rviz`.
