"""Upload staging areas, resumable, finalized into a recording.

    uploads/<id>/meta.json          {id, name, created_at}
    uploads/<id>/files/<rel path>   finished files: a whole-file PUT, or a chunked file once complete
    uploads/<id>/parts/<key>.json   a chunked file: path, size, chunk size, fingerprint, received bitmap
    uploads/<id>/parts/<key>.part   its data, written in place at chunk offsets (sparse until complete)

A big file goes up in chunks (``declare``, then ``write_chunk`` per chunk, in any order and in
parallel). Every chunk is checked (its length, the CRC-32 of its raw bytes, an optional gzip
transfer encoding) and flushed to disk before it counts as received, so an interrupted upload
resumes at the missing chunks, also after a server restart. ``start_finalize`` runs in a
background thread (unpacking a 25 GB zip takes minutes) and reports its stage; the API waits for
it or lets the client poll ``status``. Writes, finalize and delete exclude each other: no file is
added while the area is being finalized, and an area is not removed under a running finalize."""
from __future__ import annotations

import base64
import errno
import hashlib
import logging
import os
import shutil
import threading
import time
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator

from resense_web.probe import Probe, ProbeError, find_input, probe_path, safe_extract_zip, zip_total_size
from resense_web.settings import Settings
from resense_web.util import atomic_write_json, is_within, new_id, now_iso, read_json, tree_size, valid_id

log = logging.getLogger("resense_web.uploads")

MIN_CHUNK = 64 * 1024
MAX_CHUNK = 64 * 1024 ** 2
MAX_CHUNKS = 1_000_000
DISK_MARGIN = 256 * 1024 ** 2
GZIP_SLACK = 64 * 1024            # a gzip body may be slightly bigger than its raw chunk
DECODE_PIECE = 8 * 1024 ** 2      # gzip output per step while streaming (bounds memory)
CLEANUP_PERIOD_S = 3600.0
TASK_TTL_S = 1800.0               # a finished finalize stays readable through ``status`` this long
ENCODINGS = ("identity", "gzip")
TEMP_MARKERS = (".part-", ".unpacking-")


class UploadError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


GONE = "Загрузка не найдена"
BAD_GZIP = "Данные повреждены при передаче (gzip не распаковывается) — они будут отправлены снова"


# --- transfer decoding ----------------------------------------------------------------------------

def decode_body(body: bytes | bytearray, encoding: str, expected: int) -> bytes | bytearray:
    """The raw bytes of a chunk sent with ``encoding``; UploadError 400 (the client sends it again)
    when it does not decode or its length is not ``expected``."""
    if encoding == "gzip":
        z = zlib.decompressobj(wbits=31)
        try:
            raw = z.decompress(body, expected + 1)
        except zlib.error:
            raise UploadError(400, BAD_GZIP) from None
        if not z.eof or z.unconsumed_tail or z.unused_data:
            raise UploadError(400, BAD_GZIP)
    elif encoding == "identity":
        raw = body
    else:
        raise UploadError(422, "Неизвестное сжатие передачи (нужно identity или gzip)")
    if len(raw) != expected:
        raise UploadError(400, f"Часть файла пришла не полностью ({len(raw)} из {expected} байт) — она будет отправлена снова")
    return raw


class StreamDecoder:
    """Incremental decoding of a streamed body (identity or gzip) with the CRC-32 and the length of
    the raw bytes; ``limit`` stops a body that inflates beyond the size the client declared."""

    def __init__(self, encoding: str, limit: int | None = None):
        if encoding not in ENCODINGS:
            raise UploadError(422, "Неизвестное сжатие передачи (нужно identity или gzip)")
        self._z = zlib.decompressobj(wbits=31) if encoding == "gzip" else None
        self.limit = limit
        self.size = 0
        self.crc = 0

    def _inflate(self, data: bytes) -> Iterator[bytes]:
        buf = data
        while buf:
            try:
                out = self._z.decompress(buf, DECODE_PIECE)
            except zlib.error:
                raise UploadError(400, BAD_GZIP) from None
            if self._z.unused_data:
                raise UploadError(400, BAD_GZIP)
            if out:
                yield out
            buf = self._z.unconsumed_tail

    def feed(self, data: bytes) -> Iterator[bytes]:
        for piece in ((data,) if self._z is None else self._inflate(data)):
            self.size += len(piece)
            if self.limit is not None and self.size > self.limit:
                raise UploadError(400, "Файл пришёл длиннее заявленного размера")
            self.crc = zlib.crc32(piece, self.crc)
            yield piece

    def finish(self) -> None:
        if self._z is not None and not self._z.eof:
            raise UploadError(400, BAD_GZIP)


