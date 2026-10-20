#!/usr/bin/env python3
"""Check D1 source identities and changed-document links, without detector evaluation."""
import argparse
import csv
import hashlib
import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CHANGED = ['README.md', 'docs/CAPTAIN.md', 'docs/README.md', 'docs/ROLE_2_PLAN.md',
           'docs/PLAN.md', 'docs/REQUIREMENTS_MAP.md',
           'web/P2_STATUS.md', 'web/P2_REVIEW.md', 'web/DEMO_HANDOFF.md', 'webapp/README.md',
           'gitbook/getting-started/read-the-output.md', 'gitbook/getting-started/run-on-a-bag.md',
           'gitbook/visualisation/web-prototype.md', 'docs/evidence/p2_d1_2026-10-19/README.md']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    def load(path):
        return json.loads((ROOT / path).read_text())

    def git(*cmd):
        return subprocess.check_output(['git', *cmd], cwd=ROOT)
    manifest = load('docs/evidence/detector_freeze_2026-10-18_b4_merged.json')
    for path, expected in manifest['files'].items():
        assert sha((ROOT / path).read_bytes()) == expected, path
        assert sha(git('show', f"{manifest['measured_commit']}:{path}")) == expected, path
    # Positive control: an altered source byte must fail the same digest comparison.
    first = next(iter(manifest['files']))
    assert sha((ROOT / first).read_bytes() + b' altered control') != manifest['files'][first]
    base = 'docs/evidence/b4_merge_reseal_2026-10-18/'
    acceptance, gate, x3 = (load(base + name) for name in ['acceptance.json', 'gate_frame_review.json', 'x3_frame_review.json'])
    ordinary = sum(row['frames'] for row in gate['ordinary'].values())
    set_f = sum(row['rows'] for row in gate['set_F'])
    assert ordinary == acceptance['ordinary_gate_rows'] == gate['ordinary_rows']
    assert set_f == acceptance['set_F_rows'] == gate['set_F_rows']
    assert len(x3['cases']) == acceptance['x3_cases'] == x3['case_count']
    assert sum(row['frames'] for row in x3['cases'].values()) == acceptance['x3_rows'] == x3['rows_compared']
    archives = []
    for item in acceptance['archives'].values():
        path = ROOT / base / item['path']
        assert sha(path.read_bytes()) == item['sha256'], path
        archives.append(item['path'])
    assert acceptance['P4_final_acceptance'] == 'PENDING' and acceptance['release_authorized'] is False
    export_root = ROOT / 'docs/evidence/p4_eval_1.1.0_2026-10-16/export'
    register = json.loads((export_root / 'case_register.json').read_text())['rows']
    numbers = json.loads((export_root / 'numbers.json').read_text())['rows']
    with (export_root / 'case_register.csv').open() as stream:
        assert len(list(csv.DictReader(stream))) == len(register)
    sources = {}
    direct = 0
    for row in numbers:
        if row['derived']:
            continue
        name = row['source']
        if name not in sources:
            data = (ROOT / name).read_bytes()
            sources[name] = (sha(data), json.loads(data))
        digest, value = sources[name]
        assert digest == row['source_sha256'], name
        for key in row['pointer'].strip('/').split('/'):
            key = key.replace('~1', '/').replace('~0', '~')
            value = value[int(key)] if isinstance(value, list) else value[key]
        assert value == row['value'], (row['case_id'], row['metric'])
        direct += 1
    score = load('docs/evidence/judgement_2026-10-13/scores.json')
    assert sum(row['score'] for row in score['criteria'].values()) == score['total']['score'] == 66
    media = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_type,codec_name,nb_frames,avg_frame_rate,width,height', '-of', 'json',
        'docs/video/resense_overview.mp4'], cwd=ROOT))
    video = next(s for s in media['streams'] if s.get('codec_type') == 'video')
    assert float(media['format']['duration']) == 180
    assert Fraction(video['nb_frames']) / Fraction(video['avg_frame_rate']) == 180
    missing = []
    checked = 0
    for name in CHANGED:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)', (ROOT / name).read_text()):
            parsed = urlsplit(target.strip('<>'))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            checked += 1
            if not (ROOT / name).parent.joinpath(unquote(parsed.path)).exists():
                missing.append({'document': name, 'target': target})
    stale = []
    pattern = re.compile(r'0 tags|No tag or release exists|Пока релиза нет|пока нет тега|0 тегов, 0 релизов|СВОБОДНО|2:50')
    assert pattern.search('positive control: No tag or release exists')
    for name in CHANGED:
        for number, line in enumerate((ROOT / name).read_text().splitlines(), 1):
            if pattern.search(line):
                stale.append({'file': name, 'line': number, 'text': line,
                              'review': 'dated history, registered task description or explicitly historical wording; not a current release/UI assertion'})
    version = subprocess.check_output(['python3', 'scripts/release_meta.py', 'version'], cwd=ROOT, text=True).strip()
    assert version == '1.2.0'
    result = {'scope': 'stored-receipt/integrity reconciliation; no detector rerun or external approval',
              'starting_commit': '6bcd2e3', 'package_version': version,
              'local_tags': git('tag', '--list').decode().splitlines(), 'verified_frozen_files': len(manifest['files']),
              'measured_commit': manifest['measured_commit'], 'source_sha256': manifest['source_sha256'],
              'positive_control': True, 'ordinary_rows_recounted': ordinary, 'set_f_rows_recounted': set_f,
              'x3_cases_recounted': len(x3['cases']), 'x3_rows_recounted': x3['rows_compared'],
              'verified_archive_hashes': archives, 'score': score['total'], 'video_duration_s': 180,
              'current_p4_export': {'cases': len(register), 'numbers': len(numbers), 'direct_numbers_independently_checked': direct,
                                    'derived_numbers': len(numbers) - direct,
                                    'p4_check_stdout': subprocess.check_output(['python3', str(export_root / 'build_export.py'), '--check'], cwd=ROOT, text=True).strip()},
              'video_codec': video['codec_name'], 'relative_links_checked': checked, 'missing_relative_links': missing,
              'reviewed_stale_claim_search': stale,
              'document_sha256': {name: sha((ROOT / name).read_bytes()) for name in CHANGED}}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if missing:
        raise SystemExit('Changed-document relative links have missing targets')


if __name__ == '__main__':
    main()
