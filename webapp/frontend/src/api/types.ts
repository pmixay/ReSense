// Types of the HTTP contract (webapp/API.md). snake_case as on the wire; times are ISO 8601 UTC
// strings or seconds, distances metres, latencies milliseconds.
import type { TrackModelDict } from '../lib/track';

export type Decision = 'GO' | 'CAUTION' | 'STOP' | 'FAULT';

// ---------------------------------------------------------------- recordings

export type RecordingKind = 'rosbag2' | 'npy' | 'jsonl';
export type RecordingSource = 'upload' | 'server' | 'demo';

export interface TopicInfo {
  name: string;
  type: string;
  count: number;
}

export interface RecordingLabels {
  available: boolean;
  source: 'builtin' | 'upload' | null;
  name: string | null;
}

export interface Recording {
  id: string;
  name: string;
  kind: RecordingKind;
  source: RecordingSource;
  path: string;
  size_bytes: number;
  n_frames: number | null;
  duration_s: number | null;
  topics: TopicInfo[];
  default_topic: string | null;
  labels: RecordingLabels;
  created_at: string;
  warnings: string[];
}

// ---------------------------------------------------------------- jobs

export interface JobOptions {
  topic?: string | null;
  every?: number;
  start?: number;
  limit?: number | null;
  clouds?: boolean;
  cloud_points?: number;
  ego_speed?: number | null;
  evaluate?: boolean;
}

export type JobStage = 'queued' | 'opening' | 'processing' | 'evaluating' | 'finalizing' | 'done';
export type JobStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled';

export interface JobProgress {
  frames_done: number;
  frames_total: number | null;
  fps: number | null;
  eta_s: number | null;
  stage: JobStage;
  stage_ms: Record<string, number>;
  decisions: string;
  last: { frame: number; decision: Decision; nearest_distance: number | null } | null;
}

