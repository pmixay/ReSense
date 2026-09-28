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
        # Synthetic unit streams explicitly emulate historical replay. Production defaults
        # are tested separately below; old header stamps never select a mode implicitly.
        default = "replay" if name == "freshness_mode" else value
        self._params[name] = self.overrides.get(name, default)

    def get_parameter(self, name):
        return _Param(self._params[name])

    def create_subscription(self, msg_type, topic, cb, qos, raw=False):
        return types.SimpleNamespace(topic=topic, cb=cb, qos=qos, raw=raw)

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
    async def await_or_execute(cb, *args):
        return cb(*args)
    class Executor:
        def _take_subscription(self, sub):
            return "upstream"
        async def _execute_subscription(self, sub, msg):
            return sub.callback(msg)
    rclpy.executors = mod("rclpy.executors", SingleThreadedExecutor=Executor,
                         await_or_execute=await_or_execute)
    rclpy.serialization = mod("rclpy.serialization", deserialize_message=lambda raw, t: ("converted", len(raw)))
    rclpy.qos = mod("rclpy.qos", QoSProfile=lambda **kw: kw,
                    QoSReliabilityPolicy=types.SimpleNamespace(RELIABLE=1, BEST_EFFORT=2),
                    QoSHistoryPolicy=types.SimpleNamespace(KEEP_LAST=1))
    mod("geometry_msgs"), mod("geometry_msgs.msg", Point=_msg("Point"), TransformStamped=_msg("TransformStamped"))
    mod("builtin_interfaces"), mod("builtin_interfaces.msg", Time=_msg("Time"))
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
                point_step=18, row_step=18 * xyz_s.shape[0], data=data.tobytes(), is_dense=False), R


def _feed(node, xyz, n, M=None, t0=0.0, topic="/lidar_points", frame_id="hesai_lidar"):
    for k in range(n):
        msg, R = _cloud(xyz, t0 + 0.1 * k, M, frame_id=frame_id)
        node.on_cloud(msg, topic, {"source_timestamp": time.time_ns()})
    return R


@pytest.fixture(scope="module")
def box_scene():
    pytest.importorskip("open3d")
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, labels, _ = synthetic_tunnel_frame(rng=np.random.default_rng(3),
                                              specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=40.0)])
    return frame, labels


# ---------------------------------------------------------------------------

def test_clear_tunnel_is_go_with_an_estimated_monitored_range(node_cls, tunnel):
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
    """A fault without a preceding STOP clears outputs and never leaves GO visible."""
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
    _feed(node, tunnel[0].xyz, 2)
    node.on_watchdog()                                   # fresh frame: silent
    assert node.published["/resense/decision"][-1].data != "FAULT"
    node.last_frame_wall = time.perf_counter() - 2.0     # the bag / driver stopped 2 s ago
    node.on_watchdog()
    st = node.published["/resense/health"][-1].status[0]
    assert node.published["/resense/decision"][-1].data == "FAULT"
    assert ("no LiDAR frame" in st.message or "last result expired" in st.message) and st.values[0].value == "STALE"


def test_decision_levels(node_cls):
    ns = types.SimpleNamespace
    d = node_cls.decision
    assert d(ns(obstacle=True, warning=False, health={"level": "error"})) == "STOP"
    assert d(ns(obstacle=False, warning=False, health={"level": "error"})) == "FAULT"
    assert d(ns(obstacle=False, warning=True, health={"level": "ok"})) == "CAUTION"
    assert d(ns(obstacle=False, warning=False, health={"level": "warn"})) == "CAUTION"
    assert d(ns(obstacle=False, warning=False, health={"level": "ok"})) == "GO"
    # 26.09: the warning the decision reads is decision_level (the latency warning left out)
    lat = {"level": "warn", "decision_level": "ok"}
    assert d(ns(obstacle=False, warning=False, health=lat)) == "GO"
    assert d(ns(obstacle=False, warning=True, health=lat)) == "CAUTION"
    assert d(ns(obstacle=True, warning=False, health=lat)) == "STOP"
    assert d(ns(obstacle=False, warning=False, health={"level": "warn", "decision_level": "warn"})) == "CAUTION"
    assert d(ns(obstacle=False, warning=False, health={"level": "error", "decision_level": "error"})) == "FAULT"


def _latency_config(tmp_path, affects: bool) -> str:
    """A parameter file whose latency budget every frame exceeds (0 ms)."""
    import yaml
    p = tmp_path / f"latency_{affects}.yaml"
    p.write_text(yaml.safe_dump({"resense": {"health": {"latency_budget_ms": 0.0,
                                                        "latency_affects_decision": affects}}}))
    return str(p)


