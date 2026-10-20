"""Bind the published merge to the measured source and check evidence links/digests."""
import hashlib
import json
import re
import subprocess

import run_checks

ROOT, HERE = run_checks.ROOT, run_checks.HERE
MEASURED = 'afbf9fc949f31e920a4d698df8fdfd058afeb308'
MAIN = '99dab01'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


expected = json.loads((HERE / 'gate-merged-candidate-execution.json').read_text())
assert expected['commit'] == MEASURED and expected['source_unchanged'] and expected['returncode'] == 0
actual = run_checks.receipts.sources(ROOT)
assert actual == expected['source_sha256']
paths = ['resense', 'native', 'configs', 'ros2_ws', 'setup.py', 'pyproject.toml']
assert not git('diff', MEASURED, '--', *paths)
subprocess.run(['git', 'merge-base', '--is-ancestor', MAIN, 'HEAD'], cwd=ROOT, check=True)
assert git('diff', '--name-only', MAIN, '--', *paths) == 'resense/calibration.py'
assert not git('diff', '--name-only', '--diff-filter=U')

package = json.loads((HERE / 'package.json').read_text())
for archive in package['archives']:
    path = HERE / archive['file']
    assert path.stat().st_size == archive['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == archive['sha256']

files = [ROOT / name for name in ('README.md', 'CHANGELOG.md', 'docs/README.md', 'docs/BACKLOG.md')]
files += [HERE / 'README.md', HERE / 'PROTOCOL.md', HERE / 'PUBLICATION.md']
checked = []
for path in files:
    text = path.read_text()
    links = re.findall(r'\[[^\]]*\]\(([^)]+)\)', text)
    links += re.findall(r'^\[[^\]]+\]:\s+(\S+)', text, flags=re.M)
    for link in links:
        if link.startswith(('https:', 'http:', '#', 'mailto:')):
            continue
        target = path.parent / link.split('#')[0]
        assert target.exists() or target == HERE / 'publication-verification.json', (path, link)
        checked.append([str(path.relative_to(ROOT)), link])

result = {'published_merge': git('rev-parse', 'HEAD'), 'measured_source': MEASURED,
          'included_remote_main': MAIN, 'source_and_native_files_equal': len(actual),
          'independent_git_production_diff_empty': True,
          'only_production_change_from_remote_main': 'resense/calibration.py',
          'unmerged_paths': [], 'archive_digests_checked': len(package['archives']),
          'local_links_checked': len(checked), 'local_links': checked}
(HERE / 'publication-verification.json').write_text(json.dumps(result, indent=2) + '\n')
assert all((ROOT / path).parent.joinpath(link.split('#')[0]).exists() for path, link in checked)
print(json.dumps({k: v for k, v in result.items() if k != 'local_links'}, indent=2))
