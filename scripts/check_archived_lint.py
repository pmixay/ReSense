#!/usr/bin/env python3
"""Verify immutable evidence inputs before linting every other file with Ruff 0.15.8.

No historical helper is imported or executed. Exact file exclusions are derived only
after bytes, Git blobs, pre-existing package provenance and inventory pass verification.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'docs/evidence/integration_ci_2026-10-16/lint_record/snapshot_lock.json'
LOCK_SHA256 = 'b78312866a4b14a32ae69b8146c8b0729d04455240b1f86851731ac0db07a0be'
RUFF_VERSION = '0.15.8'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def safe_path(root, name):
    path = PurePosixPath(name)
    if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
            or any(c in name for c in '*?[]{}') or path.as_posix() != name):
        raise ValueError(f'not an exact repository path: {name}')
    actual = root / name
    if not actual.resolve().is_relative_to(root.resolve()) or actual.is_symlink():
        raise ValueError(f'outside repository or symlink: {name}')
    return actual


def json_pointer(value, pointer):
    for key in pointer:
        value = value[key]
    return value


def verify(root, lock):
    """Pure filesystem contract, also usable on an exported clean source snapshot."""
    if lock['schema'] != 'resense-archived-lint-v1' or lock['ruff'] != RUFF_VERSION:
        raise ValueError('unsupported snapshot policy')
    records = lock['files']
    names = [r['path'] for r in records]
    if len(names) != len(set(names)) or not names:
        raise ValueError('empty or duplicate snapshot inventory')
    blobs = {}
    for record in records:
        name = record['path']
        data = safe_path(root, name).read_bytes()
        if (len(data) != record['bytes'] or sha256(data) != record['sha256']
                or git_blob(data) != record['git_blob']):
            raise ValueError(f'changed immutable snapshot: {name}')
        blobs[name] = data
    python_files = {n for n in names if n.endswith('.py')}
    inventoried = set()
    for folder in lock['python_roots']:
        actual = {p.relative_to(root).as_posix() for p in safe_path(root, folder).rglob('*.py')}
        expected = {n for n in python_files if n.startswith(folder + '/')}
        if actual != expected:
            raise ValueError(f'unlisted/missing snapshot Python: {folder}: {sorted(actual ^ expected)}')
        inventoried.update(actual)
    if inventoried != python_files:
        raise ValueError('Python inventory has uncovered files')
    exclusions = lock['exclusions']
    paths = [entry['path'] for entry in exclusions]
    if not paths or len(paths) != len(set(paths)) or not set(paths) <= python_files:
        raise ValueError('invalid exact exclusion inventory')
    for entry in exclusions:
        source = entry['provenance']
        document = json.loads(blobs[source['path']])
        recorded = json_pointer(document, source['pointer'])
        if source['kind'] == 'package-sha256':
            if recorded != sha256(blobs[entry['path']]):
                raise ValueError(f'package hash mismatch: {entry["path"]}')
        elif source['kind'] == 'git-pinned-launch':
            # This launcher already pinned a historical commit and helper path. The
            # separately locked helper Git blob was resolved from that commit at review.
            if source['commit'] not in recorded or entry['path'] not in recorded:
                raise ValueError('launch provenance does not pin the helper')
            if source['source_blob'] != git_blob(blobs[entry['path']]):
                raise ValueError('launch source blob mismatch')
        else:
            raise ValueError('unknown provenance kind')
    return paths


def audit_live_references(root, lock):
    """Reject statically visible runtime dependencies on archived helper code.

    Scan maintained Python plus shell/build/workflow text. JSON witness references
    remain valid: only Python paths, module imports and Python search-path additions
    are forbidden. Dynamic construction still requires code review, as does any import.
    """
    paths = {entry['path'] for entry in lock['exclusions']}
    modules = {p.removesuffix('.py').replace('/', '.') for p in paths}
    folders = {str(PurePosixPath(p).parent) for p in paths}
    checked = []
    for folder in ('resense', 'ros2_ws', 'scripts', 'tests', 'web', 'webapp', 'docker', '.github'):
        for path in sorted((root / folder).rglob('*')):
            if not path.is_file() or any(p in ('node_modules', '__pycache__', 'build', 'dist', 'install', 'log') for p in path.parts):
                continue
            if path.suffix not in ('.py', '.sh', '.yaml', '.yml') and not path.name.startswith('Dockerfile'):
                continue
            relative = path.relative_to(root).as_posix()
            text = path.read_text(encoding='utf-8-sig')
            checked.append(relative)
            if path.suffix == '.py':
                tree = ast.parse(text, filename=relative)
                for node in ast.walk(tree):
                    imports = ([a.name for a in node.names] if isinstance(node, ast.Import)
                               else [node.module or '', *[f'{node.module}.{a.name}' for a in node.names]]
                               if isinstance(node, ast.ImportFrom) else [])
                    if any(m == n or m.startswith(n + '.') for m in imports for n in modules):
                        raise ValueError(f'live import of frozen helper: {relative}:{node.lineno}')
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        value = node.value.replace('\\', '/')
                        if value in folders or any(p in value for p in paths):
                            raise ValueError(f'live reference to frozen helper: {relative}:{node.lineno}')
            elif any(p in text for p in paths):
                raise ValueError(f'live invocation/copy of frozen helper: {relative}')
    return checked


def lint_command(root, exclusions, ruff):
    # Absolute exact paths avoid basename matches in unrelated maintained directories.
    return [ruff, 'check', '--no-cache', '--output-format', 'github',
            '--extend-exclude', ','.join(str((root / p).resolve()) for p in exclusions), str(root)]


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--lint', action='store_true')
    cli.add_argument('--ruff', default='ruff', help='Ruff executable, must be exactly 0.15.8')
    args = cli.parse_args(argv)
    data = (ROOT / MANIFEST).read_bytes()
    # Cross-platform checkout EOL is tolerated only for this NEW policy JSON, never snapshots.
    if sha256(data.replace(b'\r\n', b'\n')) != LOCK_SHA256:
        raise ValueError('snapshot policy changed; explicit reviewed lock update required')
    lock = json.loads(data)
    exclusions = verify(ROOT, lock)
    scanned = audit_live_references(ROOT, lock)
    print(json.dumps({'result': 'PASS', 'immutable_files': len(lock['files']),
                      'exact_ruff_exclusions': len(exclusions), 'live_files_audited': len(scanned)}), flush=True)
    if args.lint:
        version = subprocess.check_output([args.ruff, '--version'], text=True).strip()
        if version != f'ruff {RUFF_VERSION}':
            raise ValueError(f'wrong lint version: {version}')
        return subprocess.call(lint_command(ROOT, exclusions, args.ruff))
    return 0


if __name__ == '__main__':
    sys.exit(main())
