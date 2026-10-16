"""Portable H4 failure witnesses, registered before the author fix.

Geometry derives from independent H4 safety case 45 and its absorbing-column
controls (838dd32). No recording, evidence-folder import, fitted-axis truth or
external cache is needed. Absorption removes the nearest opaque hit; it never
substitutes a background return. These are clustering/tracking boundary tests.
"""
from __future__ import annotations

import copy
import hashlib

import numpy as np
import pytest

from resense.clustering import FrameRays, find_clusters, top_is_free
from resense.config import DetectorConfig
from resense.gauge import gauge_core_mask, point_in_polygon, widened_profile
from resense.sensor import RING_ELEVATION_DEG
from resense.tracking import Tracker


def physical_column(distance=67.0, lateral=0.68, width=0.46, top=3.22,
                    absorbing=None, beam=False):
    """Independent rectangular-tunnel slab intersections on the physical scan grid."""
    az = np.radians(np.arange(-50.0, 50.00001, 0.1) + 0.037)
    aa, ee = np.meshgrid(az, np.radians(RING_ELEVATION_DEG))
    rays = np.stack([np.cos(ee) * np.cos(aa), np.cos(ee) * np.sin(aa), np.sin(ee)], -1).reshape(-1, 3)
    ring = np.repeat(np.arange(len(RING_ELEVATION_DEG)), len(az))
    limits = []
    with np.errstate(divide="ignore", invalid="ignore"):
        for axis, bound in [(0, 247.0), (1, 2.43), (1, -2.43), (2, 4.12 - 1.83), (2, -1.83)]:
            t = bound / rays[:, axis]
            limits.append(np.where(t > 0, t, np.inf))
    dist = np.min(limits, axis=0)
    labels = np.zeros(len(dist), dtype=int)
    boxes = [([distance - width / 2, lateral - width / 2, -1.83],
              [distance + width / 2, lateral + width / 2, top - 1.83])]
    if beam:
        boxes.append(([distance - width / 2 - 4, -1.2, 3.05 - 1.83],
                      [distance - width / 2 - 3.7, 1.2, 3.25 - 1.83]))
    for label, (lo, hi) in enumerate(boxes, 1):
        with np.errstate(divide="ignore", invalid="ignore"):
            t0, t1 = np.asarray(lo) / rays, np.asarray(hi) / rays
        near, far = np.minimum(t0, t1).max(1), np.maximum(t0, t1).min(1)
        hit = (far >= np.maximum(near, 0)) & (near > 0) & (near < dist)
        dist[hit], labels[hit] = near[hit], label
    xyz = rays * dist[:, None]
    keep = (dist >= 2.5) & (dist <= 225)
    if absorbing is not None:
        keep &= ~((labels == 1) & (xyz[:, 2] + 1.83 >= absorbing[0])
                  & (xyz[:, 2] + 1.83 <= absorbing[1]))
    return xyz[keep].astype(np.float32), ring[keep], labels[keep]


def column_clusters(xyz, ring, cfg=None):
    cfg = cfg or DetectorConfig()
    dy, h = xyz[:, 1], xyz[:, 2] + 1.83
    warning = point_in_polygon(dy, h, widened_profile(cfg.gauge, cfg.gauge.warning_margin))
    warning &= (xyz[:, 0] >= cfg.gauge.range_min) & (xyz[:, 0] <= cfg.gauge.range_max)
    idx = np.flatnonzero(warning)
    core = gauge_core_mask(dy[idx], h[idx], xyz[idx, 0], cfg.gauge)
    return find_clusters(xyz[idx], np.full(len(idx), 35, np.float32), dy[idx], h[idx], core, cfg.cluster,
                         frame_idx=idx, gauge=cfg.gauge, axis_valid=225, height_valid=225,
                         ring=None if ring is None else ring[idx], frame_xyz=xyz, frame_ring=ring,
                         frame_h=h, frame_dy=dy)


def object_cluster(xyz, ring, labels):
    matches = [c for c in column_clusters(xyz, ring) if np.mean(labels[c.points_idx] == 1) > 0.5]
    assert len(matches) == 1
    return matches[0]


def test_h4_case45_follows_actual_returns_above_the_candidate_cut():
    xyz, ring, labels = physical_column()
    assert hashlib.sha256(xyz.tobytes()).hexdigest() == "680878ed4f0b233cec517f999ca8648b1193522c929b7ce0f9df9fad7d545a20"
    c = object_cluster(xyz, ring, labels)
    assert (int((labels == 1).sum()), c.n_gauge, c.ring_count) == (84, 80, 20)
    assert 2.93 < c.height_max < 2.95  # observed cut is NOT the physical top (3.22 m)
    assert (c.zone, c.reason, c.spared) == ("gauge", "", True)
    tracker = Tracker(DetectorConfig().tracking)
    stops = []
    for f in range(20):
        tracker.update([] if f in (9, 10) else [copy.deepcopy(c)], frame_dt=0.1)
        stops.append(any(t.zone == "gauge" for t in tracker.confirmed()))
    assert any(stops[:9]) and any(stops[11:])


@pytest.mark.parametrize("distance", [67.0, 109.0, 137.0])
@pytest.mark.parametrize("ring_mode", ["highest", "reverse", "absent"])
def test_h4_absent_face_is_not_free_sight(distance, ring_mode):
    xyz, ring, labels = physical_column(distance=distance, top=4.12, absorbing=(2.54, 4.12))
    ring = None if ring_mode == "absent" else 127 - ring if ring_mode == "reverse" else ring
    c = object_cluster(xyz, ring, labels)
    # At long range the absorbing visible stump can be shorter than the column
    # signature. This test targets evidence, not a new global shape demotion.
    rays = FrameRays(xyz, ring, xyz[:, 2] + 1.83, xyz[:, 1])
    assert not top_is_free(rays, c.points_idx, window=1.2)
    assert not c.spared
    if c.size[2] > DetectorConfig().cluster.column_min_height:
        assert (c.zone, c.reason) == ("warning", "column")


@pytest.mark.parametrize("top,absorbing,beam", [(4.12, None, False), (4.12, (2.54, 3.18), False),
                                                (2.72, None, True)])
def test_h4_opaque_resumed_face_and_occluding_beam_are_not_free(top, absorbing, beam):
    xyz, ring, labels = physical_column(top=top, absorbing=absorbing, beam=beam)
    c = object_cluster(xyz, ring, labels)
    assert (c.zone, c.reason, c.spared) == ("warning", "column", False)


@pytest.mark.parametrize("distance", [37.0, 67.0, 109.0, 137.0])
def test_h4_short_physical_pole_retains_positive_evidence(distance):
    xyz, ring, labels = physical_column(distance=distance, top=2.72)
    c = object_cluster(xyz, ring, labels)
    assert (c.zone, c.reason, c.spared) == ("gauge", "", True)
