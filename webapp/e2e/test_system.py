"""End-to-end flows of the system pages — Прямой эфир, Параметры, О системе — in a real browser
against a real backend (fixtures in conftest.py). The first test sees a fresh data dir; the others
share runs seeded once through the API (two short demos and a user preset). The real ROS 2 node is
replaced by a small rosbridge v2 stand-in (below) that publishes /resense/status from a run's results.

  python -m pytest -q webapp/e2e/test_system.py     (~1 min; the whole suite: python -m pytest -q webapp/e2e)
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
import urllib.parse

import pytest
from e2e_helpers import Held, api_route, box_of, free_port, real_errors

pw = pytest.importorskip("playwright.sync_api")
websockets = pytest.importorskip("websockets")
expect = pw.expect

STATUS_TOPIC = "/resense/status"
SENSITIVE = {"tracking.confirm_time_s": 0.3, "cluster.eps": 0.4}


def chips(page):
    """The chips next to the page title (the live state, counts, versions)."""
    return page.locator("h1 ~ div").first


CARD = "main [class*=_card_]"  # the Card component (the page's own <section> wraps them all)


def card(page, title: str):
    return page.locator(CARD).filter(has=page.locator("h2", has_text=re.compile(rf"^{re.escape(title)}$")))


def beacon(page):
    return page.locator(CARD).filter(has=page.get_by_role("button", name="Правила решения"))


def slider_pos(page) -> int | None:
    v = page.get_by_role("slider", name="Перемотка прогона").get_attribute("aria-valuenow")
    return int(v) if v is not None else None


# ---------------------------------------------------------------------------------------- rosbridge


class FakeRosbridge:
    """A stand-in for rosbridge_server (rosbridge v2 JSON over one WebSocket port): publishes
    /resense/status (std_msgs/String, the node's status JSON) at 10 Hz to every subscriber, from the
    frames of a processed run plus the node's own keys. `publishing` off = the node stops sending
    (the page must call the data stale); drop() closes every connection (the node restarts)."""

    def __init__(self, frames: list[dict]):
        self.frames = frames
        self.port = free_port()
        self.url = f"ws://127.0.0.1:{self.port}"
        self.publishing = threading.Event()
        self.publishing.set()
        self.subscriptions = 0
        self._conns: set = set()
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> FakeRosbridge:
        self._thread.start()
        assert self._ready.wait(10), "the rosbridge stand-in did not start"
        return self

    def __exit__(self, *exc) -> None:
        self._loop.call_soon_threadsafe(self._done.set)
        self._thread.join(10)

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main())

    async def _main(self) -> None:
        self._done = asyncio.Event()
        async with websockets.serve(self._handler, "127.0.0.1", self.port):
            self._ready.set()
            await self._done.wait()

    async def _handler(self, ws) -> None:
        self._conns.add(ws)
        topics: set[str] = set()

        async def read() -> None:
            async for raw in ws:
                m = json.loads(raw)
                if m.get("op") == "subscribe":
                    topics.add(m.get("topic"))
                    self.subscriptions += 1
                elif m.get("op") == "unsubscribe":
                    topics.discard(m.get("topic"))

        reader = asyncio.create_task(read())
        n = 0
        try:
            while not reader.done():  # until the client goes (an unsubscribed one gets no sends to fail)
                await asyncio.sleep(0.1)
                if not self.publishing.is_set() or STATUS_TOPIC not in topics:
                    continue
                f = {k: v for k, v in self.frames[n % len(self.frames)].items() if k not in ("frame", "frame_id", "t", "pos")}
                n += 1
                f.update(node={"latency_ms": (f.get("timing_ms") or {}).get("total", 20) + 5, "fps": 10.0, "frames": n, "dropped_frames": 0,
                               "input_topic": "/lidar_points"},
                         snapshot_kind="frame", freshness={"mode": "replay", "valid": True, "reason": "ok"}, stop_held=False)
                await ws.send(json.dumps({"op": "publish", "topic": STATUS_TOPIC, "msg": {"data": json.dumps(f)}}))
        except websockets.ConnectionClosed:
            pass
        finally:
            reader.cancel()
            self._conns.discard(ws)

    def drop(self) -> None:
        async def close_all() -> None:
            for ws in list(self._conns):
                await ws.close()

        asyncio.run_coroutine_threadsafe(close_all(), self._loop).result(10)


# ---------------------------------------------------------------------------------------- seed


@pytest.fixture(scope="module")
def seeded(backend) -> dict:
    """Two processed demos (approach: STOP from the first frames; clear: GO / CAUTION), a scratch run
    for the «run deleted meanwhile» path and a user preset."""
    api = backend.api
    approach = api.demo("approach", 5)
    clear = api.demo("clear", 5)
    jobs = {"approach": api.job(approach["id"]), "clear": api.job(clear["id"]),
            "scratch": api.job(clear["id"], options={"limit": 6, "clouds": False})}
    ids = {}
    for k, j in jobs.items():
        done = api.wait_job(j["id"])
        assert done["status"] == "done", done
        ids[k] = done["run_id"]
    api.call("PATCH", f"/runs/{ids['scratch']}", {"name": "Черновик эфира"})
    preset = api.post("/presets", {"name": "Чувствительный", "description": "Быстрее подтверждение", "overrides": SENSITIVE})
    runs = {r["id"]: r for r in api.get("/runs")}
    return {"ids": ids, "runs": runs, "preset": preset}


@pytest.fixture(scope="module")
def rosbridge(backend, seeded):
    """The stand-in node, publishing the approach run's STOP frames."""
    lines = backend.api.get(f"/runs/{seeded['ids']['approach']}/download/results.jsonl")
    frames = [json.loads(line) for line in lines.splitlines() if line.strip()]
    stops = [f for f in frames if f.get("decision") == "STOP"]
    assert stops, "the approach demo has no STOP frame"
    with FakeRosbridge(stops) as node:
        yield node


# ---------------------------------------------------------------------------------------- 1


def test_fresh_stand_empty_states(app, backend):
    """A fresh data dir: the live replay has nothing to play and says what to do, only the sealed
    built-in preset exists, and «О системе» reads this stand from /api/system."""
    page = app.page
    app.goto("/live?source=sim")
    expect(page.get_by_text("Нет обработанных прогонов")).to_be_visible()
    expect(beacon(page).get_by_text("ЭФИР НЕ ЗАПУЩЕН")).to_be_visible()
    expect(page.locator("main").get_by_role("link", name="Загрузить", exact=True)).to_have_attribute("href", "/upload")
    page.locator("main").get_by_role("link", name="Демо-запись").click()
    expect(page).to_have_url(re.compile(r"/upload\?source=demo$"))
    page.go_back()
    expect(page).to_have_url(re.compile(r"/live\?source=sim$"))

    app.goto("/presets")
    expect(chips(page)).to_contain_text("1 пресет")
    expect(chips(page)).to_contain_text("20 параметров детектора")
    strip = page.get_by_role("navigation", name="Пресеты")
    expect(strip.get_by_role("button")).to_have_count(2)  # «Стандарт 1.0» and «Новый пресет»
    expect(page.locator("main").get_by_role("heading", name="Стандарт 1.0")).to_be_visible()
    expect(page.get_by_role("spinbutton")).to_have_count(0)  # sealed: read-only values
    expect(page.locator("[data-param]")).to_have_count(20)

    system = backend.api.get("/system")
    app.goto("/about")
    expect(chips(page)).to_contain_text(f"детектор v{system['detector_version']}")
    stand = card(page, "Как проверить — веб")
    expect(stand.get_by_text(f"v{system['detector_version']}", exact=True)).to_be_visible()
    expect(stand.get_by_text(f"v{system['version']}", exact=True)).to_be_visible()
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 2


def test_live_simulation_transport(app, seeded):
    """Replay of a processed run: start, live decision and stats, pause / resume (button and Space),
    seek (strip and keyboard), speed, loop off to the end of the record, stop; the 3D view and the
    scheme; the address bar follows the choice."""
    page, rid = app.page, seeded["ids"]["approach"]
    run = seeded["runs"][rid]
    n = run["summary"]["n_frames"]
    app.goto(f"/live?source=sim&run={rid}")
    expect(page.get_by_label("Прогон", exact=True)).to_have_value(rid)
    expect(chips(page)).to_have_text("не запущен")
    expect(page.get_by_role("radio", name="Симуляция")).to_have_attribute("aria-checked", "true")

    page.get_by_role("button", name="Запустить").click()
    expect(chips(page)).to_have_text("в эфире", timeout=20_000)
    expect(beacon(page).get_by_text(re.compile(r"^(СВОБОДНО|ВНИМАНИЕ|СТОП|ОШИБКА)$"))).to_be_visible()
    expect(beacon(page).get_by_text(re.compile(r"^(До препятствия|Свободно впереди)$"))).to_be_visible()
    node = card(page, "Узел")
    expect(node).to_contain_text("Гц")
    expect(node.get_by_text("симуляция")).to_be_visible()
    expect(card(page, "Последние 30 с").get_by_text("нет данных")).to_have_count(0)
    expect(card(page, "Исправность").locator("[class*='l-ok']").first).to_be_visible()  # fresh: lamps lit
    expect(page.get_by_role("img", name="3D-вид кадра")).to_be_visible()  # the run has clouds
    # the approach demo is STOP from its first frames: the object is listed with its distance
    expect(beacon(page).get_by_text("СТОП", exact=True)).to_be_visible(timeout=10_000)
    expect(card(page, "Объекты").locator("tbody tr").first).to_contain_text("габарит")

    # pause: the chip says so, the frame stops moving
    page.get_by_role("button", name="Пауза").click()
    expect(chips(page)).to_have_text("пауза")
    p0 = slider_pos(page)
    page.wait_for_timeout(600)
    assert slider_pos(page) == p0
    # Space resumes and pauses again (focus away from the buttons, which own the key)
    page.locator("h1").click()
    page.keyboard.press("Space")
    expect(chips(page)).to_have_text("в эфире")
    page.keyboard.press("Space")
    expect(chips(page)).to_have_text("пауза")

    # seek while paused: the frame comes at once
    strip = page.get_by_role("slider", name="Перемотка прогона")
    box = box_of(strip)
    target = n // 2
    page.mouse.click(box["x"] + box["width"] * (target + 0.5) / n, box["y"] + box["height"] / 2)
    expect(strip).to_have_attribute("aria-valuenow", str(target))
    expect(page.locator("main").get_by_text(f"кадр {target} / {n}")).to_be_visible()  # the 3D view follows

    # the view switch: the scheme draws the envelope and the monitored range
    page.get_by_role("radio", name="Схема").click()
    expect(page.get_by_role("img", name=re.compile("Схема пути сверху"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"^контроль \d+ м$"))).to_be_visible()
    page.get_by_role("radio", name="3D").click()
    expect(page.get_by_role("img", name="3D-вид кадра")).to_be_visible()

    # speed and loop, then to the end: the record ends and «Запустить» comes back
    page.get_by_role("radio", name="10×").click()
    expect(page.get_by_role("radio", name="10×")).to_have_attribute("aria-checked", "true")
    page.get_by_role("button", name="По кругу: вкл.").click()  # loop is a socket parameter: it reconnects, still paused
    expect(page.get_by_role("button", name="По кругу: выкл.")).to_have_attribute("aria-pressed", "false")
    expect(chips(page)).to_have_text("пауза")
    strip.focus()
    page.keyboard.press("End")
    expect(strip).to_have_attribute("aria-valuenow", str(n - 1))
    page.locator("h1").click()
    page.keyboard.press("Space")  # resume at the last frame: the replay ends at once
    expect(chips(page)).to_have_text("конец записи", timeout=15_000)
    expect(beacon(page).get_by_text("КОНЕЦ ЗАПИСИ")).to_be_visible()
    expect(page.get_by_role("button", name="Запустить")).to_be_visible()

    # start again from the beginning (1×, loop on), then stop
    page.get_by_role("radio", name="1×", exact=True).click()
    page.get_by_role("button", name="По кругу: выкл.").click()
    page.get_by_role("button", name="Запустить").click()
    expect(chips(page)).to_have_text("в эфире", timeout=20_000)
    page.get_by_role("button", name="Остановить эфир").click()
    expect(chips(page)).to_have_text("не запущен")
    expect(beacon(page).get_by_text("ЭФИР НЕ ЗАПУЩЕН")).to_be_visible()
    expect(card(page, "Узел").get_by_text("Гц")).to_have_count(0)  # no rate without a feed
    expect(card(page, "Узел").get_by_text("мс", exact=True)).to_have_count(0)  # nor a latency as if current
    # stopping on purpose is not a fault: the freshness lamps go dark, not violet
    expect(card(page, "Исправность").locator("[class*='l-error']")).to_have_count(0)
    expect(beacon(page).locator("[class*='lampBad']")).to_have_count(0)

    # another run from the list; the address bar follows
    other = seeded["ids"]["clear"]
    page.get_by_label("Прогон", exact=True).select_option(other)
    expect(page).to_have_url(re.compile(rf"/live\?source=sim&run={other}$"))
    assert real_errors(app.errors) == []


def test_live_seek_before_start_uses_the_chosen_transport(app, seeded):
    """A click on the strip of a replay that is not running starts it there, at the speed and loop
    chosen on the page, and nothing before the chosen frame is ever shown."""
    page, rid = app.page, seeded["ids"]["clear"]
    n = seeded["runs"][rid]["summary"]["n_frames"]
    app.goto(f"/live?source=sim&run={rid}")
    page.get_by_role("radio", name="5×", exact=True).click()
    page.get_by_role("button", name="По кругу: вкл.").click()
    expect(page.get_by_role("button", name="По кругу: выкл.")).to_be_visible()
    strip = page.get_by_role("slider", name="Перемотка прогона")
    expect(strip).not_to_have_attribute("aria-valuenow", re.compile("."))
    # every frame position the playhead shows from now on
    strip.evaluate("""el => { window.__shown = [];
        new MutationObserver(() => { const v = el.getAttribute('aria-valuenow'); if (v !== null) window.__shown.push(+v); })
          .observe(el, {attributes: true, attributeFilter: ['aria-valuenow']}); }""")
    box = box_of(strip)
    target = n // 3
    with page.expect_websocket(lambda ws: "/api/live/sim" in ws.url) as opened:
        page.mouse.click(box["x"] + box["width"] * (target + 0.5) / n, box["y"] + box["height"] / 2)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(opened.value.url).query)
    assert (q["run_id"], q["speed"], q["loop"]) == ([rid], ["5"], ["false"])
    # 5× without a loop: the rest of the run plays out and the record ends
    expect(chips(page)).to_have_text("конец записи", timeout=20_000)
    shown = page.evaluate("window.__shown")
    assert shown and min(shown) >= target and shown[-1] == n - 1, shown
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 3


