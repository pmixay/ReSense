# ReSense web — HTTP API contract

> Source of truth for `webapp/backend` (FastAPI) and `webapp/frontend` (React). Every path is under
> `/api`. JSON uses `snake_case`. Times are ISO 8601 UTC strings (`created_at`) or seconds
> (`t`, `duration_s`). Distances in metres, latencies in milliseconds. Errors:
> `{"detail": "<Russian, short, user-facing message>"}` with a 4xx/5xx status.

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
  created_at: string
  warnings: string[]               // e.g. "нет поля ring" — Russian, short
}

interface JobOptions {
  topic?: string | null            // null = auto (first PointCloud2 topic / the default_topic)
  every?: number                   // frame step, >= 1 (default 1)
  start?: number                   // first frame index (default 0)
  limit?: number | null            // max frames to process (default all)
  clouds?: boolean                 // store decimated point clouds for the 3D player (default true)
  cloud_points?: number            // points per stored cloud (default 30000, 5000..120000)
  ego_speed?: number | null        // m/s given to Detector.process (default null)
  evaluate?: boolean               // score against labels when available (default true)
}

interface JobProgress {
  frames_done: number
  frames_total: number | null
  fps: number | null               // processed frames per wall second (moving average)
  eta_s: number | null
  stage: "queued" | "opening" | "processing" | "evaluating" | "finalizing" | "done"
  stage_ms: Record<string, number> // mean timing_ms of the last 20 frames, keys as the detector's timing_ms
  decisions: string                // decision string so far
  last: { frame: number, decision: Decision, nearest_distance: number | null } | null
}

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
  run_id: string | null            // set when done
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
  eval: EvalSummary | null         // when labels were available and evaluate=true
}

