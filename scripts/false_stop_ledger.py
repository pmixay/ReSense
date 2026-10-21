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
    fabric_lat: float = 1.0         # m: half width / height of the tight window for tunnel fabric (no structure found)
    z_half_min: float = 0.4         # m: half height of the window (at least; or half the onset size) ...
    z_pad: float = 0.6              # ... plus this ...
    z_per_m: float = 0.01           # ... plus this per metre travelled (pitch drift)
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
                                         "floor_verified", "age", "curv_step", "curv_knot", "joint_used")
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


def speed_series(rows):
    """Per-frame ego speed (m/s) of a piece and where each value comes from. The detector's own estimate
    (``ego_speed_estimate``; ``ego_speed`` when the caller gave one) exists on 55-75 % of the frames of the
    empty recordings; the gaps are filled by linear interpolation between valid neighbours ('interp'), the
    ends held ('hold'); a piece without any value runs at 0 ('none')."""
    v = np.full(len(rows), np.nan)
    src = np.array(["none"] * len(rows), dtype=object)
    for i, d in enumerate(rows):
        if d.get("ego_speed") is not None:
            v[i], src[i] = float(d["ego_speed"]), "given"
        elif d.get("ego_speed_estimate") is not None:
            v[i], src[i] = float(d["ego_speed_estimate"]), "estimate"
    ok = ~np.isnan(v)
    if not ok.any():
        return np.zeros(len(rows)), np.array(["none"] * len(rows), dtype=object)
    idx = np.flatnonzero(ok)
    filled = np.interp(np.arange(len(rows)), idx, v[idx])
    for i in np.flatnonzero(~ok):
        src[i] = "hold" if i < idx[0] or i > idx[-1] else "interp"
    return np.where(ok, v, filled), src


