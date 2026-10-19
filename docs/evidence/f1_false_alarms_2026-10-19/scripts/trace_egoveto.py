"""E3 receding probes (judge range_test, unchanged) with a read-only record of the ego-veto state of the tracks
near the object: the tracker's odometry speed and whether _carried_along(t) holds (base aec88d2)."""
import os, sys, json
REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import numpy as np
import range_test
from resense.detector import Detector
out = sys.argv[1]; vx = sys.argv[2]
sink = []
orig = Detector.process
def process(self, frame, *a, **k):
    res = orig(self, frame, *a, **k)
    tr = self.tracker
    rows = []
    for t in tr.tracks:
        if t.last is not None and abs(float(t.centroid[1])) < 3 and float(t.centroid[0]) > 20:
            rows.append({"id": t.id, "d": round(float(t.last.distance), 2), "carried": bool(tr._carried_along(t)),
                         "reported": t.reported, "zone": t.zone, "odo": len(t.odo)})
    sink.append({"odo_v": tr._odo_v, "tracks": rows})
    return res
Detector.process = process
sys.argv = ["range_test.py", "/data/decoded_f1/roundT_squareT_pressureGate_squareT",
            os.environ["SP"] + "/probes/icp_roundT_squareT_pressureGate_squareT.json", out,
            "--obj", "0.6,0.6,1.0", "--start", "230", "--d0", "100", "--end", "340", "--vx", vx]
range_test.main()
json.dump(sink, open(out + ".veto.json", "w"))
