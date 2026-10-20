"""A1: ground below a scanner is not evidence that forward points down."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from resense import Detector, DetectorConfig
from resense.calibration import directional_axes, orientation_candidates
from resense.frame import Frame


@pytest.fixture(scope='module')
def scenes():
    path = (Path(__file__).resolve().parents[1] / 'docs/evidence/'
            'p4_review_shipping_2026-10-20/scripts/scene.py')
    spec = importlib.util.spec_from_file_location('a1_review_scene', path)
    scene = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scene)
    rays, ring = scene.rays(-104, 106)
    return {name: scene.frame(rays, ring, *scene.cast(
        rays, tunnel=name == 'tunnel', open_air=name == 'open'))[0]
        for name in ('open', 'tunnel')}


@pytest.mark.parametrize('rotation', orientation_candidates())
@pytest.mark.parametrize('above_fraction', [0., .01])
def test_ground_half_space_cannot_become_signed_forward(rotation, above_fraction):
    rng = np.random.default_rng(9)
    az = rng.uniform(np.radians(-104), np.radians(106), 6000)
    radius = rng.uniform(5., 100., len(az))
    xyz = np.column_stack([radius * np.cos(az), radius * np.sin(az),
                           np.full(len(az), -1.9)])
    xyz[:int(len(xyz) * above_fraction), 2] = 4.5
    forward, up = directional_axes((xyz @ rotation.T).astype(np.float32))
    assert forward is None
    assert up is None


@pytest.mark.parametrize('keep_ring', [True, False])
@pytest.mark.parametrize('enter_tunnel', [False, True])
def test_correct_open_air_start_survives_the_fallback_boundary(scenes, keep_ring, enter_tunnel):
    detector = Detector(DetectorConfig())
    for i in range(450):
        source = scenes['tunnel' if enter_tunnel and i >= 10 else 'open']
        result = detector.process(Frame(
            xyz=source.xyz, intensity=source.intensity,
            ring=source.ring if keep_ring else None, stamp=.1 * i,
            frame_id='a1_open_start'))
        assert not result.obstacle
        assert result.mount['orientation_confirmed']
        assert not result.mount['orientation_conflict']
        assert result.health['level'] != 'error'
        assert detector.calib._forward_axis is None
    assert detector.calib.frozen
    assert result.mount['status'] in ('ok', 'identity')
    assert result.mount['frames_used'] > 0