def _pwrite_all(fd: int, data, offset: int) -> None:
    view = memoryview(data)
    while view:
        n = os.pwrite(fd, view, offset)
        view, offset = view[n:], offset + n


def _sync(fd: int) -> None:
    (getattr(os, "fdatasync", None) or os.fsync)(fd)


# --- chunked files --------------------------------------------------------------------------------

def file_key(rel: PurePosixPath | str) -> str:
    return hashlib.sha256(str(rel).encode("utf-8")).hexdigest()[:24]


@dataclass
class ChunkedFile:
    path: str                       # relative POSIX path inside the upload
    size: int
    chunk_size: int
    fingerprint: str
    bitmap: bytearray
    complete: bool = False
    created_at: str = ""
    count: int = 0                  # chunks received

    @property
    def n_chunks(self) -> int:
        return -(-self.size // self.chunk_size)

    def chunk_len(self, i: int) -> int:
        return min(self.chunk_size, self.size - i * self.chunk_size)

    def has(self, i: int) -> bool:
        return bool(self.bitmap[i >> 3] & (1 << (i & 7)))

    def mark(self, i: int) -> None:
        if not self.has(i):
            self.bitmap[i >> 3] |= 1 << (i & 7)
            self.count += 1

    def unmark(self, i: int) -> None:
        if self.has(i):
            self.bitmap[i >> 3] &= ~(1 << (i & 7)) & 0xFF
            self.count -= 1

    @property
    def received_bytes(self) -> int:
        if self.complete:
            return self.size
        n = self.count * self.chunk_size
        last = self.n_chunks - 1
        if last >= 0 and self.has(last):
            n -= self.chunk_size - self.chunk_len(last)
        return n

    def missing(self) -> list[list[int]]:
        """Ranges ``[first, last]`` of the chunks still to send."""
        if self.complete:
            return []
        out: list[list[int]] = []
        start = None
        for i in range(self.n_chunks):
            if self.has(i):
                if start is not None:
                    out.append([start, i - 1])
                    start = None
            elif start is None:
                start = i
        if start is not None:
            out.append([start, self.n_chunks - 1])
        return out

    def to_api(self, missing: bool = True) -> dict:
        d = {"path": self.path, "size_bytes": self.size, "chunk_size": self.chunk_size, "n_chunks": self.n_chunks,
             "received_chunks": self.n_chunks if self.complete else self.count,
             "received_bytes": self.received_bytes, "complete": self.complete}
        if missing:
            d["missing"] = self.missing()
        return d

    def to_json(self) -> dict:
        return {"path": self.path, "size": self.size, "chunk_size": self.chunk_size, "fingerprint": self.fingerprint,
                "bitmap": base64.b64encode(bytes(self.bitmap)).decode("ascii"), "complete": self.complete,
                "created_at": self.created_at}

    @classmethod
    def from_json(cls, d: dict) -> "ChunkedFile":
        cf = cls(path=str(d["path"]), size=int(d["size"]), chunk_size=int(d["chunk_size"]),
                 fingerprint=str(d.get("fingerprint") or ""), bitmap=bytearray(base64.b64decode(d.get("bitmap") or "")),
                 complete=bool(d.get("complete")), created_at=str(d.get("created_at") or ""))
        need = (cf.n_chunks + 7) // 8
        if len(cf.bitmap) != need:
            cf.bitmap = bytearray(need)
        cf.count = int.from_bytes(cf.bitmap, "little").bit_count()
        return cf


# --- finalize ---------------------------------------------------------------------------------------

class FinalizeTask:
    """One background finalize: its stage for the progress display, then the recording or the
    error (status + Russian message). Finished tasks stay readable for ``TASK_TTL_S``."""

    def __init__(self, upload_id: str, name: str):
        self.upload_id = upload_id
        self.name = name
        self.state = "running"          # running | done | failed
        self.stage = "starting"         # starting | unpacking | probing | saving
        self.fraction: float | None = None
        self.recording: dict | None = None
        self.error: str | None = None
        self.status = 0
        self.bytes = 0
        self.done = threading.Event()
        self.updated = time.monotonic()

    def set(self, stage: str, fraction: float | None = None) -> None:
        self.stage = stage
        self.fraction = None if fraction is None else round(min(1.0, max(0.0, fraction)), 4)
        self.updated = time.monotonic()

    def finish(self, recording: dict) -> None:
        self.recording = recording
        self.state = "done"
        self.updated = time.monotonic()
        self.done.set()

    def fail(self, status: int, message: str) -> None:
        self.status = status
        self.error = message
        self.state = "failed"
        self.updated = time.monotonic()
        self.done.set()

    def progress(self) -> dict:
        return {"stage": self.stage, "fraction": self.fraction}


Register = Callable[[Probe, str, "list[str]", Path], dict]


class UploadStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.uploads_dir
        self._lock = threading.RLock()
        self._used: dict[str, int] = {}             # bytes reserved per area (in-flight and declared included)
        self._inflight: dict[str, int] = {}         # write requests running per area
        self._busy: set[tuple[str, str]] = set()    # (area, path) of whole-file PUTs running
        self._tasks: dict[str, FinalizeTask] = {}
        self._deleted: set[str] = set()
        self._chunked: dict[tuple[str, str], ChunkedFile] = {}
        self._file_locks: dict[tuple[str, str], threading.RLock] = {}
        self._last_cleanup = time.monotonic()

    # -- areas ------------------------------------------------------------------------------------
    def area(self, upload_id: str) -> Path:
        if not valid_id(upload_id) or upload_id in self._deleted:
            raise UploadError(404, GONE)
        d = self.root / upload_id
        if not (d / "meta.json").is_file():
            raise UploadError(404, GONE)
        return d

    def create(self, name: str | None) -> str:
        self.maybe_cleanup()
        upload_id = new_id()
        d = self.root / upload_id
        (d / "files").mkdir(parents=True)
        atomic_write_json(d / "meta.json", {"id": upload_id, "name": (name or "").strip()[:200],
                                            "created_at": now_iso()})
        with self._lock:
            self._used[upload_id] = 0
        return upload_id

    def delete(self, upload_id: str) -> None:
        with self._lock:
            d = self.area(upload_id)
            task = self._tasks.get(upload_id)
            if task is not None and task.state == "running":
                raise UploadError(409, "Загрузка сейчас проверяется на сервере — дождитесь окончания")
            self._deleted.add(upload_id)
            self._forget(upload_id)
        shutil.rmtree(d, ignore_errors=True)

    def meta(self, upload_id: str) -> dict:
        return read_json(self.area(upload_id) / "meta.json", {}) or {}

    def gone(self, upload_id: str) -> bool:
        return upload_id in self._deleted or not (self.root / upload_id / "meta.json").is_file()

    def _forget(self, upload_id: str) -> None:
        self._used.pop(upload_id, None)
        for k in [k for k in self._chunked if k[0] == upload_id]:
            del self._chunked[k]
        for k in [k for k in self._file_locks if k[0] == upload_id]:
            del self._file_locks[k]

    def _file_lock(self, upload_id: str, key: str) -> threading.RLock:
        """Serialises declaring / dropping / completing one path of an area, without holding the
        store's lock (which the event loop takes) through multi-GB unlinks."""
        with self._lock:
            return self._file_locks.setdefault((upload_id, key), threading.RLock())

    def touch(self, upload_id: str) -> None:
        """Mark the area as written now (the stale cleanup counts from the last write)."""
        self._touch(upload_id)

    def _touch(self, upload_id: str) -> None:
        try:
            os.utime(self.root / upload_id / "meta.json")
        except OSError:
            pass

    @contextmanager
    def writing(self, upload_id: str, path: str | None = None) -> Iterator[Path]:
        """Count a write request against the area: refused while it is being finalized, and a
        finalize waits until none is running. ``path`` (whole-file PUTs) is exclusive. A write that
        outlives a DELETE of its area is swept away when it ends."""
        with self._lock:
            d = self.area(upload_id)
            task = self._tasks.get(upload_id)
            if task is not None and task.state == "running":
                raise UploadError(409, "Загрузка уже проверяется на сервере — файлы добавлять нельзя")
            if path is not None:
                if (upload_id, path) in self._busy:
                    raise UploadError(409, f"Файл «{path}» уже передаётся")
                self._busy.add((upload_id, path))
            self._inflight[upload_id] = self._inflight.get(upload_id, 0) + 1
        try:
            yield d
        except OSError:
            if self.gone(upload_id):        # deleted meanwhile: the write has nowhere to go
                raise UploadError(404, "Загрузка отменена") from None
            raise
        finally:
            with self._lock:
                n = self._inflight.get(upload_id, 1) - 1
                if n > 0:
                    self._inflight[upload_id] = n
                else:
                    self._inflight.pop(upload_id, None)
                if path is not None:
                    self._busy.discard((upload_id, path))
                sweep = n <= 0 and upload_id in self._deleted
            if sweep:
                shutil.rmtree(self.root / upload_id, ignore_errors=True)

    def _last_activity(self, d: Path) -> float:
        newest = 0.0
        for p in (d, d / "meta.json", d / "files", d / "parts"):
            try:
                newest = max(newest, p.stat().st_mtime)
            except OSError:
                pass
        try:
            for p in (d / "parts").glob("*.json"):
                newest = max(newest, p.stat().st_mtime)
        except OSError:
            pass
        return newest

    def cleanup_stale(self, max_age_s: float | None = None) -> int:
        """Remove areas without a write for ``max_age_s`` (default: the settings' upload TTL)."""
        max_age_s = self.settings.upload_ttl_s if max_age_s is None else max_age_s
        self._last_cleanup = time.monotonic()
        if not self.root.is_dir():
            return 0
        n = 0
        now = time.time()
        for d in list(self.root.iterdir()):
            try:
                if not d.is_dir():
                    continue
                with self._lock:
                    task = self._tasks.get(d.name)
                    if self._inflight.get(d.name) or (task is not None and task.state == "running"):
                        continue
                newest = self._last_activity(d)
                if newest and now - newest > max_age_s:
                    shutil.rmtree(d, ignore_errors=True)
                    with self._lock:
                        self._forget(d.name)
                    n += 1
            except (OSError, ValueError):
                continue
        return n

    def maybe_cleanup(self) -> None:
        """At most hourly, in the background: a long-running server also drops abandoned uploads."""
        if time.monotonic() - self._last_cleanup < CLEANUP_PERIOD_S:
            return
        self._last_cleanup = time.monotonic()
        threading.Thread(target=self.cleanup_stale, name="uploads-cleanup", daemon=True).start()

    # -- byte accounting --------------------------------------------------------------------------
    def _compute_used(self, upload_id: str) -> int:
        used = tree_size(self.root / upload_id / "files")
        for cf in self._all_chunked(upload_id):
            if not cf.complete:
                used += cf.size
        return used

    def reserve(self, upload_id: str, nbytes: int) -> None:
        """Count ``nbytes`` against the staging area's limit (UploadError 413 when over it)."""
        with self._lock:
            used = self._used.get(upload_id)
            if used is None:
                used = self._compute_used(upload_id)
            if used + nbytes > self.settings.max_upload_bytes:
                self._used[upload_id] = used
                gb = self.settings.max_upload_bytes / 1024 ** 3
                raise UploadError(413, f"Превышен максимальный размер загрузки ({gb:g} ГБ)")
            self._used[upload_id] = used + nbytes

    def release(self, upload_id: str, nbytes: int) -> None:
        with self._lock:
            if upload_id in self._used:
                self._used[upload_id] = max(0, self._used[upload_id] - nbytes)

    def target(self, upload_id: str, rel: PurePosixPath) -> Path:
        files = self.area(upload_id) / "files"
        dest = files.joinpath(*rel.parts)
        # the parents must stay real directories inside the area (no file / symlink in the way)
        cur = files
        for part in rel.parts[:-1]:
            cur = cur / part
            if cur.is_symlink() or (cur.exists() and not cur.is_dir()):
                raise UploadError(409, f"Путь «{rel}» конфликтует с уже загруженным файлом")
        if dest.is_dir() or dest.is_symlink():
            raise UploadError(409, f"Путь «{rel}» конфликтует с уже загруженной папкой")
        if not is_within(dest, files):     # sanitize_relpath already excludes "..": defence in depth
            raise UploadError(422, "Недопустимый путь файла")
        return dest

    # -- chunked files ----------------------------------------------------------------------------
    def _parts(self, upload_id: str) -> Path:
        return self.root / upload_id / "parts"

    def _load_chunked(self, upload_id: str, key: str) -> ChunkedFile | None:
        cf = self._chunked.get((upload_id, key))
        if cf is not None:
            return cf
        d = read_json(self._parts(upload_id) / f"{key}.json")
        if not isinstance(d, dict):
            return None
        try:
            cf = ChunkedFile.from_json(d)
        except (KeyError, TypeError, ValueError):
            return None
        self._chunked[(upload_id, key)] = cf
        return cf

    def _all_chunked(self, upload_id: str) -> list[ChunkedFile]:
        try:
            keys = sorted(p.stem for p in self._parts(upload_id).glob("*.json"))
        except OSError:
            return []
        return [cf for cf in (self._load_chunked(upload_id, k) for k in keys) if cf is not None]

    def _save_chunked(self, upload_id: str, cf: ChunkedFile) -> None:
        parts = self._parts(upload_id)
        if self.gone(upload_id):
            raise UploadError(404, "Загрузка отменена")
        atomic_write_json(parts / f"{file_key(cf.path)}.json", cf.to_json())

    def drop_chunked(self, upload_id: str, rel: PurePosixPath) -> None:
        """Forget a chunked upload of ``rel`` (its data and its reservation, if unfinished)."""
        key = file_key(rel)
        with self._file_lock(upload_id, key):
            with self._lock:
                cf = self._load_chunked(upload_id, key)
                self._chunked.pop((upload_id, key), None)
            if cf is None:
                return
            self._unlink_chunked(upload_id, key, cf)

    def _unlink_chunked(self, upload_id: str, key: str, cf: ChunkedFile) -> None:
        for suffix in (".part", ".json"):
            try:
                (self._parts(upload_id) / f"{key}{suffix}").unlink()
            except OSError:
                pass
        if not cf.complete:
            self.release(upload_id, cf.size)

    def chunked_file(self, upload_id: str, rel: PurePosixPath) -> ChunkedFile:
        self.area(upload_id)
        with self._lock:
            cf = self._load_chunked(upload_id, file_key(rel))
        if cf is None or cf.path != rel.as_posix():
            raise UploadError(404, f"Файл «{rel}» не объявлен — начните его загрузку заново")
        return cf

    def declare(self, upload_id: str, rel: PurePosixPath, size: int, chunk_size: int,
                fingerprint: str | None = None) -> dict:
        """Start (or resume) a chunked file. The same path, size, chunk size and fingerprint resume
        where it stopped; anything else starts the file over (a finished file at the path is
        replaced). Returns the file's state with the ranges of the chunks still missing."""
        if not MIN_CHUNK <= chunk_size <= MAX_CHUNK:
            raise UploadError(422, f"Размер части должен быть от {MIN_CHUNK // 1024} КБ до {MAX_CHUNK // 1024 ** 2} МБ")
        if size < 0:
            raise UploadError(422, "Размер файла не может быть отрицательным")
        if -(-size // chunk_size) > MAX_CHUNKS:
            raise UploadError(422, "Слишком мелкие части для такого большого файла")
        fp = (fingerprint or "")[:200]
        key = file_key(rel)
        with self.writing(upload_id), self._file_lock(upload_id, key):   # check and create at once
            dest = self.target(upload_id, rel)
            with self._lock:
                cur = self._load_chunked(upload_id, key)
            if (cur is not None and cur.path == rel.as_posix() and cur.size == size and cur.chunk_size == chunk_size
                    and cur.fingerprint == fp and (not cur.complete or (dest.is_file() and dest.stat().st_size == size))):
                self._touch(upload_id)
                return cur.to_api()
            self.drop_chunked(upload_id, rel)
            existing = dest.stat().st_size if dest.is_file() else 0
            if size > disk_free(self.root) + existing - DISK_MARGIN:
                raise UploadError(507, "Недостаточно места на диске сервера для этого файла")
            self.reserve(upload_id, size)
            part = self._parts(upload_id) / f"{key}.part"
            try:
                if existing:
                    dest.unlink()
                    self.release(upload_id, existing)
                part.parent.mkdir(exist_ok=True)
                with open(part, "wb") as fh:
                    fh.truncate(size)           # sparse: the chunks fill it in place
                cf = ChunkedFile(path=rel.as_posix(), size=size, chunk_size=chunk_size, fingerprint=fp,
                                 bitmap=bytearray(((-(-size // chunk_size)) + 7) // 8), created_at=now_iso())
                if size == 0:
                    self._complete(upload_id, cf, part)
                else:
                    self._save_chunked(upload_id, cf)
            except BaseException:
                self.release(upload_id, size)
                unlink_quiet(part)
                raise
            with self._lock:
                self._chunked[(upload_id, key)] = cf
            self._touch(upload_id)
            return cf.to_api()

    def write_chunk(self, upload_id: str, rel: PurePosixPath, index: int, body: bytes | bytearray,
                    crc: int | None, encoding: str = "identity") -> dict:
        """Decode, verify and store chunk ``index`` (blocking: run it in a thread). The last missing
        chunk completes the file (moved into ``files/``). Sending a stored chunk again is a no-op."""
        cf = self.chunked_file(upload_id, rel)
        if not 0 <= index < cf.n_chunks:
            raise UploadError(422, f"Номер части {index} вне файла (частей: {cf.n_chunks})")
        if cf.complete or cf.has(index):
            self._touch(upload_id)
            return cf.to_api(missing=False)
        raw = decode_body(body, encoding, cf.chunk_len(index))
        if crc is not None and zlib.crc32(raw) != crc:
            raise UploadError(400, "Контрольная сумма части не совпала — она будет отправлена снова")
        key = file_key(rel)
        part = self._parts(upload_id) / f"{key}.part"
        try:
            fd = os.open(part, os.O_WRONLY)
        except FileNotFoundError:
            if cf.complete or cf.has(index):    # a retry raced the original, which finished the file
                return cf.to_api(missing=False)
            raise UploadError(404, f"Файл «{rel}» не объявлен — начните его загрузку заново") from None
        try:
            # opened first, checked second: a file declared anew after this check has a new .part,
            # and the bytes below go to the old one (unlinked), never into the new file
            self._check_current(upload_id, key, cf, rel)
            _pwrite_all(fd, raw, index * cf.chunk_size)
            _sync(fd)                       # on disk before the chunk counts as received
        except OSError as exc:
            if exc.errno == errno.ENOSPC:
                raise UploadError(507, "Недостаточно места на диске сервера") from None
            raise
        finally:
            os.close(fd)
        with self._file_lock(upload_id, key):
            self._check_current(upload_id, key, cf, rel)
            if not cf.complete and not cf.has(index):
                cf.mark(index)
                try:
                    if cf.count == cf.n_chunks:
                        self._complete(upload_id, cf, part)
                    else:
                        self._save_chunked(upload_id, cf)
                except BaseException:
                    cf.unmark(index)        # not counted: sending it again completes the file
                    raise
        self._touch(upload_id)
        return cf.to_api(missing=False)

    def _check_current(self, upload_id: str, key: str, cf: ChunkedFile, rel: PurePosixPath) -> None:
        with self._lock:
            if self._chunked.get((upload_id, key)) is not cf:
                raise UploadError(409, f"Файл «{rel}» начат заново — эта часть относится к прежней загрузке")

    def _complete(self, upload_id: str, cf: ChunkedFile, part: Path) -> None:
        dest = self.target(upload_id, PurePosixPath(cf.path))
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(part, dest)
        cf.complete = True
        self._save_chunked(upload_id, cf)

    # -- status -----------------------------------------------------------------------------------
    def _prune_tasks(self) -> None:
        now = time.monotonic()
        for k in [k for k, t in self._tasks.items() if t.state != "running" and now - t.updated > TASK_TTL_S]:
            del self._tasks[k]

    def status(self, upload_id: str) -> dict:
        """What the server holds of an upload: finished files, chunked files in progress (with the
        missing chunks), the finalize stage, its error, or the recording it became."""
        with self._lock:
            self._prune_tasks()
            task = self._tasks.get(upload_id) if valid_id(upload_id) else None
            if task is not None and (task.state == "done" or (task.state == "running" and self.gone(upload_id))):
                return {"upload_id": upload_id, "name": task.name,
                        "state": "done" if task.state == "done" else "finalizing", "files": [], "partial": [],
                        "bytes_received": task.bytes,
                        "finalize": task.progress() if task.state == "running" else None,
                        "error": None, "recording": task.recording}
            d = self.area(upload_id)
            partial = [cf.to_api() for cf in self._all_chunked(upload_id) if not cf.complete]
        meta = read_json(d / "meta.json", {}) or {}
        files = list_files(d / "files")
        running = task is not None and task.state == "running"
        return {
            "upload_id": upload_id, "name": meta.get("name") or "", "created_at": meta.get("created_at"),
            "state": "finalizing" if running else "receiving", "files": files, "partial": partial,
            "bytes_received": sum(f["size_bytes"] for f in files) + sum(p["received_bytes"] for p in partial),
            "finalize": task.progress() if running else None,
            "error": task.error if task is not None and task.state == "failed" else None,
            "recording": None,
        }

    # -- finalize ---------------------------------------------------------------------------------
    def start_finalize(self, upload_id: str, register: Register) -> FinalizeTask:
        """Start finalizing in the background (or join the one running / just finished). 409 while
        files are still being written or a chunked file is incomplete."""
        with self._lock:
            task = self._tasks.get(upload_id) if valid_id(upload_id) else None
            if task is not None and task.state in ("running", "done"):
                return task
            d = self.area(upload_id)
            if self._inflight.get(upload_id):
                raise UploadError(409, "Файлы ещё передаются — дождитесь окончания загрузки")
            incomplete = [cf for cf in self._all_chunked(upload_id) if not cf.complete]
            if incomplete:
                more = f" и ещё {len(incomplete) - 1}" if len(incomplete) > 1 else ""
                raise UploadError(409, f"Загружены не все части файла «{incomplete[0].path}»{more}")
            meta = read_json(d / "meta.json", {}) or {}
            task = FinalizeTask(upload_id, meta.get("name") or "")
            self._tasks[upload_id] = task
        threading.Thread(target=self._run_finalize, args=(task, register), name=f"finalize-{upload_id}",
                         daemon=True).start()
        return task

    def finalize(self, upload_id: str, register: Register) -> dict:
        """Finalize and wait (blocking): the recording, or UploadError with the Russian detail."""
        task = self.start_finalize(upload_id, register)
        task.done.wait()
        if task.state != "done":
            raise UploadError(task.status or 500, task.error or "Не удалось обработать загрузку")
        return task.recording

    def _run_finalize(self, task: FinalizeTask, register: Register) -> None:
        uid = task.upload_id
        try:
            probe, name, warnings, rec_dir, undo = self._finalize(uid, task)
            task.set("saving")
            try:
                rec = register(probe, name, warnings, rec_dir)
            except BaseException:
                undo()                  # the input goes back to the staging area, nothing is lost
                raise
            task.bytes = int(probe.size_bytes)
            shutil.rmtree(self.root / uid, ignore_errors=True)
            with self._lock:
                self._forget(uid)
            task.finish(rec)
        except ProbeError as exc:
            task.fail(422, str(exc))
        except UploadError as exc:
            task.fail(exc.status, exc.message)
        except Exception:
            log.exception("finalize of upload %s failed", uid)
            task.fail(500, "Не удалось обработать загрузку — подробности в журнале сервера")

    def _finalize(self, upload_id: str, task: FinalizeTask):
        """Unpack archives, find the input, move it to ``recordings/<rec_id>/`` and probe it.
        Returns (probe, recording name, warnings, recording dir, undo). On a ProbeError the area is
        kept so the user can add the missing files."""
        d = self.area(upload_id)
        files = d / "files"
        files.mkdir(exist_ok=True)
        meta = read_json(d / "meta.json", {}) or {}
        remove_leftovers(files)
        if not any(files.iterdir()):
            raise ProbeError("Загрузка пуста — добавьте файлы")
        zips = sorted(p for p in files.rglob("*") if p.is_file() and p.suffix.lower() == ".zip"
                      and not p.name.startswith("."))
        zip_stem = None
        if zips:
            total = sum(zip_total_size(z) for z in zips) or 1
            done = 0
            task.set("unpacking", 0.0)
            for z in zips:
                out = z.parent / z.stem
                if out.exists():
                    out = z.parent / f"{z.stem}_{new_id(4)}"
                tmp = z.parent / f".{z.stem}.unpacking-{new_id(6)}"   # hidden: never taken for input
                base = done
                try:
                    done += safe_extract_zip(z, tmp, self.settings.max_upload_bytes,
                                             progress=lambda n, base=base: task.set("unpacking", (base + n) / total))
                    os.replace(tmp, out)
                except BaseException:
                    shutil.rmtree(tmp, ignore_errors=True)     # a retry starts from the intact zip
                    raise
                z.unlink()
                zip_stem = zip_stem or z.stem
        task.set("probing")
        found, warnings = find_input(files)
        probe = probe_path(found)
        # the whole input unit moves: the bag / frames dir, or the dir of a lone storage file
        unit = found if found.is_dir() else found.parent if probe.kind == "rosbag2" else found
        natural = probe.source_name if unit != files else _loose_name(files, probe, zip_stem)
        name = (meta.get("name") or "").strip() or natural
        rec_id = new_id()
        rec_dir = self.settings.recordings_dir / rec_id
        rec_dir.mkdir(parents=True)
        dest = rec_dir / _safe_leaf(unit.name if unit != files else natural)
        try:
            shutil.move(str(unit), str(dest))
        except BaseException:
            shutil.rmtree(rec_dir, ignore_errors=True)
            raise
        probe.path = dest if unit == found else dest / found.name
        probe.source_name = natural

        def undo() -> None:
            try:
                shutil.move(str(dest), str(unit))
            except OSError:
                log.exception("could not move %s back to the staging area", dest)
            shutil.rmtree(rec_dir, ignore_errors=True)

        return probe, name, warnings, rec_dir, undo


def list_files(files: Path) -> list[dict]:
    """Finished files of an area: ``[{path, size_bytes}]`` (temporary files left out)."""
    out = []
    if not files.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(files):
        dirnames[:] = sorted(n for n in dirnames if not any(m in n for m in TEMP_MARKERS))
        here = Path(dirpath)
        for f in sorted(filenames):
            if f.startswith(".") and any(m in f for m in TEMP_MARKERS):
                continue
            p = here / f
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not os.path.islink(p):
                out.append({"path": p.relative_to(files).as_posix(), "size_bytes": st.st_size})
    return out


def remove_leftovers(files: Path) -> None:
    """Temporary files of interrupted writes (``.<name>.part-*``) and unpacking folders of an
    interrupted finalize (``.<zip>.unpacking-*``): finalize runs only when no write is in flight."""
    for dirpath, dirnames, filenames in os.walk(files):
        here = Path(dirpath)
        for n in list(dirnames):
            if n.startswith(".") and ".unpacking-" in n:
                shutil.rmtree(here / n, ignore_errors=True)
                dirnames.remove(n)
        for f in filenames:
            if f.startswith(".") and ".part-" in f:
                unlink_quiet(here / f)


def _loose_name(files: Path, probe: Probe, zip_stem: str | None) -> str:
    """A name for files uploaded loose at the top of the staging area: the bag's storage file
    stem without the ``_0`` split suffix (``doubleT_obstacle_0.db3`` -> ``doubleT_obstacle``)."""
    if probe.kind == "rosbag2":
        from resense_web.probe import storage_files
        st = storage_files(files)
        if st:
            stem = st[0].stem
            head, _, tail = stem.rpartition("_")
            return head if head and tail.isdigit() else stem
    return zip_stem or ("кадры" if probe.kind == "npy" else "запись")


def _safe_leaf(name: str) -> str:
    leaf = "".join(c if c not in '/\\\x00' else "_" for c in name).strip(" .") or "recording"
    return leaf[:120]


def disk_free(path: Path) -> int:
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return 0


def unlink_quiet(path: Path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
