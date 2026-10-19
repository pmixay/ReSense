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
    assert '20px' in glass.evaluate('el => getComputedStyle(el).backdropFilter')
    expect(page.locator('[data-outgoing-snapshot="ready"]')).to_have_count(1)
    if width == 1440:
        copied_pixel = page.locator('[data-outgoing-snapshot] canvas').first.evaluate('c=>Array.from(c.getContext("2d").getImageData(Math.floor(c.width/2),Math.floor(c.height/3),1,1).data)')
        assert copied_pixel[3] == 255 and max(copied_pixel[:3]) > 40, copied_pixel
    page.wait_for_function('!document.querySelector("[data-page-fallback]") && !document.querySelector("[data-transit-loading]")')
    page.clock.run_for(75)
    expect(doors).to_have_attribute('data-phase', 'travelling')
    assert page.locator('[data-app-shell]').get_attribute('data-travel-direction') == 'left'
    page.clock.run_for(670)
    expect(doors).to_have_attribute('data-phase', 'opening')
    page.clock.run_for(460)
    expect(doors).to_be_hidden()
    expect(page.locator('[data-transit-viewport]')).to_have_count(0)
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
    assert page.locator('main').evaluate('el => getComputedStyle(el).transform') == 'none'
    assert page.locator('[data-transit-viewport]').count() == 0
    expect(page).to_have_url(app.base + '/upload')
    expect(page.locator('[data-page-fallback]')).to_be_hidden(timeout=30000)
    expect(doors).to_be_hidden()


def test_section_pages_follow_direction_with_continuous_blurred_intermediates(app):
    page = app.page
    app.goto('/runs')
    expect(page.get_by_role('heading', name='Прогоны', exact=True)).to_be_visible()
    page.clock.install()
    page.clock.pause_at(page.evaluate('Date.now()'))
    page.get_by_role('navigation', name='Линия: путь работы с записью').get_by_role('link', name='Загрузка', exact=True).click()
    doors = page.locator('[data-train-doors]')
    page.clock.run_for(360)
    expect(doors).to_have_attribute('data-phase', 'covered')
    expect(page).to_have_url(app.base + '/upload')
    expect(page.locator('[data-transit-page="queue"] h1')).to_have_text('Очередь')
    page.wait_for_function('!document.querySelector("[data-page-fallback]") && !document.querySelector("[data-transit-loading]")')
    page.clock.run_for(75)
    expect(doors).to_have_attribute('data-phase', 'travelling')
    page.evaluate("document.getAnimations().forEach(a => {if (a.animationName?.includes('section-')) {a.pause();a.currentTime=200;}})")
    arriving = page.locator('main').evaluate('el => ({x:new DOMMatrixReadOnly(getComputedStyle(el).transform).m41,blur:parseFloat(getComputedStyle(el).filter.slice(5))})')
    assert arriving['x'] < 0 and arriving['blur'] > 20, arriving
    outgoing = page.locator('[data-outgoing-snapshot]').evaluate('el => el.getBoundingClientRect().x')
    assert outgoing > 0, outgoing
    assert page.locator('[data-door-leaf]').first.evaluate('el => el.getBoundingClientRect().left') == 0
    page.clock.run_for(820)
    expect(doors).to_have_attribute('data-phase', 'opening')
    page.clock.run_for(460)
    expect(doors).to_be_hidden()
    assert page.locator('main').evaluate('el => getComputedStyle(el).transform === "none" && getComputedStyle(el).filter === "none"')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert app.errors == []


def test_long_journey_contains_every_station_without_visiting_its_url(app):
    page = app.page
    app.goto('/upload')
    expect(page.get_by_role('heading', name='Загрузка', exact=True)).to_be_visible()
    before = page.evaluate('history.length')
    stored = page.evaluate('JSON.stringify(localStorage)')
    page.clock.install()
    page.clock.pause_at(page.evaluate('Date.now()'))
    # Use an actual navigation link, including the system-branch destinations.
    page.get_by_role('navigation', name='Разделы').get_by_role('button', name='3 Система').click()
    page.get_by_role('menuitem', name='О системе', exact=False).click()
    page.clock.run_for(360)
    doors = page.locator('[data-train-doors]')
    expect(doors).to_have_attribute('data-phase', 'covered')
    expect(page).to_have_url(app.base + '/about')
    expect(page.locator('[data-transit-page]')).to_have_count(6)
    page.wait_for_function('!document.querySelector("[data-transit-loading]") && !document.querySelector("[data-page-fallback]")')
    stations = page.locator('[data-transit-page]').evaluate_all('els=>els.map(el=>el.dataset.transitPage)')
    assert stations == ['queue', 'runs', 'player', 'compare', 'live', 'presets']
    assert page.locator('[data-transit-page] canvas[role="img"]').count() == 0
    page.clock.run_for(75)
    expect(doors).to_have_attribute('data-phase', 'travelling')
    page.clock.run_for(1570)
    expect(doors).to_have_attribute('data-phase', 'opening')
    page.clock.run_for(460)
    expect(doors).to_be_hidden()
    assert page.evaluate('history.length') == before + 1
    assert page.evaluate('JSON.stringify(localStorage)') == stored
    expect(page.locator('[data-transit-viewport]')).to_have_count(0)
    assert app.errors == []
