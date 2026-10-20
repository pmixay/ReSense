"""Reviewer regression tests (NOT part of the repository's test suite; kept here as evidence).

Each test states a behaviour the F1a completion's own documentation promises (or that the previous variant 450a99f
guaranteed) and that must hold for a real object.  They PASS on the reference f56ad5e and on the parent 450a99f and
FAIL on the candidate a77d884 -- a mutation-style demonstration of findings F1-F4 of the review.

Run (the checkout's tests directory must be importable for the repo's fixtures):
    cd <checkout> && PYTHONPATH=<checkout>:<checkout>/tests python -m pytest -q <this file>
"""
import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.detector import Detector
from test_f1_false_alarms import HALF, _low, _rails


def scene(top=0.30, head=0.20, head_xs=None, extra=(), slope=0.0):
    """Both rails (web 0.11), head surface ``head`` + slope*(x-40) at ``head_xs`` on the + rail's outside edge, a narrow
    fragment on the + rail (two low returns at 0.10, one upper return at ``top``), ``extra`` = (x, dy_off, h) returns."""
    X, dy, h = _rails(30.0, 50.0, left=0.11, right=0.11)
    xs = np.arange(31.0, 50.0, 2.0) if head_xs is None else np.asarray(head_xs, float)
    X = np.r_[X, xs]
    dy = np.r_[dy, np.full(xs.size, HALF + 0.11)]
    h = np.r_[h, head + slope * (xs - 40.0)]
    for x, d, v in extra:
        X, dy, h = np.r_[X, x], np.r_[dy, HALF + d], np.r_[h, v]
    i = X.size
    X = np.r_[X, [40.05, 40.25, 40.15]]
    dy = np.r_[dy, [HALF - 0.12, HALF + 0.12, HALF + 0.02]]
    h = np.r_[h, [0.10, 0.10, top]]
    return X, dy, h, _low(40.0, HALF, 0.10, width=0.30, idx=np.array([i, i + 1]))


def rejected(X, dy, h, c):
    det = Detector(DetectorConfig())
    det._low_height = []
    return not det._rail_reference([c], np.column_stack([X, dy, h]), dy, h)


@pytest.mark.parametrize("x", [40.5, 41.5, 43.0, 44.5])
def test_F1_an_objects_own_unclustered_returns_cannot_define_the_rail_surface(x):
    """An object 10 cm above the 0.11 rail whose own two top returns lie outside every low footprint (not part of any
    low cluster) must not be explained away by them."""
    X, dy, h, c = scene(top=0.21, head=0.11, head_xs=[], extra=[(x, 0.11, 0.21), (x + 0.07, 0.11, 0.21)])
    assert not rejected(X, dy, h, c)


@pytest.mark.parametrize("head_range", [(31.0, 39.5), (40.6, 50.0)], ids=["head_before_only", "head_after_only"])
def test_F2_one_sided_head_support_does_not_reject(head_range):
    """The F1a completion README/PROTOCOL promise 'two-sided support'; the parent 450a99f's tests required that a head
    seen on one side only does not suppress (these tests were deleted in a77d884)."""
    xs = np.arange(head_range[0], head_range[1], 2.0)
    X, dy, h, c = scene(top=0.20, head=0.20, head_xs=xs)
    assert not rejected(X, dy, h, c)


@pytest.mark.parametrize("x,rise", [(36.0, 0.30), (36.0, 0.25), (44.0, 0.30)])
def test_F3_a_local_rise_on_the_rail_line_cannot_hide_a_10cm_object(x, rise):
    """Object top 0.30 = 10 cm above the local head (0.20); two returns of a local rise 5-10 cm above the head, within
    the +-5 m window, raise the window maximum 'S' and hide it."""
    X, dy, h, c = scene(top=0.30, head=0.20, extra=[(x, 0.11, rise), (x + 0.07, 0.11, rise)])
    assert not rejected(X, dy, h, c)


@pytest.mark.parametrize("slope", [0.01, 0.012, 0.02, -0.02])
def test_F4_head_height_slope_of_1cm_per_m_does_not_hide_a_10cm_object(slope):
    """Head returns rise/fall by 1-2 cm per metre along the track (data: |slope| p90 = 1.8 cm/m in the 98 ride
    snapshots); the object is 10 cm above the head at its own position."""
    X, dy, h, c = scene(top=0.30, head=0.20, slope=slope)
    assert not rejected(X, dy, h, c)
