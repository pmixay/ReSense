# ReSense web — backend

FastAPI backend of the jury prototype: uploads and server folders, a job queue that runs the
sealed detector (`resense`) in a worker subprocess, results (runs) with charts, frame paging,
decimated point clouds for the 3D player, downloads, detector presets and a live replay
WebSocket. The HTTP contract is [`../API.md`](../API.md).

## Install and run

```bash
pip install -e ".[dev]"                     # from the repository root: the detector (resense)
pip install -e webapp/backend               # this package: resense-web
python -m resense_web                       # http://0.0.0.0:8080 (serves webapp/frontend/dist when built)
python -m resense_web --port 8000 --reload  # development, behind Vite on :5173 (proxies /api)
cd webapp/backend && python -m pytest -q    # tests (~50 s; they write real bags, need open3d + rosbags)
```

One command for the whole prototype (builds the frontend when `dist/` is missing, installs nothing
unless `--install`): `scripts/run_webapp.sh` — http://localhost:8080/, `RESENSE_DATA` defaults to
`/data/for_hackathon` when it exists.

## Environment

| variable | default | meaning |
|---|---|---|
| `RESENSE_WEB_DATA` | `<repo>/webapp/data` | database, uploads, recordings, runs |
| `RESENSE_DATA` | `/data` | server-folder root for «Папка на сервере» (read-only, sandboxed) |
| `RESENSE_WEB_MAX_UPLOAD_GB` | `100` | per upload staging area (a zip also after unpacking) |
| `RESENSE_WEB_HOST` / `RESENSE_WEB_PORT` | `0.0.0.0` / `8080` | bind |
| `RESENSE_WEB_STATIC` | `webapp/frontend/dist` | the built frontend (optional override) |

## Data layout (`RESENSE_WEB_DATA`)

```
resense_web.sqlite          recordings, jobs, runs, presets (sqlite3, WAL)
uploads/<id>/files/...      staging areas of unfinished uploads (removed after 24 h)
recordings/<id>/            uploaded and demo recordings, uploaded labels.json (a demo bag carries its
                            ground_truth.json, which is used as labels wherever the bag goes)
jobs/<id>/                  spec.json (from the manager), progress.json, result.json, worker.log
runs/<id>/                  results.jsonl + results.idx (line offsets), clouds.bin + clouds.json (RSC1),
                            series.json, summary.json (RunSummary, episodes, events), worker.log
cache/                      generated demo bag zips
```

## How it fits together

- `app.py` — `create_app()`: routers under `/api`, the live WebSocket, CORS for Vite, GZip for
  JSON (not for clouds / zips), Russian error bodies, the SPA fallback. Run one process only (the
  job queue lives in it): no `--workers`.
- `jobs.py` — the queue: one background thread, exactly one `python -m resense_web.worker <job_id>`
  at a time (own process group; cancel = SIGTERM, then SIGKILL). Jobs left `running` by a dead
  server are failed at start-up («прервано перезапуском сервера») and the queue continues.
- `worker.py` — builds the config from the preset (`params.build_config`), reads the frames
  (`resense.io` for rosbag2 / npy caches, own reader for `.npz` and plain arrays), runs
  `Detector.process`, writes the run files, scores against labels (`evaluation`), writes the
  summary. A `jsonl` recording (results only) gets its decisions and summary recomputed.
- Pure, unit-tested helpers: `decision.py` (the node's rule), `summary.py` (series, episodes,
  events, RunSummary), `clouds.py` (RSC1, point flags and sampling), `results.py` (line index).
- `probe.py` / `uploads.py` / `serverfiles.py` — input detection (rosbags for sqlite3 and mcap,
  `.npy/.npz` folders, results `.jsonl`), safe zip extraction (zip-slip, symlink, size and
  compression-ratio guards), path sanitizing and the sandboxed folder browser.
- `demo.py`, `params.py`, `evaluation.py`, `live.py` — synthetic demo bags, the tunable parameter
  schema, scoring against labels, the live replay (see their docstrings).
- Tests: unit tests per module, the worker end to end on small real bags (`test_runs.py`), and
  `test_integration.py` — the real chain without stand-ins: demo endpoint → job → run with clouds,
  summary and scores → the live WebSocket, the demo zip uploaded again, a cancelled worker.
