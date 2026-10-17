#!/usr/bin/env bash
set -euo pipefail
test -d /tmp
out=/tmp/webapp-ci-b0c9c17-results
mkdir -p "$out"
npm --prefix webapp/frontend test -- --maxWorkers=2 2>&1 | tee "$out/frontend.txt"
npm --prefix webapp/frontend run build 2>&1 | tee "$out/build.txt"
for attempt in 1 2; do
    WEBAPP_PROBE_CPU=4 WEBAPP_PROBE_LOG="$out/targeted-$attempt-events.jsonl" \
        python3 -m pytest -vv -rs -p webapp_probe \
        webapp/e2e/test_analysis.py::test_player_link_waits_for_rendered_destination \
        webapp/e2e/test_analysis.py::test_run_page_timeline_chart_events_and_downloads \
        webapp/e2e/test_analysis.py::test_run_page_preset_rename_and_delete \
        webapp/e2e/test_system.py::test_live_simulation_transport \
        webapp/e2e/test_data.py::test_queue_cancel_retry_log_and_clear \
        --junitxml="$out/targeted-$attempt.xml" 2>&1 | tee "$out/targeted-$attempt.txt"
done
python3 -m pytest -vv -rs \
    webapp/e2e --junitxml="$out/full.xml" 2>&1 | tee "$out/full.txt"
python3 -m ruff check --no-cache webapp/e2e/test_analysis.py /tmp/webapp_probe.py
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
for path in Path('/tmp/webapp-ci-b0c9c17-results').glob('*.xml'):
    cases = ET.parse(path).getroot().findall('.//testcase')
    assert cases and not any(c.find(tag) is not None for c in cases for tag in ('error', 'failure', 'skipped'))
    print(path.name, len(cases), 'passed; zero skips/errors/failures')
PY
