#!/usr/bin/env bash
set -euo pipefail
out=/tmp/webapp-ci-b0c9c17-results
test -d "$out"
npm --prefix webapp/frontend test -- --maxWorkers=2 2>&1 | tee "$out/frontend.txt"
npm --prefix webapp/frontend run build 2>&1 | tee "$out/build.txt"
for attempt in 1 2; do
    python3 -m pytest -vv -rs webapp/e2e/test_system.py::test_live_simulation_transport \
        --junitxml="$out/live-$attempt.xml" 2>&1 | tee "$out/live-$attempt.txt"
done
python3 -m pytest -vv -rs webapp/e2e --junitxml="$out/full.xml" 2>&1 | tee "$out/full.txt"
python3 -m ruff check --no-cache webapp/e2e/test_analysis.py /tmp/webapp_probe.py
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
for path in Path('/tmp/webapp-ci-b0c9c17-results').glob('*.xml'):
    cases = ET.parse(path).getroot().findall('.//testcase')
    assert cases and not any(c.find(tag) is not None for c in cases for tag in ('error', 'failure', 'skipped'))
    print(path.name, len(cases), 'passed; zero skips/errors/failures')
PY
