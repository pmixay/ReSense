"""Recorded-data paths: no personal machine paths in live code, one mechanism for locating the data.

The recorded data a test needs lives under ``$RESENSE_CACHE`` (default ``/data/cache``); the test
carries ``@pytest.mark.realdata(path)`` and is *deselected* where the path is absent
(``tests/conftest.py``). docs/evidence/hygiene_2026-10-22 records the sweep that removed the
``C:/Users/...`` and ``D:/Datasets/...`` paths of the 28.09 analysis scripts and tests.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIVE = ("scripts", "tests", "resense", "native", "configs", "ros2_ws", "webapp", "web", "docker")
# built from pieces so that this file does not match itself
PERSONAL = re.compile(r"\b[CD]:[/\\]+" + r"(?:Users|Datasets)\b")
SUFFIXES = {".py", ".sh", ".yaml", ".yml", ".json", ".md", ".txt", ".cfg", ".toml", ".cpp", ".h", ".hpp"}


def _live_files():
    out = subprocess.run(["git", "ls-files", "-z", *LIVE], cwd=ROOT, capture_output=True, timeout=60)
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    for name in out.stdout.decode().split("\0"):
        if name and Path(name).suffix in SUFFIXES and (ROOT / name).is_file():
            yield name


def test_the_scan_finds_a_personal_path_when_there_is_one(tmp_path):
    """Positive control for the scan below."""
    sample = tmp_path / "sample.py"
    sample.write_text('P = Path("D:/Datasets/ReSense/x")\nQ = "C:\\\\Users\\\\someone"\nOK = "/data/cache"\n')
    hits = [line for line in sample.read_text().splitlines() if PERSONAL.search(line)]
    assert len(hits) == 2


def test_no_personal_windows_paths_in_live_code():
    hits = []
    for name in _live_files():
        for number, line in enumerate((ROOT / name).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if PERSONAL.search(line):
                hits.append(f"{name}:{number}")
    assert not hits, "personal paths in live code (use $RESENSE_CACHE): " + ", ".join(hits)


def _collect(env_cache, tmp_path):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    if env_cache is None:
        env.pop("RESENSE_CACHE", None)
    else:
        env["RESENSE_CACHE"] = str(env_cache)
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                        "tests/test_evidence_coherence.py", "tests/test_fresh_support_analysis.py"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode in (0, 5), r.stdout[-800:] + r.stderr[-800:]
    ids = [line for line in r.stdout.splitlines() if line.startswith("tests/") and "::" in line]
    return ids, r.stdout


MEASUREMENT_TESTS = {
    "test_evidence_coherence.py::test_sparse_edge_positive_rows_are_unchanged_by_fresh_onset_replay",
    "test_fresh_support_analysis.py::test_direct_fresh_selected_events_and_positive_counterexample_when_capture_available",
}


def test_data_tests_are_deselected_without_the_data_and_collected_with_it(tmp_path):
    absent = tmp_path / "absent"
    ids, out = _collect(absent, tmp_path)
    assert not ({i.split("tests/")[-1] for i in ids} & MEASUREMENT_TESTS)
    assert "deselected" in out                       # the summary names them and the missing path
    present = tmp_path / "present"
    (present / "cross_ring_2026-09-28_measurement").mkdir(parents=True)
    (present / "fresh-stop-positive-stress").mkdir()
    (present / "direct-fresh-support-all").mkdir()
    ids_present, _ = _collect(present, tmp_path)
    names = {i.split("tests/")[-1] for i in ids_present}
    assert MEASUREMENT_TESTS <= names, sorted(MEASUREMENT_TESTS - names)
    assert len(ids_present) > len(ids)


def test_the_default_root_and_the_override_agree_across_scripts_and_tests(tmp_path):
    code = ("import os; from scripts.analyze_residual_events import CACHE, MEASUREMENT;"
            "import sys; sys.path.insert(0, 'tests'); import test_evidence_coherence as t;"
            "print(CACHE, MEASUREMENT, t.POSITIVE_STRESS)")
    env = dict(os.environ)
    env.pop("RESENSE_CACHE", None)
    default = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert default.returncode == 0, default.stderr[-800:]
    assert default.stdout.split() == ["/data/cache", "/data/cache/cross_ring_2026-09-28_measurement",
                                      "/data/cache/fresh-stop-positive-stress"]
    env["RESENSE_CACHE"] = str(tmp_path)
    moved = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert moved.stdout.split() == [str(tmp_path), f"{tmp_path}/cross_ring_2026-09-28_measurement",
                                    f"{tmp_path}/fresh-stop-positive-stress"]
