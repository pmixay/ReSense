"""Local surface continuation: reject proven geometry, preserve ambiguous evidence."""
from pathlib import Path

import numpy as np
import pytest

from resense.config import DetectorConfig, LowObjectConfig
from resense.lowobj import BedTemplate, local_surface_mask, low_candidates


def _surface(*, raised=0.08, slope=0.002, cross_slope=0.05):
    x, d = np.meshgrid(np.arange(15.75, 24.5, 0.5), [-0.125, -0.075, 0.075, 0.125])
    h = raised + slope * (x - 20) + cross_slope * d
    return np.column_stack((x.ravel(), d.ravel(), h.ravel()))


def _mask(background, *, top=0.08, reference=0.0, cfg=None):
    points = np.vstack((background, [20, 0, top]))
    return local_surface_mask(*points.T, np.array([len(background)]), np.array([reference]),
                              cfg or LowObjectConfig(local_support_enabled=True))[0]


def test_default_off_and_yaml_round_trip():
    cfg = DetectorConfig()
    assert not cfg.lowobj.local_support_enabled
    root = Path(__file__).resolve().parents[1]
    assert DetectorConfig.from_yaml(str(root / 'configs/default.yaml')).to_dict() == cfg.to_dict()
    experiment = DetectorConfig.from_yaml(str(root / 'configs/experimental_low_local_support.yaml'))
    assert experiment.lowobj.local_support_enabled
    assert DetectorConfig.from_dict(experiment.to_dict()).to_dict() == experiment.to_dict()
    assert not _mask(_surface(), cfg=cfg.lowobj)


def test_continuous_sloping_surface_is_not_a_local_bump():
    assert _mask(_surface())


@pytest.mark.parametrize('height', [0.05, 0.1, 0.3])
def test_real_bump_above_local_surface_is_kept(height):
    assert not _mask(_surface(), top=0.08 + height)


@pytest.mark.parametrize('case', ['ahead_only', 'left_only', 'single_scan_line', 'step', 'rough', 'no_bed'])
def test_ambiguous_geometry_keeps_baseline(case):
    points = _surface()
    if case == 'ahead_only':
        points = points[points[:, 0] > 20]
    elif case == 'left_only':
        points = points[points[:, 1] < 0]
    elif case == 'single_scan_line':
        points[:, 0] = 22
    elif case == 'step':
        points[points[:, 0] > 20, 2] += 0.2
    elif case == 'rough':
        points[::2, 2] += 0.15
    else:
        points = points[:0]
    assert not _mask(points)


def test_duplicate_returns_cannot_make_support():
    points = _surface()[[0, 1, 18, 19]]
    assert not _mask(np.repeat(points, 50, axis=0))


def test_object_footprint_is_excluded_even_with_dense_returns():
    x, y = np.meshgrid(np.linspace(19.85, 20.15, 20), np.linspace(-0.15, 0.15, 20))
    box = np.column_stack((x.ravel(), y.ravel(), np.full(x.size, 0.1)))
    assert not _mask(box, top=0.1)


def test_local_reference_correction_is_bounded():
    assert not _mask(_surface(raised=0.3), top=0.3)
    assert not _mask(_surface(), reference=0.1)


def test_nonfinite_support_is_ignored_and_work_cap_keeps_baseline():
    assert _mask(np.vstack((_surface(), [np.nan, 0, 0], [20, np.inf, 0])))
    p = _surface()
    cfg = LowObjectConfig(local_support_enabled=True)
    assert not local_surface_mask(*p.T, np.zeros(513, dtype=int), np.zeros(513), cfg).any()


def _candidate_scene():
    # Baseline cross-section underestimated this narrow continuous raised strip. A
    # broad lower bed supplies the existing along-bin median without absorbing it.
    x, d = np.meshgrid(np.arange(14, 26, 0.2), [-0.45, -0.3, 0.3, 0.45])
    bed = np.column_stack((x.ravel(), d.ravel(), np.full(x.size, 0.05)))
    strip = _surface(raised=0.09, slope=0, cross_slope=0)
    return np.vstack((bed, strip, [20, 0, 0.114]))


def test_candidate_gate_covers_low_straddle_and_near_without_changing_seen_range():
    p = _candidate_scene()
    cfg = LowObjectConfig(near_enabled=True, near_min_bed_lateral_bins=4)
    template = BedTemplate(cfg)
    template.prof = np.full_like(template.centres, 0.05)
    before = low_candidates(*p.T, template, cfg, 3, 30, 0.12, with_near=True)
    cfg.local_support_enabled = True
    after = low_candidates(*p.T, template, cfg, 3, 30, 0.12, with_near=True)
    target = len(p) - 1
    assert before[1] == after[1]
    for i in (0, 2, 3):
        assert target in before[i]
        assert target not in after[i]


@pytest.mark.parametrize('distance,lateral', [(12, 0), (20, 0), (28, 0), (18, 0.8), (20, -0.8)])
def test_small_bed_and_rail_objects_still_confirm(distance, lateral):
    # Existing deterministic detector fixture exercises clustering and persistence,
    # including the optional 30x30x10 cm below-rail box policy.
    from test_lowobj_near import _approach, _patch

    cfg = DetectorConfig()
    cfg.lowobj.near_enabled = True
    obj = _patch(distance, lateral, base=-0.32 if lateral == 0 else 0.0)
    baseline = _approach(obj, cfg=cfg)[0]
    cfg.lowobj.local_support_enabled = True
    filtered = _approach(obj, cfg=cfg)[0]
    assert baseline and filtered
    assert [(d.distance, d.zone, d.kind) for d in baseline] == [(d.distance, d.zone, d.kind) for d in filtered]
