"""The optional live-viewer freshness check cannot pass on stale topic traffic alone."""
import asyncio
import copy
import json
import struct
import sys
import types

import pytest

import check_foxglove_live as probe


def status():
    return {
        "snapshot_kind": "frame", "decision": "GO", "obstacle": False,
        "stop_held": False, "node": {"catchup": False},
        "freshness": {
            "valid": True, "reason": "current", "mode": "replay",
            "clock_reference": "publisher_utc", "evaluated_at_utc_s": 1000.0,
            "max_result_age_s": 0.5, "future_tolerance_s": 0.05,
            "source_age_s": 0.1, "residence_age_s": 0.02, "queue_lag_s": 0.0,
        },
    }


def cdr(value, endian="<"):
    data = json.dumps(value).encode() + b"\0"
    header = b"\x00\x01\x00\x00" if endian == "<" else b"\x00\x00\x00\x00"
    return header + struct.pack(endian + "I", len(data)) + data


@pytest.mark.parametrize("endian", ["<", ">"])
@pytest.mark.parametrize("decision", ["GO", "CAUTION", "STOP"])
def test_current_status_accepts_current_frames(endian, decision):
    frame = status()
    frame["decision"] = decision
    frame["obstacle"] = decision == "STOP"
    assert probe.current_status(cdr(frame, endian), 1000.2)


@pytest.mark.parametrize("change", [
    {"snapshot_kind": "watchdog"},
    {"decision": "FAULT"},
    {"decision": "STOP", "stop_held": True},
    {"node": {"catchup": True}},
    {"freshness": {"valid": False, "reason": "source_stale"}},
    {"freshness": {"reason": "epoch_unconfirmed"}},
    {"freshness": {"source_age_s": 0.6}},
    {"freshness": {"residence_age_s": 0.6}},
    {"freshness": {"queue_lag_s": 0.1}},
    {"freshness": {"source_age_s": -0.1}},
    {"freshness": {"evaluated_at_utc_s": 1000.1}},
    {"freshness": {"evaluated_at_utc_s": 999.4}},
    {"freshness": {"source_age_s": float("nan")}},
    {"freshness": {"max_result_age_s": 20.0}},
    {"freshness": {"clock_reference": "unknown"}},
])
def test_current_status_rejects_invalid_or_expired_frames(change):
    frame = status()
    for key, value in change.items():
        if key == "freshness":
            frame[key].update(value)
        else:
            frame[key] = value
    assert not probe.current_status(cdr(frame), 1000.0)


def test_current_status_counts_transport_against_remaining_lifetime():
    frame = status()
    frame["freshness"]["source_age_s"] = 0.4
    assert probe.current_status(cdr(frame), 1000.05)
    assert not probe.current_status(cdr(frame), 1000.2)


@pytest.mark.parametrize("payload", [b"", b"\0" * 9, b"\x00\x03" + b"\0" * 12,
                                     cdr({})[:-1], cdr([1]), cdr({"freshness": None})])
def test_malformed_or_unknown_status_cannot_satisfy_probe(payload):
    assert not probe.current_status(payload, 1000.0)


class FakeSocket:
    def __init__(self, frames):
        self.frames = frames
        topics = sorted(probe.layout_topics(probe.LAYOUT) | probe.LIVE_TOPICS)
        self.topics = {i: topic for i, topic in enumerate(topics, 1)}
        channels = [{"id": i, "topic": topic, "encoding": "cdr", "schemaName": "std_msgs/msg/String"}
                    for i, topic in self.topics.items()]
        self.messages = [json.dumps({"op": "advertise", "channels": channels})]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def send(self, message):
        for sub in json.loads(message)["subscriptions"]:
            topic = self.topics[sub["channelId"]]
            prefix = struct.pack("<BIQ", 1, sub["id"], 0)
            if topic == "/resense/status":
                self.messages.extend(prefix + cdr(frame) for frame in self.frames)
            else:
                self.messages.append(prefix + b"opaque topic data")

    async def recv(self):
        if self.messages:
            return self.messages.pop(0)
        raise asyncio.TimeoutError


@pytest.mark.parametrize("require_freshness, recover, expected_pass", [
    (False, False, True), (True, False, False), (True, True, True),
])
def test_probe_requires_current_status_after_startup_when_enabled(
        monkeypatch, require_freshness, recover, expected_pass):
    invalid = status()
    invalid["freshness"].update(valid=False, reason="epoch_unconfirmed")
    frames = [invalid]
    if recover:
        frames.append(copy.deepcopy(status()))
    socket = FakeSocket(frames)
    monkeypatch.setitem(sys.modules, "websockets", types.SimpleNamespace(connect=lambda *a, **k: socket))
    monkeypatch.setattr(probe.time, "time", lambda: 1000.0)
    run = probe.check("ws://fixture:8765", 1.0, probe.LAYOUT, require_freshness)
    if expected_pass:
        asyncio.run(run)
    else:
        with pytest.raises(RuntimeError, match="no current fresh frame"):
            asyncio.run(run)
