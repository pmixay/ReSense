#!/usr/bin/env python3
"""X2: the false-STOP ledger, pass-by ground truth and a fast window replay.

    python scripts/false_stop_ledger.py --runs out/gate --windows /data/cache --out docs/evidence/false_stops_<date>

``--runs`` is the per-frame JSONL directory of a gate or ``eval_real`` run (``<bag>.jsonl`` and
``new_data_<k>.jsonl``, with its ``config.yaml``); ``--windows`` is the frame cache. The obstacle-free
recordings (the five empty bags and the ride) hold no obstacle, so every STOP episode (a GO -> STOP
transition) is a false alarm. The script

1. builds one ledger row per episode from the run outputs: onset frame, distance, lateral, size, kind,
   reason, curvature, rail_lock, ego, mount, health, the track model of the onset frame;
2. replays every episode as a *window* (``--pre-roll`` frames before the onset, calibration off, a fresh
   detector, stopped three frames after the onset) and checks that the onset frame (+-2) and the distance
   (+-2 m) come back; the speed is compared with the full replay;
3. gives every episode a *pass-by class*: the ego path is integrated (speed from the run, heading and
   pitch change from the track model of every frame) until the train is 10-25 m from the onset's world
   position; the detector is replayed over that stretch (fresh detector, calibration off), its re-fitted
   track gives the lateral ``dy`` and height ``h`` of the points around that position, and they are
   classified: nothing there = ``phantom``; only bed and rail points (``h`` < 0.15 m) = ``bed_rail``;
   structure above the bed with median ``h`` > 3.0 m = ``overhead``, with median ``|dy|`` > 1.4 m =
   ``side``, otherwise ``in_envelope``;
4. renders one PNG per episode (BEV and side view of the onset, and of the pass-by evidence).

Sub-commands: ``ledger`` (default: all of it), ``controls`` (positive controls of the classifier and of
the ego transport, ``--controls``), ``summary`` (the F2 table from an existing ledger.json).
The thresholds are the card's (BACKLOG X2); everything else is a named constant below.
"""
from __future__ import annotations

import os

if __name__ == "__main__":        # one BLAS / OpenMP thread per worker: set before numpy loads
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from dataclasses import asdict, dataclass  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCHEMA = "resense-false-stop-ledger-v1"
EMPTY_BAGS = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
              "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]
RIDE = "new_data"
RIDE_CHUNKS = 8                 # the gate's pieces of the ride (fresh detector at each piece start)

# the card's thresholds
SIDE_DY = 1.4                   # m: |dy| above it = side structure
OVERHEAD_H = 3.0                # m: h above it = overhead
BED_H = 0.15                    # m: h below it = bed or rail fitting
BAND = (10.0, 25.0)             # m: the train is this far from the onset's world position
FAR_ONSET = 100.0               # m: F2's far-onset limit
PRE_ROLL = 150                  # frames of pre-roll of the reproduction window
ONSET_TOL_FRAMES = 2
DIST_TOL_M = 2.0
CLASSES = ("in_envelope", "side", "overhead", "bed_rail", "phantom")


@dataclass
class ClassifierParams:
    lon0: float = 2.0               # m: half length (along the track) of the window around the transported position ...
    lon_per_m: float = 0.05         # ... plus this per metre travelled (the speed integral is off by up to 5 % on set O) ...
    lon_max: float = 7.0            # ... at most this
    lat0: float = 1.2               # m: half width of the window ...
    lat_per_m: float = 0.012        # ... plus this per metre travelled (heading drift) ...
    lat_max: float = 2.5            # ... at most this
    position_margin: float = 1.0    # m: a carried position this far beyond SIDE_DY is outside the gauge even when nothing is seen there
    fabric_lat: float = 1.0         # m: half width / height of the tight window for tunnel fabric (no structure found)
    z_half_min: float = 0.4         # m: half height of the window (at least; or half the onset size) ...
    z_pad: float = 0.6              # ... plus this ...
    z_per_m: float = 0.03           # ... plus this per metre travelled (the path's gradient is not integrated, see ``transport``)
    z_narrow_per_m: float = 0.01    # the narrow window that decides bed or rail against phantom
    min_any: int = 3                # fewer returns in the window than this = nothing there
    min_struct: int = 5             # fewer structure points than this = no structure of that kind
    few_up: int = 12                # ambiguous below this many structure points
    share_min: float = 0.7          # ambiguous when the winning share of the structure points is lower
    margin_dy: float = 0.2          # m: ambiguous when the median |dy| is this close to SIDE_DY
    margin_h: float = 0.3           # m: ... or the median h to OVERHEAD_H
    frame_agree: float = 0.7        # episode class: the share of the evaluated frames that agree
    fabric_near: float = 6.0        # m: the tunnel fabric is read from the slices this far (or farther) from the window ...
    fabric_far: float = 40.0        # ... up to this far, on each side
    fabric_x_min: float = 3.0       # m: the first station of the sensor's view
    outline_lat: float = 9.0        # m: lateral reach of the returns the tunnel surface is read from
    outline_cell: float = 0.5       # m: height slab of the wall / lateral column of the vault
    outline_min: int = 15           # returns a slab or column needs to count as a surface
    outline_pct: float = 85.0       # the surface is this percentile of |dy| (wall) or h (vault)
    outline_margin: float = 0.5     # m: a return this far in front of / below the surface is structure
    fabric_cell: float = 0.3        # m: cell of the (dy, h) cross-section
    fabric_slice: float = 2.0       # m: length of a slice along the track
    fabric_occ: float = 0.5         # a cell occupied in at least this share of the slices on both sides is tunnel fabric


# ---------------------------------------------------------------------------------------------
# run outputs -> pieces and rows
# ---------------------------------------------------------------------------------------------

def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def piece_table(runs, cache, bags):
    """[{bag, piece, path, files, start}]: the run files in processing order with the cache files of each
    piece (``np.array_split`` of the sorted cache, as the gate), ``start`` the index of its first frame."""
    from scripts.cache_io import cache_files
    pieces = []
    for bag in bags:
        if bag == RIDE:
            paths = sorted(glob.glob(os.path.join(runs, f"{RIDE}_*.jsonl")),
                           key=lambda p: int(os.path.basename(p)[len(RIDE) + 1:-6]))
        else:
            paths = [p for p in [os.path.join(runs, f"{bag}.jsonl")] if os.path.exists(p)]
        if not paths:
            continue
        files = cache_files(os.path.join(cache, bag))
        parts = np.array_split(np.array(files, dtype=object), len(paths)) if len(paths) > 1 else [np.array(files, dtype=object)]
        start = 0
        for k, (p, part) in enumerate(zip(paths, parts)):
            pieces.append({"bag": bag, "piece": k, "path": p, "files": list(part), "start": start})
            start += len(part)
    return pieces


def check_piece(piece, rows):
    """The run file must be the piece: same frame count and the same cache file in every row."""
    from scripts.cache_io import cache_file_stem
    if len(rows) != len(piece["files"]):
        raise SystemExit(f"{piece['path']}: {len(rows)} rows but {len(piece['files'])} cached frames")
    bad = sum(1 for r, f in zip(rows, piece["files"]) if r.get("frame_id") != cache_file_stem(f))
    if bad:
        raise SystemExit(f"{piece['path']}: {bad} rows do not match their cache file")


def global_frame(piece, i, row):
    """The frame number the ledger uses: the recording's own frame number (six bags) or the index in the
    whole ride."""
    return int(piece["start"] + i) if piece["bag"] == RIDE else int(row["frame"])


def stop_runs(rows):
    """[(first, last)] index ranges of consecutive STOP frames (obstacle flag): one per GO -> STOP transition,
    counted as ``regression_gate.stop_stats`` does (a run that starts at the piece's first frame counts)."""
    out, start = [], None
    for i, d in enumerate(rows):
        if d["obstacle"] and start is None:
            start = i
        if not d["obstacle"] and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(rows) - 1))
    return out


def nearest_detection(d):
    dets = d.get("detections") or []
    return min(dets, key=lambda x: x["distance"]) if dets else None


def episode_row(piece, rows, first, last):
    d = rows[first]
    det = nearest_detection(d)
    tr, hl, mt = d.get("track") or {}, d.get("health") or {}, d.get("mount") or {}
    span = rows[first:last + 1]
    dists = [x["distance"] for r in span for x in r.get("detections", [])]
    kinds = sorted({x.get("kind") for r in span for x in r.get("detections", [])})
    gf = global_frame(piece, first, d)
    return {
        "id": f"{piece['bag']}:{gf}",
        "recording": piece["bag"], "piece": piece["piece"], "piece_frame": first, "frame": gf,
        "frame_id": d.get("frame_id"), "stamp": d.get("stamp"),
        "distance": det["distance"], "lateral": det["lateral"], "size": det["size"], "center": det["center"],
        "kind": det.get("kind"), "reason": det.get("reason"), "zone": det.get("zone"),
        "n_points": det.get("n_points"), "height_min": det.get("height_min"), "confidence": det.get("confidence"),
        "age": det.get("age"), "track_id": det.get("id"), "n_detections": len(d.get("detections", [])),
        "far_onset": bool(det["distance"] >= FAR_ONSET),
        "episode": {"stop_frames": last - first + 1, "last_frame": gf + (last - first),
                    "min_distance": min(dists), "max_distance": max(dists), "kinds": kinds},
        "curvature": tr.get("curvature"),
        "track": {k: tr.get(k) for k in ("center", "yaw", "curvature", "rail_offset", "rail_score", "wall_quality",
                                         "axis_valid", "axis_sides", "rail_slabs", "n_bins", "residual",
                                         "floor_verified", "age", "curv_step", "curv_knot", "joint_used", "floor_coef",
                                         "floor_range")
                  if k in tr},
        "rail_lock": hl.get("rail_lock"),
        "health": {k: hl.get(k) for k in ("level", "monitored_range", "visibility", "rail_lock", "messages")
                   if k in hl},
        "ego": {"speed": d.get("ego_speed"), "source": d.get("ego_speed_source"),
                "estimate": d.get("ego_speed_estimate"), "confidence": d.get("ego_speed_confidence"),
                "n_accumulated": d.get("n_accumulated")},
        "mount": {k: mt.get(k) for k in ("status", "orientation", "roll_deg", "pitch_deg", "yaw_deg",
                                         "frames_used")},
    }


