"""F1a: an uncapped top that does not rise above the rail head's own top surface is rail geometry."""
import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.detector import Detector
from test_f1_false_alarms import HALF, _low, _rails


def _scene(side=1, top=0.20, head=0.20, slope=0.0, stray=False):
    """Rail returns on both rails (web at 0.11) and the head's top surface at ``head``.

    The head's top is seen on the outside of the narrow low footprint, so the model's
    median line reads the web while the fragment's uncapped top reads the head.
    """
    X, dy, h = _rails(30.0, 50.0, left=0.11, right=0.11)
    xs = np.arange(31.0, 50.0, 2.0)
    X = np.r_[X, xs]
    dy = np.r_[dy, np.full(xs.size, side * (HALF + 0.11))]
    h = np.r_[h, head + slope * (xs - 40.0)]
    if stray:
        X = np.r_[X, [41.0]]
        dy = np.r_[dy, [side * (HALF + 0.11)]]
        h = np.r_[h, [head + 0.30]]
    i = X.size
    X = np.r_[X, [40.05, 40.25, 40.15]]
    dy = np.r_[dy, side * np.array([HALF - 0.12, HALF + 0.12, HALF + 0.02])]
    h = np.r_[h, [0.10, 0.10, top]]
    c = _low(40.0, side * HALF, 0.10, width=0.30, idx=np.array([i, i + 1]))
    return X, dy, h, c


def _check(X, dy, h, c, neighbours=()):
    det = Detector(DetectorConfig())
    det._low_height = list(neighbours)
    kept = det._rail_reference([c], np.column_stack([X, dy, h]), dy, h)
    return bool(kept), c.low_height_weak


@pytest.mark.parametrize('side', [-1, 1])
@pytest.mark.parametrize('slope', [-0.006, 0.0, 0.006])
def test_the_head_top_surface_explains_an_uncapped_rail_fragment(side, slope):
    assert _check(*_scene(side, top=0.20, slope=slope)) == (False, True)


@pytest.mark.parametrize('side', [-1, 1])
@pytest.mark.parametrize('top', [0.28, 0.30, 0.34])
def test_a_body_above_the_head_top_surface_still_exempts_the_cluster(side, top):
    assert _check(*_scene(side, top=top)) == (True, False)


def test_without_a_head_surface_the_fragment_is_not_rejected():
    X, dy, h, c = _scene()
    head = np.isclose(dy, HALF + 0.11)
    h[head] = 0.11
    assert _check(X, dy, h, c) == (True, False)


def test_one_stray_return_cannot_define_the_surface():
    X, dy, h, c = _scene(top=0.20, head=0.11, stray=True)
    assert _check(X, dy, h, c) == (True, False)


def test_a_neighbouring_object_upper_return_cannot_supply_the_surface():
    X, dy, h, c = _scene(top=0.20, head=0.11)
    head = np.flatnonzero(np.isclose(dy, HALF + 0.11))
    neighbours = []
    for i in head:
        neighbour = _low(float(X[i]) - 0.05, HALF + 0.11, 0.20, width=0.1, length=0.1, idx=np.array([i]))
        neighbours.append(neighbour)
    assert _check(X, dy, h, c, neighbours) == (True, False)


def test_wide_cross_track_surface_is_not_a_narrow_rail():
    X, dy, h, c = _scene()
    c.bbox_min[1], c.bbox_max[1] = HALF - 0.30, HALF + 0.30
    assert _check(X, dy, h, c) == (True, False)


def test_an_originally_accepted_low_top_is_never_newly_rejected():
    X, dy, h, c = _scene()
    c.height_max = 0.15
    assert _check(X, dy, h, c) == (True, False)


def test_switch_off_disables_the_surface_rule_too():
    X, dy, h, c = _scene()
    det = Detector(DetectorConfig())
    det.cfg.lowobj.local_rail_margin = 0.0
    det._low_height = []
    assert det._rail_reference([c], np.column_stack([X, dy, h]), dy, h) == [c]
