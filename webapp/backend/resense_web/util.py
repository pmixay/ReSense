"""Small shared helpers: ids, timestamps, atomic JSON files, path sanitizing, JSON encoding."""
from __future__ import annotations

import json
import math
import os
import re
import secrets
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

import numpy as np

_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
ID_RE = re.compile(r"^[a-z0-9]{6,32}$")


def new_id(n: int = 10) -> str:
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(n))


def valid_id(value: str) -> bool:
    return bool(ID_RE.match(value or ""))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --- JSON ---------------------------------------------------------------------------------------

def _default(o: Any):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o).__name__}")


def finite(obj: Any) -> Any:
    """``obj`` with every NaN / inf float replaced by None (browsers reject NaN in JSON)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [finite(v) for v in obj]
    if isinstance(obj, np.generic):
        return finite(obj.item())
    if isinstance(obj, np.ndarray):
        return finite(obj.tolist())
    return obj


def dumps(obj: Any) -> str:
    """Compact, strictly valid JSON (non-finite floats become null)."""
    try:
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=_default)
    except ValueError:
        return json.dumps(finite(obj), separators=(",", ":"), ensure_ascii=False, allow_nan=False,
                          default=_default)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, obj: Any) -> None:
    atomic_write_bytes(path, dumps(obj).encode("utf-8"))


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


# --- paths --------------------------------------------------------------------------------------

class UnsafePath(ValueError):
    """A client-supplied relative path that could escape its directory (message in Russian)."""


def sanitize_relpath(raw: str, *, allow_backslash: bool = False) -> PurePosixPath:
    """A safe relative POSIX path from client input: no absolute paths, no ``..``, no NUL, no
    backslashes (zip members may pass ``allow_backslash`` to treat them as separators), no drive
    letters; ``.`` and empty segments are dropped."""
    if raw is None:
        raise UnsafePath("Не указан путь файла")
    if "\x00" in raw:
        raise UnsafePath("Недопустимый символ в пути файла")
    if "\\" in raw:
        if not allow_backslash:
            raise UnsafePath("Обратная косая черта в пути файла недопустима")
        raw = raw.replace("\\", "/")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise UnsafePath("Путь файла должен быть относительным")
    parts = []
    for seg in raw.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            raise UnsafePath("Путь файла не может содержать «..»")
        if len(seg.encode("utf-8")) > 255:
            raise UnsafePath("Слишком длинное имя файла")
        parts.append(seg)
    if not parts:
        raise UnsafePath("Пустой путь файла")
    if len(parts) > 32:
        raise UnsafePath("Слишком глубокая вложенность папок")
    return PurePosixPath(*parts)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def tree_size(path: Path) -> int:
    """Bytes of a file, or of every regular file under a directory (symlinks not followed)."""
    path = Path(path)
    if path.is_file():
        return path.stat().st_size
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            try:
                st = os.lstat(os.path.join(dirpath, f))
            except OSError:
                continue
            if not os.path.islink(os.path.join(dirpath, f)):
                total += st.st_size
    return total


_NATURAL = re.compile(r"(\d+)")


def natural_key(name: str):
    return [int(t) if t.isdigit() else t.lower() for t in _NATURAL.split(name)]


def tail_text(path: Path, max_bytes: int = 65536) -> str:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - max_bytes))
            data = fh.read()
    except OSError:
        return ""
    text = data.decode("utf-8", errors="replace")
    if size > max_bytes:
        nl = text.find("\n")
        text = text[nl + 1:] if nl >= 0 else text
    return text


def download_filename(name: str, suffix: str) -> str:
    """A readable file name from a run / recording name (unicode letters kept)."""
    name = unicodedata.normalize("NFC", name or "")
    name = re.sub(r"[^\w.\- ]+", "_", name, flags=re.UNICODE).strip(" ._") or "resense"
    name = re.sub(r"\s+", "_", name)[:100]
    return f"{name}{suffix}"


def content_disposition(filename: str, fallback: str = "download") -> str:
    ascii_name = filename.encode("ascii", "ignore").decode("ascii")
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_name).strip("_.") or fallback
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename, safe='')}"
