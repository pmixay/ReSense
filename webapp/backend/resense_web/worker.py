"""The detector worker: ``python -m resense_web.worker <job_id>``.

Reads ``<data>/jobs/<job_id>/spec.json`` (written by the job manager), runs the detector over the
recording's frames and writes ``runs/<run_id>/``: results.jsonl (+ .idx), clouds.bin/.json,
series.json, summary.json. Progress goes to ``jobs/<job_id>/progress.json`` (atomic, <= 5 Hz), the
outcome to ``result.json``; stdout/stderr are the job's worker.log. A ``jsonl`` recording holds
results only: its decisions and summary are recomputed without the detector and without clouds."""
from __future__ import annotations

import json
import sys
import time
import traceback
from collections import deque
from pathlib import Path
from typing import Iterator

import numpy as np

from resense_web.clouds import CloudWriter, cloud_stride, pack_frame_cloud
from resense_web.decision import decision_of, letter_of
from resense_web.results import ResultsWriter, iter_results
from resense_web.settings import get_settings
from resense_web.summary import SeriesBuilder, episodes_of, events_of, run_summary
from resense_web.util import atomic_write_json, read_json

PROGRESS_PERIOD_S = 0.2


class WorkerError(Exception):
    """A failure with a short Russian message for the user."""


class Progress:
    def __init__(self, path: Path, total: int | None):
        self.path = path
        self.total = total
        self.stage = "opening"
        self.done = 0
        self.letters: list[str] = []
        self.last: dict | None = None
        self.timings: deque = deque(maxlen=20)
        self.times: deque = deque(maxlen=60)
        self._written = 0.0

    def set_stage(self, stage: str) -> None:
        self.stage = stage
        self.write(force=True)

    def frame(self, d: dict) -> None:
        self.done += 1
        self.letters.append(letter_of(d["decision"]))
        self.last = {"frame": d["frame"], "decision": d["decision"], "nearest_distance": d.get("nearest_distance")}
        self.timings.append(d.get("timing_ms") or {})
        self.times.append((time.monotonic(), self.done))
        self.write()

    def snapshot(self) -> dict:
        fps = None
        if len(self.times) >= 2:
            (t0, n0), (t1, n1) = self.times[0], self.times[-1]
            if t1 > t0:
                fps = round((n1 - n0) / (t1 - t0), 2)
        eta = None
        if fps and self.total is not None:
            eta = round(max(0, self.total - self.done) / fps, 1)
        stage_ms: dict[str, float] = {}
        if self.timings:
            keys = {k for t in self.timings for k in t}
            for k in sorted(keys):
                vals = [float(t[k]) for t in self.timings if k in t]
                stage_ms[k] = round(sum(vals) / len(vals), 2)
        return {"frames_done": self.done, "frames_total": self.total, "fps": fps, "eta_s": eta,
                "stage": self.stage, "stage_ms": stage_ms, "decisions": "".join(self.letters), "last": self.last}

    def write(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._written < PROGRESS_PERIOD_S:
            return
        self._written = now
        atomic_write_json(self.path, self.snapshot())


# --- frame sources ------------------------------------------------------------------------------

def _to_compact(xyz: np.ndarray, intensity=None, ring=None) -> np.ndarray:
    from resense.pointcloud import COMPACT_DTYPE
    xyz = np.asarray(xyz)
    out = np.zeros(xyz.shape[0], dtype=COMPACT_DTYPE)
    out["x"], out["y"], out["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    if intensity is not None:
        out["intensity"] = np.asarray(intensity).reshape(-1)[: xyz.shape[0]]
    if ring is not None:
        out["ring"] = np.asarray(ring).reshape(-1)[: xyz.shape[0]]
    return out


def load_array_frame(path: Path) -> np.ndarray:
    """A compact structured array (sensor frame) from a .npy (structured or N x 3..5 columns
    x y z [intensity [ring]]) or an .npz (``xyz`` / ``points`` [+ ``intensity``, ``ring``] or a
    structured member)."""
    if path.suffix.lower() == ".npz":
        with np.load(path, allow_pickle=False) as z:
            key = "xyz" if "xyz" in z.files else "points" if "points" in z.files else None
            if key is not None:
                pts = z[key]
                inten = z["intensity"] if "intensity" in z.files else (pts[:, 3] if pts.shape[1] > 3 else None)
                ring = z["ring"] if "ring" in z.files else None
                return _to_compact(pts[:, :3], inten, ring)
            for k in z.files:
                a = z[k]
                if a.dtype.names and {"x", "y", "z"} <= set(a.dtype.names):
                    return a
        raise WorkerError(f"Файл {path.name}: нет массива xyz")
    a = np.load(path, allow_pickle=False)
    if a.dtype.names:
        return a
    return _to_compact(a[:, :3], a[:, 3] if a.shape[1] > 3 else None, a[:, 4] if a.shape[1] > 4 else None)


def iter_array_frames(directory: Path, sensor, every: int = 1, start: int = 0, limit: int | None = None,
                      index_from_name: bool = False) -> Iterator[tuple]:
    """Like ``resense.io.iter_npy_frames`` for folders with .npz files or plain arrays."""
    from resense.frame import frame_from_compact
    from resense.io import load_cache_stamps, npy_frame_index

    from resense_web.probe import frame_files
    files = frame_files(directory)
    stamps = load_cache_stamps(str(directory))
    n_out = 0
    for i, f in enumerate(files):
        if i < start or (i - start) % every != 0:
            continue
        idx = i
        if index_from_name:
            named = npy_frame_index(str(f))
            idx = i if named is None else named
        stamp = stamps.get(f.stem, float(idx) * 0.1)
        yield idx, frame_from_compact(load_array_frame(f), sensor, stamp=stamp, frame_id=f.name)
        n_out += 1
        if limit is not None and n_out >= limit:
            return


def open_frames(spec: dict, cfg) -> Iterator[tuple]:
    rec, opts = spec["recording"], spec["options"]
    every, start, limit = int(opts["every"]), int(opts["start"]), opts.get("limit")
    if rec["kind"] == "rosbag2":
        from resense.io import iter_bag_frames
        topic = opts.get("topic") or rec.get("default_topic")
        return iter_bag_frames(rec["path"], cfg.sensor, topic=topic, every=every, start=start, limit=limit)
    if rec["kind"] == "npy":
        meta = rec.get("meta") or {}
        if meta.get("layout") == "compact":
            from resense.io import iter_npy_frames
            return iter_npy_frames(rec["path"], cfg.sensor, every=every, start=start, limit=limit,
                                   index_from_name=bool(meta.get("index_from_name")))
        return iter_array_frames(Path(rec["path"]), cfg.sensor, every, start, limit,
                                 bool(meta.get("index_from_name")))
    raise WorkerError(f"Неизвестный тип записи: {rec['kind']}")


def iter_jsonl(path: str, every: int = 1, start: int = 0, limit: int | None = None) -> Iterator[dict]:
    """Result dicts of a ``resense run --out`` file / a status capture, with the job's frame
    selection applied over the valid lines (``---`` separators and junk skipped)."""
    i = n_out = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict) or "obstacle" not in d:
                continue
            if i >= start and (i - start) % every == 0:
                if not isinstance(d.get("frame"), int):
                    d["frame"] = i
                yield d
                n_out += 1
                if limit is not None and n_out >= limit:
                    return
            i += 1


def processed_intensity(frame, xyz: np.ndarray) -> np.ndarray:
    """Intensity aligned with the detector's processed cloud (it drops non-finite points)."""
    inten = np.asarray(frame.intensity)
    if inten.shape[0] == xyz.shape[0]:
        return inten
    ok = np.isfinite(frame.xyz).all(axis=1)
    if int(ok.sum()) == xyz.shape[0]:
        return inten[ok]
    return np.zeros(xyz.shape[0], dtype=np.float32)


# --- the job ------------------------------------------------------------------------------------

def run_job(spec: dict, progress: Progress) -> dict:
    run_dir = Path(spec["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    rec, opts = spec["recording"], spec["options"]
    print(f"job {spec['job_id']}: {rec['name']} ({rec['kind']}, {rec['path']}), preset {spec['preset']['name']}, "
          f"options {json.dumps(opts, ensure_ascii=False)}", flush=True)
    writer = ResultsWriter(run_dir)
    series = SeriesBuilder()
    clouds: CloudWriter | None = None
    snapshot = cfg = None
    pos = 0
    t_first = None
    progress.set_stage("opening")
    try:
        if rec["kind"] == "jsonl":
            source = iter_jsonl(rec["path"], int(opts["every"]), int(opts["start"]), opts.get("limit"))
            progress.set_stage("processing")
            t_start = time.perf_counter()
            for d in source:
                stamp = d.get("stamp")
                if isinstance(stamp, (int, float)):
                    t_first = stamp if t_first is None else t_first
                    d["t"] = round(float(stamp) - t_first, 3)
                else:
                    d["t"] = round(pos * 0.1, 3)
                d.setdefault("frame_id", "")
                d["decision"] = decision_of(d)
                d["pos"] = pos
                writer.write(d)
                series.add(d)
                progress.frame(d)
                pos += 1
        else:
            from resense import Detector

            from resense_web import params
            try:
                cfg = params.build_config(spec.get("overrides") or {})
            except ValueError as exc:
                raise WorkerError(str(exc)) from exc
            try:
                snapshot = params.config_snapshot(spec.get("overrides") or {})
            except Exception:
                snapshot = None
            det = Detector(cfg)
            source = open_frames(spec, cfg)
            if opts.get("clouds"):
                clouds = CloudWriter(run_dir, int(opts["cloud_points"]), cloud_stride(spec.get("frames_total")))
            ego_speed = opts.get("ego_speed")
            progress.set_stage("processing")
            t_start = time.perf_counter()
            for idx, frame in source:
                res = det.process(frame, ego_speed=ego_speed)
                d = res.to_dict()
                if t_first is None:
                    t_first = frame.stamp
                d["frame"] = int(idx)
                d["frame_id"] = frame.frame_id
                d["t"] = round(float(frame.stamp) - float(t_first), 3)
                d["decision"] = decision_of(d)
                d["pos"] = pos
                writer.write(d)
                series.add(d)
                if clouds is not None and clouds.wants(pos):
                    xyz = res.xyz if res.xyz is not None else frame.xyz
                    blob, _n = pack_frame_cloud(xyz, processed_intensity(frame, xyz), res.corridor_idx,
                                                d["detections"], d["warnings"], clouds.budget, seed=(20260929, pos))
                    clouds.add(pos, blob)
                progress.frame(d)
                pos += 1
        wall = time.perf_counter() - t_start
    except BaseException:
        writer.abort()
        if clouds is not None:
            clouds.abort()
        progress.write(force=True)
        raise
    if pos == 0:
        writer.abort()
        raise WorkerError("Не прочитано ни одного кадра — проверьте топик и диапазон кадров")
    writer.close()
    if clouds is not None:
        clouds.close()
    print(f"processed {pos} frames in {wall:.1f} s ({pos / max(wall, 1e-6):.1f} fps)", flush=True)

    eval_summary = labels_in_gauge = None
    labels_path = spec.get("labels_path")
    if labels_path:
        progress.set_stage("evaluating")
        from resense_web import evaluation
        try:
            labels_in_gauge = evaluation.labels_in_gauge(series.frame, Path(labels_path))
        except Exception:
            traceback.print_exc()
            print("labels_in_gauge failed; the series has no labels", flush=True)
        if opts.get("evaluate", True):
            try:
                eval_summary = evaluation.evaluate(iter_results(run_dir), Path(labels_path), cfg=cfg)
                if spec.get("labels_name"):          # the name the recording shows, not the file name
                    eval_summary["labels_name"] = spec["labels_name"]
            except Exception:
                traceback.print_exc()
                print("evaluation failed; the run has no scores", flush=True)

    progress.set_stage("finalizing")
    episodes = episodes_of(series.frame, series.t, series.decisions, series.nearest)
    summary = run_summary(series, pos / max(wall, 1e-6), eval_summary, episodes)
    atomic_write_json(run_dir / "series.json", series.series(labels_in_gauge))
    atomic_write_json(run_dir / "summary.json", {
        "summary": summary, "episodes": episodes, "events": events_of(episodes),
        "job_id": spec["job_id"], "recording": {"id": rec["id"], "name": rec["name"], "kind": rec["kind"]},
        "preset": spec["preset"], "overrides": spec.get("overrides") or {}, "options": opts,
        "labels_path": labels_path, "config": snapshot,
    })
    progress.set_stage("done")
    return summary


def user_message(exc: BaseException, pos: int | None) -> str:
    if isinstance(exc, WorkerError):
        return str(exc)
    if isinstance(exc, MemoryError):
        return "Недостаточно памяти для обработки"
    if isinstance(exc, FileNotFoundError):
        return "Файлы записи не найдены на сервере"
    if isinstance(exc, RuntimeError) and "no PointCloud2 topic" in str(exc):
        return "В записи нет облаков точек на выбранном топике"
    where = f" на кадре {pos}" if pos else ""
    return f"Ошибка обработки{where} ({type(exc).__name__}) — подробности в журнале"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m resense_web.worker <job_id>", file=sys.stderr)
        return 2
    job_dir = get_settings().jobs_dir / argv[0]
    spec = read_json(job_dir / "spec.json")
    if not isinstance(spec, dict):
        print(f"no spec.json in {job_dir}", file=sys.stderr)
        atomic_write_json(job_dir / "result.json", {"status": "failed", "error": "Задание для обработки не найдено"})
        return 1
    progress = Progress(job_dir / "progress.json", spec.get("frames_total"))
    try:
        summary = run_job(spec, progress)
    except BaseException as exc:
        traceback.print_exc()
        sys.stderr.flush()
        atomic_write_json(job_dir / "result.json", {"status": "failed", "error": user_message(exc, progress.done)})
        return 1
    atomic_write_json(job_dir / "result.json", {"status": "done", "run_id": spec["run_id"],
                                                "n_frames": summary["n_frames"],
                                                "source_kind": spec["recording"]["kind"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
