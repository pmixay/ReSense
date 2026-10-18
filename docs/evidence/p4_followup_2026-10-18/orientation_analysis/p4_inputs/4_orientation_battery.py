#!/usr/bin/env python3
"""B4: the 24 axis-aligned sensor orientations through the node replica, with auto-calibration on.

    orientation_battery.py run <decoded cache> <out.json> [--only K,K] [--end N]
    orientation_battery.py rotations

The cloud of every frame is rotated as if the sensor were mounted turned (the judge's ``probe.py``
transform: vehicle frame ``v -> Rt v``, back into the sensor frame with the configured axis mapping).
For each of the 24 proper rotations ``Rt`` that map axes onto signed axes, every frame records the node
decision, the calibration status and the orientation the detector adopted. The correct answer for ``Rt``
is the correction ``Rt^T``; its label (``calibration.axis_label``) is recorded as ``expected``. With the
default ``keep_up_axis`` only the 8 rotations whose up axis stays vertical are candidates.

``native_falcon`` marks the rotation that a cloud in the Falcon manual's native frame (x up, y right,
z forward) presents to the configured Pandar mapping: ``Rt = R_vs @ M``, ``M`` = native-from-vehicle.
The identity rotation is the control: it must equal a plain ``probe.py`` run frame by frame.
Run with RESENSE_REPO / PYTHONPATH set to the checkout.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "docs/evidence/judgement_2026-10-13/scripts"
NATIVE_FROM_VEHICLE = np.array([[0, 0, 1], [0, -1, 0], [1, 0, 0]], dtype=float)   # x up, y right, z forward


def rotations():
    """The 24 proper axis-aligned rotations, identity first, in a fixed order."""
    import itertools
    out = [np.eye(3)]
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            R = np.zeros((3, 3))
            for row, (col, s) in enumerate(zip(perm, signs)):
                R[row, col] = s
            if abs(np.linalg.det(R) - 1.0) < 1e-9 and not np.allclose(R, np.eye(3)):
                out.append(R)
    return out


def run(a):
    sys.path.insert(0, str(JUDGE))
    from judge_runner import NodeReplica, node_decision, record
    from range_test import run_frame
    from resense.calibration import axis_label
    meta = json.loads(Path(a.cache, "meta.json").read_text())
    files = sorted(glob.glob(os.path.join(a.cache, "f_*.npz")))
    if a.end:
        files = files[:a.end]
    frames = [np.load(f) for f in files]
    rots = rotations()
    Rvs = NodeReplica().R_vs.astype(np.float64)
    native = Rvs @ NATIVE_FROM_VEHICLE
    only = {int(v) for v in a.only.split(",")} if a.only else set(range(len(rots)))
    cases = []
    for idx, Rt in enumerate(rots):
        if idx not in only:
            continue
        rep = NodeReplica()
        rows = []
        for k, (m, d) in enumerate(zip(meta, frames)):
            xyz = d["xyz"]
            if idx:
                xyz = ((xyz.astype(np.float64) @ Rvs.T @ Rt.T) @ Rvs).astype(np.float32)
            res = run_frame(rep, xyz, d["inten"], d["ring"], m, k)
            st = rep.detector.calib.state
            msgs = record(k, m["bag_t"], m["stamp"], res, 0.0, 0.0, m["frame_id"], m["topic"])["msgs"]
            rows.append({"i": k, "decision": node_decision(res), "status": st.status, "orientation": st.orientation,
                         "msg": msgs[0] if msgs else ""})
        cases.append({"index": idx, "Rt": Rt.astype(int).tolist(), "expected": axis_label(Rt.T),
                      "applied_label": axis_label(Rt), "up_vertical": bool(abs(Rt[2, 2]) == 1.0),
                      "native_falcon": bool(np.allclose(Rt, native)), "rows": rows})
        print(idx, axis_label(Rt.T), rows[-1]["status"], rows[-1]["orientation"], flush=True)
    json.dump({"cache": a.cache, "repo": os.environ.get("RESENSE_REPO", ""), "cases": cases}, open(a.out, "w"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("cache")
    r.add_argument("out")
    r.add_argument("--only", default="")
    r.add_argument("--end", type=int, default=0)
    sub.add_parser("rotations")
    a = ap.parse_args()
    if a.cmd == "run":
        run(a)
    else:
        for i, R in enumerate(rotations()):
            print(i, R.astype(int).tolist(), "up vertical" if abs(R[2, 2]) == 1 else "sideways")


if __name__ == "__main__":
    main()
