#!/usr/bin/env python3
"""N3 Falcon dust runs, straight from the organizers' stream (nothing stored but records).

Reuses ``scripts/stream_falcon.py`` (byte stream, overflow-chain recovery, timestamp reorder)
and the judge's node decode (``fastcloud``) and record format (``judge_runner.record``).

Modes:
  full     two fresh detectors over all frames: dust guard off (reproduces the committed run)
           and dust guard on (criterion 5: clean Falcon STOP retention).
  window   fresh detectors from --start to --end (exclusive): clean plus low/medium/high with
           the given --guard state. Dust is placed in the clean detector's actually applied
           model frame (scripts/dust_reference.py), the registered generator (resense/dust.py,
           seed 20261018 unless --seed), plus a Falcon field-of-view clip: generated returns
           outside the sensor's azimuth/elevation span are dropped (a scanner cannot return
           from where it does not look). Falcon decodes carry no ring; the per-point
           is_2nd_return flag is not decoded by the node and not used by the detector, so
           generated returns enter as ordinary returns. Synthetic-model stress, not physics.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import heapq
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(os.environ.get("RESENSE_REPO", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "ros2_ws/src/resense_ros"))
sys.path.insert(0, str(ROOT / "docs/evidence/judgement_2026-10-13/scripts"))
sys.path.insert(0, str(ROOT / "docs/evidence/extended_data_2026-10-17/scripts"))

import numpy as np  # noqa: E402

from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, axis_matrix  # noqa: E402
from resense_ros import fastcloud  # noqa: E402
from judge_runner import record  # noqa: E402
from dust_reference import augment_in_reference, process_clean_reference  # noqa: E402

spec = importlib.util.spec_from_file_location("stream_falcon", ROOT / "scripts/stream_falcon.py")
stream_falcon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = stream_falcon
spec.loader.exec_module(stream_falcon)
spec = importlib.util.spec_from_file_location("dust_stress_module", ROOT / "resense/dust.py")
dust = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dust
spec.loader.exec_module(dust)

# The recording's own decoded span (characterization_summary.json), with a small margin.
FOV_AZ = (-59.8, 59.6)
FOV_EL = (-14.25, 12.4)


def config(guard: bool) -> DetectorConfig:
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
    cfg.calibration.enabled = True          # node default auto_calibrate:=true (judge NodeReplica)
    cfg.dust.enabled = guard
    return cfg


def fov_clip(frame, indices, R_vs):
    """Drop generated returns outside the sensor's field of view (sensor-frame angles)."""
    new = indices < 0
    if not new.any():
        return frame, indices, 0
    s = frame.xyz[new] @ R_vs                 # vehicle -> sensor frame (R_vs orthonormal)
    az = np.degrees(np.arctan2(s[:, 1], s[:, 0]))
    el = np.degrees(np.arctan2(s[:, 2], np.hypot(s[:, 0], s[:, 1])))
    inside = (az >= FOV_AZ[0]) & (az <= FOV_AZ[1]) & (el >= FOV_EL[0]) & (el <= FOV_EL[1])
    keep = np.ones(frame.n, dtype=bool)
    keep[np.flatnonzero(new)[~inside]] = False
    meta = dict(frame.meta)
    meta["n_raw"] = int(meta.get("n_raw", frame.n)) - int((~keep).sum())
    out = Frame(frame.xyz[keep], frame.intensity[keep], None if frame.ring is None else frame.ring[keep],
                frame.stamp, frame.frame_id, meta)
    return out, indices[keep], int((~keep).sum())


