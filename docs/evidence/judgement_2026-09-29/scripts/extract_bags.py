"""Extract only the named bags from the organizers' nested archive (Датасет.zip -> датасет.zip ->
archive/for_hackathon.zst -> tar), streaming, so the 22 GB of bags never need to be on disk at once.

    python extract_bags.py dataset.zip doubleT_obstacle,roundT_doubleT /home/user/data
"""
import sys
import tarfile
import zipfile

import zstandard


def main(archive: str, bags: str, out: str) -> None:
    want = set(bags.split(","))
    outer = zipfile.ZipFile(archive)
    inner = zipfile.ZipFile(outer.open("Датасет/датасет.zip"))      # stored, so seekable
    member = next(n for n in inner.namelist() if n.endswith("for_hackathon.zst"))
    with inner.open(member) as fh, tarfile.open(fileobj=zstandard.ZstdDecompressor().stream_reader(fh),
                                                 mode="r|") as tar:
        for m in tar:
            parts = m.name.split("/")
            if (len(parts) > 1 and parts[1] in want) or (m.isdir() and parts[-1] == "for_hackathon"):
                tar.extract(m, out)
                if m.isfile():
                    print("extracted", m.name, m.size, file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:4])