def test_live_simulation_errors_and_loading(app, backend, seeded):
    """The runs list loads (spinner), fails with the backend's message and recovers on «Повторить»;
    a run deleted after the list loaded ends the replay with «Прогон не найден»; an unknown ?run=
    falls back to a playable run."""
    page, base = app.page, app.base
    held = Held(page, api_route(base, r"/runs$"))
    app.goto("/live?source=sim")
    expect(page.get_by_role("status", name="Прогоны загружаются")).to_be_visible()
    held.release()
    expect(page.get_by_label("Прогон", exact=True)).to_be_visible()

    fail = api_route(base, r"/runs$")
    page.route(fail, lambda r: r.fulfill(status=500, json={"detail": "Сбой списка прогонов (тест)"}))
    app.goto("/live?source=sim")
    alert = page.locator("main").get_by_role("alert")
    expect(alert).to_contain_text("Прогоны не загрузились")
    expect(alert).to_contain_text("Сбой списка прогонов (тест)")
    page.unroute(fail)
    alert.get_by_role("button", name="Повторить").click()
    expect(page.get_by_label("Прогон", exact=True)).to_be_visible()

    # an unknown run in the link: the newest playable run is chosen instead
    app.goto("/live?source=sim&run=nosuchrun")
    expect(page).not_to_have_url(re.compile("nosuchrun"))
    expect(page.get_by_label("Прогон", exact=True)).not_to_have_value("nosuchrun")

    # the run disappears between the list and «Запустить»: the replay socket closes with 4404
    scratch = seeded["ids"]["scratch"]
    app.goto(f"/live?source=sim&run={scratch}")
    expect(page.get_by_label("Прогон", exact=True)).to_have_value(scratch)
    backend.api.delete(f"/runs/{scratch}")
    page.get_by_role("button", name="Запустить").click()
    expect(page.locator("main").get_by_role("alert")).to_contain_text("Прогон не найден", timeout=15_000)
    expect(chips(page)).to_have_text("нет связи")
    expect(beacon(page).get_by_text("НЕТ СВЯЗИ")).to_be_visible()
    assert real_errors(app.errors, allowed=(500,)) == []


