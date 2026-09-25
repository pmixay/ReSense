"""Module tests that run without the dataset (each < 2 s).

Hand-built inputs for the tracker, the clustering filters, the gauge, the config round trip,
PointCloud2 decoding and the captain's dry-run checker; the synthetic tunnel (Open3D, ``tunnel``
/ ``synth_npy_dir`` fixtures) for the track model and the CLI smoke tests.
"""
import importlib.util
import json
import os
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from resense.cli import run_cli
from resense.clustering import Cluster, find_clusters
from resense.config import DetectorConfig
from resense.gauge import corridor_mask, point_in_polygon, widened_profile
from resense.pointcloud import COMPACT_DTYPE, pointcloud2_to_arrays, pointcloud2_to_structured, structured_to_compact
from resense.track import TrackModel, estimate_track
from resense.tracking import Tracker

REPO = Path(__file__).resolve().parents[1]
CFG = DetectorConfig()


# ---------------------------------------------------------------------------
# tracker
# ---------------------------------------------------------------------------

def cluster_at(x, y=0.0, z=0.0, zone="gauge", score=1.0):
    c = np.array([x, y, z], dtype=float)
    return Cluster(points_idx=np.arange(3), n=10, n_raw=20, centroid=c, bbox_min=c - 0.25, bbox_max=c + 0.25,
                   distance=x - 0.25, lateral=y, height_min=0.2, height_max=0.7, intensity=30.0,
                   n_expected=10.0, score=score, zone=zone, n_gauge=10)


def test_tracker_confirms_after_confirm_hits_not_before():
    t = Tracker(CFG.tracking)
    for k in range(1, CFG.tracking.confirm_hits):
        t.update([cluster_at(100.0)])
        assert t.confirmed() == [], f"confirmed after {k} hits"
    t.update([cluster_at(100.0)])
    conf = t.confirmed()
    assert len(conf) == 1 and conf[0].hits == CFG.tracking.confirm_hits and conf[0].zone == "gauge"
    assert conf[0].confidence >= CFG.tracking.conf_threshold


def test_tracker_confidence_decays_and_track_is_dropped_after_max_misses():
    t = Tracker(CFG.tracking)
    for _ in range(4):
        t.update([cluster_at(100.0)])
    tid = t.confirmed()[0].id
    conf = t.tracks[0].confidence
    for k in range(1, CFG.tracking.max_misses + 1):
        t.update([])
        # a reported track is held over hold_misses missed frames (a single miss does not drop a
        # STOP), then no longer reported although it survives to max_misses
        assert [x.id for x in t.confirmed()] == ([tid] if k <= CFG.tracking.hold_misses else [])
        assert len(t.tracks) == 1 and t.tracks[0].id == tid and t.tracks[0].misses == k
        assert t.tracks[0].confidence == pytest.approx(max(0.0, conf - k * CFG.tracking.conf_decay))
    t.update([])
    assert t.tracks == []                                       # max_misses + 1 misses: dropped



def test_a_single_missed_frame_does_not_drop_a_reported_obstacle():
    """Review 23.09: the decision flickered (a confirmed obstacle missed in one frame gave GO for
    that frame). hold_misses = 1 keeps it for one missed frame; a new track is never created or
    confirmed by the hold, and hold_misses = 0 restores the old behaviour."""
    from dataclasses import replace
    for hold, expect in ((1, [True, True, False]), (0, [True, False, False])):
        t = Tracker(replace(CFG.tracking, hold_misses=hold))
        for _ in range(5):
            t.update([cluster_at(50.0)])
        seen = [bool(t.confirmed())]
        t.update([])                                   # one missed frame
        seen.append(bool(t.confirmed()))
        t.update([])                                   # a second one
        seen.append(bool(t.confirmed()))
        assert seen == expect, (hold, seen)
    t = Tracker(CFG.tracking)
    t.update([cluster_at(50.0)])
    t.update([])
    assert t.confirmed() == []                         # never reported, so nothing to hold

def test_tracker_keeps_a_static_object_approaching_at_ego_speed_max():
    t = Tracker(CFG.tracking)
    step = CFG.tracking.ego_speed_max * CFG.tracking.frame_dt   # 2.5 m per frame without odometry
    for k in range(6):
        t.update([cluster_at(100.0 - k * step)])
    assert len(t.tracks) == 1 and t.tracks[0].hits == 6 and t.tracks[0].misses == 0
    assert [x.id for x in t.confirmed()] == [t.tracks[0].id]
    # the same slack is not granted away from the vehicle: 6 m per frame is a new track every frame
    t = Tracker(CFG.tracking)
    for k in range(6):
        t.update([cluster_at(100.0 + k * 6.0)])
    assert all(x.hits == 1 for x in t.tracks) and t.confirmed() == []


def test_tracker_zone_is_majority_of_recent_hits():
    t = Tracker(CFG.tracking)
    for zone in ("gauge", "gauge", "warning"):
        t.update([cluster_at(50.0, zone=zone)])
    assert t.confirmed()[0].zone == "gauge"
    for zone in ("warning", "warning"):
        t.update([cluster_at(50.0, zone=zone)])
    assert t.confirmed()[0].zone == "warning"


