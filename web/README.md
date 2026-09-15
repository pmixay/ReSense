# ReSense web dashboard (frontend track)

Goal: a browser page that shows, live or from a recorded run, what the jury needs to see —
**tunnel → point cloud → corridor → obstacle → distance** — plus the health of the system.

## Data sources
1. **Live from ROS 2** via `rosbridge_suite` (`ros2 launch rosbridge_server rosbridge_websocket_launch.xml`)
   or via `foxglove_bridge` (already in the Docker image, port 8765):
   - `/resense/status` (`std_msgs/String`, JSON `FrameResult`: obstacle flag, nearest distance,
     detections with distance/lateral/size/confidence/zone, track model, timings) — **1 message per frame, small**
   - `/resense/markers` (`visualization_msgs/MarkerArray`) — boxes + corridor lines
   - `/resense/corridor_points` (`PointCloud2`, only the corridor candidates — a few thousand points)
   - `/lidar_points` (`PointCloud2`, 8 MB/frame — decimate on the server side before streaming to a browser)
2. **Offline** from `resense run --out results.jsonl --render frames/` (JSONL + PNG per frame).

## Minimal scope (Sprint 1)
- `index.html` (this folder): connects to rosbridge, subscribes to `/resense/status`, shows a
  big **PATH CLEAR / OBSTACLE 87 m** banner, a top-down canvas with the corridor and detections,
  a distance timeline (last 30 s), FPS / latency, and an alarm log.
- No build step: plain HTML + JS (roslibjs from CDN); Three.js only if a 3D view is added.

## Later
- Foxglove layout file (`foxglove_layout.json`) with 3D panel + plots — good for remote demos.
- Label tool: click on a frame render to mark obstacle position/size → `gt.json` for `resense eval`.
- Video export of a run (render frames with `resense run --render` → `ffmpeg -r 10 -i frame_%05d.png`).
