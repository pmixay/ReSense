"""ROS 2 node: PointCloud2 in -> obstacle flag, distance, Detection3DArray, RViz markers out.

Topics (defaults, all configurable via parameters):
  sub  /lidar_points, /sensing/lidar/hesai128/pointcloud, or whatever PointCloud2 topic the bag
       carries -- ``input_topic`` is a comma-separated candidate list and, with ``auto_discover``,
       the node also picks up any other PointCloud2 topic that appears on the graph. The
       organizers' bags do not agree on the name (roundT_doubleT publishes /lidar_points,
       doubleT_obstacle /sensing/lidar/hesai128/pointcloud) and the control bag is unseen.
  pub  /resense/obstacle_detected       std_msgs/Bool      (confirmed object inside the gauge)
  pub  /resense/warning                 std_msgs/Bool      (confirmed object in the advisory zone)
  pub  /resense/nearest_distance        std_msgs/Float32   (m along the track, -1 if none)
  pub  /resense/detections              vision_msgs/Detection3DArray (gauge + warning objects)
  pub  /resense/status                  std_msgs/String    (JSON: full FrameResult for dashboards)
  pub  /resense/markers                 visualization_msgs/MarkerArray (boxes, labels, corridor)
  pub  /resense/corridor_points         sensor_msgs/PointCloud2 (points inside the corridor, debug)
  pub  /resense/latency_ms              std_msgs/Float32   (per frame: decode + detect + publish, ms)
  pub  /resense/fps                     std_msgs/Float32   (frames processed per second, every stats_period s)

The status JSON carries an extra ``node`` object next to the detector fields:
``{"latency_ms", "fps", "frames", "dropped_frames", "input_period_ms"}`` (``latency_ms`` there is
decode + detect of the same frame, before publishing). ``dropped_frames``
is estimated from gaps in the input header stamps (the subscription is best-effort with a
short queue, so a slow frame silently drops the ones behind it).
"""
from __future__ import annotations

import json
import time

import numpy as np
import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Bool, Float32, String, Header
from vision_msgs.msg import Detection3D, Detection3DArray, ObjectHypothesisWithPose
from visualization_msgs.msg import Marker, MarkerArray

from resense.config import DetectorConfig
from resense.detector import Detector, FrameResult
from resense.frame import Frame, axis_matrix
from resense.pointcloud import pointcloud2_to_structured, structured_to_compact