def build_rows(pieces, all_rows):
    eps = []
    for piece, rows in zip(pieces, all_rows):
        for first, last in stop_runs(rows):
            eps.append(episode_row(piece, rows, first, last))
    return eps


# ---------------------------------------------------------------------------------------------
# ego transport (pass-by)
# ---------------------------------------------------------------------------------------------

def track_from_dict(t):
    from resense.track import TrackModel
    return TrackModel(floor_coef=np.array(t["floor_coef"], dtype=float), floor_range=tuple(t["floor_range"]),
                      center=float(t["center"]), yaw=float(t["yaw"]), curvature=float(t["curvature"]),
                      rail_offset=float(t.get("rail_offset", 0.35)), curv_step=float(t.get("curv_step", 0.0)),
                      curv_knot=float(t.get("curv_knot", 0.0)))


def floor_slope(t, x):
    """d z_floor / dx of a track dict at x (the model extrapolates linearly outside its range)."""
    m = track_from_dict(t)
    return float((m.floor_z(np.array([x + 0.5]))[0] - m.floor_z(np.array([x - 0.5]))[0]))


def step_geometry(t, near=10.0):
    """(psi, phi, dpsi_per_m, dphi_per_m): the direction of the path in the vehicle frame (yaw and pitch of
    the track at the vehicle) and how fast it turns: the curvature of the axis and of the bed."""
    psi = float(t["yaw"])
    phi = math.atan(floor_slope(t, near))
    dphi = (floor_slope(t, near + 10.0) - floor_slope(t, near - 5.0)) / 15.0
    return psi, phi, float(t["curvature"]), dphi


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def advance(p, s, psi, phi, dpsi, dphi):
    """The point ``p`` (vehicle frame of frame k) in the vehicle frame of frame k+1 after the train moved ``s`` m
    along its path: translation by ``s`` along the path direction, then the rotation of the vehicle by the
    heading change ``dpsi * s`` (left +) and the pitch change ``dphi * s`` (nose up +)."""
    u = np.array([math.cos(phi) * math.cos(psi), math.cos(phi) * math.sin(psi), math.sin(phi)])
    R = rot_z(dpsi * s) @ rot_y(-dphi * s)
    return R.T @ (np.asarray(p, dtype=float) - s * u)


def frame_dt(a, b, default=0.1):
    """The time between two stamps, clipped to a plausible range (bag receive times jitter)."""
    if a is None or b is None:
        return default
    dt = b - a
    return dt if 0.03 <= dt <= 0.3 else default


