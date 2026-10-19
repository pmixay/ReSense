#!/usr/bin/env python3
"""One organizer synthetic bag through two node replicas, as a jury plays it (judge_runner: sqlite messages in
timestamp order, node decode, continuity rules, decision rule): ``off`` (every 19.10 switch at 0: the aec88d2
behaviour) and ``cand`` (the committed configuration). The bag's .db3 is extracted from a local
``new_synth_data.zst`` to a spool directory, played, and deleted. (The rolling-buffer stream recovery of
``synth_stream.py`` lost these bags' messages: their overflow pages are not near their leaf cells.)

    synth_local.py --zst new_synth_data.zst|https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --bag synthetic_switch --spool DIR --out PREFIX
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
import sys  # noqa: E402
import tarfile  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RESENSE_REPO", HERE.parents[3]))
for p in (HERE, ROOT, ROOT / "scripts", ROOT / "ros2_ws/src/resense_ros", ROOT / "docs/evidence/judgement_2026-10-13/scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import zstandard  # noqa: E402

OFF = {"lowobj.local_rail_margin": 0.0, "cluster.mount_cross_tol": 0.0, "tracking.settle_min_hits": 0}
FRAMES = {"synthetic_platform": 386, "synthetic_switch": 736, "synthetic_tunnels": 545}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zst", required=True)
    ap.add_argument("--bag", required=True, choices=sorted(FRAMES))
    ap.add_argument("--spool", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from judge_runner import NodeReplica, iter_raw, record
    os.makedirs(a.spool, exist_ok=True)
    db3 = None
    t0 = time.time()
    if a.zst.startswith("http"):
        from unpack_dataset import open_zst_stream
        raw = open_zst_stream(a.zst, "new_synth_data.zst")
    else:
        raw = open(a.zst, "rb")
    with raw:
        stream = zstandard.ZstdDecompressor().stream_reader(raw, read_size=1 << 20)
        with tarfile.open(fileobj=stream, mode="r|") as tar:
            for ti in tar:
                if ti.isfile() and ti.name.endswith(".db3") and os.path.basename(ti.name).startswith(a.bag):
                    db3 = os.path.join(a.spool, os.path.basename(ti.name))
                    with tar.extractfile(ti) as src, open(db3, "wb") as dst:
                        shutil.copyfileobj(src, dst, 64 << 20)
                    break
    if db3 is None:
        raise SystemExit(f"{a.bag} not in {a.zst}")
    try:
        reps = {"off": NodeReplica(overrides=OFF), "cand": NodeReplica()}
        outs = {k: open(f"{a.out}_{k}_{a.bag}.jsonl", "w") for k in reps}
        n = 0
        for ts, topic, data in iter_raw(db3):
            for k, rep in reps.items():
                msg, stamp, res, dec_ms, det_ms = rep.process_raw(data, topic, n)
                outs[k].write(json.dumps(record(n, ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id,
                                                topic)) + "\n")
            n += 1
        for f in outs.values():
            f.close()
    finally:
        os.unlink(db3)
    meta = {"bag": a.bag, "frames": n, "expected": FRAMES[a.bag], "off_overrides": OFF, "repo": str(ROOT),
            "resets": {k: r.resets for k, r in reps.items()}, "wall_s": round(time.time() - t0, 1)}
    json.dump(meta, open(f"{a.out}_{a.bag}.meta.json", "w"), indent=1)
    print(json.dumps(meta))
    return 0 if n == FRAMES[a.bag] else 1


if __name__ == "__main__":
    sys.exit(main())
