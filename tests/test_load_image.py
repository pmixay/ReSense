"""scripts/load_image.sh without Docker: its sha256 check on a dummy archive, with a fake
``docker`` first on PATH that logs its calls and succeeds. The expected sum is accepted in any
case and in the forms people paste (Windows Get-FileHash / certutil print upper case, certutil
spaces the bytes, a sha256sum or BSD line, a SHA256SUMS list); a wrong sum stops before
``docker load`` with exit 4, a value that holds no sum with exit 2."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "load_image.sh"
NAME = "resense-image-0.0.0-test.tar.gz"
PAYLOAD = b"not really an image archive\n" * 500
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
OTHER = hashlib.sha256(b"another file").hexdigest()

FAKE_DOCKER = """#!/usr/bin/env bash
echo "$*" >> "$DOCKER_LOG"
case "$1" in
  info) echo 24.0.7 ;;
  load) echo "Loaded image: resense:latest" ;;
  image) echo "sha256:0000" ;;
  run) echo "resense 0.0.0 native (fake docker)" ;;
esac
exit 0
"""

def _mixed(s: str) -> str:
    return "".join(c.upper() if i % 2 else c for i, c in enumerate(s))


def _run(tmp_path, sha256_file=None, **env):
    """Run load_image.sh on a dummy archive (with ``sha256_file`` as its .sha256 when given);
    returns (the completed process, the fake docker's log)."""
    d = tmp_path / "dist"
    d.mkdir(exist_ok=True)
    (d / NAME).write_bytes(PAYLOAD)
    if sha256_file is not None:
        (d / f"{NAME}.sha256").write_bytes(sha256_file.encode())
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker = bin_dir / "docker"
    docker.write_text(FAKE_DOCKER)
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    e = {k: v for k, v in os.environ.items() if k not in ("SHA256", "NO_VERIFY", "IMAGE")}
    e.update(env, PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}", DOCKER_LOG=str(log))
    r = subprocess.run(["bash", str(SCRIPT), str(d / NAME)], env=e, capture_output=True, text=True, timeout=60)
    return r, (log.read_text() if log.exists() else "")


@pytest.mark.parametrize("content", [
    f"{DIGEST}  {NAME}\n",                                    # export_image.sh's own file
    f"{DIGEST.upper()}  {NAME}\n",                            # upper case
    f"{_mixed(DIGEST)} *{NAME}\r\n",                          # mixed case, binary marker, CRLF (Windows)
    f"{DIGEST.upper()}\r\n",                                  # the bare sum, saved by a Windows editor
    f"{OTHER}  other.bin\n{DIGEST.upper()}  {NAME}\n",        # a SHA256SUMS list: the archive's line
], ids=["lower", "upper", "mixed-crlf", "bare-upper", "sha256sums"])
def test_the_sha256_file_is_accepted_in_any_case(tmp_path, content):
    r, log = _run(tmp_path, content)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"OK {DIGEST}" in r.stdout
    assert f"load -i {tmp_path / 'dist' / NAME}" in log
    assert "PASS: resense:latest loaded" in r.stdout


@pytest.mark.parametrize("value", [
    DIGEST.upper(),                                           # Get-FileHash's Hash
    _mixed(DIGEST),
    f"  {DIGEST.upper()}\n",                                  # pasted with spaces and a newline
    " ".join(DIGEST.upper()[i:i + 2] for i in range(0, 64, 2)),   # older certutil: spaced bytes
    f"SHA256 hash of {NAME}:\r\n{DIGEST.upper()}\r\nCertUtil: -hashfile command completed successfully.\r\n",
    f"Algorithm Hash Path\n--------- ---- ----\nSHA256 {DIGEST.upper()} C:\\dist\\{NAME}\n",
    f"{DIGEST.upper()}  {NAME}",                              # a whole sha256sum line
    f"SHA256 ({NAME}) = {DIGEST.upper()}",                    # BSD / macOS shasum --tag
], ids=["upper", "mixed", "padded", "certutil-bytes", "certutil", "get-filehash", "sha256sum-line", "bsd"])
def test_sha256_variable_is_accepted_in_any_case(tmp_path, value):
    r, log = _run(tmp_path, SHA256=value)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"OK {DIGEST}" in r.stdout
    assert "load -i" in log


@pytest.mark.parametrize("where", ["variable", "file"])
def test_a_wrong_sum_fails_with_exit_4_before_docker_load(tmp_path, where):
    wrong = OTHER.upper()
    if where == "variable":
        r, log = _run(tmp_path, f"{DIGEST}  {NAME}\n", SHA256=wrong)     # the variable wins over the file
    else:
        r, log = _run(tmp_path, f"{wrong}  {NAME}\n")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "checksum mismatch" in r.stderr
    assert f"expected {OTHER}" in r.stderr and f"actual   {DIGEST}" in r.stderr
    assert "load" not in log


@pytest.mark.parametrize("value", ["not-a-sum", DIGEST[:63], DIGEST + "0", "g" * 64])
def test_a_value_without_a_sum_is_a_bad_argument(tmp_path, value):
    r, log = _run(tmp_path, SHA256=value)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "holds no sha256" in r.stderr
    assert "load" not in log


def test_no_sha256_file_and_no_variable_is_a_bad_argument(tmp_path):
    r, log = _run(tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert f"no {NAME}.sha256 next to the archive" in r.stderr
    assert "load" not in log


def test_no_verify_skips_the_check(tmp_path):
    r, log = _run(tmp_path, f"{OTHER}  {NAME}\n", NO_VERIFY="1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "checksum not checked" in r.stdout and "load -i" in log
