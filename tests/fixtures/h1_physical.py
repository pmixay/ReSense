"""Independent physical ray/AABB fixture derived from archived H4 case45.

No production geometry, fitted track or detector decision is used to cast hits.
An absorbing surface removes the nearest hit, never replaces it with background.
"""
import numpy as np

from resense.sensor import RING_ELEVATION_DEG


def physical_column(distance=67.0, lateral=0.68, width=0.46, top=3.22,
                    absorbing=None, beam=False, rails=False, wall_left=2.43, wall_right=-2.43,
                    rail_center=0.0, rail_spacing=1.59, azimuth_phase=0.037):
    az = np.radians(np.arange(-50.0, 50.00001, 0.1) + azimuth_phase)
    aa, ee = np.meshgrid(az, np.radians(RING_ELEVATION_DEG))
    rays = np.stack([np.cos(ee) * np.cos(aa), np.cos(ee) * np.sin(aa), np.sin(ee)], -1).reshape(-1, 3)
    ring = np.repeat(np.arange(len(RING_ELEVATION_DEG)), len(az))
    limits = []
    with np.errstate(divide="ignore", invalid="ignore"):
        for axis, bound in [(0, 247.0), (1, wall_left), (1, wall_right), (2, 4.12 - 1.83),
                            (2, -2.18 if rails else -1.83)]:
            t = bound / rays[:, axis]
            limits.append(np.where(t > 0, t, np.inf))
    dist = np.min(limits, axis=0)
    labels = np.zeros(len(dist), dtype=int)
    boxes = [([distance - width / 2, lateral - width / 2, -1.83],
              [distance + width / 2, lateral + width / 2, top - 1.83])]
    if beam:
        boxes.append(([distance - width / 2 - 4, -1.2, 2.65 - 1.83],
                       [distance - width / 2 - 3.7, 1.2, 3.25 - 1.83]))
    if rails:
        # 1.52 m inner gauge plus 0.07 m rail heads -> 1.59 m centres.
        for y in [rail_center - rail_spacing / 2, rail_center + rail_spacing / 2]:
            boxes.append(([3.0, y - 0.04, -2.18], [247.0, y + 0.04, -1.83]))
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
