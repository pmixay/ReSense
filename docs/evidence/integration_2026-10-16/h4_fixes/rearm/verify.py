"""Run inside the clean clone, saving identity, tests, and targeted physical controls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path("/tmp/repo")
OUT = Path("/out")
assert ROOT.is_dir() and OUT.is_dir()
assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == os.environ["H4_SOURCE_COMMIT"]
assert not subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
build = subprocess.run(["bash", "scripts/build_native.sh"], capture_output=True, text=True)
(OUT / "native-build.txt").write_text(build.stdout + build.stderr)
assert build.returncode == 0

import open3d
import resense
from resense import _native
from resense.config import DetectorConfig
from resense.tracking import Tracker

assert Path(resense.__file__).resolve() == ROOT / "resense/__init__.py"
assert _native.AVAILABLE and _native.enabled() and _native.LIBRARY.endswith(".so")
assert Path(_native.LIBRARY).parent == ROOT / "resense"
identity = dict(source_commit=os.environ["H4_SOURCE_COMMIT"], import_path=resense.__file__,
                open3d=open3d.__version__, native_status=_native.status(), native_library=_native.LIBRARY,
                native_sha256=hashlib.sha256(Path(_native.LIBRARY).read_bytes()).hexdigest(),
                tracking_sha256=hashlib.sha256((ROOT / "resense/tracking.py").read_bytes()).hexdigest(),
                clustering_sha256=hashlib.sha256((ROOT / "resense/clustering.py").read_bytes()).hexdigest(),
                config_sha256=hashlib.sha256((ROOT / "resense/config.py").read_bytes()).hexdigest())
(OUT / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")

selected = ["test_h4_spare_rearm", "test_explained_run", "test_column_free_top", "test_ego_veto",
            "test_fresh_stop_evidence", "test_history_robustness", "test_history_stress_acceptance",
            "test_stop_keep", "test_reseed_safety", "test_near_escalation", "test_track_opinion",
            "test_native", "test_modules"]
result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-ra", "--junitxml=/out/pytest.xml"] +
                        ["tests/" + name + ".py" for name in selected], capture_output=True, text=True)
(OUT / "pytest.txt").write_text(result.stdout + result.stderr)
print(result.stdout + result.stderr, flush=True)

# Use the reviewer's committed physical caster, without its old source-identity restriction.
sys.path.insert(0, str(ROOT / "docs/evidence/integration_2026-10-16/h4_safety"))
from components import cast, clusters
from common import track_desc

cfg = DetectorConfig()
physical = []
for label, top in [("case44_free", 2.72), ("genuine_column_to_vault", 4.12)]:
    boxes = [([66.77, 0.45, -1.83], [67.23, 0.91, top - 1.83])]
    xyz, ring, labels = cast(boxes)
    cs = clusters(xyz, ring, cfg)
    absent = labels == 0
    missing = clusters(xyz[absent], ring[absent], cfg)
    tracker = Tracker(cfg.tracking)
    frames = []
    for frame in range(20):
        use = copy.deepcopy(missing if frame in (9, 10) else cs)
        tracker.update(use, frame_dt=0.1)
        row = dict(frame=frame, tracks=[dict(**track_desc(t),
                   provisional_explained_hist=getattr(t, "provisional_explained_hist", None)) for t in tracker.tracks],
                   stop_ids=[t.id for t in tracker.tracks if t.reported and t.zone == "gauge"])
        frames.append(row)
    physical.append(dict(label=label, top=top, object_returns=int((labels == 1).sum()),
                         initial=[dict(n=c.n, n_gauge=c.n_gauge, ring_count=c.ring_count,
                                       spared=c.spared, reason=c.reason, zone=c.zone) for c in cs],
                         stop_frames=[f["frame"] for f in frames if f["stop_ids"]], frames=frames))
(OUT / "physical.json").write_text(json.dumps(physical, indent=2) + "\n")
print(json.dumps([dict(label=p["label"], stop_frames=p["stop_frames"]) for p in physical]), flush=True)
raise SystemExit(result.returncode)
