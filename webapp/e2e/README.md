# ReSense web — browser end-to-end tests

Real flows of every page in headless Chromium against a real backend running the sealed detector:
no mocks, except where a test provokes a failure on purpose (`page.route` holds, fails or aborts a
backend call). About 4–5 minutes for the whole suite on 4 cores.

```bash
# from the repository root; the interpreter needs resense_web, pytest, playwright and websockets
/root/.venvs/resense/bin/python -m pytest -q webapp/e2e              # everything
/root/.venvs/resense/bin/python -m pytest -q webapp/e2e/test_player.py -x
```

## How it runs

- **One production build** for the session (`dist` fixture): `WEBAPP_DIST` when set, else
  `webapp/frontend/dist` when it is newer than every frontend source, else a fresh `vite build`
  into a temporary folder (the checkout's `dist/` is never overwritten). No Vite dev server.
- **One backend per module** (`backend` fixture): `python -m resense_web` on a free port serves that
  build and the API on one origin (`RESENSE_WEB_STATIC`), with its own empty data dir
  (`RESENSE_WEB_DATA`) and server folder (`RESENSE_DATA`). The first test of each module checks
  the empty states of its pages; the next ones seed what they need through `backend.api` (short
  demo bags, jobs, presets, `.jsonl` uploads) and run in file order, building on each other. The
  data dir is deleted when the module ends (`WEBAPP_E2E_KEEP=1` keeps it); `backend.log` stays in
  pytest's temp dir.
- **One browser** for the session (SwiftShader WebGL for the 3D views; `PW_CHROMIUM` overrides the
  executable) and a fresh context per test (`app` fixture, 1600×1000). Every test ends with
  `assert real_errors(app.errors, …) == []`: zero console errors apart from the 4xx / 5xx or
  refused connections the test itself provoked.

| module | pages | what it covers |
|---|---|---|
| `test_data.py` | Главная, Загрузка, Очередь | empty stand, «Демо» → queue → run, file / folder / drag-and-drop uploads (throttled upload kept across pages, cancel), labels, server folder + preset + options, demo source, queue cancel / retry / log / clear, deep links, no page scroll at 1600×1000 / 1440×900 / 1280×800 |
| `test_analysis.py` | Прогоны, Прогон, Сравнение | search / filters / sort in the URL, selection → compare, rename / delete with backend errors, decision strip, chart and events → player, downloads, loading / offline, compare table / strips / chart / «Что изменилось», layout at four sizes |
| `test_player.py` | Плеер | picker, autoplay and every shortcut, URL without history spam, events / scrubber / loop, values against the API, run menu and back / forward, schematic (`.jsonl`) and FAULT runs, loading and backend errors, fullscreen and orbit, small viewports |
| `test_system.py` | Прямой эфир, Параметры, О системе | live replay transport over the real WebSocket, errors (run deleted → 4404), ROS 2 mode against a rosbridge v2 stand-in (stale data, reconnect), the preset editor end to end (409 inline, create / save / delete, «Обработать с этим пресетом»), About with copy and the stand's versions |

Shared code: `conftest.py` (fixtures, the `Api` client with seeding helpers) and `e2e_helpers.py`
(`real_errors`, `api_route`, `Held`, `wait_until`, `free_port`).

Writing a test: prefer roles and accessible names (`get_by_role`, `get_by_label`) — the pages are
built for them; seed through `backend.api`, keep demo bags short (~33 MB and ~1 s per simulated
second), and wait with `expect(...)`, never with fixed sleeps.
