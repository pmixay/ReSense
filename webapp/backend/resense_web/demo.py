"""Synthetic demo recordings: a round metro tunnel ray-cast analytically (numpy only, no open3d)
over the sensor's own ray grid and written as a rosbag2 bag laid out like the organizers' ones.

Vehicle frame: X forward, Y left, Z up, the LiDAR at the origin. The track runs along X; the
train's odometer ``s`` shifts every x-dependent feature (lining ribs, sleepers, lamps, niches,
trackside equipment), so the motion is visible in the cloud. Scenarios:

* ``approach`` - the train cruises at 12 m/s and brakes (1.6 m/s^2) to a stop about 25 m before a
  person standing on the track, first ~140-150 m ahead in a 15 s recording;
* ``crossing`` - the train stands; a person walks across the track at ~55 m between a cross
  passage and a niche (in and out of the envelope), like the real ``doubleT_obstacle``;
* ``clear`` - the train drives at 11 m/s past trackside equipment next to (never inside) the
  2.1 x 3.0 m envelope; no obstacle.

The bag mirrors ``scripts/make_smoke_bag.py``: topic ``/lidar_points``, frame_id ``hesai_lidar``,
fields ``x y z intensity ring timestamp`` (point_step 26, one slot per ray, ``(0, 0, 0)`` for no
return), 10 Hz, sqlite3 storage (schema 3) and ``metadata.yaml`` version 5. The CDR messages are
encoded here, so writing needs neither ROS nor ``rosbags``. ``ground_truth.json`` (the
``labels/*.json`` format, keyed by bag frame index) is written next to the bag.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import struct
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
import yaml

from resense.config import SensorConfig
from resense.frame import axis_matrix
from resense.sensor import AZIMUTH_FOV_DEG, AZIMUTH_STEP_DEG, MAX_RANGE_M, RING_ELEVATION_DEG, ray_directions

SCENARIOS = ("approach", "crossing", "clear")
SECONDS_RANGE = (1.0, 120.0)
RATE_HZ = 10.0
TOPIC = "/lidar_points"
FRAME_ID = "hesai_lidar"
MSGTYPE = "sensor_msgs/msg/PointCloud2"
GROUND_TRUTH = "ground_truth.json"
# the QoS string rosbag2 Humble wrote into the organizers' bags (as scripts/make_smoke_bag.py)
QOS = ("- history: 1\n  depth: 10\n  reliability: 1\n  durability: 2\n  deadline:\n    sec: 9223372036\n"
       "    nsec: 854775807\n  lifespan:\n    sec: 9223372036\n    nsec: 854775807\n  liveliness: 1\n"
       "  liveliness_lease_duration:\n    sec: 9223372036\n    nsec: 854775807\n"
       "  avoid_ros_namespace_conventions: false")
POINT_DTYPE = np.dtype({"names": ["x", "y", "z", "intensity", "ring", "timestamp"],
                        "formats": ["<f4", "<f4", "<f4", "<f4", "<u2", "<f8"],
                        "offsets": [0, 4, 8, 12, 16, 18], "itemsize": 26})
PF_FLOAT32, PF_UINT16, PF_FLOAT64 = 7, 4, 8
POINT_FIELDS = (("x", 0, PF_FLOAT32), ("y", 4, PF_FLOAT32), ("z", 8, PF_FLOAT32),
                ("intensity", 12, PF_FLOAT32), ("ring", 16, PF_UINT16), ("timestamp", 18, PF_FLOAT64))
BAG_T0_NS = 1_700_000_000 * 1_000_000_000      # an arbitrary but sane bag clock
SENSOR_T0 = 946_684_800.0                      # the sensor's unsynchronised year-2000 epoch
SWEEP_S = 0.028                                # the +-50 deg of returns (a 120 deg sweep takes 33 ms)

MIN_RANGE_M = 2.5

# --- tunnel geometry (vehicle frame, m) ---------------------------------------------------------
TRACK_Y = -0.10          # track axis, right of the sensor axis as in the recordings
BED_Z = -1.50            # track bed
RAIL_TOP = -1.32         # rail heads (sensor 1.32 m above them)
RAIL_Y = 0.795           # rail-head centres at +-1.59 / 2 from the axis
RAIL_W = 0.07
TUNNEL_R = 2.70
TUNNEL_CZ = 0.70         # crown 3.4 m above the sensor
RIB_PERIOD, RIB_WIDTH, RIB_DEPTH = 1.0, 0.06, 0.03   # ring flanges of the lining
WALK_Y0, WALK_Z1 = 1.75, BED_Z + 0.75                # walkway (bench) on the left
CRAIL_Y = (-2.00, -1.80)                             # contact rail and cover on the right
CRAIL_Z = (RAIL_TOP + 0.20, RAIL_TOP + 0.42)
CABLE_Y, CABLE_Z = (-2.75, -2.50), (0.00, 0.22)      # cable bundle on the right wall
SLEEPER = dict(y=(-1.25, 1.25), z=(BED_Z, BED_Z + 0.08), length=0.25, period=0.75)
LAMP = dict(y=(2.28, 2.90), z=(1.20, 1.34), length=0.5, period=10.0)
PERSON_SIZE = (0.40, 0.50, 1.70)                     # along X, across, height

# surface ids; INTENSITY[id] is the mean return intensity (reflectivity %) of that surface
LINING, RIB, BED, SLEEPER_ID, RAIL, WALKWAY, CRAIL, CABLE, BRACKET, LAMP_ID, SUPPORT, NICHE, \
    SIGNAL, CABINET, MARKER, PERSON = range(16)
INTENSITY = np.array([11, 7, 8, 14, 32, 18, 28, 20, 30, 110, 24, 9, 55, 40, 85, 45], dtype=np.float32)
_BED_LIKE = np.array([BED, SLEEPER_ID], dtype=np.int16)


def _r(v: float) -> float:
    return round(float(v), 3)


# --- ray grid -------------------------------------------------------------------------------------

@dataclass
class _Grid:
    dx: np.ndarray            # (rings, columns) unit direction components
    dy: np.ndarray
    dz: np.ndarray
    az: np.ndarray            # (columns,) deg, increasing
    el: np.ndarray            # (rings,) deg, decreasing


@lru_cache(maxsize=1)
def _grid() -> _Grid:
    n_ring = RING_ELEVATION_DEG.size
    d = ray_directions().reshape(n_ring, -1, 3).astype(np.float64)
    d = np.where(np.abs(d) < 1e-12, 1e-12, d)       # no exact zeros: the slab tests divide by them
    az = np.arange(AZIMUTH_FOV_DEG[0], AZIMUTH_FOV_DEG[1] + 1e-9, AZIMUTH_STEP_DEG)
    return _Grid(dx=d[..., 0].copy(), dy=d[..., 1].copy(), dz=d[..., 2].copy(), az=az,
                 el=np.asarray(RING_ELEVATION_DEG, dtype=np.float64))


def _slab_yz(dy, dz, y0, y1, z0, z1):
    """Entry / exit parameters of rays from the origin through the infinite (in X) prism
    ``y0..y1 x z0..z1`` (entry < exit where they cross it)."""
    ty0, ty1 = y0 / dy, y1 / dy
    tz0, tz1 = z0 / dz, z1 / dz
    t_in = np.maximum(np.minimum(ty0, ty1), np.minimum(tz0, tz1))
    t_out = np.minimum(np.maximum(ty0, ty1), np.maximum(tz0, tz1))
    return t_in, t_out


def _cylinder_exit(dy, dz, cy, cz, radius):
    """Distance along rays from the origin (inside the cylinder) to the X-axis cylinder wall."""
    a = dy * dy + dz * dz
    b = dy * cy + dz * cz
    c = cy * cy + cz * cz - radius * radius
    return (b + np.sqrt(np.maximum(b * b - a * c, 0.0))) / a


@dataclass
class _Periodic:
    """A box repeated along X (period, length, phase in world X) with a fixed Y-Z section: the
    Y-Z slab crossing of every ray is precomputed, a frame only tests X."""
    idx: np.ndarray           # flat ray indices that cross the section before the static hit
    t_in: np.ndarray
    t_out: np.ndarray
    dx: np.ndarray
    length: float
    period: float
    phase: float
    sid: int


@dataclass
class _NicheType:
    """Rays whose static hit is the lining within a side / height window, and where they would
    leave a recess of ``depth`` behind the lining."""
    idx: np.ndarray
    t_wall: np.ndarray
    t_back: np.ndarray
    dx: np.ndarray
    dz: np.ndarray
    z0: float
    z1: float


@dataclass
class _Static:
    t: np.ndarray             # (rings * columns,) nearest static hit
    sid: np.ndarray
    rib_idx: np.ndarray       # lining rays: flange inner surface / wall
    rib_t_in: np.ndarray
    rib_t_out: np.ndarray
    rib_dx: np.ndarray
    periodic: list = field(default_factory=list)
    niche_types: dict = field(default_factory=dict)


def _niche_type(g: _Grid, t_lin: np.ndarray, sid: np.ndarray, side: int, z0: float, z1: float,
                depth: float) -> _NicheType:
    dy, dz, dx = g.dy.ravel(), g.dz.ravel(), g.dx.ravel()
    zw = t_lin * dz
    yw = t_lin * dy - TRACK_Y
    sel = np.flatnonzero((sid == LINING) & (np.sign(yw) == side) & (zw >= z0) & (zw <= z1))
    t_back = _cylinder_exit(dy[sel], dz[sel], TRACK_Y, TUNNEL_CZ, TUNNEL_R + depth)
    return _NicheType(idx=sel, t_wall=t_lin[sel], t_back=t_back, dx=dx[sel], dz=dz[sel], z0=z0, z1=z1)


NICHE_TYPES = {
    # name: (side, z0, z1, depth, width along X)
    "passage": (+1, BED_Z, BED_Z + 2.40, 2.0, 3.0),     # cross passage to the other running tunnel
    "opposite": (-1, BED_Z, BED_Z + 2.30, 1.2, 2.5),    # recess opposite a passage
    "refuge_l": (+1, WALK_Z1, WALK_Z1 + 2.0, 0.6, 1.2),
    "refuge_r": (-1, BED_Z + 0.3, BED_Z + 2.3, 0.6, 1.2),
}


@lru_cache(maxsize=1)
def _static() -> _Static:
    g = _grid()
    dx, dy, dz = g.dx.ravel(), g.dy.ravel(), g.dz.ravel()
    inf = np.full(dx.shape, np.inf)
    t_lin = _cylinder_exit(dy, dz, TRACK_Y, TUNNEL_CZ, TUNNEL_R)
    t = t_lin.copy()
    sid = np.full(dx.shape, LINING, dtype=np.int16)

    def put(tc, s):
        closer = tc < t
        t[closer] = tc[closer]
        sid[closer] = s

    put(np.where(dz < 0, BED_Z / dz, inf), BED)
    for yc in (-RAIL_Y, RAIL_Y):
        a, b = _slab_yz(dy, dz, TRACK_Y + yc - RAIL_W / 2, TRACK_Y + yc + RAIL_W / 2, BED_Z, RAIL_TOP)
        put(np.where((a < b) & (a > 0), a, inf), RAIL)
    a, b = _slab_yz(dy, dz, TRACK_Y + CABLE_Y[0], TRACK_Y + CABLE_Y[1], *CABLE_Z)
    put(np.where((a < b) & (a > 0), a, inf), CABLE)

    lining = np.flatnonzero(sid == LINING)
    rib_t_in = _cylinder_exit(dy[lining], dz[lining], TRACK_Y, TUNNEL_CZ, TUNNEL_R - RIB_DEPTH)
    st = _Static(t=t, sid=sid, rib_idx=lining, rib_t_in=rib_t_in, rib_t_out=t_lin[lining],
                 rib_dx=dx[lining])
    for spec, sid_p in ((SLEEPER, SLEEPER_ID), (LAMP, LAMP_ID)):
        a, b = _slab_yz(dy, dz, TRACK_Y + spec["y"][0], TRACK_Y + spec["y"][1], *spec["z"])
        sel = np.flatnonzero((a < b) & (a > 0) & (a < t))
        st.periodic.append(_Periodic(idx=sel, t_in=a[sel], t_out=b[sel], dx=dx[sel], length=spec["length"],
                                     period=spec["period"], phase=0.0, sid=sid_p))
    for name, (side, z0, z1, depth, _w) in NICHE_TYPES.items():
        st.niche_types[name] = _niche_type(g, t_lin, sid, side, z0, z1, depth)
    return st


# --- world layout ---------------------------------------------------------------------------------

@dataclass
class _Box:
    x0: float                 # world X (the odometer frame)
    x1: float
    y0: float                 # vehicle Y (track axis included)
    y1: float
    z0: float
    z1: float
    sid: int


@dataclass
class _Niche:
    kind: str
    x0: float
    x1: float


@dataclass
class _Layout:
    boxes: list
    niches: list
    passages: list            # world X centres


def _gaps_ok(x: float, gaps: list, margin: float) -> bool:
    return all(not (a - margin <= x <= b + margin) for a, b in gaps)


def _layout(rng: np.random.Generator, x_from: float, x_to: float, passage_at: float | None,
            quiet: tuple[float, float] | None = None) -> _Layout:
    """Tunnel furniture between world X ``x_from`` and ``x_to``: cross passages (with the recess
    opposite), refuge niches, the walkway and the contact rail (interrupted at passages), rail
    supports, cable brackets, signals and equipment beside the envelope (none within ``quiet``)."""
    passages: list[float] = []
    if passage_at is not None:
        passages.append(float(passage_at))
        x = passage_at + rng.uniform(170, 240)
        while x < x_to + 20:
            passages.append(float(x))
            x += rng.uniform(170, 240)
        x = passage_at - rng.uniform(170, 240)
        while x > x_from - 20:
            passages.append(float(x))
            x -= rng.uniform(170, 240)
    else:
        x = x_from + rng.uniform(70, 150)
        while x < x_to + 20:
            passages.append(float(x))
            x += rng.uniform(170, 240)
    passages.sort()
    passage_gaps = [(xc - 3.0, xc + 3.0) for xc in passages]
    niches = []
    for xc in passages:
        for kind in ("passage", "opposite"):
            w = NICHE_TYPES[kind][4]
            niches.append(_Niche(kind, xc - w / 2, xc + w / 2))
    side = 1
    x = x_from + rng.uniform(10, 40)
    while x < x_to:                       # refuge niches, alternating sides
        if _gaps_ok(x, passage_gaps, 6.0):
            kind = "refuge_l" if side > 0 else "refuge_r"
            niches.append(_Niche(kind, x, x + NICHE_TYPES[kind][4]))
            side = -side
        x += rng.uniform(40, 70)
    right_gaps = [(n.x0 - 0.2, n.x1 + 0.2) for n in niches if n.kind in ("opposite", "refuge_r")]
    near_gaps = passage_gaps + ([quiet] if quiet else [])

    boxes = []
    # walkway and contact rail: continuous between passages
    edges = [x_from - 30.0] + [v for xc in passages for v in (xc - 2.0, xc + 2.0)] + [x_to + 30.0]
    for a, b in zip(edges[0::2], edges[1::2]):
        if b > a:
            boxes.append(_Box(a, b, TRACK_Y + WALK_Y0, TRACK_Y + 3.2, BED_Z, WALK_Z1, WALKWAY))
            boxes.append(_Box(a, b, TRACK_Y + CRAIL_Y[0], TRACK_Y + CRAIL_Y[1], *CRAIL_Z, CRAIL))
    x = x_from + rng.uniform(0, 4)
    while x < x_to:                       # contact rail brackets
        if _gaps_ok(x, passage_gaps, -0.5):
            boxes.append(_Box(x, x + 0.12, TRACK_Y + CRAIL_Y[0] - 0.05, TRACK_Y + CRAIL_Y[1] + 0.02,
                              BED_Z, CRAIL_Z[0], SUPPORT))
        x += 4.0
    x = x_from + rng.uniform(0, 2.5)
    while x < x_to:                       # cable brackets on the right wall
        if _gaps_ok(x, right_gaps, 0.0):
            boxes.append(_Box(x, x + 0.06, TRACK_Y - 2.85, TRACK_Y - 2.40, -0.05, 0.30, BRACKET))
        x += 2.5
    x = x_from + rng.uniform(20, 90)
    while x < x_to:                       # signals on the right wall
        if _gaps_ok(x, right_gaps, 0.5):
            boxes.append(_Box(x, x + 0.35, TRACK_Y - 2.85, TRACK_Y - 2.30, -0.30, 0.55, SIGNAL))
        x += rng.uniform(90, 140)
    x = x_from + rng.uniform(15, 45)
    while x < x_to:                       # equipment cabinets on the bed, left of the envelope
        if _gaps_ok(x, near_gaps, 1.0):
            boxes.append(_Box(x, x + 0.45, TRACK_Y + 1.28, TRACK_Y + 1.60, BED_Z, BED_Z + 0.55, CABINET))
        x += rng.uniform(50, 90)
    x = x_from + rng.uniform(10, 30)
    while x < x_to:                       # marker posts, right, between the rail and the contact rail
        if _gaps_ok(x, right_gaps + near_gaps, 1.0):
            boxes.append(_Box(x, x + 0.10, TRACK_Y - 1.48, TRACK_Y - 1.38, BED_Z, RAIL_TOP + 0.95, MARKER))
        x += rng.uniform(40, 80)
    return _Layout(boxes=boxes, niches=niches, passages=passages)


# --- ray casting ----------------------------------------------------------------------------------

def _box_hits(g: _Grid, t: np.ndarray, sid: np.ndarray, x0, x1, y0, y1, z0, z1, s_id: int) -> int:
    """Nearest-hit update of the (rings, columns) arrays with an axis-aligned box in the vehicle
    frame, testing only the rays inside its angular bounds. Returns the number of rays it wins."""
    if x1 <= 0.5:
        return 0
    x0 = max(x0, 0.5)
    az = [math.degrees(math.atan2(y, x)) for y in (y0, y1) for x in (x0, x1)]
    c0 = int(np.searchsorted(g.az, min(az) - 1e-9, side="left"))
    c1 = int(np.searchsorted(g.az, max(az) + 1e-9, side="right"))
    if c1 <= c0:
        return 0
    r_min = math.hypot(x0, 0.0 if y0 <= 0.0 <= y1 else min(abs(y0), abs(y1)))
    r_max = math.hypot(x1, max(abs(y0), abs(y1)))
    e_hi = math.degrees(math.atan2(z1, r_min if z1 > 0 else r_max))
    e_lo = math.degrees(math.atan2(z0, r_max if z0 > 0 else r_min))
    rows = np.flatnonzero((g.el >= e_lo - 1e-9) & (g.el <= e_hi + 1e-9))
    if rows.size == 0:
        return 0
    r0, r1 = int(rows[0]), int(rows[-1]) + 1
    sub = (slice(r0, r1), slice(c0, c1))
    dx, dy, dz = g.dx[sub], g.dy[sub], g.dz[sub]
    tx0, tx1 = x0 / dx, x1 / dx
    ty0, ty1 = y0 / dy, y1 / dy
    tz0, tz1 = z0 / dz, z1 / dz
    t_in = np.maximum(np.maximum(tx0, np.minimum(ty0, ty1)), np.minimum(tz0, tz1))
    t_out = np.minimum(np.minimum(tx1, np.maximum(ty0, ty1)), np.maximum(tz0, tz1))
    tv = t[sub]
    win = (t_in < t_out) & (t_in > 0) & (t_in < tv)
    if not win.any():
        return 0
    tv[win] = t_in[win]
    sid[sub][win] = s_id
    return int(win.sum())


def _cast(layout: _Layout, s: float, extra: list) -> tuple[np.ndarray, np.ndarray]:
    """Nearest hit distance and surface id of every ray (flat, ring-major) with the train at
    odometer ``s``; ``extra`` are vehicle-frame boxes (the person)."""
    g, st = _grid(), _static()
    t = st.t.copy()
    sid = st.sid.copy()

    # lining flanges: a rib is hit on its inner face, or on its front face inside the flange depth
    x_in = s + st.rib_t_in * st.rib_dx
    x_out = s + st.rib_t_out * st.rib_dx
    u = np.mod(x_in, RIB_PERIOD)
    on_rib = u < RIB_WIDTH
    x_next = x_in + (RIB_PERIOD - u)
    front = ~on_rib & (x_next <= x_out)
    t_rib = np.where(on_rib, st.rib_t_in, np.where(front, (x_next - s) / st.rib_dx, np.inf))
    hit = t_rib < t[st.rib_idx]
    t[st.rib_idx[hit]] = t_rib[hit]
    sid[st.rib_idx[hit]] = RIB

    # recesses in the lining: the ray goes on to the back wall, the far side face, floor or top
    for n in layout.niches:
        a, b = n.x0 - s, n.x1 - s
        if b < 1.0 or a > MAX_RANGE_M + 5:
            continue
        nt = st.niche_types[n.kind]
        xw = nt.t_wall * nt.dx
        m = (xw >= a) & (xw <= b)
        if not m.any():
            continue
        dxm, dzm = nt.dx[m], nt.dz[m]
        with np.errstate(divide="ignore"):
            t_far = b / dxm
            t_z = np.where(dzm > 0, nt.z1 / dzm, nt.z0 / dzm)
        t_new = np.minimum(np.minimum(nt.t_back[m], t_far), t_z)
        t_new = np.maximum(t_new, nt.t_wall[m])
        idx = nt.idx[m]
        take = np.isin(sid[idx], (LINING, RIB))
        t[idx[take]] = t_new[take]
        sid[idx[take]] = NICHE

    # periodic furniture with a fixed section: sleepers, wall lamps
    for p in st.periodic:
        xa = s + p.t_in * p.dx
        xb = s + p.t_out * p.dx
        u = np.mod(xa - p.phase, p.period)
        inside = u <= p.length
        x_next = xa + (p.period - u)
        tp = np.where(inside, p.t_in, np.where(x_next <= xb, (x_next - s) / p.dx, np.inf))
        cur = t[p.idx]
        win = tp < cur
        t[p.idx[win]] = tp[win]
        sid[p.idx[win]] = p.sid

    t2, s2 = t.reshape(g.dx.shape), sid.reshape(g.dx.shape)
    for bx in layout.boxes:
        if bx.x1 - s < 1.0 or bx.x0 - s > MAX_RANGE_M + 5:
            continue
        _box_hits(g, t2, s2, bx.x0 - s, bx.x1 - s, bx.y0, bx.y1, bx.z0, bx.z1, bx.sid)
    for bx in extra:
        _box_hits(g, t2, s2, bx.x0, bx.x1, bx.y0, bx.y1, bx.z0, bx.z1, bx.sid)
    return t, sid


def _person_boxes(x: float, lateral: float) -> list:
    """A standing person (vehicle frame): body and head boxes, the front face at ``x``."""
    L, W, H = PERSON_SIZE
    y = TRACK_Y + lateral
    body_h = H - 0.23
    return [_Box(x, x + L, y - W / 2, y + W / 2, BED_Z, BED_Z + body_h, PERSON),
            _Box(x + 0.08, x + L - 0.08, y - 0.11, y + 0.11, BED_Z + body_h, BED_Z + H, PERSON)]


# --- scenarios ------------------------------------------------------------------------------------

@dataclass
class _Timeline:
    s: np.ndarray                    # odometer per frame (m)
    person_x: np.ndarray | None      # world X of the person's front face per frame
    person_lat: np.ndarray | None    # lateral offset from the track axis per frame
    speed: np.ndarray                # m/s per frame
    passage_at: float | None
    quiet: tuple[float, float] | None = None     # world X kept free of equipment beside the envelope


def _approach(n: int, rng) -> _Timeline:
    T = n / RATE_HZ
    v0, dec = 12.0, 1.6
    hold = float(np.clip(0.1 * T, 0.8, 4.0))
    t_stop = max(T - hold, 0.5)
    v = v0 if t_stop >= v0 / dec else dec * t_stop * 0.6
    t_brake = t_stop - v / dec
    tt = np.arange(n) / RATE_HZ
    tb = np.clip(tt - t_brake, 0.0, v / dec)
    s = v * np.minimum(tt, t_brake) + v * tb - 0.5 * dec * tb ** 2
    speed = np.where(tt < t_brake, v, np.maximum(v - dec * (tt - t_brake), 0.0))
    s_end = v * t_brake + v * v / (2 * dec)
    gap = 25.0 + float(rng.uniform(-1.0, 1.0))
    px = np.full(n, s_end + gap)
    plat = np.full(n, float(rng.uniform(-0.15, 0.15)))
    return _Timeline(s=s, person_x=px, person_lat=plat, speed=speed, passage_at=None)


def _crossing(n: int, rng) -> _Timeline:
    T = n / RATE_HZ
    walk_v = 1.1
    y_a, y_b = 2.55, -2.25                    # in the cross passage (left) / the recess (right)
    t_walk = abs(y_a - y_b) / walk_v
    n_cross = int(np.clip(T // 7.0, 1, 4))
    stand = max((T - n_cross * t_walk) / (n_cross + 1), 0.3)
    if stand * (n_cross + 1) + n_cross * t_walk > T:      # short recording: walk faster
        t_walk = max((T - 0.6 * (n_cross + 1)) / n_cross, 0.8)
        stand = max((T - n_cross * t_walk) / (n_cross + 1), 0.0)
    tt = np.arange(n) / RATE_HZ
    lat = np.empty(n)
    for i, ti in enumerate(tt):
        k, rem = divmod(ti, stand + t_walk)
        k = int(k)
        start, end = (y_a, y_b) if k % 2 == 0 else (y_b, y_a)
        if k >= n_cross:
            lat[i] = y_a if n_cross % 2 == 0 else y_b
        elif rem < stand:
            lat[i] = start
        else:
            lat[i] = start + (end - start) * min((rem - stand) / t_walk, 1.0)
    x = 55.0 + float(rng.uniform(-1.0, 1.0))
    return _Timeline(s=np.zeros(n), person_x=np.full(n, x), person_lat=lat, speed=np.zeros(n),
                     passage_at=x + PERSON_SIZE[0] / 2, quiet=(-10.0, MAX_RANGE_M + 20.0))


def _clear(n: int, rng) -> _Timeline:
    v = 11.0
    tt = np.arange(n) / RATE_HZ
    return _Timeline(s=v * tt, person_x=None, person_lat=None, speed=np.full(n, v), passage_at=None)


# --- frames ---------------------------------------------------------------------------------------

def _frame_points(t: np.ndarray, sid: np.ndarray, s: float, rng) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Noisy returns of one frame over all ray slots (ring-major): vehicle xyz (n, 3) float32 and
    intensity, zero where the valid mask is False (no return, out of range, dropped)."""
    g = _grid()
    n = t.size
    ok = np.isfinite(t) & (t >= MIN_RANGE_M) & (t <= MAX_RANGE_M)
    # weak returns: the bed at grazing incidence fades beyond ~90 m, everything thins out far away
    bed = np.isin(sid, _BED_LIKE)
    p_drop = np.where(bed, np.clip((t - 85.0) / 45.0, 0.0, 0.97), np.clip((t - 150.0) / 120.0, 0.0, 0.5))
    p_drop = np.where(ok, p_drop + 0.01, 1.0)
    ok &= rng.random(n) >= p_drop
    tn = t + rng.normal(0.0, 1.0, n) * (0.01 + 1e-4 * np.where(ok, t, 0.0))
    xyz = np.zeros((n, 3), dtype=np.float32)
    tv = tn[ok]
    xyz[ok, 0] = g.dx.ravel()[ok] * tv
    xyz[ok, 1] = g.dy.ravel()[ok] * tv
    xyz[ok, 2] = g.dz.ravel()[ok] * tv
    inten = INTENSITY[np.where(ok, sid, 0)].copy()
    # darker ring joints on the lining, a painted band on every 10th ring
    lin = ok & (sid == LINING)
    if lin.any():
        xw = s + tv[lin[ok]] * g.dx.ravel()[lin]
        u = np.mod(xw, RIB_PERIOD)
        joint = (u > RIB_PERIOD - 0.08) | (u < RIB_WIDTH + 0.02)
        band = np.mod(np.floor(xw / RIB_PERIOD), 10) == 0
        li = inten[lin]
        li[joint] *= 0.6
        li[band] *= 1.5
        inten[lin] = li
    inten = np.clip(inten * rng.normal(1.0, 0.12, n).astype(np.float32) + rng.normal(0.0, 1.0, n).astype(np.float32),
                    1.0, 255.0)
    inten[~ok] = 0.0
    return xyz, inten, ok


