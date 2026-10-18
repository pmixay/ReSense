"""The site chrome stays pinned while every category scrolls, including player/error routes."""
import pytest

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect


@pytest.mark.parametrize("width,height", [(1920, 1080), (1280, 720), (820, 1180), (390, 844)])
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