def transport(rows, i0, center, speeds=None, max_frames=1500, max_range=BAND[1] + 150.0):
    """Walk the ego forward from frame ``i0`` of ``rows`` and carry ``center`` (vehicle frame of frame i0) along.
    Returns a list per frame i >= i0: {i, p (position in that frame's vehicle frame), range (horizontal),
    traveled, src}; stops at the end of the piece, after ``max_frames`` or once the point is behind the
    train (x < -BAND[0]) or far away."""
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
            p = advance(p, s, psi, phi, dpsi, dphi)
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
    not. Returns {(i, j): the smaller of the shares behind and ahead (a side with under three slices is ignored)}."""
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
    keys = set(occ[0]).intersection(*occ[1:])
    return {k: min(o[k] for o in occ) for k in keys}


def classify_window(xyz, track, center, size, traveled, params: ClassifierParams = ClassifierParams()):
    """Classify what stands around ``center`` (the onset's position carried into the vehicle frame of this frame)
    in the cloud ``xyz`` with the re-fitted ``track``:

    * ``in_envelope``: returns inside the strict envelope (|dy| <= SIDE_DY, BED_H < h <= OVERHEAD_H) in the window;
      an empty tunnel has none, so no fabric baseline is needed;
    * else the window's returns outside the envelope that are *not tunnel fabric* (their (dy, h) cell is rarely
      occupied in the slices around): ``side`` (|dy| > SIDE_DY) or ``overhead`` (h > OVERHEAD_H), the larger share;
    * else ``bed_rail`` when the window holds bed or rail returns (h <= BED_H, |dy| <= SIDE_DY), else ``phantom`` (nothing there).
    The window is a box around ``center`` that grows with the distance travelled (odometry drift)."""
    from resense.gauge import corridor_coordinates
    cx, cy, cz = (float(v) for v in center)
    lon = min(params.lon_max, params.lon0 + params.lon_per_m * traveled)
    lat = min(params.lat_max, params.lat0 + params.lat_per_m * traveled)
    zhalf = max(params.z_half_min, 0.5 * float(size[2])) + params.z_pad + params.z_per_m * traveled
    xyz = np.asarray(xyz)
    sel = (np.abs(xyz[:, 0] - cx) <= lon) & (np.abs(xyz[:, 1] - cy) <= lat) & (np.abs(xyz[:, 2] - cz) <= zhalf)
    n_all = int(sel.sum())
    out = {"lon": round(lon, 2), "lat": round(lat, 2), "z_half": round(zhalf, 2), "n_all": n_all, "n_up": 0, "n_bed": 0,
           "n_env": 0, "n_side": 0, "n_over": 0, "n_fabric": 0, "dy_med": None, "h_med": None, "h_range": None,
           "dy_range": None, "ambiguous": [], "class": None}
    if n_all < params.min_any:
        out["class"] = "phantom"
        return out
    dy, h = corridor_coordinates(xyz[sel].astype(np.float32), track)
    out["h_range"] = [round(float(h.min()), 2), round(float(h.max()), 2)]
    up = h > BED_H
    out["n_bed"] = int((~up & (np.abs(dy) <= SIDE_DY)).sum())          # the bed between the walls, not their foot
    out["n_up"] = int(up.sum())
    env = up & (h <= OVERHEAD_H) & (np.abs(dy) <= SIDE_DY)
    out["n_env"] = int(env.sum())
    amb = out["ambiguous"]

    def describe(m):
        out.update({"dy_med": round(float(np.median(dy[m])), 2), "h_med": round(float(np.median(h[m])), 2),
                    "h_range": [round(float(h[m].min()), 2), round(float(h[m].max()), 2)],
                    "dy_range": [round(float(dy[m].min()), 2), round(float(dy[m].max()), 2)]})

    outside = up & ~env
    loc = np.zeros(len(h), dtype=bool)
    fab_mask = np.zeros(len(h), dtype=bool)
    if outside.any():
        occ = fabric_occupancy(xyz, track, cx, params)
        ci = np.floor(dy[outside] / params.fabric_cell).astype(np.int64)
        cj = np.floor(h[outside] / params.fabric_cell).astype(np.int64)
        fab = np.array([occ.get((i, j), 0.0) >= params.fabric_occ for i, j in zip(ci.tolist(), cj.tolist())],
                       dtype=bool)
        loc[np.flatnonzero(outside)[~fab]] = True
        fab_mask[np.flatnonzero(outside)[fab]] = True
        out["n_fabric"] = int(fab.sum())
    over = loc & (h > OVERHEAD_H)
    side = loc & ~over
    out["n_side"], out["n_over"] = int(side.sum()), int(over.sum())
    if out["n_env"] >= params.min_struct:
        out["class"] = "in_envelope"
        describe(env)
        n = out["n_env"]
        other = out["n_side"] + out["n_over"]
        if other >= params.min_struct and other > 0.3 * n:
            amb.append(f"mixed(env {n}, other {other})")
    elif max(out["n_side"], out["n_over"]) >= params.min_struct:
        cls = "side" if out["n_side"] >= out["n_over"] else "overhead"
        out["class"] = cls
        m = side if cls == "side" else over
        describe(m)
        n, other = int(m.sum()), int((over if cls == "side" else side).sum())
        if other >= params.min_struct and other > (1.0 - params.share_min) * (n + other):
            amb.append(f"mixed({cls} {n}, other {other})")
    else:
        # no localized structure: tunnel fabric (wall, platform edge, vault, tray) right at the position?
        tight = outside & fab_mask & (np.abs(dy - (cy - float(track.center_y(np.array([cx]))[0]))) <= params.fabric_lat)
        if int(tight.sum()) >= params.min_struct:
            describe(tight)
            out["on_fabric"] = True
            out["class"] = ("overhead" if out["h_med"] > OVERHEAD_H else
                            "side" if abs(out["dy_med"]) > SIDE_DY else "in_envelope")
            amb.append("on_tunnel_fabric")
            out["n_fabric_tight"] = int(tight.sum())
            return out
        out["class"] = "bed_rail" if out["n_bed"] >= params.min_any else "phantom"
        return out
    if int(out["n_" + {"in_envelope": "env", "side": "side", "overhead": "over"}[out["class"]]]) < params.few_up:
        amb.append("few_points")
    if out["class"] == "side" and abs(abs(out["dy_med"]) - SIDE_DY) < params.margin_dy:
        amb.append("dy_near_limit")
    if out["class"] == "in_envelope" and abs(abs(out["dy_med"]) - SIDE_DY) < params.margin_dy:
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


def replay_job(job):
    """Window replay of one episode: fresh detector, calibration off, from ``lo`` to the onset + 3 frames, and
    (``passby``) up to the last evaluated frame, classifying the structure at the transported positions.
    Returns the reproduction facts, timing, the onset frame's cloud (``save``) and the pass-by results."""
    from resense.config import DetectorConfig
    from resense.detector import Detector
    cfg = DetectorConfig.from_dict(job["cfg"])
    det = Detector(cfg)
    params = ClassifierParams(**job.get("params", {}))
    files, stamps = job["files"], job["stamps"]
    lo, onset, hi = job["lo"], job["onset"], job["hi"]
    eval_at = {q["i"]: q for q in job.get("eval", [])}
    res_out = {"id": job["id"], "frames": 0, "cpu_s": 0.0, "stop_first": None, "stop_frames": [], "passby": []}
    saved = {}
    t0 = time.perf_counter()
    prev_stop = False
    for i, fr in _frames(files, stamps, cfg, lo, hi):
        res = det.process(fr)
        res_out["frames"] += 1
        stop = bool(res.obstacle)
        if stop:
            res_out["stop_frames"].append(i)
            if not prev_stop and res_out["stop_first"] is None and i >= onset - ONSET_TOL_FRAMES:
                nd = min(res.detections, key=lambda x: x.distance)
                res_out["stop_first"] = {"frame": i, "distance": float(nd.distance), "lateral": float(nd.lateral),
                                         "kind": nd.kind, "reason": nd.reason}
        prev_stop = stop
        if i == onset and job.get("save") and res.xyz is not None:
            saved["onset_xyz"] = np.asarray(res.xyz, dtype=np.float32)
            saved["onset_track"] = res.track.to_dict()
        if i in eval_at:
            q = eval_at[i]
            r = classify_window(res.xyz, res.track, q["p"], job["size"], q["traveled"], params)
            r.update({"frame": i, "range": round(q["range"], 1), "traveled": round(q["traveled"], 1),
                      "track": {k: res.track.to_dict().get(k) for k in ("center", "yaw", "curvature", "rail_offset")}})
            res_out["passby"].append(r)
            if job.get("save"):
                saved.setdefault("passby_xyz", {})[i] = np.asarray(res.xyz, dtype=np.float32)
                saved.setdefault("passby_track", {})[i] = res.track.to_dict()
        if job.get("stop_after_onset") and i >= onset + 3 and not eval_at:
            break
    res_out["wall_s"] = time.perf_counter() - t0
    return res_out, saved


