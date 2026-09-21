"""Configuration of the detection pipeline (plain dataclasses, loadable from YAML)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, List, Tuple

import yaml


@dataclass
class SensorConfig:
    """How to map the raw sensor frame onto the vehicle frame (X fwd, Y left, Z up).

    Each entry names the sensor axis (with sign) that points along the vehicle axis.
    Hackathon bags (frame_id ``hesai_lidar``): forward = -y, left = +x, up = +z.
    """
    forward: str = "-y"
    left: str = "+x"
    up: str = "+z"
    min_range: float = 2.5     # m, closer returns are the train's own nose / sensor artefacts
    max_range: float = 250.0   # m
    frame_id: str = "hesai_lidar"


@dataclass
class TrackConfig:
    """Track/floor model estimated per frame."""
    lateral_center: float = -0.1   # m, prior/fallback offset of the track axis (+ = left)
    yaw_deg: float = 0.0           # residual yaw of the corridor w.r.t. vehicle X axis
    curvature: float = 0.0         # 1/m, signed (left positive); 0 = straight
    floor_fit_range: Tuple[float, float] = (3.0, 120.0)
    floor_bin: float = 2.0         # m, along-track bin size for the floor profile
    floor_percentile: float = 20.0 # per-bin percentile of Z taken as floor reference (track bed)
    floor_halfwidth: float = 1.0   # m, lateral band around the track axis used for the fit
    floor_min_points: int = 15     # per bin
    floor_poly_degree: int = 2
    floor_max_residual: float = 0.35  # m, bins further from the fit are rejected (2nd pass)
    floor_smoothing: float = 0.5   # exponential smoothing of coefficients across frames (0 = off)
    # --- rail-based self-calibration of the track axis (near range) ---
    rails_enabled: bool = True
    rails_range: Tuple[float, float] = (4.0, 30.0)   # m along track
    rails_search_halfwidth: float = 2.5             # m around the prior axis
    rails_bin: float = 0.05                         # m lateral bin of the height profile
    rails_percentile: float = 85.0                  # per-bin height percentile (rail head)
    rails_spacing: float = 1.59                     # m between rail-head centres (1520 gauge + head)
    rails_min_score: float = 0.05                   # m, ridge prominence needed to accept
    rails_head_height: Tuple[float, float] = (0.08, 0.5)  # plausible rail head above bed ref
    rails_smoothing: float = 0.7                    # EMA of the axis across frames
    rail_offset_default: float = 0.35               # rail head above bed reference if not measured
    # --- yaw / curvature of the axis from the tunnel boundaries (walls, column rows) ---
    walls_enabled: bool = True
    walls_range: Tuple[float, float] = (6.0, 160.0)  # m along track
    walls_band: Tuple[float, float] = (1.6, 2.8)     # height band above the rail head (above platforms)
    walls_bin: float = 4.0                           # m along-track bin
    walls_min_points: int = 3                        # per side per bin
    walls_percentile: float = 90.0                   # boundary = this percentile of |dy| per side
    walls_max_residual: float = 0.4                  # m, bins further from the fit are rejected
    walls_min_bins: int = 6
    walls_max_rms: float = 0.35
    walls_max_yaw: float = 0.035                     # |tan(yaw)| limit (~2 deg)
    walls_min_radius: float = 150.0                  # m, curvature limit
    walls_smoothing: float = 0.6                     # EMA of (yaw, curvature) across frames
    axis_valid_margin: float = 15.0                  # m beyond the last observed boundary bin the axis is trusted
    axis_valid_straight_bonus: float = 50.0          # extra trusted range when the tunnel is straight (|curv| < 1e-4)
    floor_valid_margin: float = 60.0                 # m beyond the fitted bed range the height reference is trusted
    # --- verification of the extrapolated bed beyond its fitted range (second height anchor) ---
    floor_verify_enabled: bool = True                # confirm the extrapolated bed with the base of the side structures
    floor_verify_band: Tuple[float, float] = (1.6, 3.5)  # m, |dy| band of walls / benches / ducts (outside the advisory corridor)
    floor_verify_bin: float = 5.0                    # m, along-track bin of the side-base profile
    floor_verify_window: float = 30.0                # m, window whose median deviation must stay within the tolerance
    floor_verify_tolerance: float = 0.5              # m, allowed deviation of the far side base from its near-range height
    floor_verify_min_points: int = 5                 # side points per bin for the bin to count
    floor_verify_max_range: float = 250.0            # m, how far the verification is attempted


@dataclass
class GaugeConfig:
    """Clearance-gauge cross-section, relative to the track axis and the rail head level.

    ``profile`` is a closed polygon [(dy, h), ...] with dy = lateral offset from the track
    axis (m, + left) and h = height above the rail head (m). Default: half-width 1.4 m
    (car body 1.36 m + margin; platform edges sit at ~1.6 m) from 0.55 m up (above the contact-rail cover), and a lower
    zone from 0.12 m in the middle (|dy| < 0.95 m, between the rails). Top at 3.5 m.
    The ``warning_margin`` widens the polygon laterally for a second, advisory zone.
    Values are placeholders — refine against GOST 23961-80 drawings.
    """
    profile: List[Tuple[float, float]] = field(default_factory=lambda: [
        (-0.95, 0.12), (0.95, 0.12), (0.95, 0.55), (1.40, 0.55), (1.40, 3.50),
        (-1.40, 3.50), (-1.40, 0.55), (-0.95, 0.55),
    ])
    warning_margin: float = 0.35   # m, extra lateral width of the advisory zone
    range_min: float = 3.0         # m along track
    range_max: float = 250.0
    lateral_growth_per_100m: float = 0.0  # widen corridor with range to absorb yaw uncertainty


@dataclass
class ClusterConfig:
    eps: float = 0.35              # m, DBSCAN radius at range 0 (scaled by 1 + r / range_scale)
    range_scale: float = 40.0      # m
    voxel: float = 0.05            # m, voxel size in range-normalised space (merges dual returns)
    min_samples: int = 3
    min_points: int = 5            # minimum cluster size in voxels (near range)
    min_points_far: int = 3        # minimum cluster size beyond ``far_range``
    far_range: float = 100.0
    max_extent: float = 8.0        # m, larger clusters are tunnel structure, not obstacles
    min_height: float = 0.08       # m, vertical extent (very flat clusters = floor noise)
    # linear infrastructure (rails, pipes, cables): long, thin, flat
    thin_min_length: float = 3.0
    thin_max_width: float = 0.35
    thin_max_height: float = 0.25
    # track hardware: low, narrow things on/next to the rails (clamps, cables, joint bars)
    hardware_max_top: float = 0.35     # m above rail head
    hardware_max_width: float = 0.4
    hardware_max_height: float = 0.3
    # linear structures along the track at the side (platform edges, ducts, cable trays)
    linear_min_aspect: float = 5.0     # length / width
    linear_max_height: float = 0.8
    linear_min_lateral: float = 0.8
    # wall-like clusters at the side of the corridor (columns, gate frames, platform walls)
    wall_min_height: float = 1.9
    wall_min_lateral: float = 1.2
    wall_segment_min_length: float = 4.0   # tall + long + narrow = wall segment (a train ahead is wide)
    wall_segment_max_width: float = 1.5
    gauge_min_points: int = 3      # voxels inside the strict gauge to classify as 'gauge'
    overhead_min_height: float = 2.4   # clusters entirely above this (m over rail head) are advisory only
    visibility_ratio: float = 0.15 # cluster is plausible if n >= ratio * expected points


@dataclass
class TrackingConfig:
    gate_base: float = 1.5         # m, association gate at range 0
    gate_per_m: float = 0.02       # m per metre of range
    ego_speed_max: float = 25.0    # m/s, obstacles approach at most this fast (no odometry)
    frame_dt: float = 0.1          # s
    confirm_hits: int = 3          # consecutive frames before an obstacle is reported
    max_misses: int = 3            # frames a track survives without a match
    conf_gain: float = 0.35        # confidence added per hit
    conf_decay: float = 0.25       # confidence removed per miss
    conf_threshold: float = 0.6    # report obstacles with confidence >= threshold


@dataclass
class DetectorConfig:
    sensor: SensorConfig = field(default_factory=SensorConfig)
    track: TrackConfig = field(default_factory=TrackConfig)
    gauge: GaugeConfig = field(default_factory=GaugeConfig)
    cluster: ClusterConfig = field(default_factory=ClusterConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    voxel: float = 0.0             # optional voxel downsampling of corridor candidates (0 = off)

    # ---- (de)serialisation -------------------------------------------------
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DetectorConfig":
        cfg = cls()
        for section in ("sensor", "track", "gauge", "cluster", "tracking"):
            if section in d and d[section]:
                obj = getattr(cfg, section)
                for k, v in d[section].items():
                    if not hasattr(obj, k):
                        raise KeyError(f"unknown parameter {section}.{k}")
                    if k == "profile":
                        v = [tuple(p) for p in v]
                    elif isinstance(getattr(obj, k), tuple):
                        v = tuple(v)
                    setattr(obj, k, v)
        if "voxel" in d:
            cfg.voxel = float(d["voxel"])
        return cfg

    @classmethod
    def from_yaml(cls, path: str) -> "DetectorConfig":
        with open(path, "r", encoding="utf-8") as fh:
            d = yaml.safe_load(fh) or {}
        return cls.from_dict(d.get("resense", d))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_yaml(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump({"resense": self.to_dict()}, fh, sort_keys=False, allow_unicode=True)
