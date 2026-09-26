"""The release tooling without Docker or network: the four version declarations agree
(scripts/release_meta.py), release tags are checked against them, the release notes carry the
jury's commands and the build's identity, scripts/verify_release.sh handles its arguments and
its sha256 logic on a dummy "release" served from a file:// URL, and scripts/release.sh
refuses bad input and prints its plan with DRY_RUN=1.

Runs in the source tree and in the CI image (/opt/resense: no git checkout, maybe no curl)."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SPEC = importlib.util.spec_from_file_location("resense_release_meta", SCRIPTS / "release_meta.py")
assert SPEC is not None and SPEC.loader is not None
meta = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(meta)

VERSION = meta.package_version()
TAG = f"v{VERSION}-rc1"
ARCHIVE = f"resense-image-{TAG}.tar.gz"
DOWNLOADERS = ["python"] + (["curl"] if shutil.which("curl") else [])


# ---------------------------------------------------------------- versions and tags

def test_the_four_version_declarations_agree():
    found = meta.declared_versions()
    assert set(found) == {"pyproject.toml", "resense/__init__.py", "ros2_ws/src/resense_ros/package.xml",
                          "ros2_ws/src/resense_ros/setup.py"}
    assert set(found.values()) == {VERSION}, found


def test_the_imported_package_has_the_declared_version():
    import resense
    assert resense.__version__ == VERSION


def test_package_version_names_a_disagreement(tmp_path):
    for rel, _ in meta.SOURCES:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dst)
    assert meta.package_version(tmp_path) == VERSION
    p = tmp_path / "ros2_ws/src/resense_ros/package.xml"
    p.write_text(p.read_text(encoding="utf-8").replace(f"<version>{VERSION}<", "<version>0.0.1<"), encoding="utf-8")
    with pytest.raises(ValueError, match="disagree.*package.xml 0.0.1"):
        meta.package_version(tmp_path)
    p.unlink()
    with pytest.raises(ValueError, match="no version declaration found in ros2_ws/src/resense_ros/package.xml"):
        meta.package_version(tmp_path)


@pytest.mark.parametrize("tag, pre", [(f"v{VERSION}", "false"), (f"v{VERSION}-rc1", "true"),
                                      (f"v{VERSION}-rc12", "true"), (f"v{VERSION}-rc0-test.2", "true")])
def test_release_tags(tag, pre):
    assert meta.parse_tag(tag, VERSION) == {"tag": tag, "version": VERSION, "prerelease": pre}


@pytest.mark.parametrize("tag, why", [
    ("v1.0-rc1", "not a release tag"), ("v1.0-final", "not a release tag"), ("v0.1-intermediate", "not a release tag"),
    (VERSION, "not a release tag"), (f"v{VERSION}-", "not a release tag"), (f"v{VERSION}-rc1/x", "not a release tag"),
    (f"v{VERSION}-rc 1", "not a release tag"), (f"v{VERSION}\n", "not a release tag"),
    (f"v{VERSION}-rc1\nv{VERSION}", "not a release tag"), ("v99.0.0", "names version 99.0.0, but the package is"),
])
def test_bad_release_tags(tag, why):
    with pytest.raises(ValueError, match=why):
        meta.parse_tag(tag, VERSION)


def test_check_tag_cli_prints_github_output_lines(capsys):
    assert meta.main(["check-tag", TAG]) == 0
    assert capsys.readouterr().out.splitlines() == [f"tag={TAG}", f"version={VERSION}", "prerelease=true"]
    assert meta.main(["check-tag", "v1.0-rc1"]) == 2
    assert meta.main(["version"]) == 0


def test_release_notes_carry_the_jury_commands_and_the_identity(capsys):
    sha, commit = "ab" * 32, "0123456789abcdef0123456789abcdef01234567"
    args = ["notes", "--tag", TAG, "--commit", commit, "--sha256", sha, "--bytes", "521185902",
            "--image-id", "sha256:" + "c" * 64, "--ci-run", "https://github.com/pmixay/ReSense/actions/runs/1"]
    assert meta.main(args) == 0
    notes = capsys.readouterr().out
    for s in (f"docker load -i {ARCHIVE}", "docker run --rm -it --net=host --ipc=host resense",
              "ros2 bag play <bag> --delay 3", "ros2 topic echo /resense/decision", sha, commit,
              f"https://github.com/pmixay/ReSense/blob/{TAG}/README.md",
              f"https://github.com/pmixay/ReSense/blob/{TAG}/CHANGELOG.md",
              f"https://github.com/pmixay/ReSense/releases/download/{TAG}/{ARCHIVE}",
              "521185902 bytes (0.49 GiB)", "release candidate", "actions/runs/1", "sha256:" + "c" * 64):
        assert s in notes, s
    assert meta.main(["notes", "--tag", TAG, "--commit", commit, "--sha256", "xyz", "--bytes", "1"]) == 2
    assert meta.main(["notes", "--tag", TAG, "--commit", "HEAD", "--sha256", sha, "--bytes", "1"]) == 2
    assert meta.main(["notes", "--tag", "v1.0-rc1", "--commit", commit, "--sha256", sha, "--bytes", "1"]) == 2
    capsys.readouterr()
    assert meta.main(["notes", "--tag", f"v{VERSION}", "--commit", commit, "--sha256", sha, "--bytes", "1"]) == 0
    final = capsys.readouterr().out
    assert "release candidate" not in final and "scripts/release.sh" in final


# ---------------------------------------------------------------- scripts/verify_release.sh

def _fake_release(tmp_path, tag=TAG, sums=True, payload=b"not really an image\n" * 999):
    """A release directory as GitHub serves it: <base>/<tag>/<asset>; returns (base URL, sha256)."""
    rel = tmp_path / "releases" / tag
    rel.mkdir(parents=True)
    name = f"resense-image-{tag}.tar.gz"
    (rel / name).write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    (rel / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="ascii")
    if sums:
        (rel / "SHA256SUMS").write_text(f"{'0' * 64}  other.bin\n{digest}  {name}\n", encoding="ascii")
    return (tmp_path / "releases").as_uri(), digest


def _verify(args, **env):
    e = {k: v for k, v in os.environ.items() if k not in ("EXPECT_SHA256", "NO_DOWNLOAD", "BASE_URL", "REPO")}
    e.update(env)
    return subprocess.run(["bash", str(SCRIPTS / "verify_release.sh"), *args], env=e,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("downloader", DOWNLOADERS)
def test_verify_release_passes_on_an_intact_release(tmp_path, downloader):
    base, digest = _fake_release(tmp_path)
    out = tmp_path / "dl"
    r = _verify([TAG, str(out)], BASE_URL=base, DOWNLOADER=downloader, EXPECT_SHA256=digest.upper())
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"OK {digest}" in r.stdout and "PASS" in r.stdout
    assert sorted(p.name for p in out.iterdir()) == sorted([ARCHIVE, ARCHIVE + ".sha256", "SHA256SUMS"])
    # the same files, checked again without downloading
    r = _verify([TAG, str(out)], NO_DOWNLOAD="1", BASE_URL="file:///nonexistent")
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("downloader", DOWNLOADERS)
def test_verify_release_without_sha256sums(tmp_path, downloader):
    base, _ = _fake_release(tmp_path, sums=False)
    r = _verify([TAG, str(tmp_path / "dl")], BASE_URL=base, DOWNLOADER=downloader)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no SHA256SUMS" in r.stdout


def test_verify_release_detects_a_damaged_archive(tmp_path):
    base, digest = _fake_release(tmp_path)
    with open(tmp_path / "releases" / TAG / ARCHIVE, "r+b") as f:     # one flipped byte
        f.seek(100)
        b = f.read(1)
        f.seek(100)
        f.write(bytes([b[0] ^ 1]))
    r = _verify([TAG, str(tmp_path / "dl")], BASE_URL=base)
    assert r.returncode == 4, r.stdout + r.stderr
    assert "checksum mismatch" in r.stderr and digest in r.stderr


def test_verify_release_checks_expect_sha256_and_sha256sums(tmp_path):
    base, digest = _fake_release(tmp_path)
    r = _verify([TAG, str(tmp_path / "a")], BASE_URL=base, EXPECT_SHA256="1" * 64)
    assert r.returncode == 4 and "not EXPECT_SHA256" in r.stderr, r.stdout + r.stderr
    (tmp_path / "releases" / TAG / "SHA256SUMS").write_text(f"{'2' * 64}  {ARCHIVE}\n", encoding="ascii")
    r = _verify([TAG, str(tmp_path / "b")], BASE_URL=base)
    assert r.returncode == 4 and "disagree" in r.stderr, r.stdout + r.stderr
    (tmp_path / "releases" / TAG / "SHA256SUMS").write_text(f"{digest}  something-else.tar.gz\n", encoding="ascii")
    r = _verify([TAG, str(tmp_path / "c")], BASE_URL=base)
    assert r.returncode == 4 and "no line for" in r.stderr, r.stdout + r.stderr


def test_verify_release_rejects_a_malformed_sha256_file(tmp_path):
    base, digest = _fake_release(tmp_path)
    sha_file = tmp_path / "releases" / TAG / (ARCHIVE + ".sha256")
    sha_file.write_text(f"{digest}  resense-image-v0.0.1.tar.gz\n", encoding="ascii")
    r = _verify([TAG, str(tmp_path / "a")], BASE_URL=base)
    assert r.returncode == 4 and "is the sum of 'resense-image-v0.0.1.tar.gz'" in r.stderr, r.stdout + r.stderr
    sha_file.write_text("deadbeef\n", encoding="ascii")
    r = _verify([TAG, str(tmp_path / "b")], BASE_URL=base)
    assert r.returncode == 4 and "64 hex" in r.stderr, r.stdout + r.stderr


@pytest.mark.parametrize("downloader", DOWNLOADERS)
def test_verify_release_missing_release_is_a_download_failure(tmp_path, downloader):
    base, _ = _fake_release(tmp_path)
    r = _verify(["v9.9.9", str(tmp_path / "dl")], BASE_URL=base, DOWNLOADER=downloader)
    assert r.returncode == 6, r.stdout + r.stderr
    assert "could not download resense-image-v9.9.9.tar.gz.sha256" in r.stderr
    assert not list((tmp_path / "dl").glob("*.part"))


@pytest.mark.parametrize("args, env, why", [
    ([], {}, "Download the image archive"),
    (["-h"], {}, "Download the image archive"),
    ([TAG, "d", "extra"], {}, "Download the image archive"),
    (["bad tag"], {}, "is not a release tag"),
    (["../../etc"], {}, "is not a release tag"),
    ([TAG], {"REPO": "not-a-repo"}, "is not owner/name"),
    ([TAG], {"EXPECT_SHA256": "abc"}, "64 hex digits"),
    ([TAG], {"DOWNLOADER": "wget"}, "curl or python"),
])
def test_verify_release_argument_handling(tmp_path, args, env, why):
    r = _verify(args, **env)
    assert r.returncode == 2, r.stdout + r.stderr
    assert why in r.stderr


def test_verify_release_no_download_needs_the_files(tmp_path):
    r = _verify([TAG, str(tmp_path)], NO_DOWNLOAD="1")
    assert r.returncode == 2 and "not found" in r.stderr, r.stdout + r.stderr


# ---------------------------------------------------------------- scripts/publish_release.sh

def _publish(args, **env):
    e = {k: v for k, v in os.environ.items() if k not in ("REPO", "GITHUB_REPOSITORY", "DRY_RUN")}
    e.update(env)
    return subprocess.run(["bash", str(SCRIPTS / "publish_release.sh"), *args], env=e, capture_output=True,
                          text=True, timeout=60)


def _release_dir(tmp_path, tag=TAG):
    """What export_image.sh and release_meta.py notes leave in dist/: the archive, its .sha256, the notes."""
    d = tmp_path / "dist"
    d.mkdir()
    _, digest = _fake_release(tmp_path / "src", tag=tag)
    src = tmp_path / "src" / "releases" / tag
    name = f"resense-image-{tag}.tar.gz"
    shutil.copy(src / name, d / name)
    shutil.copy(src / f"{name}.sha256", d / f"{name}.sha256")
    (d / f"release-notes-{tag}.md").write_text("notes\n", encoding="utf-8")
    return d, digest


@pytest.mark.parametrize("tag, pre", [(TAG, True), (f"v{VERSION}", False)])
def test_publish_release_dry_run(tmp_path, tag, pre):
    d, digest = _release_dir(tmp_path, tag)
    r = _publish([tag, str(d)], DRY_RUN="1", REPO="someone/ReSense")
    assert r.returncode == 0, r.stdout + r.stderr
    name = f"resense-image-{tag}.tar.gz"
    for s in (f"OK {digest}", f"gh release create {tag} --repo someone/ReSense --verify-tag",
              f'--title "ReSense {tag}"', f"--notes-file {d}/release-notes-{tag}.md",
              f"{d}/{name} {d}/{name}.sha256 {d}/SHA256SUMS", f"gh release upload {tag} --repo someone/ReSense --clobber",
              f"--prerelease={'true' if pre else 'false'} --draft=false"):
        assert s in r.stdout, s
    assert ("--prerelease " in r.stdout) == pre
    assert not (d / "SHA256SUMS").exists()           # a dry run writes nothing


def test_publish_release_default_repo_is_the_workflows(tmp_path):
    d, _ = _release_dir(tmp_path)
    r = _publish([TAG, str(d)], DRY_RUN="1", GITHUB_REPOSITORY="fork/ReSense")
    assert r.returncode == 0 and "--repo fork/ReSense" in r.stdout, r.stdout + r.stderr
    r = _publish([TAG, str(d)], DRY_RUN="1")
    assert r.returncode == 0 and "--repo pmixay/ReSense" in r.stdout, r.stdout + r.stderr


def test_publish_release_refuses_a_damaged_archive_or_missing_files(tmp_path):
    d, _ = _release_dir(tmp_path)
    name = f"resense-image-{TAG}.tar.gz"
    with open(d / name, "ab") as f:
        f.write(b"x")
    r = _publish([TAG, str(d)], DRY_RUN="1")
    assert r.returncode == 4 and "checksum mismatch" in r.stderr, r.stdout + r.stderr
    (d / f"{name}.sha256").write_text(f"{'a' * 64}  other.tar.gz\n", encoding="ascii")
    r = _publish([TAG, str(d)], DRY_RUN="1")
    assert r.returncode == 4 and "is not '<sha256>" in r.stderr, r.stdout + r.stderr
    (d / f"release-notes-{TAG}.md").unlink()
    r = _publish([TAG, str(d)], DRY_RUN="1")
    assert r.returncode == 2 and "release-notes" in r.stderr, r.stdout + r.stderr


@pytest.mark.parametrize("args, env, why", [
    ([], {}, "Create or update the GitHub release"), ([TAG, "a", "b"], {}, "Create or update the GitHub release"),
    (["v1.0-rc1"], {}, "not a release tag"), (["v99.0.0"], {}, "names version 99.0.0"),
    ([TAG, "/nonexistent/dir"], {}, "not found"), ([TAG], {"REPO": "x"}, "is not owner/name"),
])
def test_publish_release_argument_handling(args, env, why):
    r = _publish(args, DRY_RUN="1", **env)
    assert r.returncode == 2, r.stdout + r.stderr
    assert why in r.stderr


# ---------------------------------------------------------------- scripts/release.sh

def _release(args, **env):
    e = dict(os.environ)
    e.update(env)
    return subprocess.run(["bash", str(SCRIPTS / "release.sh"), *args], env=e, capture_output=True, text=True,
                          timeout=60, cwd=ROOT)


@pytest.mark.parametrize("args, code, why", [
    ([], 2, "Manual fallback"), (["--help"], 2, "Manual fallback"), ([TAG, "x"], 2, "Manual fallback"),
    (["v1.0-rc1"], 2, "is not a release tag"), (["v99.0.0"], 2, "names version 99.0.0"),
])
def test_release_sh_refuses_bad_input(args, code, why):
    r = _release(args, DRY_RUN="1")
    assert r.returncode == code, r.stdout + r.stderr
    assert why in r.stderr


def test_release_sh_dry_run_prints_the_plan(tmp_path):
    r = _release([TAG], DRY_RUN="1", OUT_DIR=str(tmp_path / "dist"))
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    for s in (f"VERSION={TAG}", "scripts/export_image.sh", f"docker rmi resense:{TAG} resense:latest",
              f"scripts/load_image.sh {tmp_path / 'dist' / ARCHIVE}", "SHA256SUMS",
              f"gh release create {TAG}", "--prerelease", "--verify-tag", f"gh release upload {TAG}", "--clobber",
              f"scripts/verify_release.sh {TAG}"):
        assert s in out, s
    assert not (tmp_path / "dist").exists()          # a dry run writes nothing
