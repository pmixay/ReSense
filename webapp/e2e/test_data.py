"""End-to-end flows of the data pages — Главная, Загрузка, Очередь — in a real browser against a
real backend (fixtures in conftest.py). The tests share one backend and run in order: the first
one sees a fresh data dir, the later ones build on the data seeded before them.

  python -m pytest -q webapp/e2e/test_data.py        (~1.5 min; the whole suite: python -m pytest -q webapp/e2e)
"""
from __future__ import annotations

import os
import re
import shutil

import pytest
from e2e_helpers import real_errors, wait_until

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect

LONG = 180_000  # demo generation + processing on a loaded machine


def nav(page, href: str) -> None:
    """Client-side navigation through a visible link of the chrome (no page reload)."""
    page.locator(f"a[href='{href}']:visible").first.click()


def first_stop(decisions: str) -> int:
    i = decisions.find("S")
    return max(0, i)


# ---------------------------------------------------------------------------------------- 1


def test_empty_states(app, backend):
    page, api = app.page, backend.api
    backend.server_root.rmdir()  # the «Папка на сервере» root does not exist yet

    app.goto("/")
    expect(page.get_by_text("Прогонов пока нет")).to_be_visible()
    expect(page.get_by_text("записей пока нет")).to_be_visible()
    expect(page.get_by_text("после первого прогона")).to_be_visible()
    expect(page.get_by_text("онлайн", exact=True)).to_be_visible()
    runs_card = page.locator("section").get_by_role("link", name="Загрузить запись")
    expect(runs_card.first).to_be_visible()

    app.goto("/upload")
    expect(page.get_by_text("запись не выбрана")).to_be_visible()
    expect(page.get_by_role("button", name="Обработать")).to_be_disabled()
    expect(page.get_by_text("Перетащите запись")).to_be_visible()
    # the recordings source: empty, with calls to action that switch the source
    page.get_by_role("radio", name="Записи на сервере").click()
    expect(page.get_by_text("Записей пока нет")).to_be_visible()
    page.get_by_role("button", name="Создать демо").click()
    expect(page).to_have_url(re.compile(r"source=demo"))
    expect(page.get_by_role("radio", name=re.compile("^Приближение"))).to_have_attribute("aria-checked", "true")

    # the server folder is missing: its path and «Проверить снова»; once created: an empty folder
    page.get_by_role("radio", name="Папка на сервере").click()
    expect(page.get_by_text("Папка данных не найдена")).to_be_visible()
    expect(page.get_by_text(str(backend.server_root), exact=True)).to_be_visible()
    backend.server_root.mkdir()
    try:
        page.get_by_role("button", name="Проверить снова").click(timeout=4000)
    except pw.Error:
        pass  # the 5 s system poll noticed the new folder first
    expect(page.get_by_text("Папка пуста")).to_be_visible()

    app.goto("/queue")
    expect(page.get_by_text("Детектор свободен")).to_be_visible()
    expect(page.get_by_text("Очередь пуста")).to_be_visible()
    expect(page.get_by_text("Готовых задач нет")).to_be_visible()
    expect(page.get_by_role("button", name="Убрать готовые")).to_be_disabled()
    assert api.get("/recordings") == []
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 2


