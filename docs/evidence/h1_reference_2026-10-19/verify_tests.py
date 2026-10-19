"""Final E full-suite run after X3 has ended."""
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from run_checks import ROOT, HERE, WORK, archived


def main():
    deadline = time.monotonic() + 3600
    while not (HERE / 'x3-e-candidate-execution.json').exists():
        if time.monotonic() > deadline:
            raise TimeoutError('X3 not finished')
        time.sleep(5)
    before = archived.sources(ROOT)
    command = [sys.executable, '-m', 'pytest', '-q', '--junitxml=' + str(WORK / 'full-tests-e.xml')]
    with (WORK / 'full-tests-e.log').open('x') as stream:
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, RESENSE_REQUIRE_SYNTHETIC='1'),
                                stdout=stream, stderr=subprocess.STDOUT)
    xml = ET.parse(WORK / 'full-tests-e.xml').getroot()
    report = dict(command=command, returncode=result.returncode, all_green=result.returncode == 0,
        skipped=sum(int(s.attrib.get('skipped', 0)) for s in xml.iter('testsuite')),
        failures=[dict(classname=c.attrib['classname'], name=c.attrib['name']) for c in xml.iter('testcase')
                  if c.find('failure') is not None or c.find('error') is not None],
        source_sha256=before, source_unchanged=archived.sources(ROOT) == before)
    assert report['source_unchanged'] and report['skipped'] == 0
    with (HERE / 'tests-e.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    print(report['returncode'], report['failures'], flush=True)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
