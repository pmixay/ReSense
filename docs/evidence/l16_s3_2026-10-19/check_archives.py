"""Check manifest archive hashes with the independent system sha256sum tool."""
import json
from pathlib import Path
import subprocess

here = Path('/home/aiops/resense/docs/evidence/l16_s3_2026-10-19')
report = json.loads((here / 'author_acceptance.json').read_text())
entries = sorted((a['path'], a['sha256']) for a in report['archives'].values())
assert all(Path(name).name == name for name, _ in entries)
(here / 'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name, digest in entries))
control = subprocess.run(['sha256sum', '--check', '-'], cwd=here, text=True, capture_output=True,
                         input=f"{'0' * 64}  {entries[0][0]}\n")
assert control.returncode == 1 and 'FAILED' in control.stdout
result = subprocess.run(['sha256sum', '--check', 'SHA256SUMS'], cwd=here, text=True,
                        capture_output=True, check=True)
(here / 'archive_verification.log').write_text(result.stdout)
(here / 'archive_verification.json').write_text(json.dumps({
    'system_tool': 'sha256sum --check', 'archives_checked': len(entries),
    'wrong_checksum_positive_control_rejected': True, 'returncode': result.returncode}, indent=2) + '\n')
print(result.stdout, end='')
