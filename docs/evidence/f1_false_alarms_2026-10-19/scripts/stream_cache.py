#!/usr/bin/env python3
"""Cache organizer bags straight from their archive stream, without writing the bag (F1, 19.10).

The container of 19.10 has ~6 GB free disk; the 6.6 GB ``squareT_platform`` and the 7.4 GB set O
bag cannot be unpacked. This reads the archive once as a byte stream (dataset.zip -> zip -> zstd
-> tar, or a Yandex .zst tar), recovers every PointCloud2 message of each wanted ``.db3`` with the
rolling sqlite overflow-chain recovery of ``scripts/stream_falcon.py`` (``Recover``, validated
there 985/985 byte-identical against sqlite), and writes, per bag:

* the gate cache exactly as ``scripts/cache_frames.py --every 1 --int16 --stamps --zstd`` would:
  ``<gate-root>/<bag>/<bag>_<iiii>.npy.zst`` (rosbags CDR deserialisation ->
  ``structured_to_compact`` -> ``compact_to_compact16``) and ``<bag>_stamps.json`` (bag receive
  time per frame, the ``messages.timestamp`` column);
* optionally the node-decoded cache of ``judgement_2026-10-13/scripts/cache_decoded.py``
  (``f_<iiiii>.npz`` with xyz / inten / ring from ``fastcloud.decode(.., 2.5, 250.0)`` and
  ``meta.json``).

Frames are indexed in timestamp order, as the rosbags reader and the sqlite ``ORDER BY timestamp``
of the reference tools do. The message count is checked against the expected frame count.

Positive control (the run that validated this tool): roundT_doubleT and roundT_pressureGate_roundT
streamed by this script against caches of the same bags made by the reference tools from the
unpacked bags (``compare`` subcommand).

    stream_cache.py run /data/dataset.zip --bags a,b --gate-root R1 [--decoded-bags a --decoded-root R2]
    stream_cache.py run https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --bags cloud_with_fake_obj ...
    stream_cache.py compare <gate|decoded> DIR_A DIR_B
"""
from __future__ import annotations