@pytest.mark.parametrize("affects, expected", [(False, "GO"), (True, "CAUTION")])
def test_latency_over_budget_is_a_health_warning_not_caution(node_cls, tunnel, tmp_path, affects, expected):
    """26.09 (judgements of 24.09 and 26.09): a slow machine is not an unsafe path. Latency over
    the budget stays in /resense/health and the status JSON; the decision is GO on a clear track
    (CAUTION with ``health.latency_affects_decision: true``, the v0.6 behaviour)."""
    _Node.overrides = {"config_file": _latency_config(tmp_path, affects)}
    node = node_cls()
    assert node.cfg.health.latency_affects_decision is affects
    _feed(node, tunnel[0].xyz, 12)
    pub = node.published
    assert pub["/resense/decision"][-1].data == expected, [m.data for m in pub["/resense/decision"]]
    health = pub["/resense/health"][-1].status[0]
    assert health.level == 1 and "latency p95" in health.message
    values = {kv.key: kv.value for kv in health.values}
    assert values["decision_level"] == ("warn" if affects else "ok")
    status = json.loads(pub["/resense/status"][-1].data)
    assert status["decision"] == expected and status["health"]["level"] == "warn"
    assert any("latency p95" in m for m in status["health"]["messages"])
    marker = pub["/resense/markers"][-1].markers[-1].text
    assert marker.startswith(expected), marker
    # the node's own guards are unchanged: an empty frame, a stalled input, no input are FAULT
    msg, _ = _cloud(np.zeros((0, 3), np.float32), 1.2)
    node.on_cloud(msg, "/lidar_points")
    assert pub["/resense/decision"][-1].data == "FAULT"
    node.last_frame_wall = time.perf_counter() - 2.0
    node.last_stale_pub = 0.0
    node.on_watchdog()
    assert pub["/resense/decision"][-1].data == "FAULT"
    assert pub["/resense/health"][-1].status[0].values[0].value == "STALE"
    idle = node_cls()
    idle.t_node_start -= 5.0
    idle.on_watchdog()
    assert idle.published["/resense/decision"][-1].data == "FAULT"
    assert idle.published["/resense/health"][-1].status[0].values[0].value == "NO_INPUT"


@pytest.mark.parametrize("affects", [False, True])
def test_obstacle_is_stop_with_latency_over_budget(node_cls, box_scene, tmp_path, affects):
    frame, _ = box_scene
    _Node.overrides = {"config_file": _latency_config(tmp_path, affects)}
    node = node_cls()
    _feed(node, frame.xyz, 12)
    pub = node.published
    assert pub["/resense/decision"][-1].data == "STOP"
    assert pub["/resense/obstacle_detected"][-1].data is True
    assert "latency p95" in pub["/resense/health"][-1].status[0].message


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
    assert status.text.startswith("GO: NO OBSTACLE DETECTED")
    assert "monitored" in status.text and "(estimate)" in status.text
    node = node_cls()
    _feed(node, box_scene[0].xyz, 6)
    assert node.published["/resense/markers"][-1].markers[-1].text.startswith("STOP: OBSTACLE")

    def boom(*a, **k):
        raise TypeError("not JSON serializable")
    node.make_markers = boom                                  # a publishing failure (e.g. a bad value in the status)
    frames = node.n_frames
    _feed(node, box_scene[0].xyz, 1, t0=0.6)                  # must not raise out of the callback
    assert node.n_frames == frames and node.published["/resense/decision"][-1].data == "STOP"
    fault = json.loads(node.published["/resense/status"][-1].data)
    assert fault["stop_held"] and fault["snapshot_kind"] == "processing_error"


def test_input_queue_depth(node_cls):
    node = node_cls()
    assert node.subs["/lidar_points"].qos["depth"] == 40       # a burst of the player waits for the catch-up
    assert node.subs["/lidar_points"].qos["history"] == 1      # keep last
    _Node.overrides = {"input_queue_depth": 3}
    assert node_cls().subs["/lidar_points"].qos["depth"] == 3


def test_first_backlog_preserves_input_period_and_zero_step_keeps_latest(node_cls):
    """The first cold-disk burst may contain the whole overdue recording, so preserve every frame
    at the observed input period. Later live bursts still use the configured catch-up step; the
    pure planner checks below keep that behavior explicit. ``catchup_step: 0`` remains newest-only."""
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

    startup_frames = [round(0.1 * k, 1) for k in range(201)]
    for step, expect in ((0.3, startup_frames), (0.0, [20.0])):
        _Node.overrides = {"catchup_step": step}
        node = node_cls()
        node.input_period = 0.3  # a previous input ran slower than this recording's 10 Hz stream
        topic = "/sensing/lidar/hesai128/pointcloud"
        queue = [stamp_msg(0.1 * k) for k in range(1, 201)]      # the full 20 s bag burst is waiting
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
            if node.active_topic is None:
                node.active_frame_id = msg.header.frame_id
                node.startup_catchup_active = True
                node.startup_catchup_until = time.perf_counter() + 1.0
            node.active_topic = t
            seen.append(round(node._stamp(msg), 1))
        node.process_cloud = process
        node.on_cloud(stamp_msg(0.0), topic)
        while node.pending:
            node.on_pending()
        assert seen == expect
        assert max(held) <= len(expect) + 1                     # bounded by the retained startup chain
        assert not node.pending and node.pending_gc.triggered == len(expect) - 1


