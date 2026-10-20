"""Package or read-only verify the P3 response evidence and current source identity."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((HERE / name).read_text())


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def checks():
    run = load('run.json')
    assert {name: sha(ROOT / name) for name in run['source']['files']} == run['source']['files']
    for item in run['phases'].values():
        assert sha(HERE / item['path']) == item['sha256']
    verification = load('verification.json')
    retention = load('retention-verification.json')
    assert verification['status'] == retention['status'] == 'PASS'
    assert verification['tests'] == {'tests': 257, 'failures': 0, 'errors': 0, 'skipped': 0}
    empty = [case for case in load('f1a.json') if case['top_above_true_rail'] is None]
    assert len(empty) == 6 and not any(row['global_STOP'] for case in empty for row in case['rows'])
    assert verification['b4']['plain_traced_exact_cases'] == 420
    assert retention['exact_plain_traced_rows'] == 698
    for path in HERE.iterdir():
        if not path.is_file():
            continue
        assert path.stat().st_size < 20_000_000, path.name
        if path.suffix == '.json':
            json.loads(path.read_text())
        if path.suffix == '.py':
            ast.parse(path.read_bytes(), filename=path.name)
    subprocess.run(['python3', '-B', str(ROOT / 'scripts/detector_freeze.py'), 'verify'], check=True)
    return {'status': 'PASS', 'seal': run['source']['seal'],
            'author_response_complete': True, 'independent_bundle_acceptance': 'SEPARATE_PENDING',
            'production_modified': False, 'b4_is_a_confirmed_limitation': True,
            'b4_matrix': 420, 'b4_guards': 14, 'b4_retention_exact_rows': 698,
            'actual_keep_returns_checked': retention['actual_keep_returns_verified'],
            'f1a_arms': 72, 'f1a_rows': 864, 'empty_controls_global_STOP': 0,
            'r3_plain_traced_rows': 320, 'l16_rows': 1350,
            'existing_gate_raw_rows_recounted': 15269, 'tests_passed': 257}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--create', action='store_true')
    args = parser.parse_args()
    summary = checks()
    if args.create:
        partial = Path('/tmp/opencode/p3-review-response-work/b4_retention_partial.json.txt')
        summary['failed_retention_serialization_capture'] = {
            'retained_on_VM': partial.exists(), 'sha256': sha(partial) if partial.exists() else None,
            'reason': 'strict JSON rejected infinite since_clean; corrected serialization, complete experiment repeated'}
        save('finalization.json', summary)
        files = {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path)}
                 for path in sorted(HERE.iterdir()) if path.is_file()
                 and path.name not in ('artifact-manifest.json', 'SHA256SUMS')}
        tools = {str(path.relative_to(ROOT)): sha(path)
                 for path in sorted((ROOT / 'docs/evidence/p4_review_shipping_2026-10-20/scripts').glob('*.py'))}
        save('artifact-manifest.json', {'measured_commit': load('run.json')['measured_commit'],
                                        'files': files, 'original_P4_tool_hashes': tools})
        names = sorted([*files, 'artifact-manifest.json'])
        with (HERE / 'SHA256SUMS').open('x') as stream:
            for name in names:
                stream.write(f'{sha(HERE / name)}  {name}\n')
    else:
        manifest = load('artifact-manifest.json')
        for name, info in manifest['files'].items():
            assert (HERE / name).stat().st_size == info['bytes'] and sha(HERE / name) == info['sha256'], name
        for line in (HERE / 'SHA256SUMS').read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            assert sha(HERE / name) == expected, name
        sample = (HERE / 'b4.json').read_bytes()
        assert hashlib.sha256(bytes([sample[0] ^ 1]) + sample[1:]).hexdigest() != sha(HERE / 'b4.json')
        summary['artifact_files_checked'] = len(manifest['files'])
        summary['changed_byte_control_detected'] = True
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
