#!/usr/bin/env python3
"""Process the 20-minute ride `new_data` (221 split files, ~90 GB unpacked, tar members in random order)
through ONE node-faithful detector instance in temporal order, without ever holding the ride on disk.

Producer thread: streams new_data.zst from the organizers' Yandex Disk folder (HTTP with Range-resume on
connection loss) -> zstd -> tar; members whose split number is inside the current pass window are stored
re-compressed (zstd level 3, ~80 MB each instead of 408 MB); the others are skipped. Passes repeat over the
stream with consecutive windows until all splits were delivered.
Consumer (main thread): waits for split N (N = 0, 1, 2, ...), decompresses it to a temporary .db3, feeds every
message to the same NodeReplica (judge_runner.py: node decode, continuity rules, decision rule), appends
the per-frame records, deletes the split. State (tracks, calibration, health) is continuous across splits.

  stream_new_data.py --work /tmp/claude-0/judge_data/nd --out out/new_data --window 111
"""
import argparse
import csv
import json
import os
import re
import sys
import tarfile
import threading
import time
import urllib.request

import zstandard

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_runner import CSV_COLS, NodeReplica, csv_row, iter_raw, record  # noqa: E402

URL = "https://disk.yandex.ru/d/N8IUpAyd7jyvow"
MEMBER = "new_data.zst"
N_SPLITS = 221


def resolve():
    sys.path.insert(0, "/home/user/ReSense/scripts")
    from unpack_dataset import resolve_yadisk
    return resolve_yadisk(URL, MEMBER)


class ResumableHTTP:
    """File-like reader over an HTTP URL that reconnects with a Range header after a failure."""

    def __init__(self, log):
        self.pos, self.log, self.resp, self.fails = 0, log, None, 0
        self._open()

    def _open(self):
        href = resolve()
        req = urllib.request.Request(href, headers={"Range": f"bytes={self.pos}-"} if self.pos else {})
        self.resp = urllib.request.urlopen(req, timeout=120)
        self.log(f"http open at {self.pos} status {self.resp.status}")

    def read(self, n=-1):
        while True:
            try:
                b = self.resp.read(n)
                self.pos += len(b)
                return b
            except Exception as e:  # noqa: BLE001
                self.fails += 1
                self.log(f"http read failed at {self.pos}: {e!r}; reconnect #{self.fails}")
                if self.fails > 50:
                    raise
                time.sleep(min(30, 2 * self.fails))
                try:
                    self._open()
                except Exception as e2:  # noqa: BLE001
                    self.log(f"reopen failed: {e2!r}")

    def readable(self):
        return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--window", type=int, default=111)
    p.add_argument("--first", type=int, default=0)
    p.add_argument("--last", type=int, default=N_SPLITS - 1)
    a = p.parse_args()
    os.makedirs(a.work, exist_ok=True)
    logf = open(a.out + ".stream.log", "a")
    lock = threading.Lock()

    def log(msg):
        with lock:
            logf.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
            logf.flush()

    done_producing = threading.Event()
    windows = [(lo, min(lo + a.window, a.last + 1)) for lo in range(a.first, a.last + 1, a.window)]
    consumed = {"next": a.first}

    def producer():
        try:
            for wi, (lo, hi) in enumerate(windows):
                # wait until the previous window was consumed far enough to have disk room
                while consumed["next"] < lo - 5 and wi > 0:
                    time.sleep(5)
                log(f"pass {wi}: window {lo}..{hi - 1}")
                http = ResumableHTTP(log)
                reader = zstandard.ZstdDecompressor().stream_reader(http, read_across_frames=True)
                cctx = zstandard.ZstdCompressor(level=3, threads=2)
                got = 0
                with tarfile.open(fileobj=reader, mode="r|") as tar:
                    for m in tar:
                        mm = re.search(r"new_data_(\d+)\.db3$", m.name)
                        if not mm or not m.isfile():
                            continue
                        n = int(mm.group(1))
                        if not (lo <= n < hi):
                            continue
                        f = tar.extractfile(m)
                        tmp = os.path.join(a.work, f"new_data_{n}.db3.zst.part")
                        with open(tmp, "wb") as fo:
                            cctx.copy_stream(f, fo)
                        os.rename(tmp, tmp[:-5])
                        got += 1
                        log(f"pass {wi}: stored split {n} ({got}/{hi - lo}), http pos {http.pos / 1e9:.2f} GB")
                        if got == hi - lo:
                            break
                log(f"pass {wi} done: {got} splits")
        except Exception as e:  # noqa: BLE001
            log(f"PRODUCER FAILED: {e!r}")
        finally:
            done_producing.set()

    th = threading.Thread(target=producer, daemon=True)
    th.start()

    rep = NodeReplica()
    dctx = zstandard.ZstdDecompressor()
    idx = 0
    mode = "a" if a.first > 0 else "w"
    fj = open(a.out + ".jsonl", mode)
    fc = open(a.out + ".csv", mode, newline="")
    w = csv.writer(fc)
    if mode == "w":
        w.writerow(CSV_COLS + ["split"])
    splits_meta = []
    t0 = time.time()
    for n in range(a.first, a.last + 1):
        path = os.path.join(a.work, f"new_data_{n}.db3.zst")
        while not os.path.exists(path):
            if done_producing.is_set() and not os.path.exists(path):
                log(f"split {n} never arrived; stopping")
                break
            time.sleep(2)
        if not os.path.exists(path):
            break
        raw_db = os.path.join(a.work, f"new_data_{n}.db3")
        with open(path, "rb") as fi, open(raw_db, "wb") as fo:
            dctx.copy_stream(fi, fo)
        os.remove(path)
        k = 0
        for ts, topic, raw in iter_raw(raw_db):
            msg, stamp, res, dec_ms, det_ms = rep.process_raw(raw, topic, idx)
            r = record(idx, ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id, topic)
            r["split"] = n
            fj.write(json.dumps(r) + "\n")
            w.writerow(csv_row(r) + [n])
            idx += 1
            k += 1
        os.remove(raw_db)
        fj.flush()
        fc.flush()
        consumed["next"] = n + 1
        splits_meta.append({"split": n, "frames": k})
        log(f"consumed split {n}: {k} frames (total {idx}, {time.time() - t0:.0f} s)")
    json.dump({"frames": idx, "splits": splits_meta, "resets": rep.resets}, open(a.out + ".meta.json", "w"), indent=1)
    log(f"ALL DONE: {idx} frames, resets {len(rep.resets)}")


if __name__ == "__main__":
    main()