def test_catchup_skips_are_reported_apart_from_frames_never_received(node_cls, monkeypatch):
    """The start-up burst preserves every available input frame; a later live gap still counts
    missing recording messages separately from frames deliberately thinned by catch-up."""
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
    startup = [round(0.1 * k, 1) for k in range(41)]
    assert [s for s, _ in seen] == startup + [4.1, 4.2, 4.5, 4.6]
    assert [st["catchup"] for _, st in seen] == [True] * 40 + [False] * 5
    assert seen[40][1]["dropped_frames"] == seen[40][1]["catchup_skipped"] == 0
    last = seen[-1][1]
    assert last["dropped_frames"] == 2 and last["catchup_skipped"] == 0
    assert not node.skipped                                     # every skipped frame accounted
    assert any("caught up" in s and "0 skipped" in s for _, s in node.get_logger().lines)


def test_short_live_backlog_keeps_every_frame_and_still_obeys_lag_limit(node_cls, monkeypatch):
    """A brief executor delay may queue two or three clouds despite processing below 100 ms.
    The real cold run skipped isolated frames at +11.7/+12.7 s with catchup=False. Such a short
    backlog now drains in full; larger bursts still use the existing bounded catch-up policy.
    """
    node = node_cls()
    now = [100.0]
    queue, seen, cloud = _catchup_stream(node, monkeypatch, now)
    node.on_cloud(cloud(0.0), "/lidar_points")
    now[0] += 2.0  # normal live operation after the startup entry window
    queue.extend([cloud(0.2), cloud(0.3)])
    node.on_cloud(cloud(0.1), "/lidar_points")
    while node.pending:
        node.on_pending()
    assert seen == pytest.approx([0.0, 0.1, 0.2, 0.3])
    assert node.dropped == node.dropped_skipped == 0
    assert node.catchup is None and not node.startup_catchup_active
    # An explicitly smaller maximum lag must still win over preserving a short backlog.
    assert node.catchup_plan([0.1, 0.2, 0.3], 0.0, 0.3, 0.1) == [1, 2]
    assert node.catchup_plan([0.1, 0.2, 0.3], 0.0, 0.0, 5.0) == [2]


def _catchup_stream(node, monkeypatch, now, topic="/lidar_points", frame_id="hesai_lidar"):
    """Queue real-shaped headers; keep continuity and accounting, omit point-cloud work."""
    module = sys.modules[type(node).__module__]
    monkeypatch.setattr(module.time, "perf_counter", lambda: now[0])
    queue, seen = [], []
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

    def cloud(stamp):
        sec = int(np.floor(stamp))
        return _Msg(width=1, height=1, header=_Msg(frame_id=frame_id,
                    stamp=_Msg(sec=sec, nanosec=int(round((stamp - sec) * 1e9)))))

    def process(msg, source):
        if node.check_continuity(source, msg):
            node.last_frame_wall = now[0]
            node._account_frame(node._stamp(msg), (source, msg.header.frame_id))
            seen.append(node._stamp(msg))

    node.process_cloud = process
    return queue, seen, cloud


