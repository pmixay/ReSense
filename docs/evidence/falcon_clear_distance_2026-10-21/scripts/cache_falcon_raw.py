#!/usr/bin/env python3
"""Stream the Falcon recording once from the archive and store the recovered PointCloud2 messages, in the same
timestamp order and with the same duplicate rule as P4's falcon_pair.py (50-message reorder heap, duplicate
timestamps dropped), as a flat file: per message ``<qI`` (timestamp ns, byte length) + the raw CDR bytes.
No bag, no decode: the node replica decodes later (``run_falcon.py``).

    cache_falcon_raw.py <yandex link | falcon_test.zst> --out /data/falcon/raw.bin
"""
import argparse, heapq, json, os, struct, sys, time
from pathlib import Path

ROOT = Path(os.environ["RESENSE_REPO"])
for p in (ROOT / "scripts", ROOT / "docs/evidence/extended_data_2026-10-17/scripts"):
    sys.path.insert(0, str(p))
from stream_falcon import Recover, byte_stream  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("--out", required=True)
a = ap.parse_args()
rec = Recover("seyond", 256)
heap, seen, n, last = [], set(), 0, None
log = {"order_violations": 0, "duplicates": 0}
t0 = time.time()
fo = open(a.out, "wb")


def emit(ts, data):
    global n
    fo.write(struct.pack("<qI", ts, len(data)))
    fo.write(data)
    n += 1


def release(force=False):
    global last
    while heap and (force or len(heap) > 50):
        ts, data = heapq.heappop(heap)
        if last is not None and ts < last:
            log["order_violations"] += 1
        last = ts
        emit(ts, data)


for chunk in byte_stream(a.src, "falcon_test.zst", "falcon_test_second_dark_0.db3"):
    for topic_id, ts, data in rec.feed(chunk):
        if topic_id != 3:
            continue
        if ts in seen:
            log["duplicates"] += 1
            continue
        seen.add(ts)
        heapq.heappush(heap, (ts, data))
    release()
for topic_id, ts, data in rec.feed(b"", final=True):
    if topic_id == 3 and ts not in seen:
        seen.add(ts)
        heapq.heappush(heap, (ts, data))
release(force=True)
fo.close()
meta = {"src": a.src, "frames": n, "found": rec.found, "kept": rec.kept, "lost": rec.lost, **log,
        "wall_s": round(time.time() - t0, 1), "bytes": os.path.getsize(a.out)}
json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
print(json.dumps(meta))
