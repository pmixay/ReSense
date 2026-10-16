"""Accepted-only shipping selection: H1 free-top is off; explicit development opt-in remains.

These guards test withdrawal, not satisfaction of the archived H4 feature criteria.
"""
from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import resense.clustering as clustering
from resense.cli import _cfg, cmd_run
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.tracking import Tracker
from test_column_free_top import _clusters, _pole, _the


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "configs/default.yaml"
ROS = ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"


@pytest.fixture(params=["class", "cli", "yaml", "ros"])
def shipping_config(request):
    if request.param == "class":
        return DetectorConfig()
    if request.param == "cli":
        return _cfg(SimpleNamespace(config=None))
    return DetectorConfig.from_yaml(str(CANONICAL if request.param == "yaml" else ROS))


def test_shipping_selection_and_retained_parameters(shipping_config):
    cfg = shipping_config
    assert cfg.cluster.column_free_max_top == 0.0
    assert (cfg.cluster.column_free_min_core, cfg.cluster.column_free_min_returns,
            cfg.cluster.column_free_window, cfg.cluster.column_free_vault_margin,
            cfg.cluster.column_free_tall_gap) == (0.5, 2, 1.2, 0.3, 0.0)
    assert (cfg.cluster.structure_cut_tol, cfg.cluster.structure_cut_min_points) == (1.3, 8)
    assert cfg.track.axis_wall_drift == 0.8


def test_shipping_yaml_and_ros_mirror_are_identical():
    assert CANONICAL.read_bytes() == ROS.read_bytes()
    assert DetectorConfig.from_yaml(str(CANONICAL)).cluster.column_free_max_top == 0.0


def test_same_physical_pole_only_explicit_opt_in_can_be_spared(shipping_config, monkeypatch):
    cfg = shipping_config
    assert cfg.cluster.column_free_max_top == 0.0
    experimental = copy.deepcopy(cfg)
    experimental.cluster.column_free_max_top = 2.95
    boxes = [_pole(60.0, 0.7)]
    opted_in = _the(_clusters(boxes, experimental, heights=True), 60.0)
    assert (opted_in.zone, opted_in.reason, opted_in.spared) == ("gauge", "", True)

    def forbidden(*args, **kwargs):
        pytest.fail("shipping clustering called the withdrawn free-top path")

    monkeypatch.setattr(clustering, "top_is_free", forbidden)
    # The master switch also disables the otherwise separately configurable tall path.
    cfg.cluster.column_free_tall_gap = 0.3
    shipped = _the(_clusters(boxes, cfg, heights=True), 60.0)
    np.testing.assert_array_equal(shipped.points_idx, opted_in.points_idx)
    np.testing.assert_array_equal(shipped.bbox_min, opted_in.bbox_min)
    np.testing.assert_array_equal(shipped.bbox_max, opted_in.bbox_max)
    assert shipped.n_gauge == opted_in.n_gauge
    assert (shipped.zone, shipped.reason, shipped.spared) == ("warning", "column", False)
    tracker = Tracker(cfg.tracking)
    for _ in range(20):
        tracker.update([copy.deepcopy(shipped)], frame_dt=0.1)
        assert not any(t.zone == "gauge" for t in tracker.confirmed())
        for t in tracker.tracks:
            assert not any(t.spare_hist)
            assert not any(t.provisional_explained_hist)


@pytest.mark.parametrize("entry", ["ordinary", "cli"])
def test_default_detector_and_cli_never_enter_free_top(tunnel, monkeypatch, entry):
    frame, _, _ = tunnel
    seen = []
    process = Detector.process

    def forbidden(*args, **kwargs):
        pytest.fail("default detector/CLI invoked the withdrawn free-top algorithm")

    def observed(self, *args, **kwargs):
        assert self.cfg.cluster.column_free_max_top == 0.0
        result = process(self, *args, **kwargs)
        assert all(not c.spared for c in result.candidates)
        assert all(not any(t.spare_hist) and not any(t.provisional_explained_hist) for t in self.tracker.tracks)
        seen.append(result)
        return result

    monkeypatch.setattr(clustering, "top_is_free", forbidden)
    monkeypatch.setattr(Detector, "process", observed)
    frames = [(k, replace(frame, stamp=k * 0.1)) for k in range(6)]
    if entry == "ordinary":
        detector = Detector()
        for _, fr in frames:
            detector.process(fr)
    else:
        import resense.cli as cli
        monkeypatch.setattr(cli, "_frames", lambda *args, **kwargs: iter(frames))
        cmd_run(SimpleNamespace(config=None, out=None, render=None, quiet=True, ego_speed=None))
    assert len(seen) == len(frames)
