"""End-to-end flows of the analysis pages — Прогоны, Прогон, Сравнение — in a real browser against a
real backend (fixtures in conftest.py). The first test sees a fresh data dir; the others share the
runs seeded once through the API (demo recordings, a second preset, a results .jsonl, scratch runs).

  python -m pytest -q webapp/e2e/test_analysis.py     (~1 min; the whole suite: python -m pytest -q webapp/e2e)
"""
from __future__ import annotations

import re
import urllib.request

import pytest
from e2e_helpers import Held, api_route, box_of, real_errors

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect

SENSITIVE = {"tracking.confirm_time_s": 0.1}
DECISION_WORD = r"(свободно|внимание|стоп|ошибка)"


def player_pos(page, run_id: str) -> int:
    """Wait for the player URL of a run and return its ?pos=."""
    expect(page).to_have_url(re.compile(rf"/player/{run_id}\?pos=\d+$"))
    return int(page.url.rsplit("=", 1)[1])


def back_to(page, pattern: str) -> None:
    page.go_back()
    expect(page).to_have_url(re.compile(pattern))


# ---------------------------------------------------------------------------------------- seed


@pytest.fixture(scope="module")
def seeded(backend) -> dict:
    """Runs of three short demos (crossing twice: standard and a sensitive preset), a results-only
    .jsonl, and three scratch runs for the rename / delete flows. Returns ids by role."""
    api = backend.api
    recs = {sc: api.demo(sc, sec) for sc, sec in (("approach", 6), ("crossing", 6), ("clear", 5))}
    preset = api.post("/presets", {"name": "Чувствительный", "overrides": SENSITIVE})
    jobs = {
        "approach": api.job(recs["approach"]["id"]),
        "cross": api.job(recs["crossing"]["id"]),
        "cross_sens": api.job(recs["crossing"]["id"], preset_id=preset["id"]),
        "clear": api.job(recs["clear"]["id"]),
    }
    for k in ("scratch1", "scratch2", "scratch3"):
        jobs[k] = api.job(recs["clear"]["id"], options={"limit": 8, "clouds": False})
    ids = {}
    for k, j in jobs.items():
        done = api.wait_job(j["id"])
        assert done["status"] == "done", done
        ids[k] = done["run_id"]
    for i, k in enumerate(("scratch1", "scratch2", "scratch3"), 1):
        api.call("PATCH", f"/runs/{ids[k]}", {"name": f"Черновик {i}"})
    # a results-only recording: the approach run's results.jsonl uploaded again
    rec = api.upload_jsonl("tunnel_log", api.get(f"/runs/{ids['approach']}/download/results.jsonl").encode("utf-8"))
    ids["jsonl"] = api.processed(rec["id"])["run_id"]
    names = {r["id"]: r["name"] for r in api.get("/runs")}
    return {"ids": ids, "names": names, "preset": preset}


# ---------------------------------------------------------------------------------------- 1


def test_empty_states(app):
    page = app.page
    app.goto("/runs")
    expect(page.get_by_text("Прогонов пока нет")).to_be_visible()
    expect(page.get_by_label("Поиск по названию")).to_have_count(0)  # no filters before the first run
    expect(page.get_by_role("link", name="Демо")).to_have_attribute("href", "/upload?source=demo")
    page.locator("main").get_by_role("link", name="Загрузить запись").click()
    expect(page).to_have_url(re.compile(r"/upload$"))

    app.goto("/compare")
    expect(page.get_by_text("Сравнивать пока нечего")).to_be_visible()
    expect(page.locator("main").get_by_role("link", name="Загрузить запись")).to_have_attribute("href", "/upload")

    app.goto("/runs/nosuchrun")
    expect(page.get_by_role("heading", name="Прогон не найден")).to_be_visible()
    page.get_by_role("link", name="К прогонам").last.click()
    expect(page).to_have_url(re.compile(r"/runs$"))
    assert real_errors(app.errors, allowed=(404,)) == []


# ---------------------------------------------------------------------------------------- 2


