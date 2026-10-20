"""The site chrome stays pinned while every category scrolls, including player/error routes."""
import re

import pytest

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect


def hold_travel(page):
    """Hold native compositor animations while the JS clock drives preparation/recovery."""
    page.clock.install()
    page.clock.pause_at(page.evaluate('Date.now()'))
    page.evaluate('''() => {
        window.travelHeld = false;
        new MutationObserver(() => {
            if (window.travelHeld) return;
            const movement = document.getAnimations().find(a => a.id === 'section-travel');
            if (movement) {
                document.getAnimations().filter(a => a.id.startsWith('section-')).forEach(a => a.pause());
                window.travelHeld = true;
            }
        }).observe(document.body, {subtree:true,childList:true,attributes:true,attributeFilter:['data-section-motion']});
    }''')


def prepare_travel(page):
    for _ in range(100):
        page.clock.run_for(50)
        if page.locator('[data-train-doors]').get_attribute('data-phase') not in ('closing', 'covered'):
            break
        page.wait_for_timeout(20)  # image/font decode is real browser work, outside the mocked clock
    expect(page.locator('[data-train-doors]')).to_have_attribute('data-phase', 'travelling')
    assert page.locator('[data-transit-preparation-error]').count() == 0


def finish_travel(page):
    page.evaluate("document.getAnimations().filter(a => a.id.startsWith('section-')).forEach(a => a.finish())")
    page.clock.run_for(100)  # final destination must survive two painted frames before reveal
    expect(page.locator('[data-train-doors]')).to_have_attribute('data-phase', 'opening')


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
    hold_travel(page)
    rail = page.get_by_role('navigation', name='Линия: путь работы с записью')
    doors = page.locator('[data-train-doors]')
    rail.get_by_role('link', name='Прогоны', exact=True).click()
    expect(doors).to_have_attribute('data-phase', 'closing')
    expect(page).to_have_url(app.base + '/player')
    expect(page.locator('main')).to_have_attribute('inert', '')
    page.clock.run_for(270)
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
    prepare_travel(page)
    # During the slide, cached glass optics replace live backdrop passes; door motion is unchanged.
    expect(page.locator('[data-transit-frosted]')).to_have_count(1)
    assert glass.evaluate('el => getComputedStyle(el).backdropFilter') == 'none'
    assert page.locator('[data-app-shell]').get_attribute('data-travel-direction') == 'left'
    finish_travel(page)
    assert '20px' in glass.evaluate('el => getComputedStyle(el).backdropFilter')
    page.clock.run_for(330)
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
    hold_travel(page)
    page.get_by_role('navigation', name='Линия: путь работы с записью').get_by_role('link', name='Загрузка', exact=True).click()
    doors = page.locator('[data-train-doors]')
    page.clock.run_for(270)
    expect(doors).to_have_attribute('data-phase', 'covered')
    expect(page).to_have_url(app.base + '/upload')
    prepare_travel(page)
    assert page.locator('[data-transit-page="queue"] [data-motion-raster]').count() == 1
    page.evaluate("document.getAnimations().filter(a => a.id.startsWith('section-')).forEach(a => a.currentTime=200)")
    arriving = page.locator('[data-destination-snapshot]').bounding_box()
    assert arriving['x'] < 0, arriving
    outgoing = page.locator('[data-outgoing-snapshot]').evaluate('el => el.getBoundingClientRect().x')
    assert outgoing > 0, outgoing
    assert page.locator('[data-door-leaf]').first.evaluate('el => el.getBoundingClientRect().left') == 0
    # A delayed main-thread callback cannot cut the compositor's still-held journey short.
    page.clock.run_for(850)
    expect(doors).to_have_attribute('data-phase', 'travelling')
    finish_travel(page)
    page.clock.run_for(330)
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
    hold_travel(page)
    # Use an actual navigation link, including the system-branch destinations.
    page.get_by_role('navigation', name='Разделы').get_by_role('button', name='3 Система').click()
    page.get_by_role('menuitem', name='О системе', exact=False).click()
    page.clock.run_for(270)
    doors = page.locator('[data-train-doors]')
    expect(doors).to_have_attribute('data-phase', 'covered')
    expect(page).to_have_url(app.base + '/about')
    prepare_travel(page)
    expect(page.locator('[data-transit-page]')).to_have_count(6)
    stations = page.locator('[data-transit-page]').evaluate_all('els=>els.map(el=>el.dataset.transitPage)')
    assert stations == ['queue', 'runs', 'player', 'compare', 'live', 'presets']
    assert page.locator('[data-transit-page] canvas[role="img"]').count() == 0
    # Every moving surface, including both opacity-crossfade endpoints, is a bounded bitmap.
    expect(page.locator('[data-glass-raster]')).to_have_count(10)
    assert page.locator('[data-glass-raster]').evaluate_all('els=>els.every(c=>c.width<=640&&c.height<=400)')
    assert page.locator('[data-sharp-endpoint] [data-glass-raster]').evaluate_all('els=>els.every(c=>c.getContext("2d").getImageData(Math.floor(c.width/2),Math.floor(c.height/2),1,1).data[3]>250)')
    assert page.locator('[data-transit-preparation]').evaluate('el=>el.children.length') == 0
    # Data/DOM changes after departure cannot alter the frozen moving strip.
    before_strip = page.locator('[data-transit-frozen]').inner_html()
    page.locator('main').evaluate("el=>el.append(document.createTextNode('late destination update'))")
    page.clock.run_for(1600)
    expect(doors).to_have_attribute('data-phase', 'travelling')
    assert page.locator('[data-transit-frozen]').inner_html() == before_strip
    animations = page.evaluate("document.getAnimations().filter(a=>a.id.startsWith('section-')).map(a=>({id:a.id,start:a.startTime,properties:Object.keys(a.effect.getKeyframes()[0])}))")
    assert len(animations) == 3
    assert not any('filter' in a['properties'] for a in animations)
    finish_travel(page)
    page.clock.run_for(330)
    expect(doors).to_be_hidden()
    assert page.evaluate('history.length') == before + 1
    assert page.evaluate('JSON.stringify(localStorage)') == stored
    expect(page.locator('[data-transit-viewport]')).to_have_count(0)
    assert app.errors == []


