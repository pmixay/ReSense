#!/usr/bin/env python3
"""Unpack the organizers' dataset archive without intermediate copies.

The download is nested: ``Датасет.zip`` (stored) → ``Датасет/датасет.zip`` (deflate) →
``archive/for_hackathon.zst`` (zstd-compressed tar, ~4 GB) → ``for_hackathon/<bag>/``
(six ROS 2 bags, ~22 GB). Unpacking it by hand needs ~30 GB of scratch space; this script
streams zip → zip → zstd → tar and writes only the bags you ask for.

    python scripts/unpack_dataset.py Датасет.zip --list
    python scripts/unpack_dataset.py Датасет.zip --out /data                       # all six bags
    python scripts/unpack_dataset.py Датасет.zip --out /data --only doubleT_obstacle,roundT_doubleT
    python scripts/unpack_dataset.py Датасет.zip --out /tmp/meta --metadata-only   # just the metadata.yaml files

The extended dataset (``new_data.zst``, 17 GB, a tar.zst of rosbag2 split files ``new_data/
new_data_<N>.db3``) is streamed the same way, from a downloaded file or straight from the
organizers' Yandex Disk link (the public API resolves the link to a download URL; nothing is
written but the extracted files):

    python scripts/unpack_dataset.py https://disk.yandex.ru/d/N8IUpAyd7jyvow --list
    python scripts/unpack_dataset.py https://disk.yandex.ru/d/N8IUpAyd7jyvow --out /data     # /data/new_data/*.db3
    python scripts/unpack_dataset.py new_data.zst --out /data --only new_data
    python scripts/unpack_dataset.py new_data.zst --out /data --only new_data_127.db3,new_data_128.db3

Needs the ``zstandard`` package (installed with ``pip install -e ".[dev]"``). Also accepts the
inner ``датасет.zip`` or the bare ``for_hackathon.zst`` as input.
"""
from __future__ import annotations

import argparse
import json
import sys
import tarfile
import time
import urllib.parse
import urllib.request
import zipfile

YADISK_API = "https://cloud-api.yandex.net/v1/disk/public/resources"


def resolve_yadisk(public_url: str, member: str = "") -> str:
    """Turn a Yandex Disk public link (a file, or a folder holding one *.zst) into a direct
    download URL via the public REST API (no account needed)."""
    key = urllib.parse.quote(public_url, safe="")
    with urllib.request.urlopen(f"{YADISK_API}?public_key={key}&limit=200", timeout=60) as r:
        info = json.load(r)
    path = ""
    if info.get("type") == "dir":
        items = info.get("_embedded", {}).get("items", [])
        wanted = [i for i in items if i.get("type") == "file"
                  and (i["name"] == member if member else i["name"].endswith(".zst"))]
        if len(wanted) != 1:
            sys.exit(f"{public_url}: expected one .zst file in the folder, found "
                     f"{[i['name'] for i in items]} (use --member NAME)")
        path = "&path=" + urllib.parse.quote(wanted[0]["path"], safe="")
        print(f"{wanted[0]['name']}: {wanted[0]['size'] / 1e9:.2f} GB, modified {wanted[0].get('modified')}, "
              f"sha256 {wanted[0].get('sha256')}", file=sys.stderr)
    with urllib.request.urlopen(f"{YADISK_API}/download?public_key={key}{path}", timeout=60) as r:
        return json.load(r)["href"]


def open_zst_stream(path: str, member: str = ""):
    """Return a readable binary stream positioned at the start of the zstd payload."""
    if path.startswith(("http://", "https://")):
        href = resolve_yadisk(path, member) if "disk.yandex" in path else path
        return urllib.request.urlopen(href, timeout=120)
    if path.endswith(".zst"):
        return open(path, "rb")
    outer = zipfile.ZipFile(path)
    names = outer.namelist()
    inner_zip = [n for n in names if n.lower().endswith(".zip")]
    zst = [n for n in names if n.endswith(".zst")]
    if zst:
        return outer.open(zst[0])
    if not inner_zip:
        sys.exit(f"{path}: no .zip or .zst member found ({names})")
    inner = zipfile.ZipFile(outer.open(inner_zip[0]))   # the outer member is stored → seekable
    zst = [n for n in inner.namelist() if n.endswith(".zst")]
    if not zst:
        sys.exit(f"{inner_zip[0]}: no .zst member found ({inner.namelist()})")
    return inner.open(zst[0])


def selected_member(name: str, only: set[str]) -> bool:
    """Select either a nested organizer bag or the extended ride's flat split files.

    The original archive uses ``for_hackathon/<bag>/...``; the extended one uses
    ``new_data/new_data_<N>.db3``. Accepting the top-level directory also lets
    ``--only new_data`` select all split files as documented.
    """
    parts = name.split("/")
    return not only or parts[0] in only or (len(parts) > 1 and parts[1] in only)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archive", help="Датасет.zip, датасет.zip, for_hackathon.zst, new_data.zst, or a Yandex Disk "
                                   "public link / direct https URL of a .zst")
    p.add_argument("--member", default="", help="file name to pick when the Yandex Disk link is a folder "
                                                "(default: the only *.zst in it)")
    p.add_argument("--out", default="/data", help="directory that will contain for_hackathon/ (default /data)")
    p.add_argument("--only", default="", help="comma-separated bag names or split filenames to extract (default: all)")
    p.add_argument("--list", action="store_true", help="only list the archive members")
    p.add_argument("--metadata-only", action="store_true",
                   help="extract only the metadata.yaml of each bag (topic, frame count, duration)")
    a = p.parse_args()
    try:
        import zstandard
    except ImportError:
        sys.exit("pip install zstandard   (or: pip install -e '.[dev]')")

    only = {b.strip() for b in a.only.split(",") if b.strip()}
    raw = open_zst_stream(a.archive, a.member)
    dctx = zstandard.ZstdDecompressor()
    reader = dctx.stream_reader(raw, read_across_frames=True)
    t0 = time.time()
    n_files, n_bytes = 0, 0
    with tarfile.open(fileobj=reader, mode="r|") as tar:
        for member in tar:
            if a.list:
                print(f"{member.size:>14,d}  {member.name}")
                continue
            if not selected_member(member.name, only):
                continue
            if a.metadata_only and not member.name.endswith("metadata.yaml"):
                continue
            if member.isdir() or member.isfile():
                tar.extract(member, a.out)
                if member.isfile():
                    n_files += 1
                    n_bytes += member.size
                    print(f"{time.time() - t0:7.0f} s  {member.size / 1e9:6.2f} GB  {member.name}", flush=True)
    if not a.list:
        print(f"extracted {n_files} files, {n_bytes / 1e9:.1f} GB to {a.out} in {time.time() - t0:.0f} s")
        if only:
            print("bags:", ", ".join(sorted(only)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
