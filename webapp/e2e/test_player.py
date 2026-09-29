"""End-to-end flows of the 3D player (/player, /player/<run>) in a real browser (WebGL through
SwiftShader) against a real backend (fixtures in conftest.py). The first test sees a fresh data dir;
the others share runs seeded once through the API: two short demos with stored clouds, a results-only
.jsonl (schematic mode) and a .jsonl with an input fault (FAULT frames).

  python -m pytest -q webapp/e2e/test_player.py     (~2.5 min with the build; the whole suite: python -m pytest -q webapp/e2e)
"""
from __future__ import annotations

import json
import re
from decimal import ROUND_HALF_UP, Decimal

import pytest
from e2e_helpers import Held, api_route, real_errors

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect

FRAME_RE = re.compile(r"^кадр \d+ / \d+$")


def fixed(x: float, digits: int) -> str:
    """A number as the UI prints it (lib/format.ts: toFixed, comma decimals)."""
    return str(Decimal(x).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)).replace(".", ",")


def upload_jsonl(api, name: str, body: bytes) -> str:
    """A results-only recording from .jsonl bytes, processed; returns the run id."""
    return api.processed(api.upload_jsonl(name, body)["id"])["run_id"]


@pytest.fixture(autouse=True)
def _patient_expect():
    """The 3D view renders with software WebGL here: a busy machine stalls the page for seconds."""
    expect.set_options(timeout=15_000)
    yield
    expect.set_options(timeout=5_000)


# ------------------------------------------------------------------------------ page helpers


def slider(page):
    return page.get_by_role("slider", name="Кадр прогона")


def playhead(page) -> int:
    return int(slider(page).get_attribute("aria-valuenow"))


def expect_pos(page, pos: int) -> None:
    expect(slider(page)).to_have_attribute("aria-valuenow", str(pos))


def url_pos(page) -> int | None:
    m = re.search(r"[?&]pos=(\d+)", page.url)
    return int(m.group(1)) if m else None


def wait_cab(page) -> None:
    """Wait until the cab is up: the scrubber and the 3D view (SwiftShader compiles its shaders on the
    main thread: seconds on a busy machine)."""
    expect(slider(page)).to_be_visible(timeout=30_000)
    expect(page.get_by_role("img", name="3D-вид из кабины")).to_be_visible(timeout=30_000)


def open_player(app, route: str) -> None:
    """Open a player URL and wait until the cab shows a frame."""
    app.goto(route)
    wait_cab(app.page)
    expect(app.page.get_by_text(FRAME_RE)).to_be_visible()


def beacon(page):
    return page.get_by_role("status", name=re.compile(r"^Решение"))


def speed_pill(page, label: str):
    return page.get_by_role("group", name="Скорость").get_by_role("button", name=label, exact=True)


def camera(page, label: str):
    return page.get_by_role("radiogroup", name="Камера").get_by_role("radio", name=label)


# ---------------------------------------------------------------------------------------- seed


@pytest.fixture(scope="module")
def seeded(backend) -> dict:
    """approach (STOP from the first frames, clouds), crossing (GO → CAUTION → STOP → GO, clouds),
    a results-only copy of approach (schematic) and a copy of crossing with an input fault."""
    api = backend.api
    recs = {sc: api.demo(sc, 6) for sc in ("approach", "crossing")}
    jobs = {k: api.job(r["id"]) for k, r in recs.items()}
    ids = {}
    for k, j in jobs.items():
        done = api.wait_job(j["id"])
        assert done["status"] == "done", done
        ids[k] = done["run_id"]
    ids["jsonl"] = upload_jsonl(api, "tunnel_log", api.get(f"/runs/{ids['approach']}/download/results.jsonl").encode())
    lines = []
    for i, line in enumerate(api.get(f"/runs/{ids['crossing']}/download/results.jsonl").splitlines()):
        d = json.loads(line)
        if 10 <= i <= 20:  # the sensor input fails: health error, nothing verified ahead
            d["health"] = {**(d.get("health") or {}), "level": "error", "decision_level": "error"}
            d.update(obstacle=False, detections=[], clear_distance=0.0)
        lines.append(json.dumps(d))
    ids["fault"] = upload_jsonl(api, "fault_log", "\n".join(lines).encode())
    runs = {r["id"]: r for r in api.get("/runs")}
    details = {k: api.get(f"/runs/{v}") for k, v in ids.items()}
    return {"ids": ids, "runs": runs, "details": details}