@pytest.mark.parametrize("startup_lag, expect_resets", [(5.0, True), (20.0, False)])
def test_cold_recording_burst_keeps_a_continuous_startup_chain(node_cls, monkeypatch, startup_lag, expect_resets):
    """Replay the failure's arrival pattern: each callback gets another 1.5 s of recording.

    The old 5 s cutoff repeatedly jumps over a second of scene history. The startup allowance
    preserves every 0.1 s input-period frame even after its one-second entry window has elapsed,
    and closes when caught up. A later live backlog still uses the 0.3 s step and 5 s bound.
    """
    _Node.overrides = {"catchup_startup_max_lag": startup_lag}
    node = node_cls()
    now = [100.0]
    queue, seen, cloud = _catchup_stream(node, monkeypatch, now)
    resets = []
    monkeypatch.setattr(node.detector, "reset", lambda: resets.append(1))
    queue.extend(cloud(k / 10) for k in range(1, 41))
    node.on_cloud(cloud(0.0), "/lidar_points")
    next_frame = 41
    while node.pending:
        queue.extend(cloud(k / 10) for k in range(next_frame, min(next_frame + 15, 201)))
        next_frame = min(next_frame + 15, 201)
        now[0] += 0.15
        node.on_pending()
    assert next_frame == 201 and seen[-1] == 20.0
    assert bool(resets) is expect_resets
    if not expect_resets:
        assert max(np.diff(seen)) <= 0.100001
        assert seen[0] == 0.0 and len(seen) == 201
        assert node.dropped == node.dropped_skipped == 0 and not node.skipped
    assert not node.startup_catchup_active and node.catchup is None
    # An independent stall in this recording must not inherit the startup allowance.
    queue.extend(cloud(k / 10) for k in range(202, 351))
    node.on_cloud(cloud(20.1), "/lidar_points")
    assert 30.0 <= seen[-1] <= 30.3


def test_startup_burst_can_follow_an_isolated_first_cloud(node_cls, monkeypatch):
    node = node_cls()
    now = [100.0]
    queue, seen, cloud = _catchup_stream(node, monkeypatch, now)
    node.on_cloud(cloud(0.0), "/lidar_points")
    now[0] += 0.1
    queue.extend(cloud(k / 10) for k in range(2, 151))
    node.on_cloud(cloud(0.1), "/lidar_points")
    while node.pending:
        node.on_pending()
    assert seen[:3] == pytest.approx([0.0, 0.1, 0.2])  # preserve input-period frames at the start
    assert seen[-1] == 15.0 and not node.startup_catchup_active


def test_live_catchup_returns_to_configured_step_after_startup(node_cls, monkeypatch):
    node = node_cls()
    now = [100.0]
    queue, seen, cloud = _catchup_stream(node, monkeypatch, now)
    node.on_cloud(cloud(0.0), "/lidar_points")
    now[0] += 2.0  # the isolated first cloud's one-second startup entry window expired
    queue.extend(cloud(k / 10) for k in range(2, 22))
    node.on_cloud(cloud(0.1), "/lidar_points")
    while node.pending:
        node.on_pending()
    assert seen[0] == 0.0 and seen[1:3] == pytest.approx([0.3, 0.6])
    assert seen[-1] == 2.1 and max(np.diff(seen[1:])) <= 0.300001
    assert node.dropped_skipped > 0 and not node.startup_catchup_active


def test_live_input_without_startup_backlog_expires_the_extra_allowance(node_cls, monkeypatch):
    node = node_cls()
    now = [100.0]
    queue, seen, cloud = _catchup_stream(node, monkeypatch, now)
    node.on_cloud(cloud(0.0), "/lidar_points")
    now[0] += 2.0
    queue.extend(cloud(k / 10) for k in range(2, 151))
    node.on_cloud(cloud(0.1), "/lidar_points")
    assert seen[0] == 0.0 and 10.0 <= seen[1] <= 10.3
    assert not node.startup_catchup_active


@pytest.mark.parametrize("next_topic, next_frame, next_start", [
    ("/lidar_points", "hesai_lidar", 50.0),        # another playback of the same bag
    ("/lidar_points", "hesai_lidar", 200.0),       # forward jump: another recording
    ("/lidar_points", "lidar_livox", 102.1),       # mount / frame changed
    ("/sensing/lidar/hesai128/pointcloud", "lidar_livox", 102.1),
])
def test_each_new_recording_gets_its_own_startup_allowance(node_cls, monkeypatch,
                                                       next_topic, next_frame, next_start):
    node = node_cls()
    now = [100.0]
    queue, seen, cloud = _catchup_stream(node, monkeypatch, now)
    queue.extend(cloud(100.0 + k / 10) for k in range(1, 21))
    node.on_cloud(cloud(100.0), "/lidar_points")
    while node.pending:
        node.on_pending()
    assert not node.startup_catchup_active
    now[0] += 2.0  # permit a topic switch as well as a new recording on the same topic
    queue, seen, cloud = _catchup_stream(node, monkeypatch, now, next_topic, next_frame)
    queue.extend(cloud(next_start + k / 10) for k in range(1, 151))
    node.on_cloud(cloud(next_start), next_topic)
    assert seen[0] == pytest.approx(next_start)
    while node.pending:
        node.on_pending()
    assert max(np.diff(seen)) <= 0.300001 and node.n_inputs == 2
    assert not node.startup_catchup_active


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


