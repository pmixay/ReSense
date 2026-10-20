"""Retain a final full-suite run after X3, avoiding overlapping timing loads."""
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from run_checks import ROOT, HERE, WORK, archived


def main():
    deadline = time.monotonic() + 3600
    while not (HERE / 'x3-d2-candidate-execution.json').exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('X3 has not completed; no final timing run started')
        time.sleep(5)
    source = archived.sources(ROOT)
    env = dict(os.environ, RESENSE_REQUIRE_SYNTHETIC='1')
    command = [sys.executable, '-m', 'pytest', '-q', '--junitxml=' + str(WORK / 'full-tests-d-final.xml')]
    with (WORK / 'full-tests-d-final.log').open('x') as stream:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
    xml = ET.parse(WORK / 'full-tests-d-final.xml').getroot()
    failures = [dict(classname=case.attrib['classname'], name=case.attrib['name'])
                for case in xml.iter('testcase') if case.find('failure') is not None or case.find('error') is not None]
    report = dict(command=command, returncode=result.returncode, full_suite_all_green=result.returncode == 0,
        failures=failures, skipped=sum(int(s.attrib.get('skipped', 0)) for s in xml.iter('testsuite')),
        source_unchanged=source == archived.sources(ROOT), source_sha256=source)
    assert report['source_unchanged'] and report['skipped'] == 0
    with (HERE / 'tests-final-d.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2), flush=True)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