def test_runs_list_search_filters_sort_and_back(app, backend, seeded):
    page, ids = app.page, seeded["ids"]
    runs = backend.api.get("/runs")
    app.goto("/runs")
    rows = page.locator("tbody tr")
    expect(rows).to_have_count(len(runs))
    n_stop = sum(r["summary"]["counts"]["STOP"] > 0 for r in runs)
    n_labels = sum(bool(r["summary"]["eval"]) for r in runs)
    expect(page.get_by_role("radio", name=f"Со СТОП {n_stop}")).to_be_visible()
    expect(page.get_by_role("radio", name=f"Без СТОП {len(runs) - n_stop}")).to_be_visible()
    expect(page.get_by_role("radio", name=f"С разметкой {n_labels}")).to_be_visible()
    # the facts of a row: source, frames, first STOP, verdict against labels
    cross = rows.filter(has=page.get_by_role("link", name="demo_crossing", exact=True))
    expect(cross).to_contain_text("rosbag2")
    expect(cross).to_contain_text(re.compile(r"\d+,\d\s?м"))
    expect(cross.get_by_role("img", name=re.compile("Решения по кадрам"))).to_be_visible()

    # typing at key speed keeps every character (the URL follows the box)
    search = page.get_by_label("Поиск по названию")
    search.click()
    page.keyboard.type("crossing", delay=0)
    expect(search).to_have_value("crossing")
    expect(rows).to_have_count(2)
    expect(page).to_have_url(re.compile(r"[?&]q=crossing"))
    search.fill("")
    expect(rows).to_have_count(len(runs))

    # quick successive filter changes all land in the URL
    page.get_by_role("radio", name=re.compile(r"^Со СТОП")).click()
    page.get_by_label("Сортировка").select_option("name")
    expect(page).to_have_url(re.compile(r"f=stop.*sort=name|sort=name.*f=stop"))
    expect(rows).to_have_count(n_stop)
    names = page.locator("tbody tr td:nth-child(2) a").all_inner_texts()
    assert names == sorted(names, key=str.lower), names
    page.get_by_label("Источник").select_option("jsonl")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("jsonl")
    page.get_by_role("radio", name=re.compile(r"^Без СТОП")).click()
    expect(page.get_by_text("Ничего не найдено")).to_be_visible()
    page.get_by_role("button", name="Сбросить фильтры").click()
    expect(rows).to_have_count(len(runs))

    # the browser back button returns to the same list after opening a run
    page.get_by_role("radio", name=re.compile(r"^С разметкой")).click()
    search.fill("demo")
    expect(page).to_have_url(re.compile(r"q=demo"))
    rows.filter(has=page.get_by_role("link", name="demo_approach", exact=True)).locator("td").nth(2).click()
    expect(page).to_have_url(re.compile(rf"/runs/{ids['approach']}$"))
    expect(page.get_by_role("heading", name="demo_approach")).to_be_visible()
    back_to(page, r"/runs\?")
    expect(search).to_have_value("demo")
    expect(page.get_by_role("radio", name=re.compile(r"^С разметкой"))).to_have_attribute("aria-checked", "true")
    expect(rows).to_have_count(sum(bool(r["summary"]["eval"]) and "demo" in r["name"] for r in runs))
    # the row's player and open buttons
    row = rows.filter(has=page.get_by_role("link", name="demo_approach", exact=True))
    expect(row.get_by_role("link", name="Открыть в плеере: demo_approach")).to_have_attribute("href", f"/player/{ids['approach']}")
    expect(row.get_by_role("link", name="Открыть прогон demo_approach")).to_have_attribute("href", f"/runs/{ids['approach']}")
    assert real_errors(app.errors) == []


def test_runs_selection_opens_compare(app, seeded):
    page, ids, names = app.page, seeded["ids"], seeded["names"]
    app.goto("/runs")
    bar = page.get_by_role("region", name="Выбранные прогоны")
    page.get_by_label("Выбрать для сравнения: demo_crossing", exact=True).check()
    expect(bar.get_by_role("button", name="Сравнить (1)")).to_be_disabled()
    page.get_by_label("Выбрать для сравнения: demo_approach", exact=True).check()
    link = bar.get_by_role("link", name="Сравнить (2)")
    expect(link).to_have_attribute("href", f"/compare?runs={ids['cross']},{ids['approach']}")
    # at most four: the fifth checkbox is locked
    for k in ("clear", "jsonl"):
        page.get_by_label(f"Выбрать для сравнения: {names[ids[k]]}", exact=True).check()
    expect(bar.get_by_role("link", name="Сравнить (4)")).to_be_visible()
    expect(page.get_by_label("Для сравнения выбрано 4").first).to_be_disabled()
    bar.get_by_role("button", name=f"Убрать {names[ids['jsonl']]}").click()
    bar.get_by_role("button", name=f"Убрать {names[ids['clear']]}").click()
    bar.get_by_role("link", name="Сравнить (2)").click()
    expect(page).to_have_url(re.compile(rf"/compare\?runs={ids['cross']},{ids['approach']}$"))
    expect(page.get_by_role("heading", name="Показатели")).to_be_visible()
    back_to(page, r"/runs$")
    expect(bar.get_by_role("link", name="Сравнить (2)")).to_be_visible()  # the selection survives «back»
    bar.get_by_role("button", name="Сбросить").click()
    expect(bar).to_have_count(0)
    assert real_errors(app.errors) == []


