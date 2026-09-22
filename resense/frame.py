"""Frame container and sensor -> vehicle frame conversion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from resense.config import SensorConfig

_AXIS = {"x": 0, "y": 1, "z": 2}


def axis_matrix(cfg: SensorConfig) -> np.ndarray:
    """Rotation matrix R such that p_vehicle = R @ p_sensor: the signed axis mapping
    (``forward/left/up``) followed by the fixed mount correction ``Rz(yaw) Ry(pitch) Rx(roll)``."""
    R = np.zeros((3, 3))
    for row, spec in enumerate((cfg.forward, cfg.left, cfg.up)):
        spec = spec.strip().lower()
        sign = -1.0 if spec.startswith("-") else 1.0
        ax = spec.lstrip("+-")
        if ax not in _AXIS:
            raise ValueError(f"bad axis spec {spec!r}")
        R[row, _AXIS[ax]] = sign
    if abs(np.linalg.det(R) - 1.0) > 1e-6:
        raise ValueError("sensor axis mapping is not a proper rotation (check handedness)")
    roll, pitch, yaw = (np.radians(float(getattr(cfg, k, 0.0))) for k in ("roll_deg", "pitch_deg", "yaw_deg"))
    if roll or pitch or yaw:
        from resense.calibration import rot_x, rot_y, rot_z
        R = rot_z(yaw) @ rot_y(pitch) @ rot_x(roll) @ R
    return R


@dataclass
class Frame:
    """A LiDAR frame in the vehicle frame (X forward, Y left, Z up)."""
    xyz: np.ndarray                      # (N,3) float32
    intensity: np.ndarray                # (N,)
    ring: Optional[np.ndarray] = None    # (N,) uint16
    stamp: float = 0.0                   # seconds (bag/receive time)
    frame_id: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(self.xyz.shape[0])


def sensor_to_vehicle(xyz_sensor: np.ndarray, cfg: SensorConfig) -> np.ndarray:
    R = axis_matrix(cfg).astype(np.float32)
    return xyz_sensor @ R.T


def frame_from_compact(arr: np.ndarray, cfg: SensorConfig, stamp: float = 0.0,
                       frame_id: str = "") -> Frame:
    """Compact structured array (sensor frame, float32 or the quantised int16 cache) ->
    Frame (vehicle frame), range-filtered."""
    from resense.pointcloud import compact_to_xyz, expand_compact16
    arr = expand_compact16(arr)
    xyz = compact_to_xyz(arr)
    r2 = (xyz * xyz).sum(axis=1)
    finite = np.isfinite(r2)
    ok = finite & (r2 >= cfg.min_range ** 2) & (r2 <= cfg.max_range ** 2)
    xyz_v = sensor_to_vehicle(xyz[ok], cfg)
    inten = arr["intensity"][ok].astype(np.float32) if "intensity" in arr.dtype.names else np.zeros(int(ok.sum()), np.float32)
    ring = arr["ring"][ok] if "ring" in arr.dtype.names else None
    # input statistics for the health monitor (resense/health.py): returns before the range
    # filter and how many of them were closer than min_range (window dirt, the train's nose)
    meta = {"n_raw": int(finite.sum()), "n_near": int((finite & (r2 < cfg.min_range ** 2)).sum())}
    return Frame(xyz=xyz_v, intensity=inten, ring=ring, stamp=stamp, frame_id=frame_id, meta=meta)
