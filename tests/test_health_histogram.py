"""Exact sector counts and complete health outputs against the previous histogram oracle."""
from dataclasses import replace

import numpy as np
import pytest

import resense.health as health
from resense.config import GaugeConfig, HealthConfig, TrackConfig
from resense.track import default_track_model


def assert_counts(values, edges):
    expected = np.histogram(values, bins=edges)[0]
    actual = health._sector_counts(values, edges)
    np.testing.assert_array_equal(actual, expected)
    assert actual.dtype == expected.dtype
    return actual


@pytest.mark.parametrize("value_dtype", [np.float32, np.float64])
@pytest.mark.parametrize("edge_dtype", [np.float32, np.float64])
@pytest.mark.parametrize("width", [0.3, 7.0, 10.0, 60.0, 90.0])
def test_edges_and_adjacent_values_in_both_precisions(value_dtype, edge_dtype, width):
    edges = np.arange(-30.0, 30.0 + 1e-6, width, dtype=edge_dtype)
    centers = edges.astype(value_dtype)
    values = np.concatenate([centers, np.nextafter(centers, -np.inf),
                             np.nextafter(centers, np.inf),
                             np.asarray([-np.inf, np.inf, np.nan, -0.0, 0.0], dtype=value_dtype)])
    assert_counts(values, edges)
    assert_counts(np.empty(0, dtype=value_dtype), edges)


@pytest.mark.parametrize("value_dtype", [np.float32, np.float64])
def test_signed_zero_interior_boundary_and_subnormal_neighbors(value_dtype):
    values = np.asarray([-1, -0.0, 0.0, 1], dtype=value_dtype)
    values = np.concatenate([values, np.nextafter(values, -np.inf), np.nextafter(values, np.inf)])
    for edges in (np.asarray([-1, -0.0, 1], np.float32), np.asarray([-1, 0, 1], np.float64)):
        assert_counts(values, edges)


def test_previous_float32_endpoint_failure_is_rejected():
    edges = np.arange(-30.0, 30.0 + 1e-6, 0.3)
    assert edges[-1] > 30.0
    values = np.asarray([30.0], np.float32)
    expected = assert_counts(values, edges)
    assert expected[-1] == 1 and expected[-2] == 0
    # The rejected scalar comparison moves this point below the last bin on NumPy 1.x.
    if int(np.__version__.split(".")[0]) < 2:
        wrong = np.searchsorted(edges, values, side="right") - 1
        wrong[values == edges[-1]] -= 1
        assert wrong[0] == edges.size - 3


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_block_boundaries_strided_readonly_arrays_and_order(dtype):
    rng = np.random.default_rng(62928)
    values = rng.uniform(-180, 180, 2 * 65536 + 9).astype(dtype)
    edges = np.arange(-30.0, 30.0 + 1e-6, 7.0)
    for index, value in zip([65535, 65536, 65537, 131071, 131072],
                            [edges[0], edges[-1], np.nan, -np.inf, np.inf]):
        values[index] = value
    before = values.copy()
    values.setflags(write=False)
    edges.setflags(write=False)
    assert_counts(values, edges)
    assert_counts(values[::-1], edges)
    assert_counts(values[::2], edges)
    np.testing.assert_array_equal(values, before)


@pytest.mark.parametrize("values,edges", [
    (np.asarray([0, 1], np.float16), np.asarray([-1, 0, 1], np.float64)),
    (np.asarray([0, 1], np.int64), np.asarray([-1, 0, 1], np.float64)),
    (np.asarray([0, 1], dtype=">f4"), np.asarray([-1, 0, 1], np.float64)),
    (np.asarray([[0, 1], [-1, 0]], np.float32), np.asarray([-1, 0, 1], np.float64)),
    (np.asarray([0, 1], np.float32), np.arange(-30, 30.001, 0.1)),
    (np.asarray([0, 1], np.float32), np.asarray([-1, 0, 0, 1], np.float64)),
    (np.asarray([-np.inf, 0, np.inf, np.nan]), np.asarray([-np.inf, 0, np.inf])),
    (np.asarray([0, 1], np.float64), np.asarray([0, 1, np.nan])),
    (np.asarray([0, 1], np.float64), np.asarray([], np.float64)),
    ([0.0, 1.0], [-1.0, 0.0, 1.0]),
])
def test_unsupported_layouts_keep_histogram_behavior(values, edges):
    assert_counts(values, edges)


@pytest.mark.parametrize("edges", [np.asarray([1, 0], np.float64), np.asarray([[0, 1]], np.float64)])
def test_invalid_edges_keep_original_error(edges):
    values = np.asarray([0, 1], np.float32)
    with pytest.raises(ValueError) as previous:
        np.histogram(values, bins=edges)
    with pytest.raises(ValueError) as current:
        health._sector_counts(values, edges)
    assert str(current.value) == str(previous.value)