def reproduces(row, rep):
    """Does the window replay reproduce the episode: a GO -> STOP onset within ``ONSET_TOL_FRAMES`` of the
    full replay's onset and the nearest detection's distance within ``DIST_TOL_M``?"""
    sf = rep.get("stop_first")
    if sf is None:
        return False, None, None
    df = sf["frame"] - row["frame"]
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
    ax_bev.set_xlim(-9, 9)
    ax_bev.set_ylim(0, xmax)
    ax_side.set_xlim(0, xmax)
    ax_bev.set_title(title, fontsize=7)
    for a in (ax_bev, ax_side):
        a.tick_params(labelsize=6)
    ax_bev.set_xlabel("y (m)", fontsize=6)
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
                        f"pass-by frame {f}: {best['range']:.0f} m from the onset position -> {passby['class']} "
                        f"(n_up={best['n_up']}, dy={best['dy_med']}, h={best['h_med']})", 45.0,
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

def f2_summary(episodes):
    """How many far-onset (>= FAR_ONSET m) episodes fall in each pass-by class, and per class the median
    onset lateral error of the axis (onset lateral minus the structure's measured dy), height, size."""
    out = {"far_threshold_m": FAR_ONSET, "episodes": len(episodes), "far_episodes": 0, "by_class": {},
           "by_class_all": {}}
    for scope, key in ((True, "by_class"), (False, "by_class_all")):
        for e in episodes:
            if scope and not e["far_onset"]:
                continue
            c = (e.get("passby") or {}).get("class") or "unclassified"
            b = out[key].setdefault(c, {"n": 0, "ambiguous": 0, "ids": []})
            b["n"] += 1
            b["ambiguous"] += int(bool((e.get("passby") or {}).get("ambiguous")))
            b["ids"].append(e["id"])
    out["far_episodes"] = sum(1 for e in episodes if e["far_onset"])
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


