"""CI must exercise browser/synthetic checks rather than silently skipping them."""
import os

import pytest


@pytest.fixture
def page():
    from test_web import _browser_available, _launch
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        yield page
        browser.close()
        assert not errors, errors


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    if os.environ.get('RESENSE_REQUIRE_WEB') != '1':
        return
    reporter = session.config.pluginmanager.get_plugin('terminalreporter')
    if not session.testscollected or (reporter and reporter.stats.get('skipped')):
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
