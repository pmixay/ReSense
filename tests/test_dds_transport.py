"""The image's DDS transport choice without Docker: docker/dds_transport.sh (sourced by the
entrypoint) for RESENSE_DDS unset / udp / shm / an invalid value and each reason shm falls back to
UDP, docker/fastdds_shm_share.py's file filter on a temporary directory and a fake /proc, and the
two Fast DDS profiles. The files are found in a checkout (docker/) or in the image (/opt/resense,
where these tests run as /opt/resense/tests); the Dockerfile check exists only in a checkout
(the image has no Dockerfile), so nothing is skipped."""
from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOST_IPC = "ipc:[4026531839]"
NS = "{http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles}"


def _find(name: str) -> Path:
    for p in (ROOT / "docker" / name, ROOT / name, Path("/") / name):
        if p.is_file():
            return p
    raise FileNotFoundError(name)


TRANSPORT = _find("dds_transport.sh")
SHARE_PY = _find("fastdds_shm_share.py")
PROFILE_SHM = _find("fastdds_shm_udp.xml")
PROFILE_UDP = _find("fastdds_udp.xml")
ENTRYPOINT = _find("entrypoint.sh")

SPEC = importlib.util.spec_from_file_location("resense_fastdds_shm_share", SHARE_PY)
assert SPEC is not None and SPEC.loader is not None
share = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(share)

# stands in for python3: logs its arguments; --check runs the real script, the watcher is not started
FAKE_PY = """#!/bin/bash
echo "$*" >> "$PY_LOG"
case " $* " in *" --check "*) exec "{python}" "$@" ;; esac
exit 0
"""


def _select(tmp_path, dds=None, ipc=HOST_IPC, profile=True, shm_dir=True, env_profile=None):
    """Source dds_transport.sh and call resense_dds_transport under `set -e` as the entrypoint does;
    returns (exit code, FASTRTPS_DEFAULT_PROFILES_FILE after it, stderr, the fake python's calls)."""
    home = tmp_path / "opt"
    home.mkdir()
    (home / "fastdds_udp.xml").write_text(PROFILE_UDP.read_text())
    if profile:
        (home / "fastdds_shm_udp.xml").write_text(PROFILE_SHM.read_text())
    (home / "fastdds_shm_share.py").write_text(SHARE_PY.read_text())
    shm = tmp_path / "shm"
    if shm_dir:
        shm.mkdir()
    ns = tmp_path / "ns_ipc"
    os.symlink(ipc, ns)                     # readlink gives what /proc/self/ns/ipc would
    py = tmp_path / "python3"
    py.write_text(FAKE_PY.replace("{python}", sys.executable))
    py.chmod(0o755)
    log = tmp_path / "py.log"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("RESENSE_", "FASTRTPS_", "FASTDDS_"))}
    env.update(RESENSE_DDS_HOME=str(home), RESENSE_IPC_NS=str(ns), RESENSE_SHM_DIR=str(shm),
               RESENSE_PYTHON=str(py), PY_LOG=str(log),
               FASTRTPS_DEFAULT_PROFILES_FILE=env_profile or str(home / "fastdds_udp.xml"))
    if dds is not None:
        env["RESENSE_DDS"] = dds
    script = f'set -e; source "{TRANSPORT}"; resense_dds_transport; wait; echo "PROFILE=$FASTRTPS_DEFAULT_PROFILES_FILE"'
    r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=60)
    prof = r.stdout.strip().rpartition("PROFILE=")[2]
    calls = log.read_text().splitlines() if log.exists() else []
    return r.returncode, prof, r.stderr, calls, home, shm


@pytest.mark.parametrize("dds", [None, "", "udp", "UDP"], ids=["unset", "empty", "udp", "UDP"])
def test_udp_is_the_default_and_changes_nothing(tmp_path, dds):
    rc, prof, err, calls, home, _ = _select(tmp_path, dds)
    assert rc == 0
    assert prof == str(home / "fastdds_udp.xml")            # the image's profile, untouched
    assert calls == []                                        # no check, no watcher
    assert "[WARN]" not in err
    assert err.count("[INFO]") == 1 and "DDS transport: udp, UDPv4 only" in err


def test_udp_keeps_a_profile_set_with_docker_run_e(tmp_path):
    rc, prof, err, calls, _, _ = _select(tmp_path, "udp", env_profile="/data/mine.xml")
    assert rc == 0 and prof == "/data/mine.xml" and calls == []
    assert "udp mode, the Fast DDS profile of the environment: FASTRTPS_DEFAULT_PROFILES_FILE='/data/mine.xml'" in err


def test_shm_switches_the_profile_and_starts_the_watcher(tmp_path):
    rc, prof, err, calls, home, shm = _select(tmp_path, "shm")
    assert rc == 0
    assert prof == str(home / "fastdds_shm_udp.xml")
    assert calls == [f"{home}/fastdds_shm_share.py --check --shm-dir {shm}",
                     f"{home}/fastdds_shm_share.py --shm-dir {shm}"]
    assert "[WARN]" not in err
    assert err.count("[INFO]") == 1 and "DDS transport: shm, shared memory + UDPv4" in err