import argparse
import heapq
import json
import os
import struct
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
for p in (ROOT, ROOT / "scripts", ROOT / "ros2_ws/src/resense_ros",
          ROOT / "docs/evidence/extended_data_2026-10-17/scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import zstandard  # noqa: E402

from stream_falcon import Recover  # noqa: E402
from window_bag import PAGE, U, cdr_blob_len, local_size  # noqa: E402


class Recover2(Recover):
    """``Recover`` for both record layouts of the ``messages`` row (8-byte record header: id NULL,
    topic_id, timestamp int64, data blob with a 4-byte serial type):

    * ``A`` (the Falcon bag, topic id 3): topic_id is a 1-byte integer (serial type 1), so the
      header starts 17 bytes before the CDR blob - the layout ``Recover`` was written for;
    * ``B`` (the Pandar bags, topic id 1): SQLite stores the integer 1 as the zero-byte constant
      (serial type 9), so the header starts 16 bytes before the blob and the topic id is 1.

    Measured 19.10 on ``roundT_doubleT_0.db3``: every cell is ``08 00 09 06 <4-byte blob type>``
    followed by the 8-byte timestamp and the blob; ``Recover`` matched only cells whose rowid byte
    happened to be 8 (2 of 252)."""

    def __init__(self, frame_id: str, back_mb: int):
        super().__init__(frame_id, back_mb)
        self.layout = {}

    def _try(self, ps: int):
        b, i = self.buf, ps - self.base
        if self.layout[ps] == "A":
            hdr, topic_id = 17, b[i + 8]
            ts = struct.unpack_from(">q", b, i + 9)[0]
        else:
            hdr, topic_id = 16, 1
            ts = struct.unpack_from(">q", b, i + 8)[0]
        cdr = i + hdr
        try:
            blen = cdr_blob_len(b, cdr)
        except struct.error:
            return None
        loc = local_size(hdr + blen)
        if i + loc + 4 > len(b):
            return None
        parts, got = [bytes(b[cdr: i + loc])], loc - hdr
        nxt = struct.unpack_from(">I", b, i + loc)[0] if loc < hdr + blen else 0
        while got < blen:
            pg = self.page(nxt)
            if pg is None:
                return None
            if pg == "gone":
                return "lost"
            nxt = struct.unpack_from(">I", pg, 0)[0]
            take = min(U - 4, blen - got)
            parts.append(bytes(pg[4:4 + take]))
            got += take
        return topic_id, ts, b"".join(parts)

    def feed(self, data: bytes, final: bool = False):
        self.buf += data
        end = self.base + len(self.buf)
        limit = end if final else end - 64
        start = max(self.scanned, self.base)
        pos = self.buf.find(self.sig, start - self.base)
        while 0 <= pos and self.base + pos < limit:
            cdr = pos - 12
            if cdr >= 17 and self.buf[cdr:cdr + 4] == b"\x00\x01\x00\x00":
                a = self.buf[cdr - 17:cdr - 13]
                bb = self.buf[cdr - 16:cdr - 12]
                if a[0] == 8 and a[1] == 0 and a[2] == 1 and a[3] == 6:
                    ps, lay = self.base + cdr - 17, "A"
                elif bb[0] == 8 and bb[1] == 0 and bb[2] == 9 and bb[3] == 6:
                    ps, lay = self.base + cdr - 16, "B"
                else:
                    ps = None
                if ps is not None:
                    self.found += 1
                    self.layout[ps] = lay
                    self.pending.append(ps)
            pos = self.buf.find(self.sig, pos + 1)
        self.scanned = limit
        still = []
        for ps in self.pending:
            r = self._try(ps)
            if r is None:
                if final:
                    self.lost += 1
                else:
                    still.append(ps)
                    continue
            elif r == "lost":
                self.lost += 1
            else:
                self.kept += 1
                yield r
            self.layout.pop(ps, None)
        self.pending = still
        keep_from = min([end - self.back] + self.pending)
        cut = max(0, (keep_from - self.base) // PAGE * PAGE)
        if cut:
            del self.buf[:cut]
            self.base += cut


BAGS = {  # name: (topic, frame_id, frames) from docs/DATASET.md and docs/evidence/bag_metadata
    "doubleT_obstacle": ("/sensing/lidar/hesai128/pointcloud", "lidar_livox", 201),
    "doubleT_platform": ("/lidar_points", "hesai_lidar", 345),
    "roundT_doubleT": ("/lidar_points", "hesai_lidar", 252),
    "roundT_pressureGate_roundT": ("/lidar_points", "hesai_lidar", 268),
    "roundT_squareT_pressureGate_squareT": ("/lidar_points", "hesai_lidar", 545),
    "squareT_platform_squareT_switch": ("/lidar_points", "hesai_lidar", 877),
    "cloud_with_fake_obj": ("/lidar_points", "hesai_lidar", 1510),
}
CHUNK = 64 << 20


def tar_stream(src: str):
    from unpack_dataset import open_zst_stream
    member = "cloud_with_fake_obj.zst" if "KpkG" in src else ""
    raw = open_zst_stream(src, member)
    return zstandard.ZstdDecompressor().stream_reader(raw, read_size=1 << 20)


class Writer:
    def __init__(self, bag: str, gate_root: str, decoded_root: str | None):
        from rosbags.typesys import Stores, get_typestore
        self.bag = bag
        self.topic, self.frame_id, self.expected = BAGS[bag]
        self.ts = get_typestore(Stores.ROS2_HUMBLE)
        self.gate = os.path.join(gate_root, bag)
        os.makedirs(self.gate, exist_ok=False)
        self.decoded = os.path.join(decoded_root, bag) if decoded_root else None
        if self.decoded:
            os.makedirs(self.decoded, exist_ok=False)
        self.stamps, self.meta, self.n = {}, [], 0
        self.cz = zstandard.ZstdCompressor(level=3)

    def emit(self, ts: int, raw: bytes):
        from cache_frames import _atomic_save
        from resense.pointcloud import compact_to_compact16, pointcloud2_to_structured, structured_to_compact
        from resense_ros import fastcloud
        i = self.n
        msg = self.ts.deserialize_cdr(raw, "sensor_msgs/msg/PointCloud2")
        if msg.header.frame_id != self.frame_id:
            raise RuntimeError(f"{self.bag} frame {i}: frame_id {msg.header.frame_id!r}")
        arr = compact_to_compact16(structured_to_compact(pointcloud2_to_structured(msg)))
        _atomic_save(os.path.join(self.gate, f"{self.bag}_{i:04d}.npy.zst"), arr, zstd_level=3)
        self.stamps[f"{i:04d}"] = ts / 1e9
        if self.decoded:
            m = fastcloud.parse_pointcloud2(raw)
            xyz, inten, ring, n_raw, n_near = fastcloud.decode(fastcloud.packed(m), 2.5, 250.0)
            np.savez_compressed(os.path.join(self.decoded, f"f_{i:05d}.npz"), xyz=xyz, inten=inten, ring=ring)
            self.meta.append({"i": i, "stamp": m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                              "bag_t": ts / 1e9, "frame_id": m.header.frame_id, "topic": self.topic,
                              "has_ring": fastcloud.has_field(m, "ring"), "n_raw": n_raw, "n_near": n_near})
        self.n += 1

    def close(self):
        from cache_frames import _atomic_json
        if self.n != self.expected:
            raise RuntimeError(f"{self.bag}: {self.n} frames, expected {self.expected}")
        _atomic_json(os.path.join(self.gate, f"{self.bag}_stamps.json"),
                     {"bag": self.bag, "frame_id": self.frame_id, "frames": self.n, "stamps": self.stamps})
        if self.decoded:
            json.dump(self.meta, open(os.path.join(self.decoded, "meta.json"), "w"))


def stream_db3(fileobj, writer: Writer, log: dict):
    rec = Recover2(writer.frame_id, 256)
    heap, seen, topics, last = [], set(), {}, None

    def release(force=False):
        nonlocal last
        while heap and (force or len(heap) > 50):
            ts, data = heapq.heappop(heap)
            if last is not None and ts < last:
                log["order_violations"] = log.get("order_violations", 0) + 1
            last = ts
            writer.emit(ts, data)

    def take(items):
        for topic_id, ts, data in items:
            topics[topic_id] = topics.get(topic_id, 0) + 1
            if ts in seen:
                log["duplicates"] = log.get("duplicates", 0) + 1
                continue
            seen.add(ts)
            heapq.heappush(heap, (ts, data))

    while chunk := fileobj.read(CHUNK):
        take(rec.feed(chunk))
        release()
    take(rec.feed(b"", final=True))
    release(force=True)
    if len(topics) != 1:
        raise RuntimeError(f"{writer.bag}: PointCloud2 blobs on topic ids {topics}")
    log.update({"found": rec.found, "kept": rec.kept, "lost": rec.lost, "topic_ids": topics})
    if rec.lost:
        raise RuntimeError(f"{writer.bag}: {rec.lost} messages lost")


def run(a):
    want = [b for b in a.bags.split(",") if b]
    dec = {b for b in (a.decoded_bags or "").split(",") if b}
    unknown = set(want) - set(BAGS)
    if unknown:
        raise SystemExit(f"unknown bags {unknown}")
    report = {"src": a.src, "bags": {}, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    t0 = time.time()
    with tarfile.open(fileobj=tar_stream(a.src), mode="r|") as tar:
        for ti in tar:
            parts = ti.name.split("/")
            bag = next((b for b in want if b in parts[:-1]), None)
            if bag is None or not ti.isfile():
                continue
            if parts[-1] == "metadata.yaml":
                data = tar.extractfile(ti).read()
                ref = ROOT / "docs/evidence/bag_metadata" / f"{bag}_metadata.yaml"
                report["bags"].setdefault(bag, {})["metadata_original"] = (
                    ref.read_bytes() == data if ref.exists() else None)
                continue
            if not parts[-1].endswith(".db3"):
                continue
            log = report["bags"].setdefault(bag, {})
            w = Writer(bag, a.gate_root, a.decoded_root if bag in dec else None)
            tb = time.time()
            stream_db3(tar.extractfile(ti), w, log)
            w.close()
            log.update({"db3": parts[-1], "db3_bytes": ti.size, "frames": w.n, "decoded": bag in dec,
                        "wall_s": round(time.time() - tb, 1)})
            print(bag, json.dumps(log), flush=True)
            if all(b in report["bags"] and "frames" in report["bags"][b] for b in want) and \
                    all("metadata_original" in report["bags"][b] for b in want):
                break
    missing = [b for b in want if "frames" not in report["bags"].get(b, {})]
    report["missing"] = missing
    report["wall_s"] = round(time.time() - t0, 1)
    json.dump(report, open(a.report, "w"), indent=1)
    print(json.dumps(report, indent=1))
    return 1 if missing else 0


def compare(a):
    """Exact equality of two caches of one bag: every array (and the stamps / meta)."""
    sys.path.insert(0, str(ROOT))
    from scripts.cache_io import cache_files, load_cache_array
    out = {"kind": a.kind, "a": a.dir_a, "b": a.dir_b}
    if a.kind == "gate":
        fa, fb = cache_files(a.dir_a), cache_files(a.dir_b)
        sa = {os.path.basename(f).split(".")[0]: f for f in fa}
        sb = {os.path.basename(f).split(".")[0]: f for f in fb}
        out["frames"] = [len(sa), len(sb)]
        diff = [s for s in sorted(set(sa) | set(sb)) if s not in sa or s not in sb or not np.array_equal(
            load_cache_array(sa[s]), load_cache_array(sb[s]))]
        ja = [json.load(open(os.path.join(a.dir_a, f))) for f in os.listdir(a.dir_a) if f.endswith("_stamps.json")]
        jb = [json.load(open(os.path.join(a.dir_b, f))) for f in os.listdir(a.dir_b) if f.endswith("_stamps.json")]
        out["stamps_equal"] = len(ja) == len(jb) == 1 and ja[0]["stamps"] == jb[0]["stamps"]
    else:
        ma = json.load(open(os.path.join(a.dir_a, "meta.json")))
        mb = json.load(open(os.path.join(a.dir_b, "meta.json")))
        out["frames"] = [len(ma), len(mb)]
        out["meta_equal"] = ma == mb
        diff = []
        for k in range(max(len(ma), len(mb))):
            pa, pb = (os.path.join(d, f"f_{k:05d}.npz") for d in (a.dir_a, a.dir_b))
            if not (os.path.exists(pa) and os.path.exists(pb)):
                diff.append(k)
                continue
            za, zb = np.load(pa), np.load(pb)
            if sorted(za.files) != sorted(zb.files) or any(
                    za[n].dtype != zb[n].dtype or not np.array_equal(za[n], zb[n]) for n in za.files):
                diff.append(k)
    out["different"] = diff[:20]
    out["n_different"] = len(diff)
    out["equal"] = not diff and out.get("stamps_equal", out.get("meta_equal")) and out["frames"][0] == out["frames"][1]
    print(json.dumps(out))
    return 0 if out["equal"] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("src")
    r.add_argument("--bags", required=True)
    r.add_argument("--gate-root", required=True)
    r.add_argument("--decoded-bags", default="")
    r.add_argument("--decoded-root", default=None)
    r.add_argument("--report", required=True)
    c = sub.add_parser("compare")
    c.add_argument("kind", choices=["gate", "decoded"])
    c.add_argument("dir_a")
    c.add_argument("dir_b")
    a = ap.parse_args()
    return run(a) if a.cmd == "run" else compare(a)


if __name__ == "__main__":
    sys.exit(main())
