"""Run the registered complete-timing gate with clean before/after identities."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path('/workspace/ReSense-timing')
out = Path('/cycle/complete_timing/default')
sys.path.insert(0, str(root / 'scripts'))
sys.path.insert(0, str(root))
from detector_freeze import source_digest, source_hashes
from resense import _native
from resense.config import DetectorConfig


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def save(name, value):
    (out / name).write_text(json.dumps(value, indent=2) + '\n')


protocol_path = root / 'docs/evidence/cycle_2026-09-28/complete_timing/protocol.json'
protocol = json.loads(protocol_path.read_text())
files = source_hashes(root)
assert not git('status', '--porcelain'), 'dirty worktree before gate'
commit = git('rev-parse', 'HEAD')
assert commit.startswith('bc75abe'), commit
assert source_digest(files) == protocol['candidate_source_sha256']
assert _native.enabled() and _native.LIBRARY
native_sha = sha(_native.LIBRARY)
assert native_sha == protocol['native_sha256']
config = DetectorConfig.from_yaml(str(root / 'configs/default.yaml')).to_dict()
config_sha = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert config_sha == protocol['effective_config_sha256']
assert sha(root / protocol['baseline_gate']['path']) == protocol['baseline_gate']['sha256']
observer_files = {name: sha(root / name) for name in (
    'scripts/regression_gate.py', 'scripts/eval_real.py', 'scripts/compare_complete_timing.py',
    'scripts/compare_health_gate.py', 'scripts/far_range_eval.py', 'scripts/detector_freeze.py')}
out.mkdir(parents=True, exist_ok=True)
assert not (out / 'gate.json').exists() and not (out / 'run_identity.json').exists(), 'refuse to overwrite a run'
start = time.time()
command = [sys.executable, *protocol['command'][1:]]
save('run_identity.json', {'commit': commit, 'source_sha256': source_digest(files), 'files': files,
                          'native_sha256': native_sha, 'effective_config_sha256': config_sha,
                          'command': command, 'protocol_sha256': sha(protocol_path),
                          'observer_files': observer_files, 'runner_sha256': sha(__file__),
                          'started_unix': start, 'baseline_sha256': protocol['baseline_gate']['sha256']})
print(json.dumps({'started': start, 'commit': commit, 'source_sha256': source_digest(files), 'native_sha256': native_sha}), flush=True)
with (out / 'gate.txt').open('w') as stream:
    result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
source_unchanged = source_hashes(root) == files and git('rev-parse', 'HEAD') == commit and not git('status', '--porcelain')
observers_unchanged = all(sha(root / name) == digest for name, digest in observer_files.items())
native_after = sha(_native.LIBRARY)
save('completion.json', {'exit_code': result.returncode, 'source_unchanged': source_unchanged,
                         'observers_unchanged': observers_unchanged, 'native_sha256': native_after,
                         'elapsed_s': time.time() - start, 'finished_unix': time.time()})
print(json.dumps({'exit_code': result.returncode, 'source_unchanged': source_unchanged,
                  'observers_unchanged': observers_unchanged, 'native_unchanged': native_after == native_sha}), flush=True)
raise SystemExit(result.returncode or (0 if source_unchanged and observers_unchanged and native_after == native_sha else 91))