# ---------------------------------------------------------------------------------------- 1


def test_empty_picker_and_unknown_run(app):
    page = app.page
    app.goto("/player")
    expect(page.get_by_text("Прогонов пока нет")).to_be_visible()
    expect(page.get_by_role("link", name="Сделать демо-прогон")).to_have_attribute("href", "/upload?source=demo")
    expect(page.get_by_role("link", name="Загрузить запись")).to_have_attribute("href", "/upload")
    expect(page.get_by_role("region", name="Клавиши плеера")).to_contain_text("пуск / пауза")

    # a run that does not exist: the backend's Russian message, no retry (404), ways out in the tray
    app.goto("/player/nosuchrun")
    alert = page.get_by_role("alert")
    expect(alert).to_contain_text("Прогон не открылся")
    expect(alert).to_contain_text("Прогон не найден")
    expect(alert.get_by_role("button", name="Повторить")).to_have_count(0)
    page.get_by_role("link", name="Выбрать прогон").click()
    expect(page).to_have_url(re.compile(r"/player$"))
    expect(page.get_by_text("Прогонов пока нет")).to_be_visible()
    assert real_errors(app.errors, allowed=(404,)) == []


# ---------------------------------------------------------------------------------------- 2


def test_picker_lists_runs_with_clouds_first(app, seeded):
    page, ids = app.page, seeded["ids"]
    app.goto("/player")
    expect(page.get_by_role("heading", name="Выберите прогон")).to_be_visible()
    cards = page.get_by_role("link", name=re.compile(r"^Открыть в плеере: "))
    expect(cards).to_have_count(len(seeded["runs"]))
    names = [n.removeprefix("Открыть в плеере: ") for n in (c.get_attribute("aria-label") for c in cards.all())]
    with_clouds = [n for n in names if n.startswith("demo_")]
    assert names[: len(with_clouds)] == with_clouds, names  # runs with clouds first
    expect(page.get_by_text("2 прогона в 3D")).to_be_visible()
    expect(cards.filter(has_text="tunnel_log")).to_contain_text("без облака")
    cards.filter(has_text="demo_crossing").click()
    expect(page).to_have_url(re.compile(rf"/player/{ids['crossing']}(\?|$)"))
    expect(beacon(page)).to_be_visible()
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 3