class Lane:
    """One fresh detector with the node's continuity rules and a record file."""

    def __init__(self, name, cfg, out):
        self.name, self.cfg, self.det = name, cfg, Detector(cfg)
        self.fh = gzip.open(out / f"{name}.jsonl.gz", "wt")
        self.last = None
        self.counts = {"STOP": 0, "CAUTION": 0, "GO": 0, "FAULT": 0, "degraded": 0, "episodes": 0}
        self._stop = False

    def continuity(self, stamp):
        if self.last is not None:
            gap = stamp - self.last
            if gap < -0.5 or gap > 30.0:
                self.det = Detector(self.cfg)
            elif gap > 1.0:
                self.det.reset()
        self.last = stamp

    def write(self, i, bag_t, stamp, res, extra=None):
        r = record(i, bag_t, stamp, res, 0.0, res.timing_ms.get("total", 0.0), "seyond", "/iv_points")
        if extra:
            r.update(extra)
        dg = (res.health or {}).get("dust_guard")
        if dg is not None:
            r["dust_guard"] = dg
        self.fh.write(json.dumps(r) + "\n")
        d = r["decision"]
        self.counts[d] += 1
        self.counts["degraded"] += int(r["dlevel"] in ("warn", "error"))
        self.counts["episodes"] += int(d == "STOP" and not self._stop)
        self._stop = d == "STOP"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--mode", choices=("full", "window"), required=True)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=10 ** 9)
    ap.add_argument("--guard", choices=("off", "on"), default="on")
    ap.add_argument("--levels", default="low,medium,high")
    ap.add_argument("--seed", type=int, default=20261018)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--member", default="falcon_test.zst")
    ap.add_argument("--inner", default="falcon_test_second_dark_0.db3")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[k] = "1"
    guard = a.guard == "on"
    R_vs = axis_matrix(config(False).sensor).astype(np.float32)
    if a.mode == "full":
        lanes = {"clean_off": Lane("clean_off", config(False), a.out), "clean_on": Lane("clean_on", config(True), a.out)}
    else:
        lanes = {"clean": Lane("clean", config(guard), a.out)}
        for lv in a.levels.split(","):
            lanes[lv] = Lane(lv, config(guard), a.out)
    rec = stream_falcon.Recover("seyond", 256)
    heap, seen = [], set()
    state = {"n": 0, "last_ts": None, "order": 0}
    started = time.time()
    audit = {lv: {"injected": 0, "attenuated": 0, "fov_dropped": 0} for lv in lanes if lv not in ("clean", "clean_on", "clean_off")}
    intensity_low_share = []

    def process(ts, data):
        i = state["n"]
        state["n"] += 1
        if not (a.start <= i < a.end):
            return
        msg = fastcloud.parse_pointcloud2(data)
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        xyz_s, inten, ring, n_raw, n_near = fastcloud.decode(fastcloud.packed(msg), 2.5, 250.0)
        has_ring = fastcloud.has_field(msg, "ring")
        def frame():
            return Frame(xyz=(xyz_s @ R_vs.T).astype(np.float32), intensity=inten.copy(),
                         ring=ring.copy() if has_ring else None, stamp=stamp, frame_id=msg.header.frame_id,
                         meta={"n_raw": n_raw, "n_near": n_near})
        if i % 50 == 0:
            intensity_low_share.append(float((inten <= dust.PRESETS["low"].intensity_max).mean()))
        if a.mode == "full":
            for lane in lanes.values():
                lane.continuity(stamp)
                lane.write(i, ts / 1e9, stamp, lane.det.process(frame()))
            return
        clean = lanes["clean"]
        clean.continuity(stamp)
        fr = frame()
        res, ref = process_clean_reference(clean.det, fr)
        clean.write(i, ts / 1e9, stamp, res)
        for lv, lane in lanes.items():
            if lv == "clean":
                continue
            lane.continuity(stamp)
            dfr, au, idx = augment_in_reference(frame(), dust.PRESETS[lv], ref, seed=a.seed, frame_index=i)
            dfr, idx, dropped = fov_clip(dfr, idx, R_vs)
            audit[lv]["injected"] += au["added_returns"] - dropped
            audit[lv]["attenuated"] += au["removed_returns"]
            audit[lv]["fov_dropped"] += dropped
            lane.write(i, ts / 1e9, stamp, lane.det.process(dfr),
                       {"injected": au["added_returns"] - dropped, "attenuated": au["removed_returns"]})

    def release(force=False):
        while heap and (force or len(heap) > 50):
            ts, data = heapq.heappop(heap)
            if state["last_ts"] is not None and ts < state["last_ts"]:
                state["order"] += 1
            state["last_ts"] = ts
            process(ts, data)
            if state["n"] >= a.end:
                return True
        return False

    done = False
    for chunk in stream_falcon.byte_stream(a.src, a.member, a.inner):
        for topic_id, ts, data in rec.feed(chunk):
            if topic_id != 3 or ts in seen:
                continue
            seen.add(ts)
            heapq.heappush(heap, (ts, data))
        if release():
            done = True
            break
    if not done:
        for topic_id, ts, data in rec.feed(b"", final=True):
            if topic_id == 3 and ts not in seen:
                seen.add(ts)
                heapq.heappush(heap, (ts, data))
        release(force=True)
    for lane in lanes.values():
        lane.fh.close()
    summary = {"mode": a.mode, "start": a.start, "end": a.end, "guard": a.guard, "seed": a.seed,
               "frames_seen": state["n"], "order_violations": state["order"], "lost": rec.lost,
               "wall_s": round(time.time() - started, 1), "fov_deg": {"az": FOV_AZ, "el": FOV_EL},
               "dust_intensity_max": dust.PRESETS["low"].intensity_max,
               "real_share_at_or_below_dust_intensity_max_median": float(np.median(intensity_low_share)) if intensity_low_share else None,
               "lanes": {k: v.counts for k, v in lanes.items()}, "augmentation": audit,
               "records_sha256": {k: hashlib.sha256((a.out / f"{k}.jsonl.gz").read_bytes()).hexdigest() for k in lanes}}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["lanes"]))


if __name__ == "__main__":
    main()
