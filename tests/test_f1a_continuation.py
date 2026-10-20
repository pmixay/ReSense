"""F1a: distinguish an uncapped object top from independently continued rail heads."""
import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.detector import Detector
from test_f1_false_alarms import HALF, _low, _rails


def _scene(side=1, top=0.20, slope=0.0):
    X, dy, h = _rails(30.0, 50.0, left=0.11, right=0.11)
    # Sparse rail-head returns at the outside of the narrow low footprint;
    # the model-centred reference band mostly sees the web at 0.11 m.
    xs = np.arange(31.0, 50.0, 2.0)
    X = np.r_[X, xs]
    dy = np.r_[dy, np.full(xs.size, side * (HALF + 0.11))]
    h = np.r_[h, 0.20 + slope * (xs - 40.0)]
    i = X.size
    X = np.r_[X, [40.05, 40.25, 40.15]]
    dy = np.r_[dy, side * np.array([HALF - 0.12, HALF + 0.12, HALF + 0.11])]
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
def test_independent_head_continuation_still_rejects_an_uncapped_rail(side, slope):
    assert _check(*_scene(side, slope=slope)) == (False, True)


@pytest.mark.parametrize('side', [-1, 1])
@pytest.mark.parametrize('top', [0.28, 0.30, 0.34])
def test_single_upper_return_of_a_real_object_still_exempts_it(side, top):
    assert _check(*_scene(side, top=top)) == (True, False)


@pytest.mark.parametrize('missing', ['before', 'after', 'both'])
def test_one_sided_or_absent_head_support_does_not_suppress(missing):
    X, dy, h, c = _scene()
    head = np.isclose(dy, HALF + 0.11) & ((X < 39.7) | (X > 40.6))
    remove = head & ((X < 40) if missing == 'before' else (X > 40) if missing == 'after' else True)
    h[remove] = -1.0
    assert _check(X, dy, h, c) == (True, False)


@pytest.mark.parametrize('advisory', [False, True])
def test_neighbouring_object_upper_returns_cannot_supply_continuation(advisory):
    X, dy, h, c = _scene()
    head = np.flatnonzero(np.isclose(dy, HALF + 0.11) & ((X < 39.7) | (X > 40.6)))
    neighbours = []
    for i in head:
        neighbour = _low(float(X[i]) - 0.05, HALF + 0.11, float(h[i]),
                         width=0.1, length=0.1, idx=np.array([i]))
        neighbour.low_height_weak = not advisory
        if advisory:
            neighbour.zone, neighbour.reason = 'warning', 'below_rail_ref'
        neighbours.append(neighbour)
    assert _check(X, dy, h, c, neighbours) == (True, False)


def test_wide_cross_track_surface_is_not_a_narrow_rail():
    X, dy, h, c = _scene()
    c.bbox_min[1], c.bbox_max[1] = HALF - 0.30, HALF + 0.30
    assert _check(X, dy, h, c) == (True, False)


def test_originally_accepted_low_top_is_never_newly_rejected():
    X, dy, h, c = _scene()
    c.height_max = 0.15
    assert _check(X, dy, h, c) == (True, False)


def test_switch_off_disables_surface_continuation_too():
    X, dy, h, c = _scene()
    det = Detector(DetectorConfig())
    det.cfg.lowobj.local_rail_margin = 0.0
    det._low_height = []
    assert det._rail_reference([c], np.column_stack([X, dy, h]), dy, h) == [c]