export interface Job {
  id: string;
  recording_id: string;
  recording_name: string;
  preset_id: string;
  preset_name: string;
  options: Required<JobOptions>;
  status: JobStatus;
  position: number | null;
  progress: JobProgress;
  error: string | null;
  run_id: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface JobCreate {
  recording_id: string;
  preset_id?: string;
  options?: JobOptions;
}

// ---------------------------------------------------------------- runs

export interface Episode {
  decision: Decision;
  first_frame: number;
  last_frame: number;
  t0: number;
  t1: number;
  n_frames: number;
  distance_min: number | null;
  distance_max: number | null;
}

export interface EvalSummary {
  labels_name: string;
  frames_labelled: number;
  frames_with_object_in_gauge: number;
  frames_detected: number;
  recall: number | null;
  false_stop_frames: number;
  false_stop_episodes: number;
  first_detection_distance: number | null;
  raw: Record<string, unknown>;
}

export interface RunSummary {
  n_frames: number;
  duration_s: number;
  counts: Record<Decision, number>;
  decisions: string;
  stop_episodes: number;
  first_stop: { frame: number; t: number; distance: number | null } | null;
  distance_min: number | null;
  distance_max: number | null;
  latency_ms: { p50: number; p95: number; max: number };
  processing_fps: number;
  clear_distance_median: number | null;
  visibility_median: number | null;
  eval: EvalSummary | null;
}

export interface Run {
  id: string;
  name: string;
  recording_id: string | null;
  job_id: string | null;
  preset: { id: string; name: string };
  created_at: string;
  has_clouds: boolean;
  cloud_frames: number;
  source_kind: RecordingKind;
  summary: RunSummary;
}

export interface RunDetail extends Run {
  episodes: Episode[];
  events: Episode[];
  recording: Recording | null;
  /** the job options the run was made with (defaults filled in); null for old runs */
  options?: Required<JobOptions> | null;
  /** the preset's overrides at job time ({} = the detector defaults) */
  overrides?: Record<string, ParamValue>;
  /** bytes of the stored results.jsonl / clouds.bin (null when absent) */
  sizes?: { results_jsonl: number | null; clouds: number | null };
}

/** GET /api/runs/{id}/labels: the run's label file per processed frame (distance chart band). */
export interface RunLabels {
  available: boolean;
  labels_name: string | null;
  in_gauge: boolean[];
  /** nearest face of the nearest labelled, visible in-gauge object (m), null where none */
  near: (number | null)[];
  /** near + the object's length (m) */
  far: (number | null)[];
}

export interface RunSeries {
  frame: number[];
  t: number[];
  decisions: string;
  nearest: (number | null)[];
  clear: number[];
  latency_ms: number[];
  n_detections: number[];
  n_warnings: number[];
  n_points: number[];
  visibility: (number | null)[];
  labels_in_gauge: boolean[] | null;
}

/** resense.detector.Detection.to_dict() */
export interface DetectionDict {
  id: number;
  zone: string; // 'gauge' | 'warning'
  distance: number;
  lateral: number;
  center: [number, number, number];
  size: [number, number, number];
  n_points: number;
  confidence: number;
  age: number;
  height_min: number;
  intensity: number;
  reason: string;
  kind: string;
}

/** resense.health.HealthMonitor.update() */
export interface HealthDict {
  level?: 'ok' | 'warn' | 'error';
  decision_level?: 'ok' | 'warn' | 'error';
  messages?: string[];
  points?: number;
  near_fraction?: number;
  blocked_sectors?: number;
  visibility?: number;
  rail_lock?: number;
  latency_p95_ms?: number;
  monitored_range?: number;
  clear_distance?: number;
  candidate_distance?: number | null;
  [key: string]: unknown;
}

/** resense.calibration.MountCalibration.to_dict() */
export interface MountDict {
  status?: string;
  orientation?: string;
  roll_deg?: number;
  pitch_deg?: number;
  yaw_deg?: number;
  height?: number | null;
  lateral?: number | null;
  frames_used?: number;
  drift_deg?: number;
  message?: string;
  [key: string]: unknown;
}

/** FrameResult.to_dict() plus the web keys: frame (bag index), frame_id, t, decision, pos. */
export interface FrameResultDict {
  stamp: number;
  obstacle: boolean;
  warning: boolean;
  nearest_distance: number | null;
  detections: DetectionDict[];
  warnings: DetectionDict[];
  n_candidates: number;
  n_points: number;
  n_corridor: number;
  track: TrackModelDict;
  timing_ms: Record<string, number>; // track, corridor, egomotion, accumulate, cluster, tracking, total
  ego_speed: number | null;
  ego_speed_source: string;
  n_accumulated: number;
  ego_speed_estimate: number | null;
  ego_speed_confidence: number;
  clear_distance: number;
  health: HealthDict;
  mount: MountDict;
  frame: number;
  frame_id: string;
  t: number;
  decision: Decision;
  pos: number;
}

export interface FramesPage {
  from: number;
  count: number;
  total: number;
  frames: FrameResultDict[];
}

export interface CloudsIndex {
  frames: number[];
  points: number;
  format: 'RSC1';
}

export interface RunReport {
  schema: 'resense_web_report';
  version: 1;
  run: Run;
  episodes: Episode[];
  generated_at: string;
}

// ---------------------------------------------------------------- presets

export type ParamValue = number | boolean | string;

export interface Preset {
  id: string;
  name: string;
  description: string;
  builtin: boolean;
  overrides: Record<string, ParamValue>;
  created_at: string;
}

export interface PresetCreate {
  name: string;
  description?: string;
  overrides: Record<string, ParamValue>;
}

export interface PresetPatch {
  name?: string;
  description?: string;
  overrides?: Record<string, ParamValue>;
}

export interface ParamSpec {
  key: string;
  group: string;
  label: string;
  help: string;
  type: 'float' | 'int' | 'bool';
  default: number | boolean;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
}

// ---------------------------------------------------------------- system

export interface SystemInfo {
  version: string;
  detector_version: string;
  uptime_s: number;
  cpu_count: number;
  load_1m: number;
  cpu_cores_busy: number;
  disk_free_bytes: number;
  data_dir: string;
  server_root: string;
  server_root_exists: boolean;
  features: { rosbags: boolean; open3d: boolean; native_kernels: boolean; clouds: boolean };
  counts: { recordings: number; runs: number; jobs_queued: number; jobs_running: number };
}

export interface HealthOk {
  ok: true;
}

// ---------------------------------------------------------------- uploads / server files

export interface UploadCreated {
  upload_id: string;
}

export interface UploadedFile {
  path: string;
  size_bytes: number;
}

export interface ServerEntry {
  name: string;
  path: string;
  type: 'dir' | 'file';
  size_bytes: number;
  is_bag: boolean;
  is_npy_dir: boolean;
  n_frames?: number;
}

export interface ServerListing {
  path: string;
  parent: string | null;
  entries: ServerEntry[]; // dirs first, at most 2000
  truncated: boolean; // more entries exist than listed
}

export type DemoScenario = 'approach' | 'crossing' | 'clear';

export interface DemoCreate {
  scenario: DemoScenario;
  seconds?: number; // 5..60, default 15
  seed?: number;
  /** client-chosen id (8..64 of A-Za-z0-9_-) to follow the generation via DemoProgress */
  progress_id?: string;
}

/** GET /api/recordings/demo/progress/{progress_id} while POST /api/recordings/demo runs. */
export interface DemoProgress {
  progress_id: string;
  fraction: number; // 0..1
  done: boolean;
  recording_id: string | null;
  error: string | null;
}

/** Raw labels file (labels/*.json): {"_meta": {...}, "00042": [{...}], ...}. */
export type LabelsFile = Record<string, unknown>;

// ---------------------------------------------------------------- live

export interface LiveNodeStats {
  fps: number;
  latency_ms: number;
  frames: number;
  dropped_frames: number;
  [key: string]: unknown;
}

/** One message of WS /api/live/sim (and, with the same keys, of the rosbridge /resense/status topic). */
export interface LiveMessage extends Partial<FrameResultDict> {
  decision: Decision;
  node: LiveNodeStats;
  snapshot_kind: 'frame' | 'watchdog' | 'processing_error' | string;
  sim?: boolean;
  cloud_pos?: number | null;
}

export type LiveCommand =
  | { cmd: 'pause' }
  | { cmd: 'play'; speed?: number }
  | { cmd: 'seek'; pos: number; speed?: number }
  | { cmd: 'speed'; speed: number };

// ---------------------------------------------------------------- errors

export interface ApiErrorBody {
  detail: string | { msg?: string; loc?: unknown[] }[] | unknown;
}
