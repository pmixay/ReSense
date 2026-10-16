# ReSense web — backend

FastAPI backend of the jury prototype: uploads and server folders, a job queue that runs the
sealed detector (`resense`) in a worker subprocess, results (runs) with charts, frame paging,
decimated point clouds for the 3D player, downloads, detector presets and a live replay
WebSocket. The HTTP contract is [`../API.md`](../API.md).

## Install and run

```bash
pip install -e ".[dev]" -e ros2_ws/src/resense_ros -e "webapp/backend[dev]"
python -m resense_web                       # http://0.0.0.0:8080 (serves webapp/frontend/dist when built)
python -m resense_web --port 8000 --reload  # development, behind Vite on :5173 (proxies /api)
cd webapp/backend && python -m pytest -q    # tests (~50 s; they write real bags, need open3d + rosbags)
```

One command for the whole prototype (builds the frontend when `dist/` is missing or older than the sources, installs nothing
unless `--install`): `scripts/run_webapp.sh` — http://localhost:8080/, `RESENSE_DATA` defaults to
`/data/for_hackathon` when it exists.

`resense-web` declares both `resense` and `resense-ros>=1.0.0` as dependencies.
The existing `ros2_ws/src/resense_ros` package supplies the shared pure-Python
decision policy. Importing its package / policy requires no `rclpy`, ROS node or
launch stack; running the ROS node still requires ROS. `--install` and CI install
all three local projects together so pip can resolve their local distributions.

### Local wheels, outside the checkout

Build wheels for the target Python/platform, then install into a fresh venv:

```bash
# In the checkout, in a build environment with pip, setuptools and wheel:
python -m pip install wheel
python -m pip wheel --no-deps --wheel-dir wheelhouse . ./ros2_ws/src/resense_ros ./webapp/backend

# Use absolute paths when taking the wheelhouse to another directory/machine.
python -m venv /tmp/resense-web-env
/tmp/resense-web-env/bin/python -m pip install --find-links /absolute/path/wheelhouse \
  /absolute/path/wheelhouse/resense-*.whl /absolute/path/wheelhouse/resense_web-*.whl
/tmp/resense-web-env/bin/python -m pip check
cd /tmp
/tmp/resense-web-env/bin/python -I -c 'from resense_web.decision import decision_of; print(decision_of({"warning": True}))'
/tmp/resense-web-env/bin/python -I -m resense_web --help
```

The backend dependency resolves `resense_ros-*.whl` from that wheelhouse. Ordinary
third-party dependencies still need an index/cache; for an offline install,
download their target-platform wheels into the wheelhouse first and add
`--no-index`. A source-only namespace fallback is not a wheel dependency. Use a
fresh venv, or explicitly reinstall the current local ROS wheel if an older
same-version overlay lacks `resense_ros.decision_policy`.

`python scripts/check_webapp_wheels.py` automates building source copies and a
fresh non-editable venv. It checks the wheel's declared dependency, lets pip
resolve the ROS wheel, runs `pip check`, imports the actual backend application
and policy with the source namespace unavailable, forbids node/ROS imports, and
checks the installed CLI. CI runs it in the `webapp` job.

## Environment

| variable | default | meaning |
|---|---|---|
| `RESENSE_WEB_DATA` | `<repo>/webapp/data` | database, uploads, recordings, runs |
| `RESENSE_DATA` | `/data` | server-folder root for «Папка на сервере» (read-only, sandboxed) |
| `RESENSE_WEB_MAX_UPLOAD_GB` | `100` | per upload staging area (a zip also after unpacking) |
| `RESENSE_WEB_UPLOAD_TTL_H` | `72` | an unfinished (resumable) upload is kept this long after its last write |
| `RESENSE_WEB_KEEPALIVE_S` | `130` | idle connection timeout (`--timeout-keep-alive`); behind a reverse proxy keep it above the proxy's idle timeout (Caddy 2 min), else the proxy can hit a connection the backend is closing and answer 502 |
| `RESENSE_WEB_HOST` / `RESENSE_WEB_PORT` | `0.0.0.0` / `8080` | bind |
| `RESENSE_WEB_STATIC` | `webapp/frontend/dist` | the built frontend (optional override) |

## Data layout (`RESENSE_WEB_DATA`)

```
resense_web.sqlite          recordings, jobs, runs, presets (sqlite3, WAL)
uploads/<id>/files/...      staging areas of unfinished uploads: finished files ...
uploads/<id>/parts/...      ... and chunked files in progress (<key>.part written in place, <key>.json
                            the received-chunk bitmap); removed RESENSE_WEB_UPLOAD_TTL_H after the last write
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
  compression-ratio guards), path sanitizing and the sandboxed folder browser. Uploads are
  resumable: big files arrive in chunks (any order, in parallel, CRC-32 checked, optionally gzip,
  each flushed to disk before it counts), `GET /api/uploads/{id}` says what is missing, and
  finalize (unpacking, detection, the move into `recordings/`) runs in a background thread with
  its stage; writes, finalize and delete of one area exclude each other.
- The worker reads frames one step ahead in a background thread (`worker.prefetch`): reading the
  bag and decoding the clouds overlap with the detector (~20-30 % more frames per second).
- `demo.py`, `params.py`, `evaluation.py`, `live.py` — synthetic demo bags, the tunable parameter
  schema, scoring against labels, the live replay (see their docstrings).
- Tests: unit tests per module, the worker end to end on small real bags (`test_runs.py`), and
  `test_integration.py` — the real chain without stand-ins: demo endpoint → job → run with clouds,
  summary and scores → the live WebSocket, the demo zip uploaded again, a cancelled worker.