def test_overview_demo_to_queue_and_run(app, backend):
    """«Демо» on Главная: generate (live progress) → queued → /queue → done → the run's page;
    then Главная shows the run: table row, verdict, KPI tiles, the player link at the first STOP."""
    page, api = app.page, backend.api
    app.goto("/")
    page.get_by_role("button", name="Демо", exact=True).click()
    expect(page.get_by_text("создаём демо")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/queue$"), timeout=LONG)

    jobs = api.get("/jobs")
    assert len(jobs) == 1 and jobs[0]["recording_name"] == "demo_approach"
    job = api.wait_job(jobs[0]["id"])
    assert job["status"] == "done", job
    run_id = job["run_id"]
    open_run = page.get_by_role("link", name="Открыть прогон demo_approach")
    expect(open_run).to_be_visible(timeout=30_000)
    expect(page.get_by_text("Последняя задача")).to_be_visible()
    expect(page.get_by_role("link", name="Открыть в плеере")).to_have_attribute("href", f"/player/{run_id}")
    open_run.click()
    expect(page).to_have_url(re.compile(rf"/runs/{run_id}$"))
    page.go_back()
    expect(page).to_have_url(re.compile(r"/queue$"))

    run = api.get(f"/runs/{run_id}")
    app.goto("/")
    row = page.locator("tbody tr", has_text="demo_approach")
    expect(row).to_have_count(1)
    expect(row.get_by_text("препятствие")).to_be_visible()
    expect(row.get_by_text(re.compile(r"верно|ложный СТОП|объект пропущен"))).to_be_visible()
    expect(page.get_by_text("после первого прогона")).to_have_count(0)
    expect(page.get_by_text("последняя:")).to_be_visible()
    pos = first_stop(run["summary"]["decisions"])
    expect(page.locator(f'a[href="/player/{run_id}?pos={pos}"]')).to_be_visible()
    expect(page.get_by_role("link", name="Открыть плеер")).to_have_attribute("href", f"/player/{run_id}")
    row.click()
    expect(page).to_have_url(re.compile(rf"/runs/{run_id}$"))
    page.go_back()
    expect(page).to_have_url(re.compile(r"/$"))
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 3


def test_upload_files_labels_and_process(app, backend, tmp_path):
    """Файл: an unknown file (rejected by the server in Russian), a results .jsonl (upload →
    detected recording), a bad and a good labels file, «Обработать» → /queue → done."""
    page, api = app.page, backend.api
    run = api.get("/runs")[0]
    jsonl = tmp_path / "approach_results.jsonl"
    jsonl.write_text(api.get(f"/runs/{run['id']}/download/results.jsonl"), encoding="utf-8")
    notes = tmp_path / "notes.txt"
    notes.write_text("hello", encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2]", encoding="utf-8")
    demo_rec = next(r for r in api.get("/recordings") if r["name"] == "demo_approach")
    good = next((backend.data_dir / "recordings" / demo_rec["id"]).glob("*/ground_truth.json"))

    app.goto("/upload")
    files = page.locator('input[type=file][accept^=".zip"]')
    files.set_input_files(str(notes))
    expect(page.get_by_text("формат не распознан")).to_be_visible()
    page.get_by_role("button", name="Всё равно загрузить").click()
    alert = page.get_by_role("alert").filter(has_text="Запись не принята")
    expect(alert).to_be_visible()
    expect(alert).to_contain_text("не найдено")
    page.get_by_role("button", name="Убрать", exact=True).click()
    expect(alert).to_have_count(0)

    # a big upload over a slow link: live bytes / speed / time left, then cancelled
    big = tmp_path / "big_ride.zip"
    big.write_bytes(os.urandom(24 * 1024 * 1024))
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.emulateNetworkConditions",
             {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": 2 * 1024 * 1024})
    files.set_input_files(str(big))
    expect(page.get_by_text("big_ride")).to_be_visible()
    expect(page.get_by_text(re.compile(r"из\s24\sМБ"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"^осталось"))).to_be_visible()
    # the upload keeps going on another page (Главная shows it) and is still there on return
    nav(page, "/")
    expect(page.get_by_role("link", name=re.compile("загружаем big_ride"))).to_be_visible()
    page.go_back()
    expect(page.get_by_text(re.compile(r"из\s24\sМБ"))).to_be_visible()
    page.get_by_role("button", name="Отменить загрузку").click()
    expect(page.get_by_text("big_ride")).to_have_count(0)
    cdp.send("Network.emulateNetworkConditions",
             {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
    uploads = backend.data_dir / "uploads"
    wait_until(lambda: not uploads.is_dir() or not any(uploads.iterdir()))  # the staging area is gone

    files.set_input_files(str(jsonl))
    expect(page.get_by_text("проверено")).to_be_visible(timeout=60_000)
    expect(page).to_have_url(re.compile(r"rec=\w+"))
    expect(page.get_by_text("только результаты: без облаков точек")).to_be_visible()
    expect(page.get_by_text("без разметки", exact=True)).to_be_visible()
    assert next(r for r in api.get("/recordings") if r["name"] == "approach_results")["kind"] == "jsonl"
    evaluate = page.get_by_role("switch", name="Оценка по разметке")
    expect(evaluate).to_be_disabled()
    expect(page.get_by_label("Топик облака")).to_be_disabled()

    labels_input = page.locator('input[type=file][accept^=".json"]')
    labels_input.set_input_files(str(bad))
    expect(page.get_by_role("alert").filter(has_text="JSON-объектом")).to_be_visible()
    labels_input.set_input_files(str(good))
    expect(page.get_by_text("разметка есть")).to_be_visible()
    expect(evaluate).to_be_enabled()
    expect(evaluate).to_have_attribute("aria-checked", "true")

    page.get_by_role("button", name="Обработать").click()
    expect(page).to_have_url(re.compile(r"/queue$"))
    job = next(j for j in api.get("/jobs") if j["recording_name"] == "approach_results")
    assert api.wait_job(job["id"])["status"] == "done"
    expect(page.get_by_role("link", name="Открыть прогон approach_results")).to_be_visible(timeout=30_000)
    assert real_errors(app.errors, allowed=(422,)) == []


# ---------------------------------------------------------------------------------------- 4


def test_server_folder_preset_and_options(app, backend):
    """Папка на сервере: breadcrumbs, keyboard, a bag registered in place, then processed with
    another preset, frame step 2 and no clouds."""
    page, api = app.page, backend.api
    demo_rec = next(r for r in api.get("/recordings") if r["name"] == "demo_approach")
    bag = next(p for p in (backend.data_dir / "recordings" / demo_rec["id"]).iterdir() if p.is_dir())
    (backend.server_root / "rides").mkdir()
    shutil.copytree(bag, backend.server_root / "rides" / "ride_one", copy_function=os.link)
    preset = api.post("/presets", {"name": "Чувствительный", "overrides": {}})

    app.goto("/upload?source=server")
    expect(page.get_by_role("radio", name="Папка на сервере")).to_have_attribute("aria-checked", "true")
    rides = page.get_by_role("button", name=re.compile("^rides"))
    rides.dblclick()
    ride = page.get_by_role("button", name=re.compile("^ride_one"))
    expect(ride).to_contain_text("rosbag2")
    expect(ride).to_contain_text(str(demo_rec["n_frames"]))
    ride.focus()
    page.keyboard.press("Backspace")  # up to the root
    expect(rides).to_be_visible()
    rides.focus()
    page.keyboard.press("Enter")  # opens the folder
    expect(ride).to_be_visible()
    use = page.get_by_role("button", name="Использовать запись")
    ride.click()
    expect(use).to_be_enabled()
    use.click()
    expect(page.get_by_text("проверено")).to_be_visible()
    rec = next(r for r in api.get("/recordings") if r["source"] == "server")
    expect(page).to_have_url(re.compile(rf"rec={rec['id']}"))
    expect(page.get_by_text("папка на сервере").first).to_be_visible()

    page.get_by_label("Пресет").select_option(preset["id"])
    page.get_by_role("button", name="Шаг кадров: больше").click()
    page.get_by_role("switch", name=re.compile("Облака")).click()
    half = (rec["n_frames"] + 1) // 2
    expect(page.get_by_text(re.compile(rf"^{half}\s+кадр"))).to_be_visible()
    page.get_by_role("button", name="Обработать").click()
    expect(page).to_have_url(re.compile(r"/queue$"))
    job = next(j for j in api.get("/jobs") if j["recording_id"] == rec["id"])
    assert job["preset_id"] == preset["id"]
    assert job["options"]["every"] == 2 and job["options"]["clouds"] is False
    done = api.wait_job(job["id"])
    assert done["status"] == "done", done
    run = api.get(f"/runs/{done['run_id']}")
    assert run["preset"]["name"] == "Чувствительный" and run["has_clouds"] is False
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 5


def test_demo_source_survives_navigation(app, backend):
    """Демо-запись: scenario, duration, live progress that is still there after visiting another
    page; the new recording becomes the chosen one."""
    page, api = app.page, backend.api
    app.goto("/upload?source=demo")
    page.get_by_role("radio", name=re.compile("^Приближение")).focus()
    page.keyboard.press("ArrowRight")  # a radio group: arrows move the choice
    expect(page.get_by_role("radio", name=re.compile("^Пересечение пути"))).to_have_attribute("aria-checked", "true")
    minus = page.get_by_role("button", name="Длительность демо-записи: меньше")
    minus.click()
    minus.click()
    expect(page.get_by_role("spinbutton", name="Длительность демо-записи")).to_have_value("5")
    expect(minus).to_be_disabled()
    expect(page.get_by_text(re.compile(r"^≈\s165\sМБ$"))).to_be_visible()
    page.get_by_role("button", name="Создать демо").click()
    expect(page.get_by_text("Создаём «Пересечение пути»")).to_be_visible()

    nav(page, "/queue")
    expect(page).to_have_url(re.compile(r"/queue$"))
    page.go_back()
    expect(page).to_have_url(re.compile(r"/upload\?source=demo"))
    expect(page.get_by_text("проверено")).to_be_visible(timeout=LONG)
    rec = next(r for r in api.get("/recordings") if r["name"] == "demo_crossing")
    assert rec["duration_s"] < 6 and rec["labels"]["available"]
    expect(page).to_have_url(re.compile(rf"rec={rec['id']}"))
    expect(page.get_by_text("синтетическая").first).to_be_visible()
    expect(page.get_by_text("разметка есть")).to_be_visible()
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 5b


def test_folder_upload_and_drop(app, backend, tmp_path):
    """«Выбрать папку» with a whole rosbag2 folder (webkitdirectory), and a file dropped on the zone."""
    page, api = app.page, backend.api
    crossing = next(r for r in api.get("/recordings") if r["name"] == "demo_crossing")
    bag = next(p for p in (backend.data_dir / "recordings" / crossing["id"]).iterdir() if p.is_dir())
    folder = tmp_path / "tunnel_ride"
    shutil.copytree(bag, folder, copy_function=os.link)

    app.goto("/upload")
    page.locator("input[type=file][webkitdirectory]").set_input_files(str(folder))
    expect(page.get_by_text("проверено")).to_be_visible(timeout=120_000)
    rec = next(r for r in api.get("/recordings") if r["name"] == "tunnel_ride")
    assert rec["kind"] == "rosbag2" and rec["source"] == "upload" and rec["n_frames"] == crossing["n_frames"]
    assert rec["labels"]["available"]  # the demo's ground_truth.json came with the folder
    expect(page).to_have_url(re.compile(rf"rec={rec['id']}"))
    expect(page.locator("b", has_text="/lidar_points")).to_be_visible()  # the detected topic
    expect(page.get_by_label("Топик облака").locator("option")).to_have_count(2)  # авто + /lidar_points

    run = api.get("/runs")[0]
    text = api.get(f"/runs/{run['id']}/download/results.jsonl")
    heading = page.get_by_role("heading", name="Перетащите запись")
    heading.evaluate("""(el, text) => {
        window.__dt = new DataTransfer();
        window.__dt.items.add(new File([text], 'dropped_results.jsonl'));
        el.dispatchEvent(new DragEvent('dragenter', { bubbles: true, cancelable: true, dataTransfer: window.__dt }));
    }""", text)
    drop_here = page.get_by_role("heading", name="Отпустите здесь")
    expect(drop_here).to_be_visible()
    drop_here.evaluate("""el => el.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: window.__dt }))""")
    expect(page.get_by_role("heading", name="Перетащите запись")).to_be_visible()
    expect(page.get_by_text("dropped_results", exact=True)).to_be_visible(timeout=60_000)
    wait_until(lambda: any(r["name"] == "dropped_results" for r in api.get("/recordings")))
    assert real_errors(app.errors) == []


# ---------------------------------------------------------------------------------------- 6


def test_queue_cancel_retry_log_and_clear(app, backend):
    """Очередь: the running job (line, %, strip, cancel), waiting jobs (position, cancel), retry,
    the log dialog (Escape), a retry refused by the server, «Убрать готовые»."""
    page, api = app.page, backend.api
    api.wait_idle()
    approach = next(r for r in api.get("/recordings") if r["name"] == "demo_approach")
    crossing = next(r for r in api.get("/recordings") if r["name"] == "demo_crossing")
    slow = {"cloud_points": 120000}
    running = api.job(approach["id"], options=slow)
    second = api.job(crossing["id"])
    third = api.job(crossing["id"], options={"every": 2})

    app.goto("/queue")
    expect(page.get_by_text("В работе", exact=True)).to_be_visible()
    expect(page.get_by_text("детектор", exact=True)).to_be_visible()
    waiting = page.get_by_label(re.compile("^Место в очереди"))
    expect(waiting).to_have_count(2)
    expect(page.get_by_label("Место в очереди: 1")).to_be_visible()

    # cancel the last waiting job (asks once)
    page.get_by_role("button", name="Убрать из очереди").last.click()
    page.get_by_role("button", name="Убрать?").click()
    expect(waiting).to_have_count(1)
    assert api.get(f"/jobs/{third['id']}")["status"] == "cancelled"

    # cancel the running job
    page.get_by_role("button", name="Отменить обработку").click()
    page.get_by_role("button", name="Отменить?").click()
    assert api.wait_job(running["id"], timeout=30)["status"] == "cancelled"

    # the log of a cancelled job, closed with Escape
    page.get_by_role("button", name="Журнал обработки").first.click()
    dialog = page.get_by_role("dialog", name="Журнал обработки")
    expect(dialog).to_be_visible()
    expect(dialog.locator("pre, :text('Журнал пуст')").first).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)

    # retry a cancelled job: a new job of the same recording
    n_jobs = len(api.get("/jobs"))
    page.get_by_role("button", name="Повторить", exact=True).last.click()  # the oldest: «third»
    wait_until(lambda: len(api.get("/jobs")) == n_jobs + 1)
    api.wait_idle()
    assert api.get(f"/jobs/{second['id']}")["status"] == "done"

    # a retry the server refuses (its recording was deleted): the Russian detail is shown
    gone = api.demo("clear", 5)
    failed_job = api.job(gone["id"])
    api.post(f"/jobs/{failed_job['id']}/cancel")
    api.delete(f"/recordings/{gone['id']}")
    page.reload()
    row = page.locator("div", has=page.get_by_text("demo_clear", exact=True)).filter(
        has=page.get_by_role("button", name="Повторить", exact=True)).last
    row.get_by_role("button", name="Повторить", exact=True).click()
    expect(page.get_by_role("alert").filter(has_text="Запись этой задачи удалена")).to_be_visible()

    page.get_by_role("button", name="Убрать готовые").click()
    expect(page.get_by_text("Готовых задач нет")).to_be_visible()
    expect(page.get_by_text("Детектор свободен")).to_be_visible()
    assert real_errors(app.errors, allowed=(409,)) == []


# ---------------------------------------------------------------------------------------- 7


def test_recordings_list_deep_links_and_errors(app, backend):
    """Записи: pick / delete a recording; ?rec= deep links (a stale one is dropped); a job for a
    recording deleted meanwhile shows the server's error; the browser back button."""
    page, api = app.page, backend.api
    recs = api.get("/recordings")
    crossing = next(r for r in recs if r["name"] == "demo_crossing")

    app.goto(f"/upload?source=list&rec={crossing['id']}")
    pick = page.get_by_role("button", name=re.compile("^demo_crossing"))
    expect(pick).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("link", name=re.compile(r"^Скачать demo_crossing"))).to_have_attribute(
        "href", f"/api/recordings/{crossing['id']}/download")

    app.goto("/upload?rec=nosuchrecording")
    expect(page).not_to_have_url(re.compile("rec="))
    expect(page.get_by_text("запись не выбрана")).to_be_visible()

    # ?preset= (the «Обработать с этим пресетом» link of Параметры) preselects the preset
    preset = next(p for p in api.get("/presets") if not p["builtin"])
    app.goto(f"/upload?preset={preset['id']}")
    expect(page.get_by_label("Пресет")).to_have_value(preset["id"])
    page.get_by_label("Пресет").select_option("standard")
    expect(page).not_to_have_url(re.compile("preset="))
    app.goto("/upload?preset=nosuchpreset")
    expect(page).not_to_have_url(re.compile("preset="))
    expect(page.get_by_label("Пресет")).to_have_value("standard")

    # a recording deleted behind the page's back: «Обработать» shows the server's answer
    victim = api.demo("clear", 5)
    app.goto(f"/upload?source=list&rec={victim['id']}")
    expect(page.get_by_role("button", name=re.compile("^demo_clear")).first).to_be_visible()
    api.delete(f"/recordings/{victim['id']}")
    page.get_by_role("button", name="Обработать").click()
    expect(page.get_by_role("alert").filter(has_text="Запись не найдена")).to_be_visible()

    # delete from the list (asks once)
    page.reload()
    server_rec = next(r for r in api.get("/recordings") if r["source"] == "server")
    row = page.locator("div", has=page.get_by_role("button", name=re.compile(f"^{server_rec['name']}"))).last
    row.get_by_role("button", name=re.compile("Убрать из списка")).click()
    page.get_by_role("button", name="Убрать?").click()
    expect(page.get_by_role("button", name=re.compile(f"^{server_rec['name']}"))).to_have_count(0)
    assert all(r["id"] != server_rec["id"] for r in api.get("/recordings"))
    assert (backend.server_root / "rides" / "ride_one").is_dir()  # server files stay

    # the back button walks the client-side history
    nav(page, "/queue")
    expect(page).to_have_url(re.compile(r"/queue$"))
    page.go_back()
    expect(page).to_have_url(re.compile(r"/upload"))
    assert real_errors(app.errors, allowed=(404,)) == []


# ---------------------------------------------------------------------------------------- 8


@pytest.mark.parametrize("size", [(1600, 1000), (1440, 900), (1280, 800)])
def test_pages_fit_the_viewport(app, backend, size):
    """No page scroll at the three target sizes (long lists scroll inside their cards)."""
    page = app.page
    page.set_viewport_size({"width": size[0], "height": size[1]})
    for route, ready in (("/", "Последние прогоны"), ("/upload", "Источник"), ("/queue", "Завершено")):
        app.goto(route)
        expect(page.get_by_text(ready, exact=True).first).to_be_visible()
        page.wait_for_timeout(300)
        sh, ih, sw, iw = page.evaluate(
            "[document.scrollingElement.scrollHeight, innerHeight, document.scrollingElement.scrollWidth, innerWidth]")
        assert sh <= ih + 1 and sw <= iw + 1, (route, size, sh, ih, sw, iw)
    assert real_errors(app.errors) == []
