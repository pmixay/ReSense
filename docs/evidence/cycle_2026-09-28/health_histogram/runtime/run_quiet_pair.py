"""Execute the predeclared local ROS comparison, retaining every failed run."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

OUT = Path(__file__).resolve().parent
REPO = Path('/home/likikikpa/ReSense-p3-sync')
DATA = Path('/home/likikikpa/ReSense-p4-data/for_hackathon')
protocol = json.loads((OUT / 'quiet_protocol.json').read_text())
for name, checksum in protocol['script_hashes'].items():
    assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == checksum


def snapshot():
    return {'utc': datetime.now(timezone.utc).isoformat(),
            'loadavg': Path('/proc/loadavg').read_text().strip(),
            'thermal_millidegrees': {str(p): p.read_text().strip()
                                    for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}}


results = {'schema': 'resense-health-quiet-runtime-execution-v1',
           'protocol_sha256': hashlib.sha256((OUT / 'quiet_protocol.json').read_bytes()).hexdigest(),
           'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'warmed_inputs': {}, 'runs': {}}
for kind, bag, count in [('positive', 'doubleT_obstacle', 201), ('clear', 'roundT_doubleT', 252)]:
    checksums = {}
    for path in sorted((DATA / bag).glob('*.db3')):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                digest.update(block)
        checksums[path.name] = digest.hexdigest()
    assert checksums, bag
    results['warmed_inputs'][bag] = checksums
    for variant, image in [('baseline', 'resense:cycle-p3-base'), ('candidate', 'resense:cycle-health')]:
        name = f'{variant}_{kind}'
        target = OUT / name
        if target.exists():
            raise RuntimeError(f'refusing to overwrite earlier measurement: {target}')
        time.sleep(30)
        env = dict(os.environ, IMAGE=image, SKIP_BUILD='1', OFFLINE='1', RATE='1.0',
                   BAG_READ_AHEAD_QUEUE_SIZE='10', OUT=str(target))
        env['PATH'] = '/tmp/resense-health-python-bin:' + env['PATH']
        command = ['bash', 'scripts/dry_run.sh', str(DATA / bag),
                   '--min-frames', str(count), '--max-p95-latency', '100', '--max-dropped', '0']
        command += ['--expect-obstacle', '--distance', '50:62'] if kind == 'positive' else ['--expect-clear']
        entry = {'command': command, 'image': image, 'started': snapshot()}
        print('START ' + name, flush=True)
        with (OUT / f'{name}.txt').open('w') as log:
            run = subprocess.run(command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
        entry.update(exit_code=run.returncode, finished=snapshot())
        results['runs'][name] = entry
        (OUT / 'execution.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f'END {name}: exit {run.returncode}', flush=True)
