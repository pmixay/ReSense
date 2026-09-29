# ReSense web — HTTP API contract

> Source of truth for `webapp/backend` (FastAPI) and `webapp/frontend` (React). Every path is under
> `/api`. JSON uses `snake_case`. Times are ISO 8601 UTC strings (`created_at`) or seconds
> (`t`, `duration_s`). Distances in metres, latencies in milliseconds. Errors:
> `{"detail": "<Russian, short, user-facing message>"}` with a 4xx/5xx status — always a string, also
> for request validation errors (422, e.g. `"Некорректный запрос: «recording_id» обязательное поле"`).
> Interactive docs: `/api/docs`, schema: `/api/openapi.json`.

Decisions per frame are one of `GO | CAUTION | STOP | FAULT` (the ROS node's rule:
`STOP` if `obstacle`; else `FAULT` if `health.level == "error"`; else `CAUTION` if `warning` or
`health.decision_level` (fallback `health.level`) is `"warn"`; else `GO`). A **decision string** encodes
one letter per processed frame: `G`, `C`, `S`, `F`.

## Entities

```ts
type Decision = "GO" | "CAUTION" | "STOP" | "FAULT"

interface Recording {
  id: string                       // short url-safe id
  name: string                     // "doubleT_obstacle"
  kind: "rosbag2" | "npy" | "jsonl" // what the frames come from (jsonl = results only, no clouds)
  source: "upload" | "server" | "demo"
  path: string                     // absolute path on the server (display only)
  size_bytes: number
  n_frames: number | null          // PointCloud2 messages (or files / lines)
  duration_s: number | null
  topics: { name: string, type: string, count: number }[]
  default_topic: string | null     // the PointCloud2 topic the worker will read
  labels: { available: boolean, source: "builtin" | "upload" | null, name: string | null }
                                   // "upload": PUT …/labels. "builtin": a ground_truth.json next to the
                                   // bag (a demo's ground truth, also inside its re-uploaded zip or a copy
                                   // in the server folder; name "<rec> (эталон демо)" or
                                   // "ground_truth.json (рядом с записью)"), else the repo's
                                   // labels/*.json whose _meta.bag is the recording name
  created_at: string
  warnings: string[]               // e.g. "нет поля ring" — Russian, short
}

interface JobOptions {             // unknown keys -> 422
  topic?: string | null            // null = auto (first PointCloud2 topic / the default_topic)
  every?: number                   // frame step, 1..10000 (default 1)
  start?: number                   // first frame index (default 0; 422 when beyond the recording)
  limit?: number | null            // max frames to process (default all), >= 1
  clouds?: boolean                 // store decimated point clouds for the 3D player (default true)
  cloud_points?: number            // points per stored cloud (default 30000, 5000..120000)
  ego_speed?: number | null        // m/s given to Detector.process (default null), 0..50
  evaluate?: boolean               // score against labels when available (default true)
}                                  // a "jsonl" recording always runs with clouds=false, topic=null

interface JobProgress {
  frames_done: number
  frames_total: number | null
  fps: number | null               // processed frames per wall second (moving average)
  eta_s: number | null
  stage: "queued" | "opening" | "processing" | "evaluating" | "finalizing" | "done"
  stage_ms: Record<string, number> // mean timing_ms of the last 20 frames, keys as the detector's timing_ms
  decisions: string                // decision string so far
  last: { frame: number, decision: Decision, nearest_distance: number | null } | null
}                                  // finished / failed / cancelled jobs keep their last snapshot

interface Job {
  id: string
  recording_id: string
  recording_name: string
  preset_id: string
  preset_name: string
  options: JobOptions              // with defaults filled in
  status: "queued" | "running" | "done" | "failed" | "cancelled"
  position: number | null          // 1-based place in the queue while queued
  progress: JobProgress
  error: string | null
  run_id: string | null            // set only when status == "done"
  created_at: string
  started_at: string | null
  finished_at: string | null
}

interface Episode {                // a maximal block of consecutive frames with one decision
  decision: Decision
  first_frame: number              // bag frame index
  last_frame: number
  t0: number                       // seconds from the first processed frame
  t1: number
  n_frames: number
  distance_min: number | null      // nearest_distance min/max over the block (STOP only)
  distance_max: number | null
}

interface RunSummary {
  n_frames: number
  duration_s: number
  counts: Record<Decision, number>
  decisions: string                // decision string, one letter per processed frame
  stop_episodes: number
  first_stop: { frame: number, t: number, distance: number | null } | null
  distance_min: number | null      // over STOP frames
  distance_max: number | null
  latency_ms: { p50: number, p95: number, max: number }   // detector timing_ms.total
  processing_fps: number           // wall-clock throughput of the job
  clear_distance_median: number | null
  visibility_median: number | null
  eval: EvalSummary | null         // when labels were available and evaluate=true (null if scoring failed)
}

interface EvalSummary {            // from resense.metrics.Evaluation.summary(), plus these headline keys
                                   // (scored like `resense eval`: frames missing from the label file are empty)
  labels_name: string              // = Recording.labels.name at the time of the job
  frames_labelled: number
  frames_with_object_in_gauge: number
  frames_detected: number          // labelled in-gauge frames that got STOP
  recall: number | null            // frames_detected / frames_with_object_in_gauge
  false_stop_frames: number        // STOP frames without an in-gauge labelled object
  false_stop_episodes: number
  first_detection_distance: number | null  // the farthest distance at which a labelled object was matched
  raw: object                      // the full Evaluation.summary() dict
}

interface Run {
  id: string
  name: string                     // recording name (+ " · <preset>" when not the default preset)
  recording_id: string | null      // null when the recording was deleted
  job_id: string | null
  preset: { id: string, name: string }
  created_at: string
  has_clouds: boolean
  cloud_frames: number             // frames with a stored cloud
  source_kind: Recording["kind"]
  summary: RunSummary
}

interface Preset {
  id: string                       // "standard" is the built-in, read-only default
  name: string
  description: string
  builtin: boolean
  overrides: Record<string, number | boolean | string>   // dotted keys, e.g. "tracking.confirm_time_s"
  created_at: string
}

interface ParamSpec {              // one tunable detector parameter
  key: string                      // dotted: "<section>.<field>"
  group: string                    // Russian group title: "Габарит", "Кластеризация", "Трекинг", ...
  label: string                    // Russian, short
  help: string                     // Russian, one or two sentences for the "?" tooltip
  type: "float" | "int" | "bool"
  default: number | boolean
  min?: number, max?: number, step?: number   // absent for bool
  unit?: string                    // "м", "с", "кадр", "шт", "мс"; absent when unitless
}
```