# ---------------------------------------------------------------------------
# clustering filters on hand-built point sets (rail head at z = 0, track axis at y = 0)
# ---------------------------------------------------------------------------

def surface_box(x0, y0, z0, L, W, H, step=0.05):
    """Points on the front face (x = x0) and the top face of an L x W x H box whose bottom
    is z0 above the rail head, centred laterally at y0."""
    ys = np.arange(-W / 2, W / 2 + 1e-9, step)
    zs = np.arange(0, H + 1e-9, step)
    xs = np.arange(0, L + 1e-9, step)
    front = np.array([(x0, y0 + y, z0 + z) for y in ys for z in zs])
    top = np.array([(x0 + x, y0 + y, z0 + H) for x in xs for y in ys])
    return np.vstack([front, top]).astype(np.float32)


def clusters_of(pts, in_gauge=True, axis_valid=1e9):
    inten = np.full(len(pts), 30.0, np.float32)
    ig = np.full(len(pts), bool(in_gauge))
    return find_clusters(pts, inten, pts[:, 1], pts[:, 2], ig, CFG.cluster, axis_valid=axis_valid)


@pytest.mark.parametrize("name,pts", [
    ("thin linear (rail-like, 4 m x 0.1 x 0.1)", surface_box(18, 0.0, 0.0, 4.0, 0.1, 0.1)),
    ("low hardware (0.3 x 0.3 x 0.2 on the sleepers)", surface_box(20, 0.0, 0.0, 0.3, 0.3, 0.2)),
    ("wall-like (2.5 m tall at |lateral| 1.5)", surface_box(20, 1.5, 0.0, 0.5, 0.3, 2.5)),
    ("wall segment (2.5 m tall, 5 m long, 0.3 wide)", surface_box(18, 0.0, 0.0, 5.0, 0.3, 2.5)),
    ("linear side structure (4 m x 0.3 x 0.5 at lateral 1.0)", surface_box(18, 1.0, 0.0, 4.0, 0.3, 0.5)),
])
def test_infrastructure_shapes_are_filtered(name, pts):
    assert clusters_of(pts) == [], name


def test_box_at_20m_is_kept_and_zoned():
    box = surface_box(20, 0.0, 0.15, 0.5, 0.5, 0.5)
    out = clusters_of(box)
    assert len(out) == 1
    c = out[0]
    assert c.zone == "gauge" and c.n >= CFG.cluster.min_points and c.n_gauge >= CFG.cluster.gauge_min_points
    assert c.distance == pytest.approx(20.0, abs=0.01) and abs(c.lateral) < 0.05
    assert c.size[2] == pytest.approx(0.5, abs=0.06) and c.height_min == pytest.approx(0.15, abs=0.01)
    assert 0.0 < c.score <= 1.0
    # the same box with no point inside the strict gauge is advisory only
    assert [c.zone for c in clusters_of(box, in_gauge=False)] == ["warning"]
    # beyond the range where the axis is supported it is demoted to advisory
    assert [c.zone for c in clusters_of(box, axis_valid=10.0)] == ["warning"]
    # a person-sized cluster at 50 m survives the filters too
    assert [c.zone for c in clusters_of(surface_box(50, 0.0, 0.0, 0.4, 0.5, 1.7))] == ["gauge"]


def test_overhead_cluster_is_demoted():
    hanging = surface_box(20, 0.0, CFG.cluster.overhead_min_height + 0.2, 0.5, 0.5, 0.5)
    out = clusters_of(hanging)
    assert len(out) == 1 and out[0].zone == "warning" and out[0].height_min > CFG.cluster.overhead_min_height


# ---------------------------------------------------------------------------
# gauge
# ---------------------------------------------------------------------------

def test_point_in_default_gauge_profile():
    """v0.6: the organizers' envelope, |dy| <= 1.05 m, 0.12 <= h <= 3.0 m above the rail head."""
    prof = CFG.gauge.profile
    dy = np.array([0.0, 0.0, 1.2, 1.0, 1.5, 0.0, -0.9, -1.0, 0.5])
    h = np.array([1.0, 0.05, 0.3, 1.0, 1.0, 3.2, 0.2, 0.7, 2.9])
    #                in   below  side   in  wide  above  in-low  in   in-top
    assert point_in_polygon(dy, h, prof).tolist() == [True, False, False, True, False, False, True, True, True]


def test_widened_profile_keeps_inner_zone():
    wide = widened_profile(CFG.gauge, CFG.gauge.warning_margin)
    prof = np.asarray(CFG.gauge.profile)
    assert wide[:, 0].max() == pytest.approx(prof[:, 0].max() + CFG.gauge.warning_margin)
    assert wide[:, 0].min() == pytest.approx(prof[:, 0].min() - CFG.gauge.warning_margin)
    inner = np.abs(prof[:, 0]) < 0.99 * np.abs(prof[:, 0]).max()
    assert np.allclose(wide[inner], prof[inner])


