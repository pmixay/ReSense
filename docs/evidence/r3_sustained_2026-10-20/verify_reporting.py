"""Check new diagnostics against the independent recount and original gate metrics."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/r3-sustained')
sys.path.insert(0, str(ROOT))
from scripts.set_f_comparison import compare_cohorts, sequence_metrics  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def main():
    spec = importlib.util.spec_from_file_location('r3_gate', ROOT / 'scripts/regression_gate.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    raw_before, raw_after = [read(WORK / f'{s}.json') for s in ('off', 'on')]
    before, after = [sequence_metrics(r['sequences']) for r in (raw_before, raw_after)]
    audit = read(HERE / 'audit.json')
    independent = {(r['kind'], r['file0']): r for r in audit['sequences']}
    generated = read(HERE / 'paired-comparison.json')
    for kind in before:
        comparison = compare_cohorts(before[kind], after[kind])
        assert comparison == generated[kind]
        assert comparison['status'] == ('success_population_expanded' if kind == 'cable'
                                         else 'no_sequence_regression')
        for pair in comparison['pairs']:
            raw = independent[(kind, pair['identity']['file0'])]
            assert pair['baseline_sustained_m'] == raw['old_sustained']
            assert pair['current_sustained_m'] == raw['new_sustained']
            assert pair['lost_hit_frames'] == raw['lost']
            assert pair['added_hit_frames'] == raw['added']
            assert pair['false_detections_added'] == raw['new_fp'] - raw['old_fp']
            assert not pair['regressed']
    legacy = read(ROOT / 'docs/evidence/h1_trajectory_2026-10-19/merged-gate.json')
    enriched = deepcopy(legacy)
    enriched['set_F_straight'] = gate.set_f_entry(raw_after)
    # New evidence is additive. Every historic scalar value, direction and gated bit is exact.
    assert gate.metrics(enriched) == gate.metrics(legacy)
    assert all(r['verdict'] == 'same' for r in gate.compare(legacy, enriched))
    # Re-grade the same complete prior gate, do not mislabel this as a new detector replay.
    with (WORK / 'enriched-prior-gate.json').open('x') as out:
        json.dump(enriched, out, indent=2)
    subprocess.run([sys.executable, str(ROOT / 'scripts/regression_gate.py'),
        '--from-json', str(WORK / 'enriched-prior-gate.json'),
        '--baseline', str(ROOT / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json'),
        '--changed-only', '--out', str(HERE / 'regraded-prior-gate.json')],
        cwd=ROOT, check=True, stdout=(WORK / 'regraded-prior-gate.log').open('x'))
    result = read(HERE / 'regraded-prior-gate.json')
    assert result['gate'] == legacy['gate']
    assert all(r['status'] == 'not_comparable' for r in result['set_F_sequence_comparison'].values())
    # Older summaries cannot prove a paired identity. They must explicitly say so.
    assert len(gate.metrics(legacy)) == 224
    non_timing = [k for k in gate.metrics(legacy) if not k.startswith('latency_ms.')]
    assert len(non_timing) == 208
    subprocess.run(['git', 'diff', '--exit-code', '0f02b28', 'HEAD', '--', 'resense', 'native', 'configs',
                    'ros2_ws', 'setup.py', 'pyproject.toml'], cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--exit-code', '--', 'resense', 'native', 'configs', 'ros2_ws',
                    'setup.py', 'pyproject.toml'], cwd=ROOT, check=True)
    tests = ET.parse(WORK / 'tests.xml')
    test_cases = list(tests.iter('testcase'))
    assert not list(tests.iter('failure')) and not list(tests.iter('error')) and not list(tests.iter('skipped'))
    scripts = ['scripts/regression_gate.py', 'scripts/set_f_comparison.py',
               'tests/test_regression_gate.py', 'tests/test_set_f_comparison.py']
    report = dict(status='PASS', paired_sequences_independently_checked=len(independent),
        original_non_timing_metrics_unchanged=len(non_timing),
        original_all_metrics_and_gated_bits_unchanged=len(gate.metrics(legacy)),
        legacy_baseline_paired_identity='not_comparable, correctly reported',
        prior_full_gate_regrade=result['gate'], fresh_full_detector_gate_replay=False,
        detector_source_unchanged_since='0f02b283a9a8ebeb8bccae76a7b12f23862206df',
        affected_tests_passed=len(test_cases),
        reporting_source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in scripts})
    with (HERE / 'reporting-verification.json').open('x') as out:
        json.dump(report, out, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