## System

| method | path | returns |
|---|---|---|
| GET | `/api/system` | `{version, detector_version, uptime_s, cpu_count, load_1m, cpu_cores_busy, disk_free_bytes, data_dir, server_root, server_root_exists, features: {rosbags, open3d, native_kernels, clouds}, counts: {recordings, runs, jobs_queued, jobs_running}}` |
| GET | `/api/health` | `{ok: true}` |

`features.open3d` means installed (checked without importing it); `cpu_cores_busy = min(cpu_count, load_1m)`.

## Recordings (sources)

| method | path | body / query | returns |
|---|---|---|---|
| POST | `/api/uploads` | `{name?: string}` (≤ 200 chars) | `{upload_id}` (200) — a staging area |
| PUT | `/api/uploads/{upload_id}/files?path=<relative path>` | raw bytes (streamed, `application/octet-stream`); `path` may contain `/` for folder uploads (`webkitRelativePath`); sanitized (no `..`, no absolute) | `{path, size_bytes}`. 422 unsafe path, 409 path conflicts with an uploaded file / folder, 413 over `RESENSE_WEB_MAX_UPLOAD_GB` for the area, 507 disk full (checked when `Content-Length` is sent), 404 unknown area |
| POST | `/api/uploads/{upload_id}/finalize` | — | `Recording` (201). Detects: a `.zip` (unpacked safely: no zip-slip, no symlinks, size- and ratio-checked, no encrypted members) holding a rosbag2 folder (`metadata.yaml` + `.db3`/`.mcap`) or `.npy/.npz` frames or a `.jsonl`; loose `metadata.yaml` + `.db3`/`.mcap` (or a lone `.db3`/`.mcap`); a folder of `.npy/.npz`; a results `.jsonl` (`resense run --out` format, one FrameResult per line). 422 with a Russian message when nothing usable is found — the staging area is kept so files can be added and finalize retried; 409 while the same area is being finalized. **Synchronous**: unpacking a large zip takes a while (a 0.27 GB zip ≈ 4 s), clients must not time out. |
| DELETE | `/api/uploads/{upload_id}` | — | 204 (abort staging) |
| GET | `/api/server-files?path=<relative>` | browse `server_root` (env `RESENSE_DATA`, default `/data`), sandboxed: dot entries and symlinks leading out of the root are hidden | `{path, parent, entries: [{name, path, type: "dir" \| "file", size_bytes, is_bag, is_npy_dir, n_frames?}], truncated}` (dirs first; at most 2000 entries, `truncated` = more exist). 400 bad / absolute / `..` path or a file, 403 outside the root, 404 not found (or no root) |
| POST | `/api/recordings/from-server` | `{path}` (relative to server_root; a bag folder, its `metadata.yaml` / storage file, an npy folder or a `.jsonl`) | `Recording` (registered in place, not copied): 201, or 200 with the existing Recording when the same resolved path is already registered. 403 outside the root, 422 not a recording |
| POST | `/api/recordings/demo` | `{scenario?: "approach" \| "crossing" \| "clear" (default approach), seconds?: number (5..60, default 15), seed?: number (0..2^31-1, default 0), progress_id?: string (8..64 of A-Za-z0-9_-, chosen by the client)}` | `Recording` (201) — a real rosbag2 bag (sqlite3, `/lidar_points`, 10 Hz) of synthetic tunnel frames written to the data dir, with its `ground_truth.json` (labels.source = `builtin`). **Synchronous**: ≈ 0.65 s per simulated second (60 s ≈ 40 s); ≈ 33 MB per second of recording. With `progress_id` the generation can be followed with the endpoint below (409 while a generation with the same id is running). Scenes: `approach` — the train brakes to a stop ~25 m before a person standing on the track; `crossing` — the train stands, a person crosses the track at ~55 m (GO → CAUTION → STOP → GO); `clear` — trackside equipment beside the envelope, no obstacle (GO / CAUTION, no STOP) |
| GET | `/api/recordings/demo/progress/{progress_id}` | — | `{progress_id, fraction: number /* 0..1 */, done: boolean, recording_id: string \| null /* set when done */, error: string \| null /* the Russian detail of a failed generation */}` — polled by the UI while the POST above runs; 404 before the POST has started or 10 min after the last update. One API process keeps it in memory. |
| GET | `/api/recordings` | — | `Recording[]` newest first |
| GET | `/api/recordings/{id}` | — | `Recording` |
| DELETE | `/api/recordings/{id}` | — | 204 (files removed unless `source == "server"`; its queued jobs are cancelled, its runs stay with `recording_id = null`); 409 while a running job uses it |
| GET | `/api/recordings/{id}/download` | — | the demo bag as a `.zip` (demo recordings only, else 403); built on the first request (≈ 35 MB of bag per second: a 15 s demo ≈ 15 s, a 60 s demo ≈ 1 min before the first byte), then cached |
| PUT | `/api/recordings/{id}/labels` | raw JSON body in the `labels/*.json` format (`{"_meta": {...}, "00042": [{...}], ...}`), ≤ 64 MB | `Recording` (labels.source = `upload`, name = `_meta.bag`); 422 when it is not a label file, 413 when too big |
| DELETE | `/api/recordings/{id}/labels` | — | `Recording` (falls back to a bundled `ground_truth.json` or built-in labels matched by name, if any) |

