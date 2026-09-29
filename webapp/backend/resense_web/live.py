"""WS ``/api/live/sim``: replay a finished run as if the ROS node were publishing it live.

One JSON message per frame at 10 Hz x ``speed``: the run's ``/frames`` dict plus
``{"node": {"fps", "latency_ms", "frames", "dropped_frames"}, "snapshot_kind": "frame",
"sim": true, "cloud_pos"}``. The client may send ``{"cmd": "pause" | "play" | "seek" | "speed",
"pos"?: number, "speed"?: number}``. At the end the replay loops (``loop=true``) or closes with
1000. Close codes: 4400 bad query, 4404 unknown run.
"""
from __future__ import annotations

import asyncio
import bisect
import json
import logging
import math
import os
import re
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)
router = APIRouter()

RATE_HZ = 10.0
SPEED_RANGE = (0.25, 10.0)
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
CLOSE_NORMAL = 1000
CLOSE_BAD_REQUEST = 4400
CLOSE_NOT_FOUND = 4404
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def _runs_dir(ws: WebSocket) -> Path:
    """The runs folder of the app serving ``ws`` (``create_app(settings)``), else of the env."""
    ctx = getattr(ws.app.state, "ctx", None)
    if ctx is not None:
        return Path(ctx.settings.runs_dir)
    from resense_web.settings import get_settings
    return Path(get_settings().data_dir) / "runs"


class _Results:
    """Random access to the lines of ``results.jsonl`` through a byte-offset index, built (or
    taken from ``results.idx`` when it matches the file) off the event loop."""

    def __init__(self, path: Path):
        self.path = path
        self.offsets = np.zeros(1, dtype=np.int64)
        self._fd: int | None = None

    def open(self) -> int:
        self._fd = os.open(self.path, os.O_RDONLY)
        size = os.fstat(self._fd).st_size
        idx = self.path.with_name("results.idx")
        try:
            arr = np.fromfile(idx, dtype="<u8").astype(np.int64)
            if arr.size >= 1 and int(arr[-1]) == size and arr[0] == 0 and np.all(np.diff(arr) > 0):
                self.offsets = arr
                return len(self)
        except (OSError, ValueError):
            pass
        starts, base = [0], 0
        with open(self.path, "rb") as fh:
            while chunk := fh.read(8 << 20):
                nl = np.flatnonzero(np.frombuffer(chunk, dtype=np.uint8) == 10)
                starts.extend((nl + base + 1).tolist())
                base += len(chunk)
        if starts[-1] != base:
            starts.append(base)
        offs = np.asarray(starts, dtype=np.int64)
        keep = np.ones(offs.size, dtype=bool)
        keep[1:][np.diff(offs) <= 1] = False           # blank lines
        self.offsets = offs[keep]
        return len(self)

    def __len__(self) -> int:
        return max(0, int(self.offsets.size) - 1)

    def read(self, pos: int) -> dict:
        a, b = int(self.offsets[pos]), int(self.offsets[pos + 1])
        return json.loads(os.pread(self._fd, b - a, a))

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


def _cloud_positions(run_dir: Path) -> list[int]:
    try:
        with open(run_dir / "clouds.json", encoding="utf-8") as fh:
            frames = json.load(fh).get("frames") or []
        return sorted({int(p) for p in frames})
    except (OSError, ValueError, TypeError, AttributeError):
        return []


def cloud_pos_for(positions: list[int], pos: int) -> int | None:
    """``pos`` when it has a stored cloud, else the nearest earlier position that has one."""
    i = bisect.bisect_right(positions, pos) - 1
    return positions[i] if i >= 0 else None


def _num(raw) -> float | None:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


@dataclass
class _State:
    total: int
    speed: float
    loop: bool
    pos: int = 0
    paused: bool = False
    seek_to: int | None = None
    closed: bool = False


def _apply(cmd: dict, st: _State) -> None:
    """A client command; unknown or malformed commands are ignored."""
    if not isinstance(cmd, dict):
        return
    speed = _num(cmd.get("speed")) if "speed" in cmd else None
    if speed is not None and speed > 0:
        st.speed = min(max(speed, SPEED_RANGE[0]), SPEED_RANGE[1])
    kind = cmd.get("cmd")
    if kind == "pause":
        st.paused = True
    elif kind == "play":
        st.paused = False
    elif kind == "seek":
        p = _num(cmd.get("pos"))
        if p is not None and st.total > 0:
            st.seek_to = int(min(max(int(p), 0), st.total - 1))


