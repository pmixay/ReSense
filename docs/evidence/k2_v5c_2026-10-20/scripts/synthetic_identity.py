"""Off identity on synthetic scenes: run the entry-curve and station scenes of the tests through the Detector of the
checkout given as argv[1] with the K2 variant argv[2] (off, B, C15) and print every frame as a JSON line.
    python -I synthetic_identity.py <checkout> off > off.jsonl"""
import json, sys
repo, variant = sys.argv[1], sys.argv[2]
sys.path.insert(0, repo)
import numpy as np
from dataclasses import replace
from resense.detector import Detector
from resense.config import DetectorConfig
from resense.frame import Frame
from tests.test_wall_drift import _entry_scene
from tests.test_late_candidates import _station_scene, _box_surface, AXIS_Y, RAIL_HEAD_Z
assert __import__('resense').__file__.startswith(repo), __import__('resense').__file__
V = {"off": {}, "B": dict(axis_joint_fit=True, axis_joint_range=False, axis_joint_min_curvature=1e-4, axis_joint_reach_cap=True)}
V["C15"] = dict(V["B"], axis_joint_reach_dual=15.0)
def person(x, y, n=400, seed=1):
    r = np.random.default_rng(seed)
    return np.stack([x + r.uniform(0, 0.4, n), y + r.uniform(-0.25, 0.25, n), -1.5 + r.uniform(0.3, 1.8, n)], 1)
scenes = []
for j in (0.0, 1 / 60000, 1 / 100000):
    xyz, yt = _entry_scene(j=j, inner_to=70.0, x0=10.0)
    for px in (None, 60.0, 100.0, 150.0, 158.0):
        scenes.append((f"entry j={j:.2e} p={px}", xyz if px is None else np.concatenate([xyz, person(px, float(yt(px)))])))
st = _station_scene()
def box(x0, y0, length, width, height, z0=-1.5):
    return _box_surface(x0, length, y0 - AXIS_Y, z0 - RAIL_HEAD_Z, height, width)
for d in (25.0, 60.0, 83.0):
    scenes.append((f"station p={d}", np.concatenate([st, box(82.9, 1.9, 2.2, 0.4, 1.25), box(d, 0.3, 0.4, 0.5, 1.7)])))
cfg = DetectorConfig()
cfg.track = replace(cfg.track, **V[variant])
for name, pts in scenes:
    pts = pts.astype(np.float32)
    det = Detector(cfg)
    for k in range(10):
        r = det.process(Frame(xyz=pts, intensity=np.full(len(pts), 30.0, np.float32), stamp=0.1 * k))
        t = r.track.to_dict()
        print(json.dumps({"scene": name, "k": k, "obstacle": r.obstacle, "warning": r.warning, "nearest": r.nearest_distance,
                          "dets": [(round(c.distance, 3), round(c.lateral, 3), c.zone, c.reason) for c in r.detections],
                          "warns": [(round(c.distance, 3), round(c.lateral, 3), c.zone, c.reason) for c in r.warnings],
                          "track": t, "clear": r.clear_distance}, sort_keys=True))