def test_corridor_mask_strict_is_subset_of_wide():
    track = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(0.0, 100.0), center=0.0, yaw=0.0,
                       curvature=0.0, rail_offset=0.35)
    rng = np.random.default_rng(0)
    n = 20000
    xyz = np.stack([rng.uniform(-10, 300, n), rng.uniform(-3, 3, n), rng.uniform(-2.5, 3.5, n)], axis=1).astype(np.float32)
    mask, strict = corridor_mask(xyz, track, CFG.gauge)
    assert strict.sum() > 0 and mask.sum() > strict.sum()
    assert not (strict & ~mask).any()                                      # strict is a subset of wide
    X = xyz[:, 0]
    assert not mask[(X < CFG.gauge.range_min) | (X > CFG.gauge.range_max)].any()
    dy = xyz[:, 1] - track.center_y(X)
    h = xyz[:, 2] - track.rail_z(X)
    margin_only = mask & ~strict
    prof = np.asarray(CFG.gauge.profile)
    hw, top = float(np.abs(prof[:, 0]).max()), float(prof[:, 1].max())
    assert (np.abs(dy[margin_only]) > hw - 1e-6).all() and (np.abs(dy[margin_only]) <= hw + CFG.gauge.warning_margin + 1e-6).all()
    assert (h[strict] >= 0.12 - 1e-6).all() and (h[strict] <= top + 1e-6).all()


# ---------------------------------------------------------------------------
# track model on the synthetic tunnel (Open3D)
# ---------------------------------------------------------------------------

def test_track_model_on_synthetic_tunnel(tunnel):
    frame, _, gt = tunnel
    m = estimate_track(frame.xyz, CFG.track)
    assert abs(m.center - gt.center) < 0.15
    assert CFG.track.rails_head_height[0] <= m.rail_offset <= CFG.track.rails_head_height[1]
    assert m.rail_score >= CFG.track.rails_min_score
    for x in (10.0, 50.0):
        assert abs(m.floor_z(x) - gt.floor_z(x)) < 0.25, x
    assert np.isfinite(m.axis_valid) and m.axis_valid > CFG.track.walls_range[0]
    assert abs(m.yaw) < np.radians(0.5) and abs(m.curvature) < 1e-4    # the synthetic tunnel is straight
    m2 = estimate_track(frame.xyz, CFG.track, prev=m)                  # smoothing keeps it there
    assert abs(m2.center - gt.center) < 0.15 and np.isfinite(m2.axis_valid)


def _station_wall_scene(wall_curvature, rail_curvature, far_rails=True):
    """Rail bed with a platform-hall boundary that can bend independently of the rails."""
    rng = np.random.default_rng(72)
    x = rng.uniform(3, 110, 26000)
    bed = np.stack([x, rng.uniform(-1.1, 1.1, x.size),
                    -1.5 + rng.normal(0, 0.01, x.size)], axis=1)
    parts = [bed]
    for side in (-1, 1):
        x = rng.uniform(4, 85 if far_rails else 28, 15000)
        parts.append(np.stack([x, side * 0.795 + 0.5 * rail_curvature * x ** 2 + rng.normal(0, 0.015, x.size),
                               -1.16 + rng.normal(0, 0.005, x.size)], axis=1))
        x = rng.uniform(6, 150, 22000)
        parts.append(np.stack([x, side * 3.0 + 0.5 * wall_curvature * x ** 2 + rng.normal(0, 0.02, x.size),
                               rng.uniform(0.4, 1.5, x.size)], axis=1))
    return np.concatenate(parts).astype(np.float32)


def test_station_wall_curvature_is_checked_against_far_rails(monkeypatch):
    """Near rails lock but station walls invent a bend: a side structure is pulled into the
    gauge at 80 m. Two further rail slabs contradict it and restore the axis. A
    genuinely curved track (walls and rails agree) keeps its detection range."""
    from resense import track as track_module

    cfg = DetectorConfig()
    xyz = _station_wall_scene(1 / 3000, 0.0)

    def run(cloud):
        model = None
        for _ in range(6):
            model = estimate_track(cloud, cfg.track, prev=model)
        return model

    real_check = track_module._check_far_rails
    assert not cfg.track.rails_far_check_enabled
    monkeypatch.setattr(track_module, "_check_far_rails", lambda *args: pytest.fail("opt-in check ran by default"))
    unchecked = run(xyz)
    monkeypatch.setattr(track_module, "_check_far_rails", real_check)
    cfg.track.rails_far_check_enabled = True
    checked = run(xyz)
    assert unchecked.rail_slabs >= 2 and unchecked.axis_valid > 80
    assert abs(float(unchecked.center_y(80))) > 0.7  # platform edge at +1.4 m appears central
    assert abs(float(checked.center_y(80))) < 0.25, checked.to_dict()
    assert checked.axis_valid >= 80
    assert checked.axis_valid < unchecked.axis_valid

    # The same wall curvature with no independently observable far pair cannot be
    # treated as evidence of a contradiction; the old confidence policy remains.
    no_far = run(_station_wall_scene(1 / 3000, 0.0, far_rails=False))
    assert no_far.axis_valid > 80
    curved = run(_station_wall_scene(1 / 1000, 1 / 1000))
    assert curved.rail_slabs >= 2 and curved.axis_valid > 80, curved.to_dict()

    # At that range a 1.4 m platform edge is outside the envelope when the axis
    # follows the rails. A central person remains in the strict gauge, as does a
    # near-axis hanging cable; the correction is not an object-shape filter.
    def membership(model, pts):
        _, strict = corridor_mask(pts, model, cfg.gauge)
        return int(strict.sum())

    edge = surface_box(80, 1.4, 0.2, 0.3, 0.4, 1.0)
    person = surface_box(80, 0.0, 0.2, 0.4, 0.5, 1.7)
    cable = surface_box(35, 0.0, 0.6, 0.05, 0.05, 2.0)
    assert membership(unchecked, edge) > cfg.cluster.gauge_min_points
    assert membership(checked, edge) == 0
    assert membership(checked, person) > cfg.cluster.gauge_min_points
    assert membership(checked, cable) > cfg.cluster.gauge_min_points