def _slots(xyz_v: np.ndarray, inten: np.ndarray, ok: np.ndarray, frame_i: int) -> np.ndarray:
    """One PointCloud2 slot per ray, column (azimuth) major like the sensor's firing order, in the
    sensor frame; ``(0, 0, 0)`` where there is no return."""
    g = _grid()
    n_ring, n_col = g.dx.shape
    R = axis_matrix(SensorConfig())            # p_vehicle = R @ p_sensor  =>  p_sensor = p_vehicle @ R
    xyz_s = (xyz_v.astype(np.float64) @ R).astype(np.float32)
    xyz_s[~ok] = 0.0
    order = np.arange(n_ring * n_col).reshape(n_ring, n_col).T.ravel()
    pts = np.zeros(order.size, dtype=POINT_DTYPE)
    pts["x"], pts["y"], pts["z"] = xyz_s[order, 0], xyz_s[order, 1], xyz_s[order, 2]
    pts["intensity"] = inten[order]
    ring = np.repeat(np.arange(n_ring, dtype=np.uint16)[:, None], n_col, axis=1).ravel()
    pts["ring"] = ring[order]
    col = np.repeat(np.arange(n_col)[None, :], n_ring, axis=0).ravel()
    pts["timestamp"] = SENSOR_T0 + frame_i / RATE_HZ + (col[order] / n_col) * SWEEP_S
    return pts


