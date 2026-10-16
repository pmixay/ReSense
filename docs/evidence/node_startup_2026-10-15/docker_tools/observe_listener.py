#!/usr/bin/env python3
"""Wrap the unchanged judge listener with graph readiness and a flushed drain witness.

The witness is control-plane evidence only. S1 metrics always use listener.py's JSONL.
"""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    a = ap.parse_args()
    child = subprocess.Popen([sys.executable, "/tools/listener.py", "--out", a.base + ".jsonl",
                              "--seconds", "900"])
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    rclpy.init()
    node = Node("s1_drain_witness")
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    witness = open(a.base + ".observer.jsonl", "x", buffering=1)
    received_status = False

    def status(msg):
        nonlocal received_status
        s = json.loads(msg.data)
        witness.write(json.dumps({"t": time.time(), "snapshot": s.get("snapshot_kind"),
                                  "frames": (s.get("node") or {}).get("frames")}) + "\n")
        received_status = True

    node.create_subscription(String, "/resense/status", status, 50)
    ready = False
    deadline = time.monotonic() + 60
    try:
        while not stopping and child.poll() is None:
            rclpy.spin_once(node, timeout_sec=0.1)
            if not ready:
                topics = ("/resense/status", "/resense/decision", "/resense/latency_ms")
                ready = received_status and all(
                    any(s.node_name == "jury_listener" for s in node.get_subscriptions_info_by_topic(t))
                    and node.count_publishers(t) > 0 for t in topics)
                if ready:
                    Path(a.base + ".ready").write_text(str(time.time()))
                    print("S1_LISTENER_READY", flush=True)
                elif time.monotonic() > deadline:
                    raise RuntimeError("Judge listener / publishers / actual status data not ready")
        if not stopping:
            raise RuntimeError(f"Judge listener exited early: {child.returncode}")
    finally:
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=3)
        witness.close()
        node.destroy_node()
        rclpy.shutdown()
    if child.returncode != 0:
        raise RuntimeError(f"Judge listener did not flush cleanly: {child.returncode}")


if __name__ == "__main__":
    main()