def test_resize_finishes_travel_without_leaving_a_stale_strip(app):
    page = app.page
    app.goto('/runs')
    expect(page.get_by_role('heading', name='Прогоны', exact=True)).to_be_visible()
    hold_travel(page)
    page.get_by_role('navigation', name='Линия: путь работы с записью').get_by_role('link', name='Загрузка', exact=True).click()
    page.clock.run_for(270)
    prepare_travel(page)
    page.set_viewport_size({'width': 1280, 'height': 720})
    # Resize/ResizeObserver delivery uses the native browser clock. Wait for the
    # handler's inline width before driving the two virtual painted-frame checks.
    expect(page.locator('[data-destination-snapshot]')).to_have_attribute('style', re.compile(r'.*width: 1280px.*'))
    page.clock.run_for(100)
    expect(page.locator('[data-train-doors]')).to_have_attribute('data-phase', 'opening')
    page.clock.run_for(330)
    expect(page.locator('[data-train-doors]')).to_be_hidden()
    expect(page.locator('[data-transit-viewport]')).to_have_count(0)
    expect(page).to_have_url(app.base + '/upload')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert app.errors == []


def test_failed_raster_preparation_reveals_page_and_recovers_next_navigation(app):
    page = app.page
    app.goto('/runs')
    expect(page.get_by_role('heading', name='Прогоны', exact=True)).to_be_visible()
    page.evaluate('document.fonts.ready')
    page.evaluate('''() => {
        const fetch = window.fetch.bind(window);
        let failed = false;
        window.fetch = (input, init) => {
            if (!failed && /\\.woff2/.test(String(input))) {
                failed = true;
                return Promise.reject(new TypeError('injected one-time font failure'));
            }
            return fetch(input, init);
        };
    }''')
    hold_travel(page)
    rail = page.get_by_role('navigation', name='Линия: путь работы с записью')
    rail.get_by_role('link', name='Загрузка', exact=True).click()
    page.clock.run_for(270)
    for _ in range(80):
        page.clock.run_for(50)
        if page.locator('[data-transit-preparation-error]').count():
            break
        page.wait_for_timeout(20)
    expect(page.locator('[data-transit-preparation-error]')).to_have_count(1)
    expect(page.locator('[data-transit-frosted]')).to_have_count(0)
    assert '20px' in page.locator('[data-door-glass]').first.evaluate('el=>getComputedStyle(el).backdropFilter')
    # Failed bitmap decoding must still carry every frozen tab through to the destination.
    for _ in range(10):
        page.clock.run_for(50)
        if page.locator('[data-train-doors]').get_attribute('data-phase') == 'travelling':
            break
    expect(page.locator('[data-train-doors]')).to_have_attribute('data-phase', 'travelling')
    finish_travel(page)
    page.clock.run_for(330)
    expect(page.locator('[data-train-doors]')).to_be_hidden()
    expect(page).to_have_url(app.base + '/upload')
    # The failed embedded-font promise is evicted; the next journey can prepare normally.
    page.evaluate('window.travelHeld=false')
    rail.get_by_role('link', name='Очередь', exact=True).click()
    page.clock.run_for(270)
    prepare_travel(page)
    finish_travel(page)
    page.clock.run_for(330)
    expect(page.locator('[data-train-doors]')).to_be_hidden()
    expect(page).to_have_url(app.base + '/queue')
    assert app.errors == []