def test_autoplay_keyboard_and_url(app, seeded):
    page, rid = app.page, seeded["ids"]["crossing"]
    n = seeded["details"]["crossing"]["summary"]["n_frames"]
    app.goto("/runs")  # the player is opened from the runs list: Esc / «Назад» return there
    hist = page.evaluate("history.length")
    page.get_by_role("link", name="Открыть в плеере: demo_crossing").click()
    wait_cab(page)
    # without ?pos the drive starts at once; the URL follows (replaced, no new history entries)
    expect(page.get_by_role("button", name="Пауза (пробел)")).to_be_visible()
    expect(page).to_have_url(re.compile(rf"/player/{rid}\?pos=[1-9]\d*"), timeout=15_000)
    assert page.evaluate("history.length") == hist + 1
    page.keyboard.press("Space")
    expect(page.get_by_role("button", name="Воспроизвести (пробел)")).to_be_visible()
    p0 = playhead(page)
    page.keyboard.press("ArrowRight")
    expect_pos(page, p0 + 1)
    page.keyboard.press("Shift+ArrowRight")
    expect_pos(page, min(n - 1, p0 + 11))
    page.keyboard.press("Shift+ArrowLeft")
    page.keyboard.press("ArrowLeft")
    expect_pos(page, p0)
    expect(page).to_have_url(re.compile(rf"\?pos={p0}$"))
    expect(page.get_by_text(FRAME_RE)).to_have_text(f"кадр {p0} / {n}")

    # cameras: 2 / 3 / 1 and the switch; the URL keeps the camera
    page.keyboard.press("2")
    expect(camera(page, "Сверху")).to_have_attribute("aria-checked", "true")
    expect(page.get_by_text("сверху · план пути")).to_be_visible()
    page.keyboard.press("3")
    expect(camera(page, "Сзади")).to_have_attribute("aria-checked", "true")
    expect(page).to_have_url(re.compile(r"cam=chase"))
    camera(page, "Кабина").click()
    expect(page.get_by_text("кабина · вперёд")).to_be_visible()
    expect(page).not_to_have_url(re.compile(r"cam="))

    # speed: + / − keys and the pills; the URL keeps a non-default speed
    page.keyboard.press("Equal")
    expect(speed_pill(page, "2×")).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Minus")
    page.keyboard.press("Minus")
    expect(speed_pill(page, "0,5×")).to_have_attribute("aria-pressed", "true")
    expect(page).to_have_url(re.compile(r"speed=0\.5"))
    speed_pill(page, "10×").click()
    expect(page).to_have_url(re.compile(r"speed=10"))
    speed_pill(page, "1×").click()

    # the play button keeps focus: Space toggles once (not twice)
    page.get_by_role("button", name="Воспроизвести (пробел)").click()
    expect(page.get_by_role("button", name="Пауза (пробел)")).to_be_focused()
    page.keyboard.press("Space")
    expect(page.get_by_role("button", name="Воспроизвести (пробел)")).to_be_visible()
    assert page.evaluate("history.length") == hist + 1

    # Esc first closes the focused button's tooltip, then leaves the player the way the jury came
    expect(page.get_by_role("tooltip")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("tooltip")).to_have_count(0)
    expect(page).to_have_url(re.compile(rf"/player/{rid}"))
    page.keyboard.press("Escape")
    expect(page).to_have_url(re.compile(r"/runs$"))
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 4


def test_events_scrubber_loop_and_end(app, seeded):
    page, rid, det = app.page, seeded["ids"]["crossing"], seeded["details"]["crossing"]
    n = det["summary"]["n_frames"]
    starts = sorted({e["first_frame"] for e in det["events"]})
    assert starts, det["events"]
    open_player(app, f"/player/{rid}?pos=0")
    expect(page.get_by_role("button", name="Воспроизвести (пробел)")).to_be_visible()
    expect(page.get_by_role("button", name="Кадр назад (←)")).to_be_disabled()
    expect(page.get_by_role("button", name="Предыдущее событие ([)")).to_be_disabled()
    # ] / [ and the buttons walk the run's events (their pins sit on the scrubber)
    page.keyboard.press("BracketRight")
    expect_pos(page, starts[0])
    expect(page.get_by_title(f"кадр {starts[0]}")).to_be_visible()
    if len(starts) > 1:
        page.get_by_role("button", name="Следующее событие (])").click()
        expect_pos(page, starts[1])
        page.keyboard.press("BracketLeft")
        expect_pos(page, starts[0])
    expect(page.get_by_role("button", name="Предыдущее событие ([)")).to_be_disabled()
    stop = next(e for e in det["events"] if e["decision"] == "STOP")
    app.goto(f"/player/{rid}?pos={min(stop['first_frame'] + 2, stop['last_frame'])}")
    expect(beacon(page)).to_have_accessible_name("Решение: СТОП")
    tile = page.get_by_role("region", name="До препятствия")
    expect(tile).to_contain_text(re.compile(r"\d+,\d\s?м"))
    expect(page.get_by_role("region", name="Решение")).to_contain_text("в габарите 2,1 × 3,0 м")

    # a click on the strip seeks there; the keyboard works on the focused slider too
    box = slider(page).bounding_box()
    page.mouse.click(box["x"] + box["width"] * 0.75, box["y"] + box["height"] / 2)
    p = playhead(page)
    assert abs(p - round(0.75 * n)) <= 2, p
    slider(page).press("Home")
    expect_pos(page, 0)
    slider(page).press("End")
    expect_pos(page, n - 1)

    # at the end without a loop playback stops; with the loop it wraps around to the start
    loop = page.get_by_role("button", name="Повтор по кругу")
    expect(loop).to_have_attribute("aria-pressed", "false")
    loop.click()
    expect(loop).to_have_attribute("aria-pressed", "true")
    speed_pill(page, "5×").click()
    page.keyboard.press("Space")
    page.wait_for_function("() => +document.querySelector('[role=slider]').getAttribute('aria-valuenow') < 20", timeout=20_000)
    page.keyboard.press("Space")
    loop.click()
    expect(loop).to_have_attribute("aria-pressed", "false")
    slider(page).press("End")
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("Space")
    expect(page.get_by_role("button", name="Воспроизвести (пробел)")).to_be_visible(timeout=20_000)
    expect_pos(page, n - 1)
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 5


