"""X1 adapter: same fixed health-latency input in plain/traced runs; dynamic hit bar."""
import sys
import linecache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import range_attrib as ra  # noqa: E402
from resense.detector import Detector  # noqa: E402

original = Detector.process


def process(self, *args, **kwargs):
    # Tracing changes physical runtime. Feed the same diagnostic input before
    # health evaluates it, rather than deleting changed health outputs afterwards.
    if self._previous_latency_ms is not None:
        self._previous_latency_ms = 42.0
    return original(self, *args, **kwargs)


class Trace(ra.TrackerTrace):
    def _local(self, frame, event, arg):
        result = super()._local(frame, event, arg)
        if (event == 'line' and self.names.get(frame.f_code) == 'update'
                and linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip().startswith('t.reported = (q or')):
            loc = frame.f_locals
            t, c = loc['t'], loc['self'].cfg
            self._rec(t)['report_assignment'] = dict(
                line=frame.f_lineno, q=bool(loc['q']), reported_before=bool(t.reported),
                misses=t.misses, hold_misses=c.hold_misses, hold=t.hold,
                explained_blocked=bool(loc['explained_blocked']))
        if (event == 'return' and self.names.get(frame.f_code) == 'qualifies'
                and frame.f_back is not None and frame.f_back.f_code.co_name == 'update'):
            q = self._rec(frame.f_locals['t']).get('qualifies')
            if q is not None:
                q['need_hits'] = frame.f_locals.get('need_hits', q['need_hits'])
        return result


Detector.process = process
ra.TrackerTrace = Trace
sys.exit(ra.main())
