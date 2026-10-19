"""Feed 10 consecutive REAL Falcon frames (0-9, dumped raw, sensor frame = ROS FLU) to a fresh detector after
re-expressing the cloud in another axis convention (a differently mounted or differently publishing sensor).
Reports per frame the decision and the orientation the calibrator holds. Control: the identity mount must
reproduce the main run's frames 0-9.

    RESENSE_REPO=<checkout> python orient_probe.py <dir with head_f0000N.npz> <main run head.jsonl>
"""
import json
import os
import sys

import numpy as np

REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "ros2_ws/src/resense_ros"))
import stream_falcon  # noqa: E402,F401  (puts the judge scripts on the path)
import judge_runner  # noqa: E402
from resense.frame import Frame  # noqa: E402

D = sys.argv[1]
FRAMES = [np.load(f"{D}/head_f{i:05d}.npz") for i in range(10)]


def rz(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


RX180 = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]])
VARIANTS = {                                   # a cloud in convention M: p' = M @ p  (p in ROS FLU)
    "ROS FLU as recorded": np.eye(3),
    "yaw +90": rz(90), "yaw 180": rz(180), "yaw 270": rz(270),
    "upside-down (roll 180)": RX180, "upside-down + yaw 90": RX180 @ rz(90),
    "manufacturer native (x up, y right, z fwd)": np.array([[0, 0, 1], [0, -1, 0], [1, 0, 0]]),
    "roll 90 (sideways)": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]),
}
PANDAR = {}
FALCON_NATIVE = {"sensor.forward": "+z", "sensor.left": "-y", "sensor.up": "+x"}


def run(M, overrides):
    rep = judge_runner.NodeReplica(overrides=overrides)
    out = []
    for i, d in enumerate(FRAMES):
        xyz = (d["xyz"].astype(np.float64) @ M.T).astype(np.float32)
        frame = Frame(xyz=(xyz @ rep.R_vs.T).astype(np.float32), intensity=d["inten"], ring=None, stamp=0.1 * i,
                      frame_id="seyond", meta={"n_raw": len(xyz), "n_near": 0})
        res = rep.detector.process(frame, ego_speed=None)
        m = res.mount or {}
        out.append((judge_runner.node_decision(res), m.get("orientation"), m.get("orientation_confirmed")))
    return out


main = [json.loads(line) for line in open(sys.argv[2])][:10]
for name, M in VARIANTS.items():
    configs = [("default launch (Pandar axes + auto)", PANDAR)]
    if "native" in name:
        configs.append(("explicit falcon_native profile axes", FALCON_NATIVE))
    for cfgname, overrides in configs:
        o = run(M, overrides)
        first_ok = next((i for i, x in enumerate(o) if x[2]), None)
        print(f"{name:44s} | {cfgname:36s} | decisions f0-9: {' '.join(x[0][:2] for x in o)} "
              f"| orientation at f9: {o[-1][1]} | confirmed from frame: {first_ok}")
        if name.startswith("ROS FLU") and overrides is PANDAR:
            print("   control: identity mount reproduces the main run's decisions of frames 0-9:",
                  [x[0] for x in o] == [r["decision"] for r in main])