def make_jobs(pieces, all_rows, episodes, cache, cfg, pre_roll, passby_pre, with_passby, save_dir):
    from scripts.cache_io import load_cache_stamps
    stamps = {}
    pidx = {(p["bag"], p["piece"]): n for n, p in enumerate(pieces)}
    repl, pass_jobs, paths = [], [], {}
    speeds = {n: speed_series(r) for n, r in enumerate(all_rows)}
    for e in episodes:
        n = pidx[(e["recording"], e["piece"])]
        piece, rows = pieces[n], all_rows[n]
        stamps.setdefault(e["recording"], load_cache_stamps(os.path.join(cache, e["recording"])))
        onset = e["piece_frame"]
        base = {"id": e["id"], "cfg": cfg, "files": piece["files"], "stamps": stamps[e["recording"]],
                "onset": onset, "size": e["size"]}
        repl.append({**base, "lo": max(0, onset - pre_roll), "hi": min(len(rows) - 1, onset + 3),
                     "stop_first_only": True, "stop_after_onset": True, "save": save_dir is not None,
                     "onset_abs": e["frame"]})
        if not with_passby:
            continue
        path = transport(rows, onset, e["center"], speeds[n])
        fr, closest, mode = band_frames(path)
        paths[e["id"]] = (path, fr, closest, mode)
        if fr:
            first, lastf = min(q["i"] for q in fr), max(q["i"] for q in fr)
            pass_jobs.append({**base, "onset": first, "lo": max(0, first - passby_pre), "hi": lastf, "eval": fr,
                              "save": save_dir is not None, "stop_after_onset": False})
    return repl, pass_jobs, paths


