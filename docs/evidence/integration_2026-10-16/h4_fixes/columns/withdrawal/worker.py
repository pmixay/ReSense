"""Author withdrawal measurements. Immutable H4 observer/inputs remain untouched."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT, OUT = Path("/source/repo"), Path("/out")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args, **kwargs):
    return subprocess.run(args, check=True, stdout=sys.stdout, stderr=subprocess.STDOUT, **kwargs)


def identity():
    import resense
    from resense import _native
    from resense.config import DetectorConfig
    assert Path(resense.__file__).resolve() == ROOT / "resense/__init__.py"
    assert _native.enabled(), _native.status()
    head = os.environ["WITHDRAWAL_HEAD"]
    manifest = json.loads((ROOT / "docs/evidence/detector_freeze_2026-09-29_shell_off.json").read_text())
    files = {p: sha((ROOT / p).read_bytes()) for p in sorted(manifest["files"])}
    for p, digest in files.items():
        assert b"\r\n" not in (ROOT / p).read_bytes()
        assert digest == sha(subprocess.check_output(["git", "show", head + ":" + p], cwd=ROOT)), p
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip()
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
    native = {p.name: sha(p.read_bytes()) for p in (ROOT / "resense").glob("*.so")}
    assert list(native.values()) == ["b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534"]
    review = {}
    for p in Path("/review").glob("*.py"):
        expected = subprocess.check_output(["git", "show", "838dd32:docs/evidence/integration_2026-10-16/h4_safety/" + p.name], cwd=ROOT)
        assert p.read_bytes().replace(b"\r\n", b"\n") == expected
        review[p.name] = sha(expected)
    result = dict(author=True, head=head, imported=resense.__file__, clean_git=True, files=files,
                  source_sha256=sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
                  config=cfg.to_dict(), config_sha256=sha(json.dumps(cfg.to_dict(), sort_keys=True).encode()),
                  native=native, reviewer_sources=review,
                  adapter_files={p.name: sha(p.read_bytes()) for p in Path("/author").glob("*.py")},
                  environment={k: v for k, v in os.environ.items() if k.endswith("NUM_THREADS")
                               or k.startswith("WITHDRAWAL_") or k in ["PYTHONPATH", "PYTHONHASHSEED"]})
    (OUT / "results/identity.json").write_text(json.dumps(result, indent=2) + "\n")
    return cfg


def install_shipping_guard(cfg):
    import resense.clustering as cl
    from resense.detector import Detector
    assert getattr(cfg.cluster, "column_free_max_top", 0.0) == 0.0
    state = dict(disabled_by_effective_config=True, free_top_calls=0, frames=0, candidates=0,
                 spared_candidates=0, provisional_tracks=0, spare_history_tracks=0,
                 free_top_implementation_present=hasattr(cl, "top_is_free"))
    if hasattr(cl, "top_is_free"):
        def forbidden(*args, **kwargs):
            state["free_top_calls"] += 1
            raise AssertionError("shipping config invoked withdrawn free-top/observer path")
        cl.top_is_free = forbidden
    original = Detector.process

    def process(self, *args, **kwargs):
        assert getattr(self.cfg.cluster, "column_free_max_top", 0.0) == 0.0
        r = original(self, *args, **kwargs)
        state["frames"] += 1
        state["candidates"] += len(r.candidates)
        state["spared_candidates"] += sum(bool(getattr(c, "spared", False)) for c in r.candidates)
        state["provisional_tracks"] += sum(any(getattr(t, "provisional_explained_hist", [])) for t in self.tracker.tracks)
        state["spare_history_tracks"] += sum(any(getattr(t, "spare_hist", [])) for t in self.tracker.tracks)
        assert not state["spared_candidates"] and not state["provisional_tracks"] and not state["spare_history_tracks"]
        return r
    Detector.process = process
    return state


def probes():
    sys.path.insert(0, str(ROOT / "docs/evidence/judgement_2026-10-13/scripts"))
    import range_test
    jobs = [("pole_c", "roundT_squareT_pressureGate_squareT", ".3,.3,2.8",
             ["--start", "150", "--d0", "230", "--end", "340"]),
            ("C_person", "roundT_pressureGate_roundT", ".5,.5,1.75", ["--start", "0", "--d0", "230"])]
    summary = {}
    for name, bag, obj, args in jobs:
        prefix = str(OUT / "results" / name)
        sys.argv = [range_test.__file__, "/data/decoded/" + bag, "/data/odometry/icp_" + bag + ".json",
                    prefix, "--obj", obj, *args]
        range_test.main()
        result = json.loads(Path(prefix + ".json").read_text())
        summary[name] = dict(summary=result["summary"],
                             matched_stop_frames=[r["k"] for r in result["rows"] if r["hit"]])
    (OUT / "results/probes.json").write_text(json.dumps(summary, indent=2) + "\n")


def experimental(cfg):
    """Re-exercise known rejected evidence with explicit historical opt-in, without tuning."""
    import copy
    import runpy
    import numpy as np
    assert cfg.cluster.column_free_max_top == 0.0
    opt_in = copy.deepcopy(cfg)
    opt_in.cluster.column_free_max_top = 2.95
    path = "docs/evidence/integration_2026-10-16/h4_fixes/columns/withdrawn_acceptance.py.txt"
    original = subprocess.check_output(["git", "show", "4c6ea25:tests/test_h4_column_evidence.py"], cwd=ROOT)
    assert (ROOT / path).read_bytes() == original
    helpers = runpy.run_path(str(ROOT / path))
    rows = []
    for name, args in [("case45_tall_miss", {}),
                       ("absorbing_continuation_false_free_evidence", dict(top=4.12, absorbing=(2.54, 4.12)))]:
        xyz, ring, labels = helpers["physical_column"](**args)
        cs = helpers["column_clusters"](xyz, ring, opt_in)
        matches = [c for c in cs if np.mean(labels[c.points_idx] == 1) > 0.5]
        assert len(matches) == 1
        c = matches[0]
        rows.append(dict(case=name, xyz_sha256=sha(xyz.tobytes()), zone=c.zone, reason=c.reason,
                         spared=c.spared, n_gauge=c.n_gauge, rings=c.ring_count, height_max=c.height_max))
    assert (rows[0]["reason"], rows[0]["spared"]) == ("column", False)
    assert (rows[1]["zone"], rows[1]["spared"]) == ("gauge", True)
    (OUT / "results/experimental_still_rejected.json").write_text(json.dumps(dict(
        explicit_opt_in=2.95, shipping_default=0.0, accepted=False, cases=rows,
        note="Known unmet withdrawn-feature criteria; these observations are not an H4 safety PASS."), indent=2) + "\n")


def main():
    head = os.environ["WITHDRAWAL_HEAD"]
    if not ROOT.exists():
        command(["git", "-c", "safe.directory=/source.git", "clone", "--shared", "/source.git", str(ROOT)])
    command(["git", "checkout", "--detach", head], cwd=ROOT)
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip() == head
    ref = Path("/reference/candidate-f8c088dc4f32-20261016T073403Z-4b64ec55/resense")
    for p in ref.glob("*.so"):
        shutil.copyfile(p, ROOT / "resense" / p.name)
    os.chdir(ROOT)
    if "--prepared" not in sys.argv:
        os.execv(sys.executable, [sys.executable, __file__, *sys.argv[1:], "--prepared"])
    sys.path.insert(0, str(ROOT))
    (OUT / "results").mkdir(exist_ok=True)
    cfg = identity()
    task = sys.argv[1]
    mode = sys.argv[sys.argv.index("--mode") + 1]
    if task == "tests":
        tests = ["tests/test_column_shipping.py"] if mode == "shipping" else [
            "tests/test_column_shipping.py", "tests/test_column_free_top.py", "tests/test_late_candidates.py",
            "tests/test_h4_spare_rearm.py", "tests/test_stop_keep.py", "tests/test_near_escalation.py",
            "tests/test_explained_run.py", "tests/test_fresh_stop_evidence.py", "tests/test_thin_monitoring.py",
            "tests/test_evidence_coherence.py", "tests/test_ego_veto.py", "tests/test_structure_cut.py",
            "tests/test_far_structure.py", "tests/test_wall_drift.py", "tests/test_native.py",
            "tests/test_synthetic_sensitivity.py", "tests/test_synthetic_diagnosis.py", "tests/test_cli.py",
            "tests/test_shipped_defaults.py"]
        command(["python3", "-m", "pytest", "-q", "-rs", *tests, "--junitxml=/out/results/pytest.xml"], cwd=ROOT)
    elif task == "experimental":
        experimental(cfg)
    else:
        guard = install_shipping_guard(cfg)
        if task == "probes":
            probes()
        else:
            sys.path.insert(0, "/review")
            import common
            common.identity = lambda: cfg
            import replay
            # The exact registered observer is installed unchanged. Any invocation
            # reaches the fail-fast guard; config=0 must prevent all such calls.
            replay.main(["--mode", "dark-inherited"])
            observer_calls = 0
            for piece in ["ride_1", "ride_3"]:
                with (OUT / "results" / (piece + ".jsonl")).open() as f:
                    observer_calls += sum(len(json.loads(line)["observer"]) for line in f)
            assert observer_calls == 0
            guard.update(exact_observer_installed=True, observer_calls=observer_calls)
        assert guard["free_top_calls"] == 0
        (OUT / "results/shipping_guard.json").write_text(json.dumps(guard, indent=2) + "\n")


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
