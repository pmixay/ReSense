"""The job queue: a background thread in the API process that runs exactly one worker subprocess
(``python -m resense_web.worker <job_id>``) at a time, in queue order.

The worker never touches the database. The manager writes ``jobs/<id>/spec.json`` (everything
the worker needs), the worker writes ``progress.json`` (atomically, at most ~5 times a second) and
``result.json`` into the same folder and the run files into ``runs/<run_id>/``; when the process
exits the manager records the outcome (a Run row on success). Cancelling kills the worker's
process group and removes the partial run folder."""
from __future__ import annotations

import logging
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from resense_web import presets as presets_mod
from resense_web import recordings as rec_mod
from resense_web import runs as runs_mod
from resense_web.db import Database, jload
from resense_web.settings import BACKEND_DIR, Settings
from resense_web.util import atomic_write_json, dumps, new_id, now_iso, read_json, tail_text

log = logging.getLogger("resense_web.jobs")

TERMINAL = ("done", "failed", "cancelled")
INTERRUPTED = "прервано перезапуском сервера"
DEFAULT_OPTIONS = {"topic": None, "every": 1, "start": 0, "limit": None, "clouds": True,
                   "cloud_points": 30000, "ego_speed": None, "evaluate": True}


class JobError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def frames_total(n_frames: int | None, opts: dict) -> int | None:
    if n_frames is None:
        return None
    total = max(0, math.ceil((int(n_frames) - int(opts.get("start") or 0)) / max(1, int(opts.get("every") or 1))))
    if opts.get("limit"):
        total = min(total, int(opts["limit"]))
    return total


def empty_progress(total: int | None, stage: str = "queued") -> dict:
    return {"frames_done": 0, "frames_total": total, "fps": None, "eta_s": None, "stage": stage,
            "stage_ms": {}, "decisions": "", "last": None}


def default_command(job_id: str) -> list[str]:
    return [sys.executable, "-m", "resense_web.worker", job_id]