@pytest.fixture
def freshness_driver(node_cls, monkeypatch):
    """Exercise the real node queue/output policy with a deterministic detector and clocks."""
    from resense.detector import FrameResult
    from resense.track import TrackModel
    module = sys.modules[node_cls.__module__]
    clock = {"wall": 1000.0, "mono": 50.0, "obstacle": False}
    monkeypatch.setattr(module.time, "time", lambda: clock["wall"])
    monkeypatch.setattr(module.time, "perf_counter", lambda: clock["mono"])
    def detect(self, frame, **kwargs):
        return FrameResult(stamp=frame.stamp, obstacle=clock["obstacle"], warning=False,
                           nearest_distance=40.0 if clock["obstacle"] else None,
                           detections=[], warnings=[], candidates=[], track=TrackModel(np.array([0.0]), (0.0, 100.0), 0.0, 0.0, 0.0),
                           corridor_idx=np.array([], dtype=int), n_points=len(frame.xyz),
                           health={"level": "ok", "decision_level": "ok", "messages": [],
                                   "clear_distance": 100.0, "monitored_range": 100.0}, clear_distance=100.0)
    monkeypatch.setattr(module.Detector, "process", detect)
    node = node_cls()
    def send(stamp=None, *, age=0.1, dt=0.1, info=True, topic="/lidar_points", frame_id="lidar"):
        clock["wall"] += dt
        clock["mono"] += dt
        msg, _ = _cloud(np.array([[5.0, 0.0, 0.0]], dtype=np.float32),
                        clock["wall"] - age if stamp is None else stamp, frame_id=frame_id)
        metadata = {"source_timestamp": int((clock["wall"] - age) * 1e9)} if info else None
        node.on_cloud(msg, topic, metadata)
        return json.loads(node.published["/resense/status"][-1].data)
    return node, clock, send


def test_live_default_and_explicit_replay_are_not_inferred_from_header(node_cls, monkeypatch):
    defaults = {}
    def declare(self, name, value):
        defaults[name] = value
        self._params[name] = value
    monkeypatch.setattr(_Node, "declare_parameter", declare)
    node = node_cls()
    assert node.freshness_mode == defaults["freshness_mode"] == "live"
    assert defaults["max_result_age"] == 0.5 and defaults["future_tolerance"] == 0.05
    with pytest.raises(ValueError, match="freshness_mode"):
        monkeypatch.setattr(_Node, "declare_parameter", lambda self, n, v: self._params.update(
            {n: "auto" if n == "freshness_mode" else v}))
        node_cls()


def test_freshness_live_acquisition_and_replay_publication_clocks(freshness_driver):
    node, clock, send = freshness_driver
    first = send(20.0)
    assert first["decision"] == "FAULT" and first["freshness"]["reason"] == "epoch_unconfirmed"
    replay = send(20.1)
    assert replay["decision"] == "GO" and replay["freshness"]["go_allowed"]
    assert replay["freshness"]["acquisition_age_s"] is None
    assert replay["freshness"]["publication_age_s"] == pytest.approx(0.1)
    node.freshness_mode, node.freshness_previous = "live", None
    old = send(20.2, info=False)
    assert old["decision"] == "FAULT" and old["freshness"]["reason"] == "source_stale"
    # Live mode needs no DDS metadata when acquisition UTC is comparable and progressing.
    send(info=False)
    live = send(info=False)
    assert live["decision"] == "GO" and live["freshness"]["publication_age_s"] is None
    assert live["freshness"]["acquisition_age_s"] == pytest.approx(0.1)


@pytest.mark.parametrize("age,reason", [(0.501, "source_stale"), (-0.051, "source_clock_future")])
def test_stale_future_and_unknown_sources_never_allow_go(freshness_driver, age, reason):
    node, clock, send = freshness_driver
    send(20.0)
    send(20.1)
    bad = send(20.2, age=age)
    assert bad["decision"] == "FAULT" and bad["freshness"]["reason"] == reason
    assert bad["clear_distance"] == 0 and bad["detector_clear_distance"] == 100
    assert bad["health"]["level"] == "error" and not bad["freshness"]["go_allowed"]
    assert node.published["/resense/health"][-1].status[0].level == 2
    assert node.published["/resense/markers"][-1].markers[-1].text.startswith("FAULT")
    missing = send(20.3, info=False)
    assert missing["decision"] == "FAULT" and missing["freshness"]["reason"] == "source_clock_unknown"
    assert send(20.4)["decision"] == "FAULT"  # need a comparable prior source too
    assert send(20.5)["decision"] == "GO"


