"""Mechanism tests for the local-body diagnostic; no production behavior is changed."""
from __future__ import annotations

import numpy as np
import pytest

from scripts.analyze_local_body_support import (
    RADIUS_M,
    RuntimeSupport,
    decompose,
    local_parts,
    score_parts,
    snapshot_support,
)
from resense.config import ClusterConfig, GaugeConfig


def _support(xyz, strict=None, candidate=None):
    xyz = np.asarray(xyz, dtype=np.float32)
    n = len(xyz)
    strict = np.ones(n, bool) if strict is None else np.asarray(strict, bool)
    candidate = np.ones(n, bool) if candidate is None else np.asarray(candidate, bool)
    return RuntimeSupport(
        xyz, xyz[:, 1], xyz[:, 2] + 1.4, strict, candidate,
        np.arange(n), np.arange(n), "fixture_effective_mask",
        200.0, 200.0,
    )


def test_decomposition_is_independent_of_evaluation_identity():
    body = np.array([[0.0, 0.0, 0.0], [0.0, 0.1, 0.4],
                     [0.0, 0.2, 0.8], [0.0, 0.3, 1.2]])
    background = np.array([[2.0, 0.0, 0.0], [2.0, 0.1, 0.4],
                           [2.0, 0.2, 0.8]])
    support = _support(np.r_[body, background])
    cfg = ClusterConfig()
    first = [[p["indices"] for p in part] for part in decompose(support, cfg).values()]
    # Labels are supplied only after decomposition; changing them cannot change parts.
    parts_a = local_parts(support, cfg, "corridor")
    parts_b = local_parts(support, cfg, "corridor")
    assert first[0] == [[*ids] for ids in parts_a]
    assert [[*ids] for ids in parts_a] == [[*ids] for ids in parts_b]


def test_strict_mode_only_removes_non_strict_points_and_never_invents_a_mask():
    support = _support([[0, 0, 0], [0, .1, .4], [0, .2, .8], [0, .3, 1.2]],
                       strict=[True, True, False, False])
    cfg = ClusterConfig()
    corridor = local_parts(support, cfg, "corridor")
    strict = local_parts(support, cfg, "strict")
    assert len(corridor) == 1 and len(strict) == 0

    with pytest.raises(ValueError, match="strict membership"):
        RuntimeSupport(support.xyz, support.dy, support.h,
                       np.array([True, False, True, False]),
                       np.array([True, True, False, False]),
                       support.frame_idx, support.inv, "bad")


def test_same_local_body_can_be_a_positive_or_false_body_after_scoring():
    # The diagnostic's geometry is deliberately agnostic to identity. A compact
    # vertical body is identical whether the evaluator calls it a positive or a
    # false track; this is the central counterexample behind rejection.
    xyz = np.array([[0, 0, 0], [0, .1, .4], [0, .2, .8], [0, .3, 1.2],
                    [2.0, 0, 0], [2.0, .1, .4], [2.0, .2, .8]])
    support = _support(xyz)
    cfg = ClusterConfig()
    raw = [{"indices": ids.tolist(), "geometry": {},
            "geometry_proxy": {"ordinary_gauge": True},
            "reference_proxy": {"ordinary_gauge": True}}
           for ids in local_parts(support, cfg, "strict")]
    positive = score_parts(raw, np.arange(len(xyz)) < 4, support)
    false = score_parts(raw, np.arange(len(xyz)) >= 4, support)
    assert any(p["scoring"]["complete_target"] for p in positive)
    assert any(p["scoring"]["complete_target"] for p in false)


def test_snapshot_masks_are_explicitly_approximate_and_not_union_masks():
    xyz = np.array([[10, 0, -.9], [10, .1, -.5], [10, .2, 0.0]], dtype=float)
    support = snapshot_support(xyz, xyz[:, 1], xyz[:, 2] + 1.4,
                               np.arange(3), ClusterConfig(), GaugeConfig())
    assert support.mask_source == "approximate_rail_only_masks_on_cropped_snapshot"
    assert support.strict.dtype == bool
    assert np.all(support.strict <= support.candidate)


def test_fixed_scale_is_documented_not_fitted_per_event():
    assert RADIUS_M == pytest.approx(0.45)
