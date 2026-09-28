"""Run the shipped detector (default configuration) over the ride's split files as ride_producer.py
writes them: one detector, reset at every split (each split is a separate 5 s scene because they
arrive in random order; the mount calibration is kept), one JSONL row per frame without the track
and mount dictionaries. Each split file is deleted after use.

    RIDE=/home/user/data/ride OUTDIR=ride python ride_consumer.py
"""
import glob
import json
import os
import time

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.io import iter_bag_frames

IN = os.environ.get("RIDE", "/home/user/data/ride")
OUTDIR = os.environ.get("OUTDIR", "ride")


def producer_done() -> bool:
    path = f"{OUTDIR}/producer.log"
    return os.path.exists(path) and "DONE" in open(path).read()


def main():
    cfg = DetectorConfig()
    det = Detector(cfg)
    out = open(f"{OUTDIR}/ride.jsonl", "a", buffering=1)
    log = open(f"{OUTDIR}/consumer.log", "a", buffering=1)
    seq = 0
    while True:
        files = sorted(glob.glob(f"{IN}/*.db3"), key=os.path.getmtime)
        if not files:
            if producer_done():
                break
            time.sleep(0.5)
            continue
        path, t0, n = files[0], time.time(), 0
        det.reset()
        for i, frame in iter_bag_frames(path, cfg.sensor):
            d = det.process(frame).to_dict()
            d.pop("track", None)
            d.pop("mount", None)
            d.update(split=os.path.basename(path), i=i, seq=seq)
            seq += 1
            n += 1
            out.write(json.dumps(d) + "\n")
        os.remove(path)
        log.write(json.dumps({"split": os.path.basename(path), "frames": n, "s": round(time.time() - t0, 1)}) + "\n")
    log.write("DONE\n")


if __name__ == "__main__":
    main()
