#!/usr/bin/env bash
set -euo pipefail
test -d /tmp
out=/tmp/upload-followup02-results
mkdir -p "$out"
python3 - <<'PY' | tee "$out/identity.txt"
import importlib.metadata as m
from pathlib import Path
import resense
from resense import _native
assert Path(resense.__file__).resolve().parent == Path.cwd() / 'resense'
assert _native.enabled()
print('resense:', resense.__file__, 'version:', resense.__version__)
print('native:', _native.__file__, _native.status())
print({p: m.version(p) for p in ('playwright', 'pytest', 'open3d', 'numpy')})
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    print('chromium:', b.version)
    b.close()
PY
python3 -m pytest -vv -s -rs -p upload_boundary_probe webapp/e2e/test_upload_resume.py \
    --junitxml="$out/boundary.xml" 2>&1 | tee "$out/boundary.txt"
for attempt in 1 2; do
    python3 -m pytest -vv -rs webapp/e2e/test_upload_resume.py \
        --junitxml="$out/focused-$attempt.xml" 2>&1 | tee "$out/focused-$attempt.txt"
done
python3 -m pytest -vv -rs webapp/e2e --junitxml="$out/browser.xml" 2>&1 | tee "$out/browser.txt"
python3 -m ruff check --no-cache webapp/e2e/test_upload_resume.py /tmp/upload-followup02-probe
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
for path in sorted(Path('/tmp/upload-followup02-results').glob('*.xml')):
    cases = ET.parse(path).getroot().findall('.//testcase')
    assert cases and not any(c.find(tag) is not None for c in cases for tag in ('skipped', 'failure', 'error'))
    print(path.name, len(cases), 'passed; zero skips/errors/failures')
for path in Path('/tmp/upload-followup02-results').glob('*.txt'):
    text = path.read_text()
    assert 'CancelledError' not in text and 'Task was destroyed' not in text, path
PY
