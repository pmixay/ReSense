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
  pub  /resense/clear_distance          std_msgs/Float32   (v0.6: estimated monitored range in m, capped at the
                                                            nearest detected obstacle; 0 on a fault)
  pub  /resense/health                  diagnostic_msgs/DiagnosticArray (v0.6: input, visibility, track lock,
                                                            latency, mount calibration; OK / WARN / ERROR / STALE)
  pub  /tf_static                       resense_lidar -> <input frame_id>, identity, once per input frame id
  sub  <speed_topic>                    std_msgs/Float32   (optional: train speed in m/s)
  sub  <odom_topic>                     nav_msgs/Odometry  (optional: twist.linear.x is the train speed)

The status JSON carries an extra ``node`` object next to the detector fields:
``{"latency_ms", "fps", "frames", "dropped_frames", "catchup_skipped", "catchup",
"input_period_ms", "ego_speed_mps", "ego_speed_source", "input_topic", "recording"}``
(``recording`` counts the recordings seen, see "Input handling") (``latency_ms`` there is decode +
detect of the same frame, before publishing). ``dropped_frames`` is estimated from gaps in the
input header stamps, whatever the cause (a slow frame makes the node skip the ones that arrived
meanwhile, a backlog is worked through ``catchup_step`` s of recording apart, see "Backlog"; a
frame can also be lost in transport or be missing from the recording itself; the input's
reliability follows the publishers, ``input_reliability``). ``catchup_skipped`` (25.09) is the
part of ``dropped_frames`` the node received and skipped on purpose (the catch-up plan), so
``dropped_frames - catchup_skipped`` never reached the node. ``catchup`` is true while the node
works through a backlog (more than ``catchup_step`` s of recording waiting), false again from the
frame on which it is back on the newest one: ``scripts/check_dry_run.py`` counts drops after the
start-up catch-up from there.

Ego speed (multi-frame accumulation needs it): the ``ego_speed_mps`` parameter wins when >= 0,
else the latest value from ``speed_topic`` / ``odom_topic`` younger than ``speed_timeout``,
else ``None``: the single-frame path (no accumulation; the LiDAR-only speed estimator is off
by default, ``accumulation.estimate_speed``, EXPERIMENTS.md section 1b). The value is handed to
``Detector.process(frame, ego_speed=...)`` when the installed detector accepts it.

