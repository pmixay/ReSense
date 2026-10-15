"""Dataset-free image regressions: exact pure fixtures and repeatable E2 verifier options."""
import importlib.util
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
JUDGE = 'docs/evidence/judgement_2026-10-13/scripts/docker/'
STARTUP = 'docs/evidence/node_startup_2026-10-15/docker_tools/'
VERIFIER = 'docs/evidence/offline_rebuild_2026-10-15/verify.py'
FIXTURES = [
    'webapp/backend/resense_web/__init__.py',
    'webapp/backend/resense_web/decision.py',
    *[JUDGE + name for name in ('analyze_chain.py', 'chain.sh', 'listener.py')],
    *[STARTUP + name for name in ('analyze_chain.py', 'chain.sh', 'launch_matrix.py', 'listener.py',
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