def test_pause_resume_timestamp_jumps_input_switch_and_recovery(freshness_driver):
    node, clock, send = freshness_driver
    send(20.0)
    assert send(20.1)["decision"] == "GO"
    resumed = send(20.2, dt=0.6)
    assert resumed["freshness"]["reason"] == "resumed_after_silence"
    assert send(20.3)["decision"] == "GO"
    assert send(20.3)["freshness"]["reason"] == "header_not_progressing"
    assert send(20.4)["decision"] == "GO"
    assert send(10.0)["freshness"]["reason"] == "epoch_unconfirmed"
    assert send(10.1)["decision"] == "GO"
    assert send(50.0)["freshness"]["reason"] == "epoch_unconfirmed"
    assert send(50.1)["decision"] == "GO"
    changed = send(5.0, dt=1.1, topic="/another_lidar", frame_id="new_lidar")
    assert changed["freshness"]["reason"] == "epoch_unconfirmed"
    assert changed["node"]["recording"] == 4
    assert send(5.1, topic="/another_lidar", frame_id="new_lidar")["decision"] == "GO"
    clock["wall"] += 0.2
    jump = send(5.2, topic="/another_lidar", frame_id="new_lidar")
    assert jump["freshness"]["reason"] == "system_clock_jump"
    assert send(5.3, topic="/another_lidar", frame_id="new_lidar")["decision"] == "GO"


def test_startup_and_later_backlogs_and_residence_are_not_actionable(freshness_driver):
    node, clock, send = freshness_driver
    def queue(stamps, residence=0.0, age=0.1):
        clock["wall"] += 0.1
        clock["mono"] += 0.1
        for i, stamp in enumerate(stamps):
            msg, _ = _cloud(np.array([[5.0, 0, 0]], np.float32), stamp, frame_id="lidar")
            node.remember_arrival(msg, {"source_timestamp": int((clock["wall"]-age+i*0.001) * 1e9)})
            first, src = node.arrivals[id(msg)]
            node.arrivals[id(msg)] = first-residence, src
            node.pending.append(("/lidar_points", msg))
        node.process_next()
        return json.loads(node.published["/resense/status"][-1].data)
    startup = queue([20.0, 20.3, 20.6, 20.9])
    assert startup["freshness"]["reason"] == "queue_stale"
    assert startup["decision"] == "FAULT" and startup["node"]["catchup"]
    while node.pending:
        node.process_next()
    send(21.0)
    assert send(21.1)["decision"] == "GO"
    # Source ages remain current while the recording queue is behind: still no GO.
    later = queue([21.2, 21.4, 21.6])
    assert later["decision"] == "CAUTION" and later["freshness"]["reason"] == "catchup"
    assert later["clear_distance"] == 0
    while node.pending:
        node.process_next()
    send(21.7)
    slow = queue([21.8], residence=0.501)
    assert slow["decision"] == "FAULT" and slow["freshness"]["reason"] == "residence_stale"


def test_stop_survives_stale_input_errors_and_invalid_clear_then_fresh_recovery(freshness_driver):
    node, clock, send = freshness_driver
    clock["obstacle"] = True
    stop = send(20.0, age=1.0)
    assert stop["decision"] == "STOP" and not stop["freshness"]["valid"]
    clock["mono"] += 1.0
    clock["wall"] += 1.0
    node.on_watchdog()
    watchdog = json.loads(node.published["/resense/status"][-1].data)
    assert watchdog["decision"] == "STOP" and watchdog["snapshot_kind"] == "watchdog"
    assert watchdog["stop_held"] and not watchdog["freshness"]["valid"]
    assert node.published["/resense/obstacle_detected"][-1].data is True
    assert "STOP HELD" in node.published["/resense/markers"][-1].markers[-1].text
    node.publish_fault(_Msg(frame_id="lidar", stamp=_Msg(sec=21, nanosec=0)), "broken")
    fault = json.loads(node.published["/resense/status"][-1].data)
    assert fault["decision"] == "STOP" and fault["snapshot_kind"] == "processing_error"
    clock["obstacle"] = False
    stale_clear = send(20.1, info=False)
    assert stale_clear["decision"] == "STOP" and stale_clear["stop_held"]
    assert stale_clear["detector_obstacle"] is False and stale_clear["clear_distance"] == 0
    assert send(20.2)["decision"] == "STOP"
    recovered = send(20.3)
    assert recovered["decision"] == "GO" and not recovered["stop_held"]
    assert node.published["/resense/obstacle_detected"][-1].data is False