def test_deep_link_shows_real_values(app, backend, seeded):
    page, rid = app.page, seeded["ids"]["approach"]
    n = seeded["details"]["approach"]["summary"]["n_frames"]
    pos = n // 2
    fr = backend.api.get(f"/runs/{rid}/frames?from={pos}&count=1")["frames"][0]
    assert fr["decision"] == "STOP" and fr["detections"], fr["decision"]
    open_player(app, f"/player/{rid}?pos={pos}&speed=2&cam=top")
    expect_pos(page, pos)
    expect(page.get_by_role("button", name="Воспроизвести (пробел)")).to_be_visible()  # a deep link opens paused
    expect(speed_pill(page, "2×")).to_have_attribute("aria-pressed", "true")
    expect(camera(page, "Сверху")).to_have_attribute("aria-checked", "true")
    expect(beacon(page)).to_have_accessible_name("Решение: СТОП")
    expect(page.get_by_role("region", name="До препятствия")).to_contain_text(fixed(fr["nearest_distance"], 1))
    expect(page.get_by_role("region", name="Решение")).to_contain_text(f"кадр {fr['frame']}")
    expect(page.get_by_text(re.compile(r"^облако [\d\u2009\u00a0]+ точ"))).to_be_visible()
    # the HUD label over the box carries the detection's distance
    label = re.escape(fixed(fr["detections"][0]["distance"], 1))
    expect(page.get_by_text(re.compile(rf"^{label}\s?м$")).first).to_be_visible()
    lat = fr["timing_ms"]["total"]
    expect(page.get_by_role("region", name="Задержка и частота")).to_contain_text(fixed(lat, 0 if lat >= 10 else 1))
    # the tooltip of a tile opens on hover, inside the window
    page.get_by_role("region", name="До препятствия").get_by_role("button").hover()
    tip = page.get_by_role("tooltip")
    expect(tip).to_contain_text("в этом кадре")
    b = tip.bounding_box()
    assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= 1600 and b["y"] + b["height"] <= 1000, b

    # out-of-range and junk parameters are clamped / ignored
    open_player(app, f"/player/{rid}?pos=99999&speed=abc&cam=nope")
    expect_pos(page, n - 1)
    expect(speed_pill(page, "1×")).to_have_attribute("aria-pressed", "true")
    expect(camera(page, "Кабина")).to_have_attribute("aria-checked", "true")
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 6


