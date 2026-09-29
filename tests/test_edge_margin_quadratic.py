"""The quadratic term of the strict-gauge edge margin (``gauge.edge_margin_per_100m2``, 29.09, off by default)."""
from dataclasses import replace

import numpy as np

from resense.config import GaugeConfig
from resense.gauge import edge_margin_at, gauge_core_mask, gauge_reach_mask, has_edge_margin


def test_default_is_the_linear_margin():
    g = GaugeConfig()
    assert g.edge_margin_per_100m2 == 0.0
    x = np.array([0.0, 50.0, 100.0, 200.0])
    assert np.allclose(edge_margin_at(x, g), g.edge_margin + g.edge_margin_per_100m * x / 100.0)


def test_quadratic_term_grows_with_the_square_of_range():
    g = replace(GaugeConfig(), edge_margin=0.0, edge_margin_per_100m=0.15, edge_margin_per_100m2=0.3)
    assert np.allclose(edge_margin_at(np.array([100.0, 150.0]), g), [0.45, 0.225 + 0.675])
    assert has_edge_margin(replace(g, edge_margin_per_100m=0.0))


def test_core_mask_rejects_an_edge_point_far_away_but_keeps_it_near():
    g = replace(GaugeConfig(), edge_margin=0.0, edge_margin_per_100m=0.15, edge_margin_per_100m2=0.3)
    dy, h = np.array([0.8, 0.8]), np.array([1.0, 1.0])
    x = np.array([30.0, 100.0])            # margins 0.07 m and 0.45 m inside the 1.05 m edge
    assert gauge_core_mask(dy, h, x, g).tolist() == [True, False]
    assert gauge_core_mask(dy, h, x, replace(g, edge_margin_per_100m2=0.0)).tolist() == [True, True]
    # the reach mask (the distance of a gauge cluster) only ever grows with the margin
    assert gauge_reach_mask(dy, h, x, g).all()
