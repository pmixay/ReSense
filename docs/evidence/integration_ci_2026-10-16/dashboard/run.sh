#!/usr/bin/env bash
set -euo pipefail
test -d /tmp
out=/tmp/dashboard-ci-b0c9c17-results
mkdir -p "$out"
python3 - <<'PY' | tee "$out/identity.txt"
import importlib.metadata as m
from pathlib import Path
import resense
from resense import _native
print('resense:', resense.__file__)
print('native:', _native.__file__, _native.status())
assert Path(resense.__file__).resolve().parent == Path.cwd() / 'resense'
assert _native.enabled()
print({p: m.version(p) for p in ('playwright', 'pytest', 'open3d', 'numpy')})
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    print('chromium:', browser.version)
    browser.close()
PY
for attempt in 1 2 3; do
    python3 -m pytest -vv -rs web/demo/test_web.py -k 'captures_fast_dom or replays_jsonl_in_chromium' \
        --junitxml="$out/targeted-$attempt.xml" 2>&1 | tee "$out/targeted-$attempt.txt"
done
python3 -m pytest -vv -rs web/demo --junitxml="$out/full.xml" 2>&1 | tee "$out/full.txt"
python3 web/demo/make_demo_run.py --out "$out/demo_run.jsonl" 2>&1 | tee "$out/demo.txt"
python3 web/demo/check_dashboard.py --jsonl "$out/demo_run.jsonl" --screenshot "$out/dashboard.png" 2>&1 | tee "$out/smoke.txt"
python3 -m ruff check --no-cache web/demo/check_dashboard.py web/demo/test_web.py 2>&1 | tee "$out/lint.txt"
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
for path in Path('/tmp/dashboard-ci-b0c9c17-results').glob('*.xml'):
    cases = ET.parse(path).getroot().findall('.//testcase')
    assert cases and not any(c.find(tag) is not None for c in cases for tag in ('error', 'failure', 'skipped'))
    print(path.name, len(cases), 'passed; zero skips/errors/failures')
PY