# --- CDR / rosbag2 --------------------------------------------------------------------------------

def pointcloud2_cdr(pts: np.ndarray, stamp_ns: int, frame_id: str = FRAME_ID) -> bytes:
    """``sensor_msgs/msg/PointCloud2`` serialised as little-endian CDR (what rosbag2 stores)."""
    buf = bytearray(b"\x00\x01\x00\x00")

    def align(k: int) -> None:
        buf.extend(b"\x00" * ((-(len(buf) - 4)) % k))

    def string(s: str) -> None:
        raw = s.encode("utf-8") + b"\x00"
        align(4)
        buf.extend(struct.pack("<I", len(raw)))
        buf.extend(raw)

    align(4)
    buf.extend(struct.pack("<iI", int(stamp_ns // 1_000_000_000), int(stamp_ns % 1_000_000_000)))
    string(frame_id)
    align(4)
    buf.extend(struct.pack("<II", 1, int(pts.size)))
    buf.extend(struct.pack("<I", len(POINT_FIELDS)))
    for name, off, dt in POINT_FIELDS:
        string(name)
        align(4)
        buf.extend(struct.pack("<I", off))
        buf.extend(struct.pack("<B", dt))
        align(4)
        buf.extend(struct.pack("<I", 1))
    buf.extend(b"\x00")                        # is_bigendian
    align(4)
    buf.extend(struct.pack("<II", POINT_DTYPE.itemsize, POINT_DTYPE.itemsize * pts.size))
    data = pts.tobytes()
    buf.extend(struct.pack("<I", len(data)))
    buf.extend(data)
    buf.extend(b"\x00")                        # is_dense
    return bytes(buf)


def _open_db(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(str(db_path))
    con.executescript(
        "CREATE TABLE schema(schema_version INTEGER PRIMARY KEY,ros_distro TEXT NOT NULL);"
        "CREATE TABLE metadata(id INTEGER PRIMARY KEY,metadata_version INTEGER NOT NULL,metadata TEXT NOT NULL);"
        "CREATE TABLE topics(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,"
        "serialization_format TEXT NOT NULL,offered_qos_profiles TEXT NOT NULL);"
        "CREATE TABLE messages(id INTEGER PRIMARY KEY,topic_id INTEGER NOT NULL,timestamp INTEGER NOT NULL,"
        " data BLOB NOT NULL);"
        "CREATE INDEX timestamp_idx ON messages (timestamp ASC);")
    con.execute("INSERT INTO schema VALUES (3, 'humble')")
    con.execute("INSERT INTO topics VALUES (1, ?, ?, 'cdr', ?)", (TOPIC, MSGTYPE, QOS))
    return con


def _metadata(db_name: str, count: int, t0_ns: int, duration_ns: int) -> dict:
    return {"rosbag2_bagfile_information": {
        "version": 5, "storage_identifier": "sqlite3",
        "duration": {"nanoseconds": int(duration_ns)},
        "starting_time": {"nanoseconds_since_epoch": int(t0_ns)},
        "message_count": count,
        "topics_with_message_count": [{
            "topic_metadata": {"name": TOPIC, "type": MSGTYPE, "serialization_format": "cdr",
                               "offered_qos_profiles": QOS},
            "message_count": count}],
        "compression_format": "", "compression_mode": "",
        "relative_file_paths": [db_name],
        "files": [{"path": db_name, "starting_time": {"nanoseconds_since_epoch": int(t0_ns)},
                   "duration": {"nanoseconds": int(duration_ns)}, "message_count": count}],
    }}


def _check_args(scenario, seconds, seed) -> tuple[str, float, int]:
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        raise ValueError(f"Неизвестный сценарий «{scenario}»: допустимы approach, crossing, clear")
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds):
        raise ValueError("Длительность демо-записи должна быть числом секунд")
    lo, hi = SECONDS_RANGE
    if not lo <= float(seconds) <= hi:
        raise ValueError(f"Длительность демо-записи должна быть от {lo:g} до {hi:g} с")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or not 0 <= int(seed) < 2 ** 32:
        raise ValueError("Зерно генератора должно быть целым числом от 0 до 4294967295")
    return scenario, float(seconds), int(seed)


def generate_demo_bag(out_dir: Path, scenario: str = "approach", seconds: float = 15.0, seed: int = 0,
                      progress: Callable[[float], None] | None = None) -> dict:
    """Write a synthetic tunnel recording as a rosbag2 bag (``metadata.yaml`` +
    ``<name>_0.db3``) into ``out_dir`` (created; its basename is the bag name) and return
    ``{"name", "n_frames", "duration_s", "topic", "frame_id", "scenario"}``. ``progress`` gets
    0..1. Raises ValueError (Russian message) on a bad scenario, duration or seed."""
    scenario, seconds, seed = _check_args(scenario, seconds, seed)
    out_dir = Path(out_dir)
    name = out_dir.resolve().name
    if not name:
        raise ValueError("Некорректный каталог для демо-записи")
    out_dir.mkdir(parents=True, exist_ok=True)
    n = max(1, int(round(seconds * RATE_HZ)))
    rng = np.random.default_rng(seed)
    tl = {"approach": _approach, "crossing": _crossing, "clear": _clear}[scenario](n, rng)
    layout = _layout(rng, float(tl.s.min()) - 10.0, float(tl.s.max()) + MAX_RANGE_M + 10.0, tl.passage_at,
                     tl.quiet)
    if progress:
        progress(0.0)

    meta_path = out_dir / "metadata.yaml"
    if meta_path.exists():
        meta_path.unlink()                    # a half-written bag must not look complete
    db_name = f"{name}_0.db3"
    period_ns = int(round(1e9 / RATE_HZ))
    con = _open_db(out_dir / db_name)
    gt: dict = {}
    try:
        for i in range(n):
            s = float(tl.s[i])
            extra = []
            if tl.person_x is not None:
                extra = _person_boxes(float(tl.person_x[i]) - s, float(tl.person_lat[i]))
            t, sid = _cast(layout, s, extra)
            xyz, inten, ok = _frame_points(t, sid, s, rng)
            pts = _slots(xyz, inten, ok, i)
            stamp_ns = BAG_T0_NS + i * period_ns
            con.execute("INSERT INTO messages VALUES (?, 1, ?, ?)",
                        (i + 1, stamp_ns, sqlite3.Binary(pointcloud2_cdr(pts, stamp_ns))))
            rows = []
            if tl.person_x is not None:
                lat = float(tl.person_lat[i])
                L, W, H = PERSON_SIZE
                rows.append({"kind": "person", "name": "person", "label": "person",
                             "size": [L, W, H], "distance": _r(tl.person_x[i] - s), "lateral": _r(lat),
                             "yaw_deg": 0.0, "reflectivity": float(INTENSITY[PERSON]),
                             "in_gauge": bool(abs(lat) - W / 2 <= 1.05),
                             "n_points": int(np.count_nonzero(ok & (sid == PERSON)))})
            gt[f"{i:05d}"] = rows
            if progress and (i % 5 == 4 or i == n - 1):
                progress(0.98 * (i + 1) / n)
        con.commit()
    finally:
        con.close()
    duration_ns = (n - 1) * period_ns
    gt["_meta"] = {"bag": name, "topic": TOPIC, "frame_id": FRAME_ID, "coords": "vehicle", "every": 1,
                   "frames": n, "source": f"resense_web.demo, scenario {scenario}, seed {seed}",
                   "gauge_half_width_m": 1.05,
                   "speed_mps": [_r(v) for v in tl.speed],
                   "note": "synthetic ground truth: the person's nearest face (distance, m) and centre "
                           "(lateral, m from the track axis, + left); in_gauge = inside the 1.05 m half-width"}
    with open(out_dir / GROUND_TRUTH, "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(gt.items(), key=lambda kv: (not kv[0].startswith("_"), kv[0]))), fh,
                  ensure_ascii=False)
    tmp = out_dir / "metadata.yaml.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        yaml.safe_dump(_metadata(db_name, n, BAG_T0_NS, duration_ns), fh, sort_keys=False,
                       default_flow_style=False)
    os.replace(tmp, meta_path)
    if progress:
        progress(1.0)
    return {"name": name, "n_frames": n, "duration_s": round(duration_ns / 1e9, 3), "topic": TOPIC,
            "frame_id": FRAME_ID, "scenario": scenario}
