"""Synthetic obstacles and augmentation.

Two tools:

* :func:`inject_obstacles` — insert a mesh obstacle into a *real* frame by casting the
  sensor's own ray grid against it (Open3D ``RaycastingScene``). This gives the correct
  range-dependent point density, correct occlusion of the background behind the object and
  (optionally) rays that had no return in the real frame. Used to build labelled frames at
  any distance from the empty-tunnel bags.
* :func:`synthetic_tunnel_frame` — a fully synthetic round tunnel (lining, floor, rails),
  used by the unit tests so they run without the dataset.

Open3D is only imported lazily so the runtime detector does not depend on it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy.spatial import cKDTree

from resense.frame import Frame
from resense.sensor import AZIMUTH_FOV_DEG, AZIMUTH_STEP_DEG, RING_ELEVATION_DEG, ray_directions
from resense.track import TrackModel


@dataclass
class ObstacleSpec:
    kind: str = "box"                 # box | cylinder | sphere | person | plank
    size: Tuple[float, float, float] = (0.5, 0.5, 0.5)   # (length X, width Y, height Z)
    distance: float = 50.0            # m along the track (nearest face, approximately)
    lateral: float = 0.0              # m from the track axis (+ left)
    yaw_deg: float = 0.0
    reflectivity: float = 40.0        # mean intensity of returns (Hesai 0..255)
    label: str = "obstacle"
    base: Optional[float] = None      # v0.6: height of the object's bottom above the rail head (m); None = standing on the bed / sleepers
    base_z: Optional[float] = None    # v0.6: absolute Z of the bottom in the vehicle frame (set by the injector from the local bed; wins over ``base``)

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "size": list(self.size), "distance": self.distance,
             "lateral": self.lateral, "yaw_deg": self.yaw_deg,
             "reflectivity": self.reflectivity, "label": self.label}
        if self.base is not None:
            d["base"] = self.base
        if self.base_z is not None:
            d["base_z"] = round(float(self.base_z), 3)
        return d


@dataclass
class CatalogueEntry:
    """A named test object for ``resense inject``: mesh kind, size and a reflectivity range
    (intensity in the bags is reflectivity %, > 100 retro-reflective; SENSOR.md section 2).
    The ranges are assumptions until calibrated on real obstacles of the extended dataset."""
    kind: str
    size: Tuple[float, float, float]      # (length X, width Y, height Z) m
    reflectivity: Tuple[float, float]     # uniform range
    note: str = ""
    base: Optional[float] = None          # bottom above the rail head (m); None = on the bed


# v0.6: effective diameter of a thin object for the ray caster. A real beam has a footprint of
# ``range * BEAM_DIVERGENCE_RAD`` (the Pandar128 manual gives no figure; 1 mrad is typical of
# 905 nm mechanical units); a cable returns an echo when it intercepts at least
# ``THIN_MIN_FILL`` of that footprint, so the grid ray caster sees it as up to
# 1 / THIN_MIN_FILL times its diameter at range. An assumption, stated in docs/DATASET.md.
BEAM_DIVERGENCE_RAD = 1.0e-3
THIN_MIN_FILL = 0.15


def effective_thickness(diameter: float, distance: float) -> float:
    foot = max(distance, 0.0) * BEAM_DIVERGENCE_RAD
    return float(max(diameter, min(foot, diameter / THIN_MIN_FILL)))


OBJECT_CATALOGUE = {
    "person":   CatalogueEntry("person", (0.4, 0.5, 1.7), (10, 60), "person in dark / ordinary clothing"),
    "hivis":    CatalogueEntry("person", (0.4, 0.5, 1.7), (150, 250), "person in a hi-vis vest (retro-reflective)"),
    "box0.2":   CatalogueEntry("box", (0.2, 0.2, 0.2), (20, 40), "cardboard box"),
    "box0.5":   CatalogueEntry("box", (0.5, 0.5, 0.5), (20, 40), "cardboard box"),
    "box1.0":   CatalogueEntry("box", (1.0, 1.0, 1.0), (20, 40), "cardboard crate"),
    "box":      CatalogueEntry("box", (0.5, 0.5, 0.5), (20, 40), "legacy name for box0.5"),
    "plank":    CatalogueEntry("plank", (2.0, 0.25, 0.30), (30, 60), "wooden plank / sleeper"),
    "trolley":  CatalogueEntry("cylinder", (0.6, 0.6, 1.0), (40, 120), "maintenance trolley (painted metal), cylinder approximation"),
    "cylinder": CatalogueEntry("cylinder", (0.4, 0.4, 0.9), (30, 90), "legacy: drum / bin"),
    "sphere":   CatalogueEntry("sphere", (0.4, 0.4, 0.4), (20, 60), "ball-like debris"),
    # v0.6, from the organizers' Q&A: the size criterion and hanging cables
    "lowbox":   CatalogueEntry("box", (0.3, 0.3, 0.1), (20, 60), "the organizers' minimum object: 300 x 300 x 100 mm lying on the track"),
    "box0.3":   CatalogueEntry("box", (0.3, 0.3, 0.3), (20, 60), "300 mm cube"),
    "cable":    CatalogueEntry("cable", (0.03, 0.03, 3.5), (10, 40), "broken cable hanging from the vault into the envelope, lower end 1.0 m above the rail head", base=1.0),
    "cable_low": CatalogueEntry("cable", (0.03, 0.03, 4.3), (10, 40), "cable hanging down to 0.2 m above the rail head", base=0.2),
    # v0.6.2, from the criteria review: an animal-sized object and one shaped like the organizers'
    # object lying across a rail (place it at lateral +-0.8 on the bed)
    "dog":      CatalogueEntry("box", (0.6, 0.3, 0.45), (10, 40), "dog-sized: 0.6 long x 0.3 wide x 0.45 m tall, standing on the bed"),
    "railobj":  CatalogueEntry("box", (0.4, 0.6, 0.31), (15, 40), "like the organizers' object: across a rail, top ~0.13 m above the rail head"),
}


def catalogue_spec(name: str, distance: float, lateral: float = 0.0, yaw_deg: float = 0.0,
                   rng: Optional[np.random.Generator] = None, label: Optional[str] = None,
                   reflectivity: Optional[float] = None) -> ObstacleSpec:
    """ObstacleSpec for a catalogue name; the reflectivity is drawn from the entry's range
    unless given. Raises KeyError with the list of names for an unknown one."""
    if name not in OBJECT_CATALOGUE:
        raise KeyError(f"unknown object {name!r}; known: {', '.join(OBJECT_CATALOGUE)}")
    e = OBJECT_CATALOGUE[name]
    if reflectivity is None:
        rng = rng or np.random.default_rng(0)
        reflectivity = float(rng.uniform(*e.reflectivity))
    return ObstacleSpec(kind=e.kind, size=e.size, distance=float(distance), lateral=float(lateral),
                        yaw_deg=float(yaw_deg), reflectivity=float(reflectivity), label=label or name,
                        base=e.base)


@dataclass
class InjectionResult:
    frame: Frame
    labels: np.ndarray                # (N,) int: 0 = background, k = k-th obstacle spec
    n_added: List[int] = field(default_factory=list)


def _o3d():
    try:
        import open3d as o3d  # noqa
    except ImportError as e:  # pragma: no cover
        raise ImportError("open3d is required for synthetic obstacle injection (pip install open3d)") from e
    return o3d


def obstacle_mesh(spec: ObstacleSpec, track: TrackModel, base_offset: float = 0.15):
    """Legacy Open3D TriangleMesh of the obstacle standing on the sleepers (``base_offset``
    metres below the rail head) at the requested distance."""
    o3d = _o3d()
    L, W, H = spec.size
    if spec.kind == "cable":
        # a thin vertical cylinder, thickened to what a beam of finite footprint sees at that range
        d = effective_thickness(W, spec.distance)
        m = o3d.geometry.TriangleMesh.create_cylinder(radius=d / 2, height=H, resolution=12)
        m.translate([0, 0, H / 2])
        L = W = d
    elif spec.kind == "box" or spec.kind == "plank":
        m = o3d.geometry.TriangleMesh.create_box(width=L, height=W, depth=H)
        m.translate([-L / 2, -W / 2, 0.0])
    elif spec.kind == "cylinder":
        m = o3d.geometry.TriangleMesh.create_cylinder(radius=W / 2, height=H, resolution=24)
        m.translate([0, 0, H / 2])
    elif spec.kind == "sphere":
        m = o3d.geometry.TriangleMesh.create_sphere(radius=H / 2, resolution=16)
        m.translate([0, 0, H / 2])
    elif spec.kind == "person":
        # torso+legs cylinder and a head sphere: ~0.5 m wide, H tall
        body = o3d.geometry.TriangleMesh.create_cylinder(radius=W / 2, height=H * 0.85, resolution=20)
        body.translate([0, 0, H * 0.85 / 2])
        head = o3d.geometry.TriangleMesh.create_sphere(radius=0.11, resolution=12)
        head.translate([0, 0, H * 0.85 + 0.11])
        m = body + head
    else:
        raise ValueError(f"unknown obstacle kind {spec.kind}")
    R = m.get_rotation_matrix_from_xyz((0, 0, np.radians(spec.yaw_deg)))
    m.rotate(R, center=(0, 0, 0))
    x = spec.distance + L / 2
    y = float(track.center_y(x)) + spec.lateral
    if spec.base_z is not None:
        z = float(spec.base_z)
    elif spec.base is not None:
        z = float(track.rail_z(x)) + float(spec.base)
    else:
        z = float(track.rail_z(x)) - base_offset
    m.translate([x, y, z])
    m.compute_vertex_normals()
    return m


def _angles_deg(xyz: np.ndarray):
    az = np.degrees(np.arctan2(xyz[:, 1], xyz[:, 0]))
    el = np.degrees(np.arctan2(xyz[:, 2], np.hypot(xyz[:, 0], xyz[:, 1])))
    return az, el


BED_DEPTH_DEFAULT = 0.25   # m below the rail head: the bed level measured on the organizer bags (DATASET.md)


def local_bed_z(xyz: np.ndarray, track: TrackModel, x: float, lateral: float,
                min_points: int = 8) -> Optional[float]:
    """Z of the real bed surface under a placement (30th percentile of the returns within
    +-max(1.5 m, 3 % of the range) along the track and +-0.4 m across, in the band 0.8 m
    below to 0.1 m above the rail head); None where the frame has too few bed returns
    (beyond ~60-80 m the bed is not observed)."""
    half_x = max(1.5, 0.03 * x)
    X = xyz[:, 0]
    near = np.abs(X - x) < half_x
    if not near.any():
        return None
    P = xyz[near]
    Xs = P[:, 0].astype(np.float64)
    dy = P[:, 1] - track.center_y(Xs)
    h = P[:, 2] - track.rail_z(Xs)
    sel = (np.abs(dy - lateral) < 0.4) & (h > -0.8) & (h < 0.1)
    if sel.sum() < min_points:
        return None
    # height above the rail head of the bed there, moved to X = x with the model's slope
    hb = float(np.percentile(h[sel], 30))
    return float(track.rail_z(x)) + hb


def place_on_bed(frame: Frame, track: TrackModel, specs: Sequence[ObstacleSpec],
                 bed_depth: float = BED_DEPTH_DEFAULT) -> List[ObstacleSpec]:
    """Copies of ``specs`` whose objects that stand on the ground (``base`` None) get
    ``base_z`` from the real bed under them (:func:`local_bed_z`), else ``bed_depth`` below
    the model's rail head. Objects with a ``base`` (hanging cables) keep it."""
    from dataclasses import replace
    out = []
    for sp in specs:
        if sp.base is not None or sp.base_z is not None:
            out.append(sp)
            continue
        x = sp.distance + sp.size[0] / 2
        z = local_bed_z(frame.xyz, track, x, sp.lateral)
        if z is None:
            z = float(track.rail_z(x)) - bed_depth
        out.append(replace(sp, base_z=z))
    return out


