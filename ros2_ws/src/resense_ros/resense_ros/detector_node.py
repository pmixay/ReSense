"""ROS 2 node: PointCloud2 in -> obstacle flag, distance, Detection3DArray, RViz markers out.

Topics (defaults, all configurable via parameters):
  sub  /lidar_points, /sensing/lidar/hesai128/pointcloud, or whatever PointCloud2 topic the bag
       carries -- ``input_topic`` is a comma-separated candidate list and, with ``auto_discover``,
       the node also picks up any other PointCloud2 topic that appears on the graph. The
       organizers' bags do not agree on the name (roundT_doubleT publishes /lidar_points +
       hesai_lidar, doubleT_obstacle /sensing/lidar/hesai128/pointcloud + lidar_livox) and the
       organizers confirmed (23.09) that the control data may use either pair, all recorded with
       the same LiDAR. See "Input handling" below.
  pub  /resense/obstacle_detected       std_msgs/Bool      (confirmed object inside the gauge)
  pub  /resense/warning                 std_msgs/Bool      (confirmed object in the advisory zone)
  pub  /resense/nearest_distance        std_msgs/Float32   (m along the track, -1 if none)
  pub  /resense/detections              vision_msgs/Detection3DArray (gauge + warning objects)
  pub  /resense/status                  std_msgs/String    (JSON: full FrameResult for dashboards)
  pub  /resense/markers                 visualization_msgs/MarkerArray (boxes, labels, corridor)
  pub  /resense/corridor_points         sensor_msgs/PointCloud2 (points inside the corridor, debug)
  pub  /resense/latency_ms              std_msgs/Float32   (per frame: decode + detect + publish, ms)
  pub  /resense/fps                     std_msgs/Float32   (frames processed per second, every stats_period s)
  pub  /resense/decision                std_msgs/String    (v0.6: GO | CAUTION | STOP | FAULT, see below)
  pub  /resense/clear_distance          std_msgs/Float32   (v0.6: m of track verified clear: the nearest obstacle,
                                                            else how far the corridor was checked; 0 on a fault)
  pub  /resense/health                  diagnostic_msgs/DiagnosticArray (v0.6: input, visibility, track lock,
                                                            latency, mount calibration; OK / WARN / ERROR / STALE)
  pub  /tf_static                       resense_lidar -> <input frame_id>, identity, once per input frame id
  sub  <speed_topic>                    std_msgs/Float32   (optional: train speed in m/s)
  sub  <odom_topic>                     nav_msgs/Odometry  (optional: twist.linear.x is the train speed)

The status JSON carries an extra ``node`` object next to the detector fields:
``{"latency_ms", "fps", "frames", "dropped_frames", "input_period_ms", "ego_speed_mps",
"ego_speed_source", "input_topic", "recording"}`` (``recording`` counts the recordings seen,
see "Input handling") (``latency_ms`` there is decode + detect of the same frame, before
publishing). ``dropped_frames`` is estimated from gaps in the input header stamps (a slow frame
makes the node skip the ones that arrived meanwhile, and a backlog is worked through
``catchup_step`` s of recording apart, see "Input handling"; the input's reliability follows the
publishers, ``input_reliability``).

Ego speed (multi-frame accumulation needs it): the ``ego_speed_mps`` parameter wins when >= 0,
else the latest value from ``speed_topic`` / ``odom_topic`` younger than ``speed_timeout``,
else ``None``: the single-frame path (no accumulation; the LiDAR-only speed estimator is off
by default, ``accumulation.estimate_speed``, EXPERIMENTS.md section 1b). The value is handed to
``Detector.process(frame, ego_speed=...)`` when the installed detector accepts it.

Decision (v0.6, the organizers' "can we go / is there an obstacle / how far"): ``STOP`` when a
confirmed obstacle is inside the train envelope, ``FAULT`` when the input cannot be trusted
(too few returns, view blocked, no frame for ``stale_timeout`` s, an exception while
processing), ``CAUTION`` for an advisory object next to the envelope or a degraded health
(track model on its prior, short visibility, latency over budget), else ``GO``. The node never
dies on a bad frame: the exception is logged, ``FAULT`` published, and after
``max_consecutive_errors`` the detector is reset. The watchdog publishes ``FAULT`` / health
``STALE`` while the input is silent, and ``FAULT`` / ``NO_INPUT`` before the first frame
(after ``startup_grace`` s).

Sensor mount (v0.6): ``sensor_forward`` / ``sensor_left`` / ``sensor_up`` override the axis
mapping of the parameter file, ``mount_roll_deg`` / ``mount_pitch_deg`` / ``mount_yaw_deg`` a
fixed tilt correction, and ``auto_calibrate`` (default true) lets the detector find the
orientation and tilt from the rails and the bed in the first frames (``resense/calibration.py``).

Input handling (v0.6.1): every candidate subscription stays open; one input is processed at a
time (the same LiDAR may appear on two topics). When the active topic has been silent for
``input_switch_timeout`` s and another topic delivers, the node switches to it. A **new
recording** - another topic, another ``frame_id``, header stamps that jump back (a bag played
again, ``loop:=true``) or forward by more than ``new_input_gap`` s - starts from scratch: a
fresh detector, so the scene state and the mount calibration of the previous recording (the
bags use different mounts) do not carry over. A shorter forward gap above ``hole_reset_gap`` s
(a hole in the recording) resets the scene but keeps the calibration. While the input is
silent, topic discovery keeps running, so a bag with a topic name nobody listed is still found.

Backlog (v0.6.4): ``ros2 bag play`` (Humble) reads up to 1000 messages before its first publish
while its clock runs, then sends the overdue first seconds of the recording back to back. The
input queue holds ``input_queue_depth`` frames and every frame waiting is taken; one frame waiting
is processed at once, several are worked through ``catchup_step`` s of recording apart (the ones
in between skipped, none older than ``catchup_max_lag`` s behind the newest) until the node is
back on the newest frame. ``catchup_step: 0`` processes the newest only.

The static TF exists so that one RViz / Foxglove layout works for every bag: the organizers'
bags carry different ``frame_id`` values (``hesai_lidar``, ``lidar_livox``); the layouts use
``resense_lidar`` as the fixed frame and the node links it to whatever frame the input has.
"""
from __future__ import annotations

