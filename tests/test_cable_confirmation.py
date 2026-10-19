"""R3 acceptance: short bursts of positive vertical evidence, never generic clutter."""
from dataclasses import replace

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import DetectorConfig
from resense.tracking import Tracker


def cable(kind='', distance=85., width=.05, height=2.6, n=13):
    bottom = 2.7 if kind == 'hanging' else .2
    lo = np.array([distance, -.5 * width, bottom - 1.83])
    hi = lo + [width, width, height]
    return Cluster(points_idx=np.arange(n), n=n, n_raw=n, centroid=(lo+hi)/2,
                   bbox_min=lo, bbox_max=hi, distance=distance, lateral=0., height_min=bottom,
                   height_max=bottom+height, intensity=30., n_expected=float(n), score=1.,
                   zone='gauge', n_gauge=1 if kind == 'hanging' else n, kind=kind)


def stops(tr):
    return any(t.zone == 'gauge' for t in tr.confirmed())


def test_three_frame_tall_cable_burst_confirms_before_visibility_gap():
    tr = Tracker(DetectorConfig().tracking)
    for k in range(3):
        tr.update([cable(distance=89.1-1.44*k)], frame_dt=.1)
        assert stops(tr) == (k == 2)


def test_two_frame_hanging_burst_confirms_at_48m():
    tr = Tracker(DetectorConfig().tracking)
    for k in range(2):
        tr.update([cable(kind='hanging', distance=49.83-1.64*k, height=.44, n=3)], frame_dt=.1)
        assert stops(tr) == (k == 1)


@pytest.mark.parametrize('change', [dict(width=.151), dict(height=1.49), dict(n=7),
                                   dict(zone='warning'), dict(reason='column'), dict(weak=True),
                                   dict(thin=True), dict(kind='low')])
def test_weak_wide_demoted_low_or_flat_evidence_keeps_ordinary_confirmation(change):
    tr = Tracker(DetectorConfig().tracking)
    c = cable(width=change.get('width', .05), height=change.get('height', 2.6), n=change.get('n',13))
    c = replace(c, **{k:v for k,v in change.items() if k not in ('width','height')})
    for _ in range(3):
        tr.update([c], frame_dt=.1)
        assert not stops(tr)


def test_sparse_fast_input_still_needs_sensor_time():
    tr = Tracker(DetectorConfig().tracking)
    for _ in range(3):
        tr.update([cable()], frame_dt=.05)
        assert not stops(tr)
    for _ in range(3):
        tr.update([cable()], frame_dt=.05)
    assert stops(tr)


def test_missed_and_ineligible_hits_do_not_supply_fast_confirmation():
    tr = Tracker(DetectorConfig().tracking)
    tr.update([cable()], frame_dt=.1)
    tr.update([], frame_dt=.1)
    tr.update([cable()], frame_dt=.1)
    assert not stops(tr)
    tr.update([cable(width=.25)], frame_dt=.1)
    tr.update([cable()], frame_dt=.1)
    # Generic confirmation can now qualify independently after .5s; inspect the
    # special run itself to exclude stale or ineligible hit borrowing.
    t = tr.tracks[0]
    assert t.cable_hits == 1 and t.cable_span_s == pytest.approx(.1)


def test_hanging_one_scanline_never_uses_short_confirmation():
    tr = Tracker(DetectorConfig().tracking)
    for _ in range(2):
        tr.update([cable(kind='hanging',height=.01,n=3)], frame_dt=.1)
        assert not stops(tr)


@pytest.mark.parametrize('dt,expected', [(.099995, True), (.09, False), (.05, False)])
def test_hanging_timestamp_jitter_is_bounded_not_an_extra_hit(dt, expected):
    tr = Tracker(DetectorConfig().tracking)
    for _ in range(2):
        tr.update([cable(kind='hanging', distance=48.2, height=.44, n=3)], frame_dt=dt)
    assert stops(tr) == expected