interface EvalSummary {            // from resense.metrics.Evaluation.summary(), plus these headline keys
  labels_name: string
  frames_labelled: number
  frames_with_object_in_gauge: number
  frames_detected: number          // labelled in-gauge frames that got STOP
  recall: number | null            // frames_detected / frames_with_object_in_gauge
  false_stop_frames: number        // STOP frames without an in-gauge labelled object
  false_stop_episodes: number
  first_detection_distance: number | null
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
  min?: number, max?: number, step?: number
  unit?: string                    // "м", "с", "кадр", ...
}
```

## System

| method | path | returns |
|---|---|---|
| GET | `/api/system` | `{version, detector_version, uptime_s, cpu_count, load_1m, cpu_cores_busy, disk_free_bytes, data_dir, server_root, server_root_exists, features: {rosbags, open3d, native_kernels, clouds}, counts: {recordings, runs, jobs_queued, jobs_running}}` |
| GET | `/api/health` | `{ok: true}` |

## Recordings (sources)

| method | path | body / query | returns |
|---|---|---|---|
| POST | `/api/uploads` | `{name?: string}` | `{upload_id}` — a staging area |
| PUT | `/api/uploads/{upload_id}/files?path=<relative path>` | raw bytes (streamed, `application/octet-stream`); `path` may contain `/` for folder uploads; sanitized (no `..`, no absolute) | `{path, size_bytes}` |
| POST | `/api/uploads/{upload_id}/finalize` | — | `Recording` (201). Detects: a `.zip` (unpacked safely: no zip-slip, size-checked) holding a rosbag2 folder (`metadata.yaml` + `.db3`/`.mcap`) or `.npy/.npz` frames or a `.jsonl`; loose `metadata.yaml` + `.db3`/`.mcap`; a folder of `.npy/.npz`; a results `.jsonl` (`resense run --out` format, one FrameResult per line). 422 with a Russian message when nothing usable is found. |
| DELETE | `/api/uploads/{upload_id}` | — | 204 (abort staging) |
| GET | `/api/server-files?path=<relative>` | browse `server_root` (env `RESENSE_DATA`, default `/data`), sandboxed | `{path, parent, entries: [{name, path, type: "dir" \| "file", size_bytes, is_bag, is_npy_dir, n_frames?}]}` |
| POST | `/api/recordings/from-server` | `{path}` (relative to server_root) | `Recording` (registered in place, not copied) |
| POST | `/api/recordings/demo` | `{scenario: "approach" \| "crossing" \| "clear", seconds?: number (5..60, default 15), seed?: number}` | `Recording` — a real rosbag2 bag (sqlite3) of synthetic tunnel frames written to the data dir |
| GET | `/api/recordings` | — | `Recording[]` newest first |
| GET | `/api/recordings/{id}` | — | `Recording` |
| DELETE | `/api/recordings/{id}` | — | 204 (files removed unless `source == "server"`) |
| GET | `/api/recordings/{id}/download` | — | the demo bag as a `.zip` (demo recordings only) |
| PUT | `/api/recordings/{id}/labels` | raw JSON body in the `labels/*.json` format (`{"_meta": {...}, "00042": [{...}], ...}`) | `Recording` (labels.source = `upload`); 422 when it is not a label file |
| DELETE | `/api/recordings/{id}/labels` | — | `Recording` (falls back to built-in labels matched by name, if any) |

## Jobs (queue)

One worker process at a time runs the detector (`python -m resense_web.worker <job_id>`); others wait.

| method | path | body | returns |
|---|---|---|---|
| POST | `/api/jobs` | `{recording_id, preset_id?: string (default "standard"), options?: JobOptions}` | `Job` (201) |
| GET | `/api/jobs` | `?status=queued,running` optional filter | `Job[]` (running first, then queued in order, then finished newest first) |
| GET | `/api/jobs/{id}` | — | `Job` |
| POST | `/api/jobs/{id}/cancel` | — | `Job` (queued → cancelled; running → process terminated → cancelled) |
| POST | `/api/jobs/{id}/retry` | — | new `Job` with the same recording/preset/options |
| DELETE | `/api/jobs/{id}` | — | 204 (only finished/failed/cancelled; the run stays) |
| DELETE | `/api/jobs?finished=true` | — | 204 (clear finished entries) |
| GET | `/api/jobs/{id}/log` | — | `text/plain` tail of the worker log |

## Runs (results)

| method | path | returns |
|---|---|---|
| GET | `/api/runs` | `Run[]` newest first |
| GET | `/api/runs/{id}` | `Run & {episodes: Episode[], events: Episode[] /* non-GO episodes + GO gaps inside STOP */, recording: Recording \| null}` |
| PATCH | `/api/runs/{id}` | body `{name}` → `Run` |
| DELETE | `/api/runs/{id}` | 204 |
| GET | `/api/runs/{id}/series` | compact per-frame arrays for charts: `{frame: number[], t: number[], decisions: string, nearest: (number\|null)[], clear: number[], latency_ms: number[], n_detections: number[], n_warnings: number[], n_points: number[], visibility: (number\|null)[], labels_in_gauge: boolean[] \| null}` |
| GET | `/api/runs/{id}/frames?from=<i>&count=<n>` | `{from, count, total, frames: FrameResultDict[]}` — positions in processed order (0-based), `count <= 500`. Each dict is `FrameResult.to_dict()` plus `frame` (bag index), `frame_id`, `t`, `decision`, `pos` |
| GET | `/api/runs/{id}/clouds` | `{frames: number[] /* positions that have a cloud */, points: number /* budget */, format: "RSC1"}` |
| GET | `/api/runs/{id}/clouds/{pos}` | binary cloud (below); 404 when that position has no cloud |
| GET | `/api/runs/{id}/download/results.jsonl` | one JSON per line (the `/frames` dicts) |
| GET | `/api/runs/{id}/download/report.json` | `{schema: "resense_web_report", version: 1, run: Run, episodes, generated_at}` |
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
| GET | `/api/presets/schema` | — | `ParamSpec[]` (≈ 12–20 curated parameters, defaults from `configs/default.yaml`) |
| POST | `/api/presets` | `{name, description?, overrides}` | `Preset` (201); 422 on an unknown key or out-of-range value |
| PATCH | `/api/presets/{id}` | `{name?, description?, overrides?}` | `Preset` (403 for built-in) |
| DELETE | `/api/presets/{id}` | — | 204 (403 for built-in) |

## Live

| method | path | notes |
|---|---|---|
| WS | `/api/live/sim?run_id=<id>&speed=<0.25..10>&loop=<bool>` | server pushes one JSON message per frame at 10 Hz × speed: the `/frames` dict plus `{"node": {"fps", "latency_ms", "frames", "dropped_frames"}, "snapshot_kind": "frame", "sim": true, "cloud_pos": number \| null}`. Client may send `{"cmd": "pause" \| "play" \| "seek", "pos"?: number, "speed"?: number}`. |

Real node: the browser connects directly to rosbridge (`ws://<host>:9090`, topic `/resense/status`,
`std_msgs/String` JSON with the same keys) — no backend involvement.

## Static frontend

`python -m resense_web` (default `0.0.0.0:8080`) serves `webapp/frontend/dist` at `/` with an SPA
fallback (any non-`/api` path returns `index.html`) when the build exists. Dev: Vite on `:5173`
proxies `/api` (HTTP + WS) to `127.0.0.1:8000` (`python -m resense_web --port 8000 --reload`).

## Environment

| variable | default | meaning |
|---|---|---|
| `RESENSE_WEB_DATA` | `<repo>/webapp/data` | database, uploads, recordings, runs |
| `RESENSE_DATA` | `/data` | server-folder root for "Папка на сервере" |
| `RESENSE_WEB_MAX_UPLOAD_GB` | `100` | per upload staging area |
| `RESENSE_WEB_HOST` / `RESENSE_WEB_PORT` | `0.0.0.0` / `8080` | bind |
