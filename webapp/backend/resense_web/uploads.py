"""Upload staging areas: ``uploads/<id>/files/<relative path>`` filled by streamed PUTs, then
finalized into a recording (zip unpacking, input detection, a move into ``recordings/<id>/``)."""
from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path, PurePosixPath

from resense_web.probe import Probe, ProbeError, find_input, probe_path, safe_extract_zip
from resense_web.settings import Settings
from resense_web.util import atomic_write_json, is_within, new_id, now_iso, read_json, tree_size, valid_id

STALE_S = 24 * 3600


class UploadError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class UploadStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.uploads_dir
        self._lock = threading.Lock()
        self._used: dict[str, int] = {}     # bytes reserved per staging area (in-flight included)
        self._finalizing: set[str] = set()

    # -- areas ------------------------------------------------------------------------------------
    def area(self, upload_id: str) -> Path:
        if not valid_id(upload_id):
            raise UploadError(404, "Загрузка не найдена")
        d = self.root / upload_id
        if not (d / "meta.json").is_file():
            raise UploadError(404, "Загрузка не найдена")
        return d

    def create(self, name: str | None) -> str:
        upload_id = new_id()
        d = self.root / upload_id
        (d / "files").mkdir(parents=True)
        atomic_write_json(d / "meta.json", {"id": upload_id, "name": (name or "").strip()[:200],
                                            "created_at": now_iso()})
        with self._lock:
            self._used[upload_id] = 0
        return upload_id

    def delete(self, upload_id: str) -> None:
        d = self.area(upload_id)
        shutil.rmtree(d, ignore_errors=True)
        with self._lock:
            self._used.pop(upload_id, None)

    def meta(self, upload_id: str) -> dict:
        return read_json(self.area(upload_id) / "meta.json", {}) or {}

    def cleanup_stale(self, max_age_s: float = STALE_S) -> int:
        n = 0
        now = time.time()
        if not self.root.is_dir():
            return 0
        for d in self.root.iterdir():
            try:
                if not d.is_dir():
                    continue
                newest = max(p.stat().st_mtime for p in (d, d / "files", d / "meta.json") if p.exists())
                if now - newest > max_age_s:
                    shutil.rmtree(d, ignore_errors=True)
                    n += 1
            except (OSError, ValueError):
                continue
        return n

    # -- byte accounting --------------------------------------------------------------------------
    def reserve(self, upload_id: str, nbytes: int) -> None:
        """Count ``nbytes`` against the staging area's limit (UploadError 413 when over it)."""
        with self._lock:
            used = self._used.get(upload_id)
            if used is None:
                used = tree_size(self.root / upload_id / "files")
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

    # -- finalize ---------------------------------------------------------------------------------
    def finalize(self, upload_id: str) -> tuple[Probe, str, list[str], Path]:
        """Unpack archives, find the input, move it to ``recordings/<rec_id>/`` and probe it.
        Returns (probe, recording name, warnings, recording dir). The staging area is removed on
        success; on a ProbeError it is kept so the user can add the missing files."""
        self.area(upload_id)
        with self._lock:
            if upload_id in self._finalizing:
                raise UploadError(409, "Загрузка уже обрабатывается")
            self._finalizing.add(upload_id)
        try:
            return self._finalize(upload_id)
        finally:
            with self._lock:
                self._finalizing.discard(upload_id)

    def _finalize(self, upload_id: str) -> tuple[Probe, str, list[str], Path]:
        d = self.area(upload_id)
        files = d / "files"
        meta = read_json(d / "meta.json", {}) or {}
        zips = sorted(p for p in files.rglob("*") if p.is_file() and p.suffix.lower() == ".zip")
        if not any(files.iterdir()):
            raise ProbeError("Загрузка пуста — добавьте файлы")
        zip_stem = None
        for z in zips:
            out = z.parent / z.stem
            if out.exists():
                out = z.parent / f"{z.stem}_{new_id(4)}"
            try:
                safe_extract_zip(z, out, self.settings.max_upload_bytes)
            except BaseException:
                shutil.rmtree(out, ignore_errors=True)     # a retry starts from the intact zip
                raise
            z.unlink()
            zip_stem = zip_stem or z.stem
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
        shutil.rmtree(d, ignore_errors=True)
        with self._lock:
            self._used.pop(upload_id, None)
        return probe, name, warnings, rec_dir


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
