#!/usr/bin/env python3
"""Check the browser result validator against archived ROS status captures.

Uses Playwright/Chromium and the repository's actual shared validator. This verifies
format compatibility, not detector quality or live timestamp validity.
"""
import argparse
import gzip
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from check_dashboard import INDEX, launch

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = [ROOT / 'docs/evidence' / name for name in (
    'docker_2026-09-23', 'p1_p2_completion_2026-09-26', 'results/quality_freshness_2026-09-26')]


def check(paths, chromium=None):
    report = {'files': 0, 'records': 0, 'rejected': []}
    with sync_playwright() as p:
        browser = launch(p, chromium)
        page = browser.new_page()
        page.goto(Path(INDEX).as_uri())
        for directory in paths:
            for path in sorted(directory.rglob('*.jsonl.gz')):
                rows, line_numbers = [], []
                with gzip.open(path, 'rt') as stream:
                    for number, line in enumerate(stream, 1):
                        try:
                            row = json.loads(line)
                        except ValueError:
                            continue
                        if isinstance(row, dict) and type(row.get('obstacle')) is bool:
                            rows.append(row)
                            line_numbers.append(number)
                report['files'] += 1
                report['records'] += len(rows)
                rejected = page.evaluate('rows => rows.flatMap((r,i) => resenseFormat.result(r) ? [] : [i])', rows)
                report['rejected'].extend({'file': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                                           'line': line_numbers[i]} for i in rejected)
        browser.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', type=Path)
    parser.add_argument('--chromium')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    report = check(args.paths or DEFAULTS, args.chromium)
    text = json.dumps(report, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text, end='')
    return int(not report['records'] or bool(report['rejected']))


if __name__ == '__main__':
    raise SystemExit(main())
