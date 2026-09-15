"""ROS 2 node: PointCloud2 in -> obstacle flag, distance, Detection3DArray, RViz markers out.

Topics (defaults, all configurable via parameters):
  sub  /lidar_points                    sensor_msgs/PointCloud2
  pub  /resense/obstacle_detected       std_msgs/Bool      (confirmed object inside the gauge)
  pub  /resense/warning                 std_msgs/Bool      (confirmed object in the advisory zone)
  pub  /resense/nearest_distance        std_msgs/Float32   (m along the track, -1 if none)
  pub  /resense/detections              vision_msgs/Detection3DArray (gauge + warning objects)
  pub  /resense/status                  std_msgs/String    (JSON: full FrameResult for dashboards)
  pub  /resense/markers                 visualization_msgs/MarkerArray (boxes, labels, corridor)
  pub  /resense/corridor_points         sensor_msgs/PointCloud2 (points inside the corridor, debug)
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
        self.declare_parameter("input_topic", "/lidar_points")
        self.declare_parameter("config_file", "")
        self.declare_parameter("publish_markers", True)
        self.declare_parameter("publish_corridor_cloud", True)
        self.declare_parameter("marker_x_max", 250.0)
        self.declare_parameter("output_frame", "")   # empty = input frame id

        cfg_file = self.get_parameter("config_file").get_parameter_value().string_value
        self.cfg = DetectorConfig.from_yaml(cfg_file) if cfg_file else DetectorConfig()
        self.detector = Detector(self.cfg)
        self.R_vs = axis_matrix(self.cfg.sensor)            # sensor -> vehicle
        self.R_sv = self.R_vs.T                              # vehicle -> sensor (for markers)

        qos = QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                         history=QoSHistoryPolicy.KEEP_LAST)
        topic = self.get_parameter("input_topic").get_parameter_value().string_value
        self.sub = self.create_subscription(PointCloud2, topic, self.on_cloud, qos)
        self.pub_flag = self.create_publisher(Bool, "/resense/obstacle_detected", 10)
        self.pub_warn = self.create_publisher(Bool, "/resense/warning", 10)
        self.pub_dist = self.create_publisher(Float32, "/resense/nearest_distance", 10)
        self.pub_det = self.create_publisher(Detection3DArray, "/resense/detections", 10)
        self.pub_status = self.create_publisher(String, "/resense/status", 10)
        self.pub_markers = self.create_publisher(MarkerArray, "/resense/markers", 10)
        self.pub_corridor = self.create_publisher(PointCloud2, "/resense/corridor_points", 5)
        self.n_frames = 0
        self.t_last_log = time.time()
        self.get_logger().info(f"ReSense detector listening on {topic}")

    # ------------------------------------------------------------------
    def on_cloud(self, msg: PointCloud2) -> None:
        t0 = time.perf_counter()
        arr = structured_to_compact(pointcloud2_to_structured(msg))
        xyz_s = np.stack([arr["x"], arr["y"], arr["z"]], axis=1).astype(np.float32)
        r2 = (xyz_s * xyz_s).sum(axis=1)
        ok = (r2 >= self.cfg.sensor.min_range ** 2) & (r2 <= self.cfg.sensor.max_range ** 2)
        xyz_v = xyz_s[ok] @ self.R_vs.T.astype(np.float32)
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        frame = Frame(xyz=xyz_v, intensity=arr["intensity"][ok], ring=arr["ring"][ok],
                      stamp=stamp, frame_id=msg.header.frame_id)
        res = self.detector.process(frame)
        self.publish(msg.header, frame, res)
        self.n_frames += 1
        dt = (time.perf_counter() - t0) * 1e3
        if time.time() - self.t_last_log > 2.0:
            status = f"OBSTACLE at {res.nearest_distance:.1f} m" if res.obstacle else ("warning" if res.warning else "clear")
            self.get_logger().info(f"frame {self.n_frames}: {status}; {dt:.0f} ms; axis y={res.track.center:+.2f} "
                                   f"R={'inf' if abs(res.track.curvature) < 1e-6 else '%.0f' % (1 / res.track.curvature)}")
            self.t_last_log = time.time()

    # ------------------------------------------------------------------
    def publish(self, header: Header, frame: Frame, res: FrameResult) -> None:
        out_frame = self.get_parameter("output_frame").get_parameter_value().string_value or header.frame_id
        hdr = Header(stamp=header.stamp, frame_id=out_frame)
        self.pub_flag.publish(Bool(data=bool(res.obstacle)))
        self.pub_warn.publish(Bool(data=bool(res.warning)))
        self.pub_dist.publish(Float32(data=float(res.nearest_distance) if res.nearest_distance is not None else -1.0))
        self.pub_status.publish(String(data=json.dumps(res.to_dict())))

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