class JobManager:
    KILL_GRACE_S = 5.0
    POLL_S = 0.2

    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db
        self.worker_command: Callable[[str], list[str]] = default_command
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._proc: subprocess.Popen | None = None
        self._current: str | None = None
        self._kill_at: float | None = None
        self._log_fh = None

    # -- lifecycle --------------------------------------------------------------------------------
    def start(self) -> None:
        self.recover()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="resense-jobs", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
        with self._lock:
            if self._proc is None or self._current is None:
                return
            rc = self._proc.poll()
            if rc is not None:            # finished just before the shutdown: record it normally
                self._reap(rc)
                return
            job_id = self._current
            self._signal(signal.SIGTERM)
            try:
                self._proc.wait(self.KILL_GRACE_S)
            except subprocess.TimeoutExpired:
                self._signal(signal.SIGKILL)
                try:
                    self._proc.wait(5)
                except subprocess.TimeoutExpired:
                    log.error("worker of job %s did not die", job_id)
            if self._log_fh is not None:
                self._log_fh.close()
                self._log_fh = None
            row = self.get(job_id)
            if row and row["status"] == "running":
                self._fail(row, INTERRUPTED)
            elif row:
                self._cleanup_run(row)
            self._clear_current()

    def recover(self) -> None:
        """Jobs left ``running`` by a previous server process failed; kill a leftover worker."""
        for row in self.db.query("SELECT * FROM jobs WHERE status = 'running'"):
            self._kill_orphan(row)
            self._fail(row, INTERRUPTED)

    def notify(self) -> None:
        self._wake.set()

    # -- queries ----------------------------------------------------------------------------------
    def job_dir(self, job_id: str) -> Path:
        return self.settings.jobs_dir / job_id

    def get(self, job_id: str) -> dict | None:
        return self.db.one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    def positions(self) -> dict[str, int]:
        rows = self.db.query("SELECT id FROM jobs WHERE status = 'queued' ORDER BY seq")
        return {r["id"]: i + 1 for i, r in enumerate(rows)}

    def list(self, statuses: set[str] | None = None) -> list[dict]:
        rows = self.db.query("SELECT * FROM jobs")
        if statuses:
            rows = [r for r in rows if r["status"] in statuses]
        rank = {"running": 0, "queued": 1}
        running = [r for r in rows if r["status"] == "running"]
        queued = sorted((r for r in rows if r["status"] == "queued"), key=lambda r: r["seq"])
        done = sorted((r for r in rows if r["status"] not in rank),
                      key=lambda r: (r["finished_at"] or r["created_at"], r["seq"]), reverse=True)
        return running + queued + done

    def progress(self, row: dict) -> dict:
        if row["status"] == "running":
            p = read_json(self.job_dir(row["id"]) / "progress.json")
            return p if isinstance(p, dict) else empty_progress(row["frames_total"], "opening")
        if row["status"] == "queued":
            return empty_progress(row["frames_total"], "queued")
        stored = jload(row["progress"], None)
        if isinstance(stored, dict):
            return stored
        # cancelled while running and not reaped yet: the worker's last snapshot is still on disk
        p = read_json(self.job_dir(row["id"]) / "progress.json") if row["started_at"] else None
        return p if isinstance(p, dict) else empty_progress(row["frames_total"], "queued")

    def to_api(self, row: dict, positions: dict[str, int] | None = None) -> dict:
        if positions is None:
            positions = self.positions() if row["status"] == "queued" else {}
        return {
            "id": row["id"], "recording_id": row["recording_id"], "recording_name": row["recording_name"],
            "preset_id": row["preset_id"], "preset_name": row["preset_name"],
            "options": {**DEFAULT_OPTIONS, **jload(row["options"], {})}, "status": row["status"],
            "position": positions.get(row["id"]) if row["status"] == "queued" else None,
            "progress": self.progress(row), "error": row["error"],
            "run_id": row["run_id"] if row["status"] == "done" else None,
            "created_at": row["created_at"], "started_at": row["started_at"], "finished_at": row["finished_at"],
        }

    def log_tail(self, job_id: str, max_bytes: int = 65536) -> str:
        return tail_text(self.job_dir(job_id) / "worker.log", max_bytes)

    # -- commands ---------------------------------------------------------------------------------
    def create(self, recording: dict, preset: dict, options: dict) -> dict:
        opts = {**DEFAULT_OPTIONS, **options}
        if recording["kind"] == "jsonl":
            opts["clouds"] = False
            opts["topic"] = None
        topics = jload(recording["topics"], [])
        if opts.get("topic") and recording["kind"] == "rosbag2":
            if opts["topic"] not in {t["name"] for t in topics}:
                raise JobError(422, f"Топик {opts['topic']} не найден в записи")
            ttype = next(t["type"] for t in topics if t["name"] == opts["topic"])
            if ttype != "sensor_msgs/msg/PointCloud2":
                raise JobError(422, f"Топик {opts['topic']} — не облако точек (PointCloud2)")
        n_frames = recording["n_frames"]
        if opts.get("topic") and recording["kind"] == "rosbag2":
            n_frames = next((t["count"] for t in topics if t["name"] == opts["topic"]), n_frames)
        if n_frames is not None and opts["start"] >= n_frames:
            raise JobError(422, f"Начальный кадр {opts['start']} за пределами записи ({n_frames} кадров)")
        row = {
            "id": new_id(), "recording_id": recording["id"], "recording_name": recording["name"],
            "preset_id": preset["id"], "preset_name": preset["name"], "overrides": dumps(preset["overrides"]),
            "options": dumps(opts), "frames_total": frames_total(n_frames, opts), "status": "queued",
            "created_at": now_iso(),
        }
        self.db.insert("jobs", row)
        self.notify()
        return self.get(row["id"])

    def cancel(self, job_id: str) -> dict:
        with self._lock:
            row = self.get(job_id)
            if row is None:
                raise JobError(404, "Задача не найдена")
            if row["status"] == "queued":
                self.db.update("jobs", job_id, {"status": "cancelled", "finished_at": now_iso()})
            elif row["status"] == "running":
                self.db.update("jobs", job_id, {"status": "cancelled", "finished_at": now_iso()})
                if self._current == job_id and self._proc is not None:
                    self._signal(signal.SIGTERM)
                    self._kill_at = time.monotonic() + self.KILL_GRACE_S
                else:   # not ours (should not happen): nothing to reap, clean up now
                    self._cleanup_run(self.get(job_id))
            else:
                raise JobError(409, "Задача уже завершена")
        self.notify()
        return self.get(job_id)

    def retry(self, job_id: str) -> dict:
        row = self.get(job_id)
        if row is None:
            raise JobError(404, "Задача не найдена")
        if row["status"] not in TERMINAL:
            raise JobError(409, "Задача ещё не завершена")
        rec = rec_mod.get(self.db, row["recording_id"])
        if rec is None:
            raise JobError(409, "Запись этой задачи удалена")
        preset = presets_mod.get(self.db, row["preset_id"])
        if preset is None:
            raise JobError(409, "Набор параметров этой задачи удалён")
        return self.create(rec, preset, jload(row["options"], {}))

    def delete(self, job_id: str) -> None:
        row = self.get(job_id)
        if row is None:
            raise JobError(404, "Задача не найдена")
        if row["status"] not in TERMINAL:
            raise JobError(409, "Задача ещё выполняется — сначала отмените её")
        self._forget(row)

    def clear_finished(self) -> int:
        rows = self.db.query("SELECT * FROM jobs WHERE status IN ('done', 'failed', 'cancelled')")
        for row in rows:
            self._forget(row)
        return len(rows)

    def cancel_for_recording(self, rec_id: str) -> None:
        """Before a recording is deleted: cancel its queued jobs; refuse while one is running."""
        with self._lock:
            if self.db.one("SELECT id FROM jobs WHERE recording_id = ? AND status = 'running'", (rec_id,)):
                raise JobError(409, "Запись сейчас обрабатывается — сначала отмените задачу")
            self.db.execute("UPDATE jobs SET status = 'cancelled', finished_at = ? "
                            "WHERE recording_id = ? AND status = 'queued'", (now_iso(), rec_id))

    # -- internals --------------------------------------------------------------------------------
    def _forget(self, row: dict) -> None:
        self.db.execute("DELETE FROM jobs WHERE id = ?", (row["id"],))
        self.db.execute("UPDATE runs SET job_id = NULL WHERE job_id = ?", (row["id"],))
        shutil.rmtree(self.job_dir(row["id"]), ignore_errors=True)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:   # the queue must survive anything a single job does
                log.exception("job manager tick failed")
            busy = self._proc is not None
            self._wake.wait(self.POLL_S if busy else 1.0)
            self._wake.clear()

    def _tick(self) -> None:
        with self._lock:
            if self._proc is not None:
                rc = self._proc.poll()
                if rc is None:
                    if self._kill_at is not None and time.monotonic() >= self._kill_at:
                        self._signal(signal.SIGKILL)
                        self._kill_at = None
                    return
                self._reap(rc)
            if not self._stop.is_set():
                self._start_next()

    def _start_next(self) -> None:
        row = self.db.one("SELECT * FROM jobs WHERE status = 'queued' ORDER BY seq LIMIT 1")
        if row is None:
            return
        rec = rec_mod.get(self.db, row["recording_id"])
        if rec is None:
            self._fail(row, "Запись удалена")
            self._wake.set()
            return
        run_id = new_id()
        run_dir = runs_mod.run_dir(self.settings, run_id)
        job_dir = self.job_dir(row["id"])
        job_dir.mkdir(parents=True, exist_ok=True)
        for f in ("progress.json", "result.json"):
            try:
                (job_dir / f).unlink()
            except OSError:
                pass
        run_dir.mkdir(parents=True, exist_ok=True)
        labels = labels_name = None
        try:
            labels = rec_mod.labels_path(self.settings, rec)
            labels_name = rec_mod.labels_state(self.settings, rec)["name"] if labels else None
        except Exception:
            log.exception("labels lookup failed")
        spec = {
            "job_id": row["id"], "run_id": run_id, "run_dir": str(run_dir), "job_dir": str(job_dir),
            "recording": {"id": rec["id"], "name": rec["name"], "kind": rec["kind"], "path": rec["path"],
                          "default_topic": rec["default_topic"], "meta": jload(rec["meta"], {})},
            "preset": {"id": row["preset_id"], "name": row["preset_name"]},
            "overrides": jload(row["overrides"], {}),
            "options": {**DEFAULT_OPTIONS, **jload(row["options"], {})},
            "frames_total": row["frames_total"],
            "labels_path": str(labels) if labels else None,
            "labels_name": labels_name,
        }
        atomic_write_json(job_dir / "spec.json", spec)
        atomic_write_json(job_dir / "progress.json", empty_progress(row["frames_total"], "opening"))
        env = dict(os.environ)
        env["RESENSE_WEB_DATA"] = str(self.settings.data_dir)
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONPATH"] = os.pathsep.join(p for p in (str(BACKEND_DIR), env.get("PYTHONPATH", "")) if p)
        self._log_fh = open(job_dir / "worker.log", "ab")
        try:
            proc = subprocess.Popen(self.worker_command(row["id"]), stdout=self._log_fh, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, env=env, start_new_session=True,
                                    cwd=str(self.settings.data_dir))
        except OSError as exc:
            self._log_fh.close()
            self._log_fh = None
            shutil.rmtree(run_dir, ignore_errors=True)
            self._fail(row, f"Не удалось запустить обработку: {exc.strerror or exc}")
            return
        self._proc = proc
        self._current = row["id"]
        self._kill_at = None
        self.db.update("jobs", row["id"], {"status": "running", "started_at": now_iso(), "run_id": run_id,
                                           "pid": proc.pid, "error": None})

    def _reap(self, rc: int) -> None:
        job_id = self._current
        row = self.get(job_id) if job_id else None
        if self._log_fh is not None:
            self._log_fh.close()
            self._log_fh = None
        self._clear_current()
        if row is None:
            return
        job_dir = self.job_dir(row["id"])
        progress = read_json(job_dir / "progress.json")
        if not isinstance(progress, dict):
            progress = empty_progress(row["frames_total"], "opening")
        result = read_json(job_dir / "result.json", {}) or {}
        if row["status"] == "cancelled":
            self._cleanup_run(row)
            self.db.update("jobs", row["id"], {"progress": dumps(progress), "pid": None})
            return
        if rc == 0 and result.get("status") == "done" and row["run_id"]:
            try:
                rec = rec_mod.get(self.db, row["recording_id"])
                kind = rec["kind"] if rec else result.get("source_kind", "rosbag2")
                runs_mod.insert_from_job(self.db, self.settings, row, row["run_id"], kind)
                try:
                    shutil.copyfile(job_dir / "worker.log", runs_mod.run_dir(self.settings, row["run_id"]) / "worker.log")
                except OSError:
                    pass
                progress["stage"] = "done"
                self.db.update("jobs", row["id"], {"status": "done", "finished_at": now_iso(),
                                                   "progress": dumps(progress), "pid": None})
                return
            except Exception:
                log.exception("could not register run of job %s", row["id"])
                result = {"error": "Не удалось сохранить результаты обработки"}
        if rc < 0:
            default = f"Процесс обработки остановлен сигналом {-rc}"
        else:
            default = f"Процесс обработки завершился с ошибкой (код {rc})"
        self.db.update("jobs", row["id"], {"progress": dumps(progress)})
        self._fail(self.get(row["id"]), result.get("error") or default)

    def _fail(self, row: dict, message: str) -> None:
        self._cleanup_run(row)
        changes = {"status": "failed", "error": message, "finished_at": now_iso(), "pid": None}
        if not row.get("progress"):
            progress = read_json(self.job_dir(row["id"]) / "progress.json")
            if isinstance(progress, dict):
                changes["progress"] = dumps(progress)
        self.db.update("jobs", row["id"], changes)

    def _cleanup_run(self, row: dict | None) -> None:
        """Remove the partial run folder of an unfinished job (a registered Run is never touched)."""
        if not row or not row.get("run_id"):
            return
        if runs_mod.get(self.db, row["run_id"]) is None:
            runs_mod.remove(self.settings, row["run_id"])

    def _clear_current(self) -> None:
        self._proc = None
        self._current = None
        self._kill_at = None

    def _signal(self, sig: int) -> None:
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            try:
                proc.send_signal(sig)
            except OSError:
                pass

    def _kill_orphan(self, row: dict) -> None:
        pid = row.get("pid")
        if not pid:
            return
        try:
            with open(f"/proc/{int(pid)}/cmdline", "rb") as fh:
                cmd = fh.read()
        except OSError:
            return
        if b"resense_web.worker" in cmd and row["id"].encode() in cmd:
            try:
                os.killpg(int(pid), signal.SIGKILL)
            except OSError:
                pass
