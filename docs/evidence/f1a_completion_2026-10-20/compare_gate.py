"""Compare the two F1a gate reports on the gated ride and recording metrics."""
import json
from pathlib import Path

WORK = Path('/tmp/opencode/f1a-completion-work')
HERE = Path('/tmp/opencode/f1a-completion-checkout/docs/evidence/f1a_completion_2026-10-20')


def load(path):
    return json.loads(Path(path).read_text())


def ride(report):
    r = report.get('ride', {})
    return {k: r.get(k) for k in ('available', 'frames', 'alarm_frames', 'alarm_events', 'stop_episodes',
                                  'advisory_frames', 'first_alarm_frame')}


def main():
    cand = load(HERE / 'gate-c-candidate.json')
    ref = load(HERE / 'gate-c-reference.json')
    print('candidate gate passed', cand['gate']['passed'], 'allow', cand['gate']['allow'],
          'worse', cand['gate']['worse_gated'], 'missing', cand['gate']['missing_gated'])
    print('reference gate passed', ref['gate']['passed'])
    print('candidate commit', cand['code']['commit'], 'dirty', cand['code']['uncommitted_detector_changes'])
    print('reference commit', ref['code']['commit'])
    print('\nride candidate ', ride(cand))
    print('ride reference ', ride(ref))
    print('\nrecorded 8c2bf51 (P4 acceptance): alarm events 18, STOP episodes 24, alarm frames 102')
    print('recorded 99dab01 (current main):    alarm events 23, STOP episodes 26, alarm frames 111')
    print('\nrecordings:')
    for name in sorted(cand['recordings']):
        a, b = cand['recordings'][name], ref['recordings'][name]
        keys = ('frames', 'alarm_frames', 'alarm_events', 'stop_episodes', 'advisory_frames')
        line = '  %-38s cand %s' % (name, {k: a.get(k) for k in keys})
        if {k: a.get(k) for k in keys} != {k: b.get(k) for k in keys}:
            line += '\n  %-38s ref  %s' % ('', {k: b.get(k) for k in keys})
        print(line)
    print('\nset O objects:')
    for label, obj in sorted(cand['set_O']['objects'].items()):
        other = ref['set_O']['objects'].get(label, {})
        keys = ('stop_frames', 'first_stop_m', 'advisory_frames')
        diff = {k: (obj.get(k), other.get(k)) for k in keys if obj.get(k) != other.get(k)}
        print('  %-22s %s%s' % (label, {k: obj.get(k) for k in keys}, '' if not diff else '  DIFF ' + str(diff)))
    print('\nset O background', cand['set_O'].get('background'), 'ref', ref['set_O'].get('background'))
    print('\nset F:', {k: cand['set_F_straight'].get(k) for k in ('available',)},
          'summary', cand['set_F_straight'].get('summary'))


if __name__ == '__main__':
    main()