class DetectorNode(Node):
    def __init__(self) -> None:
        super().__init__("resense_detector")
        self.declare_parameter("input_topic", "/lidar_points,/sensing/lidar/hesai128/pointcloud")
        self.declare_parameter("auto_discover", True)    # also take PointCloud2 topics found on the graph
        self.declare_parameter("discover_period", 2.0)   # s, how often to look while no frame has arrived
        self.declare_parameter("config_file", "")
        self.declare_parameter("publish_markers", True)
        self.declare_parameter("publish_corridor_cloud", True)
        self.declare_parameter("marker_x_max", 250.0)
        self.declare_parameter("output_frame", "")   # empty = input frame id
        self.declare_parameter("stats_period", 2.0)  # s, between FPS / latency log lines and /resense/fps

        cfg_file = self.get_parameter("config_file").get_parameter_value().string_value
        self.cfg = DetectorConfig.from_yaml(cfg_file) if cfg_file else DetectorConfig()
        self.detector = Detector(self.cfg)
        self.R_vs = axis_matrix(self.cfg.sensor)            # sensor -> vehicle
        self.R_sv = self.R_vs.T                              # vehicle -> sensor (for markers)

        self.qos = QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                              history=QoSHistoryPolicy.KEEP_LAST)
        topic = self.get_parameter("input_topic").get_parameter_value().string_value
        self.subs = {}                 # topic -> Subscription
        self.active_topic = None       # the topic the first frame arrived on; the others are dropped
        for t in (x.strip() for x in topic.split(",")):
            if t:
                self.subscribe(t)
        self.pub_flag = self.create_publisher(Bool, "/resense/obstacle_detected", 10)
        self.pub_warn = self.create_publisher(Bool, "/resense/warning", 10)
        self.pub_dist = self.create_publisher(Float32, "/resense/nearest_distance", 10)
        self.pub_det = self.create_publisher(Detection3DArray, "/resense/detections", 10)
        self.pub_status = self.create_publisher(String, "/resense/status", 10)
        self.pub_markers = self.create_publisher(MarkerArray, "/resense/markers", 10)
        self.pub_corridor = self.create_publisher(PointCloud2, "/resense/corridor_points", 5)
        self.pub_latency = self.create_publisher(Float32, "/resense/latency_ms", 10)
        self.pub_fps = self.create_publisher(Float32, "/resense/fps", 10)

        # --- runtime statistics (spec 8.3: latency, frame rate, real-time stability) ---
        self.n_frames = 0
        self.dropped = 0                      # frames the queue dropped, estimated from stamp gaps
        self.input_period = 0.1               # s, running estimate of the sensor period
        self.last_stamp = None                # header stamp of the previous processed frame
        self.win_latency = []                 # ms, latencies since the last stats line
        self.win_frames = 0
        self.fps = 0.0
        self.last_latency_ms = 0.0
        self.last_status = "clear"
        self.t_stats = time.perf_counter()
        period = self.get_parameter("stats_period").get_parameter_value().double_value
        self.stats_timer = self.create_timer(max(period, 0.1), self.on_stats)
        self.discover_timer = None
        if self.get_parameter("auto_discover").get_parameter_value().bool_value:
            dp = self.get_parameter("discover_period").get_parameter_value().double_value
            self.discover_timer = self.create_timer(max(dp, 0.5), self.on_discover)
        self.get_logger().info("ReSense detector listening on " + ", ".join(self.subs)
                               + (" (+ auto-discovery)" if self.discover_timer else ""))

    # ------------------------------------------------------------------
    def subscribe(self, topic: str) -> None:
        """Subscribe to one more candidate input topic (idempotent)."""
        if topic in self.subs:
            return
        self.subs[topic] = self.create_subscription(
            PointCloud2, topic, lambda msg, t=topic: self.on_cloud(msg, t), self.qos)

    def on_discover(self) -> None:
        """While nothing has arrived, subscribe to every PointCloud2 topic on the graph.

        The organizers' bags disagree on the topic name and the control bag is unseen, so the
        node finds its input instead of requiring the jury to pass the right one. Stops at the
        first frame."""
        if self.active_topic is not None:
            self.discover_timer.cancel()
            return
        for name, types in self.get_topic_names_and_types():
            if ("sensor_msgs/msg/PointCloud2" in types and not name.startswith("/resense/")
                    and name not in self.subs):
                self.get_logger().info("auto-discovered PointCloud2 topic " + name)
                self.subscribe(name)

    # ------------------------------------------------------------------
    def _account_frame(self, stamp: float) -> None:
        """Estimate dropped frames from the gap between consecutive input stamps."""
        if self.last_stamp is not None:
            gap = stamp - self.last_stamp
            if 0.0 < gap < 1.6 * self.input_period:
                # a regular gap: refine the period estimate (EMA)
                self.input_period = 0.9 * self.input_period + 0.1 * gap
            elif gap >= 1.6 * self.input_period:
                self.dropped += int(round(gap / self.input_period)) - 1
            # gap <= 0: a bag loop / restart, not a drop
        self.last_stamp = stamp

    def on_stats(self) -> None:
        now = time.perf_counter()
        dt = now - self.t_stats
        self.t_stats = now
        self.fps = self.win_frames / dt if dt > 0 else 0.0
        self.pub_fps.publish(Float32(data=float(self.fps)))
        if self.win_frames:
            lat = np.asarray(self.win_latency)
            self.get_logger().info(
                f"frame {self.n_frames}: {self.last_status}; {self.fps:.1f} fps; "
                f"latency mean {lat.mean():.0f} / p95 {np.percentile(lat, 95):.0f} / max {lat.max():.0f} ms; "
                f"input period {self.input_period * 1e3:.0f} ms; dropped {self.dropped}")
        self.win_latency.clear()
        self.win_frames = 0

    def node_stats(self) -> dict:
        return {"latency_ms": round(self.last_latency_ms, 2), "fps": round(self.fps, 2),
                "frames": self.n_frames, "dropped_frames": self.dropped,
                "input_period_ms": round(self.input_period * 1e3, 1)}

    # ------------------------------------------------------------------
    def on_cloud(self, msg: PointCloud2, topic: str = "") -> None:
        if self.active_topic is None and topic:
            self.active_topic = topic
            self.get_logger().info(
                f"input: {topic} (frame_id={msg.header.frame_id}, {msg.width * msg.height} points)")
            for other, sub in list(self.subs.items()):      # one input wins; stop listening to the rest
                if other != topic:
                    self.destroy_subscription(sub)
                    del self.subs[other]
        elif topic and topic != self.active_topic:
            return
        t0 = time.perf_counter()
        arr = structured_to_compact(pointcloud2_to_structured(msg))
        xyz_s = np.stack([arr["x"], arr["y"], arr["z"]], axis=1).astype(np.float32)
        r2 = (xyz_s * xyz_s).sum(axis=1)
        ok = (r2 >= self.cfg.sensor.min_range ** 2) & (r2 <= self.cfg.sensor.max_range ** 2)
        xyz_v = xyz_s[ok] @ self.R_vs.T.astype(np.float32)
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        frame = Frame(xyz=xyz_v, intensity=arr["intensity"][ok], ring=arr["ring"][ok],
                      stamp=stamp, frame_id=msg.header.frame_id)
        self._account_frame(stamp)
        res = self.detector.process(frame)
        self.last_latency_ms = (time.perf_counter() - t0) * 1e3   # decode + detect, goes into the status JSON
        self.publish(msg.header, frame, res)
        self.n_frames += 1
        self.win_frames += 1
        latency_ms = (time.perf_counter() - t0) * 1e3               # + publishing, goes to /resense/latency_ms
        self.win_latency.append(latency_ms)
        self.pub_latency.publish(Float32(data=float(latency_ms)))
        self.last_status = (f"OBSTACLE at {res.nearest_distance:.1f} m" if res.obstacle
                            else ("warning" if res.warning else "clear"))
        self.last_status += (f"; axis y={res.track.center:+.2f} "
                             f"R={'inf' if abs(res.track.curvature) < 1e-6 else '%.0f' % (1 / res.track.curvature)}")

    # ------------------------------------------------------------------
    def publish(self, header: Header, frame: Frame, res: FrameResult) -> None:
        out_frame = self.get_parameter("output_frame").get_parameter_value().string_value or header.frame_id
        hdr = Header(stamp=header.stamp, frame_id=out_frame)
        self.pub_flag.publish(Bool(data=bool(res.obstacle)))
        self.pub_warn.publish(Bool(data=bool(res.warning)))
        self.pub_dist.publish(Float32(data=float(res.nearest_distance) if res.nearest_distance is not None else -1.0))
        status = res.to_dict()
        status["node"] = self.node_stats()
        self.pub_status.publish(String(data=json.dumps(status)))

        det_msg = Detection3DArray(header=hdr)
        for d in res.detections + res.warnings:
            det = Detection3D(header=hdr)
            c_s = self.R_sv @ d.center
            det.bbox.center.position.x, det.bbox.center.position.y, det.bbox.center.position.z = map(float, c_s)
            det.bbox.center.orientation.w = 1.0
            size_s = np.abs(self.R_sv @ d.size)
            det.bbox.size.x, det.bbox.size.y, det.bbox.size.z = map(float, size_s)
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = f"{d.zone}_obstacle"
            hyp.hypothesis.score = float(d.confidence)
            det.results.append(hyp)
            det.id = str(d.id)
            det_msg.detections.append(det)
        self.pub_det.publish(det_msg)

        if self.get_parameter("publish_markers").get_parameter_value().bool_value:
            self.pub_markers.publish(self.make_markers(hdr, res))
        if self.get_parameter("publish_corridor_cloud").get_parameter_value().bool_value and res.corridor_idx.size:
            self.pub_corridor.publish(self.make_cloud(hdr, frame.xyz[res.corridor_idx] @ self.R_sv.T.astype(np.float32),
                                                     frame.intensity[res.corridor_idx]))

    def make_markers(self, hdr: Header, res: FrameResult) -> MarkerArray:
        arr = MarkerArray()
        clear = Marker(header=hdr, ns="resense", id=0, action=Marker.DELETEALL)
        arr.markers.append(clear)
        mid = 1
        for d in res.detections + res.warnings:
            box = Marker(header=hdr, ns="resense", id=mid, type=Marker.CUBE, action=Marker.ADD)
            c_s = self.R_sv @ d.center
            box.pose.position.x, box.pose.position.y, box.pose.position.z = map(float, c_s)
            box.pose.orientation.w = 1.0
            size_s = np.maximum(np.abs(self.R_sv @ d.size), 0.4)
            box.scale.x, box.scale.y, box.scale.z = map(float, size_s)
            if d.zone == "gauge":
                box.color.r, box.color.g, box.color.b, box.color.a = 1.0, 0.1, 0.1, 0.55
            else:
                box.color.r, box.color.g, box.color.b, box.color.a = 1.0, 0.6, 0.0, 0.45
            box.lifetime.sec = 0
            arr.markers.append(box)
            mid += 1
            txt = Marker(header=hdr, ns="resense", id=mid, type=Marker.TEXT_VIEW_FACING, action=Marker.ADD)
            txt.pose.position.x, txt.pose.position.y, txt.pose.position.z = float(c_s[0]), float(c_s[1]), float(c_s[2] + size_s[2] / 2 + 0.6)
            txt.pose.orientation.w = 1.0
            txt.scale.z = 0.8
            txt.color.r = txt.color.g = txt.color.b = txt.color.a = 1.0
            txt.text = f"{'OBSTACLE' if d.zone == 'gauge' else 'warning'} {d.distance:.1f} m  p={d.confidence:.2f}"
            arr.markers.append(txt)
            mid += 1
        # corridor outline: left/right edges of the strict gauge at rail-head + 1 m
        x_max = self.get_parameter("marker_x_max").get_parameter_value().double_value
        prof = np.asarray(self.cfg.gauge.profile)
        half = float(prof[:, 0].max())
        xs = np.linspace(self.cfg.gauge.range_min, x_max, 60)
        for k, side in enumerate((half, -half)):
            line = Marker(header=hdr, ns="resense", id=mid, type=Marker.LINE_STRIP, action=Marker.ADD)
            line.scale.x = 0.08
            line.color.r, line.color.g, line.color.b, line.color.a = 0.2, 1.0, 0.3, 0.8
            line.pose.orientation.w = 1.0
            for x in xs:
                p_v = np.array([x, res.track.center_y(x) + side, res.track.rail_z(x) + 1.0])
                p_s = self.R_sv @ p_v
                line.points.append(Point(x=float(p_s[0]), y=float(p_s[1]), z=float(p_s[2])))
            arr.markers.append(line)
            mid += 1
        status = Marker(header=hdr, ns="resense", id=mid, type=Marker.TEXT_VIEW_FACING, action=Marker.ADD)
        p_s = self.R_sv @ np.array([8.0, 0.0, 3.5])
        status.pose.position.x, status.pose.position.y, status.pose.position.z = map(float, p_s)
        status.pose.orientation.w = 1.0
        status.scale.z = 1.2
        if res.obstacle:
            status.text = f"OBSTACLE  {res.nearest_distance:.1f} m"
            status.color.r, status.color.g, status.color.b, status.color.a = 1.0, 0.1, 0.1, 1.0
        elif res.warning:
            status.text = "WARNING: object near gauge"
            status.color.r, status.color.g, status.color.b, status.color.a = 1.0, 0.6, 0.0, 1.0
        else:
            status.text = "PATH CLEAR"
            status.color.r, status.color.g, status.color.b, status.color.a = 0.2, 1.0, 0.3, 1.0
        arr.markers.append(status)
        return arr

    @staticmethod
    def make_cloud(hdr: Header, xyz: np.ndarray, intensity: np.ndarray) -> PointCloud2:
        data = np.zeros(xyz.shape[0], dtype=[("x", "f4"), ("y", "f4"), ("z", "f4"), ("intensity", "f4")])
        data["x"], data["y"], data["z"], data["intensity"] = xyz[:, 0], xyz[:, 1], xyz[:, 2], intensity
        msg = PointCloud2(header=hdr, height=1, width=xyz.shape[0], is_dense=True, is_bigendian=False,
                          point_step=16, row_step=16 * xyz.shape[0])
        msg.fields = [PointField(name=n, offset=4 * i, datatype=PointField.FLOAT32, count=1)
                      for i, n in enumerate(("x", "y", "z", "intensity"))]
        msg.data = data.tobytes()
        return msg


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
