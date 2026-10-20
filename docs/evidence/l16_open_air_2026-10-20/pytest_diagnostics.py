"""Post-failure diagnostics only: never hook or alter a node/detector call."""
import json

import pytest


def plain(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    return plain(vars(value))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != 'call' or not report.failed:
        return
    for entry in call.excinfo.traceback:
        node = entry.frame.f_locals.get('node')
        if node is not None and 'published' in vars(node):
            health = node.published.get('/resense/health', [])
            if health:
                report.sections.append(('post-failure published health', json.dumps(plain(health[-1]), indent=2)))
                break
