"""Persist a fresh unhooked R3 replay for an independent pair comparison."""
import json
from pathlib import Path

import run_checks


HERE = Path(__file__).resolve().parent


def main():
    traced = json.loads((HERE / 'r3.json').read_text())
    plain = []
    for case in traced:
        current = run_checks.r3_sequence(case['kind'], case['carried'], case['enabled'], case['speed_known'], traced=False)
        for a, b in zip(current['rows'], case['rows'], strict=True):
            assert {k: v for k, v in a.items() if k != 'qualification_calls'} == {
                k: v for k, v in b.items() if k != 'qualification_calls'}
        plain.append(current)
    run_checks.save(HERE / 'r3_plain_recheck.json', plain)
    print('Fresh unhooked R3 rows equal captured traced outputs:', sum(len(c['rows']) for c in plain))


if __name__ == '__main__':
    main()
