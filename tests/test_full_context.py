"""Safety boundaries of the one preregistered D1 full-context candidate."""
from dataclasses import replace

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import ClusterConfig
from resense.context import compact_context, restore_context


def cloud(x=20.0, width=1.2, height=0.6, bottom=1.4):
    points = np.asarray([[x + a, y, bottom + z] for z in np.arange(0, height + 0.001, 0.1)
                         for y in np.arange(-width / 2, width / 2 + 0.001, 0.1)
                         for a in (0.0, 0.1)], np.float32)
    ids = np.flatnonzero(points[:, 2] == np.float32(bottom))
    seed = points[ids]
    cluster = Cluster(points_idx=ids, n=10, n_raw=len(ids), centroid=seed.mean(axis=0),
                      bbox_min=seed.min(axis=0), bbox_max=seed.max(axis=0), distance=x,
                      lateral=0.0, height_min=bottom + 1.5, height_max=bottom + 1.5,
                      intensity=1.0, n_expected=10, score=1.0, zone="gauge", n_gauge=5, thin=True)
    return points, cluster


def check(points, cluster, cfg=None, intensity=None, axis=200.0, height=200.0):
    return compact_context(cluster, points, np.ones(len(points)) if intensity is None else intensity,
                           points[:, 1], points[:, 2] + 1.5, cfg or ClusterConfig(), axis, height)


def test_top_crop_recovers_measured_full_height_without_changing_candidate_geometry():
    points, cluster = cloud()
    assert check(points, cluster) == (True, "compact_full_context")
    ordinary = replace(cluster, thin=False, reason="", zone="gauge")
    output, thin, stats = restore_context([ordinary], [cluster], points, np.ones(len(points)),
                                          points[:, 1], points[:, 2] + 1.5, ClusterConfig(), 200, 200)
    assert output[0] is ordinary
    assert len(output) == 2 and not thin and stats["compact_full_context"] == 1
    restored = output[1]
    assert not restored.thin and restored.zone == "gauge"
    assert restored.points_idx is cluster.points_idx
    assert restored.centroid is cluster.centroid and restored.bbox_min is cluster.bbox_min
    assert restored.distance == cluster.distance and restored.n_gauge == cluster.n_gauge
    assert cluster.thin                                  # no input mutation


def test_compact_floating_candidate_requires_full_context():
    points, cluster = cloud(width=0.3, height=0.3, bottom=-0.2)
    cluster = replace(cluster, thin=False, zone="warning", reason="floating", demoted=True)
    assert check(points, cluster)[0]
    chain = np.asarray([[x, 0, -0.2] for x in np.arange(20.2, 35, 0.2)], np.float32)
    assert check(np.concatenate([points, chain]), cluster)[0] is False


@pytest.mark.parametrize("x", [20.0, 130.0])
def test_compact_object_touching_long_structure_is_not_promoted_even_beyond_crop(x):
    points, cluster = cloud(x=x)
    # At range, sparse connectivity can jump several metres in X under the production
    # normalized metric. The chain continues far beyond the query's finite bounds.
    step = 0.2 if x == 20 else 1.0
    chain = np.asarray([[d, 0, 1.4] for d in np.arange(x + 0.2, x + 80, step)], np.float32)
    connected = np.concatenate([points, chain])
    accepted, reason = check(connected, cluster)
    assert not accepted and reason in ("extended_component", "query_boundary")
    outputs, remaining, _ = restore_context([], [cluster], connected, np.ones(len(connected)),
                                            connected[:, 1], connected[:, 2] + 1.5,
                                            ClusterConfig(), 200, 200)
    assert not outputs and remaining[0] is cluster


def test_full_column_cannot_become_a_new_obstacle_from_its_clipped_fragment():
    points, cluster = cloud(width=0.4, height=2.4, bottom=-1.0)
    assert check(points, cluster) == (False, "full_context_column")


def test_full_retro_context_keeps_exclusion():
    points, cluster = cloud(width=0.4, height=0.3, bottom=-0.2)
    cfg = ClusterConfig(retro_intensity=100)
    assert check(points, cluster, cfg, np.full(len(points), 150)) == (False, "full_context_retro")


@pytest.mark.parametrize("reason", ["column", "beyond_axis", "beyond_height_ref", "overhead", "edge", "wall_face"])
def test_existing_exclusion_never_overridden(reason):
    points, cluster = cloud()
    assert not check(points, replace(cluster, reason=reason))[0]


def test_strict_support_and_both_geometry_ranges_are_required():
    points, cluster = cloud()
    assert check(points, replace(cluster, n_gauge=2))[1] == "insufficient_original_strict_support"
    assert check(points, cluster, axis=19)[1] == "unsupported_geometry"
    assert check(points, cluster, height=19)[1] == "unsupported_geometry"


def test_empty_noise_and_still_thin_context_fail_closed():
    points, cluster = cloud()
    assert check(points, replace(cluster, points_idx=np.empty(0, np.int64)))[1] == "no_current_seed"
    line = points[cluster.points_idx]
    line_cluster = replace(cluster, points_idx=np.arange(len(line)))
    assert check(line, line_cluster)[1] == "context_still_thin"
    isolated = np.asarray([[20, 0, 1.4]], np.float32)
    assert check(isolated, replace(cluster, points_idx=np.array([0])))[1] == "fragmented_or_noise_seed"


def test_accumulated_input_is_unchanged():
    points, cluster = cloud()
    ordinary, thin = [], [cluster]
    out, remaining, stats = restore_context(ordinary, thin, points, np.ones(len(points)),
                                            points[:, 1], points[:, 2] + 1.5, ClusterConfig(), 200, 200, 2)
    assert out is ordinary and remaining is thin
    assert stats == {"accumulated_frame_unchanged": 1}