def run_pool(fn, jobs, n_jobs):
    if n_jobs <= 1:
        return [fn(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        return list(ex.map(fn, jobs, chunksize=1))


def cmd_ledger(a):
    t_start = time.time()
    bags = [b for b in a.bags.split(",") if b]
    pieces, all_rows = load_all(a.runs, a.windows, bags)
    if not pieces:
        raise SystemExit(f"no run files for {bags} in {a.runs}")
    episodes = build_rows(pieces, all_rows)
    cfg = window_config(a.runs, a.set)
    os.makedirs(a.out, exist_ok=True)
    png_dir = os.path.join(a.out, "png")
    save = png_dir if not a.no_png else None
    if save:
        os.makedirs(save, exist_ok=True)
    repl, pass_jobs, paths = make_jobs(pieces, all_rows, episodes, a.windows, cfg, a.pre_roll, a.passby_pre,
                                       not a.no_passby, save)
    # the onset window of an episode that the pass-by also needs to draw is saved there; the reproduction
    # window of the picture runs again only for the onset frame (cheap: it is the same replay)
    t0 = time.time()
    rep_out = run_pool(replay_job, repl, a.jobs)
    wall_repro = time.time() - t0
    t0 = time.time()
    pas_out = run_pool(replay_job, pass_jobs, a.jobs) if pass_jobs else []
    wall_pass = time.time() - t0
    rep = {r[0]["id"]: r for r in rep_out}
    pas = {r[0]["id"]: r for r in pas_out}
    n_ok = 0
    for e in episodes:
        r, saved = rep[e["id"]]
        ok, df, dd = reproduces(e, r)
        n_ok += int(ok)
        e["window"] = {"reproduced": ok, "onset_delta_frames": df, "distance_delta_m": dd,
                       "first_stop": r["stop_first"], "frames_replayed": r["frames"], "wall_s": round(r["wall_s"], 2)}
        if a.no_passby:
            continue
        path, fr, closest, mode = paths[e["id"]]
        pb = {"closest_range_m": None if closest is None else round(closest, 1), "frames": [], "mode": mode}
        if e["id"] in pas:
            pb["frames"] = pas[e["id"]][0]["passby"]
            cls, agree, why = episode_class(pb["frames"], ClassifierParams())
            if mode == "nearest":
                why = [*why, f"beyond_band(closest {pb['closest_range_m']} m)"]
        else:
            cls, agree, why = "unreached", 0.0, [f"closest_range_{pb['closest_range_m']}"]
        pb.update({"class": cls, "agreement": round(agree, 2), "ambiguous": bool(why), "ambiguous_why": why,
                   "traveled_m": round(path[-1]["traveled"], 1), "speed_sources": sorted({q["src"] for q in path}),
                   "interp_share": round(float(np.mean([q["src"] in ("interp", "hold", "none") for q in path[1:]]))
                                         if len(path) > 1 else 0.0, 2)})
        e["passby"] = pb
        if save:
            ps = pas[e["id"]][1] if e["id"] in pas else {}
            sv = {**saved, **ps}
            if "onset_xyz" in sv:
                render_episode(os.path.join(png_dir, e["id"].replace(":", "_") + ".png"), e, sv,
                               {**pb, "path": path} if pb["frames"] else pb)
    meta = {"schema": SCHEMA, "created": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            "runs": os.path.abspath(a.runs), "bags": bags, "pre_roll": a.pre_roll, "passby_pre_roll": a.passby_pre,
            "tolerance": {"onset_frames": ONSET_TOL_FRAMES, "distance_m": DIST_TOL_M},
            "thresholds": {"side_dy": SIDE_DY, "overhead_h": OVERHEAD_H, "bed_h": BED_H, "band_m": list(BAND),
                           "far_onset_m": FAR_ONSET},
            "classifier": asdict(ClassifierParams()), "jobs": a.jobs}
    summary = {"episodes": len(episodes), "reproduced": n_ok,
               "frames_replayed_repro": sum(rep[e["id"]][0]["frames"] for e in episodes),
               "wall_repro_s": round(wall_repro, 1), "wall_passby_s": round(wall_pass, 1),
               "wall_total_s": round(time.time() - t_start, 1)}
    if not a.no_passby:
        summary["f2"] = f2_summary(episodes)
    doc = {"meta": meta, "summary": summary, "episodes": episodes}
    with open(os.path.join(a.out, "ledger.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    print(json.dumps(summary, indent=1))
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True, help="per-frame JSONL directory of a gate / eval_real run")
    ap.add_argument("--windows", required=True, help="frame cache directory (<cache>/<bag>/*.npy)")
    ap.add_argument("--out", required=True, help="output directory: ledger.json and png/")
    ap.add_argument("--bags", default=",".join(EMPTY_BAGS + [RIDE]))
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--pre-roll", type=int, default=PRE_ROLL)
    ap.add_argument("--passby-pre", type=int, default=60, help="pre-roll frames of the pass-by replay")
    ap.add_argument("--set", action="append", default=[], help="extra section.key=value override of the window config")
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--no-passby", action="store_true")
    a = ap.parse_args(argv)
    cmd_ledger(a)


if __name__ == "__main__":
    main()
