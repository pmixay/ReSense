"""The diagnostic must preserve decisions and attribute source returns without loose matching."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("trace_object_failures", ROOT / "scripts/trace_object_failures.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

from resense import clustering  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame  # noqa: E402
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame  # noqa: E402
from trace_detector_stages import TraceDetector  # noqa: E402


def frame(points, intensity=None, ring=None):
    xyz = np.asarray(points, np.float32)
    return Frame(xyz, np.asarray(intensity if intensity is not None else np.ones(len(xyz)), np.float32),
                 np.asarray(ring if ring is not None else np.zeros(len(xyz)), np.uint16))


def test_source_attribution_uses_intensity_and_ring():
    cached = frame([[10, 0, 1]] * 3, [1, 2, 1], [0, 0, 1])
    source = frame([[10, 0, 1]])
    ids, extra = module.source_indices(module.point_keys(cached), module.point_keys(source))
    assert ids.tolist() == [0]
    assert extra == 0


def test_source_attribution_preserves_multiplicity_and_reports_equal_background_copy():
    cached = frame([[10, 0, 1]] * 3)
    source = frame([[10, 0, 1]] * 2)
    ids, extra = module.source_indices(module.point_keys(cached), module.point_keys(source))
    assert len(ids) == len(set(ids.tolist())) == 2
    assert extra == 1


def test_missing_source_return_fails_closed():
    with pytest.raises(RuntimeError, match="source return missing"):
        module.source_indices(module.point_keys(frame([[10, 0, 1]])),
                              module.point_keys(frame([[10, 0, 1]] * 2)))


def test_records_actual_rejection_return_condition_and_restores_function():
    points = np.asarray([[20, 0, 0], [20.2, 0, 0.3], [20, 0.2, 0.3], [20.2, 0.2, 0]], np.float32)
    blob = clustering._Blob.of(points, np.arange(4), 4)
    detector = TraceDetector()
    detector.target_groups = {"object": np.arange(4)}
    detector.target_indices = np.arange(4)
    detector.trace = {"blobs": []}
    original = clustering._corridor_cluster
    with detector._observe_blobs():
        result = clustering._corridor_cluster(blob, points[:, 1], points[:, 2], np.ones(4, bool),
                                             np.ones(4), np.arange(4), np.arange(4), detector.cfg.cluster,
                                             1.0, 40.0, 100.0, 100.0)
    assert result is None
    assert clustering._corridor_cluster is original
    record = detector.trace["blobs"][0]
    assert record["target_points"] == 4
    # Below the point-count bar and without weak_from, neither the ordinary weak path nor
    # the opt-in cross-ring relaxation is eligible. The trace records their joint rejection.
    assert record["returns"][-1]["condition"] == "not (ordinary or cross_ring)"
    assert record["returns"][-1]["value"] is None
    assert sys.getprofile() is None


@pytest.mark.synthetic
@pytest.mark.parametrize("fresh", [False, True])
def test_tracing_preserves_stateful_detector_output(fresh):
    cloud, labels, _ = synthetic_tunnel_frame(rng=np.random.default_rng(12), specs=[
        ObstacleSpec(kind="box", size=(0.3, 0.3, 0.3), distance=25, lateral=0, base_z=-0.2)])
    cfg = DetectorConfig()
    cfg.tracking.fresh_stop_evidence = fresh
    plain, traced = Detector(cfg), TraceDetector(DetectorConfig.from_dict(cfg.to_dict()))
    original = clustering._corridor_cluster
    targets = np.flatnonzero(labels == 1)
    assert len(targets) > 0
    for k in range(8):
        current = Frame(cloud.xyz, cloud.intensity, stamp=0.1 * k)
        actual = traced.process_target(current, {"cube": targets}).to_dict()
        expected = plain.process(current).to_dict()
        assert module.semantic(actual) == module.semantic(expected)
        assert traced.trace["geometry"]["groups"]["cube"]["points"] == len(targets)
        assert clustering._corridor_cluster is original
    assert traced.trace["blobs"]
    assert traced.trace["tracker_hits"]
    if fresh:
        assert all(hit["evidence_after"] for hit in traced.trace["tracker_hits"].values())