def test_runs_rename_and_delete_with_errors(app, backend, seeded):
    page, api, ids = app.page, backend.api, seeded["ids"]
    app.goto("/runs")
    rows = page.locator("tbody tr")
    # inline rename: Escape cancels, Enter saves
    page.get_by_role("button", name="Действия: Черновик 1").click()
    page.get_by_role("menuitem", name="Переименовать").click()
    box = page.get_by_label("Новое название прогона")
    box.fill("не сохранится")
    box.press("Escape")
    expect(page.get_by_role("link", name="Черновик 1", exact=True)).to_be_visible()
    page.get_by_role("button", name="Действия: Черновик 1").click()
    page.get_by_role("menuitem", name="Переименовать").click()
    box.fill("Прогон жюри")
    box.press("Enter")
    expect(page.get_by_role("link", name="Прогон жюри", exact=True)).to_be_visible()
    assert api.get(f"/runs/{ids['scratch1']}")["name"] == "Прогон жюри"

    # the run vanished meanwhile: the backend's Russian 404 shows in place (rename, then delete)
    api.delete(f"/runs/{ids['scratch2']}")
    page.get_by_role("button", name="Действия: Черновик 2").click()
    page.get_by_role("menuitem", name="Переименовать").click()
    box.fill("Черновик 2Б")
    box.press("Enter")
    expect(page.get_by_role("alert").filter(has_text="Прогон не найден")).to_be_visible()
    box.press("Escape")
    page.get_by_role("button", name="Действия: Черновик 2").click()
    page.get_by_role("menuitem", name="Удалить").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Удалить «Черновик 2»?")
    dialog.get_by_role("button", name="Удалить").click()
    expect(dialog).to_contain_text("Прогон не найден")
    page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)

    # delete after confirming: the row goes, the run is gone on the server
    before = rows.count()
    page.get_by_role("button", name="Действия: Прогон жюри").click()
    page.get_by_role("menuitem", name="Удалить").click()
    page.get_by_role("dialog").get_by_role("button", name="Удалить").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(page.get_by_role("link", name="Прогон жюри", exact=True)).to_have_count(0)
    expect(rows).to_have_count(before - 2)  # the vanished one goes with the refresh
    with pytest.raises(Exception, match="404"):
        api.get(f"/runs/{ids['scratch1']}")
    assert real_errors(app.errors, allowed=(404,)) == []


# ---------------------------------------------------------------------------------------- 3


