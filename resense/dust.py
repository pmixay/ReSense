"""Reproducible volumetric-return/occlusion stress; not a calibrated dust model.

The output contains no truth hint for the detector. Source indices and augmentation
metadata are returned separately, so an evaluator can keep clean obstacle labels.
Coordinates are vehicle-frame metres; callers supply the clean rail reference.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from resense.frame import Frame


@dataclass(frozen=True)
class DustSpec:
    density: float = 0.0
    extinction: float = 0.0
    x_bounds: tuple[float, float] = (2.5, 60.0)
    y_bounds: tuple[float, float] = (-3.0, 3.0)
    height_bounds: tuple[float, float] = (0.1, 3.5)
    intensity_max: float = 5.0

    def __post_init__(self):
        for name in ("density", "extinction", "intensity_max"):
            if not np.isfinite(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        for name in ("x_bounds", "y_bounds", "height_bounds"):
            bounds = getattr(self, name)
            if len(bounds) != 2 or not np.isfinite(bounds).all() or bounds[0] >= bounds[1]:
                raise ValueError(f"{name} must be two increasing finite values")
        if self.x_bounds[0] < 0:
            raise ValueError("dust cloud must be ahead of the sensor")
        volume = np.prod([b[1] - b[0] for b in
                          (self.x_bounds, self.y_bounds, self.height_bounds)])
        if volume * self.density > 2_000_000:
            raise ValueError("stress cloud exceeds two million expected returns")


PRESETS = {"clean": DustSpec(),
           "low": DustSpec(density=0.1, extinction=0.0005),
           "medium": DustSpec(density=1.0, extinction=0.003),
           "high": DustSpec(density=10.0, extinction=0.02)}


def ray_lengths_in_box(xyz: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Length of each sensor-to-return segment inside the cloud's axis-aligned box."""
    points = np.asarray(xyz, dtype=np.float64)
    nonzero = points != 0
    a = np.divide(lo, points, out=np.full_like(points, -np.inf), where=nonzero)
    b = np.divide(hi, points, out=np.full_like(points, np.inf), where=nonzero)
    near = np.maximum(np.minimum(a, b).max(axis=1), 0.0)
    far = np.minimum(np.maximum(a, b).min(axis=1), 1.0)
    parallel_outside = ((~nonzero) & ((lo > 0) | (hi < 0))).any(axis=1)
    return np.where(parallel_outside, 0.0, np.maximum(far - near, 0.0) *
                    np.linalg.norm(points, axis=1))


def augment_dust(frame: Frame, spec: DustSpec, *, rail_z: float,
                 seed: int = 0, frame_index: int = 0) -> tuple[Frame, dict, np.ndarray]:
    """Return augmented frame, audit metadata and original index (-1 for new returns).

    Uniform volume returns follow a Poisson count. Real-return survival follows
    exp(-extinction * ray length through cloud). Independent RNG streams make
    attenuation identical for the same source/seed regardless of injected count.
    The ring of a synthetic return is the nearest measured ring elevation when
    rings exist; this approximates channel metadata, not a scanner ray simulation.
    No input array or original label is modified.
    """
    if not np.isfinite(rail_z) or seed < 0 or frame_index < 0:
        raise ValueError("finite rail_z and nonnegative seed/frame_index required")
    lo = np.array([spec.x_bounds[0], spec.y_bounds[0], rail_z + spec.height_bounds[0]])
    hi = np.array([spec.x_bounds[1], spec.y_bounds[1], rail_z + spec.height_bounds[1]])
    streams = np.random.SeedSequence([seed, frame_index]).spawn(2)
    attenuation, volume = (np.random.default_rng(s) for s in streams)
    path = ray_lengths_in_box(frame.xyz, lo, hi)
    keep = attenuation.random(frame.n) < np.exp(-spec.extinction * path)
    count = int(volume.poisson(float(np.prod(hi - lo)) * spec.density))
    dust = volume.uniform(lo, hi, size=(count, 3)).astype(np.float32)
    dust_i = volume.uniform(0, spec.intensity_max, size=count).astype(np.float32)
    xyz = np.concatenate((frame.xyz[keep], dust))
    intensity = np.concatenate((frame.intensity[keep], dust_i))
    ring = None
    if frame.ring is not None:
        ids = np.unique(frame.ring)
        if count and len(ids):
            elevations = np.arctan2(frame.xyz[:, 2], np.hypot(frame.xyz[:, 0], frame.xyz[:, 1]))
            medians = np.array([np.median(elevations[frame.ring == r]) for r in ids])
            order = np.argsort(medians)
            medians, ids = medians[order], ids[order]
            dust_e = np.arctan2(dust[:, 2], np.hypot(dust[:, 0], dust[:, 1]))
            upper = np.minimum(np.searchsorted(medians, dust_e), len(ids) - 1)
            lower = np.maximum(upper - 1, 0)
            nearest = np.where(abs(dust_e - medians[lower]) < abs(dust_e - medians[upper]), lower, upper)
            dust_ring = ids[nearest]
        else:
            dust_ring = np.zeros(count, dtype=frame.ring.dtype)
        ring = np.concatenate((frame.ring[keep], dust_ring))
    indices = np.concatenate((np.flatnonzero(keep), np.full(count, -1, dtype=np.int64)))
    meta = dict(frame.meta)
    removed = int((~keep).sum())
    meta["n_raw"] = max(0, int(meta.get("n_raw", frame.n)) - removed + count)
    result = Frame(xyz, intensity, ring, frame.stamp, frame.frame_id, meta)
    audit = {"model": "volumetric_stress_v1_not_measured_physics", "seed": seed,
             "frame_index": frame_index, "spec": asdict(spec), "rail_z": float(rail_z),
             "source_points": frame.n, "added_returns": count, "removed_returns": removed,
             "affected_source_returns": int((path > 0).sum()),
             "maximum_optical_depth": float((spec.extinction * path).max(initial=0))}
    return result, audit, indices