Decision (v0.6, the organizers' "can we go / is there an obstacle / how far"): ``STOP`` when a
confirmed obstacle is inside the train envelope, ``FAULT`` when the input cannot be trusted
(too few returns, view blocked, no frame for ``stale_timeout`` s, an exception while
processing), ``CAUTION`` for an advisory object next to the envelope or a degraded health
(track model on its prior, short visibility), else ``GO``. ``CAUTION`` is advisory, not an alarm:
the alarm is ``STOP`` (``/resense/obstacle_detected``). Since 26.09 latency over budget is a
health warning only (``/resense/health``, the status JSON), not ``CAUTION``, unless
``health.latency_affects_decision`` (the parameter file) is true. The node never
dies on a bad frame: the exception is logged, ``FAULT`` published, and after
``max_consecutive_errors`` the detector is reset. The watchdog marks monitoring invalid / health
``STALE`` while input is silent. A previous STOP stays held until a fresh valid non-STOP result;
without a previous STOP the decision is ``FAULT``. Before the first frame it publishes
``FAULT`` / ``NO_INPUT`` after ``startup_grace`` s.

Freshness: ``freshness_mode`` defaults to ``live`` (acquisition header versus system UTC).
Historical playback explicitly selects ``replay`` (DDS publisher UTC; acquisition age unknown).
Source age and Python residence must be <= ``max_result_age`` (0.5 s), future skew <=
``future_tolerance`` (0.05 s). A first/resumed/jumped epoch needs progression before GO.
Queued older frames cannot allow GO; invalid/unknown/stale clocks give FAULT, current clocks
in catch-up give CAUTION, and STOP has priority. JSON ``freshness`` explains validity and
``go_allowed``. Exposed monitored range is zero while invalid; ``detector_clear_distance``
retains the raw estimate. ``snapshot_kind`` separates frames from watchdog/error snapshots.

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
is processed at once. Short backlogs spanning at most ``catchup_step`` are processed in full;
longer live backlogs are worked through ``catchup_step`` s of recording apart (the ones in between
skipped, none older than ``catchup_max_lag`` s behind the newest). On the first backlog of a new
recording (the player's start-up burst, ~0.7 s of recording with ``--read-ahead-queue-size 10``,
the whole recording from a cold disk) the experimental branch preserves every observed
input-period frame by default (``catchup_startup_step: 0``), within the start-up lag allowance
(``catchup_startup_max_lag``). An explicit ``catchup_startup_step: 0.2`` enables the main branch's
5 Hz start-up thinning; its A/B improved latency but skipped some obstacle frames. The start-up
allowance closes when that first catch-up drains, or after 1 s without a catch-up starting; later
stalls retain the normal 5 s limit. ``catchup_step: 0`` keeps the newest-only behavior.

Warm-up (29.09, ``warmup``): before it logs "listening", the node runs the decode and a
throwaway detector on three synthetic frames, so the first real frame does not pay first-call
costs. The node's own detector starts from the first real frame.

The static TF exists so that one RViz / Foxglove layout works for every bag: the organizers'
bags carry different ``frame_id`` values (``hesai_lidar``, ``lidar_livox``); the layouts use
``resense_lidar`` as the fixed frame and the node links it to whatever frame the input has.

Socket buffers (25.09): at start the node reads ``net.core.rmem_max`` (and ``rmem_default``) and
logs one WARN below 32 MiB: at Ubuntu's 212992 a player on CycloneDDS got none of the ~24 MB
360-degree clouds through to the node and all of them at 32 MiB; a stock Fast DDS player got all of
them at 212992 too (25.09, EXPERIMENTS.md section 3b). Never fatal.

Threads (25.09): ``OMP_NUM_THREADS`` / ``OPENBLAS_NUM_THREADS`` / ``MKL_NUM_THREADS`` default to 1
(``resense_ros/__init__.py``, before numpy is imported; an explicit value in the environment
wins), as the image sets them.

Input path (28.09, ``raw_input``, default true): the clouds are taken as serialized bytes and read
by ``resense_ros.fastcloud`` (``data`` stays a view of the bytes) instead of rclpy's message
conversion: 12.5 ms median, 32 ms p95 per 24 MB 360-degree cloud on a 4-vCPU sandbox, paid for
every queued frame of a start-up burst too. The decode is unchanged, so the detector gets the same
arrays bit for bit (``scripts/check_fast_input.py`` on the original recordings). Bytes the parser
rejects go through rclpy's conversion; a message neither can read is logged and dropped.
Publishing (28.09): the decision topics go out first; the RViz markers and the corridor cloud
are built only while something subscribes to them. The ``node`` object also reports
``decode_ms`` and ``detect_ms`` of the frame, ``cpu_cores`` (the node process's CPU time per
wall-clock second over the last ``stats_period``, DDS threads included) and ``rss_peak_mb``.
"""
from __future__ import annotations

import copy
import inspect
import json
import math
import os
import resource
import time
import traceback
from types import SimpleNamespace

import numpy as np
import rclpy
from geometry_msgs.msg import Point, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor, await_or_execute
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

from resense_ros import fastcloud


UNSET = -999.0   # sentinel of the mount_*_deg parameters: keep the value of the parameter file
PROC_NET_CORE = "/proc/sys/net/core"
RMEM_WANT = 33554432   # 32 MiB: with it a CycloneDDS player delivered every 360-degree cloud (25.09)


class SourceInfoExecutor(SingleThreadedExecutor):
    """Humble adapter: preserve RMW metadata for our LiDAR subscriptions only.

    Humble's executor takes (message, metadata) but forwards only the message.
    Keep the original pair for explicitly marked subscriptions. Other callbacks
    retain upstream behavior; unavailable metadata fails closed in replay mode.
    """
    def _take_subscription(self, sub):
        if not getattr(sub, "_resense_with_info", False):
            return super()._take_subscription(sub)
        with sub.handle:
            return sub.handle.take_message(sub.msg_type, sub.raw)

    async def _execute_subscription(self, sub, taken):
        if not getattr(sub, "_resense_with_info", False):
            return await super()._execute_subscription(sub, taken)
        if taken is not None:
            await await_or_execute(sub.callback, *taken)


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
        self.declare_parameter("freshness_mode", "live")  # live acquisition UTC | replay publisher UTC
        self.declare_parameter("max_result_age", 0.5)  # s: source/residence/recording lag limit
        self.declare_parameter("future_tolerance", 0.05)  # s: permitted clock skew into the future
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
        self.declare_parameter("catchup_startup_max_lag", 20.0)  # s: extra allowance for a recording's initial burst
        # --- 29.09 main integration: experimental keeps every input-period frame by default.
        # Explicit 0.2 s enables main's 5 Hz start-up thinning, which lowers start-up latency but
        # has not passed the branch's paired target-coverage acceptance (see P3_SCORE_SYNC_2026-09-28).
        self.declare_parameter("catchup_startup_step", 0.0)
        # --- 29.09: run the decode and a throwaway detector on synthetic frames before listening, so the
        # first real frame does not pay the first-call costs (imports, allocations: +55 ms measured)
        self.declare_parameter("warmup", True)
        # --- v0.6.2: reliability of the input subscription. A 360-degree cloud is ~10 MB, i.e. ~160 UDP
        # fragments; best-effort loses the whole message with any fragment (measured in Docker with
        # `ros2 bag play` of doubleT_obstacle: 5 of 201 frames delivered best-effort, 174+ reliable).
        # auto = match the publishers: reliable when every publisher of the topic is (`ros2 bag play`
        # of the organizers' recordings), best-effort when one is not (a sensor-data driver)
        self.declare_parameter("input_reliability", "auto")   # auto | reliable | best_effort
        # --- 28.09: take the clouds as serialized bytes and read them with resense_ros.fastcloud
        # (rclpy's conversion: 12.5 ms median, 32 ms p95 per 24 MB cloud); false = rclpy's messages
        self.declare_parameter("raw_input", True)

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
        self.raw_input = self.get_parameter("raw_input").get_parameter_value().bool_value
        self.raw_fallbacks = 0          # raw clouds that needed rclpy's conversion (logged once)
        self.catchup_step = self.get_parameter("catchup_step").get_parameter_value().double_value
        self.catchup_max_lag = self.get_parameter("catchup_max_lag").get_parameter_value().double_value
        self.catchup_startup_max_lag = self.get_parameter("catchup_startup_max_lag").get_parameter_value().double_value
        self.catchup_startup_step = max(
            0.0, self.get_parameter("catchup_startup_step").get_parameter_value().double_value)
        self.startup_catchup_active = False
        self.startup_catchup_until = 0.0  # first cloud may arrive alone just before the preload burst
        self.pending = []              # (topic, msg) taken from the input queues, not processed yet, oldest first
        self.arrivals = {}             # message id -> (first Python arrival monotonic, DDS source UTC)
        self.current_arrival = None
        self.current_queue_lag = 0.0
        self.freshness_previous = None  # (header stamp, source UTC, monotonic, UTC) of accepted input
        self.epoch_reason = "epoch_unconfirmed"
        self.stop_latch = None          # small output snapshot; never retains point-cloud arrays
        self.stop_ros = None
        self.last_result_clock = None  # (source UTC, Python arrival monotonic) for watchdog expiry
        self.last_published_valid = False
        self.freshness_mode = self.get_parameter("freshness_mode").get_parameter_value().string_value
        if self.freshness_mode not in ("live", "replay"):
            raise ValueError("freshness_mode must be live or replay")
        self.max_result_age = self.get_parameter("max_result_age").get_parameter_value().double_value
        self.future_tolerance = self.get_parameter("future_tolerance").get_parameter_value().double_value
        if (not math.isfinite(self.max_result_age) or self.max_result_age <= 0
                or not math.isfinite(self.future_tolerance) or self.future_tolerance < 0):
            raise ValueError("freshness age must be positive and future tolerance nonnegative")
        self.pending_last = None       # (topic, frame_id, stamp) of the last frame handed to processing
        self.catchup = None            # [frames processed, max s behind, start time] of the current catch-up
        self.catchup_skipped = 0       # frames skipped since the current catch-up started (its log line)
        self.skipped = []              # ((topic, frame_id), stamp) of skipped frames not yet accounted
        self.frame_in_catchup = False  # the frame being processed is a link of a catch-up (status "catchup")
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
        self.dropped = 0                      # frames not processed, estimated from stamp gaps (any cause)
        self.dropped_skipped = 0              # ... of which the node received and skipped (the catch-up plan)
        self.input_period = 0.1               # s, running estimate of the sensor period
        self.last_stamp = None                # header stamp of the previous processed frame
        self.win_latency = []                 # ms, latencies since the last stats line
        self.win_frames = 0
        self.fps = 0.0
        self.last_latency_ms = 0.0
        self.last_decode_ms = 0.0
        self.last_detect_ms = 0.0
        self.cpu_cores = 0.0                  # node process CPU s per wall s over the last stats period
        self.t_cpu = time.process_time()
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
        if self.get_parameter("warmup").get_parameter_value().bool_value:
            self.warm_up()
        self.get_logger().info("ReSense detector listening on " + ", ".join(self.subs)
                               + (" (+ auto-discovery)" if self.discover_timer else "")
                               + f"; input reliability {self.input_reliability}; per-frame kernels: {_native.status()}"
                               + f"; resense {RESENSE_VERSION}")
        self.check_socket_buffers()

    # ------------------------------------------------------------------
    @staticmethod
    def synthetic_cloud(R_vs: np.ndarray, n_slots: int = 921_600, seed: int = 0):
        """A PointCloud2-shaped cloud in the organizers' 26-byte layout (x, y, z, intensity float32,
        ring uint16, timestamp float64): a straight tunnel - bed, rails, walls, vault - and a box
        on the track 40 m ahead, in the sensor frame of ``R_vs``; two of three slots empty, as in
        the dual-return recordings. Only the warm-up uses it."""
        rng = np.random.default_rng(seed)
        m = n_slots // 3
        x = rng.uniform(2.0, 150.0, m)
        part = rng.integers(0, 5, m)
        y = np.select([part == 0, part == 1, part == 2, part == 3],
                      [rng.uniform(-1.5, 1.5, m), rng.choice([-0.795, 0.795], m), -2.4 + 0 * x, 2.4 + 0 * x],
                      rng.uniform(-2.4, 2.4, m))
        z = np.select([part == 0, part == 1, part >= 2],
                      [-1.25 + 0 * x, -1.075 + 0 * x, rng.uniform(-1.25, 3.5, m)])
        z[part == 4] = 3.5
        box = (x > 40.0) & (x < 40.6) & (np.abs(y) < 0.5)
        z[box] = rng.uniform(-1.2, 0.3, int(box.sum()))
        pts = np.c_[x, y, z] @ R_vs                       # vehicle -> sensor (R_vs rotates sensor -> vehicle)
        dt = np.dtype({"names": ["x", "y", "z", "intensity", "ring", "timestamp"],
                       "formats": ["<f4", "<f4", "<f4", "<f4", "<u2", "<f8"],
                       "offsets": [0, 4, 8, 12, 16, 18], "itemsize": 26})
        arr = np.zeros(n_slots, dt)
        slots = rng.choice(n_slots, m, replace=False)
        for k, name in enumerate("xyz"):
            arr[name][slots] = pts[:, k]
        arr["intensity"][slots] = rng.uniform(0.0, 60.0, m)
        arr["ring"][slots] = rng.integers(0, 128, m)
        fields = [SimpleNamespace(name=nm, offset=off, datatype=dtp, count=1) for nm, off, dtp in
                  (("x", 0, 7), ("y", 4, 7), ("z", 8, 7), ("intensity", 12, 7), ("ring", 16, 4), ("timestamp", 18, 8))]
        return SimpleNamespace(height=1, width=n_slots, fields=fields, is_bigendian=False, point_step=26,
                                     row_step=26 * n_slots, data=memoryview(arr.view(np.uint8)), is_dense=False)

    def warm_up(self) -> None:
        """The decode and a throwaway detector on three synthetic frames, before the first input:
        the first real frame then costs what the next ones do. The node's own detector is not
        touched (its scene and mount calibration start from the first real frame); a failure is
        logged and ignored."""
        t0 = time.perf_counter()
        try:
            cloud = self.synthetic_cloud(self.R_vs)
            scratch = Detector(self.cfg)
            for k in range(3):
                xyz_s, inten, ring, n_raw, n_near = fastcloud.decode(
                    cloud, self.cfg.sensor.min_range, self.cfg.sensor.max_range)
                frame = Frame(xyz=xyz_s @ self.R_vs.T.astype(np.float32), intensity=inten, ring=ring,
                              stamp=0.1 * k, frame_id="warmup", meta={"n_raw": n_raw, "n_near": n_near})
                res = scratch.process(frame)
                json.dumps(res.to_dict())
            self.get_logger().info(f"warm-up: {1e3 * (time.perf_counter() - t0):.0f} ms")
        except Exception as e:  # noqa: BLE001 - the warm-up is an optimisation only
            self.get_logger().warn(f"warm-up skipped: {e!r}")

    @staticmethod
    def socket_buffer_warning(values: dict, profile: bool = True):
        """The WARN line for the kernel's UDP receive-buffer limits, or None when they are fine.

        ``values``: ``rmem_max`` / ``rmem_default`` in bytes (a missing one is not checked);
        ``profile``: the image's Fast DDS profile is in use (``FASTRTPS_DEFAULT_PROFILES_FILE``),
        which asks for a 32 MiB receive buffer explicitly, so only ``rmem_max`` caps it; without it
        Fast DDS keeps the kernel default, ``rmem_default``."""
        keys = ("rmem_max",) if profile else ("rmem_max", "rmem_default")
        if not any(values.get(k) is not None and values[k] < RMEM_WANT for k in keys):
            return None
        now = ", ".join(f"net.core.{k} = {values[k]}" for k in ("rmem_max", "rmem_default") if values.get(k) is not None)
        return (f"{now}: below 32 MiB. A bag player may then deliver few or none of the ~24 MB "
                "360-degree clouds to this node (a CycloneDDS player; stock Fast DDS was not affected; the "
                "120-degree clouds arrive). Fix on the host, before playing: sudo sysctl -w "
                f"net.core.rmem_max={RMEM_WANT} net.core.rmem_default={RMEM_WANT}")

    def check_socket_buffers(self):
        """Read the kernel's receive-buffer limits and log one WARN when a host player might not
        deliver the 360-degree clouds (EXPERIMENTS.md section 3b, 25.09). Never fails."""
        values = {}
        for key in ("rmem_max", "rmem_default"):
            try:
                with open(os.path.join(PROC_NET_CORE, key), encoding="ascii") as fh:
                    values[key] = int(fh.read().split()[0])
            except (OSError, ValueError, IndexError):
                pass
        try:
            msg = self.socket_buffer_warning(values, bool(os.environ.get("FASTRTPS_DEFAULT_PROFILES_FILE")))
            if msg:
                self.get_logger().warn(msg)
        except Exception:  # noqa: BLE001 - a diagnostic must never stop the node
            pass
        return values

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
            PointCloud2, topic, lambda msg, info=None, t=topic: self.on_cloud(msg, t, info),
            self.input_qos(reliability), raw=self.raw_input)
        self.subs[topic]._resense_with_info = True

    @staticmethod
    def make_header(sec: int, nanosec: int, frame_id: str) -> Header:
        """A real ``std_msgs/Header`` for a cloud read from its bytes: it is copied into the
        published messages."""
        from builtin_interfaces.msg import Time
        return Header(stamp=Time(sec=sec, nanosec=nanosec), frame_id=frame_id)

    def as_cloud(self, msg):
        """The cloud the node processes: a raw subscription's bytes read by ``fastcloud``
        (rclpy's own conversion if they are not a plain-CDR PointCloud2), anything else as is.
        None for bytes neither can read: the frame is dropped (logged), the node keeps running
        and the watchdog reports the silence."""
        if not isinstance(msg, (bytes, bytearray, memoryview)):
            return msg
        try:
            return fastcloud.parse_pointcloud2(msg, self.make_header)
        except ValueError as e:
            self.raw_fallbacks += 1
            if self.raw_fallbacks == 1:
                self.get_logger().warn(f"input cloud not read from its bytes ({e}); using rclpy's conversion")
        try:
            from rclpy.serialization import deserialize_message
            return deserialize_message(bytes(msg), PointCloud2)
        except Exception as e:  # noqa: BLE001 - an unreadable message must not take the node down
            self.get_logger().error(f"input cloud dropped: neither read from its bytes nor converted ({e!r})")
            return None

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
    def _account_frame(self, stamp: float, key=None) -> None:
        """Estimate dropped frames from the gap between consecutive input stamps; the frames of
        the gap that the node received and skipped itself (``prune``) also go to
        ``dropped_skipped``. ``key``: (topic, frame_id) of the frame, as in ``skipped``."""
        last, skipped = self.last_stamp, 0
        if self.skipped:
            keep = []
            for k, s in self.skipped:
                if k == key and s < stamp:           # accounted now (or older than the input's start)
                    skipped += int(last is not None and s > last)
                else:
                    keep.append((k, s))
            self.skipped = keep
        if last is not None:
            gap = stamp - last
            if 0.0 < gap < 1.6 * self.input_period:
                # a regular gap: refine the period estimate (EMA)
                self.input_period = 0.9 * self.input_period + 0.1 * gap
            elif gap >= 1.6 * self.input_period:
                missing = int(round(gap / self.input_period)) - 1
                self.dropped += missing
                self.dropped_skipped += min(missing, skipped)
            # gap <= 0: a bag loop / restart, not a drop
        self.last_stamp = stamp

    def on_stats(self) -> None:
        now = time.perf_counter()
        dt = now - self.t_stats
        self.t_stats = now
        self.fps = self.win_frames / dt if dt > 0 else 0.0
        cpu = time.process_time()
        self.cpu_cores = (cpu - self.t_cpu) / dt if dt > 0 else 0.0
        self.t_cpu = cpu
        self.pub_fps.publish(Float32(data=float(self.fps)))
        if self.win_frames:
            lat = np.asarray(self.win_latency)
            self.get_logger().info(
                f"frame {self.n_frames}: {self.last_status}; {self.fps:.1f} fps; "
                f"latency mean {lat.mean():.0f} / p95 {np.percentile(lat, 95):.0f} / max {lat.max():.0f} ms; "
                f"input period {self.input_period * 1e3:.0f} ms; dropped {self.dropped} "
                f"({self.dropped_skipped} skipped by the catch-up); CPU {self.cpu_cores:.2f} cores")
        self.win_latency.clear()
        self.win_frames = 0

    def node_stats(self) -> dict:
        return {"latency_ms": round(self.last_latency_ms, 2), "fps": round(self.fps, 2),
                "frames": self.n_frames, "dropped_frames": self.dropped,
                "catchup_skipped": self.dropped_skipped, "catchup": bool(self.frame_in_catchup),
                "input_period_ms": round(self.input_period * 1e3, 1),
                "ego_speed_mps": None if self.last_speed is None else round(float(self.last_speed), 2),
                "ego_speed_source": self.last_speed_source,
                "input_topic": self.active_topic, "recording": self.n_inputs,
                "decode_ms": round(self.last_decode_ms, 2), "detect_ms": round(self.last_detect_ms, 2),
                "cpu_cores": round(self.cpu_cores, 2),
                "rss_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)}

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
        self.freshness_previous = None
        self.startup_catchup_active = True
        self.startup_catchup_until = time.perf_counter() + 1.0
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
    def catchup_plan(stamps, last, step: float, max_lag: float, thin_short: bool = False):
        """Indices of the waiting frames to process, oldest first; the others are skipped.

        ``stamps``: the header stamps of the waiting frames of one input, in arrival order and
        increasing; ``last``: the stamp of the input's last processed frame (None at its start).
        One frame waiting: that frame. A backlog spanning at most ``step``: every waiting frame,
        because a brief scheduler delay does not require skipping sensor frames. Longer backlogs:
        a chain through them that
        steps at most ``step`` s of recording - each link the latest frame within ``step`` of the
        previous one, the next frame when none is - from ``last`` (from the first frame at the
        start of an input) to the newest frame; frames older than the newest by more than
        ``max_lag`` s are dropped first. ``step`` <= 0: the newest frame only. ``thin_short``
        (a recording's start-up catch-up): a short backlog is chained too, so a node slower than
        the input keeps ``step`` apart instead of lagging further behind frame by frame."""
        n = len(stamps)
        if n <= 1:
            return list(range(n))
        if step <= 0:
            return [n - 1]
        i = 0
        if max_lag > 0:
            while i < n - 1 and stamps[i] < stamps[-1] - max_lag:
                i += 1
        if not thin_short and stamps[-1] - stamps[i] <= step + 1e-6:
            return list(range(i, n))
        plan, cur = [], last
        while i < n:
            j = i
            while cur is not None and j + 1 < n and stamps[j + 1] <= cur + step + 1e-6:
                j += 1
            plan.append(j)
            cur, i = stamps[j], j + 1
        return plan

    def remember_arrival(self, msg, info=None):
        source = info.get("source_timestamp") if isinstance(info, dict) else getattr(info, "source_timestamp", None)
        try:
            source = float(source) * 1e-9
            if not math.isfinite(source) or source <= 0:
                source = None
        except (TypeError, ValueError, OverflowError):
            source = None
        self.arrivals[id(msg)] = (time.perf_counter(), source)

    def on_cloud(self, msg: PointCloud2, topic: str = "", info=None) -> None:
        """Input callback: the frame joins the ones already waiting behind it, then the next one
        is processed (``catchup_step``)."""
        msg = self.as_cloud(msg)
        if msg is None:
            return
        self.remember_arrival(msg, info)
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
                cloud = self.as_cloud(got[0])
                if cloud is None:
                    continue
                self.remember_arrival(cloud, got[1])
                self.pending.append((topic, cloud))
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
        # A whole-recording cold-start burst otherwise keeps moving the 5 s cutoff ahead of
        # processing. Its artificial 1+ s gaps reset the scene before a track can confirm.
        # The extra allowance belongs only to a new recording and its first catch-up. A
        # one-second window also catches a first cloud delivered just ahead of that burst.
        if (self.startup_catchup_active and self.catchup is None
                and time.perf_counter() >= self.startup_catchup_until):
            self.startup_catchup_active = False
        max_lag = self.catchup_max_lag
        if (last is None or self.startup_catchup_active) and 0 < max_lag < self.catchup_startup_max_lag:
            max_lag = self.catchup_startup_max_lag
        step = self.catchup_step
        startup = last is None or self.startup_catchup_active
        if step > 0 and startup:
            # Preserve the observed input period unless startup thinning was explicitly enabled.
            # The running period may still describe a previous recording with a different rate.
            observed = min((b - a for a, b in zip(stamps, stamps[1:]) if b > a),
                           default=self.input_period)
            step = min(step, max(min(self.input_period, observed), self.catchup_startup_step))
        plan = self.catchup_plan(stamps, last, step, max_lag,
                                 thin_short=startup and self.catchup_startup_step > 0)
        if len(plan) < n:
            run, self.pending = self.pending[:n], self.pending[n:]
            self.pending[:0] = [run[i] for i in plan]
            self.catchup_skipped += n - len(plan)
            key, kept = (topic0, m0.header.frame_id), set(plan)
            self.skipped.extend((key, stamps[i]) for i in range(n) if i not in kept)
            for i in range(n):
                if i not in kept:
                    self.arrivals.pop(id(run[i][1]), None)
            if len(self.skipped) > 4 * self.qos_depth + 100:     # entries of an input that never came
                del self.skipped[:len(self.skipped) - 4 * self.qos_depth - 100]
        return [stamps[i] for i in plan]

    def process_next(self) -> None:
        """Process one waiting frame: the only one, or the next link of the catch-up chain."""
        if not self.pending:
            return
        stamps = self.prune()
        self.track_catchup(stamps[-1] - stamps[0], len(stamps))
        topic, msg = self.pending.pop(0)
        self.current_queue_lag = max(0.0, stamps[-1] - stamps[0])
        self.current_arrival = self.arrivals.pop(id(msg), None)
        try:
            self.process_cloud(msg, topic)
        finally:
            self.current_arrival = None
            self.frame_in_catchup = False
            if topic == self.active_topic:
                self.pending_last = (topic, msg.header.frame_id, self._stamp(msg))
            if self.pending:
                self.pending_gc.trigger()

    def track_catchup(self, behind: float, left: int) -> None:
        """Log a catch-up - more than ``catchup_step`` s of recording waiting - when it starts and
        when the node is back on the newest frame (``left``: frames of the chain, this one included).
        Sets ``frame_in_catchup`` (status ``node.catchup``) for the frames processed while behind;
        the frame that brings the node back on the newest one is not."""
        self.frame_in_catchup = False
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
            self.startup_catchup_active = False
        else:
            self.frame_in_catchup = True

    def process_cloud(self, msg: PointCloud2, topic: str = "") -> None:
        if not self.check_continuity(topic, msg):
            return
        self.send_static_tf(msg.header.frame_id)
        t0 = time.perf_counter()
        self.begin_freshness(msg, t0)
        self.last_frame_wall = t0
        try:
            xyz_s, inten, ring, n_raw, n_near = fastcloud.decode(
                fastcloud.packed(msg), self.cfg.sensor.min_range, self.cfg.sensor.max_range)
            xyz_v = xyz_s @ self.R_vs.T.astype(np.float32)
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            # a cloud without a ring field has unknown channels, not channel 0 for every point
            frame = Frame(xyz=xyz_v, intensity=inten, ring=ring if fastcloud.has_field(msg, "ring") else None,
                          stamp=stamp, frame_id=msg.header.frame_id, meta={"n_raw": n_raw, "n_near": n_near})
            self._account_frame(stamp, (topic, msg.header.frame_id))
            self.last_speed, self.last_speed_source = self.ego_speed()
            t_detect = time.perf_counter()
            res = (self.detector.process(frame, ego_speed=self.last_speed) if self._process_takes_speed
                   else self.detector.process(frame))
        except Exception as e:  # noqa: BLE001 - a bad frame must never take the node down
            self.on_processing_error(msg.header, e)
            return
        self.consecutive_errors = 0
        t_done = time.perf_counter()
        self.last_latency_ms = (t_done - t0) * 1e3   # decode + detect, goes into the status JSON
        self.last_decode_ms = (t_detect - t0) * 1e3
        self.last_detect_ms = (t_done - t_detect) * 1e3
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
        self.last_status += (f"; axis y={res.track.center:+.2f} "
                             f"R={'inf' if abs(res.track.curvature) < 1e-6 else '%.0f' % (1 / res.track.curvature)}")

    def begin_freshness(self, msg, now):
        """Require progression within each clock/input epoch, including after silence."""
        stamp, wall = self._stamp(msg), time.time()
        source = stamp if self.freshness_mode == "live" else (
            self.current_arrival[1] if self.current_arrival is not None else None)
        previous = self.freshness_previous
        reason = "epoch_unconfirmed"
        if previous is not None:
            ph, ps, pm, pw = previous
            if self.last_frame_wall is not None and now - self.last_frame_wall > self.max_result_age:
                reason = "resumed_after_silence"
            elif abs((wall - pw) - (now - pm)) > self.future_tolerance:
                reason = "system_clock_jump"
            elif stamp <= ph:
                reason = "header_not_progressing"
            elif stamp - ph > self.get_parameter("hole_reset_gap").get_parameter_value().double_value:
                reason = "header_jump"
            elif source is None or ps is None or source <= 0 or ps <= 0:
                reason = "epoch_unconfirmed"
            elif source <= ps:
                reason = "source_not_progressing"
            else:
                reason = ""
        self.epoch_reason = reason
        self.freshness_previous = (stamp, source, now, wall)

    def result_freshness(self, res):
        now, wall = time.perf_counter(), time.time()
        arrival = self.current_arrival
        source = self.freshness_previous[1] if self.freshness_previous is not None else None
        age = wall - source if source is not None and math.isfinite(source) and source > 0 else None
        residence = now - arrival[0] if arrival is not None else None
        reason = ""
        clock_jump = (self.freshness_previous is not None and
                      abs((wall - self.freshness_previous[3]) -
                          (now - self.freshness_previous[2])) > self.future_tolerance)
        if clock_jump:
            reason = "system_clock_jump"
        elif age is None:
            reason = "source_clock_unknown"
        elif age < -self.future_tolerance:
            reason = "source_clock_future"
        elif age > self.max_result_age:
            reason = "source_stale"
        elif residence is None or not math.isfinite(residence) or residence < 0:
            reason = "residence_unknown"
        elif residence > self.max_result_age:
            reason = "residence_stale"
        elif self.current_queue_lag > self.max_result_age:
            reason = "queue_stale"
        elif self.epoch_reason:
            reason = self.epoch_reason
        elif (getattr(res, "health", {}) or {}).get("level") == "error":
            reason = "detector_error"
        elif self.frame_in_catchup or self.current_queue_lag > 1e-6:
            reason = "catchup"
        valid = not reason
        return {"mode": self.freshness_mode, "evaluated_at_utc_s": wall,
                "max_result_age_s": self.max_result_age, "future_tolerance_s": self.future_tolerance,
                "clock_reference": "acquisition_utc" if self.freshness_mode == "live" else "publisher_utc",
                "source_age_s": age, "acquisition_age_s": age if self.freshness_mode == "live" else None,
                "publication_age_s": age if self.freshness_mode == "replay" else None,
                "residence_age_s": residence, "queue_lag_s": self.current_queue_lag,
                "valid": valid, "reason": reason or "current", "go_allowed": False}

    # ------------------------------------------------------------------
    def on_processing_error(self, header: Header, err: Exception) -> None:
        """Guard: log, publish FAULT, and reset the detector after repeated failures."""
        self.freshness_previous = None
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
        """Invalidate monitoring while preserving a previously detected STOP."""
        self.last_published_valid = False
        self.freshness_previous = None
        held = self.stop_latch is not None
        decision = "STOP" if held else "FAULT"
        distance = self.stop_latch["nearest_distance"] if held else None
        self.pub_decision.publish(String(data=decision))
        self.pub_clear.publish(Float32(data=0.0))
        self.pub_flag.publish(Bool(data=held))
        self.pub_warn.publish(Bool(data=False))
        self.pub_dist.publish(Float32(data=float(distance) if distance is not None else -1.0))
        arr = DiagnosticArray(header=Header(stamp=self.get_clock().now().to_msg(), frame_id=header.frame_id))
        diag_level = (DiagnosticStatus.STALE if level_name == "STALE" else DiagnosticStatus.ERROR)
        st = DiagnosticStatus(level=diag_level, name="resense/detector", message=message,
                              hardware_id=header.frame_id or "lidar")
        st.values.append(KeyValue(key="state", value=level_name))
        arr.status.append(st)
        self.pub_health.publish(arr)

        # Keep the status stream useful to headless consumers as well.  A
        # watchdog/error snapshot is not a frame from a recording. snapshot_kind
        # identifies it and there is no ``node`` object; tools must not count it as a
        # zero-latency frame or include it in per-recording criteria.
        try:
            stamp = float(header.stamp.sec) + float(header.stamp.nanosec) * 1e-9
        except (AttributeError, TypeError, ValueError):
            stamp = 0.0
        fault_status = {
            "stamp": stamp,
            "obstacle": held,
            "warning": False,
            "nearest_distance": distance,
            "detections": self.stop_latch["detections"] if held else [],
            "warnings": [],
            "n_candidates": 0,
            "n_points": 0,
            "n_corridor": 0,
            "timing_ms": {},
            "health": {"level": "error", "messages": [message]},
            "mount": {},
            "clear_distance": 0.0,
            "decision": decision,
            "detector_clear_distance": None,
            "stop_held": held,
            "snapshot_kind": "processing_error" if level_name == "ERROR" else "watchdog",
            "freshness": {"mode": self.freshness_mode, "evaluated_at_utc_s": time.time(),
                          "max_result_age_s": self.max_result_age, "future_tolerance_s": self.future_tolerance,
                          "clock_reference": "acquisition_utc" if self.freshness_mode == "live" else "publisher_utc",
                          "valid": False, "reason": level_name.lower(),
                          "go_allowed": False, "source_age_s": None, "acquisition_age_s": None,
                          "publication_age_s": None, "residence_age_s": None, "queue_lag_s": None},
        }
        if held:
            fault_status["stop_source_stamp"] = self.stop_latch["stamp"]
            fault_status["stop_source_frame_id"] = self.stop_latch["frame_id"]
        self.pub_status.publish(String(data=json.dumps(fault_status)))
        self.pub_det.publish(self.stop_ros if held and self.stop_ros is not None else Detection3DArray(header=header))
        if self.get_parameter("publish_markers").get_parameter_value().bool_value:
            clear = Marker(header=header, ns="resense", id=0, action=Marker.DELETEALL)
            markers = [clear]
            if held:
                label = Marker(header=header, ns="resense", id=1, type=Marker.TEXT_VIEW_FACING, action=Marker.ADD)
                label.pose.orientation.w = 1.0
                label.scale.z = 1.2
                label.color.r, label.color.a = 1.0, 1.0
                label.text = "STOP HELD: previous obstacle; monitoring invalid"
                markers.append(label)
            self.pub_markers.publish(MarkerArray(markers=markers))
        self.last_status = decision + ": " + message

    def on_watchdog(self) -> None:
        """Guard: silent input -> invalid monitoring at 2 Hz; preserve a held STOP;
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
        source_expired = False
        if self.last_result_clock is not None:
            source, arrival = self.last_result_clock
            age = time.time() - source if source is not None else None
            source_expired = (age is None or age > self.max_result_age or age < -self.future_tolerance
                              or arrival is None or now - arrival > self.max_result_age)
        if (silent > timeout or source_expired) and (self.last_published_valid or now - self.last_stale_pub > 0.5):
            self.last_stale_pub = now
            message = (f"last result expired (> {self.max_result_age:.1f} s source/residence age): path not monitored"
                       if source_expired else
                       f"no LiDAR frame for {silent:.1f} s (> {timeout:.1f} s): path not monitored")
            self.publish_fault(Header(frame_id=self.active_frame_id or ""), message, "STALE")

    @staticmethod
    def decision(res: FrameResult) -> str:
        """STOP > FAULT (health ``level`` error) > CAUTION (an advisory object, or a warning in
        the health ``decision_level``) > GO. ``decision_level`` (26.09) is ``level`` without the
        latency warning unless ``health.latency_affects_decision``; a result without it (older
        core) uses ``level``."""
        h = getattr(res, "health", {}) or {}
        level = h.get("level", "ok")
        if res.obstacle:
            return "STOP"
        if level == "error":
            return "FAULT"
        if res.warning or h.get("decision_level", level) == "warn":
            return "CAUTION"
        return "GO"

    def health_msg(self, hdr: Header, res: FrameResult) -> DiagnosticArray:
        h = getattr(res, "health", {}) or {}
        lv = {"ok": DiagnosticStatus.OK, "warn": DiagnosticStatus.WARN, "error": DiagnosticStatus.ERROR}
        st = DiagnosticStatus(level=lv.get(h.get("level", "ok"), DiagnosticStatus.OK), name="resense/detector",
                              message="; ".join(h.get("messages", [])) or "ok", hardware_id=hdr.frame_id or "lidar")
        for k in ("points", "near_fraction", "blocked_sectors", "visibility", "rail_lock", "latency_p95_ms",
                  "monitored_range", "clear_distance", "decision_level", "freshness_valid", "freshness_reason"):
            if k in h:
                st.values.append(KeyValue(key=k, value=str(h[k])))
        m = getattr(res, "mount", {}) or {}
        for k in ("status", "orientation", "roll_deg", "pitch_deg", "yaw_deg", "height", "drift_deg"):
            if k in m:
                st.values.append(KeyValue(key=f"mount_{k}", value=str(m[k])))
        st.values.append(KeyValue(key="fps", value=f"{self.fps:.1f}"))
        st.values.append(KeyValue(key="dropped_frames", value=str(self.dropped)))
        st.values.append(KeyValue(key="catchup_skipped", value=str(self.dropped_skipped)))
        return DiagnosticArray(header=hdr, status=[st])

    # ------------------------------------------------------------------
    def publish(self, header: Header, frame: Frame, res: FrameResult) -> None:
        out_frame = self.get_parameter("output_frame").get_parameter_value().string_value or header.frame_id
        hdr = Header(stamp=header.stamp, frame_id=out_frame)
        freshness = self.result_freshness(res)
        raw_range = float(getattr(res, "clear_distance", 0.0))
        raw_obstacle = bool(res.obstacle)
        status = res.to_dict()
        if raw_obstacle:
            self.stop_latch = {"nearest_distance": res.nearest_distance, "detections": status["detections"],
                               "stamp": status["stamp"], "frame_id": header.frame_id}
        elif freshness["valid"]:
            self.stop_latch, self.stop_ros = None, None
        held = not raw_obstacle and self.stop_latch is not None
        # Do not mutate the detector's FrameResult or health dictionary.
        res = copy.copy(res)
        res.health = copy.deepcopy(getattr(res, "health", {}) or {})
        if not freshness["valid"]:
            level = "warn" if freshness["reason"] == "catchup" else "error"
            res.health.update(level=level, decision_level=level)
            res.health.setdefault("messages", []).append("freshness: " + freshness["reason"])
            res.clear_distance = 0.0
            res.health["clear_distance"] = 0.0
            res.health["monitored_range"] = 0.0
        res.health.update(freshness_valid=freshness["valid"], freshness_reason=freshness["reason"])
        if held:
            res.obstacle, res.nearest_distance = True, self.stop_latch["nearest_distance"]
            # Old boxes keep their original header through stop_ros; never transform them
            # using a later recording's mount or frame.
            res.detections = []
            status.update(obstacle=True, nearest_distance=res.nearest_distance,
                          detections=self.stop_latch["detections"],
                          stop_source_stamp=self.stop_latch["stamp"],
                          stop_source_frame_id=self.stop_latch["frame_id"])
        decision = self.decision(res)
        freshness["go_allowed"] = freshness["valid"] and decision == "GO"
        # the answer first (28.09): flag, distance and decision before the JSON and the visualisation
        self.pub_flag.publish(Bool(data=bool(res.obstacle)))
        self.pub_dist.publish(Float32(data=float(res.nearest_distance) if res.nearest_distance is not None else -1.0))
        self.pub_decision.publish(String(data=decision))
        self.pub_clear.publish(Float32(data=float(res.clear_distance)))
        self.pub_warn.publish(Bool(data=bool(res.warning)))
        self.last_published_valid = freshness["valid"]
        self.last_result_clock = (self.freshness_previous[1] if self.freshness_previous else None,
                                  self.current_arrival[0] if self.current_arrival else None)
        self.last_status = decision + (f" at {res.nearest_distance:.1f} m" if res.obstacle else "")
        self.last_status += "; freshness " + freshness["reason"]
        status.update(node=self.node_stats(), decision=decision, snapshot_kind="frame", freshness=freshness,
                      stop_held=held, detector_obstacle=raw_obstacle, detector_clear_distance=raw_range,
                      clear_distance=float(res.clear_distance), health=res.health)
        self.pub_status.publish(String(data=json.dumps(status)))
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
        if raw_obstacle:
            self.stop_ros = det_msg
        self.pub_det.publish(self.stop_ros if held and self.stop_ros is not None else det_msg)

        if (self.get_parameter("publish_markers").get_parameter_value().bool_value
                and self.subscribed(self.pub_markers)):
            markers = self.make_markers(hdr, res, R_out)
            if held:
                markers.markers[-1].text = "STOP HELD: previous obstacle; monitoring invalid"
            self.pub_markers.publish(markers)
        if (self.get_parameter("publish_corridor_cloud").get_parameter_value().bool_value and res.corridor_idx.size
                and self.subscribed(self.pub_corridor)):
            pts = res.xyz if getattr(res, "xyz", None) is not None else frame.xyz
            self.pub_corridor.publish(self.make_cloud(hdr, pts[res.corridor_idx] @ R_out.T.astype(np.float32),
                                                     frame.intensity[res.corridor_idx]))

    @staticmethod
    def subscribed(pub) -> bool:
        """Whether anything subscribes to ``pub`` (RViz, Foxglove, a recorder); unknown = yes. The
        markers and the corridor cloud are built only then (together ~8 ms per 360-degree frame)."""
        count = getattr(pub, "get_subscription_count", None)
        if count is None:
            return True
        try:
            return count() > 0
        except Exception:  # noqa: BLE001 - a graph query must never cost a frame
            return True

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
        axis = np.stack([xs, np.broadcast_to(np.asarray(res.track.center_y(xs), dtype=float), xs.shape),
                         np.broadcast_to(np.asarray(res.track.rail_z(xs), dtype=float) + 1.0, xs.shape)], axis=1)
        for k, side in enumerate((half, -half)):
            line = Marker(header=hdr, ns="resense", id=mid, type=Marker.LINE_STRIP, action=Marker.ADD)
            line.scale.x = 0.08
            if (getattr(res, "health", {}) or {}).get("freshness_valid") is False:
                line.color.r, line.color.g, line.color.b, line.color.a = 0.5, 0.5, 0.5, 0.4
            else:
                line.color.r, line.color.g, line.color.b, line.color.a = 0.2, 1.0, 0.3, 0.8
            line.pose.orientation.w = 1.0
            edge = (axis + np.array([0.0, side, 0.0])) @ R_out.T      # the whole edge at once
            line.points = [Point(x=a, y=b, z=c) for a, b, c in edge.tolist()]
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
            status.text = (("CAUTION: object near gauge" if res.warning else "CAUTION: degraded")
                           + f"  monitored {clear:.0f} m (estimate)")
            status.color.r, status.color.g, status.color.b, status.color.a = 1.0, 0.6, 0.0, 1.0
        else:
            status.text = f"GO: NO OBSTACLE DETECTED  monitored {clear:.0f} m (estimate)"
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
    executor = SourceInfoExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        # Ctrl+C: rclpy's signal handler has already shut the context down, so a plain
        # rclpy.shutdown() raised "rcl_shutdown already called" and launch reported exit code 1
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
