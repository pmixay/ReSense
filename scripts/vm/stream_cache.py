#!/usr/bin/env python3
"""Stream the organizers' 20-minute ride and build its frame cache one split file at a time.

``new_data.zst`` (17 GB on Yandex Disk) is a zstd tar of one rosbag2 bag: 221 split files
``new_data_<N>.db3`` of 408 MB (90 GB unpacked) and ``metadata.yaml`` as the last member. This
reads the archive with the streaming reader of ``scripts/unpack_dataset.py`` (link -> zstd -> tar,
no 17 GB copy), writes each split file to disk, hands it to ``scripts/cache_frames.py <file>
<cache> --every 1 --int16 --stamps`` as soon as it is complete (``--jobs`` workers) and deletes it
afterwards unless ``--keep`` is given. At most ``--max-pending`` split files wait on disk.

    python scripts/vm/stream_cache.py --cache /data/cache/new_data --tmp /data/.new_data_stream
    python scripts/vm/stream_cache.py --cache /data/cache/new_data --keep /data/new_data    # the bag too (90 GB)
    python scripts/vm/stream_cache.py --cache /data/cache/new_data --from-dir /data/new_data   # no download

A split file whose ``new_data_<N>_stamps.json`` (written last by cache_frames.py) is already in
the cache is not processed again: the stream is read through it, so an interrupted run resumes.
The cache is what ``scripts/eval_real.py`` / ``scripts/regression_gate.py`` read as ``<cache>/new_data``.
Exit 0 when every split file is cached, 1 when some failed or are missing, 2 on bad arguments.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(ROOT, "scripts")
RIDE_URL = "https://disk.yandex.ru/d/N8IUpAyd7jyvow"
RIDE_FILES = 221                     # DATASET.md "Extended dataset"
CHUNK = 16 << 20


def natural(name: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def cached(cache: str, stem: str) -> bool:
    return os.path.exists(os.path.join(cache, f"{stem}_stamps.json"))


def free_bytes(path: str) -> int:
    return shutil.disk_usage(path).free


def listed_files(metadata: str) -> int:
    """How many split files a rosbag2 metadata.yaml lists (0 when it cannot be read)."""
    try:
        lines = open(metadata, encoding="utf-8").read().splitlines()
    except OSError:
        return 0
    n, inside = 0, False
    for line in lines:
        if line.strip() == "relative_file_paths:":
            inside = True
        elif inside and line.strip().startswith("- "):
            n += 1
        elif inside:
            break
    return n


class Worker:
    """Runs cache_frames.py on split files, deletes them unless kept, counts results."""

    def __init__(self, cache: str, python: str, keep: bool, jobs: int, max_pending: int):
        self.cache, self.python, self.keep = cache, python, keep
        self.pool = ThreadPoolExecutor(max_workers=jobs)
        self.slots = threading.BoundedSemaphore(max_pending)
        self.lock = threading.Lock()
        self.ok, self.failed, self.frames = [], [], 0
        self.futures = []

    def submit(self, path: str):
        self.futures.append(self.pool.submit(self._run, path))

    def _run(self, path: str):
        stem = os.path.basename(path)[:-4]
        t0 = time.time()
        env = dict(os.environ, PYTHONPATH=ROOT + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
                   OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
        cmd = [self.python, os.path.join(SCRIPTS, "cache_frames.py"), path, self.cache,
               "--every", "1", "--int16", "--stamps"]
        try:
            r = subprocess.run(cmd, env=env, capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip().splitlines()
            m = re.search(r"cached (\d+) frames", r.stdout)
            with self.lock:
                if r.returncode == 0 and cached(self.cache, stem):
                    self.ok.append(stem)
                    self.frames += int(m.group(1)) if m else 0
                    print(f"  cached {stem}: {m.group(1) if m else '?'} frames in {time.time() - t0:.0f} s "
                          f"({len(self.ok)} of {RIDE_FILES} split files done)", flush=True)
                else:
                    self.failed.append(stem)
                    print(f"  FAILED {stem} (exit {r.returncode}): {out[-1] if out else ''}", flush=True)
        finally:
            if not self.keep:
                try:
                    os.remove(path)
                except OSError:
                    pass
            self.slots.release()

    def wait(self):
        for f in self.futures:
            f.result()
        self.pool.shutdown()


def from_dir(a, worker: Worker) -> set:
    files = sorted(glob.glob(os.path.join(a.from_dir, "new_data_*.db3")), key=natural)
    if not files:
        sys.exit(f"no new_data_*.db3 in {a.from_dir}")
    seen = set()
    for f in files:
        stem = os.path.basename(f)[:-4]
        seen.add(stem)
        if cached(a.cache, stem):
            continue
        worker.slots.acquire()
        worker.submit(f)
    return seen


def from_stream(a, worker: Worker, dest: str) -> set:
    sys.path.insert(0, SCRIPTS)
    import zstandard

    from unpack_dataset import open_zst_stream     # scripts/unpack_dataset.py: link -> zstd payload

    raw = open_zst_stream(a.source, a.member)
    reader = zstandard.ZstdDecompressor().stream_reader(raw, read_across_frames=True)
    seen, t0, nbytes = set(), time.time(), 0
    with tarfile.open(fileobj=reader, mode="r|") as tar:
        for member in tar:
            base = os.path.basename(member.name.removeprefix("./"))
            nbytes += member.size
            if not member.isfile():
                continue
            if base == "metadata.yaml":
                fh = tar.extractfile(member)
                with open(os.path.join(dest, "metadata.yaml"), "wb") as out:
                    shutil.copyfileobj(fh, out)
                continue
            if not (base.startswith("new_data_") and base.endswith(".db3")):
                continue
            stem = base[:-4]
            seen.add(stem)
            target = os.path.join(dest, base)
            kept_whole = a.keep and os.path.exists(target) and os.path.getsize(target) == member.size
            if cached(a.cache, stem) and (not a.keep or kept_whole):
                print(f"  skip {stem} (cached{', kept' if a.keep else ''})", flush=True)
                continue
            worker.slots.acquire()
            if free_bytes(dest) < member.size + a.min_free_gb * 1e9:
                worker.slots.release()
                sys.exit(f"disk full: {free_bytes(dest) / 1e9:.1f} GB free on {dest}, "
                         f"need {member.size / 1e9:.1f} + {a.min_free_gb} GB; nothing kept of {stem}")
            if kept_whole:
                worker.submit(target)
                continue
            src = tar.extractfile(member)
            with open(target + ".part", "wb") as out:
                shutil.copyfileobj(src, out, CHUNK)
            os.replace(target + ".part", target)
            rate = nbytes / 1e6 / max(time.time() - t0, 1e-3)
            print(f"{time.time() - t0:7.0f} s  {base} ({member.size / 1e6:.0f} MB, stream {rate:.1f} MB/s unpacked)",
                  flush=True)
            worker.submit(target)
    return seen


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", required=True, help="cache directory of the ride (e.g. /data/cache/new_data)")
    p.add_argument("--source", default=RIDE_URL, help="Yandex Disk link, URL or local new_data.zst (default: the organizers' link)")
    p.add_argument("--member", default="new_data.zst", help="file in the Yandex Disk folder (default new_data.zst)")
    p.add_argument("--keep", default="", metavar="DIR", help="keep the bag: write the split files and metadata.yaml here")
    p.add_argument("--tmp", default="", metavar="DIR", help="where split files wait for caching when not kept")
    p.add_argument("--from-dir", default="", metavar="DIR", help="cache the split files of an existing bag directory")
    p.add_argument("--jobs", type=int, default=2, help="parallel cache_frames.py workers (default 2)")
    p.add_argument("--max-pending", type=int, default=4, help="split files on disk waiting for a worker (default 4)")
    p.add_argument("--min-free-gb", type=float, default=2.0, help="stop when less than this would remain free")
    p.add_argument("--python", default=sys.executable, help="python for cache_frames.py (needs rosbags, numpy)")
    p.add_argument("--dry-run", action="store_true", help="print what would be done")
    a = p.parse_args(argv)
    if a.from_dir and a.keep:
        p.error("--from-dir and --keep exclude each other")
    dest = a.keep or a.tmp or os.path.join(os.path.dirname(os.path.abspath(a.cache)), ".new_data_stream")
    mode = f"from {a.from_dir}" if a.from_dir else f"stream {a.source} ({a.member}) -> {dest}"
    print(f"ride: {mode}; cache {a.cache}; keep bag: {bool(a.keep)}; jobs {a.jobs}; at most {a.max_pending} "
          f"split files ({a.max_pending * 0.41:.1f} GB) waiting", flush=True)
    if a.dry_run:
        return 0
    os.makedirs(a.cache, exist_ok=True)
    if not a.from_dir:
        os.makedirs(dest, exist_ok=True)
    worker = Worker(a.cache, a.python, keep=bool(a.keep) or bool(a.from_dir), jobs=max(1, a.jobs),
                    max_pending=max(1, a.max_pending))
    t0 = time.time()
    try:
        seen = from_dir(a, worker) if a.from_dir else from_stream(a, worker, dest)
    finally:
        worker.wait()
    expected = listed_files(os.path.join(a.from_dir or dest, "metadata.yaml")) or RIDE_FILES
    if not a.keep and not a.from_dir:
        shutil.rmtree(dest, ignore_errors=True)
    done = sorted({os.path.basename(f)[:-len("_stamps.json")]
                   for f in glob.glob(os.path.join(a.cache, "new_data_*_stamps.json"))}, key=natural)
    missing = sorted(seen - set(done), key=natural)
    print(f"ride cache: {len(done)} of {expected} split files in {a.cache} "
          f"({worker.frames} frames cached in this run, {time.time() - t0:.0f} s); failed: {worker.failed or 'none'}")
    if missing:
        print(f"missing: {', '.join(missing[:20])}{' ...' if len(missing) > 20 else ''}")
    return 0 if len(done) >= expected and not worker.failed else 1


if __name__ == "__main__":
    sys.exit(main())