def inject_obstacles(frame: Frame, track: TrackModel, specs: Sequence[ObstacleSpec],
                     rng: Optional[np.random.Generator] = None, noise_sigma: float = 0.02,
                     dropout_start: float = 120.0, dropout_full: float = 260.0,
                     use_missing_rays: bool = True, angular_tol_deg: float = 0.06,
                     on_bed: bool = False) -> InjectionResult:
    """Insert obstacles into a real frame with occlusion-correct ray casting.

    For every ray of the sensor grid that hits an obstacle: if the real frame has a return
    on that ray closer than the hit, the obstacle is occluded (nothing changes); if it has a
    return farther away, that return is removed (the obstacle shadows it) and the hit is
    added; if the ray had no return at all and ``use_missing_rays`` is set, the hit is added.

    ``on_bed`` (v0.6): stand ground objects on the real bed measured under them
    (:func:`place_on_bed`) instead of 0.15 m below the model's rail head, which beyond the
    fitted bed range buried far objects under the real bed (EXPERIMENTS.md §2c).
    """
    o3d = _o3d()
    rng = rng or np.random.default_rng(0)
    if on_bed:
        specs = place_on_bed(frame, track, specs)
    scene = o3d.t.geometry.RaycastingScene()
    for spec in specs:
        scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(obstacle_mesh(spec, track)))

    dirs = ray_directions()  # full grid, vehicle frame
    rays = np.concatenate([np.zeros_like(dirs), dirs], axis=1).astype(np.float32)
    ans = scene.cast_rays(o3d.core.Tensor(rays))
    t_hit = ans["t_hit"].numpy()
    geom = ans["geometry_ids"].numpy()
    hit = np.isfinite(t_hit)
    if not hit.any():
        return InjectionResult(frame=frame, labels=np.zeros(frame.n, dtype=np.int32), n_added=[0] * len(specs))

    hit_idx = np.flatnonzero(hit)
    hit_dirs, hit_t, hit_geom = dirs[hit_idx], t_hit[hit_idx], geom[hit_idx]
    az_h, el_h = _angles_deg(hit_dirs)

    xyz = frame.xyz
    rng_real = np.linalg.norm(xyz, axis=1)
    az_r, el_r = _angles_deg(xyz)
    tree = cKDTree(np.stack([az_r, el_r], axis=1))
    keep = np.ones(frame.n, dtype=bool)
    new_pts, new_int, new_lab = [], [], []
    added = [0] * len(specs)
    for k in range(hit_idx.size):
        d = hit_t[k]
        # range-dependent dropout (weak returns are lost at long range)
        p_drop = np.clip((d - dropout_start) / max(dropout_full - dropout_start, 1.0), 0.0, 0.95)
        p_drop *= (1.0 - specs[hit_geom[k]].reflectivity / 255.0)
        if rng.random() < p_drop:
            continue
        near = tree.query_ball_point([az_h[k], el_h[k]], angular_tol_deg)
        occluded = False
        for j in near:
            if rng_real[j] < d - 0.05:
                occluded = True
                break
        if occluded:
            continue
        if not near and not use_missing_rays:
            continue
        for j in near:
            keep[j] = False  # shadowed background returns
        dn = d + rng.normal(0.0, noise_sigma * (1.0 + d / 100.0))
        new_pts.append(hit_dirs[k] * dn)
        spec = specs[hit_geom[k]]
        new_int.append(np.clip(rng.normal(spec.reflectivity, 0.15 * spec.reflectivity + 1.0), 1.0, 255.0))
        new_lab.append(int(hit_geom[k]) + 1)
        added[int(hit_geom[k])] += 1

    labels = np.zeros(frame.n, dtype=np.int32)
    xyz_out = xyz[keep]
    int_out = frame.intensity[keep]
    ring_out = frame.ring[keep] if frame.ring is not None else None
    lab_out = labels[keep]
    if new_pts:
        xyz_out = np.concatenate([xyz_out, np.asarray(new_pts, dtype=np.float32)])
        int_out = np.concatenate([int_out, np.asarray(new_int, dtype=np.float32)])
        if ring_out is not None:
            ring_out = np.concatenate([ring_out, np.zeros(len(new_pts), dtype=ring_out.dtype)])
        lab_out = np.concatenate([lab_out, np.asarray(new_lab, dtype=np.int32)])
    out = Frame(xyz=xyz_out, intensity=int_out, ring=ring_out, stamp=frame.stamp,
                frame_id=frame.frame_id, meta=dict(frame.meta, obstacles=[s.to_dict() for s in specs]))
    return InjectionResult(frame=out, labels=lab_out, n_added=added)


