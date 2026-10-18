#!/usr/bin/env python3
"""Capture the actual software-rendered RViz window while the documented wrapper plays a curve."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=Path('/home/resense/data/n1_rviz_final'))
parser.add_argument('--rate', default='0.5')
parser.add_argument('--headless', action='store_true', help='Matched wrapper playback without RViz')
args = parser.parse_args()
OUT = args.out
OUT.mkdir(parents=True, exist_ok=True)
command = [str(ROOT/('scripts/play_bag.sh' if args.headless else 'scripts/run_demo.sh')), '--sensor-profile', 'pandar128',
           '--clear-range-policy', 'conservative',
           '/home/resense/data/n4_curve_preview', '--rate', args.rate]
environment = {**os.environ, 'IMAGE':'resense:n1n4-check', 'NODE_NAME':'resense_n1_graphics',
               'LIBGL_ALWAYS_SOFTWARE':'1'}
observer_command = ['docker', 'run', '--rm', '--name', 'resense_n1_observer',
                    '--net=host', '--ipc=host', '-v', f'{OUT.resolve()}:/out',
                    '-v', f'{Path(__file__).with_name("capture_status.py").resolve()}:/capture.py:ro',
                    'resense:n1n4-check', 'python3', '/capture.py', '/out/status.jsonl']
observer_log = (OUT/'observer.log').open('w')
observer = subprocess.Popen(observer_command, stdout=observer_log, stderr=subprocess.STDOUT)
deadline = time.monotonic() + 20
while not (OUT/'status.ready').exists():
    if observer.poll() is not None or time.monotonic() >= deadline:
        raise RuntimeError('status observer failed to start')
    time.sleep(.1)
samples = []
cgroup = None
with (OUT/'wrapper.log').open('w') as log:
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
    started = time.monotonic()
    captures = []
    try:
        while process.poll() is None and time.monotonic()-started < 90:
            time.sleep(.5)
            logs = subprocess.run(['docker','logs','resense_n1_graphics'],capture_output=True,text=True)
            if logs.returncode == 0:
                (OUT/'container.log').write_text(logs.stdout+logs.stderr)
                if cgroup is None:
                    inspect = subprocess.run(['docker', 'inspect', 'resense_n1_graphics', '--format', '{{.State.Pid}}'], capture_output=True, text=True)
                    if inspect.returncode == 0 and int(inspect.stdout) > 0:
                        entry = Path(f'/proc/{int(inspect.stdout)}/cgroup').read_text().strip()
                        cgroup = Path('/sys/fs/cgroup') / entry.split('::', 1)[1].lstrip('/')
                if cgroup is not None and (cgroup/'cpu.stat').exists():
                    cpu = dict(line.split() for line in (cgroup/'cpu.stat').read_text().splitlines())
                    samples.append({'mono': time.monotonic(), 'cpu_usage_usec': int(cpu['usage_usec']),
                                    'memory_current_bytes': int((cgroup/'memory.current').read_text()),
                                    'memory_peak_bytes': int((cgroup/'memory.peak').read_text())})
            if not args.headless and 'axis y=' in logs.stdout+logs.stderr:
                path = OUT/f'capture_{len(captures):02d}.png'
                ImageGrab.grab(xdisplay=os.environ['DISPLAY']).save(path)
                captures.append(str(path))
        if process.poll() is None:
            process.terminate()
        code = process.wait(timeout=15)
    finally:
        if process.poll() is None:
            process.kill()
        subprocess.run(['docker', 'stop', '-t', '2', 'resense_n1_observer'], capture_output=True)
        observer.wait(timeout=5)
        observer_log.close()
result = {'command':command,'observer_command':observer_command,'exit_code':code,'display':os.environ.get('DISPLAY'),
          'image':subprocess.check_output(['docker','inspect','resense:n1n4-check','--format','{{.Id}}'],text=True).strip(),
          'software_rendering':not args.headless,'captures':captures,
          'cpu_affinity': sorted(os.sched_getaffinity(0)),
          'cgroup_samples':samples,
          'node_container_cpu_cores_mean': ((samples[-1]['cpu_usage_usec']-samples[0]['cpu_usage_usec']) / 1e6 /
                                            (samples[-1]['mono']-samples[0]['mono'])) if len(samples)>1 else None,
          'node_container_memory_peak_mb': max((s['memory_peak_bytes']/2**20 for s in samples), default=None),
          'scope':'actual Docker wrapper, optional RViz on Xvfb; decoded curve geometry; cgroup includes detector+RViz, not player/observer/Xvfb'}
(OUT/'capture.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