def test_run_page_timeline_chart_events_and_downloads(app, backend, seeded):
    page, api = app.page, backend.api
    rid = seeded["ids"]["cross"]
    detail = api.get(f"/runs/{rid}")
    series = api.get(f"/runs/{rid}/series")
    frames = series["frame"]
    fs = detail["summary"]["first_stop"]
    assert fs is not None, "the crossing demo stops"
    first_pos = frames.index(fs["frame"])

    app.goto(f"/runs/{rid}")
    expect(page.get_by_role("heading", name="demo_crossing")).to_be_visible()
    expect(page.locator("main")).to_contain_text(f"с кадра {fs['frame']}")
    for label in ("Кадров", "Длительность", "СТОП-эпизоды", "Первый СТОП", "Мин. дистанция", "Пропуски", "p95 задержка", "Ложные тревоги"):
        expect(page.get_by_text(label, exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="Оценка по разметке")).to_be_visible()
    expect(page.locator("main")).to_contain_text("разметка: в габарите")  # the labels lane legend
    # every KPI explains itself: hovering a «?» opens its tooltip
    page.get_by_text("Пропуски", exact=True).locator("xpath=..").get_by_role("button", name="Подсказка").hover()
    expect(page.get_by_role("tooltip").filter(has_text="Объект в габарите по разметке")).to_be_visible()

    # the strip: keyboard from the playhead (the first STOP), Enter opens the player there
    strip = page.get_by_role("slider", name=re.compile("^Решения по кадрам: выберите кадр"))
    strip.focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    expect(strip).to_have_attribute("aria-valuenow", str(first_pos + 2))
    page.keyboard.press("Enter")
    assert player_pos(page, rid) == first_pos + 2
    back_to(page, rf"/runs/{rid}$")
    # a click on a frame opens that frame
    strip = page.get_by_role("slider", name=re.compile("^Решения по кадрам: выберите кадр"))
    box = box_of(strip)
    target = len(frames) // 4
    page.mouse.click(box["x"] + (target + 0.5) / len(frames) * box["width"], box["y"] + box["height"] / 2)
    assert player_pos(page, rid) == target
    back_to(page, rf"/runs/{rid}$")

    # the distance chart: hover reads frame / time / decision, a click opens the player
    chart = page.get_by_role("group", name="График: детектор по времени")
    cb = box_of(chart)
    page.mouse.move(cb["x"] + cb["width"] * 0.6, cb["y"] + cb["height"] * 0.4)
    tip = chart.locator("[class*=_tip_]")
    expect(tip).to_contain_text(re.compile(r"кадр \d+ · [\d,]+\s?с"))
    expect(tip).to_contain_text(re.compile(r"СВОБОДНО|ВНИМАНИЕ|СТОП|ОШИБКА"))
    page.mouse.click(cb["x"] + cb["width"] * 0.6, cb["y"] + cb["height"] * 0.4)
    assert 0 <= player_pos(page, rid) < len(frames)
    back_to(page, rf"/runs/{rid}$")
    page.get_by_role("radio", name="Путь").click()
    expect(page.get_by_role("group", name="График: свободный путь по времени")).to_be_visible()
    page.get_by_role("radio", name="Видимость").click()
    expect(page.get_by_role("group", name="График: видимость по времени")).to_be_visible()

    # events: one row per event of the API; hovering points the 3D card, a click opens the player
    events = page.locator("main button[aria-label$='открыть в плеере']")
    expect(events).to_have_count(len(detail["events"]))
    last = detail["events"][-1]
    pos = frames.index(last["first_frame"])
    events.last.hover()
    expect(page.locator("section[aria-label='3D-вид кадра']")).to_contain_text(f"кадр {last['first_frame']} /")
    events.last.click()
    assert player_pos(page, rid) == pos
    back_to(page, rf"/runs/{rid}$")

    # downloads answer, and the CSV tile shows its real size
    links = page.locator("a[download]")
    expect(links).to_have_count(3)
    for href in links.evaluate_all("els => els.map(e => e.getAttribute('href'))"):
        with urllib.request.urlopen(backend.url + href, timeout=30) as r:
            assert r.status == 200 and "attachment" in r.headers["Content-Disposition"], href
    expect(links.last).to_contain_text(re.compile(r"\d\s?(Б|КБ|МБ)"))
    # header actions
    expect(page.get_by_role("link", name="Открыть в плеере")).to_have_attribute("href", f"/player/{rid}")
    expect(page.get_by_role("link", name="Сравнить")).to_have_attribute("href", f"/compare?runs={rid},{seeded['ids']['cross_sens']}")
    assert real_errors(app.errors) == []


def test_run_page_preset_rename_and_delete(app, backend, seeded):
    page, api, ids = app.page, backend.api, seeded["ids"]
    sens = ids["cross_sens"]
    app.goto(f"/runs/{sens}")
    # the default name's « · preset» suffix is left to the preset chip, whose «?» lists the overrides
    expect(page.get_by_role("heading", name="demo_crossing")).to_be_visible()
    chip = page.locator("[class*=_preset_]").filter(has_text="Чувствительный")
    chip.get_by_role("button", name="Подсказка").hover()
    expect(page.get_by_role("tooltip").filter(has_text="Время подтверждения")).to_contain_text(re.compile(r"0,1\s?с"))

    page.get_by_role("button", name="Действия с прогоном").click()
    page.get_by_role("menuitem", name="Переименовать").click()
    dialog = page.get_by_role("dialog", name="Переименовать прогон")
    dialog.get_by_label("Название прогона").fill("  ")
    expect(dialog.get_by_role("button", name="Сохранить")).to_be_disabled()
    dialog.get_by_label("Название прогона").fill("Пересечение, быстрый трекер")
    dialog.get_by_role("button", name="Сохранить").click()
    expect(dialog).to_have_count(0)
    expect(page.get_by_role("heading", name="Пересечение, быстрый трекер")).to_be_visible()
    api.call("PATCH", f"/runs/{sens}", {"name": seeded["names"][sens]})

    # delete from the run page: back to the list, the run is gone
    app.goto(f"/runs/{ids['scratch3']}")
    expect(page.get_by_role("heading", name="Черновик 3")).to_be_visible()
    page.get_by_role("button", name="Действия с прогоном").click()
    page.get_by_role("menuitem", name="Удалить").click()
    page.get_by_role("dialog").get_by_role("button", name="Удалить").click()
    expect(page).to_have_url(re.compile(r"/runs$"))
    expect(page.locator("tbody tr").first).to_be_visible()
    expect(page.get_by_role("link", name="Черновик 3", exact=True)).to_have_count(0)
    assert real_errors(app.errors) == []


