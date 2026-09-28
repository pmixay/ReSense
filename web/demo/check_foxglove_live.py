#!/usr/bin/env python3
"""Check the committed Foxglove layout against a running foxglove_bridge.

Start detector, bridge and bag player first. Requires ``pip install websockets``.
This checks channel names and live messages; open the layout in Foxglove to check its rendering.
With --require-freshness it also requires a current frame status within the node's age bounds
at receipt. The viewer and node must have synchronized UTC clocks, as for the live dashboard.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
import struct
import time

LAYOUT = Path(__file__).resolve().parents[1] / "foxglove_layout.json"
LIVE_TOPICS = {
    "/resense/decision",
    "/resense/status",
    "/resense/corridor_points",
    "/resense/markers",
}


def layout_topics(path: Path) -> set[str]:
    config = json.loads(path.read_text(encoding="utf-8"))["configById"]
    topics = set()
    for panel in config.values():
        topics.update(panel.get("topics", {}))
        if panel.get("topicPath"):
            topics.add(panel["topicPath"])
        if panel.get("path"):
            topics.add(panel["path"].removesuffix(".data"))
        topics.update(item["value"].removesuffix(".data") for item in panel.get("paths", []))
    return topics


def current_status(payload: bytes, now: float) -> bool:
    """Decode CDR std_msgs/String and reject stale, unknown or held-only result evidence."""
    try:
        if len(payload) < 9 or payload[:2] not in (b"\x00\x00", b"\x00\x01"):
            return False
        endian = "<" if payload[1] else ">"
        size = struct.unpack_from(endian + "I", payload, 4)[0]
        if size < 1 or size > len(payload) - 8 or payload[8 + size - 1] != 0:
            return False
        res = json.loads(payload[8:8 + size - 1].decode("utf-8"))
        if not isinstance(res, dict) or res.get("snapshot_kind") != "frame" or res.get("stop_held"):
            return False
        if res.get("decision") not in ("GO", "CAUTION", "STOP"):
            return False
        if type(res.get("obstacle")) is not bool:
            return False
        if res.get("health", {}).get("level") == "error":
            return False
        f = res.get("freshness")
        if not isinstance(f, dict) or f.get("valid") is not True or f.get("reason") != "current":
            return False
        if f.get("go_allowed") is not (res["decision"] == "GO"):
            return False
        clocks = {"live": "acquisition_utc", "replay": "publisher_utc"}
        if f.get("mode") not in clocks or f.get("clock_reference") != clocks[f["mode"]]:
            return False
        names = ("evaluated_at_utc_s", "max_result_age_s", "future_tolerance_s",
                 "source_age_s", "residence_age_s", "queue_lag_s")
        if any(type(f.get(key)) not in (int, float) or not math.isfinite(f[key]) for key in names):
            return False
        bound, tolerance = f["max_result_age_s"], f["future_tolerance_s"]
        if not 0 < bound <= 0.5 or not 0 <= tolerance <= 0.05:
            return False
        transport = now - f["evaluated_at_utc_s"]
        if transport < -tolerance or f["source_age_s"] < -tolerance or f["residence_age_s"] < 0:
            return False
        elapsed = max(0.0, transport)
        if any(max(0.0, f[key]) + elapsed > bound for key in ("source_age_s", "residence_age_s")):
            return False
        if not 0 <= f["queue_lag_s"] <= 1e-6 or res.get("node", {}).get("catchup"):
            return False
        return True
    except (ValueError, TypeError, AttributeError, UnicodeError, struct.error):
        return False


async def check(url: str, timeout: float, layout: Path, require_freshness: bool = False) -> None:
    import websockets

    expected = layout_topics(layout)
    raw_clouds = {"/lidar_points", "/sensing/lidar/hesai128/pointcloud"}
    required = (expected - raw_clouds) | LIVE_TOPICS
    deadline = time.monotonic() + timeout
    async with websockets.connect(url, subprotocols=["foxglove.sdk.v1"], max_size=None) as ws:
        advertised = {}
        channels = {}
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), deadline - time.monotonic())
            except asyncio.TimeoutError:
                break
            if not isinstance(raw, str):
                continue
            msg = json.loads(raw)
            if msg.get("op") == "advertise":
                channels.update({ch["topic"]: ch for ch in msg["channels"]})
                advertised.update({ch["topic"]: ch["id"] for ch in msg["channels"]})
                if required <= advertised.keys() and raw_clouds & advertised.keys():
                    break

        # Bags use one of two raw-cloud topic names; every other layout topic must exist.
        missing = required - advertised.keys()
        if missing or not (raw_clouds & advertised.keys()):
            raise RuntimeError(f"layout topics unavailable: {sorted(missing or raw_clouds)}")
        if require_freshness:
            channel = channels["/resense/status"]
            if channel.get("encoding") != "cdr" or channel.get("schemaName") != "std_msgs/msg/String":
                raise RuntimeError("freshness probe requires the ROS 2 CDR std_msgs/String status channel")

        ids = {i: topic for i, topic in enumerate(sorted(LIVE_TOPICS), 1)}
        await ws.send(json.dumps({"op": "subscribe", "subscriptions": [
            {"id": i, "channelId": advertised[topic]} for i, topic in ids.items()
        ]}))
        received = set()
        fresh = not require_freshness
        while time.monotonic() < deadline and (received != LIVE_TOPICS or not fresh):
            try:
                raw = await asyncio.wait_for(ws.recv(), deadline - time.monotonic())
            except asyncio.TimeoutError:
                break
            # Foxglove messageData: one opcode byte, uint32 subscription ID, uint64 timestamp, payload.
            if isinstance(raw, bytes) and len(raw) >= 13 and raw[0] == 1:
                sub_id = struct.unpack_from("<I", raw, 1)[0]
                if sub_id in ids:
                    received.add(ids[sub_id])
                    if require_freshness and ids[sub_id] == "/resense/status":
                        fresh = fresh or current_status(raw[13:], time.time())
        if received != LIVE_TOPICS:
            raise RuntimeError(f"no live messages on: {sorted(LIVE_TOPICS - received)}")
        if not fresh:
            raise RuntimeError("no current fresh frame status received within the timeout")
        print(f"PASS: {len(expected)} layout topics available; live messages on {', '.join(sorted(received))}")
        if require_freshness:
            print("PASS: a current frame status arrived within source, residence and transport age bounds")


def main() -> None:
    import websockets

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="ws://127.0.0.1:8765")
    ap.add_argument("--layout", type=Path, default=LAYOUT)
    ap.add_argument("--timeout", type=float, default=20)
    ap.add_argument("--require-freshness", action="store_true",
                    help="require a current non-held frame status (UTC clocks synchronized; max age 0.5 s)")
    args = ap.parse_args()
    try:
        asyncio.run(check(args.url, args.timeout, args.layout, args.require_freshness))
    except (OSError, asyncio.TimeoutError, RuntimeError, websockets.WebSocketException) as exc:
        raise SystemExit(f"FAIL: {exc}") from exc


if __name__ == "__main__":
    main()
