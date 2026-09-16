"""Sensor model of the hackathon LiDAR (Hesai Pandar128 E3X, see docs/SENSOR.md).

Measured from the provided bags (see docs/DATASET.md):
    * 1200 azimuth columns per frame, 0.1 deg step, returns only within +-50 deg
    * 128 rings, elevation +14.4 .. -25.1 deg; 0.125 deg step in the ROI (+2 .. -6.2 deg)
    * dual return (2 x 153 600 slots per frame), 10 Hz, 33 ms sweep
    * useful range ~200 m (last returns at ~206 m); the manual instruments 200 m only on
      channels 26-89 (elevation +2 .. -6 deg), 100 m elsewhere
The tables below drive the synthetic obstacle injector and the "expected number of
points" model used to score clusters.
"""
from __future__ import annotations

import numpy as np

AZIMUTH_STEP_DEG = 0.1
AZIMUTH_FOV_DEG = (-50.0, 50.0)
FRAME_RATE_HZ = 10.0
MAX_RANGE_M = 210.0

# median elevation of each ring (deg), measured on roundT_doubleT frame 0
RING_ELEVATION_DEG = np.array([
    14.402, 13.509, 13.025, 12.588, 12.120, 11.670, 11.188, 10.749, 10.259, 9.808,
    9.318, 8.846, 8.339, 7.892, 7.376, 6.904, 6.415, 5.928, 5.441, 4.948,
    4.460, 3.964, 3.466, 2.972, 2.450, 1.969, 1.841, 1.715, 1.595, 1.456,
    1.325, 1.211, 1.057, 0.952, 0.821, 0.702, 0.591, 0.437, 0.323, 0.203,
    0.040, -0.046, -0.191, -0.303, -0.425, -0.570, -0.690, -0.805, -0.971, -1.062,
    -1.207, -1.322, -1.431, -1.583, -1.710, -1.822, -1.982, -2.079, -2.225, -2.337,
    -2.450, -2.596, -2.739, -2.848, -3.016, -3.106, -3.252, -3.374, -3.479, -3.633,
    -3.758, -3.868, -4.019, -4.117, -4.274, -4.391, -4.501, -4.652, -4.769, -4.891,
    -5.046, -5.144, -5.293, -5.406, -5.521, -5.673, -5.784, -5.909, -6.067, -6.158,
    -6.686, -7.182, -7.707, -8.206, -8.747, -9.216, -9.750, -10.231, -10.759, -11.243,
    -11.757, -12.245, -12.772, -13.243, -13.770, -14.240, -14.762, -15.247, -15.748, -16.221,
    -16.736, -17.207, -17.705, -18.171, -18.662, -19.143, -19.613, -20.099, -20.562, -21.036,
    -21.493, -21.971, -22.424, -22.873, -23.328, -23.797, -24.237, -25.120,
], dtype=np.float64)


def elevation_step_deg(elevation_deg: np.ndarray | float) -> np.ndarray:
    """Local vertical angular resolution at a given elevation (deg)."""
    e = np.asarray(elevation_deg, dtype=np.float64)
    return np.where((e > -6.3) & (e < 2.1), 0.125, 0.5)


def expected_points(range_m, width_m, height_m, elevation_deg=None, returns: float = 1.0):
    """Approximate number of LiDAR returns from a flat ``width x height`` target facing the
    sensor at ``range_m`` (single return). Used as a visibility prior for clusters.

    n ~= (w / (r * d_az)) * (h / (r * d_el))
    """
    r = np.maximum(np.asarray(range_m, dtype=np.float64), 1e-3)
    if elevation_deg is None:
        elevation_deg = np.degrees(np.arctan2(-1.2, r))  # objects standing on the track bed
    d_az = np.radians(AZIMUTH_STEP_DEG)
    d_el = np.radians(elevation_step_deg(elevation_deg))
    n = (width_m / (r * d_az)) * (height_m / (r * d_el)) * returns
    return n


def ray_directions(fov_deg=AZIMUTH_FOV_DEG, az_step_deg=AZIMUTH_STEP_DEG,
                   ring_elev_deg=RING_ELEVATION_DEG) -> np.ndarray:
    """Unit ray directions (K,3) in the *vehicle* frame (X fwd, Y left, Z up) covering the
    sensor's angular grid. Azimuth is positive to the left."""
    az = np.radians(np.arange(fov_deg[0], fov_deg[1] + 1e-9, az_step_deg))
    el = np.radians(np.asarray(ring_elev_deg))
    az_g, el_g = np.meshgrid(az, el)
    d = np.stack(
        [np.cos(el_g) * np.cos(az_g), np.cos(el_g) * np.sin(az_g), np.sin(el_g)], axis=-1
    )
    return d.reshape(-1, 3)
