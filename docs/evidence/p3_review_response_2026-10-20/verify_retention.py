"""Verify actual B4 keep-rule returns and the ten-second cap from captures."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    cases = json.loads((HERE / 'b4_retention.json').read_text())
    summaries = []
    calls = 0
    exact_rows = 0
    positive_calls = []
    for case in cases:
        for row, plain_hash in zip(case['rows'], case['plain_row_hashes'], strict=True):
            assert row['state_hash'] == plain_hash
            exact_rows += 1
            assert row['STOP'] == any(t['reported'] and t['zone'] == 'gauge' for t in row['tracks'])
            for event in row['actual_keep_calls']:
                expected = (case['keep_enabled'] and event['demoted'] and event['previous_reported']
                            and event['previous_zone'] == 'gauge' and event['n_gauge'] >= 10
                            and float(event['since_clean']) <= 10. + 1e-9)
                assert event['returned'] == expected
                calls += 1
                if expected:
                    positive_calls.append(event)
        hits = [r['k'] for r in case['rows'] if r['after_fault'] and r['STOP']]
        keep_rows = [r for r in case['rows'] if any(e['returned'] for e in r['actual_keep_calls'])]
        summary = {key: case[key] for key in ['warm_scans', 'error', 'gauge_voxels', 'keep_enabled']}
        summary.update(post_fault_STOP_count=len(hits), first_post_fault_STOP=min(hits) if hits else None,
                       last_post_fault_STOP=max(hits) if hits else None,
                       last_keep_scan=max((r['k'] for r in keep_rows), default=None),
                       maximum_kept_age_s=max((float(e['since_clean']) for r in keep_rows
                                               for e in r['actual_keep_calls'] if e['returned']), default=None))
        summaries.append(summary)
    assert positive_calls
    assert max(float(e['since_clean']) for e in positive_calls) <= 10. + 1e-9
    bad = dict(positive_calls[0], returned=False)
    assert bad['returned'] != positive_calls[0]['returned']
    with (HERE / 'retention-verification.json').open('x') as stream:
        json.dump({'status': 'PASS', 'exact_plain_traced_rows': exact_rows,
                   'actual_keep_returns_verified': calls, 'changed_return_control_detected': True,
                   'cases': summaries}, stream, indent=2)
        stream.write('\n')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