def test_hidden_player_suspends_only_its_renderer_during_frozen_travel(app):
    page = app.page
    app.goto('/queue')
    expect(page.get_by_role('heading', name='Очередь', exact=True)).to_be_visible()
    hold_travel(page)
    page.get_by_role('navigation', name='Линия: путь работы с записью').get_by_role('link', name='Плеер', exact=True).click()
    page.clock.run_for(270)
    prepare_travel(page)
    canvas = page.locator('main [data-train-backdrop] canvas')
    expect(canvas).to_have_attribute('data-navigation-paused', 'true')
    finish_travel(page)
    expect(canvas).to_have_attribute('data-navigation-paused', 'false')
    page.clock.run_for(330)
    expect(page.locator('[data-train-doors]')).to_be_hidden()
    expect(page.get_by_text('Прогонов пока нет', exact=True)).to_be_visible()
    assert app.errors == []


@pytest.mark.parametrize('source,target,label,expected', [
    ('/upload', '/player', 'Плеер', ['upload', 'queue', 'runs', 'player']),
    ('/player', '/upload', 'Загрузка', ['player', 'runs', 'queue', 'upload']),
    ('/queue', '/compare', 'Сравнение', ['queue', 'runs', 'player', 'compare']),
    ('/compare', '/queue', 'Очередь', ['compare', 'player', 'runs', 'queue']),
])
def test_every_visible_tab_passes_in_order_and_target_is_centered_before_open(app, source, target, label, expected):
    page = app.page
    app.goto(source)
    expect(page.locator('main')).to_be_visible()
    expect(page.locator('[data-page-fallback]')).to_have_count(0)
    hold_travel(page)
    page.get_by_role('navigation', name='Линия: путь работы с записью').get_by_role('link', name=label, exact=True).click()
    page.clock.run_for(270)
    prepare_travel(page)
    samples = page.evaluate('''() => {
        const animations=document.getAnimations().filter(a=>a.id.startsWith('section-'));
        const duration=animations.find(a=>a.id==='section-travel').effect.getTiming().duration;
        const stages=[...document.querySelector('[data-transit-frozen]').children];
        const passed=[];
        for(let i=0;i<=100;i++){
            animations.forEach(a=>a.currentTime=duration*i/100);
            const nearest=stages.reduce((a,b)=>Math.abs(a.getBoundingClientRect().x)<Math.abs(b.getBoundingClientRect().x)?a:b);
            const index=+nearest.dataset.journeyIndex;
            if(passed.at(-1)!==index)passed.push(index);
        }
        const target=stages.at(-1).getBoundingClientRect();
        const targetNav=stages.at(-1).dataset.snapshotPath;
        return {passed,keys:stages.map((s,i)=>s.dataset.transitPage|| (i===0?'origin':'target')),targetX:target.x,targetNav};
    }''')
    assert samples['passed'] == list(range(len(expected))), samples
    assert samples['keys'][1:-1] == expected[1:-1], samples
    assert abs(samples['targetX']) < .5, samples
    assert samples['targetNav'] == target, samples
    expect(page.locator('[data-train-doors]')).to_have_attribute('data-phase', 'travelling')
    finish_travel(page)
    page.clock.run_for(330)
    expect(page.locator('[data-train-doors]')).to_be_hidden()
    expect(page).to_have_url(app.base + target)
    assert app.errors == []


def test_native_dropdown_picker_is_themed_and_retains_keyboard_selection(app, backend):
    page = app.page
    preset = backend.api.post('/presets', {'name': 'Проверка списка', 'overrides': {}})
    app.goto('/upload')
    expect(page.get_by_role('heading', name='Загрузка', exact=True)).to_be_visible()
    select = page.get_by_role('combobox', name='Пресет', exact=True)
    expect(select).to_have_css('appearance', 'base-select')
    select.focus()
    page.keyboard.press('Space')
    expect(page.get_by_role('option', name='Проверка списка', exact=True)).to_be_visible()
    picker = select.evaluate('el=>({radius:getComputedStyle(el,"::picker(select)").borderRadius,font:getComputedStyle(el,"::picker(select)").fontFamily})')
    assert picker['radius'] == '16px' and 'Raleway' in picker['font'], picker
    page.keyboard.press('ArrowDown')
    page.keyboard.press('Enter')
    expect(select).to_have_value(preset['id'])
    assert app.errors == []