@pytest.mark.parametrize("case, reason", [
    ("own_ipc", "it needs --ipc=host"),
    ("no_profile", "fastdds_shm_udp.xml is missing"),
    ("no_shm_dir", "cannot be shared from here"),
])
def test_shm_falls_back_to_udp_with_a_warning(tmp_path, case, reason):
    kw = {"own_ipc": {"ipc": "ipc:[4026532461]"}, "no_profile": {"profile": False},
          "no_shm_dir": {"shm_dir": False}}[case]
    rc, prof, err, calls, home, _ = _select(tmp_path, "shm", **kw)
    assert rc == 0
    assert prof == str(home / "fastdds_udp.xml")
    assert all("--check" in c for c in calls)                 # the watcher is never started
    assert "[WARN] [resense.dds]: RESENSE_DDS=shm: " in err and reason in err and "staying on UDP only" in err
    assert "DDS transport: udp, UDPv4 only" in err


@pytest.mark.parametrize("dds", ["tcp", "shared", "1"])
def test_an_invalid_value_fails_safe_to_udp(tmp_path, dds):
    rc, prof, err, calls, home, _ = _select(tmp_path, dds)
    assert rc == 0 and prof == str(home / "fastdds_udp.xml") and calls == []
    assert f"RESENSE_DDS='{dds}' is neither udp nor shm; staying on UDP only" in err
    assert "DDS transport: udp" in err


def test_the_entrypoint_chooses_the_transport_before_exec():
    lines = [ln.strip() for ln in ENTRYPOINT.read_text().splitlines()]
    i = lines.index("source /opt/resense/dds_transport.sh")
    assert lines[i + 1] == "resense_dds_transport"
    assert lines.index('exec "$@"') > i + 1


# ---------------------------------------------------------------- fastdds_shm_share.py
MAPS = b"""\
55d0c0a00000-55d0c0a01000 r--p 00000000 08:01 1234  /usr/bin/python3.10
7f0000000000-7f0000080000 rw-s 00000000 00:1a 11    /dev/shm/fastrtps_port7411
7f0000080000-7f0000100000 rw-s 00000000 00:1a 12    /dev/shm/fastrtps_0123456789abcdef
7f0000100000-7f0000180000 rw-s 00000000 00:1a 13    /dev/shm/fastrtps_port7400 (deleted)
7f0000180000-7f0000200000 rw-s 00000000 00:1a 14    /dev/shm/sub/fastrtps_port7000
7f0000200000-7f0000280000 rw-s 00000000 00:1a 15    /dev/shmx/fastrtps_port7001
7f0000280000-7f0000300000 rw-p 00000000 00:00 0
7f0000300000-7f0000380000 rw-s 00000000 00:1a 16    /dev/shm/sem.fastrtps_port7411_mutex
"""


def test_parse_maps_keeps_live_files_directly_in_dev_shm():
    assert share.parse_maps(MAPS) == {"fastrtps_port7411", "fastrtps_0123456789abcdef", "sem.fastrtps_port7411_mutex"}
    assert share.parse_maps(MAPS, "/dev/shmx/") == {"fastrtps_port7001"}


def test_targets_are_fast_dds_ports_their_semaphores_and_data_segments():
    mapped = {"fastrtps_port7411", "fastrtps_port7400", "fastrtps_0123456789abcdef",
              "fastrtps_port7411_el", "fastrtps_0123456789abcdef_el", "fastrtps_port7400_sl",
              "fastrtps_0123456789ABCDEF", "fastrtps_0123", "fastrtps_port", "fastdds_port7411",
              "sem.fastrtps_port7412_mutex", "rclone-vfscache", "other_0123456789abcdef"}
    assert share.targets(mapped) == {"fastrtps_port7411", "sem.fastrtps_port7411_mutex",
                                     "fastrtps_port7400", "sem.fastrtps_port7400_mutex",
                                     "fastrtps_0123456789abcdef"}


def _shm_dir(tmp_path):
    d = tmp_path / "shm"
    d.mkdir()
    for name in ("fastrtps_port7411", "sem.fastrtps_port7411_mutex", "fastrtps_0123456789abcdef",
                 "fastrtps_port7411_el", "fastrtps_fedcba9876543210"):
        (d / name).write_bytes(b"\0" * 64)
        (d / name).chmod(0o644)
    outside = tmp_path / "outside"
    outside.write_text("not in /dev/shm")
    outside.chmod(0o600)
    (d / "fastrtps_port7500").symlink_to(outside)             # a symlink under a Fast DDS name
    (d / "fastrtps_port7501").mkdir(mode=0o755)               # a directory under a Fast DDS name
    return d, outside


def _mode(p: Path) -> int:
    return stat.S_IMODE(os.lstat(p).st_mode)


