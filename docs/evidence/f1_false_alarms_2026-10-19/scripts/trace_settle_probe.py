"""S_person_<d> with H+S2 and a read-only record of the tracks near the probe object (settle state)."""
import os, sys, json
REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import numpy as np
import range_test
from resense.detector import Detector
D = float(sys.argv[1])
over = {"cluster.mount_cross_tol": 0.5, "tracking.settle_min_hits": 50, "tracking.settle_check_z": False}
class R(range_test.NodeReplica):
    def __init__(self, *a, **k):
        k.setdefault("overrides", over); super().__init__(*a, **k)
range_test.NodeReplica = R
sink = []
orig = Detector.process
def process(self, frame, *a, **k):
    res = orig(self, frame, *a, **k)
    rows = []
    for t in self.tracker.tracks:
        if abs(float(t.centroid[0]) - D) < 4 and abs(float(t.centroid[1])) < 3:
            n = len(t.settle_hist)
            sp = np.ptp(np.stack(t.settle_cen), axis=0).round(2).tolist() if n else None
            rows.append({"id": t.id, "hits": t.hits, "n": n, "share": round(sum(t.settle_hist) / n, 2) if n else None,
                         "spread": sp, "settled_out": t.settled_out, "zone": t.zone, "reported": t.reported,
                         "misses": t.misses})
    sink.append(rows)
    return res
Detector.process = process
sys.argv = ["range_test.py", "/data/decoded_f1/squareT_platform_squareT_switch",
            os.environ["SP"] + "/probes/icp_squareT_platform_squareT_switch.json", os.environ["SP"] + f"/probes/settle_trace_{int(D)}",
            "--obj", "0.5,0.5,1.75", "--start", "360", "--d0", str(int(D)), "--end", "620"]
range_test.main()
json.dump(sink, open(os.environ["SP"] + f"/probes/settle_trace_{int(D)}.tracks.json", "w"))
