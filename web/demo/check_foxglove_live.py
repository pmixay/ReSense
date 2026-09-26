#!/usr/bin/env python3
"""Check the committed Foxglove layout against a running foxglove_bridge.

Start detector, bridge and bag player first. Requires ``pip install websockets``.
This checks channel names and live messages; open the layout in Foxglove to check its rendering.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import struct
import time

import websockets

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


async def check(url: str, timeout: float, layout: Path) -> None:
    expected = layout_topics(layout)
    deadline = time.monotonic() + timeout
    async with websockets.connect(url, subprotocols=["foxglove.sdk.v1"], max_size=None) as ws:
        advertised = {}
        while time.monotonic() < deadline:
            raw = await asyncio.wait_for(ws.recv(), deadline - time.monotonic())
            if not isinstance(raw, str):
                continue
            msg = json.loads(raw)
            if msg.get("op") == "advertise":
                advertised.update({ch["topic"]: ch["id"] for ch in msg["channels"]})
                if LIVE_TOPICS <= advertised.keys():
                    break
        else:
            raise RuntimeError("bridge did not advertise the detector's live topics")

        # Bags use one of two raw-cloud topic names; every other layout topic must exist.
        raw_clouds = {"/lidar_points", "/sensing/lidar/hesai128/pointcloud"}
        missing = (expected - raw_clouds) - advertised.keys()
        if missing or not (raw_clouds & advertised.keys()):
            raise RuntimeError(f"layout topics unavailable: {sorted(missing or raw_clouds)}")

        ids = {i: topic for i, topic in enumerate(sorted(LIVE_TOPICS), 1)}
        await ws.send(json.dumps({"op": "subscribe", "subscriptions": [
            {"id": i, "channelId": advertised[topic]} for i, topic in ids.items()
        ]}))
        received = set()
        while time.monotonic() < deadline and received != LIVE_TOPICS:
            raw = await asyncio.wait_for(ws.recv(), deadline - time.monotonic())
            # Foxglove messageData: one opcode byte, uint32 subscription ID, uint64 timestamp, payload.
            if isinstance(raw, bytes) and len(raw) >= 13 and raw[0] == 1:
                sub_id = struct.unpack_from("<I", raw, 1)[0]
                if sub_id in ids:
                    received.add(ids[sub_id])
        if received != LIVE_TOPICS:
            raise RuntimeError(f"no live messages on: {sorted(LIVE_TOPICS - received)}")
        print(f"PASS: {len(expected)} layout topics available; live messages on {', '.join(sorted(received))}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="ws://127.0.0.1:8765")
    ap.add_argument("--layout", type=Path, default=LAYOUT)
    ap.add_argument("--timeout", type=float, default=20)
    args = ap.parse_args()
    try:
        asyncio.run(check(args.url, args.timeout, args.layout))
    except (OSError, TimeoutError, RuntimeError, websockets.WebSocketException) as exc:
        raise SystemExit(f"FAIL: {exc}") from exc


if __name__ == "__main__":
    main()