# ---------------------------------------------------------------------------
# background augmentation (no Open3D needed)
# ---------------------------------------------------------------------------

def augment_background(frame: Frame, rng: Optional[np.random.Generator] = None,
                       dropout: float = 0.05, range_noise: float = 0.01,
                       pitch_deg: float = 0.3, yaw_deg: float = 0.3, roll_deg: float = 0.2,
                       intensity_jitter: float = 0.1) -> Frame:
    """Cheap augmentations of an empty-tunnel frame: random point dropout, range noise,
    small rotations (mounting tolerance), intensity jitter."""
    rng = rng or np.random.default_rng()
    xyz = frame.xyz.astype(np.float32).copy()
    inten = frame.intensity.copy()
    ring = frame.ring
    n = xyz.shape[0]
    if dropout > 0:
        keep = rng.random(n) >= dropout
        xyz, inten = xyz[keep], inten[keep]
        ring = ring[keep] if ring is not None else None
    if range_noise > 0:
        r = np.linalg.norm(xyz, axis=1, keepdims=True)
        xyz = xyz * (1.0 + rng.normal(0.0, range_noise, size=(xyz.shape[0], 1)) / np.maximum(r, 1.0))
    a, b, c = (np.radians(rng.uniform(-v, v)) for v in (roll_deg, pitch_deg, yaw_deg))
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    Rz = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    xyz = (xyz @ (Rz @ Ry @ Rx).T.astype(np.float32))
    if intensity_jitter > 0:
        inten = np.clip(inten * rng.normal(1.0, intensity_jitter, size=inten.shape), 0, 255).astype(np.float32)
    return Frame(xyz=xyz.astype(np.float32), intensity=inten, ring=ring, stamp=frame.stamp,
                 frame_id=frame.frame_id, meta=dict(frame.meta))