def intake_speeds(path=None):
    """{split file number: train speed m/s} of the ride from the organizer intake (``speed_tracks``: the drift of
    static tracks, a method independent of the estimator); {} when the file is absent."""
    path = path or os.path.join(ROOT, "docs", "extended_dataset_intake.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        files = json.load(fh).get("files", [])
    return {int(f["n"]): float(f["speed_tracks"]) for f in files
            if f.get("speed_tracks") is not None and (f.get("speed_tracks_n") or 0) >= 3}


def split_of(frame_id):
    """The ride split number of a frame id ``new_data_<n>_<k>``; None for other recordings."""
    m = re.match(r"new_data_(\d+)_\d+$", frame_id or "")
    return int(m.group(1)) if m else None


def speed_series(rows, split_speeds=None, max_gap=30):
    """Per-frame ego speed (m/s) of a piece and where each value comes from. The detector's own estimate
    (``ego_speed_estimate``; ``ego_speed`` when the caller gave one) exists on 55-75 % of the frames of the
    empty recordings. A gap of at most ``max_gap`` frames between two estimates is interpolated ('interp');
    a longer one takes the intake speed of the ride split when there is one ('intake'); otherwise it is
    interpolated or held ('interp', 'hold'); a piece without any value runs at 0 ('none')."""
    v = np.full(len(rows), np.nan)
    src = np.array(["none"] * len(rows), dtype=object)
    for i, d in enumerate(rows):
        if d.get("ego_speed") is not None:
            v[i], src[i] = float(d["ego_speed"]), "given"
        elif d.get("ego_speed_estimate") is not None:
            v[i], src[i] = float(d["ego_speed_estimate"]), "estimate"
    ok = ~np.isnan(v)
    out = v.copy()
    idx = np.flatnonzero(ok)
    if not idx.size and not split_speeds:
        return np.zeros(len(rows)), src
    if idx.size:
        filled = np.interp(np.arange(len(rows)), idx, v[idx])
        nxt = np.searchsorted(idx, np.arange(len(rows)))            # first valid index at or after i
        for i in np.flatnonzero(~ok):
            lo = idx[nxt[i] - 1] if nxt[i] > 0 else None
            hi = idx[nxt[i]] if nxt[i] < idx.size else None
            short = lo is not None and hi is not None and hi - lo <= max_gap
            sp = split_speeds.get(split_of(rows[i].get("frame_id"))) if split_speeds else None
            if short:
                out[i], src[i] = filled[i], "interp"
            elif sp is not None:
                out[i], src[i] = sp, "intake"
            else:
                out[i], src[i] = filled[i], "hold" if lo is None or hi is None else "interp"
    else:
        for i in range(len(rows)):
            sp = split_speeds.get(split_of(rows[i].get("frame_id")))
            out[i], src[i] = (sp, "intake") if sp is not None else (0.0, "none")
    return out, src


def transport(rows, i0, center, speeds=None, max_frames=4000, max_range=BAND[1] + 150.0, pitch=False):
    """Walk the ego forward from frame ``i0`` of ``rows`` and carry ``center`` (vehicle frame of frame i0) along.
    Returns a list per frame i >= i0: {i, p (position in that frame's vehicle frame), range (horizontal),
    traveled, src}; stops at the end of the piece, after ``max_frames`` or once the point is behind the
    train (x < -BAND[0]) or far away. The pitch (gradient) of the path is not integrated by default: on set O
    the transported height of the organizers' objects is off by a median 0.09 m without it and 0.75 m with it
    (the floor slope in the vehicle frame includes the mount tilt and its noise adds up); the vertical window
    of ``classify_window`` therefore grows with the distance instead."""
    speeds = speed_series(rows) if speeds is None else speeds
    v, vsrc = speeds
    p = np.asarray(center, dtype=float)
    out = [{"i": i0, "p": p.copy(), "range": float(math.hypot(p[0], p[1])), "traveled": 0.0, "src": "onset"}]
    traveled = 0.0
    last = min(len(rows) - 1, i0 + max_frames)
    for i in range(i0, last):
        d, dn = rows[i], rows[i + 1]
        s = float(v[i]) * frame_dt(d.get("stamp"), dn.get("stamp"))
        t = d.get("track") or {}
        if "floor_coef" in t and s > 0.0:
            psi, phi, dpsi, dphi = step_geometry(t)
            p = advance(p, s, psi, phi if pitch else 0.0, dpsi, dphi if pitch else 0.0)
        elif s > 0.0:
            p = p - np.array([s, 0.0, 0.0])
        traveled += s
        out.append({"i": i + 1, "p": p.copy(), "range": float(math.hypot(p[0], p[1])), "traveled": traveled,
                    "src": str(vsrc[i])})
        if p[0] < -BAND[0] or out[-1]["range"] > max_range:
            break
    return out


def band_frames(path, band=BAND, n_max=6, nearest_max=50.0, nearest_pad=2.5):
    """The frames of a transport path in the band, thinned to at most ``n_max`` (evenly). When the train never
    comes that close (it stops at a platform, the recording ends) the frames within ``nearest_pad`` m of the
    closest approach are used instead, if that is within ``nearest_max`` m. Returns (frames, closest range, mode)
    with mode 'band', 'nearest' or 'none'."""
    inb = [q for q in path[1:] if band[0] <= q["range"] <= band[1] and q["p"][0] > 0.0]
    closest = min((q["range"] for q in path), default=None)
    mode = "band"
    if not inb and closest is not None and closest <= nearest_max:
        inb = [q for q in path[1:] if q["range"] <= closest + nearest_pad and q["p"][0] > 0.0]
        mode = "nearest" if inb else "none"
    elif not inb:
        mode = "none"
    if len(inb) > n_max:
        idx = np.unique(np.linspace(0, len(inb) - 1, n_max).round().astype(int))
        inb = [inb[j] for j in idx]
    return inb, closest, mode


# ---------------------------------------------------------------------------------------------
# the pass-by classifier
# ---------------------------------------------------------------------------------------------

def fabric_occupancy(xyz, track, cx, params: ClassifierParams):
    """The tunnel fabric around station ``cx``: for every (dy, h) cell of the cross-section the share of the 1 m
    slices (``fabric_slice`` m long), behind and ahead of the window (``fabric_near`` .. ``fabric_far`` m away), that hold a return in it.
    Walls, ceiling, bed, rails and continuous trays fill the same cells along the whole tunnel; an object does
    not. Returns {(i, j): the larger of the shares behind and ahead (the sensor does not see the vault close to it, so a
    surface seen on one side only still counts; a side with under three slices is ignored)}."""
    from resense.gauge import corridor_coordinates
    x = xyz[:, 0]
    occ = []
    for sign in (-1.0, 1.0):
        lo, hi = sorted((cx + sign * params.fabric_near, cx + sign * params.fabric_far))
        lo = max(lo, params.fabric_x_min)             # nothing is seen behind the sensor's first metres
        n_slices = int((hi - lo) / params.fabric_slice)
        if n_slices < 3:
            continue                                  # a side with less than three slices tells nothing
        sel = (x >= lo) & (x < lo + n_slices * params.fabric_slice)
        if not sel.any():
            occ.append({})
            continue
        dy, h = corridor_coordinates(xyz[sel].astype(np.float32), track)
        ci = np.floor(dy / params.fabric_cell).astype(np.int64)
        cj = np.floor(h / params.fabric_cell).astype(np.int64)
        sl = np.floor((x[sel] - lo) / params.fabric_slice).astype(np.int64)
        cnt = {}
        for i, j, _ in set(zip(ci.tolist(), cj.tolist(), sl.tolist())):
            cnt[(i, j)] = cnt.get((i, j), 0) + 1
        occ.append({k: v / n_slices for k, v in cnt.items()})
    if not occ:
        return {}
    keys = set().union(*occ)
    return {k: max(o.get(k, 0.0) for o in occ) for k in keys}


def outline_structure(dy, h, dy_ref, h_ref, params: ClassifierParams):
    """Which of the candidate returns (``dy``, ``h``) stand out of the tunnel surface, measured from the reference
    returns around the position: a return outside the envelope is *structure* when it stands in front of the wall
    (``|dy|`` at least ``outline_margin`` less than the wall of its side and 0.5 m height slab) or below the vault
    (``h`` at least ``outline_margin`` less than the vault of its 0.5 m lateral column); a slab or column with few
    reference returns has no surface to stand out of, its returns count as structure. Returns (side, over) masks."""
    side = np.zeros(len(dy), dtype=bool)
    over = np.zeros(len(dy), dtype=bool)
    cs = params.outline_cell
    # walls: per side and height slab
    ref = (h_ref > BED_H) & (h_ref <= OVERHEAD_H) & (np.abs(dy_ref) > SIDE_DY)
    wall = {}
    key_r = np.floor(h_ref[ref] / cs).astype(np.int64) * 2 + (dy_ref[ref] > 0)
    adr = np.abs(dy_ref[ref])
    for k in np.unique(key_r):
        m = key_r == k
        if int(m.sum()) >= params.outline_min:
            wall[int(k)] = float(np.percentile(adr[m], params.outline_pct))
    cand = (h > BED_H) & (h <= OVERHEAD_H) & (np.abs(dy) > SIDE_DY)
    for i in np.flatnonzero(cand):
        k = int(np.floor(h[i] / cs)) * 2 + int(dy[i] > 0)
        side[i] = (k not in wall) or abs(dy[i]) <= wall[k] - params.outline_margin
    # vault: per lateral column
    ref = h_ref > OVERHEAD_H
    vault = {}
    key_r = np.floor(dy_ref[ref] / cs).astype(np.int64)
    hr = h_ref[ref]
    for k in np.unique(key_r):
        m = key_r == k
        if int(m.sum()) >= params.outline_min:
            vault[int(k)] = float(np.percentile(hr[m], params.outline_pct))
    top = {sg: max((w for kk, w in wall.items() if kk % 2 == sg), default=None) for sg in (0, 1)}
    for i in np.flatnonzero(h > OVERHEAD_H):
        k = int(np.floor(dy[i] / cs))
        wl = top[int(dy[i] > 0)]
        if wl is not None and abs(dy[i]) > wl - 0.3:
            continue                                              # the wall running up into the vault, not a body below it
        over[i] = (k not in vault) or h[i] <= vault[k] - params.outline_margin
    return side, over


def classify_window(xyz, track, center, size, traveled, params: ClassifierParams = ClassifierParams()):  # noqa: B008
    """Classify what stands around ``center`` (the onset's position carried into the vehicle frame of this frame)
    in the cloud ``xyz`` with the re-fitted ``track``:

    * ``in_envelope``: returns inside the strict envelope (|dy| <= SIDE_DY, BED_H < h <= OVERHEAD_H) that are not
      continuous tunnel fabric (a platform edge fills the same (dy, h) cells along the track, an object does not);
    * else ``side`` (|dy| > SIDE_DY) or ``overhead`` (h > OVERHEAD_H) *structure*: returns that stand out of the tunnel
      surface (``outline_structure``), the larger share wins;
    * else, with only the tunnel surface (wall, platform edge, vault) right at the position, the class of that surface
      by its (dy, h), flagged ``on_tunnel_fabric``;
    * else ``side`` when the carried position itself lies beyond the gauge (``by_position``: nothing is seen there,
      behind the wall), ``bed_rail`` when the window holds bed or rail returns (h <= BED_H, |dy| <= SIDE_DY), else
      ``phantom`` (nothing there).
    The window is a box around ``center`` that grows with the distance travelled (odometry drift)."""
    from resense.gauge import corridor_coordinates
    cx, cy, cz = (float(v) for v in center)
    lon = min(params.lon_max, params.lon0 + params.lon_per_m * traveled)
    lat = min(params.lat_max, params.lat0 + params.lat_per_m * traveled)
    zhalf = max(params.z_half_min, 0.5 * float(size[2])) + params.z_pad + params.z_per_m * traveled
    xyz = np.asarray(xyz)
    zn = max(params.z_half_min, 0.5 * float(size[2])) + params.z_pad + params.z_narrow_per_m * traveled
    along = np.abs(xyz[:, 0] - cx) <= lon
    box = along & (np.abs(xyz[:, 1] - cy) <= lat)
    sel = box & (np.abs(xyz[:, 2] - cz) <= zhalf)
    narrow = (np.abs(xyz[sel][:, 2] - cz) <= zn)
    dy_pos = cy - float(track.center_y(np.array([cx]))[0])        # the position's lateral from the re-fitted axis
    out = {"dy_position": round(dy_pos, 2), "lon": round(lon, 2), "lat": round(lat, 2), "z_half": round(zhalf, 2),
           "n_all": int(sel.sum()), "n_narrow": int(narrow.sum()), "n_up": 0, "n_bed": 0, "n_env": 0, "n_side": 0,
           "n_over": 0, "n_fabric": 0, "dy_med": None, "h_med": None, "h_range": None, "dy_range": None,
           "ambiguous": [], "class": None}
    amb = out["ambiguous"]

    def beyond_gauge():
        if abs(dy_pos) > SIDE_DY + params.position_margin:
            out.update({"class": "side", "by_position": True})
            amb.append(f"side_by_position(dy {dy_pos:+.1f} m, nothing observed)")
            return True
        return False

    if int(sel.sum()) < params.min_any:
        if not beyond_gauge():
            out["class"] = "phantom"
        return out
    dy, h = corridor_coordinates(xyz[sel].astype(np.float32), track)
    out["h_range"] = [round(float(h.min()), 2), round(float(h.max()), 2)]
    up = h > BED_H
    out["n_bed"] = int((~up & (np.abs(dy) <= SIDE_DY) & narrow).sum())  # the bed between the walls, not their foot
    out["n_up"] = int(up.sum())
    env_all = up & (h <= OVERHEAD_H) & (np.abs(dy) <= SIDE_DY)
    out["n_env_all"] = int(env_all.sum())
    # the surface of the tunnel around the position, from every return of the along-track stretch
    ref = along & (np.abs(xyz[:, 1] - cy) <= params.outline_lat)
    dy_r, h_r = corridor_coordinates(xyz[ref].astype(np.float32), track)
    side_s, over_s = outline_structure(dy, h, dy_r, h_r, params)
    fab = np.zeros(len(h), dtype=bool)                  # continuous along the track: the same (dy, h) cells in the slices around
    if up.any():
        occ = fabric_occupancy(xyz, track, cx, params)
        ci = np.floor(dy[up] / params.fabric_cell).astype(np.int64)
        cj = np.floor(h[up] / params.fabric_cell).astype(np.int64)
        fab[np.flatnonzero(up)] = np.array(
            [max(occ.get((i + di, j + dj), 0.0) for di in (-1, 0, 1) for dj in (-1, 0, 1)) >= params.fabric_occ
             for i, j in zip(ci.tolist(), cj.tolist())], dtype=bool)
    fab_env = fab & env_all
    side_s, over_s = side_s & ~fab, over_s & ~fab       # structure = stands out of the surface and is not continuous
    env = env_all & ~fab_env
    out["n_env"], out["n_side"], out["n_over"] = int(env.sum()), int(side_s.sum()), int(over_s.sum())
    surface = up & ~env & ~side_s & ~over_s                       # what is left above the bed: the tunnel's surface
    out["n_fabric"] = int(surface.sum())

    def describe(m):
        out.update({"dy_med": round(float(np.median(dy[m])), 2), "h_med": round(float(np.median(h[m])), 2),
                    "h_range": [round(float(h[m].min()), 2), round(float(h[m].max()), 2)],
                    "dy_range": [round(float(dy[m].min()), 2), round(float(dy[m].max()), 2)],
                    "h_bottom": round(float(h[m].min()), 2)})

    if out["n_env"] >= params.min_struct and out["n_over"] >= params.min_struct and \
            float(np.median(h[env])) >= OVERHEAD_H - 0.4:
        out["class"] = "overhead"                         # a body hanging from above the limit, its underside inside
        describe(over_s | env)
        amb.append("straddles_limit")
    elif out["n_env"] >= params.min_struct:
        out["class"] = "in_envelope"
        describe(env)
        other = out["n_side"] + out["n_over"]
        if other >= params.min_struct and other > 0.3 * out["n_env"]:
            amb.append(f"mixed(env {out['n_env']}, other {other})")
    elif max(out["n_side"], out["n_over"]) >= params.min_struct:
        cls = "side" if out["n_side"] >= out["n_over"] else "overhead"
        out["class"] = cls
        m = side_s if cls == "side" else over_s
        describe(m)
        n, other = int(m.sum()), int((over_s if cls == "side" else side_s).sum())
        if other >= params.min_struct and other > (1.0 - params.share_min) * (n + other):
            amb.append(f"mixed({cls} {n}, other {other})")
    else:
        # no structure: the tunnel surface (wall, platform edge, vault) right at the position?
        tight = (surface | (env_all & fab_env)) & narrow & (np.abs(dy - dy_pos) <= params.fabric_lat)
        if int(tight.sum()) >= params.min_struct:
            describe(tight)
            out["on_fabric"] = True
            out["class"] = ("overhead" if out["h_med"] > OVERHEAD_H else
                            "side" if abs(out["dy_med"]) > SIDE_DY else "in_envelope")
            amb.append("on_tunnel_fabric")
            out["n_fabric_tight"] = int(tight.sum())
            return out
        if not beyond_gauge():
            out["class"] = "bed_rail" if out["n_bed"] >= params.min_any else "phantom"
            if abs(dy_pos) > SIDE_DY:
                amb.append(f"position_beyond_limit(dy {dy_pos:+.1f} m)")
        return out
    if int(out["n_" + {"in_envelope": "env", "side": "side", "overhead": "over"}[out["class"]]]) < params.few_up:
        amb.append("few_points")
    if out["class"] in ("side", "in_envelope") and abs(abs(out["dy_med"]) - SIDE_DY) < params.margin_dy:
        amb.append("dy_near_limit")
    if abs(out["h_med"] - OVERHEAD_H) < params.margin_h:
        amb.append("h_near_limit")
    return out


def episode_class(frame_results, params: ClassifierParams = ClassifierParams()):
    """Combine the per-frame classes of the evaluated frames: the most frequent class, ambiguous when fewer than
    ``frame_agree`` of the frames agree or most frames are ambiguous."""
    if not frame_results:
        return None, 0.0, ["no_frames"]
    classes = [r["class"] for r in frame_results]
    cls = max(set(classes), key=lambda c: (classes.count(c), -CLASSES.index(c)))
    agree = classes.count(cls) / len(classes)
    why = []
    if agree < params.frame_agree:
        why.append(f"frames_disagree({agree:.2f})")
    amb_frames = sum(1 for r in frame_results if r["class"] == cls and r["ambiguous"])
    if amb_frames > 0.5 * classes.count(cls):
        flags = {}
        for r in frame_results:
            if r["class"] == cls:
                for w in r["ambiguous"]:
                    flags[w.split("(")[0]] = flags.get(w.split("(")[0], 0) + 1
        why.append("frames_ambiguous")
        why.append("flags:" + ",".join(sorted(flags, key=lambda k: -flags[k])))
    return cls, agree, why


# ---------------------------------------------------------------------------------------------
# window replay
# ---------------------------------------------------------------------------------------------

def load_run_config(runs):
    """The parameter dict of the run (its ``config.yaml``), or the default configuration."""
    from scripts.eval_real import load_cfg_dict
    path = os.path.join(runs, "config.yaml")
    if not os.path.exists(path):
        path = os.path.join(ROOT, "configs", "default.yaml")
    return load_cfg_dict(path, [])


def window_config(runs, extra_sets=()):
    """The effective config of the run with the calibration off (and the stated overrides)."""
    from scripts.eval_real import load_cfg_dict
    path = os.path.join(runs, "config.yaml")
    if not os.path.exists(path):
        path = os.path.join(ROOT, "configs", "default.yaml")
    return load_cfg_dict(path, ["calibration.enabled=false", *extra_sets])


def _frames(files, stamps, cfg, lo, hi):
    from scripts.cache_io import cache_file_stem, load_cache_array
    from resense.frame import frame_from_compact
    for i in range(lo, hi + 1):
        stem = cache_file_stem(files[i])
        yield i, frame_from_compact(load_cache_array(files[i]), cfg.sensor, stamp=stamps.get(stem, i * 0.1),
                                    frame_id=stem)


def ref_row(d):
    """What a replayed frame is compared with: the STOP flag, the nearest detection and the track model of the run."""
    t = d.get("track") or {}
    nd = nearest_detection(d)
    return (bool(d["obstacle"]), None if nd is None else nd["distance"], t.get("center"), t.get("curvature"),
            (t.get("floor_coef") or [None] * 3)[2])


def same_as_run(res, ref):
    """Is a replayed frame result the run's frame: same STOP flag, same nearest detection, same track model
    (to 1e-9)? Everything but wall-clock timing is compared this way."""
    t = res.track
    nd = min(res.detections, key=lambda x: x.distance) if res.detections else None
    got = (bool(res.obstacle), None if nd is None else round(float(nd.distance), 2), float(t.center),
           float(t.curvature), float(np.asarray(t.floor_coef)[2]))
    if got[0] != ref[0] or (got[1] is None) != (ref[1] is None):
        return False
    if got[1] is not None and abs(got[1] - ref[1]) > 1e-6:
        return False
    return abs(got[2] - ref[2]) < 5e-4 and abs(got[3] - ref[3]) < 1e-9 and abs(got[4] - ref[4]) < 5e-9


def replay_job(job):
    """Window replay of one episode from ``lo`` to ``hi``: a fresh detector (calibration as the job's config says),
    or the detector restored from ``ckpt`` (a snapshot taken after frame ``lo - 1`` of the full replay). Records the
    first GO -> STOP at or after the onset - 2, the processing time, the pass-by classification at the ``eval``
    positions and (``save``) the clouds for the pictures; with ``ref`` (the run's frames) whether every replayed
    frame equals the run's."""
    import pickle
    from resense.config import DetectorConfig
    from resense.detector import Detector
    cfg = DetectorConfig.from_dict(job["cfg"])
    if job.get("ckpt"):
        with open(job["ckpt"], "rb") as fh:
            det = pickle.load(fh)
    else:
        det = Detector(cfg)
    params = ClassifierParams(**job.get("params", {}))
    files, stamps = job["files"], job["stamps"]
    lo, onset, hi = job["lo"], job["onset"], job["hi"]
    eval_at = {}
    for q in job.get("eval", []):
        eval_at.setdefault(q["i"], []).append(q)
    ref = job.get("ref")
    res_out = {"id": job["id"], "frames": 0, "proc_ms": 0.0, "stop_first": None, "stop_frames": [], "passby": [],
               "identical": True if ref else None, "first_diff": None, "onset_track": None}
    saved = {}
    t0 = time.perf_counter()
    prev_stop = bool(job.get("prev_stop", False))
    for i, fr in _frames(files, stamps, cfg, lo, hi):
        res = det.process(fr)
        res_out["frames"] += 1
        res_out["proc_ms"] += float(res.timing_ms.get("total", 0.0))
        if ref is not None and res_out["identical"] and i - lo < len(ref) and not same_as_run(res, ref[i - lo]):
            res_out["identical"], res_out["first_diff"] = False, i
        stop = bool(res.obstacle)
        if stop:
            res_out["stop_frames"].append(i)
            if not prev_stop and res_out["stop_first"] is None and i >= onset - ONSET_TOL_FRAMES:
                nd = min(res.detections, key=lambda x: x.distance)
                res_out["stop_first"] = {"frame": i, "distance": float(nd.distance), "lateral": float(nd.lateral),
                                         "kind": nd.kind, "reason": nd.reason}
        prev_stop = stop
        if i == onset:
            td = res.track.to_dict()
            res_out["onset_track"] = {k: td.get(k) for k in ("center", "yaw", "curvature", "floor_coef", "axis_valid")}
            if job.get("save") and res.xyz is not None:
                saved["onset_xyz"] = np.asarray(res.xyz, dtype=np.float32)
                saved["onset_track"] = td
        for q in eval_at.get(i, []):
            xyz_q, p_q = res.xyz, q.get("p")
            if q.get("spec") is not None:                       # a synthetic structure in track coordinates (controls)
                xyz_q, p_q = apply_spec(res.xyz, res.track, q["spec"])
            r = classify_window(xyz_q, res.track, p_q, job["size"], q["traveled"], params)
            td = res.track.to_dict()
            r.update({"frame": i, "tag": q.get("tag"), "range": round(q["range"], 1), "traveled": round(q["traveled"], 1),
                      "center": [round(float(v), 2) for v in p_q],
                      "track": {k: td.get(k) for k in ("center", "yaw", "curvature", "rail_offset")}})
            res_out["passby"].append(r)
            if job.get("save"):
                saved.setdefault("passby_xyz", {})[i] = np.asarray(res.xyz, dtype=np.float32)
                saved.setdefault("passby_track", {})[i] = td
        if job.get("stop_after_onset") and i >= onset + 3 and not eval_at:
            break
    res_out["wall_s"] = time.perf_counter() - t0
    return res_out, saved


def checkpoint_job(job):
    """One pass of the detector over a piece from its first frame, snapshotting it (pickle) before each frame of
    ``frames``; the pass is compared frame by frame with the run (STOP flag, nearest detection, track model)."""
    import pickle
    from resense.config import DetectorConfig
    from resense.detector import Detector
    cfg = DetectorConfig.from_dict(job["cfg"])
    det = Detector(cfg)
    want = set(job["frames"])
    last = max(want)
    ref, paths, bad = job["ref"], {}, []
    t0 = time.perf_counter()
    n = 0
    for i, fr in _frames(job["files"], job["stamps"], cfg, 0, last):
        if i in want:
            path = os.path.join(job["dir"], f"{job['key']}_{i}.pkl")
            with open(path, "wb") as fh:
                pickle.dump(det, fh, protocol=pickle.HIGHEST_PROTOCOL)
            paths[i] = path
        if i == last:
            break
        res = det.process(fr)
        n += 1
        if not same_as_run(res, ref[i]):
            bad.append(i)
    return {"key": job["key"], "paths": paths, "frames": n, "mismatch_frames": bad,
            "wall_s": time.perf_counter() - t0}


def track_delta(win, ref):
    """Window minus run: the track model at the onset frame (centre m, curvature 1/m, bed height at the sensor m,
    the range the axis is supported to, m)."""
    if not win or not ref or ref.get("floor_coef") is None:
        return None
    return {"center_m": round(float(win["center"]) - float(ref["center"]), 4),
            "curvature_per_m": float(win["curvature"]) - float(ref["curvature"]),
            "floor_z0_m": round(float(win["floor_coef"][2]) - float(ref["floor_coef"][2]), 4),
            "axis_valid_m": round(float(win["axis_valid"]) - float(ref["axis_valid"]), 1)}


def reproduces(row, rep):
    """Does the window replay reproduce the episode: a GO -> STOP onset within ``ONSET_TOL_FRAMES`` of the
    full replay's onset and the nearest detection's distance within ``DIST_TOL_M``?"""
    sf = rep.get("stop_first")
    if sf is None:
        return False, None, None
    df = sf["frame"] - row.get("piece_frame", row["frame"])
    dd = sf["distance"] - row["distance"]
    return bool(abs(df) <= ONSET_TOL_FRAMES and abs(dd) <= DIST_TOL_M), df, round(dd, 2)


# ---------------------------------------------------------------------------------------------
# pictures
# ---------------------------------------------------------------------------------------------

def _scatter_panels(ax_bev, ax_side, xyz, track_dict, center, size, title, xmax, window=None, mark=None):
    from resense.gauge import corridor_coordinates
    m = track_from_dict(track_dict)
    xs = xyz[:, 0]
    sel = (xs > 0) & (xs < xmax) & (np.abs(xyz[:, 1] - float(m.center_y(np.array([0.0]))[0])) < 9.0)
    pts = xyz[sel]
    if len(pts) > 40000:
        pts = pts[np.random.default_rng(0).choice(len(pts), 40000, replace=False)]
    dy, h = corridor_coordinates(pts.astype(np.float32), m)
    for ax, (u, v) in ((ax_bev, (1, 0)), (ax_side, (0, 2))):
        ax.scatter(pts[:, u], pts[:, v], c=np.clip(h, -0.5, 4.0), s=0.6, cmap="viridis", vmin=-0.5, vmax=4.0,
                   linewidths=0, rasterized=True)
    xg = np.linspace(0.0, xmax, 60)
    cy = m.center_y(xg)
    ax_bev.plot(cy, xg, "r-", lw=0.7)
    ax_bev.plot(cy + SIDE_DY, xg, "r:", lw=0.6)
    ax_bev.plot(cy - SIDE_DY, xg, "r:", lw=0.6)
    ax_side.plot(xg, m.rail_z(xg), "r-", lw=0.7)
    ax_side.plot(xg, m.rail_z(xg) + OVERHEAD_H, "r:", lw=0.6)
    cx, cyy, cz = (float(v) for v in center)
    from matplotlib.patches import Rectangle
    ax_bev.add_patch(Rectangle((cyy - size[1] / 2, cx - size[0] / 2), size[1], size[0], fill=False, ec="orange", lw=1.2))
    ax_side.add_patch(Rectangle((cx - size[0] / 2, cz - size[2] / 2), size[0], size[2], fill=False, ec="orange", lw=1.2))
    if window is not None:
        lon, lat, zh = window
        ax_bev.add_patch(Rectangle((cyy - lat, cx - lon), 2 * lat, 2 * lon, fill=False, ec="magenta", lw=0.9))
        ax_side.add_patch(Rectangle((cx - lon, cz - zh), 2 * lon, 2 * zh, fill=False, ec="magenta", lw=0.9))
    ax_bev.set_xlim(9, -9)                                 # left of the train on the left of the picture
    ax_bev.set_ylim(0, xmax)
    ax_side.set_xlim(0, xmax)
    ax_side.set_title(title, fontsize=7, loc="left")
    for a in (ax_bev, ax_side):
        a.tick_params(labelsize=6)
    ax_bev.set_xlabel("y (m), left +", fontsize=6)
    ax_bev.set_ylabel("x (m)", fontsize=6)
    ax_side.set_xlabel("x (m)", fontsize=6)
    ax_side.set_ylabel("z (m)", fontsize=6)
    ax_side.set_ylim(float(np.min(m.rail_z(xg))) - 1.0, float(np.max(m.rail_z(xg))) + 5.5)
    return mark


def render_episode(path, row, saved, passby):
    """One PNG: BEV and side view of the onset frame (top) and of the pass-by frame nearest to 18 m (bottom)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    fig, axs = plt.subplots(2, 2, figsize=(9.0, 6.2), gridspec_kw={"width_ratios": [1, 2]})
    xmax = max(40.0, row["distance"] + 25.0)
    _scatter_panels(axs[0][0], axs[0][1], saved["onset_xyz"], saved["onset_track"], row["center"], row["size"],
                    f"{row['id']}  onset d={row['distance']:.0f} m lat={row['lateral']:+.1f} "
                    f"{row['kind']}/{row['reason']}", xmax)
    if passby and passby.get("frames") and saved.get("passby_xyz"):
        best = min(passby["frames"], key=lambda r: abs(r["range"] - 18.0))
        f = best["frame"]
        q = next(x for x in passby["path"] if x["i"] == f)
        _scatter_panels(axs[1][0], axs[1][1], saved["passby_xyz"][f], saved["passby_track"][f], q["p"], row["size"],
                        f"pass-by frame {f}, {best['range']:.0f} m from the onset position: {passby['class']} "
                        f"(structure dy {best['dy_med']}, h {best['h_med']}; position dy {best['dy_position']})", 45.0,
                        window=(best["lon"], best["lat"], best["z_half"]))
    else:
        for a in axs[1]:
            a.axis("off")
        axs[1][0].text(0.0, 0.5, f"no pass-by: {passby['class'] if passby else 'n/a'}", fontsize=8)
    fig.tight_layout()
    tmp = path + ".tmp.png"
    fig.savefig(tmp, dpi=80)
    plt.close(fig)
    Image.open(tmp).convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)
    os.remove(tmp)


# ---------------------------------------------------------------------------------------------
# the F2 summary
# ---------------------------------------------------------------------------------------------

CARD_FRACTION = 34.0 / 36.0     # the card's reproduction share, restated for the episode count of the seal
AXIS_MISFIT_M = 0.9              # the strict edge at 100 m: 1.05 - 0.15 (BACKLOG K1)


def mechanism(e):
    """The F2 mechanism of an episode from its pass-by block: what the far cluster turned out to be, and by how much the far
    axis had to be off for it to lie in the gauge (``axis_error_m``: where the structure stands relative to the re-fitted
    axis minus the lateral the onset reported)."""
    pb = e.get("passby") or {}
    cls = pb.get("class")
    err = pb.get("axis_error_m")
    if cls == "side" and err is not None and abs(err) >= AXIS_MISFIT_M:
        return "side_structure_axis_misfit" + ("_tunnel_surface" if pb.get("on_tunnel_surface") else "_object")
    if cls == "side":
        return "side_structure_within_axis_error"
    if cls == "overhead":
        return "overhead_height_reference"
    if cls == "in_envelope":
        return "in_envelope_structure"
    if cls in ("bed_rail", "phantom"):
        return "bed_or_phantom_height_reference"
    return "unclassified"


def f2_summary(episodes):
    """How many far-onset (>= FAR_ONSET m) episodes fall in each pass-by class and mechanism, and the far axis error."""
    out = {"far_threshold_m": FAR_ONSET, "episodes": len(episodes), "far_episodes": 0, "by_class": {},
           "by_class_all": {}, "by_mechanism_far": {}, "by_mechanism_all": {}}
    for scope, key in ((True, "by_class"), (False, "by_class_all")):
        for e in episodes:
            if scope and not e["far_onset"]:
                continue
            pb = e.get("passby") or {}
            b = out[key].setdefault(pb.get("class") or "unclassified", {"n": 0, "ambiguous": 0, "ids": []})
            b["n"] += 1
            b["ambiguous"] += int(bool(pb.get("ambiguous")))
            b["ids"].append(e["id"])
    for scope, key in ((True, "by_mechanism_far"), (False, "by_mechanism_all")):
        for e in episodes:
            if scope and not e["far_onset"]:
                continue
            b = out[key].setdefault(mechanism(e), {"n": 0, "ids": []})
            b["n"] += 1
            b["ids"].append(e["id"])
    out["far_episodes"] = sum(1 for e in episodes if e["far_onset"])
    far = [e for e in episodes if e["far_onset"] and (e.get("passby") or {}).get("axis_error_m") is not None]
    if far:
        err = np.array([e["passby"]["axis_error_m"] for e in far])
        out["far_axis_error_m"] = {"n": len(far), "median_abs": round(float(np.median(np.abs(err))), 2),
                                   "p25_abs": round(float(np.percentile(np.abs(err), 25)), 2),
                                   "p75_abs": round(float(np.percentile(np.abs(err), 75)), 2),
                                   "share_at_least_0.9": round(float(np.mean(np.abs(err) >= AXIS_MISFIT_M)), 2),
                                   "share_at_least_1.4": round(float(np.mean(np.abs(err) >= SIDE_DY)), 2)}
    return out


# ---------------------------------------------------------------------------------------------
# positive controls
# ---------------------------------------------------------------------------------------------

def apply_spec(xyz, track, spec):
    """Add a synthetic box, given in track coordinates (``x``, ``dy`` from the axis, ``h`` above the rail head), to
    the cloud and return (cloud, centre of the box in the vehicle frame). ``n`` = 0 adds nothing (an empty
    position, for the negative controls)."""
    x0, x1, d0, d1, h0, h1 = spec["box"]
    xm, dm, hm = 0.5 * (x0 + x1), 0.5 * (d0 + d1), 0.5 * (h0 + h1)
    X = np.array([xm])
    centre = np.array([xm, float(track.center_y(X)[0]) + dm, float(track.rail_z(X)[0]) + hm])
    n = int(spec.get("n", 0))
    if n <= 0:
        return xyz, centre
    r = np.random.default_rng(int(spec.get("seed", 0)))
    x = r.uniform(x0, x1, n)
    pts = np.column_stack([x, track.center_y(x) + r.uniform(d0, d1, n), track.rail_z(x) + r.uniform(h0, h1, n)])
    return np.vstack([np.asarray(xyz), pts.astype(np.float32)]), centre


# the synthetic cases: (name, box in track coordinates, number of points, the known answer)
SYNTHETIC_CASES = [
    ("box_in_envelope", [21.8, 22.2, -0.25, 0.25, 0.1, 1.0], 150, "in_envelope"),
    ("box_beside_wall", [21.8, 22.2, 1.65, 1.85, 0.2, 1.2], 150, "side"),
    ("plate_overhead", [21.8, 22.2, -0.3, 0.3, 3.25, 3.45], 150, "overhead"),
    ("bed_only", [21.8, 22.2, -0.25, 0.25, -0.30, -0.25], 0, "bed_rail"),
    ("empty_above_the_crown", [21.8, 22.2, -0.25, 0.25, 9.0, 9.5], 0, "phantom"),
    ("air_in_envelope", [21.8, 22.2, -0.25, 0.25, 0.5, 1.0], 0, "not_in_envelope"),
]


def expected_from_label(o, margin=0.1):
    """The answer the organizers' labels give for one labelled object in one frame (an independent source: their own
    appended points, not this classifier): the centre of the box above ``OVERHEAD_H`` = overhead; the whole box
    beyond ``SIDE_DY`` + ``margin`` from the axis = side; the whole box inside ``SIDE_DY`` - ``margin`` = in_envelope;
    anything that straddles a limit is None (a boundary case: not scored)."""
    h = o.get("h_above_rail")
    if h and 0.5 * (h[0] + h[1]) > OVERHEAD_H:
        return "overhead"
    half = 0.5 * float(o["size"][1]) if o.get("size") else 0.0
    near, far = abs(o.get("lateral", 0.0)) - half, abs(o.get("lateral", 0.0)) + half
    if near > SIDE_DY + margin:
        return "side"
    if far < SIDE_DY - margin:
        return "in_envelope"
    return None


def label_center(o):
    return np.array(o["bbox"], dtype=float).mean(axis=0)


def label_size(o):
    b = np.array(o["bbox"], dtype=float)
    return (b[1] - b[0]).tolist()


def cmd_controls(a):
    """Positive controls: (1) set O: each organizer object carried from ~120 m with the ledger's transport and
    classified in the band, and classified at its labelled position; (2) the real labelled people and the object on the
    rail of doubleT_obstacle at their labelled positions; (3) synthetic structures, one known answer per class,
    added to real frames, with their empty positions as negative controls."""
    cfg = window_config(a.runs, a.set)
    bags = {"set_O": "cloud_with_fake_obj", "doubleT": "doubleT_obstacle"}
    result = {"schema": SCHEMA + "-controls", "set_O": [], "transport": [], "doubleT_obstacle": [], "synthetic": []}
    from scripts.cache_io import cache_files, load_cache_stamps
    jobs, meta = [], []
    # --- set O
    runs_o = a.runs_o or a.runs
    if os.path.exists(os.path.join(runs_o, bags["set_O"] + ".jsonl")):
        pieces, all_rows = load_all(runs_o, a.windows, [bags["set_O"]])
        rows, piece = all_rows[0], pieces[0]
        speeds = speed_series(rows)
        labels = json.load(open(os.path.join(ROOT, "labels", bags["set_O"] + ".json")))
        stamps = load_cache_stamps(os.path.join(a.windows, bags["set_O"]))
        objs = {}
        for i in range(len(rows)):
            for o in labels.get(f"{i:05d}", []):
                if o.get("plausible") and o.get("bbox") and o.get("n_points", 0) >= 5:
                    objs.setdefault(o["name"], {})[i] = o
        for name, fr in objs.items():
            far = [k for k in fr if 40.0 <= fr[k]["distance"] <= 140.0]
            near = [k for k in fr if BAND[0] <= fr[k]["distance"] <= BAND[1] and fr[k]["n_points"] >= 3]
            if not far:
                result["set_O"].append({"object": name, "skipped": "no plausible frame with 5+ points between 40 and 140 m"})
                continue
            f0 = min(far, key=lambda k: abs(fr[k]["distance"] - 110.0))
            c0, size = label_center(fr[f0]), label_size(fr[f0])
            path = transport(rows, f0, c0, speeds)
            tr, closest, mode = band_frames(path)
            entries = [{**q, "tag": "transport"} for q in tr]
            if near:
                pick = np.unique(np.linspace(0, len(near) - 1, min(6, len(near))).round().astype(int))
                for j in pick:
                    f = sorted(near)[j]
                    entries.append({"i": f, "p": label_center(fr[f]), "traveled": 0.0, "range": fr[f]["distance"],
                                    "tag": "truth"})
            if not entries:
                result["set_O"].append({"object": name, "skipped": f"no frames in band (closest {closest})"})
                continue
            frames_ = [q["i"] for q in entries]
            jobs.append({"id": f"{bags['set_O']}:{name}", "cfg": cfg, "files": piece["files"], "stamps": stamps,
                         "onset": min(frames_), "size": size, "lo": max(0, min(frames_) - a.passby_pre),
                         "hi": max(frames_), "eval": entries, "save": False, "stop_after_onset": False})
            meta.append(("set_O", name, fr, path, c0, f0))
    # --- doubleT_obstacle: labelled people and the object on the rail (the train stands: labelled positions)
    runs_d = a.runs_d or a.runs
    if os.path.exists(os.path.join(runs_d, bags["doubleT"] + ".jsonl")):
        pieces, all_rows = load_all(runs_d, a.windows, [bags["doubleT"]])
        piece = pieces[0]
        labels = json.load(open(os.path.join(ROOT, "labels", bags["doubleT"] + ".json")))
        stamps = load_cache_stamps(os.path.join(a.windows, bags["doubleT"]))
        picks = {"person_crossing_inside": [], "person_outside": [], "object_on_rail": []}
        for i in range(len(all_rows[0])):
            for o in labels.get(f"{i:05d}", []):
                if not o.get("bbox") or o.get("n_points", 0) < 20 and o["name"] == "person":
                    continue
                if o["name"] == "person" and o.get("in_gauge") and 10 <= i <= 60:
                    picks["person_crossing_inside"].append((i, o))
                elif o["name"] == "person" and not o.get("in_gauge") and i >= 100:
                    picks["person_outside"].append((i, o))
                elif o["name"] == "object_on_rail" and i >= 75 and o.get("n_points", 0) >= 5:
                    picks["object_on_rail"].append((i, o))
        for name, lst in picks.items():
            if not lst:
                continue
            lst = lst[:: max(1, len(lst) // 5)][:5]
            entries = [{"i": i, "p": label_center(o), "traveled": 0.0, "range": o["distance"], "tag": "truth"}
                       for i, o in lst]
            jobs.append({"id": f"{bags['doubleT']}:{name}", "cfg": cfg, "files": piece["files"], "stamps": stamps,
                         "onset": entries[0]["i"], "size": label_size(lst[0][1]), "lo": max(0, min(e["i"] for e in entries) - 60),
                         "hi": max(e["i"] for e in entries), "eval": entries, "save": False, "stop_after_onset": False})
            meta.append(("doubleT", name, dict(lst), None, None, None))
    # --- synthetic structures on real frames
    for bag, frame in ((b, f) for b, f in a.synthetic_frames):
        d = os.path.join(a.windows, bag)
        if not os.path.isdir(d):
            continue
        files, stamps = cache_files(d), load_cache_stamps(d)
        entries = [{"i": frame, "spec": {"box": box, "n": n, "seed": 7}, "traveled": 0.0, "range": 22.0,
                    "tag": f"{name}|{want}"} for name, box, n, want in SYNTHETIC_CASES]
        jobs.append({"id": f"synthetic:{bag}:{frame}", "cfg": cfg, "files": files, "stamps": stamps, "onset": frame,
                     "size": [0.4, 0.5, 0.9], "lo": max(0, frame - 80), "hi": frame, "eval": entries, "save": False,
                     "stop_after_onset": False})
        meta.append(("synthetic", bag, None, None, None, frame))
    outs = run_pool(replay_job, jobs, a.jobs)
    for (kind, name, fr, path, c0, f0), (r, _) in zip(meta, outs):
        if kind == "synthetic":
            base = next((f for f in r["passby"] if f["tag"].startswith("air_in_envelope")), None)
            if base is None or base["class"] == "in_envelope":
                result.setdefault("skipped_frames", []).append(
                    {"bag": name, "frame": f0, "why": "the empty control position already holds a real structure"})
                continue
        res = r["passby"]
        if kind == "set_O":
            for pr in res:
                o = fr.get(pr["frame"])
                exp = expected_from_label(o) if o else None
                pr["expected"], pr["object"] = exp, name
                if pr["tag"] == "transport" and o is not None:
                    q = next(x for x in path if x["i"] == pr["frame"])
                    pr["transport_error"] = np.round(q["p"] - label_center(o), 2).tolist()
                    result["transport"].append({"object": name, "frame": pr["frame"], "traveled": pr["traveled"],
                                                "error": pr["transport_error"], "label_distance": o["distance"]})
            result["set_O"].append({"object": name, "onset_frame": f0, "onset_center": np.round(c0, 2).tolist(),
                                    "frames": res})
        elif kind == "doubleT":
            for pr in res:
                pr["object"] = name
                pr["expected"] = {"person_crossing_inside": "in_envelope", "person_outside": "side",
                                  "object_on_rail": "in_envelope"}[name]
            result["doubleT_obstacle"].append({"object": name, "frames": res})
        else:
            for pr in res:
                case, want = pr["tag"].split("|")
                pr["case"], pr["expected"] = case, want
            result["synthetic"].append({"bag": name, "frame": f0, "frames": res})
    result["summary"] = control_summary(result)
    os.makedirs(os.path.dirname(os.path.abspath(a.controls_out)) or ".", exist_ok=True)
    with open(a.controls_out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps(result["summary"], indent=1))
    return result


def control_summary(result):
    """Per source and per class: how many control frames got the known answer."""
    out = {}

    def tally(source, rows, key=lambda r: r["expected"], ok=None):
        t = out.setdefault(source, {})
        for r in rows:
            exp = key(r)
            if exp is None:
                t.setdefault("unscored", 0)
                t["unscored"] += 1
                continue
            hit = r["class"] == exp if ok is None else ok(r, exp)
            b = t.setdefault(exp, {"n": 0, "hit": 0, "got": {}})
            b["n"] += 1
            b["hit"] += int(hit)
            b["got"][r["class"]] = b["got"].get(r["class"], 0) + 1

    for o in result["set_O"]:
        for tag in ("truth", "transport"):
            tally(f"set_O_{tag}", [f for f in o.get("frames", []) if f["tag"] == tag])
    for o in result["doubleT_obstacle"]:
        tally("doubleT_obstacle_truth", o["frames"])
    for o in result["synthetic"]:
        tally("synthetic", o["frames"], ok=lambda r, exp: (r["class"] != "in_envelope") if exp == "not_in_envelope"
              else r["class"] == exp)
    err = np.array([t["error"] for t in result["transport"]]) if result["transport"] else np.zeros((0, 3))
    if len(err):
        out["transport_error_m"] = {ax: {"median_abs": round(float(np.median(np.abs(err[:, k]))), 2),
                                         "p90_abs": round(float(np.percentile(np.abs(err[:, k]), 90)), 2)}
                                    for k, ax in enumerate("xyz")}
        out["transport_error_m"]["n"] = int(len(err))
    return out


# ---------------------------------------------------------------------------------------------
# the command
# ---------------------------------------------------------------------------------------------

def load_all(runs, cache, bags):
    pieces = piece_table(runs, cache, bags)
    all_rows = []
    for p in pieces:
        rows = read_jsonl(p["path"])
        check_piece(p, rows)
        all_rows.append(rows)
    return pieces, all_rows


def piece_index(pieces):
    return {(p["bag"], p["piece"]): n for n, p in enumerate(pieces)}


def run_pool(fn, jobs, n_jobs):
    if n_jobs <= 1:
        return [fn(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        return list(ex.map(fn, jobs, chunksize=1))


def extended(pieces, all_rows, n):
    """The rows and cache files of piece ``n`` followed by the later pieces of the same recording (the ride's pieces are
    consecutive: the train goes on after a piece ends, only the detector restarts)."""
    rows, files = list(all_rows[n]), list(pieces[n]["files"])
    for m in range(n + 1, len(pieces)):
        if pieces[m]["bag"] != pieces[n]["bag"]:
            break
        rows += all_rows[m]
        files += pieces[m]["files"]
    return rows, files


def episode_paths(pieces, all_rows, episodes):
    """The ego transport of every episode: {id: (path, band frames, closest range, mode)}. The path continues into the
    later pieces of the ride, so an onset near the end of a piece is still carried to the train's arrival."""
    split_speeds = intake_speeds()
    pidx = piece_index(pieces)
    cache, out = {}, {}
    for e in episodes:
        n = pidx[(e["recording"], e["piece"])]
        if n not in cache:
            rows, _ = extended(pieces, all_rows, n)
            cache[n] = (rows, speed_series(rows, split_speeds))
        rows, speeds = cache[n]
        path = transport(rows, e["piece_frame"], e["center"], speeds)
        fr, closest, mode = band_frames(path)
        out[e["id"]] = (path, fr, closest, mode)
    return out


