"""29.09 (new): ride_producer.py with a reconnecting download. On 29.09 the single long-lived download
of ride_producer.py fell from ~40 MB/s to ~1 MB/s after ~5 GB (16:04 UTC), while a fresh connection
with an HTTP Range request got ~60 MB/s. This version reads new_data.zst through HTTP Range requests,
opening a fresh connection every CHUNK bytes (and on a slow or failed read), feeds the same zstd/tar
stream, and skips (reads through without writing) the split files already written by an earlier
producer run (listed in LOG). Output, pacing (MAX_PENDING) and log format are those of
ride_producer.py.

    RIDE=/home/user/data/ride LOG=ride/producer.log python ride_producer_range.py
"""
import json
import os
import sys
import tarfile
import time
import urllib.error
import urllib.request

import zstandard

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../scripts"))
from unpack_dataset import resolve_yadisk  # noqa: E402

OUT = os.environ.get("RIDE", "/home/user/data/ride")
LOG = os.environ.get("LOG", "ride/producer.log")
MAX_PENDING = 4
CHUNK = 512 << 20          # bytes per connection
SLOW_S = 20.0              # reconnect when one 4 MB read takes longer than this


class RangeReader:
    def __init__(self, public_url: str, member: str):
        self.public_url, self.member = public_url, member
        self.href = resolve_yadisk(public_url, member)
        self.pos, self.resp, self.left, self.reconnects = 0, None, 0, 0

    def _open(self):
        if self.resp is not None:
            self.resp.close()
        for attempt in range(8):
            try:
                req = urllib.request.Request(self.href, headers={"Range": f"bytes={self.pos}-{self.pos + CHUNK - 1}"})
                self.resp = urllib.request.urlopen(req, timeout=60)
                self.left = CHUNK
                self.reconnects += 1
                return
            except urllib.error.HTTPError as e:
                if e.code == 416:                         # past the end of the file
                    self.resp, self.left = None, -1
                    return
                print("reconnect failed", self.pos, repr(e), file=sys.stderr, flush=True)
                time.sleep(2 + 2 * attempt)
                self.href = resolve_yadisk(self.public_url, self.member)
            except Exception as e:  # noqa: BLE001 - retry with a freshly resolved link
                print("reconnect failed", self.pos, repr(e), file=sys.stderr, flush=True)
                time.sleep(2 + 2 * attempt)
                self.href = resolve_yadisk(self.public_url, self.member)
        raise RuntimeError("download failed")

    def read(self, n: int = -1) -> bytes:
        n = 1 << 22 if n is None or n < 0 else n
        while True:
            if self.resp is None or self.left <= 0:
                self._open()
                if self.left < 0:
                    return b""
            t0 = time.time()
            try:
                b = self.resp.read(min(n, self.left))
            except Exception as e:  # noqa: BLE001
                print("read failed", self.pos, repr(e), file=sys.stderr, flush=True)
                self.left = 0
                continue
            if not b:
                if self.left == CHUNK:                    # nothing at all at this offset: end of file
                    return b""
                self.left = 0                             # connection ended: reopen at pos
                continue
            self.pos += len(b)
            self.left -= len(b)
            if time.time() - t0 > SLOW_S:
                self.left = 0                             # slow connection: next read reconnects
            return b


def main():
    done = set()
    if os.path.exists(LOG):
        for line in open(LOG):
            if line.startswith("{"):
                done.add(os.path.basename(json.loads(line)["member"]))
    src_stream = RangeReader("https://disk.yandex.ru/d/N8IUpAyd7jyvow", "new_data.zst")
    stream = zstandard.ZstdDecompressor().stream_reader(src_stream, read_size=1 << 22)
    log = open(LOG, "a", buffering=1)
    skipped = 0
    with tarfile.open(fileobj=stream, mode="r|") as tar:
        for m in tar:
            if not m.isfile():
                continue
            name = os.path.basename(m.name)
            if name in done:
                skipped += 1
                continue
            while len([f for f in os.listdir(OUT) if f.endswith(".db3")]) >= MAX_PENDING:
                time.sleep(0.5)
            src = tar.extractfile(m)
            tmp = os.path.join(OUT, name + ".part")
            with open(tmp, "wb") as fh:
                while block := src.read(1 << 22):
                    fh.write(block)
            os.rename(tmp, os.path.join(OUT, name))
            log.write(json.dumps({"t": time.time(), "member": m.name, "size": m.size,
                                  "reconnects": src_stream.reconnects, "skipped": skipped}) + "\n")
    log.write("DONE\n")


if __name__ == "__main__":
    main()