def test_run_page_loading_offline_and_retry(app, seeded):
    page, rid = app.page, seeded["ids"]["approach"]
    # loading: the run's answer is held back — skeletons, no text
    pattern = api_route(app.base, rf"/runs/{rid}$")
    held = Held(page, pattern)
    app.goto(f"/runs/{rid}", wait_until="domcontentloaded")
    expect(page.get_by_role("status", name="Загрузка").first).to_be_visible()
    held.release()
    expect(page.get_by_role("heading", name="demo_approach")).to_be_visible()

    # the backend is unreachable: the banner, then «Повторить» once it is back
    page.route(pattern, lambda route: route.abort("connectionrefused"))
    app.goto(f"/runs/{rid}")
    expect(page.get_by_text("Бэкенд недоступен")).to_be_visible()
    page.unroute(pattern)
    page.get_by_role("button", name="Повторить").click()
    expect(page.get_by_role("heading", name="demo_approach")).to_be_visible()
    app.errors[:] = [e for e in app.errors if "ERR_CONNECTION_REFUSED" not in e]
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 4


def test_compare_deep_link_table_strips_chart_and_diff(app, backend, seeded):
    page, ids = app.page, seeded["ids"]
    trio = [ids["cross"], ids["cross_sens"], ids["approach"]]
    app.goto(f"/compare?runs={','.join(trio)}")
    for rid in trio:
        expect(page.get_by_role("button", name=re.compile(f"^Убрать из сравнения: {re.escape(seeded['names'][rid])}$"))).to_be_visible()
    table = page.locator("table").first
    expect(table.locator("tbody tr")).to_have_count(11)
    # the best value of a row sits in an ink pill (ties share it)
    firsts = [backend.api.get(f"/runs/{rid}")["summary"]["first_stop"]["distance"] for rid in trio]
    best = sum(d == max(firsts) for d in firsts) if len(set(firsts)) > 1 else 0
    expect(table.locator("tbody tr").filter(has_text="Первый СТОП").locator("[class*=_best_]")).to_have_count(best)
    expect(table.locator("thead")).to_contain_text("Чувствительный")  # presets differ: named per column
    # runs of one recording with different presets: what changed
    expect(page.get_by_role("heading", name="Что изменилось")).to_be_visible()
    row = page.locator("table").nth(1).locator("tbody tr").filter(has_text="Время подтверждения")
    expect(row).to_contain_text(re.compile(r"0,5\s?с"))
    expect(row).to_contain_text(re.compile(r"0,1\s?с"))
    # every row explains itself
    table.locator("tbody tr").first.get_by_role("button", name="Подсказка").hover()
    expect(page.get_by_role("tooltip").filter(has_text="Сколько кадров")).to_be_visible()

    # the strips share one time axis: hovering reads each run's frame there
    area = page.locator("[class*=_hoverArea_]")
    ab = box_of(area)
    page.mouse.move(ab["x"] + ab["width"] * 0.3, ab["y"] + 10)
    reads = page.locator("[class*=_stripRead_]")
    expect(reads).to_have_count(3)
    for i in range(3):
        expect(reads.nth(i)).to_have_text(re.compile(rf"кадр \d+ · {DECISION_WORD}"))
    # a click opens the run under the pointer (the third row) in the player
    rows = page.locator("[class*=_stripRow_]")
    rb = box_of(rows.nth(2))
    page.mouse.click(ab["x"] + ab["width"] * 0.3, rb["y"] + rb["height"] / 2)
    player_pos(page, ids["approach"])
    back_to(page, r"/compare\?runs=")

    # the overlaid distances: one tooltip row per run
    chart = page.get_by_role("group", name="Дистанция по времени, все прогоны")
    cb = box_of(chart)
    page.mouse.move(cb["x"] + cb["width"] * 0.5, cb["y"] + cb["height"] * 0.5)
    expect(chart.locator("[class*=_tipRow_]")).to_have_count(3)
    page.get_by_role("radio", name="Путь").click()
    expect(page.get_by_role("radio", name="Путь")).to_have_attribute("aria-checked", "true")

    # a chip opens its run; back returns to the same comparison
    page.get_by_role("link", name="demo_approach", exact=True).first.click()
    expect(page).to_have_url(re.compile(rf"/runs/{ids['approach']}$"))
    back_to(page, rf"/compare\?runs={','.join(trio)}$")
    expect(table.locator("tbody tr")).to_have_count(11)
    assert real_errors(app.errors) == []


