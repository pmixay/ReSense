"""Author adapter around read-only independent H4 geometry (838dd32)."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

OUT = Path("/out")
ROOT = Path("/source/repo")
OWNED = ["resense/clustering.py", "resense/config.py", "configs/default.yaml",
         "ros2_ws/src/resense_ros/config/detector.yaml", "tests/test_column_free_top.py",
         "tests/test_h4_column_evidence.py"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args, **kwargs):
    return subprocess.run(args, check=True, stdout=sys.stdout, stderr=subprocess.STDOUT, **kwargs)


def identity():
    import resense
    from resense import _native
    from resense.config import DetectorConfig
    import yaml
    assert Path(resense.__file__).resolve() == ROOT / "resense/__init__.py", resense.__file__
    assert _native.enabled(), _native.status()
    manifest = json.loads((ROOT / "docs/evidence/detector_freeze_2026-09-29_shell_off.json").read_text())
    files = {p: sha((ROOT / p).read_bytes()) for p in sorted(manifest["files"])}
    differing = []
    for p, digest in files.items():
        assert b"\r\n" not in (ROOT / p).read_bytes(), p
        committed = subprocess.check_output(["git", "show", os.environ["AUTHOR_HEAD"] + ":" + p], cwd=ROOT)
        if sha(committed) != digest:
            assert p in OWNED, p
            differing.append(p)
    cfg = DetectorConfig.from_dict(yaml.safe_load((ROOT / "configs/default.yaml").read_text())["resense"])
    so = {p.name: sha(p.read_bytes()) for p in (ROOT / "resense").glob("*.so")}
    assert list(so.values()) == ["b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534"]
    review = {}
    for p in Path("/review").glob("*.py"):
        expected = subprocess.check_output(["git", "show", "838dd32:docs/evidence/integration_2026-10-16/h4_safety/" + p.name], cwd=ROOT)
        assert p.read_bytes().replace(b"\r\n", b"\n") == expected, p
        review[p.name] = sha(expected)
    data = dict(author=True, head=os.environ["AUTHOR_HEAD"], imported=resense.__file__,
                files=files, source_sha256=sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
                native=so, native_status=_native.status(), config=cfg.to_dict(), reviewer_sources=review,
                files_differing_from_commit=differing,
                adapter_files={p.name: sha(p.read_bytes()) for p in Path("/author").glob("*.py")},
                environment={k: v for k, v in os.environ.items() if k.endswith("NUM_THREADS") or k.startswith("AUTHOR_")})
    (OUT / "results/identity.json").write_text(json.dumps(data, indent=2) + "\n")
    return cfg


def main():
    head = os.environ["AUTHOR_HEAD"]
    if not ROOT.exists():
        command(["git", "-c", "safe.directory=/source.git", "clone", "--shared", "/source.git", str(ROOT)])
    command(["git", "checkout", "--detach", head], cwd=ROOT)
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip() == head
    if os.environ["AUTHOR_OVERLAY"] == "1":
        for p in OWNED:
            (ROOT / p).write_bytes((Path("/integration") / p).read_bytes().replace(b"\r\n", b"\n"))
    (OUT / "source.patch").write_bytes(subprocess.check_output(["git", "diff", "--", *OWNED], cwd=ROOT))
    ref = Path("/reference/candidate-f8c088dc4f32-20261016T073403Z-4b64ec55/resense")
    for p in ref.glob("*.so"):
        shutil.copyfile(p, ROOT / "resense" / p.name)
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    # The image's sitecustomize eagerly imports installed resense at interpreter
    # startup, before the new clone exists. Restart with the source path present.
    if "--prepared" not in sys.argv:
        os.execv(sys.executable, [sys.executable, __file__, *sys.argv[1:], "--prepared"])
    (OUT / "results").mkdir(exist_ok=True)
    cfg = identity()
    task = sys.argv[1]
    mode = sys.argv[sys.argv.index("--mode") + 1]
    if task == "tests":
        tests = ["tests/test_h4_column_evidence.py"] if mode == "witness" else [
            "tests/test_h4_column_evidence.py", "tests/test_column_free_top.py", "tests/test_structure_cut.py",
            "tests/test_far_structure.py", "tests/test_native.py", "tests/test_synthetic_sensitivity.py",
            "tests/test_synthetic_diagnosis.py"]
        r = subprocess.run(["python3", "-m", "pytest", "-q", "-rs", *tests,
                            "--junitxml=/out/results/pytest.xml"], cwd=ROOT,
                           stdout=sys.stdout, stderr=subprocess.STDOUT)
        if r.returncode:
            raise RuntimeError(f"pytest exit {r.returncode}")
    else:
        sys.path.insert(0, "/review")
        import common
        common.identity = lambda: cfg
        if task == "components":
            import components
            components.main(["--mode", mode])
        elif task == "replay":
            import replay
            replay.main(["--mode", mode])
        else:
            sys.path.insert(0, "/author")
            import probes
            probes.main(cfg, mode)


start = time.time()
with (OUT / "worker.txt").open("a", buffering=1) as log:
    sys.stdout = sys.stderr = log
    try:
        main()
    except BaseException:
        traceback.print_exc()
        (OUT / "completion.json").write_text(json.dumps(dict(ok=False, wall_s=time.time() - start)))
        raise
    (OUT / "completion.json").write_text(json.dumps(dict(ok=True, wall_s=time.time() - start)))
