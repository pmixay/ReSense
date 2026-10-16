"""Focused Linux preflight of full-CI routing; never plays bags or mutates Docker resources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REF = 'refs/heads/integration/2026-10-15-16'
WORKFLOW = '.github/workflows/ci.yml'
COLD = 'scripts/p1_cold_bag_test.sh'


def refs(expression):
    return set(re.findall(r"github\.ref == '([^']+)'", expression))


def condition(expression, values, success=True):
    """Evaluate only the checked workflow's Boolean routing expressions, not shell code."""
    code = expression.removeprefix('${{').removesuffix('}}').strip()
    code = re.sub(r'\b(?:github|env|steps)\.[\w.-]+', lambda m: repr(values.get(m[0], '')), code)
    for call, value in (('success()', success), ('cancelled()', False), ('always()', True)):
        code = code.replace(call, repr(value))
    code = re.sub(r'!(?!=)', ' not ', code.replace('&&', ' and ').replace('||', ' or '))
    return bool(eval(code.strip(), {'__builtins__': {}}, {}))


def linux(payload):
    import yaml

    before, after = (yaml.load(payload[n][WORKFLOW], Loader=yaml.BaseLoader) for n in ('before', 'after'))
    assert after['on'] == {'push': ''}, after['on']
    assert set(after['jobs']) == {'checks', 'pytest', 'webapp', 'docker', 'offline-build'}
    for name in ('checks', 'pytest', 'webapp'):
        assert before['jobs'][name] == after['jobs'][name], name
    old_docker, docker = before['jobs']['docker'], after['jobs']['docker']
    assert refs(docker['env']['FULL']) == refs(old_docker['env']['FULL']) | {REF}
    assert docker['needs'] == 'checks'
    steps = docker['steps']
    viewer = next(s for s in steps if 'scripts/p2_viewer_test.sh' in s.get('run', ''))
    restore = next(s for s in steps if s.get('id') == 'bags')
    fetch = next(s for s in steps if s.get('id') == 'fetch')
    regression = next(s for s in steps if 'NO_DOWNLOAD=1 scripts/p1_cold_bag_test.sh' in s.get('run', ''))
    missing = next(s for s in steps if 'regression not run' in s.get('name', ''))
    assert all('continue-on-error' not in s for s in steps)
    assert regression['timeout-minutes'] == '15'
    assert regression['run'] == next(s['run'] for s in old_docker['steps']
                                     if 'NO_DOWNLOAD=1 scripts/p1_cold_bag_test.sh' in s.get('run', ''))
    assert fetch['run'] == next(s['run'] for s in old_docker['steps'] if s.get('id') == 'fetch')
    assert restore['with'] == next(s['with'] for s in old_docker['steps'] if s.get('id') == 'bags')

    # Execute the production Bash guard, stopping before ROOT/mktemp/Docker/data operations.
    script, old_script = (payload[n][COLD] for n in ('after', 'before'))
    guard, tail = script.split('\nesac', 1)
    assert tail == old_script.split('\nesac', 1)[1], 'cold/warm execution and thresholds changed'
    subprocess.run(['bash', '-n'], input=script, text=True, check=True)
    shell_refs = set(re.findall(r'refs/heads/[^|)\s]+', guard))
    assert shell_refs == refs(docker['env']['FULL'])
    negative = ['refs/heads/integration/2026-10-15-160', 'refs/heads/feature/ordinary', 'refs/pull/1/merge', '']
    branch_checks = []
    for ref in sorted(shell_refs) + negative:
        expected = ref in shell_refs
        actual = condition(docker['env']['FULL'], {'github.ref': ref})
        result = subprocess.run(['bash', '-s'], input=guard + '\nesac\nprintf "FULL_GUARD_ACCEPTED\\n"\n',
                                text=True, capture_output=True, env=dict(os.environ, GITHUB_REF=ref), check=True)
        assert actual == expected == ('FULL_GUARD_ACCEPTED' in result.stdout), (ref, result.stdout)
        branch_checks.append({'ref': ref, 'full': actual, 'shell_guard_matches': True})

    values = {'env.FULL': 'true', 'steps.bags.outcome': 'success'}
    assert condition(viewer['if'], values) and condition(restore['if'], values)
    scenarios = [('cache_hit', 'true', '', True, False), ('verified_download', 'false', 'success', True, False),
                 ('download_failed', 'false', 'failure', False, True)]
    for name, hit, outcome, runs, fails in scenarios:
        state = dict(values, **{'steps.bags.outputs.cache-hit': hit, 'steps.fetch.outcome': outcome})
        assert condition(regression['if'], state) == runs, name
        assert condition(missing['if'], state, success=not fails) == fails, name
        assert condition(fetch['if'], state) == (hit != 'true'), name
    assert not condition(viewer['if'], {'env.FULL': 'false'})
    assert not condition(restore['if'], {'env.FULL': 'false'})

    # Execute the real missing-data handler: nonzero exit, error annotation, retained summary.
    with tempfile.TemporaryDirectory(prefix='resense-ci-routing-') as tmp:
        summary = Path(tmp) / 'summary.md'
        result = subprocess.run(['bash', '-s'], input=missing['run'], text=True, capture_output=True,
                                env=dict(os.environ, GITHUB_STEP_SUMMARY=str(summary)))
        assert result.returncode == 1 and '::error::' in result.stdout, result
        assert 'NOT RUN' in summary.read_text()

    archive = next(s for s in after['jobs']['offline-build']['steps'] if s.get('id') == 'artifact')
    old_archive = next(s for s in before['jobs']['offline-build']['steps'] if s.get('id') == 'artifact')
    assert refs(archive['if']) == refs(old_archive['if']) | {REF}
    state = {'github.ref': REF, 'github.event_name': 'push'}
    assert condition(archive['if'], state) and not condition(archive['if'], state, success=False)
    assert not condition(archive['if'], dict(state, **{'github.event_name': 'pull_request'}))
    shell_steps = 0
    for job in after['jobs'].values():
        for step in job['steps']:
            if 'run' in step:
                shell = re.sub(r'\$\{\{.*?\}\}', 'actions_value', step['run'])
                subprocess.run(['bash', '-n'], input=shell, text=True, check=True)
                shell_steps += 1
    return {'result': 'PASS', 'branch_checks': branch_checks, 'workflow_bash_steps_syntax_checked': shell_steps,
            'cache_hit_runs_regression': True, 'verified_download_runs_regression': True,
            'missing_verified_bags_fail_job': True, 'cold_warm_body_and_thresholds_unchanged': True,
            'integration_archive_enabled_after_success': True, 'trigger': 'push'}


def main():
    if sys.argv[1:] == ['--linux']:
        print(json.dumps(linux(json.load(sys.stdin)), indent=2))
        return
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--image', default='resense:integration-fixtures-f8c088d-20261016')
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    root = Path(__file__).resolve().parents[3]
    args.out.mkdir(parents=True, exist_ok=False)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    payload = {'before': {}, 'after': {}}
    for path in (WORKFLOW, COLD):
        payload['before'][path] = subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=root, text=True)
        payload['after'][path] = (root / path).read_text(encoding='utf-8')
    image_id = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', args.image], text=True).strip()
    command = ['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python3',
               '-v', f'{Path(__file__).resolve()}:/verify.py:ro', '-w', '/', args.image, '/verify.py', '--linux']
    result = subprocess.run(command, input=json.dumps(payload), capture_output=True, text=True, timeout=90)
    (args.out / 'linux-preflight.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    result.check_returncode()
    report = dict(json.loads(result.stdout), source_commit=commit, command=command, image=args.image, image_id=image_id,
                  checked_sha256={p: hashlib.sha256(payload['after'][p].encode()).hexdigest() for p in (WORKFLOW, COLD)},
                  scope='routing, Linux Bash syntax and missing-data failure only; no detector/runtime CI claim')
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
