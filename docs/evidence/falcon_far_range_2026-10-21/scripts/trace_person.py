#!/usr/bin/env python3
"""Trace one frame: replay frames [a, b] of the cache (fresh detector at a, falcon_ros, the checkout's defaults) and at
frame b report, for the main person's raw points (N2 reviewed box, +-1.5 m along, +-1 m lateral): the corridor lateral
the detector gave them (near / far / union), whether they are corridor candidates and in the strict gauge, and the
clusters near the person with their verdict. Read-only (wraps Detector._corridor / _cluster).

    trace_person.py --frames 2600:2660 [--cache /data/falcon]"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(os.environ["RESENSE_REPO"])
sys.path.insert(0, str(REPO / "docs/evidence/n2_falcon_2026-10-18"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "falcon_long_range_2026-10-19/scripts"))
import numpy as np  # noqa: E402
import summarize_falcon as N2  # noqa: E402
import run_cache  # noqa: E402
from resense.detector import Detector  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--cache", default="/data/falcon")
    a = ap.parse_args()
    lo, hi = (int(v) for v in a.frames.split(":"))
    _, BY = N2.references()
    meta = json.loads((Path(a.cache) / "meta.json").read_text())
    cfg = run_cache.build_cfg("falcon_ros", [], [])
    det = Detector(cfg)
    R_vs = run_cache.axis_matrix(cfg.sensor).astype(np.float32)
    rec = {}
    orig_corr, orig_cl = Detector._corridor, Detector._cluster

    def corr(self, xyz, inten):
        out = orig_corr(self, xyz, inten)
        rec["xyz"], rec["cand"], rec["dy_all"], rec["valid"] = xyz, out[0], out[1], out[4]
        rec["shift"] = self._union_shift
        rec["far"] = self._far_axis
        return out

    def clus(self, cand, *args, **kw):
        cl = orig_cl(self, cand, *args, **kw)
        rec["clusters"] = cl
        return cl
    Detector._corridor, Detector._cluster = corr, clus
    import resense.clustering as CL
    orig_cc = CL._corridor_cluster
    blobs = []

    def cc(b, *args, **kw):
        c = orig_cc(b, *args, **kw)
        blobs.append((float(b.bmin[0]), float(b.bmax[0]), float(b.bmin[1]), float(b.bmax[1]), float(b.bmin[2]), float(b.bmax[2]),
                      int(b.n_vox), len(b.idx), None if c is None else (c.zone, c.reason, bool(getattr(c, "thin", False)),
                                                                        bool(getattr(c, "weak", False)))))
        return c
    CL._corridor_cluster = cc
    for i in range(lo, hi + 1):
        d = np.load(Path(a.cache) / f"f_{i:05d}.npz")
        xyz, inten = d["xyz"], d["inten"]
        k = run_cache.crop(xyz, cfg.sensor.min_range, cfg.sensor.max_range)
        fr = run_cache.Frame(xyz=xyz[k] @ R_vs.T, intensity=inten[k], ring=None, stamp=meta[i]["stamp"],
                             frame_id=meta[i]["frame_id"], meta={"n_raw": meta[i]["n_raw"], "n_near": meta[i]["n_near"]})
        blobs.clear()
        res = det.process(fr, ego_speed=None)
    box = np.asarray(BY[hi]["main_approach"]).mean(axis=0)
    M = np.asarray(det.mount_rotation)
    raw = rec["xyz"] @ M                  # vehicle -> raw (as assoc.raw_center)
    sel = (np.abs(raw[:, 0] - box[0]) < 1.5) & (np.abs(raw[:, 1] - box[1]) < 1.0)
    idx = np.flatnonzero(sel)
    far = rec["far"]
    print("frame", hi, "person raw x/y", box[:2].round(2), "points", idx.size, "decision", res.obstacle, res.warning,
          "far.valid", None if far is None else far.valid, "near axis_valid", det.track.axis_valid, "valid tuple", rec["valid"])
    near = rec["dy_all"][idx] - (0 if rec["shift"] is None else rec["shift"][idx])
    print("dy used  ", np.round(rec["dy_all"][idx], 2)[:12])
    print("dy near  ", np.round(near, 2)[:12])
    if far is not None:
        print("dy farline", np.round(near - far.line_offset(rec["xyz"][idx, 0], det.track), 2)[:12])
    c = rec["cand"]
    inc = np.isin(c.idx, idx)
    print("candidates", int(inc.sum()), "strict", int(c.in_gauge[inc].sum()))
    for cl in rec.get("clusters", []):
        if abs(cl.distance - box[0]) < 4:
            print("cluster", round(cl.distance, 1), {k: getattr(cl, k) for k in ("zone", "reason", "n_points") if hasattr(cl, k)})
    for bl in blobs:
        if bl[0] - 4 < box[0] < bl[1] + 4:
            print("blob x %.1f-%.1f y %.2f..%.2f z %.2f..%.2f vox %d pts %d ->" % bl[:8], bl[8])
    thin = [(round(x.distance, 1), x.zone, x.reason) for x in getattr(det, "_thin", []) if abs(x.distance - box[0]) < 4]
    print("thin/weak near the person", thin)
    print("dets", [(round(x.distance, 1), x.zone, x.reason) for x in res.detections], "warns",
          [(round(x.distance, 1), x.zone, x.reason) for x in res.warnings], "clear", res.clear_distance)


if __name__ == "__main__":
    main()
