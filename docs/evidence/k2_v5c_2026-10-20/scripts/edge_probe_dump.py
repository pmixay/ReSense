"""X3's probe.py (judgement_2026-10-13, unchanged) with a read-only dump of chosen frames, for the edge-entry check: after
``Detector.process`` returns, the frame's cloud in the detector frame with every return's corridor lateral ``dy`` and
height ``h`` (``_frame_hd``), the output track model and the frame's clusters near a given distance are saved.
``--set`` overrides the replica's config (as judge_runner_set.py). The probe's ``.jsonl`` must equal X3's raw record of
the same case (checked by the caller).

    RESENSE_REPO=<tree> python edge_probe_dump.py <out.pkl> <frames a-b> [--set k=v ...] -- <probe.py args>
"""
import os
import pickle
import runpy
import sys

import numpy as np
import yaml

cut = sys.argv.index("--")
out, frames = sys.argv[1], sys.argv[2]
lo, hi = (int(v) for v in frames.split("-"))
sets, it = {}, iter(sys.argv[3:cut])
for a in it:
    if a == "--set":
        k, v = next(it).split("=", 1)
        sets[k] = yaml.safe_load(v)
ROOT = os.environ["RESENSE_REPO"]
J = os.path.join(ROOT, "docs/evidence/judgement_2026-10-13/scripts")
sys.path.insert(0, ROOT)
sys.path.insert(0, J)
import judge_runner as jr  # noqa: E402
import resense.detector as detm  # noqa: E402

_Replica = jr.NodeReplica


class Replica(_Replica):
    def __init__(self, *a, **k):
        k.setdefault("overrides", sets)
        super().__init__(*a, **k)


jr.NodeReplica = Replica
import range_test  # noqa: E402
range_test.NodeReplica = Replica
dumps, n = {}, [0]
_process = detm.Detector.process


def process(self, frame, ego_speed=None):
    res = _process(self, frame, ego_speed)
    i = n[0]
    n[0] += 1
    if lo <= i <= hi:
        xyz = np.asarray(self._frame_xyz)
        dy, h = (np.asarray(v) for v in self._frame_hd)
        m = (xyz[:, 0] > 0) & (xyz[:, 0] < 90) & (np.abs(xyz[:, 1]) < 8)
        dumps[i] = {"xyz": xyz[m].astype(np.float32), "dy": dy[m].astype(np.float32), "h": h[m].astype(np.float32),
                    "model": res.track, "calib_R": np.array(self.calib.R),
                    "dets": [d.to_dict() for d in res.detections], "warns": [d.to_dict() for d in res.warnings]}
    return res


detm.Detector.process = process
sys.argv = [os.path.join(J, "probe.py")] + sys.argv[cut + 1:]
runpy.run_path(sys.argv[0], run_name="__main__")
pickle.dump(dumps, open(out, "wb"))
print(f"{out}: {len(dumps)} frames dumped", file=sys.stderr)