# ---------------------------------------------------------------------------------------- 4


def test_live_ros_node(app, rosbridge):
    """The real node through rosbridge: connect, live STOP with its object and health, data stale
    when the node falls silent (never green), reconnect after the node restarts, disconnect; a
    malformed and an unreachable address; switching to the replay forgets the node's frames."""
    page = app.page
    app.goto(f"/live?source=ros&url={rosbridge.url}")
    url_box = page.get_by_label("Адрес rosbridge")
    expect(url_box).to_have_value(rosbridge.url)
    expect(chips(page)).to_have_text("не подключено")
    expect(beacon(page).get_by_text("НЕ ПОДКЛЮЧЕНО")).to_be_visible()

    page.get_by_role("button", name="Подключить", exact=True).click()
    expect(chips(page)).to_have_text("в эфире", timeout=20_000)
    assert rosbridge.subscriptions >= 1
    b = beacon(page)
    expect(b.get_by_text("СТОП", exact=True)).to_be_visible()
    expect(b.get_by_text("До препятствия")).to_be_visible()
    expect(card(page, "Объекты").locator("tbody tr").first).to_contain_text("габарит")
    expect(card(page, "Узел").get_by_text("ROS 2")).to_be_visible()
    expect(page.locator("main").get_by_text("/lidar_points")).to_be_visible()  # the node's input topic
    expect(page.get_by_role("img", name=re.compile("Схема пути сверху"))).to_be_visible()
    expect(url_box).to_be_disabled()

    # the node falls silent: stale within a second, the decision and the lamps go dark
    rosbridge.publishing.clear()
    expect(chips(page)).to_have_text("данные устарели", timeout=5_000)
    expect(b.get_by_text("ДАННЫЕ УСТАРЕЛИ")).to_be_visible()
    expect(b.get_by_text("СТОП", exact=True)).to_have_count(0)
    expect(card(page, "Исправность").locator("[class*='l-ok']")).to_have_count(0)
    rosbridge.publishing.set()
    expect(chips(page)).to_have_text("в эфире", timeout=5_000)

    # the node restarts: the page reconnects by itself
    rosbridge.drop()
    expect(chips(page)).to_have_text("переподключение…", timeout=5_000)
    expect(chips(page)).to_have_text("в эфире", timeout=15_000)
    assert rosbridge.subscriptions >= 2

    page.get_by_role("button", name="Отключить").click()
    expect(chips(page)).to_have_text("не подключено")
    expect(url_box).to_be_enabled()

    # a malformed address is caught before connecting
    url_box.fill("http://nowhere")
    page.get_by_role("button", name="Подключить", exact=True).click()
    expect(page.get_by_text("адрес вида ws://хост:9090")).to_be_visible()
    # an unreachable one fails with the reason and a retry
    dead = f"ws://127.0.0.1:{free_port()}"
    url_box.fill(dead)
    url_box.press("Enter")
    alert = page.locator("main").get_by_role("alert")
    expect(alert).to_contain_text("Нет связи с узлом ROS (rosbridge)", timeout=15_000)
    expect(alert.get_by_role("button", name="Повторить")).to_be_visible()
    expect(page).to_have_url(re.compile(re.escape("url=" + urllib.parse.quote(dead, safe=""))))  # a link to this address
    # the error was about that address: editing it clears the error
    url_box.fill(rosbridge.url)
    expect(page.locator("main").get_by_role("alert")).to_have_count(0)
    expect(chips(page)).to_have_text("не подключено")

    # the other source: nothing of the node's is shown as the replay's
    page.get_by_role("radio", name="Симуляция").click()
    expect(page).to_have_url(re.compile(r"source=sim"))
    expect(chips(page)).to_have_text("не запущен")
    expect(beacon(page).get_by_text("ЭФИР НЕ ЗАПУЩЕН")).to_be_visible()
    expect(card(page, "Последние 30 с").get_by_text("нет данных")).to_be_visible()
    # the browser's back button leaves the page (the source switch replaces the entry)
    app.goto("/about")
    app.goto("/live")
    page.go_back()
    expect(page).to_have_url(re.compile(r"/about$"))
    assert real_errors(app.errors, patterns=(r"WebSocket connection to 'ws://127\.0\.0\.1:\d+/' failed",)) == []