def classify_episode(e, path, fr, closest, mode, results):
    """The pass-by block of a ledger row from the per-frame classifications."""
    pb = {"closest_range_m": None if closest is None else round(closest, 1), "frames": results or [], "mode": mode}
    if results:
        cls, agree, why = episode_class(results, ClassifierParams())
        if mode == "nearest":
            why = [*why, f"beyond_band(closest {pb['closest_range_m']} m)"]
    else:
        cls, agree, why = "unreached", 0.0, [f"closest_range_{pb['closest_range_m']}"]
    srcs = [q["src"] for q in path[1:]]
    use = [f for f in (results or []) if f["class"] == cls]
    dys = [f["dy_position"] for f in (results or [])]
    hb = [f["h_bottom"] for f in use if f.get("h_bottom") is not None]
    pb["position_dy_m"] = None if not dys else round(float(np.median(dys)), 2)
    pb["axis_error_m"] = None if not dys else round(float(np.median(dys)) - float(e["lateral"]), 2)
    pb["structure_h_bottom_m"] = None if not hb else round(float(np.median(hb)), 2)
    pb["height_error_m"] = (None if not hb or e.get("height_min") is None
                            else round(float(e["height_min"]) - float(np.median(hb)), 2))
    pb["on_tunnel_surface"] = bool(use) and sum(bool(f.get("on_fabric")) for f in use) > 0.5 * len(use)
    pb["by_position"] = bool(use) and sum(bool(f.get("by_position")) for f in use) > 0.5 * len(use)
    pb["n_localized"] = None if not use else int(np.median([f["n_env"] + f["n_side"] + f["n_over"] for f in use]))
    pb.update({"class": cls, "agreement": round(agree, 2), "ambiguous": bool(why), "ambiguous_why": why,
               "traveled_m": round(path[-1]["traveled"], 1), "speed_sources": sorted(set(srcs)),
               "odometry_not_measured_share": round(float(np.mean([x in ("interp", "hold", "none", "intake")
                                                                    for x in srcs])) if srcs else 0.0, 2)})
    return pb