def test_compare_edit_selection(app, seeded):
    page, ids, names = app.page, seeded["ids"], seeded["names"]
    trio = [ids["cross"], ids["cross_sens"], ids["approach"]]
    app.goto(f"/compare?runs={','.join(trio)}")
    # two quick removals both apply; the survivor keeps its colour slot
    page.get_by_role("button", name="Убрать из сравнения: demo_crossing", exact=True).click()
    page.get_by_role("button", name="Убрать из сравнения: demo_approach", exact=True).click()
    expect(page).to_have_url(re.compile(rf"/compare\?runs=,{ids['cross_sens']}$"))
    # one run left: the chooser lists the others, same recording first
    expect(page.get_by_role("heading", name="Добавьте ещё прогон")).to_be_visible()
    first_tile = page.locator("label").filter(has=page.locator("input[type=checkbox]")).first
    expect(first_tile).to_contain_text("demo_crossing")
    page.get_by_label(f"Сравнить: {names[ids['clear']]}", exact=True).click()  # the grid replaces the chooser
    expect(page.get_by_role("heading", name="Показатели")).to_be_visible()
    expect(page).to_have_url(re.compile(rf"runs={ids['clear']},{ids['cross_sens']}$"))

    # «+ Прогон»: search, pick; at four runs the button goes
    for query, rid in (("approach", ids["approach"]), ("tunnel", ids["jsonl"])):
        page.get_by_role("button", name="Прогон", exact=True).click()
        pop = page.get_by_role("dialog", name="Добавить прогон к сравнению")
        pop.get_by_label("Поиск прогона").fill(query)
        expect(pop.locator("button")).to_have_count(1)
        pop.locator("button").first.click()
        expect(page).to_have_url(re.compile(rid))
    expect(page.locator("table").first.locator("thead th")).to_have_count(5)
    expect(page.get_by_role("button", name="Прогон", exact=True)).to_have_count(0)
    # a results-only run was not processed by the detector: no processing rate to compare
    fps = page.locator("table").first.locator("tbody tr").filter(has_text="Обработка")
    expect(fps.locator("td").last).to_have_text("—")

    # a deleted run in a shared link: its chip says so, the rest is compared
    app.goto(f"/compare?runs={ids['cross']},nosuchrun,{ids['approach']}")
    expect(page.get_by_text("прогон удалён")).to_be_visible()
    expect(page.locator("table").first.locator("thead th")).to_have_count(3)
    assert real_errors(app.errors, allowed=(404,)) == []


# ---------------------------------------------------------------------------------------- 5


@pytest.mark.parametrize("size", [(1600, 1000), (1440, 900), (1366, 768), (1280, 800)])
def test_analysis_pages_fit_the_viewport(app, seeded, size):
    """No horizontal scroll anywhere; no page scroll where the layout promises it (the run page may
    scroll a little below 900 px of height); KPI labels never ellipsize."""
    page, ids = app.page, seeded["ids"]
    w, h = size
    page.set_viewport_size({"width": w, "height": h})
    pages = {
        "/runs": "tbody tr",
        f"/runs/{ids['cross']}": "section[aria-label='3D-вид кадра']",
        f"/compare?runs={ids['cross']},{ids['cross_sens']},{ids['approach']},{ids['jsonl']}": "table",
    }
    for route, ready in pages.items():
        app.goto(route)
        page.locator(ready).first.wait_for()
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        m = page.evaluate(
            """() => {
              const de = document.documentElement;
              const clipped = [...document.querySelectorAll('main [class*=_labelText_]')]
                .filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.textContent);
              return { sh: de.scrollHeight, ch: de.clientHeight, sw: de.scrollWidth, cw: de.clientWidth, clipped };
            }"""
        )
        assert m["sw"] <= m["cw"], (route, size, m)
        assert m["clipped"] == [], (route, size, m["clipped"])
        may_scroll = route.startswith("/runs/") and h < 900
        if not may_scroll:
            assert m["sh"] <= m["ch"] + 1, (route, size, m)
    assert real_errors(app.errors) == []
