"""Focused Linux contracts and real shell gate wiring, without playing any ROS data."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def shell_checks(root):
    for name in ('scripts/dry_run.sh', 'scripts/p1_cold_bag_test.sh'):
        subprocess.run(['bash', '-n'], input=(root / name).read_text(), text=True, check=True)
    text = (root / 'scripts/dry_run.sh').read_text()
    section = text.split("<<'INNER'\n", 1)[1].split('\nINNER', 1)[0].split('sleep 2\n', 1)[1].split('kill "$ECHO_PID"', 1)[0]
    with tempfile.TemporaryDirectory(prefix='warm-gate-') as tmp:
        work = Path(tmp)
        bag = work / 'bag'
        bag.mkdir()
        env = dict(os.environ, WARM_CACHE='1', BAG_NAME='fixture', RATE='1.0', BAG_READ_AHEAD_QUEUE_SIZE='10',
                   BAG_FIXTURE=str(bag), PLAY_LOG=str(work / 'played.txt'))
        outcomes = []
        for valid in (False, True):
            out = work / ('green' if valid else 'red')
            out.mkdir()
            if valid:
                (bag / 'metadata.yaml').write_text('storage_identifier: sqlite3\n')
                (bag / 'fixture.db3').write_bytes(b'a' * 8192)
            script = ('set -euo pipefail\nsleep() { :; }\nros2() { printf "%s\\n" "$*" >> "$PLAY_LOG"; }\n' + section
                      .replace('/out/', str(out) + '/').replace('"/data/$BAG_NAME"', '"$BAG_FIXTURE"'))
            result = subprocess.run(['bash', '-s'], input=script, env=env, cwd=root, text=True, capture_output=True)
            assert result.returncode == (0 if valid else 1), result.stdout + result.stderr
            played = Path(env['PLAY_LOG']).exists()
            assert played == valid, 'failed precondition reached player'
            receipt = json.loads((out / 'warm_cache_before.json').read_text())
            assert receipt['status'] == ('WARM_VERIFIED' if valid else 'ERROR')
            if valid:
                assert json.loads((out / 'warm_cache_after.json').read_text())['status'] == 'OBSERVED'
                assert '--rate 1.0 --clock --delay 3 --read-ahead-queue-size 10 --disable-keyboard-controls' in (
                    work / 'played.txt').read_text()
            outcomes.append({'valid_bag': valid, 'exit': result.returncode, 'player_called': played})
        return outcomes


def warm_commands(text):
    lines = text.replace('\\\n', ' ').splitlines()
    return [[w for w in shlex.split(line) if w != 'WARM_CACHE=1'] for line in lines
            if 'OUT="$OUT/warm_' in line and 'scripts/dry_run.sh' in line]


def main():
    if sys.argv[1:] == ['--linux']:
        root = Path('/work')
        subprocess.run(['python3', 'tests/test_warm_cache.py', '-v'], cwd=root, check=True)
        print(json.dumps({'shell_gate': shell_checks(root)}))
        return
    root = Path(__file__).resolve().parents[4]
    out = Path(__file__).resolve().parent / 'preflight-final'
    out.mkdir(exist_ok=False)
    original = subprocess.check_output(['git', 'show', 'b0c9c17:scripts/p1_cold_bag_test.sh'], cwd=root, text=True)
    current = (root / 'scripts/p1_cold_bag_test.sh').read_text()
    before, after = warm_commands(original), warm_commands(current)
    assert len(before) == len(after) == 2 and before == after, 'warm acceptance command changed'
    command = ['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python3',
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', f'{root}:/work:ro', '-w', '/work',
               'resense:h4-fixture-fixed-1cfe8de-20261016',
               '/work/docs/evidence/integration_ci_2026-10-16/warm_playback/preflight.py', '--linux']
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (out / 'linux-contracts.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    result.check_returncode()
    report = {'result': 'PASS', 'command': command, 'unit_tests': 12, 'warm_commands_unchanged': before,
              'shell': json.loads(result.stdout.strip().splitlines()[-1])}
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