def test_ndarray_subclass_keeps_histogram_dispatch():
    class Override(np.ndarray):
        def __array_function__(self, function, types, args, kwargs):
            if function is np.histogram:
                return np.asarray([71], np.intp), np.asarray([0, 1])
            return super().__array_function__(function, types, args, kwargs)

    values = np.asarray([0, 1], np.float32).view(Override)
    assert_counts(values, np.asarray([0, 1], np.float64))


@pytest.mark.parametrize("latency_affects_decision", [False, True])
@pytest.mark.parametrize("sector_deg", [0.3, 7.0, 10.0, 90.0, -10.0])
def test_complete_health_state_sequence_matches_oracle(monkeypatch, latency_affects_decision, sector_deg):
    cfg = replace(HealthConfig(), min_points=24, sector_deg=sector_deg,
                  latency_affects_decision=latency_affects_decision)
    old, new = health.HealthMonitor(cfg), health.HealthMonitor(cfg)
    track = replace(default_track_model(TrackConfig()), rail_score=0.8)
    gauge = GaugeConfig()
    optimized = health._sector_counts
    for index in range(15):
        angles = np.repeat(np.asarray([-25, -15, -5, 5, 15, 25], np.float64), 8)
        if index % 5 == 1:
            angles = angles[angles < -10]  # four blocked sectors and low return count
        elif index % 5 == 2:
            angles = angles[:0]           # health bypasses histogram on empty clouds
        xy = 50.0 * np.column_stack((np.cos(np.radians(angles)), np.sin(np.radians(angles))))
        xyz = np.column_stack((xy, np.zeros(angles.size))).astype(np.float32)
        meta = {"n_raw": max(len(xyz), 1), "n_near": 20 if index % 3 == 0 else 0}
        arguments = (xyz, meta, track, gauge, 100.0, 0.1, 150.0 if index > 4 else 20.0)
        options = {"calibration": {"status": "fallback", "message": "fixture"} if index == 7 else {},
                   "obstacle_distance": 30.0 if index % 2 else None,
                   "candidate_distance": 20.0 if index % 3 else None}
        with monkeypatch.context() as context:
            context.setattr(health, "_sector_counts", lambda values, edges: np.histogram(values, bins=edges)[0])
            expected = old.update(*arguments, **options)
        monkeypatch.setattr(health, "_sector_counts", optimized)
        actual = new.update(*arguments, **options)
        assert actual == expected


@pytest.mark.parametrize("value_dtype", [np.float32, np.float64])
@pytest.mark.parametrize("edge_dtype", [np.float32, np.float64])
def test_randomised_clouds_with_edge_nan_and_infinite_values(value_dtype, edge_dtype):
    """29.09 (compare counts): random azimuths of any size, salted with every edge, the next float
    outside the range, NaN, +-inf and -0.0, against np.histogram."""
    rng = np.random.default_rng(29)
    for trial in range(300):
        sector = float(rng.choice([0.1, 0.7, 1.0, 2.5, 5.0, 7.3, 10.0]))
        edges = np.arange(-30.0, 30.0 + 1e-6, sector).astype(edge_dtype)
        n = int(rng.integers(0, 200_000 if trial % 50 == 0 else 3_000))
        values = rng.uniform(-40.0, 40.0, n).astype(value_dtype)
        if n > 12:
            k = rng.integers(0, n, 12)
            values[k[:6]] = edges[rng.integers(0, edges.size, 6)].astype(value_dtype)
            values[k[6:9]] = (np.nan, np.inf, -np.inf)
            values[k[9]] = np.nextafter(value_dtype(edges[-1]), value_dtype(np.inf))
            values[k[10]] = np.nextafter(value_dtype(edges[0]), value_dtype(-np.inf))
            values[k[11]] = -0.0
        assert_counts(values, edges)


@pytest.mark.parametrize("edges", [
    np.asarray([0.1, 0.2, 0.30000000000000004, 1 / 3]),            # not representable in float32
    np.asarray([-1e-40, 0.0, 1e-45, 1e-38]),                        # float32 subnormal / tiny range
    np.asarray([-3.0e38, -1.0, 0.0, 3.3e38]),                       # near float32 max, still float32 path
    np.asarray([-1.0, 0.0, float(np.finfo(np.float32).max)]),       # at float32 max: float64 path
    np.asarray([-3.5e38, -1.0, 0.0, 3.5e38]),                       # beyond float32 max: float64 path
    np.asarray([np.float32(0.1), np.nextafter(np.float32(0.1), np.float32(1))], dtype=np.float32),
])
def test_float32_thresholds_match_float64_comparison(edges):
    """29.09: float32 clouds are compared with float32 thresholds; every float32 next to an edge,
    on either side, must fall in the bin np.histogram's float64 comparison puts it in."""
    with np.errstate(over="ignore"):                                 # edges beyond float32 round to inf
        near = edges.astype(np.float32)
        values = np.concatenate([near, np.nextafter(near, np.float32(np.inf)), np.nextafter(near, np.float32(-np.inf)),
                                 np.asarray([np.nan, np.inf, -np.inf, -0.0, 0.0, np.finfo(np.float32).max,
                                             -np.finfo(np.float32).max], dtype=np.float32)])
        assert_counts(values, edges)
