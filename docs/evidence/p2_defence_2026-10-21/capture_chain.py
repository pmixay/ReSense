"""Actual ROS/DDS/RViz screen capture, run inside Dockerfile.capture.

No fabricated status or cloud: both RViz and the console consume the running node.
Use an isolated ROS_DOMAIN_ID. Writes the complete status stream and input hashes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def listen(output):
    import rclpy
    from std_msgs.msg import String
    from sensor_msgs.msg import PointCloud2
    rclpy.init()
    node = rclpy.create_node("p2_demo_receipt")
    with open(output, "w", buffering=1) as file:
        last_paint = 0
        def status(msg):
            nonlocal last_paint
            row = json.loads(msg.data)
            file.write(json.dumps({"received_wall": time.time(), "status": row}) + "\n")
            if time.monotonic() - last_paint > .2:
                last_paint = time.monotonic()
                header = Path(output).with_name("screen-header.txt")
                text = header.read_text() if header.exists() else "ReSense live status\n"
                print("\033[2J\033[H" + text + f"\n  {row.get('decision', '?')}\n\n  Distance: {row.get('nearest_distance')} m\n\n  Fresh: {row.get('freshness', {}).get('valid')}\n\n  Frames: {row.get('node', {}).get('frames')}\n", flush=True)

        def cloud(data):
            file.write(json.dumps({"received_wall": time.time(), "input_cdr_sha256": hashlib.sha256(data).hexdigest()}) + "\n")
        node.create_subscription(String, "/resense/status", status, 50)
        for topic in ("/iv_points", "/sensing/lidar/hesai128/pointcloud"):
            node.create_subscription(PointCloud2, topic, cloud, 10, raw=True)
        try:
            rclpy.spin(node)
        except (KeyboardInterrupt, Exception) as exc:
            print(type(exc).__name__, str(exc), flush=True)
        finally:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen")
    parser.add_argument("--bag")
    parser.add_argument("--profile", default="pandar128")
    parser.add_argument("--rate", type=float, default=1)
    parser.add_argument("--out", default="/out")
    args = parser.parse_args()
    if args.listen:
        return listen(args.listen)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DISPLAY=":97", LIBGL_ALWAYS_SOFTWARE="1", QT_X11_NO_MITSHM="1")
    processes = []
    files = []

    def start(cmd, name):
        log = open(out / f"{name}.log", "w")
        files.append(log)
        proc = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(proc)
        return proc

    def wait_for(predicate, timeout, description):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.2)
        raise RuntimeError(f"Timed out: {description}")

    recorder = None
    try:
        start(["Xvfb", ":97", "-screen", "0", "1920x1080x24", "-nolisten", "tcp"], "xvfb")
        wait_for(lambda: Path("/tmp/.X11-unix/X97").exists(), 10, "X11")
        start(["openbox"], "window-manager")
        node = start(["ros2", "launch", "resense_ros", "detector.launch.py", "freshness_mode:=replay",
                      f"sensor_profile:={args.profile}", "clear_range_policy:=conservative"], "node")
        wait_for(lambda: "ReSense detector listening on" in (out / "node.log").read_text(), 60, "node ready")
        start([sys.executable, __file__, "--listen", str(out / "status.jsonl")], "status-console")
        share = "/opt/resense/ros2_ws/install/resense_ros/share/resense_ros/rviz/resense.rviz"
        # Display-only copy: camera, panels and raw topic; geometry/decisions come from the node.
        import yaml
        config = yaml.safe_load(Path(share).read_text())
        raw_displays = [d for d in config["Visualization Manager"]["Displays"] if d.get("Name", "").startswith("LiDAR")]
        for display in raw_displays:
            display["Enabled"] = False
        raw_displays[0]["Enabled"] = True
        raw_displays[0]["Topic"]["Value"] = "/iv_points" if args.profile == "falcon_ros" else "/sensing/lidar/hesai128/pointcloud"
        config["Window Geometry"]["Hide Left Dock"] = True
        config["Window Geometry"]["Hide Right Dock"] = True
        if args.profile == "falcon_ros":
            view = config["Visualization Manager"]["Views"]["Current"]
            view["Yaw"] = 3.14159
            view["Focal Point"] = {"X": 45.0, "Y": 0.0, "Z": -1.0}
        config["Window Geometry"]["Width"] = 1400
        config["Window Geometry"]["Height"] = 1030
        config["Window Geometry"]["X"] = 0
        config["Window Geometry"]["Y"] = 0
        rviz_config = out / "capture.rviz"
        rviz_config.write_text(yaml.safe_dump(config, sort_keys=False))
        start(["rviz2", "-d", str(rviz_config)], "rviz")
        header = out / "screen-header.txt"
        header.write_text(f"ReSense 1.2.0 — source 31154690\nLOCAL ROS / RViz CAPTURE\nprofile: {args.profile}  rate: {args.rate}x\nDevelopment data, not held-out\n\nros2 launch resense_ros\n  detector.launch.py\n  freshness_mode:=replay\n  clear_range_policy:=conservative\n\nros2 bag play /bag\n  --rate {args.rate}\n  --read-ahead-queue-size 10\n\nLive /resense/status:\n")
        start(["xterm", "-title", "ReSense actual ROS status", "-geometry", "46x45+1400+0", "-fa", "DejaVu Sans Mono", "-fs", "13",
               "-bg", "#10151e", "-fg", "#edf1f6", "-e", "tail", "-n", "40", "-f", str(out / "status-console.log")], "terminal")
        wait_for(lambda: (out / "status.jsonl").exists() and (out / "status.jsonl").stat().st_size > 0, 20, "listener status")
        time.sleep(4)  # allow the window manager and RViz to paint before recording
        recorder = start(["ffmpeg", "-y", "-f", "x11grab", "-video_size", "1920x1080", "-framerate", "15", "-i", ":97",
                          "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25", "-pix_fmt", "yuv420p", str(out / "capture.mp4")], "ffmpeg")
        time.sleep(2)
        started = time.time()
        with open(out / "player.log", "w") as log:
            subprocess.run(["ros2", "bag", "play", args.bag, "--rate", str(args.rate), "--delay", "3",
                            "--read-ahead-queue-size", "10", "--disable-keyboard-controls"], env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
        ended = time.time()
        time.sleep(2)
        recorder.stdin.write(b"q\n")
        recorder.stdin.flush()
        assert recorder.wait(timeout=30) == 0
        recorder = None
        (out / "execution.json").write_text(json.dumps({"source": "31154690", "profile": args.profile,
            "rate": args.rate, "player_started_wall": started, "player_ended_wall": ended,
            "node_returncode_during_playback": node.poll(), "ros_domain_id": env.get("ROS_DOMAIN_ID"),
            "screen": [1920, 1080], "fps": 15, "software_gl": True}, indent=2) + "\n")
    finally:
        for proc in reversed(processes):
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGINT)
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
        for file in files:
            file.close()


if __name__ == "__main__":
    main()