import inspect
import json
import math
import time
import traceback

import numpy as np
import rclpy
from geometry_msgs.msg import Point, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Bool, Float32, String, Header
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from vision_msgs.msg import Detection3D, Detection3DArray, ObjectHypothesisWithPose
from visualization_msgs.msg import Marker, MarkerArray
from tf2_ros import StaticTransformBroadcaster

from resense import __version__ as RESENSE_VERSION, _native
from resense.config import DetectorConfig
from resense.detector import Detector, FrameResult
from resense.frame import Frame, axis_matrix
from resense.pointcloud import pointcloud2_to_arrays


UNSET = -999.0   # sentinel of the mount_*_deg parameters: keep the value of the parameter file


class DetectorNode(Node):
    def __init__(self) -> None:
        super().__init__("resense_detector")
        self.declare_parameter("input_topic", "/lidar_points,/sensing/lidar/hesai128/pointcloud")
        self.declare_parameter("auto_discover", True)    # also take PointCloud2 topics found on the graph
        self.declare_parameter("discover_period", 2.0)   # s, how often to look while the input is silent
        self.declare_parameter("config_file", "")
        self.declare_parameter("publish_markers", True)
        self.declare_parameter("publish_corridor_cloud", True)
        self.declare_parameter("marker_x_max", 250.0)
        self.declare_parameter("output_frame", "")   # empty = input frame id
        self.declare_parameter("stats_period", 2.0)  # s, between FPS / latency log lines and /resense/fps
        self.declare_parameter("ego_speed_mps", -1.0)   # train speed for accumulation; < 0 = unknown
        self.declare_parameter("speed_topic", "")       # std_msgs/Float32, m/s (optional)
        self.declare_parameter("odom_topic", "")        # nav_msgs/Odometry, twist.linear.x (optional)
        self.declare_parameter("speed_timeout", 1.0)    # s, a speed message older than this no longer counts
        self.declare_parameter("publish_tf", True)      # static identity TF tf_parent_frame -> input frame id
        self.declare_parameter("tf_parent_frame", "resense_lidar")
        # --- v0.6: sensor mount (the organizers: the LiDAR position is not fixed between trains)
        self.declare_parameter("sensor_forward", "")    # e.g. "-y" / "+x"; empty = the parameter file
        self.declare_parameter("sensor_left", "")
        self.declare_parameter("sensor_up", "")
        self.declare_parameter("mount_roll_deg", UNSET)    # UNSET (-999) = the parameter file
        self.declare_parameter("mount_pitch_deg", UNSET)
        self.declare_parameter("mount_yaw_deg", UNSET)
        self.declare_parameter("auto_calibrate", True)  # find orientation / tilt from rails and bed in the first frames
        # --- v0.6: production guards
        self.declare_parameter("stale_timeout", 0.5)    # s without an input frame before FAULT / STALE
        self.declare_parameter("startup_grace", 2.0)    # s after start before "no input yet" is a FAULT
        self.declare_parameter("max_consecutive_errors", 5)   # processing exceptions in a row before the detector is reset
        # --- v0.6.1: several recordings / topic names through one running node
        self.declare_parameter("input_switch_timeout", 1.0)   # s the active topic must be silent before another one is taken
        self.declare_parameter("new_input_gap", 30.0)         # s of forward stamp jump that means a new recording (full reset)
        self.declare_parameter("hole_reset_gap", 1.0)         # s of forward stamp jump that resets the scene (calibration kept)
        # --- v0.6.4: the start of a played bag. `ros2 bag play` (Humble) reads up to 1000 messages - all
        # of a short recording, ~2 GB for 20 s of 360-degree clouds - before its first publish while
        # its clock already runs, then sends the overdue first seconds back to back (doubleT_obstacle:
        # 4.1 s of recording in 0.4 s). A keep-last-1 input kept the newest of them only and the first
        # 2-4 s of every played bag were lost. The input now holds input_queue_depth frames; while
        # frames wait, the node works through them catchup_step s of recording apart (the frames in
        # between are skipped) until it is back on the newest. A frame that waits alone is processed
        # at once: a node slower than the sensor still skips, never lags (EXPERIMENTS.md section 3b).
        # 40 frames ride out a transport stall inside the burst (20 lost 1.7 s once in 3 runs); the
        # reader keeps what it once held: ~0.4 GB more resident memory with 10 MB clouds
        self.declare_parameter("input_queue_depth", 40)       # frames the input subscription may hold between two frames
        self.declare_parameter("catchup_step", 0.3)           # s of recording between processed frames while frames wait;
                                                              # 0 = always the newest (the v0.6.3 behaviour)
        self.declare_parameter("catchup_max_lag", 5.0)        # s: waiting frames older than the newest by more are dropped
        # --- v0.6.2: reliability of the input subscription. A 360-degree cloud is ~10 MB, i.e. ~160 UDP
        # fragments; best-effort loses the whole message with any fragment (measured in Docker with
        # `ros2 bag play` of doubleT_obstacle: 5 of 201 frames delivered best-effort, 174+ reliable).
        # auto = match the publishers: reliable when every publisher of the topic is (`ros2 bag play`
        # of the organizers' recordings), best-effort when one is not (a sensor-data driver)
        self.declare_parameter("input_reliability", "auto")   # auto | reliable | best_effort

        cfg_file = self.get_parameter("config_file").get_parameter_value().string_value
        self.cfg = DetectorConfig.from_yaml(cfg_file) if cfg_file else DetectorConfig()
        for axis in ("forward", "left", "up"):
            v = self.get_parameter(f"sensor_{axis}").get_parameter_value().string_value.strip()
            if v:
                setattr(self.cfg.sensor, axis, v)
        for ang in ("roll", "pitch", "yaw"):
            v = self.get_parameter(f"mount_{ang}_deg").get_parameter_value().double_value
            if not math.isnan(v) and v > UNSET + 1.0:
                setattr(self.cfg.sensor, f"{ang}_deg", float(v))
        self.cfg.calibration.enabled = self.get_parameter("auto_calibrate").get_parameter_value().bool_value
        self.detector = Detector(self.cfg)
        self.R_vs = axis_matrix(self.cfg.sensor)            # sensor -> configured vehicle frame
        self.R_sv = self.R_vs.T                              # configured vehicle frame -> sensor (for markers)
        self.get_logger().info(
            f"sensor mount: forward={self.cfg.sensor.forward} left={self.cfg.sensor.left} up={self.cfg.sensor.up} "
            f"roll/pitch/yaw={self.cfg.sensor.roll_deg}/{self.cfg.sensor.pitch_deg}/{self.cfg.sensor.yaw_deg} deg; "
            f"auto-calibration {'on' if self.cfg.calibration.enabled else 'off'}")

        # --- ego speed: parameter > topic > none (single-frame path). The accumulation stage
        # takes ``ego_speed`` as a keyword; a detector without it (older core) still works.
        self._process_takes_speed = "ego_speed" in inspect.signature(Detector.process).parameters
        self.speed_value = None        # m/s, latest topic value
        self.speed_time = None         # perf_counter() when it arrived
        self.last_speed = None         # what the last frame was processed with
        self.last_speed_source = None  # "param" | "topic" | None
        speed_topic = self.get_parameter("speed_topic").get_parameter_value().string_value
        odom_topic = self.get_parameter("odom_topic").get_parameter_value().string_value
        if speed_topic:
            self.create_subscription(Float32, speed_topic, self.on_speed, 10)
        if odom_topic:
            self.create_subscription(Odometry, odom_topic, self.on_odom, 10)
        # --- one fixed frame for the visualisation layouts, whatever the bag's frame_id is
        self.tf_static = (StaticTransformBroadcaster(self)
                          if self.get_parameter("publish_tf").get_parameter_value().bool_value else None)
        self.tf_frames_sent = set()

        self.qos_depth = max(1, self.get_parameter("input_queue_depth").get_parameter_value().integer_value)
        self.catchup_step = self.get_parameter("catchup_step").get_parameter_value().double_value
        self.catchup_max_lag = self.get_parameter("catchup_max_lag").get_parameter_value().double_value
        self.pending = []              # (topic, msg) taken from the input queues, not processed yet, oldest first
        self.pending_last = None       # (topic, frame_id, stamp) of the last frame handed to processing
        self.catchup = None            # [frames processed, max s behind, start time] of the current catch-up
        self.catchup_skipped = 0       # frames skipped since the current catch-up started
        self.pending_gc = self.create_guard_condition(self.on_pending)
        rel = self.get_parameter("input_reliability").get_parameter_value().string_value.strip().lower()
        self.input_reliability = rel.replace("-", "_") if rel else "auto"
        self.sub_rel = {}              # topic -> "reliable" | "best_effort" of its subscription
        topic = self.get_parameter("input_topic").get_parameter_value().string_value
        self.subs = {}                 # topic -> Subscription (all kept: a later recording may use another name)
        self.active_topic = None       # the topic being processed; frames on the others are ignored while it is live
        self.active_frame_id = None
        self.n_inputs = 0              # recordings seen (a new topic, frame id or a stamp discontinuity)
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
        self.pub_decision = self.create_publisher(String, "/resense/decision", 10)
        self.pub_clear = self.create_publisher(Float32, "/resense/clear_distance", 10)
        self.pub_health = self.create_publisher(DiagnosticArray, "/resense/health", 10)
        # --- guards: last processed frame time (watchdog), consecutive processing errors
        self.last_frame_wall = None
        self.t_node_start = time.perf_counter()
        self.consecutive_errors = 0
        self.mount_logged = ""
        self.watchdog = self.create_timer(0.1, self.on_watchdog)
        self.last_stale_pub = 0.0

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
        self.qos_timer = (self.create_timer(1.0, self.on_match_qos)
                          if self.input_reliability not in ("reliable", "best_effort") else None)
        self.get_logger().info("ReSense detector listening on " + ", ".join(self.subs)
                               + (" (+ auto-discovery)" if self.discover_timer else "")
                               + f"; input reliability {self.input_reliability}; per-frame kernels: {_native.status()}"
                               + f"; resense {RESENSE_VERSION}")

    # ------------------------------------------------------------------
    def input_qos(self, reliability: str):
        return QoSProfile(depth=self.qos_depth, history=QoSHistoryPolicy.KEEP_LAST,
                          reliability=(QoSReliabilityPolicy.RELIABLE if reliability == "reliable"
                                       else QoSReliabilityPolicy.BEST_EFFORT))

    def publisher_reliability(self, topic: str):
        """'reliable' when every publisher of ``topic`` is, 'best_effort' when one is not (a
        best-effort reader matches both), None when there is no publisher yet."""
        try:
            infos = self.get_publishers_info_by_topic(topic)
        except Exception:  # noqa: BLE001 - graph queries are best effort
            return None
        rels = [getattr(getattr(i, "qos_profile", None), "reliability", None) for i in infos]
        rels = [r for r in rels if r is not None]
        if not rels:
            return None
        return "reliable" if all(r == QoSReliabilityPolicy.RELIABLE for r in rels) else "best_effort"

    def subscribe(self, topic: str, reliability: str = None) -> None:
        """Subscribe to one more candidate input topic (idempotent)."""
        if topic in self.subs:
            return
        if reliability is None:
            reliability = (self.input_reliability if self.input_reliability in ("reliable", "best_effort")
                           else self.publisher_reliability(topic) or "reliable")
        self.sub_rel[topic] = reliability
        self.subs[topic] = self.create_subscription(
            PointCloud2, topic, lambda msg, t=topic: self.on_cloud(msg, t), self.input_qos(reliability))

    def on_match_qos(self) -> None:
        """(input_reliability auto) Re-create a subscription whose reliability differs from its
        publishers': a reliable reader gets nothing from a best-effort writer, and a best-effort
        reader loses most multi-megabyte clouds of a reliable one."""
        for topic in list(self.subs):
            want = self.publisher_reliability(topic)
            if want is None or want == self.sub_rel.get(topic):
                continue
            self.destroy_subscription(self.subs.pop(topic))
            self.get_logger().info(f"{topic}: publishers are {want.replace('_', '-')}; subscription re-created to match")
            self.subscribe(topic, want)

    def on_discover(self) -> None:
        """While no input is live, subscribe to every PointCloud2 topic on the graph.

        The organizers' bags disagree on the topic name and the control data may use either,
        so the node finds its input instead of requiring the jury to pass the right one. Keeps
        looking whenever the input is silent (the next recording may use another name)."""
        if self.active_topic is not None and not self.input_silent(
                self.get_parameter("stale_timeout").get_parameter_value().double_value):
            return
        for name, types in self.get_topic_names_and_types():
            if ("sensor_msgs/msg/PointCloud2" in types and not name.startswith("/resense/")
                    and name not in self.subs):
                self.get_logger().info("auto-discovered PointCloud2 topic " + name)
                self.subscribe(name)

    # ------------------------------------------------------------------
    def on_speed(self, msg: Float32) -> None:
        self.speed_value, self.speed_time = float(msg.data), time.perf_counter()

    def on_odom(self, msg: Odometry) -> None:
        self.speed_value, self.speed_time = float(msg.twist.twist.linear.x), time.perf_counter()

    def ego_speed(self):
        """(train speed in m/s or None, source): the parameter wins, then a fresh topic value."""
        v = self.get_parameter("ego_speed_mps").get_parameter_value().double_value
        if v >= 0.0:
            return v, "param"
        timeout = self.get_parameter("speed_timeout").get_parameter_value().double_value
        if self.speed_value is not None and time.perf_counter() - self.speed_time <= timeout:
            return self.speed_value, "topic"
        return None, None

    def send_static_tf(self, child: str) -> None:
        """Identity transform ``tf_parent_frame`` -> the input frame id, sent once per frame id, so
        that RViz / Foxglove can keep ``resense_lidar`` as the fixed frame for every bag."""
        if self.tf_static is None or not child or child in self.tf_frames_sent:
            return
        parent = self.get_parameter("tf_parent_frame").get_parameter_value().string_value
        self.tf_frames_sent.add(child)
        if child == parent:
            return
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = parent
        t.child_frame_id = child
        t.transform.rotation.w = 1.0
        self.tf_static.sendTransform(t)
        self.get_logger().info(f"static TF {parent} -> {child} (identity)")

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
                "input_period_ms": round(self.input_period * 1e3, 1),
                "ego_speed_mps": None if self.last_speed is None else round(float(self.last_speed), 2),
                "ego_speed_source": self.last_speed_source,
                "input_topic": self.active_topic, "recording": self.n_inputs}

    # ------------------------------------------------------------------
    def input_silent(self, timeout: float) -> bool:
        return self.last_frame_wall is None or time.perf_counter() - self.last_frame_wall > timeout

    def start_new_input(self, topic: str, msg: PointCloud2, why: str) -> None:
        """A new recording: a fresh detector (scene state and mount calibration start over)."""
        first = self.active_topic is None
        self.active_topic = topic or self.active_topic
        self.active_frame_id = msg.header.frame_id
        self.n_inputs += 1
        if not first:
            self.detector = Detector(self.cfg)
            self.consecutive_errors = 0
            self.mount_logged = ""
        self.last_stamp = None
        self.get_logger().info(
            f"input {self.n_inputs}: {self.active_topic} (frame_id={msg.header.frame_id}, "
            f"{msg.width * msg.height} points){'' if first else ' - ' + why + ': detector restarted'}")

    def check_continuity(self, topic: str, msg: PointCloud2) -> bool:
        """Decide what a frame means for the input state; False = ignore the frame."""
        if self.active_topic is None:
            self.start_new_input(topic, msg, "")
            return True
        if topic and topic != self.active_topic:
            timeout = self.get_parameter("input_switch_timeout").get_parameter_value().double_value
            if not self.input_silent(timeout):
                return False                 # the same LiDAR on a second topic: one input at a time
            self.start_new_input(topic, msg, f"input switched from {self.active_topic}")
            return True
        if msg.header.frame_id != self.active_frame_id:
            self.start_new_input(topic, msg, f"frame_id changed from {self.active_frame_id}")
            return True
        if self.last_stamp is not None:
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            gap = stamp - self.last_stamp
            new_gap = self.get_parameter("new_input_gap").get_parameter_value().double_value
            hole = self.get_parameter("hole_reset_gap").get_parameter_value().double_value
            if gap < -0.5 or gap > new_gap:
                self.start_new_input(topic, msg, f"header stamps jumped by {gap:+.1f} s (a new recording)")
            elif gap > hole:
                self.get_logger().warn(f"{gap:.1f} s hole in the input: scene state reset, calibration kept")
                self.detector.reset()
        return True

    # ------------------------------------------------------------------
    @staticmethod
    def _stamp(msg: PointCloud2) -> float:
        return msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

    @staticmethod
    def catchup_plan(stamps, last, step: float, max_lag: float):
        """Indices of the waiting frames to process, oldest first; the others are skipped.

        ``stamps``: the header stamps of the waiting frames of one input, in arrival order and
        increasing; ``last``: the stamp of the input's last processed frame (None at its start).
        One frame waiting: that frame. Several (the node is behind): a chain through them that
        steps at most ``step`` s of recording - each link the latest frame within ``step`` of the
        previous one, the next frame when none is - from ``last`` (from the first frame at the
        start of an input) to the newest frame; frames older than the newest by more than
        ``max_lag`` s are dropped first. ``step`` <= 0: the newest frame only."""
        n = len(stamps)
        if n <= 1:
            return list(range(n))
        if step <= 0:
            return [n - 1]
        i = 0
        if max_lag > 0:
            while i < n - 1 and stamps[i] < stamps[-1] - max_lag:
                i += 1
        plan, cur = [], last
        while i < n:
            j = i
            while cur is not None and j + 1 < n and stamps[j + 1] <= cur + step + 1e-6:
                j += 1
            plan.append(j)
            cur, i = stamps[j], j + 1
        return plan

    def on_cloud(self, msg: PointCloud2, topic: str = "") -> None:
        """Input callback: the frame joins the ones already waiting behind it, then the next one
        is processed (``catchup_step``)."""
        self.pending.append((topic, msg))
        self.take_waiting(topic)
        self.process_next()

    def on_pending(self) -> None:
        """Guard condition: frames are still waiting after the last one processed."""
        for topic in {t for t, _ in self.pending}:
            self.take_waiting(topic)
        self.process_next()

    def take_waiting(self, topic: str) -> None:
        """Move the frames waiting in the subscription's queue into ``pending`` (the rclpy call the
        executor itself makes; without it, e.g. in the unit tests, nothing is taken)."""
        sub = self.subs.get(topic)
        handle = getattr(sub, "handle", None)
        if handle is None or not hasattr(handle, "take_message"):
            return
        try:
            while True:
                with handle:
                    got = handle.take_message(sub.msg_type, sub.raw)
                if got is None:
                    return
                self.pending.append((topic, got[0]))
                if len(self.pending) > 2:
                    self.prune()                # hold the chain's frames only, not the whole burst
        except Exception as e:  # noqa: BLE001 - never lose the input over the queue peek
            self.get_logger().warn(f"could not take the waiting frames of {topic}: {e!r}")

    def prune(self):
        """Drop the waiting frames the catch-up will skip; returns the stamps of the frames of
        one input at the head of ``pending`` that are left (the next to process first)."""
        topic0, m0 = self.pending[0]
        stamps = [self._stamp(m0)]
        for t, m in self.pending[1:]:           # the frames of one input at the head of the queue
            s = self._stamp(m)
            if t != topic0 or m.header.frame_id != m0.header.frame_id or s < stamps[-1]:
                break
            stamps.append(s)
        last = self.pending_last
        new_gap = self.get_parameter("new_input_gap").get_parameter_value().double_value
        last = (last[2] if last is not None and last[:2] == (topic0, m0.header.frame_id)
                and -0.5 <= stamps[0] - last[2] <= new_gap else None)
        n = len(stamps)
        plan = self.catchup_plan(stamps, last, self.catchup_step, self.catchup_max_lag)
        if len(plan) < n:
            run, self.pending = self.pending[:n], self.pending[n:]
            self.pending[:0] = [run[i] for i in plan]
            self.catchup_skipped += n - len(plan)
        return [stamps[i] for i in plan]

    def process_next(self) -> None:
        """Process one waiting frame: the only one, or the next link of the catch-up chain."""
        if not self.pending:
            return
        stamps = self.prune()
        self.track_catchup(stamps[-1] - stamps[0], len(stamps))
        topic, msg = self.pending.pop(0)
        try:
            self.process_cloud(msg, topic)
        finally:
            if topic == self.active_topic:
                self.pending_last = (topic, msg.header.frame_id, self._stamp(msg))
            if self.pending:
                self.pending_gc.trigger()

    def track_catchup(self, behind: float, left: int) -> None:
        """Log a catch-up - more than ``catchup_step`` s of recording waiting - when it starts and
        when the node is back on the newest frame (``left``: frames of the chain, this one included)."""
        if self.catchup is None:
            if self.catchup_step <= 0 or behind <= self.catchup_step:
                self.catchup_skipped = 0
                return
            self.catchup = [0, 0.0, time.perf_counter()]
            self.get_logger().info(f"{behind:.1f} s of recording waiting: catching up, one frame every "
                                   f"{self.catchup_step:g} s of recording")
        c = self.catchup
        c[0], c[1] = c[0] + 1, max(c[1], behind)
        if left == 1 and len(self.pending) <= 1:
            self.get_logger().info(f"caught up in {time.perf_counter() - c[2]:.1f} s: {c[0]} frames processed, "
                                   f"{self.catchup_skipped} skipped, at most {c[1]:.1f} s of recording behind")
            self.catchup, self.catchup_skipped = None, 0

    def process_cloud(self, msg: PointCloud2, topic: str = "") -> None:
        if not self.check_continuity(topic, msg):
            return
        self.send_static_tf(msg.header.frame_id)
        t0 = time.perf_counter()
        self.last_frame_wall = t0
        try:
            xyz_s, inten, ring, n_raw, n_near = pointcloud2_to_arrays(
                msg, self.cfg.sensor.min_range, self.cfg.sensor.max_range)
            xyz_v = xyz_s @ self.R_vs.T.astype(np.float32)
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            frame = Frame(xyz=xyz_v, intensity=inten, ring=ring, stamp=stamp, frame_id=msg.header.frame_id,
                          meta={"n_raw": n_raw, "n_near": n_near})
            self._account_frame(stamp)
            self.last_speed, self.last_speed_source = self.ego_speed()
            res = (self.detector.process(frame, ego_speed=self.last_speed) if self._process_takes_speed
                   else self.detector.process(frame))
        except Exception as e:  # noqa: BLE001 - a bad frame must never take the node down
            self.on_processing_error(msg.header, e)
            return
        self.consecutive_errors = 0
        self.last_latency_ms = (time.perf_counter() - t0) * 1e3   # decode + detect, goes into the status JSON
        mount = getattr(res, "mount", {}) or {}
        if mount.get("status") and mount.get("status") != self.mount_logged:
            self.mount_logged = mount["status"]
            self.get_logger().info(f"mount calibration: {mount.get('status')} - {mount.get('message', '')}")
        try:
            self.publish(msg.header, frame, res)
        except Exception as e:  # noqa: BLE001 - a publishing failure must not take the node down either
            self.on_processing_error(msg.header, e)
            return
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
    def on_processing_error(self, header: Header, err: Exception) -> None:
        """Guard: log, publish FAULT, and reset the detector after repeated failures."""
        self.consecutive_errors += 1
        self.get_logger().error(f"frame processing failed ({self.consecutive_errors} in a row): {err!r}\n"
                                + traceback.format_exc(limit=4))
        self.publish_fault(header, f"processing error: {type(err).__name__}: {err}")
        limit = self.get_parameter("max_consecutive_errors").get_parameter_value().integer_value
        if self.consecutive_errors >= max(1, limit):
            self.get_logger().warn("resetting the detector after repeated processing errors")
            self.detector.reset()
            self.consecutive_errors = 0

    def publish_fault(self, header: Header, message: str, level_name: str = "ERROR") -> None:
        """Publish a fault as a complete output snapshot.

        A fault must not leave the last successful decision visible on any of the
        alarm topics or in RViz.  In particular, publishing only ``/decision``
        used to leave the previous warning, distance, detections, markers and
        status JSON latched at their old values.
        """
        self.pub_decision.publish(String(data="FAULT"))
        self.pub_clear.publish(Float32(data=0.0))
        self.pub_flag.publish(Bool(data=False))
        self.pub_warn.publish(Bool(data=False))
        self.pub_dist.publish(Float32(data=-1.0))
        arr = DiagnosticArray(header=Header(stamp=self.get_clock().now().to_msg(), frame_id=header.frame_id))
        diag_level = (DiagnosticStatus.STALE if level_name == "STALE" else DiagnosticStatus.ERROR)
        st = DiagnosticStatus(level=diag_level, name="resense/detector", message=message,
                              hardware_id=header.frame_id or "lidar")
        st.values.append(KeyValue(key="state", value=level_name))
        arr.status.append(st)
        self.pub_health.publish(arr)

        # Keep the status stream useful to headless consumers as well.  A
        # watchdog/error snapshot is not a frame from a recording, so it has no
        # ``node`` timing object: acceptance tooling must not count it as a
        # zero-latency frame or include it in per-recording criteria.
        try:
            stamp = float(header.stamp.sec) + float(header.stamp.nanosec) * 1e-9
        except (AttributeError, TypeError, ValueError):
            stamp = 0.0
        fault_status = {
            "stamp": stamp,
            "obstacle": False,
            "warning": False,
            "nearest_distance": None,
            "detections": [],
            "warnings": [],
            "n_candidates": 0,
            "n_points": 0,
            "n_corridor": 0,
            "timing_ms": {},
            "health": {"level": "error", "messages": [message]},
            "mount": {},
            "clear_distance": 0.0,
            "decision": "FAULT",
        }
        self.pub_status.publish(String(data=json.dumps(fault_status)))
        self.pub_det.publish(Detection3DArray(header=header))
        if self.get_parameter("publish_markers").get_parameter_value().bool_value:
            clear = Marker(header=header, ns="resense", id=0, action=Marker.DELETEALL)
            self.pub_markers.publish(MarkerArray(markers=[clear]))
        self.last_status = "FAULT: " + message

    def on_watchdog(self) -> None:
        """Guard: the input went silent (sensor, driver or bag stopped) -> FAULT / STALE at 2 Hz;
        before the first frame, after ``startup_grace`` s, FAULT / NO_INPUT (v0.6.2: silence is
        not an answer to "can we go")."""
        timeout = self.get_parameter("stale_timeout").get_parameter_value().double_value
        now = time.perf_counter()
        if self.last_frame_wall is None:
            grace = self.get_parameter("startup_grace").get_parameter_value().double_value
            if now - self.t_node_start > grace and now - self.last_stale_pub > 0.5:
                self.last_stale_pub = now
                self.publish_fault(Header(frame_id=""), "no LiDAR frame received yet (listening on "
                                   + ", ".join(self.subs) + "): path not monitored", "NO_INPUT")
            return
        silent = now - self.last_frame_wall
        if silent > timeout and now - self.last_stale_pub > 0.5:
            self.last_stale_pub = now
            self.publish_fault(Header(frame_id=self.active_topic or ""),
                               f"no LiDAR frame for {silent:.1f} s (> {timeout:.1f} s): path not monitored", "STALE")

    @staticmethod
    def decision(res: FrameResult) -> str:
        level = (getattr(res, "health", {}) or {}).get("level", "ok")
        if res.obstacle:
            return "STOP"
        if level == "error":
            return "FAULT"
        if res.warning or level == "warn":
            return "CAUTION"
        return "GO"

    def health_msg(self, hdr: Header, res: FrameResult) -> DiagnosticArray:
        h = getattr(res, "health", {}) or {}
        lv = {"ok": DiagnosticStatus.OK, "warn": DiagnosticStatus.WARN, "error": DiagnosticStatus.ERROR}
        st = DiagnosticStatus(level=lv.get(h.get("level", "ok"), DiagnosticStatus.OK), name="resense/detector",
                              message="; ".join(h.get("messages", [])) or "ok", hardware_id=hdr.frame_id or "lidar")
        for k in ("points", "near_fraction", "blocked_sectors", "visibility", "rail_lock", "latency_p95_ms",
                  "monitored_range", "clear_distance"):
            if k in h:
                st.values.append(KeyValue(key=k, value=str(h[k])))
        m = getattr(res, "mount", {}) or {}
        for k in ("status", "orientation", "roll_deg", "pitch_deg", "yaw_deg", "height", "drift_deg"):
            if k in m:
                st.values.append(KeyValue(key=f"mount_{k}", value=str(m[k])))
        st.values.append(KeyValue(key="fps", value=f"{self.fps:.1f}"))
        st.values.append(KeyValue(key="dropped_frames", value=str(self.dropped)))
        return DiagnosticArray(header=hdr, status=[st])

    # ------------------------------------------------------------------
    def publish(self, header: Header, frame: Frame, res: FrameResult) -> None:
        out_frame = self.get_parameter("output_frame").get_parameter_value().string_value or header.frame_id
        hdr = Header(stamp=header.stamp, frame_id=out_frame)
        self.pub_flag.publish(Bool(data=bool(res.obstacle)))
        self.pub_warn.publish(Bool(data=bool(res.warning)))
        self.pub_dist.publish(Float32(data=float(res.nearest_distance) if res.nearest_distance is not None else -1.0))
        status = res.to_dict()
        status["node"] = self.node_stats()
        status["decision"] = self.decision(res)
        self.pub_status.publish(String(data=json.dumps(status)))
        self.pub_decision.publish(String(data=status["decision"]))
        self.pub_clear.publish(Float32(data=float(getattr(res, "clear_distance", -1.0))))
        self.pub_health.publish(self.health_msg(hdr, res))
        # vehicle frame of the detector (after the mount calibration) -> sensor frame
        R_out = self.R_sv @ np.asarray(getattr(self.detector, "mount_rotation", np.eye(3))).T

        det_msg = Detection3DArray(header=hdr)
        for d in res.detections + res.warnings:
            det = Detection3D(header=hdr)
            c_s = R_out @ d.center
            det.bbox.center.position.x, det.bbox.center.position.y, det.bbox.center.position.z = map(float, c_s)
            det.bbox.center.orientation.w = 1.0
            size_s = np.abs(R_out @ d.size)
            det.bbox.size.x, det.bbox.size.y, det.bbox.size.z = map(float, size_s)
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = f"{d.zone}_obstacle" if getattr(d, "kind", "") != "low" else f"{d.zone}_low_obstacle"
            hyp.hypothesis.score = float(d.confidence)
            det.results.append(hyp)
            det.id = str(d.id)
            det_msg.detections.append(det)
        self.pub_det.publish(det_msg)

        if self.get_parameter("publish_markers").get_parameter_value().bool_value:
            self.pub_markers.publish(self.make_markers(hdr, res, R_out))
        if self.get_parameter("publish_corridor_cloud").get_parameter_value().bool_value and res.corridor_idx.size:
            pts = res.xyz if getattr(res, "xyz", None) is not None else frame.xyz
            self.pub_corridor.publish(self.make_cloud(hdr, pts[res.corridor_idx] @ R_out.T.astype(np.float32),
                                                     frame.intensity[res.corridor_idx]))

    def make_markers(self, hdr: Header, res: FrameResult, R_out=None) -> MarkerArray:
        R_out = self.R_sv if R_out is None else R_out
        arr = MarkerArray()
        clear = Marker(header=hdr, ns="resense", id=0, action=Marker.DELETEALL)
        arr.markers.append(clear)
        mid = 1
        for d in res.detections + res.warnings:
            box = Marker(header=hdr, ns="resense", id=mid, type=Marker.CUBE, action=Marker.ADD)
            c_s = R_out @ d.center
            box.pose.position.x, box.pose.position.y, box.pose.position.z = map(float, c_s)
            box.pose.orientation.w = 1.0
            size_s = np.maximum(np.abs(R_out @ d.size), 0.4)
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
                p_s = R_out @ p_v
                line.points.append(Point(x=float(p_s[0]), y=float(p_s[1]), z=float(p_s[2])))
            arr.markers.append(line)
            mid += 1
        status = Marker(header=hdr, ns="resense", id=mid, type=Marker.TEXT_VIEW_FACING, action=Marker.ADD)
        p_s = R_out @ np.array([8.0, 0.0, 3.5])
        status.pose.position.x, status.pose.position.y, status.pose.position.z = map(float, p_s)
        status.pose.orientation.w = 1.0
        status.scale.z = 1.2
        decision = self.decision(res)             # the same word as /resense/decision
        clear = float(getattr(res, "clear_distance", -1.0))
        if res.obstacle:
            status.text = f"STOP: OBSTACLE  {res.nearest_distance:.1f} m"
            status.color.r, status.color.g, status.color.b, status.color.a = 1.0, 0.1, 0.1, 1.0
        elif decision == "FAULT":
            status.text = "FAULT: input not trusted"
            status.color.r, status.color.g, status.color.b, status.color.a = 0.8, 0.2, 0.8, 1.0
        elif decision == "CAUTION":
            status.text = ("CAUTION: object near gauge" if res.warning else "CAUTION: degraded") + f"  clear {clear:.0f} m"
            status.color.r, status.color.g, status.color.b, status.color.a = 1.0, 0.6, 0.0, 1.0
        else:
            status.text = f"GO: path clear {clear:.0f} m"
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
