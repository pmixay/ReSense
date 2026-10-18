#!/usr/bin/env python3
"""Actual ROS/DDS + PTY integration: SPACE, rate key, and two profiles in one node.

Run inside the image with host-generated make_profile_smoke_bags.py output mounted.
No mock ROS modules. Writes raw status, terminal output and a fail-closed report.
"""

import argparse
import json
import os
from pathlib import Path
import pty
import subprocess
import time

import rclpy
import yaml
from rclpy.parameter import Parameter
from rcl_interfaces.srv import SetParametersAtomically
from rosbag2_interfaces.srv import GetRate, IsPaused
from std_msgs.msg import String
from std_srvs.srv import Trigger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bags", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--falcon-bag", type=Path,
                        help="Use an actual Falcon ROS bag for the second input; no synthetic obstacle truth asserted")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows, controls, players = [], {}, []
    rclpy.init()
    observer = rclpy.create_node("interactive_replay_observer")
    stream = (args.out / "status.jsonl").open("w")

    def status(msg):
        row = json.loads(msg.data)
        row["_received_mono"] = time.monotonic()
        rows.append(row)
        stream.write(json.dumps(row) + "\n")
        stream.flush()

    observer.create_subscription(String, "/resense/status", status, 1000)
    node_log = (args.out / "node.log").open("w")
    detector = subprocess.Popen(
        [
            "ros2",
            "run",
            "resense_ros",
            "detector_node",
            "--ros-args",
            "-p",
            "freshness_mode:=replay",
            "-p",
            "warmup:=false",
            "-p",
            "clear_range_policy:=conservative",
        ],
        stdout=node_log,
        stderr=subprocess.STDOUT,
    )
    active = None

    def spin_until(predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while not predicate():
            if detector.poll() is not None:
                raise RuntimeError("detector exited; see node.log")
            if time.monotonic() >= deadline:
                raise TimeoutError("integration condition timed out")
            rclpy.spin_once(observer, timeout_sec=0.03)
            if active is not None:
                try:
                    data = os.read(active["master"], 65536)
                    if data:
                        active["log"].write(data)
                        active["log"].flush()
                except (BlockingIOError, OSError):
                    pass

    def call(client, request):
        if not client.wait_for_service(timeout_sec=10):
            raise RuntimeError("service unavailable")
        future = client.call_async(request)
        spin_until(future.done)
        if future.exception():
            raise future.exception()
        return future.result()

    report = {
        "passed": False,
        "scope": "real ROS2 DDS node and PTY rosbag2 player, no mocks",
    }
    try:
        spin_until(lambda: bool(rows), 40)
        param = observer.create_client(
            SetParametersAtomically, "/resense_detector/set_parameters_atomically"
        )
        if not param.wait_for_service(timeout_sec=10):
            raise RuntimeError("parameter service unavailable")
        reset = observer.create_client(Trigger, "/resense/reset_input")
        for profile in ("pandar128", "falcon_ros"):
            bag = args.falcon_bag if profile == "falcon_ros" and args.falcon_bag else args.bags / profile
            metadata = yaml.safe_load((bag / "metadata.yaml").read_text())["rosbag2_bagfile_information"]
            expected_frames = sum(item["message_count"] for item in metadata["topics_with_message_count"]
                                  if item["topic_metadata"]["type"] == "sensor_msgs/msg/PointCloud2")
            assert expected_frames >= 25, "integration requires at least25 real PointCloud2 frames"
            future = param.call_async(
                SetParametersAtomically.Request(
                    parameters=[
                        Parameter("sensor_profile", value=profile).to_parameter_msg()
                    ]
                )
            )
            spin_until(future.done)
            assert future.result().result.successful, future.result().result.reason
            assert call(reset, Trigger.Request()).success
            before = len(rows)
            master, slave = pty.openpty()
            os.set_blocking(master, False)
            log = (args.out / (profile + "_player.log")).open("wb")
            player = subprocess.Popen(
                [
                    "ros2",
                    "bag",
                    "play",
                    str(bag),
                    "--rate",
                    ".5",
                    "--delay",
                    "2",
                    "--read-ahead-queue-size",
                    "10",
                ],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                start_new_session=True,
            )
            os.close(slave)
            active = {"master": master, "log": log}
            players.append(player)

            def frames():
                return [r for r in rows[before:] if r.get("snapshot_kind") == "frame"]

            spin_until(lambda: len(frames()) >= 5, 30)
            if profile == "pandar128":
                paused = observer.create_client(IsPaused, "/rosbag2_player/is_paused")
                rate = observer.create_client(GetRate, "/rosbag2_player/get_rate")
                controls["initial_rate"] = call(rate, GetRate.Request()).rate
                os.write(master, b" ")
                spin_until(lambda: call(paused, IsPaused.Request()).paused)
                controls["space_pauses"] = True
                start = time.monotonic()
                spin_until(lambda: time.monotonic() - start >= 1.2)
                controls["pause_invalidates_monitoring"] = not rows[-1]["freshness"][
                    "valid"
                ]
                count = len(frames())
                start = time.monotonic()
                spin_until(lambda: time.monotonic() - start >= 0.5)
                controls["no_frames_while_paused"] = len(frames()) == count
                os.write(master, b"\x1b[B")
                spin_until(lambda: call(rate, GetRate.Request()).rate < 0.5)
                controls["keyboard_reduced_rate"] = call(rate, GetRate.Request()).rate
                os.write(master, b" ")
                spin_until(lambda: not call(paused, IsPaused.Request()).paused)
                controls["space_resumes"] = True
                observer.destroy_client(paused)
                observer.destroy_client(rate)
            spin_until(lambda: player.poll() is not None, 40)
            assert player.returncode == 0
            start = time.monotonic()
            spin_until(lambda: time.monotonic() - start >= 1.2)
            obtained = frames()
            assert len(obtained) == expected_frames, (profile, len(obtained), expected_frames)
            if profile != "falcon_ros" or args.falcon_bag is None:
                assert any(r["decision"] == "GO" for r in obtained)
                assert any(
                    r["decision"] == "STOP" and abs(r["nearest_distance"] - 40) < 2
                    for r in obtained
                )
            assert all(r["sensor_profile"] == profile for r in obtained)
            assert all(r["range_policy"] == "c2_conservative_2026_10_17" for r in obtained)
            assert all(r["gauge"]["solid_range_m"] <= r["gauge"]["axis_valid_m"] for r in obtained)
            if profile == "pandar128":
                assert all(r["clear_distance"] <= 88.7 for r in obtained)
            else:
                assert all(r["clear_distance"] == 0 and r["monitored_small"] is None for r in obtained)
            controls[profile] = {
                "frames": len(obtained),
                "expected_frames": expected_frames,
                "input": str(bag),
                "synthetic_obstacle_truth_asserted": profile != "falcon_ros" or args.falcon_bag is None,
                "recordings": sorted({r["node"]["recording"] for r in obtained}),
                "first_decision": obtained[0]["decision"],
                "first_freshness": obtained[0]["freshness"]["reason"],
                "go": sum(r["decision"] == "GO" for r in obtained),
                "stop": sum(r["decision"] == "STOP" for r in obtained),
                "generations": sorted(
                    {r["node"]["input_generation"] for r in obtained}
                ),
            }
            assert obtained[0]["freshness"]["reason"] == "epoch_unconfirmed"
            assert not obtained[0]["stop_held"]
            os.close(master)
            log.close()
            active = None
        assert (
            controls["initial_rate"] == 0.5 and controls["keyboard_reduced_rate"] < 0.5
        )
        assert (
            controls["pause_invalidates_monitoring"]
            and controls["no_frames_while_paused"]
        )
        assert controls["pandar128"]["recordings"] == [1] and controls["falcon_ros"][
            "recordings"
        ] == [2]
        report.update(
            passed=True,
            detector_pid=detector.pid,
            detector_restarts=0,
            controls=controls,
        )
    except Exception as error:
        report.update(error=repr(error), controls=controls)
        raise
    finally:
        for player in players:
            if player.poll() is None:
                player.terminate()
        if detector.poll() is None:
            detector.terminate()
        try:
            detector.wait(timeout=10)
        except subprocess.TimeoutExpired:
            detector.kill()
        if active is not None:
            os.close(active["master"])
            active["log"].close()
        (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        stream.close()
        node_log.close()
        observer.destroy_node()
        rclpy.shutdown()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
