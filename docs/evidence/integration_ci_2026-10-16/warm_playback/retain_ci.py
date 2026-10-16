"""Retain the authoritative failed P1 playback logs and GitHub job provenance, without replay."""
import json
from pathlib import Path
import subprocess


def main():
    out = Path(__file__).resolve().parent / 'original-ci'
    out.mkdir(exist_ok=False)
    repo = Path(__file__).resolve().parents[4]
    commands = {
        'failed-steps.txt': ['gh', 'run', 'view', '38897519801', '--job', '116961605744', '--log-failed'],
        'docker-job.txt': ['gh', 'run', 'view', '38897519801', '--job', '116961605744', '--log'],
        'run.json': ['gh', 'run', 'view', '38897519801', '--json', 'headSha,conclusion,jobs,url'],
    }
    receipts = []
    for name, command in commands.items():
        result = subprocess.run(command, cwd=repo, capture_output=True)
        result.check_returncode()
        (out / name).write_bytes(result.stdout)
        receipts.append({'command': command, 'exit': result.returncode, 'bytes': len(result.stdout)})
    (out / 'capture.json').write_text(json.dumps(receipts, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