def test_humble_executor_preserves_first_and_drained_source_info(node_cls):
    import asyncio
    module = sys.modules[node_cls.__module__]
    node = node_cls()
    first, _ = _cloud(np.array([[5.0, 0, 0]], np.float32), 20.0)
    second, _ = _cloud(np.array([[5.0, 0, 0]], np.float32), 20.1)
    pairs = [(first, {"source_timestamp": 100_000_000_000}),
             (second, {"source_timestamp": 100_100_000_000})]
    class Handle:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def take_message(self, *a): return pairs.pop(0) if pairs else None
    sub = node.subs["/lidar_points"]
    sub.handle, sub.msg_type, sub.raw, sub.callback = Handle(), object, False, sub.cb
    node.process_next = lambda: None  # inspect queue before it drains
    executor = module.SourceInfoExecutor()
    taken = executor._take_subscription(sub)
    asyncio.run(executor._execute_subscription(sub, taken))
    assert [m for _, m in node.pending] == [first, second]
    assert node.arrivals[id(first)][1] == 100.0
    assert node.arrivals[id(second)][1] == pytest.approx(100.1)
    # Non-LiDAR subscriptions use upstream behavior, including one-argument callbacks.
    seen = []
    ordinary = types.SimpleNamespace(callback=seen.append)
    assert executor._take_subscription(ordinary) == "upstream"
    asyncio.run(executor._execute_subscription(ordinary, "ordinary"))
    assert seen == ["ordinary"]


def test_watchdog_expires_source_age_before_processing_silence_timeout(freshness_driver):
    node, clock, send = freshness_driver
    send(20.0, age=0.4)
    assert send(20.1, age=0.4)["decision"] == "GO"
    assert node.last_status.startswith("GO")
    # Only 0.11 s since processing, but the source result is now 0.51 s old.
    clock["mono"] += 0.11
    clock["wall"] += 0.11
    node.on_watchdog()
    invalid = json.loads(node.published["/resense/status"][-1].data)
    assert invalid["decision"] == "FAULT" and invalid["snapshot_kind"] == "watchdog"
    assert not invalid["freshness"]["valid"] and node.last_status.startswith("FAULT")
    assert send(20.2)["decision"] == "FAULT"  # expiry closes the previous epoch
    assert send(20.3)["decision"] == "GO"


def test_invalid_rviz_range_is_gray_and_logs_use_published_decision(freshness_driver):
    node, clock, send = freshness_driver
    invalid = send(20.0, age=1.0)
    assert invalid["decision"] == "FAULT" and node.last_status.startswith("FAULT")
    outlines = [m for m in node.published["/resense/markers"][-1].markers if getattr(m, "type", None) == 4]
    assert len(outlines) == 2
    assert all(m.color.r == m.color.g == m.color.b for m in outlines)
    send(20.1)
    assert send(20.2)["decision"] == "GO"
    outlines = [m for m in node.published["/resense/markers"][-1].markers if getattr(m, "type", None) == 4]
    assert all(m.color.g > m.color.r for m in outlines)


def test_result_carries_evaluation_clock_and_configured_expiry_for_consumers(freshness_driver):
    node, clock, send = freshness_driver
    send(20.0)
    result = send(20.1)
    f = result["freshness"]
    assert f["evaluated_at_utc_s"] == clock["wall"]
    assert f["max_result_age_s"] == 0.5 and f["future_tolerance_s"] == 0.05
    remaining = f["max_result_age_s"] - max(0, f["source_age_s"], f["residence_age_s"])
    assert remaining == pytest.approx(0.4)
    assert f["evaluated_at_utc_s"] + remaining < clock["wall"] + 0.5


# ---------------------------------------------------------------------------
# 28.09: the input read from its serialized bytes, the publishing order, launch arguments

_VOLATILE = {"timing_ms", "node", "freshness"}


def _frames(node):
    return [json.loads(m.data) for m in node.published["/resense/status"]]


def _stable(status):
    out = {k: v for k, v in status.items() if k not in _VOLATILE}
    out["health"] = {k: v for k, v in status["health"].items() if "latency" not in k and k != "messages"}
    return out


def test_raw_cdr_input_gives_the_same_results_as_messages(node_cls, tunnel, box_scene):
    """The raw subscription's bytes (``resense_ros/fastcloud.py``) and rclpy's message of the same
    cloud give the same decision, distances, objects, track model and health on every frame."""
    from test_fastcloud import _cdr
    for scene in (tunnel[0].xyz, box_scene[0].xyz):
        by_msg, by_raw = node_cls(), node_cls()
        for k in range(7):
            msg, _ = _cloud(scene, 0.1 * k)
            by_msg.on_cloud(msg, "/lidar_points", {"source_timestamp": time.time_ns()})
            by_raw.on_cloud(_cdr(msg), "/lidar_points", {"source_timestamp": time.time_ns()})
        a, b = _frames(by_msg), _frames(by_raw)
        assert len(a) == len(b) == 7
        assert [_stable(x) for x in a] == [_stable(x) for x in b]
    assert b[-1]["decision"] == "STOP" and 38.0 < b[-1]["nearest_distance"] < 42.0
    assert by_raw.published["/resense/detections"][-1].header.stamp.sec == 0     # a real Header was made
    assert {"decode_ms", "detect_ms", "cpu_cores", "rss_peak_mb"} <= set(b[-1]["node"])
    assert b[-1]["node"]["latency_ms"] >= b[-1]["node"]["detect_ms"] > 0


