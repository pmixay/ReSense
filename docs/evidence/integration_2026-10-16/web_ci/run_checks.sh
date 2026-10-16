#!/usr/bin/env bash
# Run from the repository root in the retained Linux tools container (3 GiB, 4 CPUs).
set -euo pipefail
out="${WEB_CI_OUT:-/tmp/web-ci-final}"
test -d "$(dirname "$out")"
mkdir -p "$out"
python3 -c 'import sys, importlib.metadata as m; print(sys.version); print({p: m.version(p) for p in ("playwright", "pytest", "fastapi", "starlette", "uvicorn", "open3d", "numpy", "websockets")})' | tee "$out/versions.txt"
node --version | tee -a "$out/versions.txt"

python3 -m pytest -q -rs --junitxml="$out/backend.xml" webapp/backend/tests 2>&1 | tee "$out/backend.txt"
npm --prefix webapp/frontend test -- --maxWorkers=2 2>&1 | tee "$out/frontend.txt"
npm --prefix webapp/frontend run build 2>&1 | tee "$out/build.txt"

for attempt in 1 2; do
    WEB_CI_SEED=1 WEB_CI_DELAY_RELOAD_S=8 WEB_CI_EVENTS="$out/targeted-$attempt-events.jsonl" \
        python3 -m pytest -vv -rs -p web_ci_events --junitxml="$out/targeted-$attempt.xml" \
        webapp/e2e/test_data.py::test_queue_reload_with_a_pending_nonblocking_resource \
        webapp/e2e/test_data.py::test_server_folder_preset_and_options \
        webapp/e2e/test_data.py::test_queue_cancel_retry_log_and_clear \
        webapp/e2e/test_upload_resume.py 2>&1 | tee "$out/targeted-$attempt.txt"
done

# All original 45 cases plus the load-readiness regression, without injected delays / seeding.
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
