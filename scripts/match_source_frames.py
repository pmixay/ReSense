#!/usr/bin/env python3
"""Find the source frames of derived recordings in a streamed organizer archive (exact references).

    match_source_frames.py <archive url | .zst> --member NAME --query <decoded cache> [...] --out DIR
        [--sample 60] [--min-frac 0.9] [--skip-members FILE]

The organizers' synthetic bags of 16.10 insert object points into real scans. Where the real scan
is available, the inserted points are exactly the points absent from it (``label_marked_objects.py
--reference``); the intensity-1 marker alone is not reliable (README of the synthetic evidence).
This script streams the archive once (zstd -> tar, one split ``.db3`` on disk at a time), decodes
every message with the node decoder of the checkout on PYTHONPATH (the same ``cache_decoded.py``
decode, so float32 xyz compare bit-exactly) and looks up ``--sample`` random points of every query
frame (intensity > 3, so no inserted point is sampled). A source frame matches a query frame when
at least ``--min-frac`` of its sample points occur in it. Matched source frames are written as a
decoded cache: ``<out>/<query bag>/f_<query idx>.npz`` plus ``meta.json`` (source member, message
index, bag time, stamp, matched fraction), usable as ``--reference`` with ``--ref-offset 0``.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path

import numpy as np
import zstandard

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "docs/evidence/judgement_2026-10-13/scripts"))


def point_hash(xyz):
    u = np.ascontiguousarray(xyz, dtype=np.float32).view(np.uint32).astype(np.uint64)
    return ((u[:, 0] * np.uint64(0x9E3779B97F4A7C15)) ^ (u[:, 1] * np.uint64(0xC2B2AE3D27D4EB4F))
            ^ (u[:, 2] * np.uint64(0x165667B19E3779F9)))


def build_queries(caches, n_sample, seed=0):
    owners, hashes, names = [], [], []
    for c in caches:
        bag = os.path.basename(os.path.normpath(c))
        for f in sorted(glob.glob(os.path.join(c, "f_*.npz"))):
            d = np.load(f)
            ok = np.flatnonzero(d["inten"] > 3.0)
            if ok.size < n_sample:
                continue
            sel = np.random.default_rng(seed).choice(ok, n_sample, replace=False)
            hs = np.unique(point_hash(d["xyz"][sel]))
            owners.append(np.full(hs.size, len(names)))
            hashes.append(hs)
            names.append((bag, int(Path(f).stem[2:]), hs.size))
    h, o = np.concatenate(hashes), np.concatenate(owners)
    order = np.argsort(h, kind="stable")
    return h[order], o[order], names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archive")
    ap.add_argument("--member", default="")
    ap.add_argument("--query", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--min-frac", type=float, default=0.9)
    ap.add_argument("--skip-members", default="", help="file of split basenames already searched (a resumed stream)")
    a = ap.parse_args()
    from judge_runner import iter_raw
    from resense_ros import fastcloud
    from unpack_dataset import open_zst_stream

    skip = set(Path(a.skip_members).read_text().split()) if a.skip_members else set()
    qh, qo, names = build_queries(a.query, a.sample)
    print(f"{len(names)} query frames, {qh.size} sample points", flush=True)
    best = {}
    tmpdir = tempfile.mkdtemp(dir=a.out if os.path.isdir(a.out) else None)
    stream = zstandard.ZstdDecompressor().stream_reader(open_zst_stream(a.archive, a.member), read_size=1 << 20)
    n_members = n_msgs = 0
    with tarfile.open(fileobj=stream, mode="r|") as tar:
        for ti in tar:
            if not ti.isfile() or not ti.name.endswith(".db3") or os.path.basename(ti.name) in skip:
                continue
            tmp = os.path.join(tmpdir, "split.db3")
            with tar.extractfile(ti) as src, open(tmp, "wb") as dst:
                while chunk := src.read(1 << 22):
                    dst.write(chunk)
            for j, (ts, topic, raw) in enumerate(iter_raw(tmp)):
                msg = fastcloud.parse_pointcloud2(raw)
                xyz, inten, ring, _, _ = fastcloud.decode(fastcloud.packed(msg), 2.5, 250.0)
                n_msgs += 1
                if not xyz.size:
                    continue
                hs = point_hash(xyz)
                pos = np.minimum(np.searchsorted(qh, hs), qh.size - 1)
                hit = qh[pos] == hs
                if not hit.any():
                    continue
                pairs = np.unique(np.stack([qo[pos[hit]], qh[pos[hit]].view(np.int64)]), axis=1)
                counts = np.bincount(pairs[0], minlength=len(names))
                for q in np.flatnonzero(counts):
                    frac = counts[q] / names[q][2]
                    if frac >= a.min_frac and frac > best.get(q, {}).get("frac", 0.0):
                        bag, k, _ = names[q]
                        os.makedirs(os.path.join(a.out, bag), exist_ok=True)
                        np.savez_compressed(os.path.join(a.out, bag, f"f_{k:05d}.npz"), xyz=xyz, inten=inten, ring=ring)
                        best[q] = {"i": k, "member": ti.name, "msg": j, "bag_t": ts / 1e9, "topic": topic,
                                   "stamp": msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
                                   "frac": round(float(frac), 3)}
            os.remove(tmp)
            n_members += 1
            print(f"{ti.name}: {n_members} splits, {n_msgs} messages, {len(best)}/{len(names)} matched", flush=True)
    os.rmdir(tmpdir)
    per_bag = {}
    for q, v in best.items():
        per_bag.setdefault(names[q][0], []).append(v)
    for bag, rows in per_bag.items():
        json.dump(sorted(rows, key=lambda r: r["i"]), open(os.path.join(a.out, bag, "meta.json"), "w"), indent=0)
    summary = {bag: {"query_frames": sum(1 for n in names if n[0] == bag), "matched": len(per_bag.get(bag, []))}
               for bag in sorted({n[0] for n in names})}
    json.dump({"archive": a.archive, "member": a.member, "splits": n_members, "messages": n_msgs,
               "sample": a.sample, "min_frac": a.min_frac, "bags": summary},
              open(os.path.join(a.out, "match_summary.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