# ---------------------------------------------------------------------------------------- 5


def test_presets_editor(app, backend, seeded):
    """Duplicate the sealed built-in, change values (stepper, toggle), reset one, a name conflict
    (409) shown at the name field, create; edit and save a user preset; the process link and the
    back button; delete with confirmation."""
    page, api = app.page, backend.api
    app.goto("/presets")
    head = page.locator("main").get_by_role("heading", name="Стандарт 1.0")
    expect(head).to_be_visible()
    expect(page.get_by_text("опечатан").first).to_be_visible()
    # a parameter's «?»: its help, the default and the range
    page.get_by_role("button", name="Что такое «Время подтверждения»").hover()
    tip = page.get_by_role("tooltip").filter(has_text="По умолчанию")
    expect(tip).to_be_visible()
    expect(tip).to_contain_text("По умолчанию 0,5 с")
    expect(tip).to_contain_text("диапазон 0,0–2,0 с")

    page.get_by_role("button", name="Дублировать").click()
    expect(page).to_have_url(re.compile(r"/presets\?id=__new__$"))
    name = page.get_by_label("Название пресета")
    expect(name).to_have_value("Стандарт 1.0 (копия)")
    expect(page.get_by_label("Описание пресета")).to_have_value("На основе «Стандарт 1.0»")
    page.get_by_role("button", name="Радиус объединения точек: больше").click()
    page.get_by_role("button", name="Время подтверждения: меньше").click()
    page.get_by_role("button", name="Время подтверждения: меньше").click()
    page.get_by_role("switch", name="Поиск низких предметов").click()
    expect(page.locator("main").get_by_text("изменено 3", exact=True).first).to_be_visible()
    expect(page.locator("[data-param='cluster.eps']")).to_have_class(re.compile("changed"))
    page.get_by_role("button", name=re.compile(r"^Поиск низких предметов: сбросить к да$")).click()
    expect(page.get_by_role("switch", name="Поиск низких предметов")).to_have_attribute("aria-checked", "true")
    expect(page.locator("main").get_by_text("изменено 2", exact=True).first).to_be_visible()

    # a taken name: the backend's 409 message under the field, nothing created
    name.fill("чувствительный")
    page.get_by_role("button", name="Создать").click()
    expect(page.get_by_text("Пресет с таким названием уже есть")).to_be_visible()
    assert len(api.get("/presets")) == 2
    name.fill("Быстрый")
    expect(page.get_by_text("Пресет с таким названием уже есть")).to_have_count(0)
    page.get_by_role("button", name="Создать").click()
    expect(page).to_have_url(re.compile(r"/presets\?id=(?!__new__)\w+$"))
    new_id = page.url.rsplit("=", 1)[1]
    created = api.get(f"/presets/{new_id}")
    assert created["name"] == "Быстрый"
    assert created["overrides"] == {"cluster.eps": 0.4, "tracking.confirm_time_s": 0.3}
    expect(page.get_by_role("navigation", name="Пресеты").get_by_role("button", name=re.compile("^Быстрый"))).to_have_attribute("aria-current", "true")

    # edit and save: PATCH replaces the overrides; «Сохранить» is off again afterwards
    page.get_by_role("button", name="Радиус объединения точек: сбросить к 0,35 м").click()
    page.get_by_label("Минимум точек объекта", exact=True).fill("7")
    page.get_by_label("Минимум точек объекта", exact=True).press("Enter")
    save = page.get_by_role("button", name="Сохранить")
    expect(save).to_be_enabled()
    save.click()
    expect(save).to_be_disabled()
    assert api.get(f"/presets/{new_id}")["overrides"] == {"cluster.min_points": 7, "tracking.confirm_time_s": 0.3}
    # an edit then «Отменить» restores the saved values
    page.get_by_role("button", name="Минимум точек объекта: больше").click()
    expect(page.get_by_label("Минимум точек объекта", exact=True)).to_have_value("8")
    page.get_by_role("button", name="Отменить").click()
    expect(page.get_by_label("Минимум точек объекта", exact=True)).to_have_value("7")

    # «Обработать с этим пресетом» hands the preset to Загрузка; back returns to it
    page.get_by_role("link", name="Обработать с этим пресетом").click()
    expect(page).to_have_url(re.compile(rf"/upload\?preset={new_id}$"))
    expect(page.get_by_label("Пресет", exact=True)).to_have_value(new_id)
    page.go_back()
    expect(page).to_have_url(re.compile(rf"/presets\?id={new_id}$"))
    expect(page.get_by_label("Название пресета")).to_have_value("Быстрый")

    # delete asks once, then the list and the URL fall back to the built-in
    page.get_by_role("button", name="Удалить пресет").click()
    page.get_by_role("button", name="Удалить?").click()
    expect(page).to_have_url(re.compile(r"/presets$"))
    expect(head).to_be_visible()
    assert [p["id"] for p in api.get("/presets")] == ["standard", seeded["preset"]["id"]]
    assert real_errors(app.errors, allowed=(409,)) == []


