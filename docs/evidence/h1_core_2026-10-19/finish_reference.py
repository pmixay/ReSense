"""Finish only the interrupted X3 reference case; validate all 40 raw completions.

The timeout left 39 complete workers and one partial worker. Keep those original
files immutable and rerun the incomplete case in a fresh directory.
"""
from datetime import datetime, timezone
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import robustness_battery as rb  # noqa: E402
from run_checks import DATA, HERE, REF, WORK, sources  # noqa: E402

before = sources(REF)
assert before == rb.read_json(HERE / 'gate-a-reference-execution.json')['source_sha256']
report = dict(schema=rb.SCHEMA, created=datetime.now(timezone.utc).isoformat(), protocol=rb.protocol(),
              runtime=dict(platform=platform.platform(), python=sys.version, executable=sys.executable,
                           jobs=2, threads=1, resource_adapter='None'),
              harness_commit=rb.git(ROOT, 'rev-parse', 'HEAD'), sources={}, entries={}, errors=[],
              assembly='39 original completed workers + fresh rerun of the interrupted worker')
for bag, count in rb.BAGS.items():
    report['sources'][bag] = rb.source_info(DATA / 'decoded' / bag, count)
report['labels'] = {b: rb.sha256(REF / f'labels/{b}.json') for b in ('doubleT_obstacle', 'cloud_with_fake_obj')}
for bag in rb.BAGS:
    meta, _ = rb.cache_meta(DATA / 'decoded' / bag, rb.BAGS[bag])
    labels = rb.read_json(REF / f'labels/{bag}.json') if bag in report['labels'] else None
    for variant in rb.VARIANTS:
        folder = WORK / 'x3-b2-reference.raw' / bag / variant
        raw = folder / 'probe.jsonl'
        complete = folder / 'probe.complete.json'
        if not complete.exists():
            original_plan = rb.read_json(folder / 'job.json')
            fresh = WORK / 'x3-reference-recovered' / bag / variant
            fresh.mkdir(parents=True, exist_ok=False)
            plan = dict(original_plan, prefix=str(fresh / 'probe'))
            rb.write_new(fresh / 'job.json', plan)
            command = [sys.executable, str(ROOT / 'scripts/robustness_battery.py'), '--worker', str(fresh / 'job.json')]
            with (fresh / 'process.log').open('x') as log:
                result = subprocess.run(command, cwd=REF, env=rb.environment(REF, None),
                                        stdout=log, stderr=subprocess.STDOUT)
            assert result.returncode == 0
            raw, complete = fresh / 'probe.jsonl', fresh / 'probe.complete.json'
        receipt = rb.read_json(complete)
        assert receipt['identity']['commit'] == '9621024fcced776f157bd68471a4995c38f7dfd7'
        assert report.setdefault('evaluation', receipt['identity']) == receipt['identity']
        rows = rb.checked_rows(raw, meta, 2 if variant == 'hz5' else 1)
        report['entries'][f'{bag}/{variant}'] = dict(raw_path=str(raw), raw_sha256=rb.sha256(raw),
                                                    metrics=rb.summarize(rows, labels), wall_s=receipt['wall_s'])
assert before == sources(REF)
report.update(status='MEASURED', wall_s=sum(e['wall_s'] for e in report['entries'].values()))
rb.validated_entries(report, DATA / 'decoded', REF)
rb.write_new(WORK / 'x3-final-reference.json', report)
rb.write_new(HERE / 'x3-final-reference.json', report)
print('Reference complete:', len(report['entries']), 'cases', sum(e['metrics']['frames'] for e in report['entries'].values()), 'rows')
