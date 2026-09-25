"""The ROS 2 node's own logic without ROS: decision, guards, watchdog, mount parameters, and the
mapping of detections back into the sensor frame after the mount calibration.

``rclpy`` and the message packages exist only in the Docker image (CI plays a synthetic bag
through the real node there). Here they are replaced by minimal stand-ins - a message is an
object whose unknown attributes are created on first access, a publisher records what it is
given - so the node module is imported unchanged and driven with ``PointCloud2``-shaped
messages built from the synthetic ray-cast tunnel.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import time
import types
from collections import defaultdict
from pathlib import Path

import numpy as np
import pytest

NODE_PKG = Path(__file__).resolve().parents[1] / "ros2_ws" / "src" / "resense_ros"


# ---------------------------------------------------------------------------
# stand-ins for rclpy and the message packages
# ---------------------------------------------------------------------------

class _Msg:
    _lists: tuple = ()

    def __init__(self, **kw):
        for n in self._lists:
            object.__setattr__(self, n, [])
        for k, v in kw.items():
            setattr(self, k, v)

    def __getattr__(self, name):          # nested fields (header.stamp.sec, bbox.center.position.x, ...)
        if name.startswith("__"):
            raise AttributeError(name)
        v = _Msg()
        object.__setattr__(self, name, v)
        return v


def _msg(name, lists=(), **consts):
    return type(name, (_Msg,), {"_lists": tuple(lists), **consts})


class _Param:
    def __init__(self, v):
        self.v = v

    def get_parameter_value(self):
        v = self.v
        num = isinstance(v, (int, float)) and not isinstance(v, bool)
        return types.SimpleNamespace(string_value=v if isinstance(v, str) else "",
                                     bool_value=v if isinstance(v, bool) else False,
                                     double_value=float(v) if num else 0.0,
                                     integer_value=int(v) if num else 0)


class _Logger:
    def __init__(self):
        self.lines = []

    def info(self, s):
        self.lines.append(("info", s))

    def warn(self, s):
        self.lines.append(("warn", s))

    def error(self, s):
        self.lines.append(("error", s))


class _Node:
    overrides: dict = {}

    def __init__(self, name):
        self._params = {}
        self.published = defaultdict(list)
        self._logger = _Logger()

    def declare_parameter(self, name, value):
        self._params[name] = self.overrides.get(name, value)

    def get_parameter(self, name):
        return _Param(self._params[name])

    def create_subscription(self, msg_type, topic, cb, qos):
        return types.SimpleNamespace(topic=topic, cb=cb, qos=qos)

    def destroy_subscription(self, sub):
        pass

    def create_publisher(self, msg_type, topic, depth):
        node = self
        return types.SimpleNamespace(publish=lambda m: node.published[topic].append(m))

    def create_timer(self, period, cb):
        return types.SimpleNamespace(cancel=lambda: None, cb=cb)

    def create_guard_condition(self, cb):
        gc = types.SimpleNamespace(cb=cb, triggered=0)
        gc.trigger = lambda: setattr(gc, "triggered", gc.triggered + 1)
        return gc

    def get_logger(self):
        return self._logger

    def get_clock(self):
        return types.SimpleNamespace(now=lambda: types.SimpleNamespace(to_msg=lambda: _Msg(sec=0, nanosec=0)))

    def get_topic_names_and_types(self):
        return []

    def get_publishers_info_by_topic(self, topic):
        return []


def _stub_modules():
    m = {}

    def mod(name, **attrs):
        md = types.ModuleType(name)
        md.__dict__.update(attrs)
        m[name] = md
        return md

    rclpy = mod("rclpy", init=lambda args=None: None, spin=lambda n: None, shutdown=lambda: None)
    rclpy.node = mod("rclpy.node", Node=_Node)
    rclpy.qos = mod("rclpy.qos", QoSProfile=lambda **kw: kw,
                    QoSReliabilityPolicy=types.SimpleNamespace(RELIABLE=1, BEST_EFFORT=2),
                    QoSHistoryPolicy=types.SimpleNamespace(KEEP_LAST=1))
    mod("geometry_msgs"), mod("geometry_msgs.msg", Point=_msg("Point"), TransformStamped=_msg("TransformStamped"))
    mod("nav_msgs"), mod("nav_msgs.msg", Odometry=_msg("Odometry"))
    mod("sensor_msgs"), mod("sensor_msgs.msg", PointCloud2=_msg("PointCloud2", ["fields"]),
                            PointField=_msg("PointField", FLOAT32=7, UINT16=4))
    mod("std_msgs"), mod("std_msgs.msg", Bool=_msg("Bool"), Float32=_msg("Float32"), String=_msg("String"),
                         Header=_msg("Header"))
    mod("diagnostic_msgs"), mod("diagnostic_msgs.msg", DiagnosticArray=_msg("DiagnosticArray", ["status"]),
                                DiagnosticStatus=_msg("DiagnosticStatus", ["values"], OK=0, WARN=1, ERROR=2, STALE=3),
                                KeyValue=_msg("KeyValue"))
    mod("vision_msgs"), mod("vision_msgs.msg", Detection3D=_msg("Detection3D", ["results"]),
                            Detection3DArray=_msg("Detection3DArray", ["detections"]),
                            ObjectHypothesisWithPose=_msg("ObjectHypothesisWithPose"))
    mod("visualization_msgs"), mod("visualization_msgs.msg", Marker=_msg("Marker", ["points"], ADD=0, CUBE=1,
                                                                        LINE_STRIP=4, TEXT_VIEW_FACING=9, DELETEALL=3),
                                   MarkerArray=_msg("MarkerArray", ["markers"]))
    mod("tf2_ros", StaticTransformBroadcaster=lambda node: types.SimpleNamespace(sendTransform=lambda t: None))
    return m


@pytest.fixture
def node_cls(monkeypatch):
    """The real ``DetectorNode`` class, imported against the stand-ins; ``overrides`` set node parameters."""
    for name, md in _stub_modules().items():
        monkeypatch.setitem(sys.modules, name, md)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        monkeypatch.setenv(var, os.environ.get(var, "1"))     # the package sets them; undone after the test
    monkeypatch.syspath_prepend(str(NODE_PKG))
    for name in [n for n in sys.modules if n.startswith("resense_ros")]:
        monkeypatch.delitem(sys.modules, name)
    mod = importlib.import_module("resense_ros.detector_node")
    monkeypatch.setattr(_Node, "overrides", {})
    yield mod.DetectorNode
    for name in [n for n in sys.modules if n.startswith("resense_ros")]:
        sys.modules.pop(name, None)


def _cloud(xyz_vehicle: np.ndarray, stamp: float, M: np.ndarray = None, frame_id: str = "hesai_lidar"):
    """PointCloud2-shaped message of a vehicle-frame cloud as the default-mounted sensor sees it
    (``M``: an extra mount rotation, p_seen = M @ p_true)."""
    from resense.config import SensorConfig
    from resense.frame import axis_matrix
    R = axis_matrix(SensorConfig())
    p = xyz_vehicle if M is None else xyz_vehicle @ M.T
    xyz_s = (p @ R).astype(np.float32)
    dt = np.dtype({"names": ["x", "y", "z", "intensity", "ring"], "formats": ["f4", "f4", "f4", "f4", "u2"],
                   "offsets": [0, 4, 8, 12, 16], "itemsize": 18})
    data = np.zeros(xyz_s.shape[0], dt)
    data["x"], data["y"], data["z"] = xyz_s.T
    data["intensity"] = 20.0
    fields = [_Msg(name=n, offset=o, datatype=t, count=1)
              for n, o, t in (("x", 0, 7), ("y", 4, 7), ("z", 8, 7), ("intensity", 12, 7), ("ring", 16, 4))]
    header = _Msg(frame_id=frame_id, stamp=_Msg(sec=int(stamp), nanosec=int((stamp % 1) * 1e9)))
    return _Msg(header=header, height=1, width=xyz_s.shape[0], fields=fields, is_bigendian=False,
                point_step=18, row_step=18 * xyz_s.shape[0], data=data.tobytes()), R


def _feed(node, xyz, n, M=None, t0=0.0, topic="/lidar_points", frame_id="hesai_lidar"):
    for k in range(n):
        msg, R = _cloud(xyz, t0 + 0.1 * k, M, frame_id=frame_id)
        node.on_cloud(msg, topic)
    return R


@pytest.fixture(scope="module")
def box_scene():
    pytest.importorskip("open3d")
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, labels, _ = synthetic_tunnel_frame(rng=np.random.default_rng(3),
                                              specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=40.0)])
    return frame, labels


# ---------------------------------------------------------------------------

def test_clear_tunnel_is_go_with_a_verified_range(node_cls, tunnel):
    node = node_cls()
    _feed(node, tunnel[0].xyz, 6)
    pub = node.published
    assert pub["/resense/decision"][-1].data == "GO", [m.data for m in pub["/resense/decision"]]
    assert pub["/resense/obstacle_detected"][-1].data is False
    assert pub["/resense/clear_distance"][-1].data > 100.0
    health = pub["/resense/health"][-1].status[0]
    assert health.level == 0 and {kv.key for kv in health.values} >= {"monitored_range", "mount_status"}
    assert node.n_frames == 6 and node.dropped == 0


def test_obstacle_is_stop_and_published_in_the_sensor_frame(node_cls, box_scene):
    frame, labels = box_scene
    node = node_cls()
    R = _feed(node, frame.xyz, 6)
    pub = node.published
    assert pub["/resense/decision"][-1].data == "STOP"
    assert 38.0 < pub["/resense/nearest_distance"][-1].data < 42.0
    assert pub["/resense/clear_distance"][-1].data == pytest.approx(pub["/resense/nearest_distance"][-1].data, abs=0.2)
    det = pub["/resense/detections"][-1].detections[0]
    c = det.bbox.center.position
    truth = R.T @ frame.xyz[labels > 0].mean(axis=0)          # the box centroid in the sensor frame
    assert np.linalg.norm(np.array([c.x, c.y, c.z]) - truth) < 0.6
    assert det.results[0].hypothesis.class_id.startswith("gauge")
    markers = pub["/resense/markers"][-1].markers
    assert any(getattr(mk, "text", "").startswith("OBSTACLE") for mk in markers if isinstance(getattr(mk, "text", ""), str))


def test_remounted_sensor_is_calibrated_and_outputs_stay_in_the_sensor_frame(node_cls, box_scene):
    """The LiDAR is mounted with forward = +x instead of the configured -y: the node must find
    the orientation, report the box at 40 m, and publish it where the sensor sees it."""
    from resense.calibration import rot_z
    frame, labels = box_scene
    M = rot_z(np.pi / 2)
    node = node_cls()
    R = _feed(node, frame.xyz, 12, M=M)
    pub = node.published
    assert node.detector.calib.state.orientation == "forward=+y left=-x up=+z", node.detector.calib.state
    assert pub["/resense/decision"][-1].data == "STOP"
    assert 38.0 < pub["/resense/nearest_distance"][-1].data < 42.0
    c = pub["/resense/detections"][-1].detections[0].bbox.center.position
    truth = R.T @ (M @ frame.xyz[labels > 0].mean(axis=0))
    assert np.linalg.norm(np.array([c.x, c.y, c.z]) - truth) < 0.6


def test_mount_parameters_override_the_parameter_file(node_cls):
    _Node.overrides = {"sensor_forward": "+x", "sensor_left": "+y", "mount_roll_deg": 2.5,
                       "auto_calibrate": False}
    node = node_cls()
    s = node.cfg.sensor
    assert (s.forward, s.left, s.up) == ("+x", "+y", "+z")
    assert s.roll_deg == 2.5 and s.pitch_deg == 0.0
    assert node.cfg.calibration.enabled is False
    from resense.calibration import rot_x
    assert np.allclose(node.R_vs, rot_x(np.radians(2.5)))


def test_empty_and_nan_frames_are_fault_not_a_crash(node_cls, tunnel):
    node = node_cls()
    _feed(node, tunnel[0].xyz, 3)
    msg, _ = _cloud(np.full((500, 3), np.nan, np.float32), 0.3)
    node.on_cloud(msg, "/lidar_points")
    msg, _ = _cloud(np.zeros((0, 3), np.float32), 0.4)
    node.on_cloud(msg, "/lidar_points")
    pub = node.published
    assert [m.data for m in pub["/resense/decision"][-2:]] == ["FAULT", "FAULT"]
    assert pub["/resense/clear_distance"][-1].data == 0.0
    assert pub["/resense/health"][-1].status[0].level == 2


def test_processing_exception_is_fault_then_detector_reset(node_cls, tunnel, monkeypatch):
    _Node.overrides = {"max_consecutive_errors": 3}
    node = node_cls()
    _feed(node, tunnel[0].xyz, 2)
    resets = []
    monkeypatch.setattr(node.detector, "process", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(node.detector, "reset", lambda: resets.append(1))
    _feed(node, tunnel[0].xyz, 3, t0=0.2)
    pub = node.published
    assert [m.data for m in pub["/resense/decision"][-3:]] == ["FAULT"] * 3
    assert pub["/resense/obstacle_detected"][-1].data is False
    assert resets == [1] and node.consecutive_errors == 0
    assert any(level == "error" and "boom" in s for level, s in node.get_logger().lines)


def test_fault_snapshot_clears_previous_alarm_outputs(node_cls):
    """A watchdog/error snapshot must not leave a previous GO/STOP payload latched."""
    node = node_cls()
    node.publish_fault(_Msg(frame_id="hesai_lidar", stamp=_Msg(sec=12, nanosec=0)), "input is stale", "STALE")
    pub = node.published
    assert pub["/resense/decision"][-1].data == "FAULT"
    assert pub["/resense/obstacle_detected"][-1].data is False
    assert pub["/resense/warning"][-1].data is False
    assert pub["/resense/nearest_distance"][-1].data == -1.0
    assert pub["/resense/detections"][-1].detections == []
    assert pub["/resense/markers"][-1].markers[0].action == 3  # Marker.DELETEALL
    status = json.loads(pub["/resense/status"][-1].data)
    assert status["decision"] == "FAULT" and "node" not in status


def test_watchdog_no_input_and_stale_are_faults_without_open3d(node_cls):
    """Input guards remain testable on the ROS-message stubs without synthetic data."""
    node = node_cls()
    node.t_node_start -= 5.0
    node.on_watchdog()
    assert node.published["/resense/decision"][-1].data == "FAULT"
    assert node.published["/resense/health"][-1].status[0].values[0].value == "NO_INPUT"
    node.last_frame_wall = time.perf_counter() - 2.0
    node.last_stale_pub = 0.0
    node.on_watchdog()
    assert node.published["/resense/decision"][-1].data == "FAULT"
    stale = node.published["/resense/health"][-1].status[0]
    assert stale.values[0].value == "STALE" and stale.level == 3


def test_watchdog_reports_a_silent_input(node_cls, tunnel):
    node = node_cls()
    node.on_watchdog()                                   # just started, nothing received yet: no verdict
    assert not node.published["/resense/decision"]
    node.t_node_start -= 5.0                             # 5 s later, still nothing: FAULT, not silence
    node.on_watchdog()
    assert node.published["/resense/decision"][-1].data == "FAULT"
    st = node.published["/resense/health"][-1].status[0]
    assert "no LiDAR frame received yet" in st.message and st.values[0].value == "NO_INPUT"
    node.last_stale_pub = 0.0
    _feed(node, tunnel[0].xyz, 1)
    node.on_watchdog()                                   # fresh frame: silent
    assert node.published["/resense/decision"][-1].data != "FAULT"
    node.last_frame_wall = time.perf_counter() - 2.0     # the bag / driver stopped 2 s ago
    node.on_watchdog()
    st = node.published["/resense/health"][-1].status[0]
    assert node.published["/resense/decision"][-1].data == "FAULT"
    assert "no LiDAR frame" in st.message and st.values[0].value == "STALE"


def test_decision_levels(node_cls):
    ns = types.SimpleNamespace
    d = node_cls.decision
    assert d(ns(obstacle=True, warning=False, health={"level": "error"})) == "STOP"
    assert d(ns(obstacle=False, warning=False, health={"level": "error"})) == "FAULT"
    assert d(ns(obstacle=False, warning=True, health={"level": "ok"})) == "CAUTION"
    assert d(ns(obstacle=False, warning=False, health={"level": "warn"})) == "CAUTION"
    assert d(ns(obstacle=False, warning=False, health={"level": "ok"})) == "GO"


# ---------------------------------------------------------------------------
# several recordings through one running node (the organizers, 23.09: the control data may use
# either topic / frame pair - /lidar_points + hesai_lidar or /sensing/lidar/hesai128/pointcloud
# + lidar_livox - all from the same LiDAR, played from the console)
# ---------------------------------------------------------------------------

def test_next_recording_on_the_other_topic_pair_is_taken_with_a_fresh_detector(node_cls, tunnel):
    node = node_cls()
    _feed(node, tunnel[0].xyz, 4)
    first = node.detector
    assert node.active_topic == "/lidar_points" and node.n_frames == 4
    node.last_frame_wall = time.perf_counter() - 2.0          # the first bag has ended
    _feed(node, tunnel[0].xyz, 4, t0=5000.0, topic="/sensing/lidar/hesai128/pointcloud", frame_id="lidar_livox")
    assert node.active_topic == "/sensing/lidar/hesai128/pointcloud" and node.active_frame_id == "lidar_livox"
    assert node.n_inputs == 2 and node.detector is not first and node.n_frames == 8
    assert node.published["/resense/decision"][-1].data == "GO"
    assert any("input switched" in s for _, s in node.get_logger().lines)


def test_the_same_lidar_on_two_topics_is_processed_once(node_cls, tunnel):
    node = node_cls()
    msg_a, _ = _cloud(tunnel[0].xyz, 0.0)
    msg_b, _ = _cloud(tunnel[0].xyz, 0.0, frame_id="lidar_livox")
    node.on_cloud(msg_a, "/lidar_points")
    node.on_cloud(msg_b, "/sensing/lidar/hesai128/pointcloud")    # while /lidar_points is live: ignored
    assert node.n_frames == 1 and node.active_topic == "/lidar_points" and node.n_inputs == 1


def test_a_bag_played_again_restarts_and_a_hole_only_resets_the_scene(node_cls, tunnel, monkeypatch):
    node = node_cls()
    _feed(node, tunnel[0].xyz, 3, t0=100.0)
    first = node.detector
    _feed(node, tunnel[0].xyz, 2, t0=99.0)                   # stamps jump back: the bag again (loop:=true)
    assert node.detector is not first and node.n_inputs == 2
    resets = []
    monkeypatch.setattr(node.detector, "reset", lambda: resets.append(1))
    second = node.detector
    _feed(node, tunnel[0].xyz, 1, t0=105.0)                  # a 5.9 s hole in the recording
    assert resets == [1] and node.detector is second and node.n_inputs == 2
    _feed(node, tunnel[0].xyz, 1, t0=500.0)                  # 395 s forward: another recording
    assert node.detector is not second and node.n_inputs == 3


def test_discovery_keeps_looking_while_the_input_is_silent(node_cls, tunnel):
    node = node_cls()
    _feed(node, tunnel[0].xyz, 1)
    node.get_topic_names_and_types = lambda: [("/new_lidar", ["sensor_msgs/msg/PointCloud2"]),
                                              ("/resense/corridor_points", ["sensor_msgs/msg/PointCloud2"])]
    node.on_discover()                                       # input live: nothing to do
    assert "/new_lidar" not in node.subs
    node.last_frame_wall = time.perf_counter() - 2.0
    node.on_discover()                                       # silent: the next bag may use another name
    assert "/new_lidar" in node.subs and "/resense/corridor_points" not in node.subs


def test_input_reliability_follows_the_publishers(node_cls, monkeypatch):
    """A 10 MB cloud is ~160 UDP fragments: best-effort lost 196 of 201 frames of doubleT_obstacle
    played by `ros2 bag play` (reliable) in Docker. auto subscribes reliable, and switches to the
    publishers' reliability when they are known (a best-effort driver would give a reliable reader
    nothing)."""
    node = node_cls()
    assert node.sub_rel == {"/lidar_points": "reliable", "/sensing/lidar/hesai128/pointcloud": "reliable"}
    assert node.subs["/lidar_points"].qos["reliability"] == 1
    def pub(rel):
        return types.SimpleNamespace(qos_profile=types.SimpleNamespace(reliability=rel))

    graph = {"/lidar_points": [pub(1)], "/sensing/lidar/hesai128/pointcloud": [pub(2), pub(1)]}
    node.get_publishers_info_by_topic = lambda t: graph.get(t, [])
    node.on_match_qos()
    assert node.sub_rel["/lidar_points"] == "reliable"                          # unchanged
    assert node.sub_rel["/sensing/lidar/hesai128/pointcloud"] == "best_effort"  # one best-effort writer
    assert node.subs["/sensing/lidar/hesai128/pointcloud"].qos["reliability"] == 2
    assert any("re-created" in s for _, s in node.get_logger().lines)
    monkeypatch.setattr(_Node, "overrides", {"input_reliability": "best_effort"})
    forced = node_cls()
    assert set(forced.sub_rel.values()) == {"best_effort"} and forced.qos_timer is None


def test_status_marker_says_the_decision_and_publishing_errors_are_contained(node_cls, tunnel, box_scene):
    node = node_cls()
    _feed(node, tunnel[0].xyz, 4)
    status = node.published["/resense/markers"][-1].markers[-1]
    assert status.text.startswith("GO: path clear")
    node = node_cls()
    _feed(node, box_scene[0].xyz, 6)
    assert node.published["/resense/markers"][-1].markers[-1].text.startswith("STOP: OBSTACLE")

    def boom(*a, **k):
        raise TypeError("not JSON serializable")
    node.make_markers = boom                                  # a publishing failure (e.g. a bad value in the status)
    frames = node.n_frames
    _feed(node, box_scene[0].xyz, 1, t0=0.6)                  # must not raise out of the callback
    assert node.n_frames == frames and node.published["/resense/decision"][-1].data == "FAULT"


def test_input_queue_depth(node_cls):
    node = node_cls()
    assert node.subs["/lidar_points"].qos["depth"] == 40       # a burst of the player waits for the catch-up
    assert node.subs["/lidar_points"].qos["history"] == 1      # keep last
    _Node.overrides = {"input_queue_depth": 3}
    assert node_cls().subs["/lidar_points"].qos["depth"] == 3


def test_backlog_is_worked_through_catchup_step_apart(node_cls):
    """`ros2 bag play` (Humble) preloads the bag, then sends the overdue first seconds back to back
    (doubleT_obstacle: 41 clouds in 0.4 s, EXPERIMENTS.md section 3b). The node takes every waiting
    frame and processes one every catchup_step s of recording from the first frame on, instead of
    the newest only (the first 2-4 s of every played bag were lost); a frame that waits alone is
    processed at once, and catchup_step 0 restores the newest-only behaviour."""
    plan = node_cls.catchup_plan
    assert plan([5.0], 4.9, 0.3, 5.0) == [0]
    t = [0.1 * k for k in range(41)]
    chain = [round(0.3 * k, 1) for k in range(14)] + [4.0]      # from the first frame to the newest
    assert [round(t[i], 1) for i in plan(t, None, 0.3, 5.0)] == chain
    assert plan(t, None, 0.0, 5.0) == [40]                       # step 0: the newest only
    assert [round(t[i], 1) for i in plan(t, 1.0, 0.3, 5.0)][:3] == [1.3, 1.6, 1.9]
    assert plan(t, None, 0.3, 1.0)[0] == 30                      # older than the newest by > max lag: dropped
    assert plan([2.0, 2.1], 0.0, 0.3, 5.0) == [0, 1]             # a hole in the data: the next frame

    def stamp_msg(s):
        return _Msg(header=_Msg(frame_id="lidar_livox", stamp=_Msg(sec=int(s), nanosec=int(round((s % 1) * 1e9)))))

    for step, expect in ((0.3, chain), (0.0, [4.0])):
        _Node.overrides = {"catchup_step": step}
        node = node_cls()
        topic = "/sensing/lidar/hesai128/pointcloud"
        queue = [stamp_msg(0.1 * k) for k in range(1, 41)]       # waiting behind the first frame
        sub = node.subs[topic]
        sub.msg_type, sub.raw = None, False

        class _Handle:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def take_message(self, msg_type, raw):
                held.append(len(node.pending))
                return (queue.pop(0), {}) if queue else None
        sub.handle = _Handle()
        held = []
        seen = []

        def process(msg, t, node=node):
            node.active_topic = t
            seen.append(round(node._stamp(msg), 1))
        node.process_cloud = process
        node.on_cloud(stamp_msg(0.0), topic)
        while node.pending:
            node.on_pending()
        assert seen == expect
        assert max(held) <= len(expect) + 1                     # the frames to be skipped are not held
        assert not node.pending and node.pending_gc.triggered == len(expect) - 1


def test_catchup_skips_are_reported_apart_from_frames_never_received(node_cls, monkeypatch):
    """25.09, the dry run on the team VM: the start-up catch-up's own skips were counted as dropped
    frames and failed the acceptance check. ``node.catchup_skipped`` is the part of
    ``dropped_frames`` the node received and skipped on purpose; ``node.catchup`` marks the frames
    processed while behind and is false from the frame that is back on the newest one (where
    scripts/check_dry_run.py starts counting). Which frames are processed does not change."""
    node = node_cls()
    topic = "/sensing/lidar/hesai128/pointcloud"
    xyz = np.random.default_rng(0).uniform(5.0, 30.0, (64, 3)).astype(np.float32)

    def cloud(s):
        return _cloud(xyz, s, frame_id="lidar_livox")[0]

    queue = [cloud(0.1 * k) for k in range(1, 41)]              # waiting behind the first frame
    sub = node.subs[topic]
    sub.msg_type, sub.raw = None, False

    class _Handle:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def take_message(self, msg_type, raw):
            return (queue.pop(0), {}) if queue else None
    sub.handle = _Handle()
    seen = []
    monkeypatch.setattr(node.detector, "process", lambda frame, ego_speed=None: types.SimpleNamespace(
        obstacle=False, warning=False, nearest_distance=None, mount={},
        track=types.SimpleNamespace(center=0.0, curvature=0.0)))
    node.publish = lambda header, frame, res: seen.append((round(frame.stamp, 1), node.node_stats()))
    node.on_cloud(cloud(0.0), topic)
    while node.pending:
        node.on_pending()
    for s in (4.1, 4.2, 4.5, 4.6):                               # 4.3 and 4.4 never arrive
        node.on_cloud(cloud(s), topic)
    chain = [round(0.3 * k, 1) for k in range(14)] + [4.0]
    assert [s for s, _ in seen] == chain + [4.1, 4.2, 4.5, 4.6]
    assert [st["catchup"] for _, st in seen] == [True] * 14 + [False] * 5
    last = seen[-1][1]
    assert last["dropped_frames"] == 26 + 2 and last["catchup_skipped"] == 26
    assert seen[14][1]["dropped_frames"] == seen[14][1]["catchup_skipped"] == 26
    assert not node.skipped                                     # every skipped frame accounted
    assert any("caught up" in s and "26 skipped" in s for _, s in node.get_logger().lines)


def test_socket_buffer_warning(node_cls, tmp_path, monkeypatch):
    """25.09: with a host `ros2 bag play` on CycloneDDS (stock Fast DDS was not affected) the
    node received none or almost none of the 360-degree clouds at Ubuntu's
    net.core.rmem_max / rmem_default 212992 and all of them at 32 MiB. The node says so once at
    start, with the host fix; unreadable values are no failure."""
    warn = node_cls.socket_buffer_warning
    msg = warn({"rmem_max": 212992, "rmem_default": 212992})
    assert "sudo sysctl -w net.core.rmem_max=33554432 net.core.rmem_default=33554432" in msg
    assert "CycloneDDS" in msg and "net.core.rmem_max = 212992" in msg
    assert warn({"rmem_max": 33554432, "rmem_default": 212992}) is None      # the profile asks for 32 MiB itself
    assert warn({"rmem_max": 33554432, "rmem_default": 212992}, profile=False) is not None
    assert warn({}) is None
    mod = sys.modules[node_cls.__module__]
    (tmp_path / "rmem_max").write_text("212992\n")
    (tmp_path / "rmem_default").write_text("212992\n")
    monkeypatch.setattr(mod, "PROC_NET_CORE", str(tmp_path))
    warns = [s for level, s in node_cls().get_logger().lines if level == "warn"]
    assert len(warns) == 1 and "rmem_max = 212992" in warns[0]
    (tmp_path / "rmem_max").write_text("33554432\n")
    (tmp_path / "rmem_default").write_text("33554432\n")
    assert not [s for level, s in node_cls().get_logger().lines if level == "warn"]
    monkeypatch.setattr(mod, "PROC_NET_CORE", str(tmp_path / "missing"))
    node = node_cls()
    assert node.check_socket_buffers() == {} and not [s for lv, s in node.get_logger().lines if lv == "warn"]


def test_blas_threads_default_to_one_unless_set(node_cls, monkeypatch):
    """The package pins OMP / OpenBLAS / MKL to one thread before the node imports numpy, as the
    image does (EXPERIMENTS.md section 3a: 256 against 67 ms per 360-degree frame with numpy's
    default pool on a busy 4-vCPU box); an explicit value wins."""
    monkeypatch.delenv("OPENBLAS_NUM_THREADS", raising=False)
    monkeypatch.setenv("OMP_NUM_THREADS", "3")
    importlib.reload(sys.modules["resense_ros"])
    assert os.environ["OPENBLAS_NUM_THREADS"] == "1" and os.environ["OMP_NUM_THREADS"] == "3"



def test_rviz_shows_the_played_clouds():
    """The shipped RViz config reads the raw clouds reliable, like the node: `ros2 bag play` offers
    the recorded RELIABLE profile and a best-effort display showed almost none of the 5-10 MB
    clouds (EXPERIMENTS.md section 3b); the decision overlay and markers stay subscribed."""
    import yaml
    cfg = yaml.safe_load((NODE_PKG / "rviz" / "resense.rviz").read_text())
    displays = {d.get("Topic", {}).get("Value"): d for d in cfg["Visualization Manager"]["Displays"] if "Topic" in d}
    for topic in ("/lidar_points", "/sensing/lidar/hesai128/pointcloud"):
        assert displays[topic]["Enabled"] and displays[topic]["Topic"]["Reliability Policy"] == "Reliable"
    assert displays["/resense/markers"]["Enabled"]
