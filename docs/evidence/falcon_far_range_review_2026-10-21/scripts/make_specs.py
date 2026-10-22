#!/usr/bin/env python3
"""Scene specs of the review (generalisation tests the author did not run). Writes <dir>/<name>.json and
<dir>/index.json = [[name, frames], ...]."""
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
ALL = ["centre", "left", "right", "farright", "high"]
PERSON = json.loads(Path("/home/user/ReSense/docs/evidence/falcon_long_range_2026-10-19/person_model.json").read_text())
PF = {k: PERSON[k] for k in ("size", "bottom", "fill", "intensity")}
PF["rho"] = {"split": 0.8, "lower": 0.05, "upper": 0.30}
REAL = "2400:3300"          # the main person 191 -> ~100 m
EMPTY = (1290, 1440)        # the matrix' empty window, 150 frames
idx = []


def put(name, spec, frames):
    (out / f"{name}.json").write_text(json.dumps(spec, indent=1))
    idx.append([name, frames])


put("plain_real", {}, REAL)
# 1. curves of the whole scene (track, structures, person), outer wall face 2.0 m outside: a curve right after the last
#    confirmed bin (142 / 172 m), inside the 195-245 m gap, and earlier
for xc in (120, 150, 175, 200, 245):
    for R, dirs in ((300, (1, -1)), (1000, (1,))):
        for d in dirs:
            put(f"curve_all_xc{xc}_R{R}_d{d:+d}", {"warp": [{"xc": xc, "R": R, "dir": d, "groups": ALL, "outer_wall": 2.0}]}, REAL)
# 2. one straight boundary (left posts stay straight), track + right row + person curve right, away from it
for xc in (100, 130, 160):
    put(f"left_straight_xc{xc}_R600", {"warp": [{"xc": xc, "R": 600, "dir": -1, "groups": ["centre", "right", "farright", "high"]}]}, REAL)
# 3. the right column row belongs to another track: it stays straight, the track + left side + person curve left
for xc in (100, 130, 160):
    put(f"row_other_track_xc{xc}_R600", {"warp": [{"xc": xc, "R": 600, "dir": 1, "groups": ["centre", "left", "high"]}]}, REAL)
# 4. both boundaries straight, only the track and the person curve (a turnout); structures in the way removed
for xc in (120, 150, 195):
    for R in (300, 1000):
        for d in (1, -1):
            put(f"turnout_xc{xc}_R{R}_d{d:+d}", {"warp": [{"xc": xc, "R": R, "dir": d, "groups": ["centre"], "clear_envelope": 1.7}]}, REAL)
# 5. the same with the structures 1.5 m further out on both sides (wide boundaries inside the 1.2-4 m band)
for xc in (100, 130):
    for d in (1, -1):
        put(f"wide_turnout_xc{xc}_R600_d{d:+d}", {"shift": [{"groups": ["left"], "dy": 1.5, "x0": 50}, {"groups": ["right"], "dy": -1.5, "x0": 50}],
                                                  "warp": [{"xc": xc, "R": 600, "dir": d, "groups": ["centre"], "clear_envelope": 1.7}]}, REAL)
# 6. skewed structures (straight track, structures diverge at slope s from 50 m)
for s in (0.003, 0.006):
    put(f"skew_structures_{s}", {"skew": [{"groups": ["left", "right", "farright", "high"], "slope": s, "x0": 50}]}, REAL)
# 7. a parallel but offset second side (the right row moved), straight track; and a step of the row from 150 m
for dy in (0.4, -0.4, 0.8):
    put(f"row_offset_{dy:+.1f}", {"shift": [{"groups": ["right"], "dy": dy, "x0": 50}]}, REAL)
put("row_step_0.45_from150", {"shift": [{"groups": ["right"], "dy": 0.45, "x0": 150}]}, REAL)
# 8. objects on a curved continuation (the empty window, a static person on the warped track), 120-160 m,
#    with a curve from 100 m (R 300 / 1000) of everything (outer wall) and the plain straight control
for D in (120, 140, 160):
    inj = {"seed": 7 + D, "k_pod": 3.0, "targets": [dict(PF, **{"from": EMPTY[0], "to": EMPTY[1], "dist": float(D), "name": f"person{D}"})]}
    put(f"obj{D}_straight", {"inject": inj}, f"{EMPTY[0]}:{EMPTY[1]}")
    for xc, R, d in ((100, 300, 1), (100, 1000, 1), (100, 300, -1), (130, 600, 1)):
        put(f"obj{D}_curve_xc{xc}_R{R}_d{d:+d}", {"inject": inj, "warp": [{"xc": xc, "R": R, "dir": d, "groups": ALL, "outer_wall": 2.0}]},
            f"{EMPTY[0]}:{EMPTY[1]}")
# 9. gauge-edge (lateral) static targets, straight track: the strict gauge shrinks by sigma under the far axis
for D in (60, 80, 100, 120, 140):
    for lat in (0.6, 0.75, 0.9):
        inj = {"seed": 11 + D, "k_pod": 3.0, "targets": [dict(PF, **{"from": EMPTY[0], "to": EMPTY[1], "dist": float(D), "lat": lat, "name": f"edge{D}_{lat}"})]}
        put(f"edge{D}_lat{lat}", {"inject": inj}, f"{EMPTY[0]}:{EMPTY[1]}")
# 10. a moving train (the scene of empty frame 1400 scrolled towards the sensor at v), a curve whose start is at 230 m
#     at the first frame (moves with the scene), a standing person on the curved track starting at 200 m
for v in (0, 10, 25, 30):
    n = 60
    inj = {"seed": 99, "k_pod": 3.0, "targets": [dict(PF, **{"from": 1290, "to": 1290 + n, "dist": 200.0, "name": "person200"})]}
    for R in (300,):
        put(f"moving_v{v}_curve230_R{R}", {"inject": inj, "scroll": {"v": v, "base_frame": 1400, "x_from": 50.0},
                                           "warp": [{"xc": 230, "R": R, "dir": 1, "groups": ALL, "outer_wall": 2.0}]}, f"1290:{1290 + n}")
    put(f"moving_v{v}_straight", {"inject": inj, "scroll": {"v": v, "base_frame": 1400, "x_from": 50.0}}, f"1290:{1290 + n}")
(out / "index.json").write_text(json.dumps(idx, indent=0))
print(len(idx), "specs")