def test_station_edge_false_event_and_central_obstacle_regression():
    """Full pipeline: a station edge at 80 m is an event with the hall-wall bend,
    but not with the rail-checked axis; a central object must still STOP."""
    from resense.detector import Detector
    from resense.frame import Frame

    scene = _station_wall_scene(1 / 3000, 0.0)
    edge = surface_box(80, 1.4, -0.96, 0.3, 0.4, 1.0)
    central = surface_box(80, 0.0, -0.96, 0.4, 0.5, 1.7)

    def run(extra, enable_far_check=False):
        points = np.concatenate([scene, extra])
        frame = Frame(xyz=points, intensity=np.full(points.shape[0], 30, np.float32))
        cfg = DetectorConfig()
        cfg.track.rails_far_check_enabled = enable_far_check
        det = Detector(cfg)
        results = [det.process(frame) for _ in range(8)]
        return results[-1]

    old_edge = run(edge)
    new_edge = run(edge, enable_far_check=True)
    new_central = run(central, enable_far_check=True)
    assert old_edge.obstacle, [(c.distance, c.lateral, c.reason) for c in old_edge.candidates]
    assert not new_edge.obstacle, [(c.distance, c.lateral, c.reason) for c in new_edge.candidates]
    assert new_central.obstacle and abs(new_central.nearest_distance - 80) < 1.0, (
        new_central.track.to_dict(), new_central.corridor_idx.size,
        [(c.distance, c.lateral, c.reason) for c in new_central.candidates])


def test_without_a_rail_pair_far_clusters_remain_advisory():
    from resense.detector import Detector

    det = Detector(DetectorConfig())
    det.track = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(3, 120),
                           center=0.0, yaw=0.0, curvature=0.0, axis_valid=150,
                           floor_verified=120, rail_slabs=0)
    pts = surface_box(80, 0, -0.9, 0.4, 0.5, 1.0)
    cand, _, _, _, (valid, _, _) = det._corridor(pts, np.full(pts.shape[0], 30, np.float32))
    clusters = det._cluster(cand, 1, valid, 120, None)
    assert valid == det.cfg.gauge.no_rail_range
    assert len(clusters) == 1 and clusters[0].zone == "warning" and clusters[0].reason == "beyond_axis"


# ---------------------------------------------------------------------------
# config round trip
# ---------------------------------------------------------------------------

