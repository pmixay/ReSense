"""The site chrome stays pinned while every category scrolls, including player/error routes."""
import pytest

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect


@pytest.mark.parametrize("width,height", [(1920, 1080), (1280, 720), (1366, 768), (1440, 900)])
def test_site_navigation_stays_pinned(app, width, height):
    page = app.page
    page.set_viewport_size({"width": width, "height": height})
    for route in ("/", "/upload", "/queue", "/runs", "/player", "/player/unknown", "/compare", "/live", "/presets", "/about"):
        app.goto(route)
        rail = page.get_by_role("navigation", name="Линия: путь работы с записью")
        expect(rail).to_be_visible()
        # Font loading can change the wrapped chrome's height on narrow screens.
        page.evaluate("document.fonts.ready")
        chrome = rail.locator("..")
        before = chrome.bounding_box()
        page.locator("main").evaluate("el => el.scrollTo(0, el.scrollHeight)")
        after = chrome.bounding_box()
        assert before and after and abs(before["y"] - after["y"]) < 1
        assert after["y"] == 0 and after["height"] < height
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.evaluate('document.fonts.check("16px Raleway", "Загрузка Player")')
        # The rail remains interactive after scrolling, rather than being covered by the page.
        rail.get_by_role("link", name="Загрузка", exact=True).click()
        expect(page).to_have_url(app.base + "/upload")
        expect(page.locator("main")).to_have_js_property("scrollTop", 0)


@pytest.mark.parametrize('width,height', [(1280, 720), (1366, 768), (1440, 900), (1920, 1080)])
def test_train_doors_cover_navigation_before_revealing_destination(app, width, height):
    page = app.page
    page.set_viewport_size({'width': width, 'height': height})
    app.goto('/player')
    page.evaluate('document.fonts.ready')
    page.clock.install()
    page.clock.pause_at(page.evaluate('Date.now()'))
    rail = page.get_by_role('navigation', name='Линия: путь работы с записью')
    doors = page.locator('[data-train-doors]')
    rail.get_by_role('link', name='Прогоны', exact=True).click()
    expect(doors).to_have_attribute('data-phase', 'closing')
    expect(page).to_have_url(app.base + '/player')
    expect(page.locator('main')).to_have_attribute('inert', '')
    page.clock.run_for(360)
    expect(page).to_have_url(app.base + '/runs')
    expect(doors).to_have_attribute('data-phase', 'covered')
    leaves = page.locator('[data-door-leaf]').evaluate_all('els => els.map(el => el.getBoundingClientRect().toJSON())')
    assert leaves[0]['left'] <= 0 and leaves[0]['right'] >= width / 2
    assert leaves[1]['left'] <= width / 2 and leaves[1]['right'] >= width
    assert all(leaf['top'] == 0 and leaf['bottom'] == height for leaf in leaves)
    # The user's screen is the frame: no stationary header, jambs or sill may remain.
    assert doors.locator(':scope > :not([data-door-leaf])').count() == 0
    glass = page.locator('[data-door-glass]').first
    assert '38px' in glass.evaluate('el => getComputedStyle(el).backdropFilter')
    page.clock.run_for(100)
    expect(doors).to_have_attribute('data-phase', 'opening')
    page.clock.run_for(460)
    expect(doors).to_be_hidden()
    expect(page.locator('main')).not_to_have_attribute('inert', '')
    assert page.locator('main').evaluate('el => document.activeElement === el')
    # History navigation gets the same close/swap/open sequence.
    page.evaluate('history.back()')
    expect(doors).to_have_attribute('data-phase', 'closing')
    # Let lazy Player/GPU initialization use real time rather than freezing its effects.
    page.clock.resume()
    expect(page).to_have_url(app.base + '/player')
    expect(doors).to_be_hidden(timeout=30000)


def test_train_doors_reduced_motion_uses_fade(app):
    page = app.page
    page.emulate_media(reduced_motion='reduce')
    app.goto('/runs')
    page.get_by_role('navigation', name='Линия: путь работы с записью').get_by_role('link', name='Загрузка', exact=True).click()
    doors = page.locator('[data-train-doors]')
    assert page.locator('[data-door-leaf]').first.evaluate('el => getComputedStyle(el).display') == 'none'
    expect(page).to_have_url(app.base + '/upload')
    expect(page.locator('[data-page-fallback]')).to_be_hidden(timeout=30000)
    expect(doors).to_be_hidden()
