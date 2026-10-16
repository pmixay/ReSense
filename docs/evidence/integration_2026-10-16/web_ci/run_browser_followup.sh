#!/usr/bin/env bash
# After the unchanged backend checks: validate acknowledged progress and pause/reload.
set -euo pipefail
out="${WEB_CI_OUT:-/tmp/web-ci-final}"
test -d "$out"
if [[ "${WEB_CI_SKIP_FRONTEND:-0}" != 1 ]]; then
    npm --prefix webapp/frontend test -- --maxWorkers=2 2>&1 | tee "$out/frontend.txt"
    npm --prefix webapp/frontend run build 2>&1 | tee "$out/build.txt"
fi
for attempt in 1 2 3; do
    WEB_CI_DELAY_RELOAD_S=8 WEB_CI_EVENTS="$out/upload-$attempt-events.jsonl" \
        python3 -m pytest -vv -rs -p web_ci_events --junitxml="$out/upload-$attempt.xml" \
        webapp/e2e/test_upload_resume.py 2>&1 | tee "$out/upload-$attempt.txt"
done
python3 -m pytest -vv -rs --junitxml="$out/browser.xml" webapp/e2e 2>&1 | tee "$out/browser.txt"
python3 - "$out" <<'PY'
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
for path in sorted(Path(sys.argv[1]).glob("*.xml")):
    cases = ET.parse(path).getroot().findall(".//testcase")
    bad = [c for c in cases if any(c.find(tag) is not None for tag in ("skipped", "failure", "error"))]
    print(f"{path.name}: {len(cases)} tests, {len(bad)} skipped/failed/errored")
    assert cases and not bad
PY
