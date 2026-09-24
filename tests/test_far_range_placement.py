"""Set F placement contract: deterministic independent truth, without Open3D or bag files."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from resense.config import TrackConfig
from resense.frame import Frame
from resense.synthetic import InjectionResult
from resense.track import TrackModel

# Load the repository script by path. Docker deliberately runs these tests from ``/`` so the
# installed ``resense`` package is tested rather than the source tree; a top-level ``scripts``
# import would otherwise depend on the current working directory.
_FAR_PATH = Path(__file__).resolve().parents[1] / "scripts" / "far_range_eval.py"
_FAR_SPEC = importlib.util.spec_from_file_location("resense_far_range_eval", _FAR_PATH)
assert _FAR_SPEC is not None and _FAR_SPEC.loader is not None
far = importlib.util.module_from_spec(_FAR_SPEC)
sys.modules[_FAR_SPEC.name] = far
_FAR_SPEC.loader.exec_module(far)


def test_fixed_reference_never_reads_far_points(monkeypatch):
    ref = far.fixed_reference(0.2, 0.5, 0.001, -1.1, -0.01)
    def forbidden(*args, **kwargs):
        raise AssertionError("independent placement must not fit the cloud or read vault drift")

    monkeypatch.setattr("resense.track.estimate_track", forbidden)
    monkeypatch.setattr(far, "vault_drift", forbidden)
    monkeypatch.setattr("resense.synthetic.local_bed_z", forbidden)
    # Two otherwise identical backgrounds, with arbitrarily changed far returns. Placement
    # accepts neither background as input; in particular no far observation can be an anchor.
    near = np.array([[10., 0., -1.], [20., 0., -1.]])
    placements = []
    for far_points in (np.array([[150., 3., 3.]]), np.array([[150., -30., -8.]])):
        cloud = np.concatenate([near, far_points])
        assert cloud.shape == (3, 3)
        spec, track = far.independent_placement("box0.5", 150., 0.6, 30., ref, -0.2, 15., "bed")
        placements.append((spec.to_dict(), float(track.center_y(150.25))))
    assert placements[0] == placements[1]
    assert spec.to_dict()["reference"] == ref
    assert spec.to_dict()["perturbation"] == {"lateral_m": -0.2, "yaw_deg": 15.,
                                               "nominal_lateral_m": 0.6}
    assert spec.lateral == pytest.approx(0.4)
    assert spec.base_z == pytest.approx(float(track.rail_z(150.25)) - 0.25)


def test_legacy_and_independent_respond_differently_to_far_axis(monkeypatch):
    def fitted(xyz, cfg, prev):
        return TrackModel(np.array([0., 0., -1.]), (4., 40.),
                          center=float(xyz[-1, 1]), yaw=0., curvature=0., rail_offset=0.)

    monkeypatch.setattr("resense.track.estimate_track", fitted)
    ref = far.fixed_reference(0., 0., 0., -1., 0.)
    legacies = []
    independents = []
    for far_y in (0., 3.):
        xyz = np.array([[10., 0., -1.], [150., far_y, 3.]])
        old, old_axis = far.legacy_placement(xyz, TrackConfig(), None, "box0.5", 150., 0., 30., "rail")
        new, new_axis = far.independent_placement("box0.5", 150., 0., 30., ref, 0., 0., "rail")
        legacies.append(float(old_axis.center_y(150.25)) + old.lateral)
        independents.append(float(new_axis.center_y(150.25)) + new.lateral)
        assert old.reference is None and old.perturbation is None
        assert old.base_z == new.base_z == -1.
    assert legacies == [0., 3.]
    assert independents == [0., 0.]


def test_independent_match_uses_vehicle_coordinates():
    ref = far.fixed_reference(0., 0., 0., -1., 0.)
    sp, physical = far.independent_placement("box0.5", 100., 0., 30., ref, 0., 0., "rail")
    biased = TrackModel(np.array([0., 0., -1.]), (0., 100.), center=2., yaw=0., curvature=0.)
    det = SimpleNamespace(distance=100., lateral=0.)
    assert far.placement_match(det, 100., sp, physical, biased, "legacy")
    assert not far.placement_match(det, 100., sp, physical, biased, "independent")
    det.lateral = -2.
    assert far.placement_match(det, 100., sp, physical, biased, "independent")


def test_sequence_does_not_fit_far_cloud_and_writes_ground_truth(monkeypatch):
    from resense.config import DetectorConfig

    ref = far.fixed_reference(0., 0., 0., -1., 0.)
    cloud = np.array([[10., 0., -1.], [150., 8., 4.]], dtype=np.float32)

    def frame_from_compact(arr, sensor, stamp, frame_id):
        return Frame(xyz=cloud.copy(), intensity=np.zeros(2), stamp=stamp, frame_id=frame_id)

    def inject(frame, track, specs, **kwargs):
        return InjectionResult(frame=frame, labels=np.array([0, 1]), n_added=[1])

    class FakeDetector:
        def __init__(self, cfg):
            self.track = None

        def process(self, frame, ego_speed):
            track = TrackModel(np.array([0., 0., -1.]), (0., 100.), 0., 0., 0.)
            return SimpleNamespace(track=track, detections=[SimpleNamespace(distance=150., lateral=0.,
                                                                              size=[0.5] * 3, kind="box")],
                                   candidates=[], health={})

    def forbidden(*args, **kwargs):
        raise AssertionError("far-frame fitting leaked into placement")

    monkeypatch.setattr("resense.track.estimate_track", forbidden)
    monkeypatch.setattr(far, "vault_drift", forbidden)
    monkeypatch.setattr("resense.frame.frame_from_compact", frame_from_compact)
    monkeypatch.setattr("resense.synthetic.inject_obstacles", inject)
    monkeypatch.setattr("resense.detector.Detector", FakeDetector)
    monkeypatch.setattr(far.np, "load", lambda _: None)
    job = (["new_data_46_000.npy"], {"new_data_46_000": 1.}, [20.], "box0.5", 150., 0., 30., 1,
           DetectorConfig().to_dict(), None, False, "rail", "independent", ref, 0.3, 12.)
    first = far.run_sequence(job)
    cloud[-1, 1] = -8.
    second = far.run_sequence(job)
    assert first == second
    row = first["rows"][0]
    assert row["n"] == 1 and row["hit"]
    assert row["gt"]["reference"] == ref
    assert row["gt"]["perturbation"]["yaw_deg"] == 12.
    assert row["gt_vehicle_y_m"] == pytest.approx(0.3)


def test_zero_return_cannot_be_claimed_by_a_nearby_background_detection(monkeypatch):
    from resense.config import DetectorConfig

    track = TrackModel(np.array([0., 0., -1.]), (0., 100.), 0., 0., 0.)
    frame = Frame(np.array([[10., 0., -1.]], dtype=np.float32), np.array([0.]))

    class BackgroundDetection:
        def __init__(self, cfg):
            self.track = track

        def process(self, injected, ego_speed):
            return SimpleNamespace(track=track,
                                   detections=[SimpleNamespace(distance=50., lateral=0., size=[0.5] * 3,
                                                               kind="box")], candidates=[], health={})

    monkeypatch.setattr("resense.frame.frame_from_compact", lambda *a, **kw: frame)
    monkeypatch.setattr("resense.detector.Detector", BackgroundDetection)
    monkeypatch.setattr("resense.synthetic.inject_obstacles", lambda *a, **kw:
                        InjectionResult(frame=frame, labels=np.zeros(1, int), n_added=[0]))
    monkeypatch.setattr(far.np, "load", lambda _: None)
    job = (["new_data_46_0000.npy"], {"new_data_46_0000": 1.}, [0.], "box0.5", 50., 0., 30., 1,
           DetectorConfig().to_dict(), None, False, "rail", "independent",
           far.fixed_reference(0., 0., 0., -1., 0.), 0., 0.)
    result = far.run_sequence(job)
    assert result["first"] is None and result["fp"] == 1
    assert result["rows"][0]["n"] == 0 and not result["rows"][0]["hit"]


def test_zero_return_injection_retains_reference_metadata(monkeypatch):
    from resense import synthetic

    class NoHits:
        def numpy(self):
            return np.array([np.inf])

    class Scene:
        def add_triangles(self, mesh):
            pass

        def cast_rays(self, rays):
            return {"t_hit": NoHits(), "geometry_ids": NoHits()}

    o3d = SimpleNamespace(t=SimpleNamespace(geometry=SimpleNamespace(RaycastingScene=Scene)),
                          core=SimpleNamespace(Tensor=lambda x: x))
    o3d.t.geometry.TriangleMesh = SimpleNamespace(from_legacy=lambda mesh: mesh)
    monkeypatch.setattr(synthetic, "_o3d", lambda: o3d)
    monkeypatch.setattr(synthetic, "obstacle_mesh", lambda spec, track: None)
    monkeypatch.setattr(synthetic, "ray_directions", lambda: np.array([[1., 0., 0.]]))
    ref = far.fixed_reference(0., 0., 0., -1., 0.)
    sp, track = far.independent_placement("box0.5", 180., 0., 25., ref, 0.2, 5., "bed")
    frame = Frame(np.array([[10., 0., 0.]], dtype=np.float32), np.array([1.]))
    res = synthetic.inject_obstacles(frame, track, [sp])
    assert res.n_added == [0] and res.labels.tolist() == [0]
    assert res.frame.meta["obstacles"][0]["reference"] == ref
    assert res.frame.meta["obstacles"][0]["perturbation"]["lateral_m"] == 0.2