def _flatten(d, prefix=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from _flatten(v, prefix + k + ".")
        else:
            yield prefix + k, v


def test_default_yaml_equals_code_defaults():
    """configs/default.yaml must never drift from the dataclass defaults (field by field)."""
    from_file = dict(_flatten(DetectorConfig.from_yaml(str(REPO / "configs" / "default.yaml")).to_dict()))
    from_code = dict(_flatten(DetectorConfig().to_dict()))
    assert set(from_file) == set(from_code)
    for k in from_code:
        assert from_file[k] == from_code[k], f"{k}: yaml {from_file[k]!r} != code {from_code[k]!r}"


def test_ros_parameters_in_sync_and_far_check_is_opt_in():
    canonical = REPO / "configs" / "default.yaml"
    ros = REPO / "ros2_ws" / "src" / "resense_ros" / "config" / "detector.yaml"
    assert canonical.read_text(encoding="utf-8") == ros.read_text(encoding="utf-8")
    assert not DetectorConfig().track.rails_far_check_enabled
    assert DetectorConfig.from_yaml(str(canonical)).to_dict() == DetectorConfig().to_dict()
    assert not DetectorConfig.from_yaml(str(ros)).track.rails_far_check_enabled
    enabled = DetectorConfig.from_dict({"track": {"rails_far_check_enabled": True}})
    assert enabled.track.rails_far_check_enabled


def test_unknown_config_key_raises():
    with pytest.raises(KeyError):
        DetectorConfig.from_dict({"tracking": {"confirm_hitz": 3}})
    with pytest.raises(KeyError):
        DetectorConfig.from_dict({"cluster": {"eps": 0.3, "bogus": 1}})
    cfg = DetectorConfig.from_dict({"tracking": {"confirm_hits": 5}, "track": {"rails_range": [5.0, 40.0]}})
    assert cfg.tracking.confirm_hits == 5 and cfg.track.rails_range == (5.0, 40.0)
    assert asdict(cfg.gauge) == asdict(DetectorConfig().gauge)


# ---------------------------------------------------------------------------
# PointCloud2 decoding with a hand-built message
# ---------------------------------------------------------------------------

class _Field:
    def __init__(self, name, offset, datatype, count=1):
        self.name, self.offset, self.datatype, self.count = name, offset, datatype, count


class _PointCloud2:
    """Mimics sensor_msgs/PointCloud2 as the Hesai driver fills it (point_step 26)."""

    def __init__(self, rows):
        self.fields = [_Field("x", 0, 7), _Field("y", 4, 7), _Field("z", 8, 7), _Field("intensity", 12, 7),
                       _Field("ring", 16, 4), _Field("timestamp", 18, 8)]
        self.point_step = 26
        self.height = 1
        self.width = len(rows)
        self.is_bigendian = False
        dt = np.dtype({"names": ["x", "y", "z", "intensity", "ring", "timestamp"],
                       "formats": ["f4", "f4", "f4", "f4", "u2", "f8"], "offsets": [0, 4, 8, 12, 16, 18], "itemsize": 26})
        arr = np.zeros(len(rows), dt)
        for i, r in enumerate(rows):
            arr[i] = r
        self.data = arr.tobytes()


def test_pointcloud2_decoding_drops_dual_return_zeros_and_keeps_ring_intensity():
    msg = _PointCloud2([
        (1.0, -20.0, -1.5, 12.0, 40, 1e9),      # valid
        (0.0, 0.0, 0.0, 0.0, 41, 1e9),          # empty dual-return slot
        (-2.0, -50.0, 0.4, 255.0, 64, 1e9),     # valid, retro-reflective
        (np.nan, 1.0, 1.0, 5.0, 3, 1e9),        # NaN
    ])
    st = pointcloud2_to_structured(msg)
    assert st.shape == (4,) and st.dtype.itemsize == 26 and st["ring"].tolist() == [40, 41, 64, 3]
    out = structured_to_compact(st)
    assert out.dtype == COMPACT_DTYPE and out.shape == (2,)
    assert out["x"].tolist() == [1.0, -2.0] and out["y"].tolist() == [-20.0, -50.0]
    assert out["intensity"].tolist() == [12.0, 255.0] and out["ring"].tolist() == [40, 64]


def test_node_decode_matches_the_compact_path_and_counts_near_returns():
    """pointcloud2_to_arrays (the node's one-pass decode, v0.6.2) = structured_to_compact + the
    node's former range crop; returns inside min_range are counted as near, not kept."""
    rng = np.random.default_rng(3)
    rows = [(float(x), float(y), float(z), float(i), int(r), 1e9) for x, y, z, i, r in
            zip(rng.uniform(-80, 80, 300), rng.uniform(-80, 80, 300), rng.uniform(-3, 3, 300),
                rng.uniform(0, 255, 300), rng.integers(0, 128, 300))]
    rows += [(0.0, 0.0, 0.0, 0.0, 5, 1e9)] * 30 + [(0.5, 0.3, 0.1, 9.0, 7, 1e9)] * 4 + [(300.0, 0.0, 0.0, 9.0, 7, 1e9)]
    msg = _PointCloud2(rows)
    xyz, inten, ring, n_raw, n_near = pointcloud2_to_arrays(msg, 2.5, 250.0)
    ref = structured_to_compact(pointcloud2_to_structured(msg))
    r2 = ref["x"] ** 2 + ref["y"] ** 2 + ref["z"] ** 2
    keep = (r2 >= 2.5 ** 2) & (r2 <= 250.0 ** 2)
    assert n_raw == len(ref) == 305 and n_near == 4 and xyz.shape == (int(keep.sum()), 3)
    assert np.array_equal(xyz[:, 0], ref["x"][keep]) and np.array_equal(xyz[:, 2], ref["z"][keep])
    assert np.array_equal(inten, ref["intensity"][keep]) and np.array_equal(ring, ref["ring"][keep])
    assert xyz.dtype == np.float32 and inten.dtype == np.float32 and ring.dtype == np.uint16


# ---------------------------------------------------------------------------
# scripts/check_dry_run.py (the captain's, loaded read-only)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def check_dry_run():
    path = REPO / "scripts" / "check_dry_run.py"
    spec = importlib.util.spec_from_file_location("check_dry_run", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _capture(path, n=60, alarms=(20, 21, 22, 23, 24), distance=55.5, latency=50.0, dropped=0, fps=9.9,
             recording=None):
    with open(path, "w") as fh:
        fh.write("garbage line\n")
        for i in range(n):
            alarm = i in alarms
            d = {"stamp": i * 0.1, "obstacle": alarm, "warning": False,
                 "nearest_distance": distance if alarm else None,
                 "detections": [{"id": 1, "distance": distance}] if alarm else [],
                 "timing_ms": {"total": latency - 5.0},
                 "node": {"latency_ms": latency + (i % 3), "fps": fps,
                          "dropped_frames": dropped(i) if callable(dropped) else dropped}}
            if recording is not None:
                d["node"]["recording"] = recording(i)
            fh.write(json.dumps(d) + "\n---\n")
    return str(path)


def test_check_dry_run_pass(check_dry_run, tmp_path, capsys):
    p = _capture(tmp_path / "ok.jsonl")
    assert check_dry_run.main([p, "--expect-obstacle", "--distance", "50:62"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out and "status messages      : 60 (1 lines skipped)" in out and "alarm frames         : 5" in out


@pytest.mark.parametrize("case,kwargs,args", [
    ("too few frames", dict(n=10), ["--expect-obstacle", "--distance", "50:62"]),
    ("no alarm", dict(alarms=()), ["--expect-obstacle", "--distance", "50:62"]),
    ("distance outside the window", dict(distance=70.0), ["--expect-obstacle", "--distance", "50:62"]),
    ("p95 latency too high", dict(latency=150.0), ["--expect-obstacle", "--distance", "50:62"]),
    ("dropped frames", dict(dropped=lambda i: 3 + (i >= 55) * 2), ["--expect-obstacle", "--distance", "50:62"]),
    ("alarms on a bag expected clear", dict(), ["--expect-clear"]),
    ("fps below the minimum", dict(fps=5.0), ["--expect-obstacle", "--min-fps", "9"]),
])
def test_check_dry_run_failures(check_dry_run, tmp_path, capsys, case, kwargs, args):
    p = _capture(tmp_path / "bad.jsonl", **kwargs)
    assert check_dry_run.main([p] + args) == 1, case
    assert "FAIL:" in capsys.readouterr().out


def test_check_dry_run_allows_the_known_alarm_frames_of_a_recording(check_dry_run, tmp_path, capsys):
    p = _capture(tmp_path / "known.jsonl", alarms=(40, 41), distance=129.0)
    assert check_dry_run.main([p, "--expect-clear"]) == 1
    assert check_dry_run.main([p, "--expect-clear", "--max-alarm-frames", "2"]) == 0
    assert check_dry_run.main([p, "--expect-clear", "--max-alarm-frames", "1"]) == 1
    assert "(allowed 1)" in capsys.readouterr().out



def test_check_dry_run_ignores_the_start_up_hole_and_takes_the_obstacle_recording(check_dry_run, tmp_path, capsys):
    """Review 23.09: frames lost in the first seconds (the DDS start-up of 5-10 MB reliable clouds)
    are not the node's drops; a clear recording may precede the one with the obstacle."""
    p = _capture(tmp_path / "startup.jsonl", dropped=9)                 # all 9 lost before the first frame
    assert check_dry_run.main([p, "--expect-obstacle"]) == 0
    assert check_dry_run.main([p, "--expect-obstacle", "--settle-s", "0"]) == 1
    two = _capture(tmp_path / "two.jsonl", n=80, alarms=range(60, 70), recording=lambda i: 1 + (i >= 40))
    args = [two, "--expect-obstacle", "--expect-inputs", "2"]
    assert check_dry_run.main(args) == 1                                # recording 1 is clear
    assert check_dry_run.main(args + ["--obstacle-in", "2"]) == 0
    assert "recording 1: 0 alarm frames" in capsys.readouterr().out


def _capture_stream(path, stamps, dropped, catchup=None, skipped=None, t0=946687298.1):
    """A capture of the given processed stamps (s after the first) with the node's counters."""
    with open(path, "w") as fh:
        for i, s in enumerate(stamps):
            node = {"latency_ms": 55.0, "fps": 10.0, "dropped_frames": dropped[i], "recording": 1,
                    "input_topic": "/sensing/lidar/hesai128/pointcloud", "input_period_ms": 100.0}
            if catchup is not None:
                node["catchup"] = catchup[i]
            if skipped is not None:
                node["catchup_skipped"] = skipped[i]
            fh.write(json.dumps({"stamp": t0 + s, "obstacle": 20 <= i < 30, "warning": False,
                                 "nearest_distance": 55.9 if 20 <= i < 30 else None,
                                 "timing_ms": {"total": 25.0}, "node": node}) + "\n---\n")
    return str(path)


def _played(until=19.5, catchup_end=7.9, holes=(), lost=()):
    """What the node processed of a bag played from its first frame: every 3rd frame while it
    catches up (to ``catchup_end``, None: to the end), then every frame; ``holes``: frames the
    recording lacks, ``lost``: frames that never reached the node (tenths of a second)."""
    stamps, dropped, flags, skipped, d, sk = [], [], [], [], 0, 0
    n = int(round(until * 10))
    for k in range(n + 1):
        if k in holes or k in lost:
            continue
        behind = catchup_end is None or k < round(catchup_end * 10)
        if behind and k % 3 and k != n:
            continue
        if stamps:
            miss = k - int(round(stamps[-1] * 10)) - 1
            d += miss
            sk += sum(1 for j in range(int(round(stamps[-1] * 10)) + 1, k) if j not in holes and j not in lost)
        stamps.append(k / 10)
        dropped.append(d)
        skipped.append(sk)
        flags.append(bool(behind))
    return stamps, dropped, flags, skipped


def test_check_dry_run_counts_drops_after_the_start_up_catchup(check_dry_run, tmp_path, capsys):
    """25.09, team VM: the player's preload left the node 4.8 s behind, its catch-up (one frame per
    0.3 s of recording) ran to +7.9 s, and its own skips failed --max-dropped 0 (20 after the first
    5 s). The settle point is now the later of 5 s and the end of the start-up catch-up (node.catchup),
    at most --max-settle-s; frames lost after it still fail, and so does a catch-up that never ends."""
    stamps, dropped, flags, skipped = _played()
    args = ["--expect-obstacle", "--distance", "50:62"]
    p = _capture_stream(tmp_path / "a.jsonl", stamps, dropped, flags, skipped)
    assert check_dry_run.main([p] + args) == 0
    out = capsys.readouterr().out
    assert "back on the newest frame at +7.9 s" in out and "0 after +7.9 s (the end of the start-up catch-up)" in out
    assert f"dropped input frames : {dropped[-1]} ({skipped[-1]} of them skipped" in out
    old = _capture_stream(tmp_path / "old.jsonl", stamps, dropped)            # a node without node.catchup
    assert check_dry_run.main([old] + args) == 1
    assert "dropped input frames after the first 5 s > 0" in capsys.readouterr().out
    stamps, dropped, flags, skipped = _played(lost=(120, 121))                  # 2 frames lost at +12 s
    p = _capture_stream(tmp_path / "b.jsonl", stamps, dropped, flags, skipped)
    assert check_dry_run.main([p] + args) == 1
    assert "FAIL: 2 dropped input frames after +7.9 s (the end of the start-up catch-up) > 0" in capsys.readouterr().out
    stamps, dropped, flags, skipped = _played(catchup_end=None)                # never back on the newest frame
    p = _capture_stream(tmp_path / "c.jsonl", stamps, dropped, flags, skipped)
    assert check_dry_run.main([p] + args) == 1
    out = capsys.readouterr().out
    assert "never back on the newest frame" in out and "after the first 5 s (the start-up catch-up never ended)" in out
    assert check_dry_run.main([p] + args + ["--max-settle-s", "30"]) == 1       # a recording shorter than the cap too
    flags[-1] = False                     # behind all along: on the newest frame only when the input stopped
    p = _capture_stream(tmp_path / "c2.jsonl", stamps, dropped, flags, skipped)
    assert check_dry_run.main([p] + args + ["--max-settle-s", "30"]) == 1
    assert "never back on the newest frame" in capsys.readouterr().out
    stamps, dropped, flags, skipped = _played(catchup_end=12.0)
    p = _capture_stream(tmp_path / "d.jsonl", stamps, dropped, flags, skipped)
    assert check_dry_run.main([p] + args) == 0
    assert check_dry_run.main([p] + args + ["--max-settle-s", "10"]) == 1


def _bag(path, holes=(), n=196, recv0=1788354623.11, header0=946687297.2, topic="/sensing/lidar/hesai128/pointcloud"):
    """A rosbag2 sqlite3 bag of ``n`` 10 Hz frame slots of which ``holes`` were never recorded,
    with receive-time jitter; only the first message carries a (CDR) header, all the checker reads."""
    import sqlite3
    import struct
    path.mkdir()
    con = sqlite3.connect(path / f"{path.name}_0.db3")
    con.executescript("CREATE TABLE topics(id INTEGER PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,"
                      " serialization_format TEXT NOT NULL, offered_qos_profiles TEXT NOT NULL);"
                      "CREATE TABLE messages(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL,"
                      " timestamp INTEGER NOT NULL, data BLOB NOT NULL);")
    con.execute("INSERT INTO topics VALUES (1, '/imu', 'sensor_msgs/msg/Imu', 'cdr', '')")
    con.execute("INSERT INTO topics VALUES (2, ?, 'sensor_msgs/msg/PointCloud2', 'cdr', '')", (topic,))
    jitter = np.random.default_rng(0).uniform(-0.03, 0.03, n)
    first = True
    for k in range(n):
        if k in holes:
            continue
        data = b""
        if first:            # CDR little-endian: encapsulation 00 01 00 00, then header.stamp sec / nanosec
            h = header0 + 0.1 * k
            data = b"\x00\x01\x00\x00" + struct.pack("<iI", int(h), int(round((h % 1) * 1e9)))
            first = False
        con.execute("INSERT INTO messages (topic_id, timestamp, data) VALUES (2, ?, ?)",
                    (int(round((recv0 + 0.1 * k + jitter[k]) * 1e9)), data))
        con.execute("INSERT INTO messages (topic_id, timestamp, data) VALUES (1, ?, ?)",
                    (int(round((recv0 + 0.1 * k + 0.05) * 1e9)), b""))
    con.commit()
    con.close()
    return str(path)


def test_check_dry_run_bag_holes_are_not_drops(check_dry_run, tmp_path, capsys):
    """doubleT_obstacle lacks 4 frames itself (bag receive-time gaps of 0.201 s and 0.413 s at +14.0
    and +16.9 s): the node's stamp-gap counter sees them in every run. With --bag the checker
    counts the recording's messages the node did not process instead."""
    holes = {139 + 9, 166 + 9, 167 + 9, 168 + 9}     # slots of the bag; the node's first frame is slot 9
    stamps, dropped, flags, skipped = _played(until=18.6, holes={h - 9 for h in holes})
    p = _capture_stream(tmp_path / "a.jsonl", stamps, dropped, flags, skipped, t0=946687297.2 + 0.9)
    bag = _bag(tmp_path / "doubleT_obstacle", holes=holes)
    args = [p, "--expect-obstacle", "--distance", "50:62"]
    assert check_dry_run.main(args) == 1
    assert "FAIL: 4 dropped input frames after +7.9 s" in capsys.readouterr().out
    assert check_dry_run.main(args + ["--bag", bag]) == 0
    out = capsys.readouterr().out
    assert "4 frame(s) missing from the recording itself; 0 of its messages not processed" in out
    stamps, dropped, flags, skipped = _played(until=18.6, holes={h - 9 for h in holes}, lost={100})
    p = _capture_stream(tmp_path / "b.jsonl", stamps, dropped, flags, skipped, t0=946687297.2 + 0.9)
    assert check_dry_run.main([p, "--bag", bag]) == 1
    assert "FAIL: 1 frames of the recording not processed after +7.9 s" in capsys.readouterr().out
    assert check_dry_run.main([p, "--bag", str(tmp_path)]) == 1                 # no bag there: the counter decides
    assert "--bag not applied: no readable rosbag2 sqlite3 bag" in capsys.readouterr().out
    assert check_dry_run.cdr_stamp(b"\x00\x00\x00\x00" + (946687297).to_bytes(4, "big")
                                   + (200101000).to_bytes(4, "big")) == pytest.approx(946687297.200101)


def test_check_dry_run_empty_capture(check_dry_run, tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("---\n")
    assert check_dry_run.main([str(p)]) == 2
    assert check_dry_run.percentile([1.0, 2.0, 3.0, 4.0], 95) == pytest.approx(np.percentile([1, 2, 3, 4], 95))


def test_check_dry_run_rejects_missing_metrics_and_fault_only_capture(check_dry_run, tmp_path, capsys):
    capture = tmp_path / "missing_metrics.jsonl"
    capture.write_text("".join(json.dumps({"obstacle": False, "stamp": i * 0.1}) + "\n" for i in range(60)))
    assert check_dry_run.main([str(capture)]) == 1
    out = capsys.readouterr().out
    assert "node.latency_ms missing" in out and "node.dropped_frames missing" in out

    capture.write_text("".join(json.dumps({"obstacle": False, "stamp": i * 0.1,
                                           "node": {"latency_ms": float("nan"), "dropped_frames": "0"}}) + "\n"
                               for i in range(60)))
    assert check_dry_run.main([str(capture)]) == 1
    out = capsys.readouterr().out
    assert "latency_ms missing or invalid" in out and "dropped_frames missing or invalid" in out

    capture.write_text("".join(json.dumps({"obstacle": False, "decision": "FAULT", "stamp": i * 0.1}) + "\n"
                               for i in range(60)))
    assert check_dry_run.main([str(capture)]) == 2
    assert "no status messages parsed" in capsys.readouterr().out


def test_bench_empty_input_has_a_diagnostic(tmp_path):
    with pytest.raises(SystemExit, match="no input frames"):
        run_cli(["bench", "--npy", str(tmp_path)])


# ---------------------------------------------------------------------------
# CLI smoke on two cached synthetic frames (Open3D)
# ---------------------------------------------------------------------------

def test_cli_run_bench_summarize(synth_npy_dir, tmp_path, capsys):
    jsonl = tmp_path / "run.jsonl"
    run_cli(["run", "--npy", str(synth_npy_dir), "--out", str(jsonl), "--quiet"])
    lines = [json.loads(ln) for ln in open(jsonl)]
    assert [ln["frame"] for ln in lines] == [0, 1] and lines[0]["frame_id"] == "synthetic_0000.npy"
    assert {"stamp", "obstacle", "warning", "nearest_distance", "detections", "warnings", "track", "timing_ms"} <= set(lines[0])
    assert not lines[1]["obstacle"] and lines[1]["timing_ms"]["total"] > 0
    capsys.readouterr()
    run_cli(["bench", "--npy", str(synth_npy_dir)])
    out = capsys.readouterr().out
    assert "total" in out and "p95" in out
    s = run_cli(["summarize", str(jsonl)])
    assert s["frames"] == 2 and s["alarm_frames"] == 0 and s["fp_events"] == 0 and s["frame_stride"] == 1


def test_cli_inject_and_eval(synth_npy_dir, tmp_path, capsys):
    out = tmp_path / "inj"
    run_cli(["inject", "--npy", str(synth_npy_dir), "--limit", "1", "--out", str(out), "--kinds", "box0.5",
          "--distances", "30:30", "--negative-fraction", "0", "--seed", "1"])
    assert sorted(os.listdir(out)) == ["00000.npz", "gt.json"]
    res = run_cli(["eval", str(out), "--text"])
    assert res["frames"] == 1 and res["recall"] == 1.0
    assert "recall            : 100.0%" in capsys.readouterr().out
