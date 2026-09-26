"""Rail heads just ahead of a standing train at a fresh start (26.09, P3 rail start;
docs/evidence/results/p3_rail_start_2026-09-26.json, EXPERIMENTS §1k).

The open finding of the start-up census (EXPERIMENTS §1j): from the gate's piece-2 cut of the ride
(``new_data_55_0013``) a fresh detector STOPped at 2.9-3.1 m on frames 12-15 on a low track made
of the rail heads 3.0-3.6 m ahead, 3-12 cm above a young model's rail-head plane. The 4 m rule
(``tracking.low_min_seen_distance``) removed it but never reported a real low object that stays
within 4 m. ``lowobj.rail_start_within`` (``lowobj.mark_rail_line``) instead marks a low cluster
near the train as rail geometry only when it reaches a rail line, is narrow across the track and
does not rise above the rail head's own returns along the track; the tracker then withholds a new
report of such a track that was never matched at 4 m or farther. Every blind-zone case of the
4 m rule stays a STOP on its usual frame.
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import DetectorConfig, LowObjectConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.lowobj import mark_rail_line
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
from resense.tracking import Tracker

ROOT = Path(__file__).resolve().parents[1]
FLOOR_Z = -1.5                 # synthetic_tunnel_frame default: the bed
RAIL_HEAD_Z = FLOOR_Z + 0.18   # the synthetic rails are 0.18 m tall
RIDE = "/data/cache/new_data"


def _on(within: float = 4.0) -> DetectorConfig:
    cfg = DetectorConfig()
    cfg.lowobj.rail_start_within = within
    return cfg


def test_rail_start_defaults():
    """Off by default (0), with its sub-parameters margin 0.05 m, lateral 0.10 m, width 0.45 m, in
    the dataclass, the YAML and the ROS copy."""
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        low = cfg.lowobj
        assert (low.rail_start_within, low.rail_start_margin, low.rail_start_lateral,
                low.rail_start_max_width) == (0.0, 0.05, 0.10, 0.45)


# --- the marking itself, on hand-built points ---------------------------------------------------

def _rail_scene(object_top: float = None, across: bool = False, continuation: bool = True, x_obj: float = 3.0):
    """Frame points in track coordinates (X, dy, h) and the low cluster: the left rail head a line
    at dy -0.86, 0.15 m above the (wrong) modelled plane from 2.8 m on; the low cluster the rail's
    flank returns 3.0-3.6 m ahead at 0.03-0.11 m across dy -0.98 ... -0.80 (the finding's shape);
    or instead the lower faces of an object standing on the rail at ``x_obj`` whose top face is at
    ``object_top`` (above the envelope floor: corridor points, not in the cluster), or of an object
    lying across the rail (0.6 m wide, top 0.28); ``continuation`` False: the rail line only as far
    as the cluster."""
    rng = np.random.default_rng(3)
    X, dy, h = [], [], []
    xs = np.arange(2.8, 6.0 if continuation else 3.7, 0.02)
    for d in (-0.88, -0.86, -0.84):
        X.append(xs)
        dy.append(np.full(xs.size, d))
        h.append(0.15 + rng.normal(0, 0.005, xs.size))
    n = 40
    if across:
        low = [rng.uniform(x_obj, x_obj + 0.4, n), rng.uniform(-1.05, -0.45, n), rng.uniform(0.05, 0.11, n)]
        top = [rng.uniform(x_obj, x_obj + 0.4, n), rng.uniform(-1.05, -0.45, n), np.full(n, 0.28)]
    elif object_top is not None:
        low = [rng.uniform(x_obj, x_obj + 0.3, n), rng.uniform(-1.0, -0.72, n), rng.uniform(0.03, 0.11, n)]
        top = [rng.uniform(x_obj, x_obj + 0.3, n), rng.uniform(-1.0, -0.72, n), np.full(n, object_top)]
    else:
        low = [rng.uniform(3.0, 3.6, n), rng.uniform(-0.98, -0.80, n), rng.uniform(0.03, 0.11, n)]
        top = None
    first = sum(a.size for a in X)
    for k in range(3):
        (X, dy, h)[k].append(low[k])
    idx = np.arange(first, first + n)
    if top is not None:
        for k in range(3):
            (X, dy, h)[k].append(top[k])
    X, dy, h = (np.concatenate(a) for a in (X, dy, h))
    pts = np.stack([X, dy, h], axis=1)[idx]
    c = Cluster(points_idx=idx, n=n, n_raw=n, centroid=pts.mean(axis=0), bbox_min=pts.min(axis=0),
                bbox_max=pts.max(axis=0), distance=float(pts[:, 0].min()), lateral=float(pts[:, 1].mean()),
                height_min=float(pts[:, 2].min()), height_max=float(pts[:, 2].max()), intensity=10.0,
                n_expected=10.0, score=1.0, zone="gauge", n_gauge=n, kind="low")
    return c, X, dy, h


def _marked(c, X, dy, h, within: float = 4.0) -> bool:
    cfg = LowObjectConfig(rail_start_within=within)
    mark_rail_line([c], X, dy, h, cfg, rails_spacing=1.59, range_min=3.0)
    return c.rail_line


def test_rail_flank_near_the_train_is_rail_geometry():
    """The finding's shape: the rail head's flank 3.0-3.6 m ahead, under the rail head's own line
    that continues along the track: marked."""
    assert _marked(*_rail_scene())


@pytest.mark.parametrize("case,kw", [
    ("organizers' 0.10 m object on the rail head", {"object_top": 0.25}),
    ("the same object at 3.8 m", {"object_top": 0.25, "x_obj": 3.8}),
    ("a 0.07 m object on the rail head", {"object_top": 0.22}),
    ("object lying across the rail, 0.6 m wide", {"across": True}),
    ("no rail line beyond the cluster", {"continuation": False}),
])
def test_objects_near_the_train_are_not_rail_geometry(case, kw):
    """Anything standing on the rail rises above its line (the 0.10 m object: 0.10 m), an object
    across a rail is wider than 0.45 m, and without the rail line continuing along the track
    nothing is marked."""
    assert not _marked(*_rail_scene(**kw)), case


def test_marking_only_near_the_train_and_only_when_on():
    c, X, dy, h = _rail_scene()
    assert not _marked(c, X, dy, h, within=3.0)          # the cluster starts at 3.0 m: not nearer
    c, X, dy, h = _rail_scene()
    assert not _marked(c, X, dy, h, within=0.0)          # off
    c, X, dy, h = _rail_scene()
    c.kind = ""                                          # a corridor cluster is never marked
    assert not _marked(c, X, dy, h)


# --- the tracker ----------------------------------------------------------------------------------

def _low(x: float, rail: bool, lateral: float = -0.88) -> Cluster:
    c = np.array([x + 0.2, lateral, -1.2])
    return Cluster(points_idx=np.arange(3), n=10, n_raw=20, centroid=c, bbox_min=c - [0.2, 0.1, 0.04],
                   bbox_max=c + [0.2, 0.1, 0.04], distance=x, lateral=lateral, height_min=0.04, height_max=0.12,
                   intensity=20.0, n_expected=8.0, score=1.0, zone="gauge", n_gauge=5, kind="low", rail_line=rail)


def _reported(xs, rails, within: float = 4.0) -> list:
    tr = Tracker(DetectorConfig().tracking)
    out = []
    for x, r in zip(xs, rails):
        tr.update([_low(x, r)], frame_dt=0.1, rail_within=within)
        out.append(any(t.reported for t in tr.tracks))
    return out


FINDING = [3.0, 3.0, 3.6, 3.1, 3.1, 3.0, 3.0, 3.2, 3.1, 3.0]


def test_tracker_withholds_the_rail_track_near_the_train():
    """The finding's track (3.0-3.6 m, every cluster rail geometry): never reported with the rule;
    reported from its 5th hit without it, or when its clusters are not rail geometry."""
    n = len(FINDING)
    assert _reported(FINDING, [True] * n) == [False] * n
    assert _reported(FINDING, [True] * n, within=0.0) == [False] * 4 + [True] * (n - 4)
    assert _reported(FINDING, [False] * n) == [False] * 4 + [True] * (n - 4)


def test_tracker_one_object_frame_reports_and_a_reported_track_stays():
    """Safety first: a frame on which the cluster is not rail geometry reports the track at once
    (it has the hits), and a reported track is not withdrawn when its cluster later looks like rail."""
    rails = [True] * 5 + [False] + [True] * 4
    assert _reported(FINDING, rails) == [False] * 5 + [True] * 5


def test_tracker_keeps_an_object_approached_from_afar():
    """A low object first matched far away (set O's are matched at >= 10 m) is reported all the
    way in even if its clusters under 4 m looked like rail: only tracks never matched at >= 4 m are
    affected."""
    xs = list(np.linspace(12.0, 2.5, 20))
    rails = [x < 4.0 for x in xs]
    assert _reported(xs, rails) == _reported(xs, rails, within=0.0) == [False] * 4 + [True] * 16


# --- the real finding (needs the ride cache) --------------------------------------------------------

@pytest.mark.skipif(not os.path.isdir(RIDE), reason="the ride cache /data/cache/new_data is not here")
def test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop():
    """The judge's case: a fresh detector from ``new_data_55_0013`` (the gate's piece-2 cut), 40
    frames. Off: STOP on frames 12-15 at 2.9-3.1 m (low). On: no STOP."""
    from resense.frame import frame_from_compact
    from resense.io import _natural_key, load_cache_stamps
    files = sorted(glob.glob(os.path.join(RIDE, "*.npy")), key=_natural_key)
    i0 = [os.path.basename(f) for f in files].index("new_data_55_0013.npy")
    stamps = load_cache_stamps(RIDE)
    runs = {}
    for within in (0.0, 4.0):
        cfg = _on(within)
        det = Detector(cfg)
        stops = []
        for k, f in enumerate(files[i0:i0 + 40]):
            stem = os.path.splitext(os.path.basename(f))[0]
            r = det.process(frame_from_compact(np.load(f), cfg.sensor, stamp=stamps.get(stem, 0.1 * k), frame_id=stem))
            if r.obstacle:
                stops.append((k, r.detections[0].kind, round(r.nearest_distance, 1)))
        runs[within] = stops
    assert [k for k, _, _ in runs[0.0]] == [12, 13, 14, 15]
    assert all(kind == "low" and 2.8 <= d <= 3.2 for _, kind, d in runs[0.0])
    assert runs[4.0] == []


# --- every blind-zone case of the 4 m rule stays a STOP (ray-cast) -------------------------------

_frames: dict = {}


def _cast(spec, seed):
    key = (None if spec is None else (spec.size, round(spec.distance, 4), spec.lateral, spec.base_z), seed)
    if key not in _frames:
        fr, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(seed), specs=[] if spec is None else [spec])
        _frames[key] = fr
    return _frames[key]


def _object(name: str, d: float) -> ObstacleSpec:
    if name == "organizers":      # 300 x 300 x 100 mm on a rail head
        return ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=d, lateral=0.8, base_z=RAIL_HEAD_Z)
    if name == "across":          # lying across a rail on the bed
        return ObstacleSpec(kind="box", size=(0.4, 0.6, 0.31), distance=d, lateral=-0.8, base_z=FLOOR_Z)
    return ObstacleSpec(kind="box", size=(0.5, 0.5, 0.5), distance=d, lateral=0.8, base_z=FLOOR_Z)


def _stops(specs) -> list:
    det = Detector(_on())
    out = []
    for k, (spec, seed) in enumerate(specs):
        fr = _cast(spec, seed)
        out.append(det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k)).obstacle)
    return [k for k, s in enumerate(out) if s]


@pytest.mark.synthetic
@pytest.mark.parametrize("name", ["organizers", "across", "box0.5_across"])
@pytest.mark.parametrize("d", [3.0, 3.5, 3.9])
def test_blind_zone_fresh_start_at_a_standing_train_stops(name, d):
    """An object 3.0-3.9 m ahead of a standing train from a fresh start (5 noise realisations
    cycled): STOP from frame 4 on every frame, with the rule on (as without it)."""
    assert _stops([(_object(name, d), k % 5) for k in range(30)]) == list(range(4, 30))


@pytest.mark.synthetic
@pytest.mark.parametrize("name", ["organizers", "across"])
def test_blind_zone_object_falling_onto_the_track_stops(name):
    """30 empty frames, then the object appears 3.5 m ahead of the standing train: STOP from its
    5th frame on."""
    specs = [(None, k % 5) for k in range(30)] + [(_object(name, 3.5), k % 5) for k in range(30)]
    assert _stops(specs) == list(range(34, 60))


@pytest.mark.synthetic
@pytest.mark.parametrize("name,v,n", [("organizers", 0.5, 21), ("organizers", 1.0, 9),
                                      ("across", 0.5, 23), ("across", 1.0, 10)])
def test_blind_zone_object_appearing_ahead_of_a_slow_train_stops(name, v, n):
    """20 empty frames, then the object appears 3.9 m ahead of a train at 0.5 / 1.0 m/s, which
    approaches it to 2.5 m: STOP from its 5th frame, as without the rule."""
    specs = [(None, k % 5) for k in range(20)]
    k = 0
    while 3.9 - k * v * 0.1 >= 2.5 - 1e-9:
        specs.append((_object(name, 3.9 - k * v * 0.1), k % 5))
        k += 1
    assert _stops(specs) == list(range(24, 24 + n))