def test_share_opens_up_only_regular_files_of_its_own_uid(tmp_path):
    d, outside = _shm_dir(tmp_path)
    names = {"fastrtps_port7411", "sem.fastrtps_port7411_mutex", "fastrtps_0123456789abcdef",
             "fastrtps_port7500", "fastrtps_port7501", "sem.fastrtps_port7500_mutex"}
    assert share.share(names, str(d), uid=os.geteuid() + 1) == []       # another uid's files: untouched
    assert _mode(d / "fastrtps_port7411") == 0o644
    changed = share.share(names, str(d))
    assert changed == ["fastrtps_0123456789abcdef", "fastrtps_port7411", "sem.fastrtps_port7411_mutex"]
    for n in changed:
        assert _mode(d / n) == 0o666
    assert _mode(d / "fastrtps_port7411_el") == 0o644                   # not a target: stays
    assert _mode(d / "fastrtps_fedcba9876543210") == 0o644              # not in names (not mapped): stays
    assert _mode(outside) == 0o600                                      # the symlink was not followed
    assert _mode(d / "fastrtps_port7501") == 0o755                      # the directory was not changed
    assert share.share(names, str(d)) == []                             # already 0666: nothing to do


def _fake_proc(tmp_path, maps: bytes):
    proc = tmp_path / "proc"
    (proc / "self").mkdir(parents=True)
    (proc / "self" / "maps").write_bytes(b"")
    (proc / "4242").mkdir()
    (proc / "4242" / "maps").write_bytes(maps)
    (proc / "sys").mkdir()                                              # not a pid: skipped
    return proc


def test_one_pass_opens_up_what_the_container_maps(tmp_path, capsys):
    d, _ = _shm_dir(tmp_path)
    maps = MAPS.replace(b"/dev/shm/", str(d).encode() + b"/")
    proc = _fake_proc(tmp_path, maps)
    assert share.mapped_names(str(proc), str(d)) == {"fastrtps_port7411", "fastrtps_0123456789abcdef",
                                                     "sem.fastrtps_port7411_mutex"}
    assert share.main(["--once", "--proc", str(proc), "--shm-dir", str(d)]) == 0
    err = capsys.readouterr().err
    assert "[resense.shm] fastrtps_port7411: mode 666" in err
    assert "[resense.shm] sem.fastrtps_port7411_mutex: mode 666" in err
    assert "[resense.shm] fastrtps_0123456789abcdef: mode 666" in err
    assert _mode(d / "fastrtps_fedcba9876543210") == 0o644


def test_check(tmp_path):
    d, _ = _shm_dir(tmp_path)
    proc = _fake_proc(tmp_path, b"")
    assert share.main(["--check", "--proc", str(proc), "--shm-dir", str(d)]) == 0
    assert share.main(["--check", "--proc", str(proc), "--shm-dir", str(tmp_path / "missing")]) == 1
    assert share.main(["--check", "--proc", str(tmp_path / "noproc"), "--shm-dir", str(d)]) == 1


# ---------------------------------------------------------------- the profiles
def _profile(path: Path):
    root = ET.parse(path).getroot()
    desc = {t.findtext(f"{NS}transport_id"): t for t in root.iter(f"{NS}transport_descriptor")}
    part = root.find(f"{NS}participant")
    assert part is not None and part.get("is_default_profile") == "true"
    used = [t.text for t in part.iter(f"{NS}transport_id")]
    builtin = part.findtext(f"{NS}rtps/{NS}useBuiltinTransports")
    return desc, used, builtin


def test_the_shm_profile_is_shared_memory_plus_the_udp_profiles_udp():
    desc, used, builtin = _profile(PROFILE_SHM)
    assert builtin == "false"
    assert [desc[t].findtext(f"{NS}type") for t in used] == ["SHM", "UDPv4"]
    udp_desc, udp_used, udp_builtin = _profile(PROFILE_UDP)
    assert udp_builtin == "false" and [udp_desc[t].findtext(f"{NS}type") for t in udp_used] == ["UDPv4"]
    for tag in ("sendBufferSize", "receiveBufferSize"):                 # the same UDP settings
        assert desc[used[1]].findtext(f"{NS}{tag}") == udp_desc[udp_used[0]].findtext(f"{NS}{tag}")


if (ROOT / "docker" / "Dockerfile").is_file():

    def test_the_image_defaults_to_udp_and_ships_the_shm_mode():
        text = (ROOT / "docker" / "Dockerfile").read_text()
        assert "\nENV FASTRTPS_DEFAULT_PROFILES_FILE=/opt/resense/fastdds_udp.xml\n" in text
        copy = next(ln for ln in text.splitlines() if ln.startswith("COPY docker/fastdds_udp.xml"))
        for f in ("fastdds_shm_udp.xml", "dds_transport.sh", "fastdds_shm_share.py"):
            assert f"docker/{f}" in copy
        assert copy.endswith(" /opt/resense/")