def test_paused_steps_bring_their_clouds(app, backend, seeded):
    page, rid = app.page, seeded["ids"]["approach"]
    n = seeded["details"]["approach"]["summary"]["n_frames"]
    stored = set(backend.api.get(f"/runs/{rid}/clouds")["frames"])
    pos = n - 5
    assert {pos, pos - 10, pos - 11} <= stored, sorted(stored)  # a short demo keeps every cloud
    open_player(app, f"/player/{rid}?pos={pos}")
    expect(page.get_by_text("загрузка облака")).to_have_count(0)
    # paused, a step or a jump shows the points of the new frame (its cloud is fetched), not the old ones
    with page.expect_response(re.compile(rf"/api/runs/{rid}/clouds/{pos - 10}$")) as r:
        page.keyboard.press("Shift+ArrowLeft")
    assert r.value.ok
    expect_pos(page, pos - 10)
    with page.expect_response(re.compile(rf"/api/runs/{rid}/clouds/{pos - 11}$")):
        page.get_by_role("button", name="Кадр назад (←)").click()
    expect_pos(page, pos - 11)
    expect(page.get_by_text("загрузка облака")).to_have_count(0)
    # the focused strip keeps the player's keys: ← / → step one frame, Shift ten
    slider(page).focus()
    page.keyboard.press("Shift+ArrowLeft")
    expect_pos(page, pos - 21)
    page.keyboard.press("ArrowRight")
    expect_pos(page, pos - 20)
    expect(page.get_by_role("button", name="Воспроизвести (пробел)")).to_be_visible()
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 7


def test_run_menu_switch_and_browser_back(app, seeded):
    page, ids = app.page, seeded["ids"]
    open_player(app, f"/player/{ids['approach']}?pos=7")
    # the jury in fullscreen stays there when it opens another run
    page.keyboard.press("f")
    page.wait_for_function("() => !!document.fullscreenElement")
    page.get_by_role("button", name="Другой прогон").click()
    menu = page.get_by_role("navigation", name="Прогоны")
    expect(menu.get_by_role("button", name=re.compile("demo_approach"))).to_have_attribute("aria-current", "page")
    menu.get_by_role("button", name=re.compile("demo_crossing")).click()
    expect(page).to_have_url(re.compile(rf"/player/{ids['crossing']}"))
    # the new run plays at once; «back» returns to the old run where it was left
    expect(page.get_by_role("button", name="Пауза (пробел)")).to_be_visible()
    assert page.evaluate("!!document.fullscreenElement")
    page.get_by_role("button", name="Выйти из полноэкранного режима (F)").click()
    page.wait_for_function("() => !document.fullscreenElement")
    expect(page).to_have_url(re.compile(rf"/player/{ids['crossing']}\?pos=[1-9]"), timeout=15_000)
    page.go_back()
    expect(page).to_have_url(re.compile(rf"/player/{ids['approach']}\?pos=7$"))
    expect_pos(page, 7)
    page.wait_for_timeout(1500)  # the old run's URL writer is gone: nothing rewrites this entry
    expect(page).to_have_url(re.compile(rf"/player/{ids['approach']}\?pos=7$"))
    page.go_forward()
    expect(page).to_have_url(re.compile(rf"/player/{ids['crossing']}"))
    # the menu closes on Escape without leaving the player; its link opens the picker
    page.get_by_role("button", name="Другой прогон").click()
    expect(page.get_by_role("navigation", name="Прогоны")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("navigation", name="Прогоны")).to_have_count(0)
    expect(page).to_have_url(re.compile(rf"/player/{ids['crossing']}"))
    page.get_by_role("button", name="Другой прогон").click()
    page.get_by_role("link", name="Все прогоны").click()
    expect(page).to_have_url(re.compile(r"/player$"))
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 8


def test_schematic_and_fault_runs(app, seeded):
    page, ids = app.page, seeded["ids"]
    open_player(app, f"/player/{ids['jsonl']}?pos=30")
    expect(page.get_by_text("без облака точек")).to_be_visible()
    expect(beacon(page)).to_have_accessible_name("Решение: СТОП")
    expect(page.get_by_role("img", name="3D-вид из кабины")).to_be_visible()  # envelope, track and boxes still drawn

    open_player(app, f"/player/{ids['fault']}?pos=15")
    expect(beacon(page)).to_have_accessible_name("Решение: ОШИБКА")
    expect(page.get_by_role("region", name="Путь не проверен")).to_contain_text("не проверено")
    expect(page.get_by_role("region", name="Решение")).to_contain_text("сбой датчика")
    expect(page.get_by_title("кадр 10")).to_be_visible()  # the FAULT event's pin
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 9


