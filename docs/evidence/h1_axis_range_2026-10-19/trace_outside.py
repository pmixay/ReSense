"""Executed return branches for every former 0.6m false core, with controls."""
import json
import linecache
import sys

import numpy as np

from run_checks import HERE, archived, ROOT
from trace_ranges import fingerprint

sys.path.insert(0, str(ROOT / 'tests'))
from test_column_collision_core import matched, physical_column, stop_history  # noqa: E402


def main():
    source = archived.sources(ROOT)
    cases = [(37., -1.29, -.6), (37., 1.29, .6), (67., -1.29, -.6),
             (67., 1.29, .6), (109., -1.29, -.6)]
    cases = [(distance, lateral, error, rails) for rails in [False, True] for distance, lateral, error in cases]
    cases.append((67., .68, 0., True))
    report = dict(source_sha256=source, cases=[])
    for distance, lateral, error, rails in cases:
        xyz, ring, labels = physical_column(distance=distance, lateral=lateral, top=4.12, rails=rails)
        plain = matched(xyz, ring, labels, axis_error=error)
        calls = []

        def profile(frame, event, result):
            if event != 'return' or frame.f_code.co_name != '_collision_core':
                return
            state = frame.f_locals
            fi = state['frame_idx'][state['b'].idx]
            fi = fi[fi >= 0]
            if not fi.size or np.mean(labels[fi] == 1) <= .5:
                return
            rays = state['rays']
            calls.append(dict(return_value=bool(result), return_line=frame.f_lineno,
                executed_statement=linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip(),
                interval=state.get('interval'), absolute_anchor=rays._core_anchor,
                anchor_checked=rays._core_anchor_checked,
                final_k_count=int(state['k'].size) if 'k' in state else None))

        sys.setprofile(profile)
        try:
            traced = matched(xyz, ring, labels, axis_error=error)
        finally:
            sys.setprofile(None)
        assert fingerprint(plain) == fingerprint(traced)
        assert calls
        actual_stop = any(any(stop_history(c)) for c in traced)
        if abs(lateral) > 1:
            assert not actual_stop and not any(c['return_value'] for c in calls)
        else:
            assert actual_stop and any(c['return_value'] for c in calls)
        report['cases'].append(dict(distance=distance, lateral=lateral, error=error, rails=rails,
            full_cluster_fields_plain_traced_equal=True, executed_returns=calls, matched_STOP=actual_stop))
    assert source == archived.sources(ROOT)
    report['source_unchanged'] = True
    with (HERE / 'outside-trace-d.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report['cases'], indent=2))


if __name__ == '__main__':
    main()
