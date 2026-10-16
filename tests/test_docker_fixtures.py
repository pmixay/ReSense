"""Dataset-free image regressions: exact pure fixtures and repeatable E2 verifier options."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]
JUDGE = 'docs/evidence/judgement_2026-10-13/scripts/'
STARTUP = 'docs/evidence/node_startup_2026-10-15/docker_tools/'
VERIFIER = 'docs/evidence/offline_rebuild_2026-10-15/verify.py'
FIXTURES = [
    'docs/evidence/cycle_2026-09-28/evaluation/protocol.json',
    'docs/evidence/cycle_2026-09-28/evaluation/protocol_v2.json',
    'docs/evidence/results/residual_events_2026-09-28.json',
    'docs/RESIDUAL_EVENTS_2026-09-28.md',
    'docs/evidence/integration_2026-10-16/h4_safety/results/rearm_witness.json',
    'labels/doubleT_obstacle.json',
    'webapp/backend/resense_web/__init__.py',
    'webapp/backend/resense_web/decision.py',
    *[JUDGE + name for name in ('probe.py', 'judge_runner.py', 'range_test.py',
                               'score_objects.py', 'judge_geom.py')],
    *[JUDGE + 'docker/' + name for name in ('analyze_chain.py', 'chain.sh', 'listener.py')],
    *[STARTUP + name for name in ('analyze_chain.py', 'bags_volume.py', 'chain.sh', 'launch_matrix.py', 'listener.py',
                                 'observe_listener.py', 'publish_report.py', 'runtime_probe.py')],
    VERIFIER,
]


@pytest.mark.parametrize('relative', FIXTURES)
def test_image_has_readable_pure_fixture(relative):
    path = ROOT / relative
    text = path.read_text(encoding='utf-8')
    assert text.strip(), relative
    if path.suffix == '.py':
        compile(text, relative, 'exec')
    elif path.suffix == '.json':
        assert json.loads(text), relative


def test_real_judge_probe_and_worker_seeds_outside_source_tree(tmp_path):
    """Import the real transitive closure and process tiny generated clouds, without bag data.

    Only the worker's git-checkout metadata is replaced: an installed image has no .git.
    NodeReplica, run_frame, record, detector processing and the X3 seed proxy all execute.
    A child process prevents other tests' mocked judge/ROS modules from hiding missing files.
    """
    code = textwrap.dedent('''
        import json, os, sys
        from pathlib import Path
        import numpy as np
        import resense
        from resense import _native

        root, work = map(Path, sys.argv[1:])
        assert Path.cwd() == work
        if os.environ.get("RESENSE_REQUIRE_SYNTHETIC") == "1":
            assert _native.enabled(), _native.status()
        installed = {"import": resense.__file__, "native": _native.status()}
        # Import resense first, just as the Docker CI job does from -w /.
        sys.path.insert(0, str(root))
        from scripts import robustness_battery as battery
        probe = battery.load_probe()
        import judge_runner, range_test, judge_geom
        from resense_ros import fastcloud
        for module in (probe, judge_runner, range_test, judge_geom):
            assert Path(module.__file__).parent == battery.JUDGE
        assert Path(fastcloud.__file__).is_relative_to(root / "ros2_ws/src")
        assert Path(judge_runner.CONFIG) == root / "configs/default.yaml"
        assert len(battery.protocol()["scripts"]) == 4

        # Detector-independent geometry is executable too, not just present/compilable.
        x = np.linspace(6.1, 29.9, 600)
        rails = np.concatenate([np.c_[x, np.full_like(x, y), np.full_like(x, -2)]
                                for y in (-.8, .8)])
        geometry = judge_geom.fit_rails(rails)
        assert geometry and abs(geometry["spacing"] - 1.6) < .05
        assert abs(geometry["axis"](15)) < .05

        cache = work / "cache"
        cache.mkdir()
        rng_factory = np.random.default_rng
        rng = rng_factory(19)
        xyz = rng.uniform([5, -2, -2.5], [40, 2, -.5], (256, 3)).astype(np.float32)
        intensity = np.arange(len(xyz), dtype=np.float32)
        ring = np.arange(len(xyz), dtype=np.uint16)
        meta = [{"i": i, "stamp": 100 + i * .1, "bag_t": 200 + i * .1,
                 "topic": "/generated", "frame_id": "fixture", "has_ring": True,
                 "n_raw": len(xyz), "n_near": 0} for i in range(2)]
        (cache / "meta.json").write_text(json.dumps(meta))
        for i in range(2):
            np.savez(cache / f"f_{i:05d}.npz", xyz=xyz, inten=intensity, ring=ring)

        captured = []
        real_run_frame = probe.run_frame
        def run_frame(rep, points, intensities, rings, m, k):
            assert np.random.default_rng is rng_factory
            np.testing.assert_array_equal(rng_factory(23).integers(100, size=8),
                                          np.random.default_rng(23).integers(100, size=8))
            np.testing.assert_array_equal(intensities, rings)
            captured.append(intensities.copy())
            return real_run_frame(rep, points, intensities, rings, m, k)
        probe.run_frame = run_frame
        battery.load_probe = lambda: probe
        battery.identity = lambda repo: installed

        def run(seed, name):
            captured.clear()
            job = {"repo": str(root), "cache": str(cache), "prefix": str(work / name),
                   "args": ["--drop", ".3", "--pitch", "2"], "seed": seed}
            plan = work / f"{name}.json"
            plan.write_text(json.dumps(job))
            battery.worker(plan)
            assert probe.np is np and np.random.default_rng is rng_factory
            rows = battery.checked_rows(Path(job["prefix"] + ".jsonl"), meta)
            assert len(rows) == 2
            assert [r["n_points"] for r in rows] == [len(a) for a in captured]
            return [a.copy() for a in captured]
        first, again, other = run(1, "first"), run(1, "again"), run(2, "other")
        for a, b in zip(first, again):
            np.testing.assert_array_equal(a, b)
        assert any(not np.array_equal(a, b) for a, b in zip(first, other))
        print(json.dumps({"runtime": installed, "same_seed_repeatable": True,
                          "different_seed_independent": True, "frames_per_run": 2,
                          "real_judge_imports": True}))
    ''')
    env = dict(os.environ, RESENSE_REPO=str(ROOT))
    result = subprocess.run([sys.executable, '-c', code, str(ROOT), str(tmp_path)],
                            cwd=tmp_path, env=env, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    proof = json.loads(result.stdout.splitlines()[-1])
    assert proof['same_seed_repeatable'] and proof['different_seed_independent']


def test_judge_scorer_consumes_committed_label_schema_outside_source_tree(tmp_path):
    labels = ROOT / 'labels/doubleT_obstacle.json'
    truth = json.loads(labels.read_text(encoding='utf-8'))
    assert truth['_meta']['gauge_half_width_m'] == 1.05
    key, objects = next((k, rows) for k, rows in truth.items() if not k.startswith('_')
                        and any(o['in_gauge'] and o.get('n_points', 1) for o in rows))
    obj = next(o for o in objects if o['in_gauge'] and o.get('n_points', 1))
    lateral = sum(p[1] for p in obj['bbox']) / 2 if 'bbox' in obj else obj['lateral']
    detection = {'d': obj['distance'], 'c': [obj['distance'], lateral, 0], 'lat': lateral}
    rows = [{'i': int(key), 'decision': 'STOP', 'dets': [detection], 'warns': []},
            {'i': truth['_meta']['frames'], 'decision': 'STOP', 'dets': [detection], 'warns': []}]
    raw, out = tmp_path / 'run.jsonl', tmp_path / 'score.json'
    raw.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    result = subprocess.run([sys.executable, str(ROOT / JUDGE / 'score_objects.py'),
                             str(raw), str(labels), str(out)], cwd=tmp_path,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    score = json.loads(out.read_text(encoding='utf-8'))
    assert score['objects'][obj['label']]['stop_rows'] == 1
    assert score['unmatched_stop_frames'] == 1
    assert score['unmatched_stop_episodes'] == [[truth['_meta']['frames']] * 2]


def verifier():
    spec = importlib.util.spec_from_file_location('e2_verifier_options', ROOT / VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verifier_default_mutation_tag_is_fresh_and_never_the_retained_tag():
    cli = verifier()
    first, second = cli.options([]), cli.options([])
    assert first.mutation_image != second.mutation_image
    assert re.fullmatch(r'resense:p1-e2-mutation-[0-9a-f]{32}', first.mutation_image)
    assert first.mutation_image != 'resense:p1-e2-mutation-check'


def test_verifier_accepts_explicit_tags_and_output_without_creating_them(tmp_path):
    out = tmp_path / 'not-created'
    args = verifier().options(['--base-image', 'resense:repro-runtime',
                               '--offline-image', 'resense:repro-offline',
                               '--mutation-image', 'resense:repro-mutation', '--out', str(out),
                               '--supplemental'])
    assert (args.base_image, args.offline_image, args.mutation_image) == (
        'resense:repro-runtime', 'resense:repro-offline', 'resense:repro-mutation')
    assert args.out == out and args.supplemental
    assert not out.exists()


@pytest.mark.parametrize('option', ['--offline-image', '--mutation-image'])
def test_verifier_refuses_output_tag_aliasing_the_runtime(option):
    with pytest.raises(SystemExit) as error:
        verifier().options(['--base-image', 'resense:original', option, 'resense:original'])
    assert error.value.code == 2


def test_supplemental_lints_the_source_verifier_with_redirected_output(tmp_path, monkeypatch):
    module = verifier()
    module.OUT = tmp_path / 'new-evidence'
    calls = []

    class StopAfterLint(Exception):
        pass

    def run(name, command):
        calls.append((name, command))
        raise StopAfterLint

    monkeypatch.setattr(module, 'run', run)
    with pytest.raises(StopAfterLint):
        module.supplemental(module.options(['--supplemental', '--out', str(module.OUT)]))
    assert calls[0][0] == 'lint'
    assert str((ROOT / VERIFIER).resolve()) in calls[0][1]
    assert str(module.OUT / 'verify.py') not in calls[0][1]