def code_state():
    """The commit this ran on and whether the sealed detector files are intact (scripts/detector_freeze.py verify)."""
    import subprocess

    def run(*cmd):
        try:
            return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
    return {"commit": run("git", "rev-parse", "HEAD"), "branch": run("git", "rev-parse", "--abbrev-ref", "HEAD"),
            "detector_freeze": (run(sys.executable, os.path.join(ROOT, "scripts", "detector_freeze.py"), "verify") or "").splitlines()[:1]}


def cmd_ledger(a):
    from scripts.cache_io import load_cache_stamps
    t_start = time.time()
    bags = [b for b in a.bags.split(",") if b]
    pieces, all_rows = load_all(a.runs, a.windows, bags)
    if not pieces:
        raise SystemExit(f"no run files for {bags} in {a.runs}")
    episodes = build_rows(pieces, all_rows)
    pidx = piece_index(pieces)
    cfg_fresh = window_config(a.runs, a.set)                      # the card's window: calibration off
    cfg_run = window_config(a.runs, a.set)
    cfg_run["calibration"] = dict(load_run_config(a.runs).get("calibration", cfg_run.get("calibration", {})))
    os.makedirs(a.out, exist_ok=True)
    png_dir = os.path.join(a.out, "png")
    save = png_dir if not a.no_png else None
    if save:
        os.makedirs(save, exist_ok=True)
    stamps = {b: load_cache_stamps(os.path.join(a.windows, b)) for b in {e["recording"] for e in episodes}}
    paths = episode_paths(pieces, all_rows, episodes) if not a.no_passby else {}
    timing = {}

    def base(e):
        n = pidx[(e["recording"], e["piece"])]
        return {"id": e["id"], "files": pieces[n]["files"], "stamps": stamps[e["recording"]], "onset": e["piece_frame"],
                "size": e["size"]}, all_rows[n]

    # --- 1. the card's window: a fresh detector, calibration off, ``pre_roll`` frames before the onset
    def fresh_jobs(pre, with_save):
        jobs = []
        for e in episodes:
            b, rows = base(e)
            jobs.append({**b, "cfg": cfg_fresh, "lo": max(0, e["piece_frame"] - pre),
                         "hi": min(len(rows) - 1, e["piece_frame"] + 3), "stop_after_onset": True, "save": with_save})
        return jobs

    t0 = time.time()
    fresh = run_pool(replay_job, fresh_jobs(a.pre_roll, False), a.jobs) if not a.no_fresh else \
        [({"stop_first": None, "frames": 0, "proc_ms": 0.0, "onset_track": None}, {}) for _ in episodes]
    timing["fresh"] = {"pre_roll": a.pre_roll, "wall_s": round(time.time() - t0, 1),
                       "frames": sum(r[0]["frames"] for r in fresh),
                       "proc_s": round(sum(r[0]["proc_ms"] for r in fresh) / 1e3, 1)}
    sweep = {}
    for pre in a.sweep:
        out = run_pool(replay_job, fresh_jobs(pre, False), a.jobs)
        sweep[str(pre)] = {"reproduced": sum(int(reproduces(e, r[0])[0]) for e, r in zip(episodes, out)),
                           "frames": sum(r[0]["frames"] for r in out)}
    for e, (r, _) in zip(episodes, fresh):
        ok, df, dd = reproduces(e, r)
        e["window"] = {"reproduced": ok, "onset_delta_frames": df, "distance_delta_m": dd, "first_stop": r["stop_first"],
                       "frames_replayed": r["frames"], "pre_roll": a.pre_roll,
                       "track_delta_at_onset": track_delta(r.get("onset_track"), e["track"])}

    # --- 2. exact windows: the detector restored from a snapshot ``ckpt_pre`` frames before the onset
    ckpt_dir = os.path.join(a.out, ".ckpt") if not a.ckpt_dir else a.ckpt_dir
    timing["checkpoint_pass"] = timing["checkpoint_windows"] = None
    cp_results = {}
    if not a.no_checkpoint:
        os.makedirs(ckpt_dir, exist_ok=True)
        by_piece = {}
        for e in episodes:
            by_piece.setdefault((e["recording"], e["piece"]), []).append(max(0, e["piece_frame"] - a.ckpt_pre))
        cjobs = []
        for (bag, k), frames in by_piece.items():
            n = pidx[(bag, k)]
            cjobs.append({"key": f"{bag}_{k}", "cfg": cfg_run, "files": pieces[n]["files"], "stamps": stamps[bag],
                          "frames": sorted(set(frames)), "dir": ckpt_dir, "ref": [ref_row(d) for d in all_rows[n]]})
        cjobs.sort(key=lambda j: -max(j["frames"]))
        t0 = time.time()
        have = a.reuse_checkpoints and all(os.path.exists(os.path.join(ckpt_dir, f"{j['key']}_{c}.pkl"))
                                           for j in cjobs for c in j["frames"])
        if have:                                           # development: the snapshots of an earlier run of the same detector
            cps = [{"key": j["key"], "paths": {c: os.path.join(ckpt_dir, f"{j['key']}_{c}.pkl")
                                                for c in j["frames"]}, "frames": 0, "mismatch_frames": []} for j in cjobs]
        else:
            cps = run_pool(checkpoint_job, cjobs, a.jobs)
        timing["checkpoint_pass"] = {"wall_s": round(time.time() - t0, 1), "frames": sum(c["frames"] for c in cps),
                                     "pieces": len(cps), "mismatch_frames": sum(len(c["mismatch_frames"]) for c in cps)}
        cp_paths = {c["key"]: c["paths"] for c in cps}
        wjobs = []
        for e in episodes:
            b, rows = base(e)
            n = pidx[(e["recording"], e["piece"])]
            rows_ext, files_ext = extended(pieces, all_rows, n)
            c = max(0, e["piece_frame"] - a.ckpt_pre)
            last = e["piece_frame"] + 3
            ev = []
            if e["id"] in paths and paths[e["id"]][1]:
                ev = paths[e["id"]][1]
                last = max(last, max(q["i"] for q in ev))
            last = min(last, len(rows_ext) - 1)
            b = {**b, "files": files_ext}
            wjobs.append({**b, "cfg": cfg_run, "ckpt": cp_paths[f"{e['recording']}_{e['piece']}"][c], "lo": c, "hi": last,
                          "prev_stop": bool(rows[c - 1]["obstacle"]) if c > 0 else False, "eval": ev,
                          "ref": [ref_row(d) for d in rows[c:min(last, len(rows) - 1) + 1]], "save": save is not None,
                          "stop_after_onset": False})
        t0 = time.time()
        cw = run_pool(replay_job, wjobs, a.jobs)
        timing["checkpoint_windows"] = {"wall_s": round(time.time() - t0, 1), "frames": sum(r[0]["frames"] for r in cw),
                                        "proc_s": round(sum(r[0]["proc_ms"] for r in cw) / 1e3, 1)}
        for e, (r, sv) in zip(episodes, cw):
            ok, df, dd = reproduces(e, r)
            e["checkpoint_window"] = {"reproduced": ok, "onset_delta_frames": df, "distance_delta_m": dd,
                                      "identical_to_run": r["identical"], "first_difference": r["first_diff"],
                                      "frames_replayed": r["frames"], "snapshot_frame": max(0, e["piece_frame"] - a.ckpt_pre)}
            cp_results[e["id"]] = (r, sv)
    else:
        # fallback without snapshots: a fresh detector with ``passby_pre`` frames of pre-roll up to the last band frame
        pj = []
        for e in episodes:
            if e["id"] in paths and paths[e["id"]][1]:
                b, rows = base(e)
                b = {**b, "files": extended(pieces, all_rows, pidx[(e["recording"], e["piece"])])[1]}
                ev = paths[e["id"]][1]
                first, last = min(q["i"] for q in ev), max(q["i"] for q in ev)
                pj.append({**b, "cfg": cfg_fresh, "onset": first, "lo": max(0, first - a.passby_pre), "hi": last,
                           "eval": ev, "save": save is not None, "stop_after_onset": False})
        for r, sv in run_pool(replay_job, pj, a.jobs):
            cp_results[r["id"]] = (r, sv)

    # --- 3. pass-by classes and pictures
    if not a.no_passby:
        for e in episodes:
            path, fr, closest, mode = paths[e["id"]]
            r, sv = cp_results.get(e["id"], ({"passby": []}, {}))
            e["passby"] = classify_episode(e, path, fr, closest, mode, r["passby"])
            if save and sv and "onset_xyz" in sv:
                render_episode(os.path.join(png_dir, e["id"].replace(":", "_") + ".png"), e, sv,
                               {**e["passby"], "path": path} if e["passby"]["frames"] else e["passby"])
    if not a.keep_checkpoints and not a.ckpt_dir:
        import shutil
        shutil.rmtree(ckpt_dir, ignore_errors=True)

    odo = {}
    split_speeds = intake_speeds()
    for piece, rows in zip(pieces, all_rows):
        v, src = speed_series(rows, split_speeds)
        dts = np.array([frame_dt(rows[i].get("stamp"), rows[i + 1].get("stamp")) for i in range(len(rows) - 1)] + [0.1])
        o = odo.setdefault(piece["bag"], {"frames": 0, "path_m": 0.0, "by_source": {}})
        o["frames"] += len(rows)
        o["path_m"] += float((v * dts).sum())
        for k in set(src.tolist()):
            o["by_source"][k] = o["by_source"].get(k, 0) + int((src == k).sum())
    for o in odo.values():
        o["path_m"] = round(o["path_m"], 0)
    full_frames = sum(len(r) for r in all_rows)
    full_proc = sum(float((d.get("timing_ms") or {}).get("total", 0.0)) for rows in all_rows for d in rows) / 1e3
    summary = {"episodes": len(episodes), "far_episodes": sum(int(e["far_onset"]) for e in episodes),
               "reproduced_fresh_window": (sum(int(e["window"]["reproduced"]) for e in episodes) if not a.no_fresh else None),
               "reproduced_checkpoint_window": (sum(int(e["checkpoint_window"]["reproduced"]) for e in episodes)
                                                if not a.no_checkpoint else None),
               "checkpoint_windows_identical_to_run": (sum(int(bool(e["checkpoint_window"]["identical_to_run"]))
                                                           for e in episodes) if not a.no_checkpoint else None),
               "full_replay": {"frames": full_frames, "proc_s_in_run": round(full_proc, 1)},
               "odometry": odo, "timing": timing, "fresh_pre_roll_sweep": sweep, "wall_total_s": round(time.time() - t_start, 1)}
    if not a.no_passby:
        summary["f2"] = f2_summary(episodes)
    meta = {"schema": SCHEMA, "created": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            "runs": os.path.abspath(a.runs), "bags": bags, "pre_roll": a.pre_roll, "checkpoint_pre": a.ckpt_pre,
            "passby_pre_roll_without_checkpoints": a.passby_pre,
            "tolerance": {"onset_frames": ONSET_TOL_FRAMES, "distance_m": DIST_TOL_M},
            "thresholds": {"side_dy": SIDE_DY, "overhead_h": OVERHEAD_H, "bed_h": BED_H, "band_m": list(BAND),
                           "far_onset_m": FAR_ONSET},
            "classifier": asdict(ClassifierParams()), "jobs": a.jobs}
    need = int(math.ceil(CARD_FRACTION * len(episodes) - 1e-9))
    summary["done_when"] = {"card": "34 of 36 episodes (>= 94.4 %), onset within 2 frames, distance within 2 m, "
                                    "at least 2x faster than full replays",
                            "restated_for_episodes": len(episodes), "required": need,
                            "fresh_window_reproduced": summary["reproduced_fresh_window"],
                            "fresh_window_met": (None if a.no_fresh else summary["reproduced_fresh_window"] >= need),
                            "snapshot_window_reproduced": summary["reproduced_checkpoint_window"]}
    if not a.no_fresh and timing["fresh"]["proc_s"]:
        summary["done_when"]["fresh_window_speedup_proc_time"] = round(full_proc / timing["fresh"]["proc_s"], 2)
        summary["done_when"]["fresh_window_speedup_frames"] = round(full_frames / timing["fresh"]["frames"], 2)
    meta["code"] = code_state()
    doc = {"meta": meta, "summary": summary, "episodes": episodes}
    with open(os.path.join(a.out, "ledger.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    print(json.dumps(summary, indent=1))
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True, help="per-frame JSONL directory of a gate / eval_real run")
    ap.add_argument("--windows", required=True, help="frame cache directory (<cache>/<bag>/*.npy)")
    ap.add_argument("--out", default=None, help="output directory: ledger.json and png/")
    ap.add_argument("--bags", default=",".join(EMPTY_BAGS + [RIDE]))
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--pre-roll", type=int, default=PRE_ROLL)
    ap.add_argument("--passby-pre", type=int, default=60, help="pre-roll frames of the pass-by replay")
    ap.add_argument("--set", action="append", default=[], help="extra section.key=value override of the window config")
    ap.add_argument("--sweep", default="", help="comma-separated extra pre-roll lengths for the fresh-window sweep")
    ap.add_argument("--ckpt-pre", type=int, default=30, help="frames between the snapshot and the onset")
    ap.add_argument("--ckpt-dir", default=None, help="keep the snapshots here (default: a temporary directory under --out)")
    ap.add_argument("--keep-checkpoints", action="store_true")
    ap.add_argument("--reuse-checkpoints", action="store_true", help="development: reuse the snapshots in --ckpt-dir")
    ap.add_argument("--no-fresh", action="store_true", help="development: skip the fresh windows")
    ap.add_argument("--no-checkpoint", action="store_true", help="skip the exact (snapshot) windows")
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--no-passby", action="store_true")
    ap.add_argument("--controls", action="store_true", help="run the positive controls instead of the ledger")
    ap.add_argument("--controls-out", default="controls.json")
    ap.add_argument("--runs-o", default=None, help="run directory holding cloud_with_fake_obj.jsonl (default --runs)")
    ap.add_argument("--runs-d", default=None, help="run directory holding doubleT_obstacle.jsonl (default --runs)")
    ap.add_argument("--synthetic-frame", action="append", default=[], metavar="BAG:FRAME",
                    help="a real frame that gets the synthetic controls (repeatable)")
    a = ap.parse_args(argv)
    a.sweep = [int(x) for x in a.sweep.split(",") if x]
    a.synthetic_frames = [(x.rsplit(":", 1)[0], int(x.rsplit(":", 1)[1])) for x in a.synthetic_frame]
    if a.controls:
        cmd_controls(a)
        return
    if not a.out:
        ap.error("--out is required for the ledger")
    cmd_ledger(a)


if __name__ == "__main__":
    main()
