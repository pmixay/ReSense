"""Stream the organizers' 20-minute ride (new_data.zst, 17 GB, Yandex Disk) and write its rosbag2
split files one at a time into $RIDE, pausing while MAX_PENDING wait for ride_consumer.py (the
unpacked ride is 90 GB). The splits come out of the archive in no particular order.

    RIDE=/home/user/data/ride LOG=ride/producer.log python ride_producer.py
"""
import json
import os
import sys
import tarfile
import time
import urllib.request

import zstandard

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../scripts"))
from unpack_dataset import resolve_yadisk  # noqa: E402

OUT = os.environ.get("RIDE", "/home/user/data/ride")
LOG = os.environ.get("LOG", "ride/producer.log")
MAX_PENDING = 4


def main():
    href = resolve_yadisk("https://disk.yandex.ru/d/N8IUpAyd7jyvow", "new_data.zst")
    stream = zstandard.ZstdDecompressor().stream_reader(urllib.request.urlopen(href, timeout=300))
    log = open(LOG, "a", buffering=1)
    with tarfile.open(fileobj=stream, mode="r|") as tar:
        for m in tar:
            if not m.isfile():
                continue
            while len([f for f in os.listdir(OUT) if f.endswith(".db3")]) >= MAX_PENDING:
                time.sleep(0.5)
            src = tar.extractfile(m)
            name = os.path.basename(m.name)
            tmp = os.path.join(OUT, name + ".part")
            with open(tmp, "wb") as fh:
                while block := src.read(1 << 22):
                    fh.write(block)
            os.rename(tmp, os.path.join(OUT, name))
            log.write(json.dumps({"t": time.time(), "member": m.name, "size": m.size}) + "\n")
    log.write("DONE\n")


if __name__ == "__main__":
    main()
