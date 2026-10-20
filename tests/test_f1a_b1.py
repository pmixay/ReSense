"""B1: a fragmented low obstacle must not supply its own rail-head reference."""
from __future__ import annotations

import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.lowobj import low_free_mask
from resense.tracking import Tracker
from test_f1_false_alarms import HALF, _long_object_on_the_left_rail, _low, _rails


@pytest.mark.parametrize("side", [-1, 1])
@pytest.mark.parametrize("offset,cant", [(0.0, 0.0), (0.10, 0.0), (0.04, 0.06)])
@pytest.mark.parametrize("support", ["both", "own", "none"])
def test_default_f1a_keeps_fragmented_rail_obstacle(side, offset, cant, support):
    (X, dy, h), pieces = _long_object_on_the_left_rail()
    dy *= side
    h += offset + cant * dy / (2 * HALF)
    for c in pieces:
        c.lateral = side * HALF
        c.bbox_min[1], c.bbox_max[1] = c.lateral - 0.15, c.lateral + 0.15
        c.height_max = offset + cant * side / 2 + 0.08
    # Remove raw rail returns without changing object indices.
    raw_end = int(pieces[0].points_idx[0])
    if support != "both":
        keep = (side * dy[:raw_end] > 0) if support == "own" else np.zeros(raw_end, dtype=bool)
        h[:raw_end][~keep] = -1.0
    det = Detector(DetectorConfig())
    det._low_height = []
    xyz = np.column_stack([X, dy, h]).astype(np.float32)
    kept = det._rail_reference(pieces, xyz, dy, h)
    assert len(kept) == 6
    assert not det._low_height
    assert all(c.zone == "gauge" and not c.low_height_weak for c in kept)


def test_default_f1a_keeps_fragments_on_both_rails_and_confirms_them():
    (X, dy, h), left = _long_object_on_the_left_rail()
    right = []
    for c in left:
        idx = np.arange(X.size, X.size + c.points_idx.size)
        X = np.concatenate([X, X[c.points_idx]])
        dy = np.concatenate([dy, -dy[c.points_idx]])
        h = np.concatenate([h, h[c.points_idx]])
        right.append(_low(c.distance, -HALF, 0.08, length=0.6, idx=idx))
    det = Detector(DetectorConfig())
    det._low_height = []
    kept = det._rail_reference(left + right, np.column_stack([X, dy, h]), dy, h)
    assert len(kept) == 12
    tracker = Tracker(det.cfg.tracking)
    for _ in range(12):
        tracker.update(kept, frame_dt=0.1)
    assert len(tracker.tracks) == 12
    assert all(t.reported and t.zone == "gauge" for t in tracker.tracks)


def test_weak_and_advisory_neighbours_cannot_supply_the_reference():
    (X, dy, h), pieces = _long_object_on_the_left_rail()
    det = Detector(DetectorConfig())
    # Include already-weak evidence, not only current confirmation candidates.
    det._low_height = pieces[1:3]
    for c in det._low_height:
        c.low_height_weak = True
    for c in pieces[3:]:
        c.zone, c.reason = "warning", "below_rail_ref"
    kept = det._rail_reference([pieces[0]] + pieces[3:], np.column_stack([X, dy, h]), dy, h)
    assert any(c is pieces[0] for c in kept)
    assert not pieces[0].low_height_weak


def test_independent_elevated_rails_still_reject_a_fragment():
    X, dy, h = _rails(30.0, 50.0, left=0.11, right=0.10)
    idx = np.arange(X.size, X.size + 6)
    X = np.concatenate([X, np.linspace(40.0, 40.3, 6)])
    dy = np.concatenate([dy, np.full(6, HALF)])
    h = np.concatenate([h, np.full(6, 0.108)])
    frag = _low(40.0, HALF, 0.108, idx=idx)
    det = Detector(DetectorConfig())
    det._low_height = []
    assert det._rail_reference([frag], np.column_stack([X, dy, h]), dy, h) == []
    assert frag.low_height_weak


def test_removing_low_bins_cannot_raise_the_rejection_threshold():
    # Original per-rail median = 0.075. Excluding the two low bins leaves
    # 0.15, above a genuine 0.10 m target: independent-only would hide it.
    xs = np.array([35.0, 36.0, 44.0, 45.0])
    X = np.tile(xs, 2)
    dy = np.repeat([-HALF, HALF], 4)
    h = np.tile([0.0, 0.0, 0.15, 0.15], 2)
    neighbours = [_low(35.0, -HALF, 0.0, idx=np.array([0, 1])),
                  _low(35.0, HALF, 0.0, idx=np.array([4, 5]))]
    target = _low(40.0, 0.0, 0.10, idx=np.array([8]))
    X, dy, h = (np.append(v, z) for v, z in ((X, 40.1), (dy, 0.0), (h, 0.10)))
    det = Detector(DetectorConfig())
    det._low_height = neighbours
    for c in neighbours:
        c.low_height_weak = True
    assert det._rail_reference([target], np.column_stack([X, dy, h]), dy, h) == [target]
    assert not target.low_height_weak


@pytest.mark.parametrize("upper", [0.24, 0.34])
def test_capped_low_top_does_not_hide_the_observed_upper_body(upper):
    X, dy, h = _rails(30.0, 50.0, left=0.18, right=0.18)
    i = X.size
    X = np.append(X, [40.05, 40.25, 40.15])
    dy = np.append(dy, [-0.1, 0.1, 0.0])
    h = np.append(h, [0.11, 0.11, upper])
    target = _low(40.0, 0.0, 0.11, idx=np.array([i, i + 1]))
    det = Detector(DetectorConfig())
    det._low_height = []
    assert det._rail_reference([target], np.column_stack([X, dy, h]), dy, h) == [target]
    assert not target.low_height_weak


@pytest.mark.parametrize("dx,lat,top", [(0.15, 0.0, 2.5), (1.0, 0.0, 0.24), (0.15, 0.4, 0.24)])
def test_ceiling_and_neighbouring_objects_do_not_exempt_a_rail_fragment(dx, lat, top):
    X, dy, h = _rails(30.0, 50.0, left=0.18, right=0.18)
    i = X.size
    X = np.append(X, [40.05, 40.25, 40.0 + dx])
    dy = np.append(dy, [-0.1, 0.1, lat])
    h = np.append(h, [0.11, 0.11, top])
    frag = _low(40.0, 0.0, 0.11, idx=np.array([i, i + 1]))
    det = Detector(DetectorConfig())
    det._low_height = []
    assert det._rail_reference([frag], np.column_stack([X, dy, h]), dy, h) == []
    assert frag.low_height_weak


def test_independent_reference_excludes_unselected_upper_points_of_all_pieces():
    (X, dy, h), pieces = _long_object_on_the_left_rail()
    upper_indices = []
    for c in pieces:
        upper_indices.append(X.size)
        X = np.append(X, c.distance + 0.25)
        dy = np.append(dy, HALF)
        h = np.append(h, 0.20)
    free = low_free_mask(X.size, pieces, X, dy)
    assert not free[upper_indices].any()
    assert all(not free[c.points_idx].any() for c in pieces)