def test_input_is_subscribed_raw_unless_disabled_and_bad_bytes_fall_back(node_cls):
    node = node_cls()
    assert all(sub.raw is True for sub in node.subs.values())
    assert node.as_cloud(b"\x00\x02\x00\x00not cdr") == ("converted", 11)      # rclpy's conversion instead
    node.as_cloud(b"")
    assert node.raw_fallbacks == 2 and sum("not read from its bytes" in s for _, s in node.get_logger().lines) == 1
    msg = object()
    assert node.as_cloud(msg) is msg

    def unreadable(raw, msg_type):
        raise RuntimeError("failed to deserialize ROS message")
    sys.modules["rclpy.serialization"].deserialize_message = unreadable
    frames = node.n_frames
    node.on_cloud(b"\x00\x01\x00\x00truncated", "/lidar_points", {"source_timestamp": time.time_ns()})
    assert node.as_cloud(b"garbage") is None and node.n_frames == frames and not node.pending
    assert sum("input cloud dropped" in s for _, s in node.get_logger().lines) == 2
    _Node.overrides = {"raw_input": False}
    assert all(sub.raw is False for sub in node_cls().subs.values())


def test_decision_goes_out_before_the_json_and_visualisation_only_for_subscribers(node_cls, box_scene):
    node = node_cls()
    order = []
    for attr in ("pub_decision", "pub_dist", "pub_status", "pub_markers", "pub_corridor"):
        pub = getattr(node, attr)
        pub.publish = (lambda m, a=attr, p=pub.publish: (order.append(a), p(m)))
    node.pub_markers.get_subscription_count = lambda: 0
    node.pub_corridor.get_subscription_count = lambda: 0
    _feed(node, box_scene[0].xyz, 3)
    assert order.index("pub_dist") < order.index("pub_decision") < order.index("pub_status")
    assert "pub_markers" not in order and "pub_corridor" not in order
    node.pub_markers.get_subscription_count = lambda: 1           # RViz / Foxglove connects
    node.pub_corridor.get_subscription_count = lambda: 2
    _feed(node, box_scene[0].xyz, 1, t0=0.3)
    assert order[-2:] == ["pub_markers", "pub_corridor"]
    edge = node.published["/resense/markers"][-1].markers[-3]
    assert len(edge.points) == 60 and all(isinstance(p.x, float) for p in edge.points)


def test_every_node_parameter_is_a_launch_argument_with_the_same_default(node_cls):
    """README "Node parameters": every node parameter is a launch argument (``config_file`` is the
    launch file's own), with the node's default."""
    import ast
    tree = ast.parse((NODE_PKG / "launch" / "detector.launch.py").read_text())
    table = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 and any(getattr(t, "id", "") == "PARAMS" for t in n.targets))
    launch = {k.value: (v.elts[0].value, v.elts[1].id) for k, v in zip(table.keys, table.values)}
    node = node_cls()
    declared = {k: v for k, v in node._params.items() if k != "config_file"}
    assert set(declared) == set(launch)
    cast = {"bool": lambda s: s.lower() == "true", "float": float, "int": int, "str": str}
    for name, (default, typ) in launch.items():
        if name != "freshness_mode":          # the stand-in node declares replay for the unit streams
            assert cast[typ](default) == declared[name], name


def test_the_node_default_stays_the_live_clock(node_cls, monkeypatch):
    """28.09: the image's default command passes freshness_mode:=replay (next test); the node's own
    default remains the stricter live clock for a train."""
    defaults = {}
    monkeypatch.setattr(_Node, "declare_parameter", lambda self, n, v: (defaults.update({n: v}), self._params.update({n: v})))
    assert node_cls().freshness_mode == defaults["freshness_mode"] == "live"


_DOCKERFILE = NODE_PKG.parents[2] / "docker" / "Dockerfile"
if _DOCKERFILE.is_file():       # a checkout (CI job "pytest"); the image does not carry docker/Dockerfile
    def test_the_image_starts_the_node_for_recorded_bags():
        """28.09: `docker run resense` (no arguments) must give current results on a played bag,
        the spec's chain."""
        import re
        cmd = re.search(r'^CMD \[(.*)\]$', _DOCKERFILE.read_text(), re.M).group(1)
        assert json.loads(f"[{cmd}]") == ["ros2", "launch", "resense_ros", "detector.launch.py",
                                          "freshness_mode:=replay"]