async def _receive(ws: WebSocket, st: _State, wake: asyncio.Event) -> None:
    try:
        while not st.closed:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            try:
                cmd = json.loads(msg.get("text") or msg.get("bytes") or b"")
            except ValueError:
                continue
            _apply(cmd, st)
            wake.set()
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        st.closed = True
        wake.set()


async def _close(ws: WebSocket, code: int, reason: str) -> None:
    try:
        await ws.close(code=code, reason=reason)
    except (RuntimeError, OSError, WebSocketDisconnect):
        pass


async def _stream(ws: WebSocket, res: _Results, clouds: list[int], st: _State, wake: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    next_t = loop.time()
    sent = 0
    recent: deque = deque(maxlen=20)
    while not st.closed:
        forced = False
        if st.seek_to is not None:
            st.pos, st.seek_to = st.seek_to, None
            forced = True
            recent.clear()
        elif st.paused:
            wake.clear()
            if st.paused and st.seek_to is None and not st.closed:
                await wake.wait()
            next_t = loop.time()
            recent.clear()
            continue
        else:
            delay = next_t - loop.time()
            if delay > 0:
                wake.clear()
                try:
                    await asyncio.wait_for(wake.wait(), timeout=delay)
                    continue                     # a command arrived: re-evaluate the state first
                except asyncio.TimeoutError:
                    pass
        if st.pos >= st.total:
            if st.loop and st.total > 0:
                st.pos = 0
            else:
                await _close(ws, CLOSE_NORMAL, "Конец записи")
                return
        frame = await asyncio.to_thread(res.read, st.pos)
        pos = int(frame.get("pos", st.pos))
        sent += 1
        now = time.monotonic()
        recent.append(now)
        fps = (len(recent) - 1) / (recent[-1] - recent[0]) if len(recent) >= 2 and recent[-1] > recent[0] \
            else RATE_HZ * st.speed
        latency = (frame.get("timing_ms") or {}).get("total")
        frame.update({
            "pos": pos,
            "node": {"fps": round(fps, 2), "latency_ms": latency, "frames": sent, "dropped_frames": 0},
            "snapshot_kind": "frame",
            "sim": True,
            "cloud_pos": cloud_pos_for(clouds, pos),
        })
        await ws.send_text(json.dumps(frame, ensure_ascii=False, separators=(",", ":")))
        st.pos += 1
        period = 1.0 / (RATE_HZ * st.speed)
        next_t = loop.time() + period if forced else max(next_t + period, loop.time() - period)
        if not st.loop and st.pos >= st.total and not st.paused:
            await _close(ws, CLOSE_NORMAL, "Конец записи")
            return


@router.websocket("/api/live/sim")
async def live_sim(websocket: WebSocket) -> None:
    await websocket.accept()
    q = websocket.query_params
    run_id = q.get("run_id", "")
    if not RUN_ID_RE.match(run_id):
        await _close(websocket, CLOSE_BAD_REQUEST, "Не указан или неверен run_id")
        return
    speed = _num(q.get("speed", "1"))
    if speed is None or not SPEED_RANGE[0] <= speed <= SPEED_RANGE[1]:
        await _close(websocket, CLOSE_BAD_REQUEST, "Скорость должна быть от 0,25 до 10")
        return
    loop_raw = q.get("loop", "false").strip().lower()
    if loop_raw not in _TRUE | _FALSE:
        await _close(websocket, CLOSE_BAD_REQUEST, "Параметр loop: true или false")
        return
    run_dir = _runs_dir(websocket) / run_id
    res = _Results(run_dir / "results.jsonl")
    try:
        total = await asyncio.to_thread(res.open)
    except OSError:
        res.close()
        await _close(websocket, CLOSE_NOT_FOUND, "Прогон не найден")
        return
    clouds = await asyncio.to_thread(_cloud_positions, run_dir)
    st = _State(total=total, speed=speed, loop=loop_raw in _TRUE)
    wake = asyncio.Event()
    receiver = asyncio.create_task(_receive(websocket, st, wake))
    try:
        if total == 0:
            await _close(websocket, CLOSE_NORMAL, "В прогоне нет кадров")
        else:
            await _stream(websocket, res, clouds, st, wake)
    except (WebSocketDisconnect, RuntimeError, OSError) as e:
        log.debug("live sim %s: client gone (%s)", run_id, e)
    except Exception:                                   # a broken line must not kill the server loop
        log.exception("live sim %s failed", run_id)
        await _close(websocket, 1011, "Ошибка чтения прогона")
    finally:
        st.closed = True
        receiver.cancel()
        try:
            await receiver
        except (asyncio.CancelledError, Exception):
            pass
        res.close()
