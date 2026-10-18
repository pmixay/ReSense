"""The jury wrapper keeps one node, uses explicit boundaries and preserves shell arguments."""

import ast
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/play_bag.sh"


def test_wrapper_rejects_invalid_rate_and_interactive_without_tty(tmp_path):
    bag = tmp_path / "bag"
    bag.mkdir()
    (bag / "metadata.yaml").touch()
    for args in (
        ["--rate", "0"],
        ["--rate", "x"],
        ["--interactive"],
        ["--sensor-profile", "guess"],
    ):
        result = subprocess.run(
            ["bash", str(SCRIPT), *args, str(bag)], capture_output=True, text=True
        )
        assert result.returncode == 2


def test_two_bag_paths_with_spaces_one_node_and_two_confirmed_resets(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    log = tmp_path / "calls.jsonl"
    docker = binary / "docker"
    docker.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['DOCKER_LOG'], 'a') as f: f.write(json.dumps(args)+'\\n')
if args and args[0]=='logs':
    print('ReSense detector listening on /lidar_points' if 'listen' not in args[-1] else 'STOP 40 m')
elif args and args[0]=='exec': print('recording boundary confirmed')
""")
    docker.chmod(0o755)
    sleep = binary / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    paths = []
    for name in ("Pandar bag", "Falcon bag"):
        path = tmp_path / name
        path.mkdir()
        (path / "metadata.yaml").touch()
        paths.append(path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--rate", ".5", str(paths[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2  # require an unambiguous decimal literal, e.g. 0.5
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--rate",
            "0.5",
            "--sensor-profile",
            "pandar128",
            str(paths[0]),
            "--sensor-profile",
            "falcon_ros",
            str(paths[1]),
        ],
        env={
            **os.environ,
            "PATH": str(binary) + os.pathsep + os.environ["PATH"],
            "DOCKER_LOG": str(log),
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    node_runs = [args for args in calls if args[:2] == ["run", "-d"] and "ros2" in args]
    players = [args for args in calls if "play" in args]
    boundaries = [args for args in calls if args and args[0] == "exec"]
    assert len(node_runs) == 1 and len(players) == len(boundaries) == 2
    assert [args[-1] for args in boundaries] == ["pandar128", "falcon_ros"]
    assert all(
        "--disable-keyboard-controls" in args
        and args[args.index("--rate") + 1] == "0.5"
        for args in players
    )
    assert [args[args.index("-v") + 1] for args in players] == [
        str(p) + ":/data/bag:ro" for p in paths
    ]
    listener = next(args[-1] for args in calls if "-c" in args)
    ast.parse(
        listener
    )  # protect the inline listener from shell/Python quoting mistakes