def test_loading_and_backend_errors(app, seeded):
    page, rid, base = app.page, seeded["ids"]["approach"], app.base
    # loading: the run detail is held back → the spinner in the glass
    held = Held(page, api_route(base, rf"/runs/{rid}$"))
    app.goto(f"/player/{rid}?pos=5")
    expect(page.get_by_role("status", name="Загрузка прогона")).to_be_visible()
    page.wait_for_timeout(300)
    expect(page.get_by_role("status", name="Загрузка прогона")).to_be_visible()  # still held
    held.release()
    expect(slider(page)).to_be_visible()

    # frames fail (5xx with a Russian detail) → the banner with that detail; «Повторить» recovers
    frames_re = api_route(base, rf"/runs/{rid}/frames\?.*")
    page.route(frames_re, lambda route: route.fulfill(status=503, content_type="application/json", body=json.dumps({"detail": "Результаты прогона недоступны"})))
    app.goto(f"/player/{rid}?pos=12")
    alert = page.get_by_role("alert").filter(has_text="Кадры не загрузились")
    expect(alert).to_contain_text("Результаты прогона недоступны")
    expect(page.get_by_text("загрузка кадров")).to_have_count(0)
    page.unroute(frames_re)
    alert.get_by_role("button", name="Повторить").click()
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(page.get_by_text(FRAME_RE)).to_have_text(re.compile(r"^кадр 12 / "))

    # a cloud fails → the HUD says so with the backend's message (the frame itself is still shown)
    cloud_re = api_route(base, rf"/runs/{rid}/clouds/\d+$")
    page.route(cloud_re, lambda route: route.fulfill(status=500, content_type="application/json", body=json.dumps({"detail": "Облако повреждено"})))
    app.goto(f"/player/{rid}?pos=20")
    expect(page.get_by_role("status").filter(has_text="Облако повреждено")).to_be_visible()
    expect(beacon(page)).to_be_visible()
    page.unroute(cloud_re)

    # the cloud list fails → the message and a retry that loads the clouds
    index_re = api_route(base, rf"/runs/{rid}/clouds$")
    page.route(index_re, lambda route: route.fulfill(status=500, content_type="application/json", body=json.dumps({"detail": "Список облаков недоступен"})))
    app.goto(f"/player/{rid}?pos=20")
    chip = page.get_by_role("status").filter(has_text="Список облаков недоступен")
    expect(chip).to_be_visible()
    page.unroute(index_re)
    chip.get_by_role("button", name="Загрузить облако снова").click()
    expect(page.get_by_text("Список облаков недоступен")).to_have_count(0)

    # the runs list of the picker fails → the banner, «Повторить» recovers
    runs_re = api_route(base, r"/runs$")
    page.route(runs_re, lambda route: route.fulfill(status=500, content_type="application/json", body=json.dumps({"detail": "База недоступна"})))
    app.goto("/player")
    expect(page.get_by_role("alert")).to_contain_text("База недоступна")
    page.unroute(runs_re)
    page.get_by_role("button", name="Повторить").click()
    expect(page.get_by_role("heading", name="Выберите прогон")).to_be_visible()
    assert real_errors(app.errors, allowed=(500, 503)) == []


# ---------------------------------------------------------------------------------------- 10


