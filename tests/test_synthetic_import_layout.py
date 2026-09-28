"""Observer imports work with installed packages; measurement never mixes source roots."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/synthetic_sensitivity.py"


@pytest.fixture(scope="module")
def installed_package(tmp_path_factory):
    folder = tmp_path_factory.mktemp("synthetic_installed_layout")
    shutil.copytree(ROOT / "resense", folder / "resense", ignore=shutil.ignore_patterns("__pycache__"))
    return folder


def observe(installed, *, explicit=False, measure=False):
    # Preload an installed package before loading the observer, as Docker's conftest does.
    environment = {**os.environ, "PYTHONPATH": str(installed), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    environment.pop("RESENSE_DETECTOR_ROOT", None)
    if explicit:
        environment["RESENSE_DETECTOR_ROOT"] = str(ROOT)
    code = f"import resense, runpy; ns = runpy.run_path({str(SCRIPT)!r}, run_name='observer'); "
    if measure:
        code += "ns['evaluate'](None)"  # origin must be rejected before accessing any input/cache arguments
    else:
        code += "print(resense.__file__)"
    return subprocess.run([sys.executable, "-c", code], cwd=installed, env=environment,
                          capture_output=True, text=True, check=False)


def test_default_observer_import_supports_installed_package_and_source_scripts(installed_package):
    result = observe(installed_package)
    assert result.returncode == 0, result.stderr
    assert str(installed_package / "resense/__init__.py") in result.stdout


def test_explicit_checkout_rejects_already_imported_different_package(installed_package):
    result = observe(installed_package, explicit=True)
    assert result.returncode != 0
    assert "does not belong to selected detector checkout" in result.stderr


def test_measurement_rejects_implicit_installed_source_mismatch(installed_package):
    result = observe(installed_package, measure=True)
    assert result.returncode != 0
    assert "does not belong to selected detector checkout" in result.stderr
