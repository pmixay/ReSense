"""Full paired H2 route and low-object preservation; constructed coordinate controls."""
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

if sys.argv[1] == "launch":
    out = HERE / "run-004"
    out.mkdir(exist_ok=False)
    cmd = json.loads((HERE / "run-001/launch.json").read_text())["argv"]
    cmd[cmd.index("--name") + 1] = "rs-h4-selected-independent-c9aea87-004"
    cmd[-1] = "/review/paired_h2.py"
    cmd.append("worker")
    r = subprocess.run(cmd, capture_output=True, text=True)
    (out / "launch.json").write_text(json.dumps(dict(argv=cmd, stdout=r.stdout, stderr=r.stderr,
                                                  returncode=r.returncode), indent=2) + "\n")
    print(r.stdout + r.stderr)
    raise SystemExit(r.returncode)

if sys.argv[1] == "worker":
    for name in ("selected", "sealed"):
        root = Path("/work") / name
        r = subprocess.run(["python3", __file__, name], cwd=root,
            env={**os.environ, "PYTHONPATH": str(root), "RESENSE_REPO": str(root)},
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (HERE / ("run-004/" + name + ".txt")).write_text(r.stdout)
        assert r.returncode == 0, r.stdout
    a, b = [json.loads((HERE / ("run-004/" + n + ".json")).read_text()) for n in ("selected", "sealed")]
    assert [r["input_sha256"] for r in a["rows"]] == [r["input_sha256"] for r in b["rows"]]
    assert all(not r["clusters"] for r in b["rows"])
    assert any(r["clusters"] for r in a["rows"])
    (HERE / "run-004/paired.json").write_text(json.dumps(dict(paired_inputs=len(a["rows"]),
        sealed_accepted=0, selected_accepted=sum(bool(r["clusters"]) for r in a["rows"]),
        labelled_support_only=True, low_duplicate_controls=a["low_duplicate"], passed=True), indent=2) + "\n")
    print("Paired H2 and low-duplicate checks passed")
    raise SystemExit(0)

import hashlib
import itertools
import numpy as np
import resense
from resense import _native, clustering as cl
from resense.config import DetectorConfig
from resense.detector import Candidates, Detector

MODE = sys.argv[1]
assert Path(resense.__file__).resolve() == Path.cwd() / "resense/__init__.py" and _native.enabled()
cfg = DetectorConfig().cluster
X, H = np.meshgrid(np.arange(102., 137., .31), np.arange(.13, 2.95, .21))
wall = np.column_stack([X.ravel(), np.full(X.size, 1.88), H.ravel()])
rows = []
for n, span, sign, echoes in itertools.product((7, 8, 9), (.099999, .1, .100001), (-1, 1), (1, 2)):
    y = np.where(np.arange(n) % 2, 118. * np.tan(np.arctan2(.31, 118.) + np.radians(span)), .31)
    part = np.column_stack([np.full(n, 118.), y, .23 + .25 * np.arange(n)])
    xyz = np.concatenate([wall, np.repeat(part, echoes, axis=0)]) * [1., sign, 1.]
    strict = (np.abs(xyz[:, 1]) < 1.05) & (xyz[:, 2] > 0) & (xyz[:, 2] < 3.)
    cs = cl.find_clusters(xyz, np.full(len(xyz), 20.), xyz[:, 1], xyz[:, 2], strict, cfg)
    if MODE == "selected":
        for c in cs:
            assert c.cut and not c.spared and c.n >= 8 and c.n_gauge > 0
            assert all(i >= len(wall) for i in c.points_idx)
            assert np.ptp(np.arctan2(xyz[c.points_idx, 1], xyz[c.points_idx, 0])) >= np.radians(.1)
    rows.append(dict(n=n, span=span, side=sign, echoes=echoes,
        input_sha256=hashlib.sha256(xyz.tobytes()).hexdigest(),
        clusters=[dict(n=c.n, n_gauge=c.n_gauge, zone=c.zone, reason=c.reason,
                       point_indices=c.points_idx.tolist(), cut=getattr(c, "cut", False)) for c in cs]))

low_results = []
if MODE == "selected":
    det = Detector()
    empty = Candidates(xyz=np.zeros((0,3), np.float32), dy=np.zeros(0), h=np.zeros(0),
        in_gauge=np.zeros(0, bool), intensity=np.zeros(0, np.float32), idx=np.zeros(0, np.int64), low=np.zeros(0, bool))
    def c(kind, reason):
        height = .1 if kind == "low" else 1.
        center = np.array([43.2, .2, height])
        return cl.Cluster(points_idx=np.arange(12), n=12, n_raw=12, centroid=center,
            bbox_min=np.array([43., 0., .05]), bbox_max=np.array([43.4, .4, .15 if kind == "low" else 1.95]),
            distance=43., lateral=.2, height_min=.05, height_max=.15 if kind == "low" else 1.95,
            intensity=20., n_expected=12., score=1., n_gauge=12, kind=kind,
            zone="warning" if reason else "gauge", reason=reason, cut=kind != "low")
    for reason in ("column", "beyond_axis", "floating", "doubt", ""):
        low, corridor = c("low", ""), c("", reason)
        keep = det._not_part_of_corridor_objects([low], [], [corridor], empty)
        assert bool(keep) == bool(reason)
        low_results.append(dict(reason=reason, independent_low_preserved=bool(keep)))

(HERE / ("run-004/" + MODE + ".json")).write_text(json.dumps(dict(rows=rows, low_duplicate=low_results,
    imported=resense.__file__, native=_native.status(), head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()), indent=2) + "\n")