def test_lost_3d_view_keeps_the_console(app, seeded):
    page, rid = app.page, seeded["ids"]["approach"]
    open_player(app, f"/player/{rid}?pos=10")
    # the GPU drops the context: a message instead of a black glass; the console still plays
    page.evaluate(
        "() => document.querySelector('canvas[aria-label=\"3D-вид из кабины\"]').getContext('webgl2')"
        ".getExtension('WEBGL_lose_context').loseContext()"
    )
    alert = page.get_by_role("alert").filter(has_text="3D-вид недоступен")
    expect(alert).to_contain_text("Видеокарта сбросила 3D-вид")
    expect(page.get_by_role("img", name="3D-вид из кабины")).to_have_count(0)
    page.keyboard.press("Space")
    page.wait_for_function("() => +document.querySelector('[role=slider]').getAttribute('aria-valuenow') > 12", timeout=20_000)
    page.keyboard.press("Space")
    # «Повторить» builds the view again
    alert.get_by_role("button", name="Повторить").click()
    expect(page.get_by_role("img", name="3D-вид из кабины")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 11


def test_fullscreen_orbit_and_back(app, seeded):
    page, rid = app.page, seeded["ids"]["approach"]
    open_player(app, f"/player/{rid}?pos=25")
    # F: the real Fullscreen API on the cab
    page.keyboard.press("f")
    page.wait_for_function("() => !!document.fullscreenElement")
    expect(page.get_by_role("button", name="Выйти из полноэкранного режима (F)")).to_be_visible()
    page.get_by_role("button", name="Выйти из полноэкранного режима (F)").click()
    page.wait_for_function("() => !document.fullscreenElement")
    # a browser that refuses fullscreen: the cab hides its navigation instead, Esc brings it back
    page.evaluate("() => { Element.prototype.requestFullscreen = () => Promise.reject(new Error('denied')); }")
    page.get_by_role("button", name="Во весь экран (F)").click()
    expect(page.get_by_role("button", name="Назад", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Выйти из полноэкранного режима (F)")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("button", name="Назад", exact=True)).to_be_visible()
    expect(page).to_have_url(re.compile(rf"/player/{rid}"))

    # dragging the 3D view frees the camera; double-click (or the chip's button) gives it back
    canvas = page.get_by_role("img", name="3D-вид из кабины")
    box = canvas.bounding_box()
    page.mouse.move(box["x"] + 800, box["y"] + 350)
    page.mouse.down()
    page.mouse.move(box["x"] + 900, box["y"] + 320, steps=8)
    page.mouse.up()
    expect(page.get_by_text("свободная камера")).to_be_visible()
    page.mouse.dblclick(box["x"] + 800, box["y"] + 350)
    expect(page.get_by_text("кабина · вперёд")).to_be_visible()
    page.mouse.move(box["x"] + 700, box["y"] + 350)
    page.mouse.down()
    page.mouse.move(box["x"] + 640, box["y"] + 360, steps=8)
    page.mouse.up()
    expect(page.get_by_text("свободная камера")).to_be_visible()
    page.keyboard.press("Escape")  # Esc first gives the camera back, then leaves
    expect(page.get_by_text("кабина · вперёд")).to_be_visible()
    expect(page).to_have_url(re.compile(rf"/player/{rid}"))
    # opened directly (no page before it): «Назад» goes to the run's page
    page.get_by_role("button", name="Назад", exact=True).click()
    expect(page).to_have_url(re.compile(rf"/runs/{rid}$"))
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 12


def test_cab_fits_small_viewports(app, seeded):
    page, rid = app.page, seeded["ids"]["approach"]
    for w, h in ((1440, 900), (1280, 800), (1280, 720)):
        page.set_viewport_size({"width": w, "height": h})
        open_player(app, f"/player/{rid}?pos=30")
        assert page.evaluate("document.documentElement.scrollHeight <= innerHeight && document.documentElement.scrollWidth <= innerWidth")
        for name in ("Схема пути", "Решение", "До препятствия", "Задержка и частота", "Исправность"):
            b = page.get_by_role("region", name=name).bounding_box()
            assert b and b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, (w, h, name, b)
        sb = slider(page).bounding_box()
        assert sb["y"] + sb["height"] <= h, (w, h, sb)
    assert real_errors(app.errors) == []