# ---------------------------------------------------------------------------
# fully synthetic tunnel (tests / demos without data)
# ---------------------------------------------------------------------------

def synthetic_tunnel_frame(length: float = 250.0, radius: float = 2.7, axis_y: float = 0.25,
                           axis_z: float = 0.8, floor_z: float = -1.5, grade: float = 0.0,
                           noise_sigma: float = 0.01, rng: Optional[np.random.Generator] = None,
                           specs: Sequence[ObstacleSpec] = (), reflect_floor: float = 8.0,
                           reflect_wall: float = 12.0) -> Tuple[Frame, np.ndarray, TrackModel]:
    """Ray-cast a round tunnel with a flat track bed (+ two rails) and optional obstacles.
    Returns (frame, labels, ground-truth track model)."""
    o3d = _o3d()
    rng = rng or np.random.default_rng(0)
    track = TrackModel(floor_coef=np.array([0.0, grade, floor_z]), floor_range=(0.0, length),
                       center=axis_y, yaw=0.0, curvature=0.0)
    scene = o3d.t.geometry.RaycastingScene()
    # tunnel lining: cylinder along X
    cyl = o3d.geometry.TriangleMesh.create_cylinder(radius=radius, height=length * 2, resolution=64, split=4)
    cyl.rotate(cyl.get_rotation_matrix_from_xyz((0, np.pi / 2, 0)), center=(0, 0, 0))
    cyl.translate([0, axis_y, axis_z])
    # floor slab (track bed) and rails
    floor = o3d.geometry.TriangleMesh.create_box(width=length * 2, height=2 * radius, depth=0.3)
    floor.translate([-length, axis_y - radius, floor_z - 0.3])
    if abs(grade) > 0:
        floor.rotate(floor.get_rotation_matrix_from_xyz((0, -np.arctan(grade), 0)), center=(0, axis_y, floor_z))
    meshes = [cyl, floor]
    for side in (-1.0, 1.0):   # benches / walkways at the tunnel sides, 0.9 m high
        bench = o3d.geometry.TriangleMesh.create_box(width=length * 2, height=1.2, depth=0.9)
        bench.translate([-length, axis_y + (side * 1.95 if side > 0 else side * 1.95 - 1.2), floor_z])
        meshes.append(bench)
    for side in (-0.8, 0.8):
        rail = o3d.geometry.TriangleMesh.create_box(width=length * 2, height=0.07, depth=0.18)
        rail.translate([-length, axis_y + side - 0.035, floor_z])
        meshes.append(rail)
    for spec in specs:
        meshes.append(obstacle_mesh(spec, track))
    for m in meshes:
        scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(m))
    dirs = ray_directions()
    rays = np.concatenate([np.zeros_like(dirs), dirs], axis=1).astype(np.float32)
    ans = scene.cast_rays(o3d.core.Tensor(rays))
    t = ans["t_hit"].numpy()
    g = ans["geometry_ids"].numpy()
    ok = np.isfinite(t) & (t > 2.5) & (t < 210.0)
    t = t[ok] + rng.normal(0.0, noise_sigma, size=int(ok.sum())) * (1.0 + t[ok] / 100.0)
    xyz = (dirs[ok] * t[:, None]).astype(np.float32)
    g = g[ok]
    n_bg = 2 + 2 + 2
    labels = np.where(g >= n_bg, g - n_bg + 1, 0).astype(np.int32)
    inten = np.where(g == 0, reflect_wall, reflect_floor).astype(np.float32)
    for k, spec in enumerate(specs):
        inten[labels == k + 1] = spec.reflectivity
    inten = np.clip(inten * rng.normal(1.0, 0.1, size=inten.shape), 0, 255).astype(np.float32)
    frame = Frame(xyz=xyz, intensity=inten, ring=None, stamp=0.0, frame_id="synthetic",
                  meta={"obstacles": [s.to_dict() for s in specs]})
    return frame, labels, track
