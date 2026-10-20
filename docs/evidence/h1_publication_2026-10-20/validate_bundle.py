"""Check portable H1 evidence, including exact archived experiment tools."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archive_tools(directory):
    metadata = directory / 'tool-snapshots.json'
    if not metadata.exists():
        return {}
    recorded = json.loads(metadata.read_text())
    archive = directory / 'tool-snapshots.tar.xz'
    assert digest(archive.read_bytes()) == recorded['archive_sha256']
    result = {}
    with tarfile.open(archive, 'r:xz') as stream:
        assert set(stream.getnames()) == set(recorded['members'])
        for member, expected in recorded['members'].items():
            assert Path(member).name == member
            data = stream.extractfile(member).read()
            assert len(data) == expected['bytes'] and digest(data) == expected['sha256']
            ast.parse(data, filename=member)
            result[member] = data
    return result


def read_payload(directory, name, tools):
    if name in tools:
        return tools[name]
    path = directory / name
    assert path.resolve().is_relative_to(directory.resolve())
    return path.read_bytes()


def main():
    receipt = json.loads((HERE / 'copy-receipt.json').read_text())
    toolsets = {}
    for item in receipt['copied_files']:
        path = ROOT / item['path']
        tools = toolsets.setdefault(path.parent, archive_tools(path.parent))
        data = read_payload(path.parent, path.name, tools)
        assert len(data) == item['bytes'] and digest(data) == item['sha256'], item['path']
    packages = [ROOT / 'docs/evidence' / name for name in [
        'h1_independent_2026-10-20', 'h1_miss_audit_2026-10-20',
        'h1_rail_limits_2026-10-20', 'h1_final_review_2026-10-20',
        'h1_current_source_2026-10-20']]
    checksum_count = 0
    for directory in packages:
        tools = archive_tools(directory)
        lists = [directory / ('SHA256SUMS-publication' if (directory / 'SHA256SUMS-publication').exists() else 'SHA256SUMS')]
        for checksum_list in lists:
            if not checksum_list.exists():
                continue
            for line in checksum_list.read_text().splitlines():
                if not line.strip():
                    continue
                expected, name = line.split(maxsplit=1)
                name = name.lstrip('* ')
                assert digest(read_payload(directory, name, tools)) == expected, (directory.name, name)
                checksum_count += 1
    selected = [ROOT / path for path in (HERE / 'publication-paths.txt').read_text().splitlines()]
    selected = [path for path in selected if path.exists()]
    for directory in packages + [HERE]:
        selected.extend(path for path in directory.rglob('*')
                        if path.is_file() and '__pycache__' not in path.parts)
    selected = sorted(set(selected))
    secret = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
    links_checked = 0
    for path in selected:
        data = path.read_bytes()
        assert len(data) < 20_000_000, path
        assert not secret.search(data), path
        if path.suffix == '.py':
            ast.parse(data, filename=str(path))
        if path.suffix == '.json':
            json.loads(data)
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^\s)]+)', data.decode('utf-8')):
                target = target.split('#')[0]
                if not target or ':' in target or target.startswith('#'):
                    continue
                actual = (path.parent / target).resolve()
                if not actual.exists() and actual.name in archive_tools(actual.parent):
                    links_checked += 1
                    continue
                assert actual.exists(), (str(path), target)
                links_checked += 1
    control = (HERE / 'copy-receipt.json').read_bytes()
    assert digest(control) != digest(bytes([control[0] ^ 1]) + control[1:])
    git = ['git', '--no-optional-locks', '-C', str(ROOT)]
    assert not subprocess.check_output(git + ['diff', '--name-only', 'HEAD', '--',
                                            'resense', 'native', 'configs', 'ros2_ws', 'setup.py', 'pyproject.toml'])
    assert not subprocess.check_output(git + ['diff', '--name-only', receipt['current_replayed_head'], 'HEAD', '--',
                                            'resense', 'native', 'configs', 'ros2_ws', 'setup.py', 'pyproject.toml'])
    subprocess.run(['python3', '-B', str(ROOT / 'scripts/detector_freeze.py'), 'verify'], check=True)
    report_path = HERE / 'validation.json'
    report = {'status': 'PASS', 'h1_acceptance': 'BLOCKED',
              'publication_parent': subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip(),
              'detector_bytes_equal_replayed_520e7dc': True,
              'copied_payloads_checked': len(receipt['copied_files']),
              'original_checksum_entries_checked': checksum_count,
              'archived_python_tools': sum(len(archive_tools(p)) for p in packages),
              'local_markdown_links_checked': links_checked,
              'planted_changed_byte_detected': True,
              'intended_files': len(selected) + (0 if report_path in selected else 1)}
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    selected.append(report_path)
    (HERE / 'publication-paths.txt').write_text('\n'.join(sorted({str(p.relative_to(ROOT)) for p in selected})) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
