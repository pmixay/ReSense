"""Population expansion must not disguise real per-sequence or per-frame losses."""
from copy import deepcopy

import pytest

from scripts.set_f_comparison import compare_cohorts, comparison_lines, sequence_metrics


def sequence(file, distance, hit):
    return dict(kind='cable', file0=file, d0=220., lateral=0., refl=42., placement_mode='legacy',
        first=distance if hit else None, rows=[dict(frame=f'{file}_{i}', d=distance-i, n=8,
            gt={'size': [0.03, 0.03, 2.8]}, hit=hit, fp_dets=[]) for i in range(5)])


def population():
    before = [sequence('A', 19., True), sequence('B', 49.5, True),
              sequence('C', 16.6, False), sequence('D', 16.4, False)]
    after = [sequence('A', 19., True), sequence('B', 49.5, True),
             sequence('C', 16.6, True), sequence('D', 16.4, True)]
    return before, after


def compare(before, after):
    return compare_cohorts(sequence_metrics(before)['cable'], sequence_metrics(after)['cable'])


def test_more_successes_lower_conditional_median_without_a_sequence_regression():
    before, after = population()
    report = compare(before, after)
    assert report['status'] == 'success_population_expanded'
    assert (report['baseline_conditional_median_m'], report['current_conditional_median_m']) == (34.2, 17.8)
    assert (report['baseline_sustained_sequences'], report['current_sustained_sequences']) == (2, 4)
    assert report['baseline_success_cohort_current_median_m'] == 34.2
    assert report['lost_hit_frames'] == report['regressed_sequences'] == 0
    assert report['added_hit_frames'] == 10
    assert 'successful sequences 2 -> 4/4' in comparison_lines({'cable': report})[0]


def test_higher_conditional_median_cannot_hide_a_lost_success():
    before, _ = population()
    after = deepcopy(before)
    after[0] = sequence('A', 19., False)
    report = compare(before, after)
    assert report['current_conditional_median_m'] == 49.5  # scalar improves by dropping A
    assert report['status'] == 'sequence_regression'
    assert report['lost_sustained_sequences'] == 1
    assert report['lost_hit_frames'] == 5
    assert report['baseline_success_cohort_current_median_m'] is None


def test_one_lost_hit_is_found_even_when_added_hits_compensate_the_total():
    before, after = population()
    after[0]['rows'][2]['hit'] = False
    report = compare(before, after)
    assert report['status'] == 'sequence_regression'
    assert report['lost_hit_frames'] == 1 and report['added_hit_frames'] == 10
    assert report['pairs'][0]['lost_hit_frames'] == ['A_2']


@pytest.mark.parametrize('change', ['missing', 'visibility', 'placement', 'skipped'])
def test_unlike_or_missing_input_is_not_claimed_as_a_pass(change):
    before, after = population()
    if change == 'missing':
        after.pop()
    elif change == 'visibility':
        after[0]['rows'][0]['n'] = 0
    elif change == 'placement':
        after[0]['rows'][0]['gt']['size'][0] += .1
    else:
        after[0]['skipped'] = 'no reference'
    assert compare(before, after)['status'] == 'not_comparable'


def test_legacy_summary_is_explicitly_unavailable():
    assert compare_cohorts(None, [])['status'] == 'not_comparable'


def test_duplicate_sequences_or_frames_fail_instead_of_overwriting():
    before, _ = population()
    with pytest.raises(ValueError, match='duplicate Set F sequence'):
        sequence_metrics(before + before[:1])
    before[0]['rows'][1]['frame'] = before[0]['rows'][0]['frame']
    with pytest.raises(ValueError, match='duplicate frame'):
        sequence_metrics(before)


def test_equal_distance_rows_are_evaluated_together_and_need_five_visible_rows():
    seq = sequence('A', 19., True)
    for row in seq['rows']:
        row['d'] = 19.
    seq['rows'][-1]['hit'] = False
    assert sequence_metrics([seq])['cable'][0]['sustained_m'] is None  # 4/5, not the first 4/4
    seq['rows'][-1]['hit'] = True
    assert sequence_metrics([seq])['cable'][0]['sustained_m'] == 19.
    seq['rows'].pop()
    assert sequence_metrics([seq])['cable'][0]['sustained_m'] is None
