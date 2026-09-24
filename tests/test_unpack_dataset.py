"""Organizer archives have different nesting; --only must not silently drop split files."""

import importlib.util
import io
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "unpack_dataset.py"
SPEC = importlib.util.spec_from_file_location("resense_unpack_dataset", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
unpack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(unpack)


@pytest.mark.parametrize("selection, expected", [
    ("new_data", {"new_data/new_data_127.db3", "new_data/new_data_128.db3", "new_data/metadata.yaml"}),
    ("new_data_127.db3", {"new_data/new_data_127.db3"}),
    ("doubleT_obstacle", {"for_hackathon/doubleT_obstacle/metadata.yaml"}),
])
def test_selective_unpack_of_both_archive_layouts(monkeypatch, tmp_path, selection, expected):
    members = ("new_data/new_data_127.db3", "new_data/new_data_128.db3", "new_data/metadata.yaml",
               "for_hackathon/doubleT_obstacle/metadata.yaml", "for_hackathon/roundT_doubleT/metadata.yaml")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name in members:
            payload = name.encode()
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))

    # The selection happens after decompression. A passthrough stream keeps the test
    # independent of the optional zstandard module in the runtime Docker image.
    monkeypatch.setitem(sys.modules, "zstandard", SimpleNamespace(
        ZstdDecompressor=lambda: SimpleNamespace(stream_reader=lambda stream, **kw: stream)))
    monkeypatch.setattr(unpack, "open_zst_stream", lambda *args: io.BytesIO(buf.getvalue()))
    monkeypatch.setattr(sys, "argv", ["unpack_dataset.py", "archive.zst", "--out", str(tmp_path),
                                      "--only", selection])
    assert unpack.main() == 0
    actual = {str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file()}
    assert actual == expected
    for path in actual:
        assert (tmp_path / path).read_text() == path