## Jobs (queue)

One worker process at a time runs the detector (`python -m resense_web.worker <job_id>`); others wait.
The queue lives in the API process: run the server as a single process (no `uvicorn --workers`).
Jobs left `running` by a stopped server are marked `failed` («прервано перезапуском сервера»).

| method | path | body | returns |
|---|---|---|---|
| POST | `/api/jobs` | `{recording_id, preset_id?: string (default "standard"), options?: JobOptions}` | `Job` (201); 404 unknown recording / preset, 422 bad options or a topic that is not a PointCloud2 topic of the recording |
| GET | `/api/jobs` | `?status=queued,running` optional filter (422 on an unknown status) | `Job[]` (running first, then queued in order, then finished newest first) |
| GET | `/api/jobs/{id}` | — | `Job` |
| POST | `/api/jobs/{id}/cancel` | — | `Job` (queued → cancelled; running → SIGTERM, SIGKILL after 5 s → cancelled, the partial run removed); 409 when already finished |
| POST | `/api/jobs/{id}/retry` | — | new `Job` (201) with the same recording/preset/options (the preset's current overrides); 409 while the job is active or when its recording / preset was deleted |
| DELETE | `/api/jobs/{id}` | — | 204 (only finished/failed/cancelled, else 409; the run stays with `job_id = null`) |
| DELETE | `/api/jobs?finished=true` | — | 204 (clear finished entries; 422 without `finished=true`) |
| GET | `/api/jobs/{id}/log` | — | `text/plain` tail (64 KB) of the worker log |

## Runs (results)

| method | path | returns |
|---|---|---|
| GET | `/api/runs` | `Run[]` newest first |
| GET | `/api/runs/{id}` | `RunDetail`: `Run & {episodes: Episode[], events: Episode[] /* non-GO episodes + GO gaps inside STOP */, recording: Recording \| null, options: JobOptions \| null /* as run, defaults filled in */, overrides: Record<string, number \| boolean \| string> /* the preset's overrides at job time ({} = defaults) */, sizes: {results_jsonl: number \| null, clouds: number \| null, frames_csv: number \| null} /* bytes of the stored results.jsonl / clouds.bin and of the frames.csv download (measured once, then kept as runs/<id>/frames.csv.size) */}` |
| PATCH | `/api/runs/{id}` | body `{name}` → `Run` (422 on a blank name) |
| DELETE | `/api/runs/{id}` | 204 |
| GET | `/api/runs/{id}/series` | compact per-frame arrays for charts: `{frame: number[], t: number[], decisions: string, nearest: (number\|null)[], clear: number[], latency_ms: number[], n_detections: number[], n_warnings: number[], n_points: number[], visibility: (number\|null)[], labels_in_gauge: boolean[] \| null}` |
| GET | `/api/runs/{id}/labels` | the run's label file per processed frame (for the distance chart): `{available: boolean, labels_name: string \| null, in_gauge: boolean[], near: (number\|null)[], far: (number\|null)[]}` — `near` = the nearest face of the nearest labelled, visible in-gauge object, `far` = `near` + its length (m), null where there is none. `available: false` (arrays empty, still 200) when the run was made without labels or its label file is gone (e.g. the recording was deleted) |
| GET | `/api/runs/{id}/frames?from=<i>&count=<n>` | `{from, count, total, frames: FrameResultDict[]}` — positions in processed order (0-based); `from >= 0` (default 0), `count >= 1` (default 100; above 500 it is clamped to 500). Each dict is `FrameResult.to_dict()` plus `frame` (bag index), `frame_id`, `t`, `decision`, `pos` |
| GET | `/api/runs/{id}/clouds` | `{frames: number[] /* positions that have a cloud */, points: number /* budget */, format: "RSC1"}` |
| GET | `/api/runs/{id}/clouds/{pos}` | binary cloud (below), `application/octet-stream`, not gzipped, `Cache-Control: immutable`; 404 when that position has no cloud |
| GET | `/api/runs/{id}/download/results.jsonl` | one JSON per line (the `/frames` dicts) |
| GET | `/api/runs/{id}/download/report.json` | `{schema: "resense_web_report", version: 1, run: Run, episodes, generated_at, events, recording: Recording \| null, options: JobOptions, overrides, config /* the effective DetectorConfig */}` |
| GET | `/api/runs/{id}/download/frames.csv` | `pos,frame,t,decision,nearest_distance,clear_distance,latency_ms,n_detections,n_warnings,n_points` (UTF-8, `;`-free, comma separated) |

### Binary cloud format `RSC1` (little-endian)

```
bytes 0..3   ASCII "RSC1"
uint32       n                      number of points
int16[n*3]   x0 y0 z0 x1 y1 z1 ...   centimetres, vehicle frame (X forward, Y left, Z up), after the mount correction
uint8[n]     intensity              clipped 0..255
uint8[n]     flags                  bit0 in corridor · bit1 inside a confirmed gauge object box (STOP) · bit2 inside an advisory (warning) box
```

Points kept per frame: every corridor / object point, then a uniform random sample of the rest up to
`cloud_points`. A run keeps at most 3000 clouds; longer runs store every k-th frame (`/clouds` lists which).

## Presets (detector parameters)

| method | path | body | returns |
|---|---|---|---|
| GET | `/api/presets` | — | `Preset[]` (the built-in `standard` first) |
| GET | `/api/presets/schema` | — | `ParamSpec[]` (20 curated parameters in 7 groups, defaults from `configs/default.yaml`) |
| GET | `/api/presets/{id}` | — | `Preset` (404 unknown) |
| POST | `/api/presets` | `{name, description?, overrides}` | `Preset` (201); 422 on a blank name (≤ 80 chars), an unknown key, a wrong type or an out-of-range value (the message names the parameter; a decimal comma `"0,4"` is accepted); 409 when the name is taken |
| PATCH | `/api/presets/{id}` | `{name?, description?, overrides?}` | `Preset` (403 for built-in, 404 unknown; `overrides` replaces the whole set) |
| DELETE | `/api/presets/{id}` | — | 204 (403 for built-in, 404 unknown; jobs keep the overrides they were created with) |

## Live

| method | path | notes |
|---|---|---|
| WS | `/api/live/sim?run_id=<id>&speed=<0.25..10>&loop=<bool>` | server pushes one JSON message per frame at 10 Hz × speed: the `/frames` dict plus `{"node": {"fps", "latency_ms", "frames", "dropped_frames"}, "snapshot_kind": "frame", "sim": true, "cloud_pos": number \| null}`. Client may send `{"cmd": "pause" \| "play" \| "seek" \| "speed", "pos"?: number, "speed"?: number}`. |

Live details: `node.fps` is the measured send rate, `node.latency_ms` = the frame's `timing_ms.total`,
`node.frames` counts messages of this connection, `dropped_frames` is 0. `cloud_pos` is the frame's own
stored cloud, else the nearest earlier one. `speed` is honoured in any command and clipped to 0.25..10;
`pos` is clipped to the run. A `seek` sends that frame at once, also while paused. At the end the
replay loops (`loop=true`) or closes with 1000. Close codes: 1000 end of the run, 4400 bad query
(`run_id` / `speed` / `loop`), 4404 unknown run, 1011 unreadable results line.

Real node: the browser connects directly to rosbridge (`ws://<host>:9090`, topic `/resense/status`,
`std_msgs/String` JSON with the same keys) — no backend involvement.

## Static frontend

`python -m resense_web` (default `0.0.0.0:8080`; `--host`, `--port`, `--reload`) serves
`webapp/frontend/dist` at `/` with an SPA fallback (any non-`/api` path returns `index.html`; a
missing `/assets/*` file is a 404, `/assets/*` are served `immutable`) when the build exists, else a
short Russian help page. `scripts/run_webapp.sh` builds the frontend when needed and starts it on
`:8080`. Dev: Vite on `:5173` (`npm run dev`; `vite preview` on `:4173`) proxies `/api` (HTTP + WS)
to `127.0.0.1:8000` (`python -m resense_web --port 8000 --reload`); CORS allows those origins.

## Environment

| variable | default | meaning |
|---|---|---|
| `RESENSE_WEB_DATA` | `<repo>/webapp/data` | database, uploads, recordings, runs |
| `RESENSE_DATA` | `/data` | server-folder root for "Папка на сервере" |
| `RESENSE_WEB_MAX_UPLOAD_GB` | `100` | per upload staging area |
| `RESENSE_WEB_HOST` / `RESENSE_WEB_PORT` | `0.0.0.0` / `8080` | bind |
| `RESENSE_WEB_STATIC` | `<repo>/webapp/frontend/dist` | the built frontend to serve |

Data dir layout: `resense_web.sqlite`; `uploads/<id>/` staging areas (stale ones > 24 h removed at
start); `recordings/<id>/` uploaded and demo recordings, uploaded labels; `jobs/<id>/` spec.json,
progress.json, result.json, worker.log; `runs/<id>/` results.jsonl (+ .idx), clouds.bin +
clouds.json, series.json, summary.json, worker.log, frames.csv.size; `cache/` demo zips.