def test_presets_errors_and_deep_link(app, backend, seeded):
    """A deep link opens a user preset; a preset deleted elsewhere cannot be saved (404, the
    backend's message in a banner); loading and offline states with a retry."""
    page, base, api = app.page, app.base, backend.api
    # a link to a preset that does not exist (any more) opens «Стандарт 1.0» and says so in the address
    app.goto("/presets?id=nosuch")
    expect(page.locator("main").get_by_role("heading", name="Стандарт 1.0")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/presets$"))

    tmp = api.post("/presets", {"name": "Временный", "overrides": {"gauge.range_max": 150}})
    app.goto(f"/presets?id={tmp['id']}")
    expect(page.get_by_label("Название пресета")).to_have_value("Временный")
    expect(page.get_by_label("Дальность контроля", exact=True)).to_have_value("150")
    expect(page.locator("main").get_by_text("изменено 1", exact=True).first).to_be_visible()
    api.delete(f"/presets/{tmp['id']}")
    page.get_by_role("button", name="Дальность контроля: больше").click()
    page.get_by_role("button", name="Сохранить").click()
    banner = page.locator("main").get_by_role("alert")
    expect(banner).to_contain_text("Не сохранено")
    expect(banner).to_contain_text("Пресет не найден")

    held = Held(page, api_route(base, r"/presets(/schema)?$"))
    app.goto("/presets")
    expect(page.get_by_role("status", name="Пресеты загружаются")).to_be_visible()
    held.release()
    expect(page.locator("[data-param]")).to_have_count(20)

    offline = api_route(base, r"/presets(/schema)?$")
    page.route(offline, lambda r: r.abort())
    app.goto("/presets")
    alert = page.locator("main").get_by_role("alert")
    expect(alert).to_contain_text("Бэкенд недоступен")
    page.unroute(offline)
    alert.get_by_role("button", name="Повторить").click()
    expect(page.locator("[data-param]")).to_have_count(20)
    assert real_errors(app.errors, allowed=(404,), patterns=(r"net::ERR_FAILED",)) == []


# ---------------------------------------------------------------------------------------- 6


def test_about_page(app, backend):
    """The pipeline with a «?» per station, the four decisions with their rule, the six results
    with their caveat, the commands copied exactly, the documentation links, the team, the stand
    from /api/system (and when the backend is gone), the demo call to action and back."""
    page, base = app.page, app.base
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    app.goto("/about")
    stations = page.get_by_role("list", name="Обработка кадра").get_by_role("listitem")
    expect(stations).to_have_count(7)
    for s in ("декодирование", "калибровка", "модель пути", "габарит", "кластеризация", "трекинг", "решение"):
        expect(page.get_by_role("button", name=f"Этап «{s}»")).to_be_visible()
    page.get_by_role("button", name="Этап «габарит»").hover()
    expect(page.get_by_role("tooltip").filter(has_text="1,05 м в каждую сторону")).to_be_visible()

    decisions = page.get_by_role("list", name="Решения").get_by_role("listitem")
    expect(decisions).to_have_text([re.compile(rf"^{d}\?$") for d in ("СВОБОДНО", "ВНИМАНИЕ", "СТОП", "ОШИБКА")])
    page.get_by_role("button", name="Когда СТОП").hover()
    expect(page.get_by_role("tooltip").filter(has_text="подтверждённое препятствие в габарите 2,1 × 3,0 м")).to_be_visible()

    results = page.get_by_role("list", name="Результаты в выборке").get_by_role("listitem")
    expect(results).to_have_count(6)
    for value in ("55,5–56,6", "2,3", "8 из 8", "81", "10", "≈ 210"):
        expect(results.filter(has_text=value).first).to_be_visible()
    results.filter(has_text="Ложные СТОП").get_by_role("button").hover()
    expect(page.get_by_role("tooltip").filter(has_text="20-минутная поездка")).to_be_visible()

    # copy: the exact command lands on the clipboard, the button confirms
    ros = card(page, "Как проверить — ROS 2")
    expect(ros.locator("code")).to_have_count(5)
    ros.get_by_role("button", name="Скопировать").nth(1).click()
    expect(ros.get_by_role("button", name="Скопировано")).to_be_visible()
    assert page.evaluate("navigator.clipboard.readText()") == "docker run --rm -it --net=host --ipc=host resense"
    web = card(page, "Как проверить — веб")
    expect(web.locator("code")).to_have_text("scripts/run_webapp.sh")
    expect(web.get_by_role("link", name="localhost:8080")).to_have_attribute("href", "http://localhost:8080")

    links = page.get_by_role("list", name="Ссылки на документацию").get_by_role("link")
    expect(links).to_have_count(5)
    expect(links.filter(has_text="Руководство")).to_have_attribute("href", "https://resense.gitbook.io/resense-docs/")
    for label, doc in (("Архитектура", "ARCHITECTURE"), ("Алгоритм", "ALGORITHM"), ("Эксперименты", "EXPERIMENTS")):
        expect(links.filter(has_text=label)).to_have_attribute("href", re.compile(rf"/docs/{doc}\.md$"))
    expect(links.filter(has_text="Прежний дашборд")).to_have_attribute("href", re.compile(r"/web$"))
    for i in range(5):
        expect(links.nth(i)).to_have_attribute("target", "_blank")
    expect(page.get_by_role("list", name="Роли в команде").get_by_role("listitem")).to_have_count(4)

    features = backend.api.get("/system")["features"]
    for label, key in (("Бэги ROS 2", "rosbags"), ("Ядра C++", "native_kernels"), ("open3d", "open3d"), ("Облака для 3D", "clouds")):
        expect(web.get_by_role("listitem").filter(has_text=label)).to_contain_text(": есть" if features[key] else ": нет")

    page.get_by_role("link", name="Попробовать на демо").click()
    expect(page).to_have_url(re.compile(r"/upload\?source=demo$"))
    page.go_back()
    expect(page).to_have_url(re.compile(r"/about$"))

    # the backend goes away: the stand says so, the rest of the page stays
    offline = api_route(base, r"/system$")
    page.route(offline, lambda r: r.abort())
    app.goto("/about")
    expect(web.get_by_role("alert")).to_contain_text("Нет связи с бэкендом")
    expect(results).to_have_count(6)
    page.unroute(offline)
    assert real_errors(app.errors, patterns=(r"net::ERR_FAILED",)) == []
