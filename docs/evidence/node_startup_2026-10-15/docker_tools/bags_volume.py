#!/usr/bin/env python3
"""Stage exactly the original bags in a new Docker volume; verify read-only before use.

Host and container code use only the Python standard library. The data volume contains
only the two bag directories, databases and unmodified metadata, never helper markers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import struct
import sys
import time
import uuid


def file_sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def identity(bags):
    """Canonical full-file identity, independent of host paths and storage location."""
    return {bag: {"expected_frames": v["expected_frames"], "topic": v["topic"],
                  "metadata_sha256": v["metadata_sha256"],
                  "files": sorted(v["files"], key=lambda f: f["name"])} for bag, v in sorted(bags.items())}


def inventory_digest(bags):
    return hashlib.sha256(json.dumps(identity(bags), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_plan(expected):
    plan = []
    for bag, info in expected.items():
        if Path(bag).name != bag or bag in (".", "..") or not bag:
            raise ValueError("Invalid bag path component")
        plan.append((bag, "metadata.yaml", info["metadata_sha256"], None))
        for db in info["files"]:
            name = db["name"]
            if Path(name).name != name or not name.endswith(".db3") or "/" in name or "\\" in name:
                raise ValueError("Invalid database path component")
            plan.append((bag, name, db["sha256"], db["bytes"]))
    return plan


def copy_bags(source, destination, expected):
    if any(destination.iterdir()):
        raise ValueError("Refusing a nonempty volume, including partially copied data")
    for bag, name, digest, size in file_plan(expected):
        original = source / bag / name
        if original.is_symlink() or not original.is_file():
            raise ValueError(f"Missing/non-regular original file: {original}")
        target = destination / bag / name
        target.parent.mkdir(exist_ok=True)
        # Exclusive create: no source metadata or previous destination can be overwritten.
        with original.open("rb") as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        target.chmod(0o444)
        if (size is not None and target.stat().st_size != size) or file_sha256(target) != digest:
            raise ValueError(f"Copy digest/size mismatch: {bag}/{name}")
    return {"copied": True, "inventory_digest": inventory_digest(expected),
            "files": [f"{bag}/{name}" for bag, name, _, _ in file_plan(expected)]}


def verify_bags(folder, expected):
    plan = file_plan(expected)
    wanted = {f"{bag}/{name}" for bag, name, _, _ in plan}
    found = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    entries = list(folder.rglob("*"))
    directories = {p.relative_to(folder).as_posix() for p in entries if p.is_dir()}
    if found != wanted or directories != set(expected) or any(p.is_symlink() for p in entries):
        raise ValueError(f"Volume file/directory inventory differs: {sorted(found ^ wanted)}")
    actual = {}
    for bag, info in expected.items():
        dbs, stamps, topics = [], [], set()
        for db in info["files"]:
            path = folder / bag / db["name"]
            actual_db = {"name": path.name, "bytes": path.stat().st_size, "sha256": file_sha256(path)}
            if actual_db != db:
                raise ValueError(f"Full database SHA256/size mismatch: {bag}/{path.name}")
            dbs.append(actual_db)
            with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as con:
                rows = con.execute("SELECT id, name FROM topics WHERE type = ?",
                                   ("sensor_msgs/msg/PointCloud2",)).fetchall()
                if len(rows) != 1:
                    raise ValueError("Expected one original PointCloud2 topic")
                tid, topic = rows[0]
                topics.add(topic)
                for (prefix,) in con.execute("SELECT substr(data, 1, 12) FROM messages WHERE topic_id = ? "
                                              "ORDER BY timestamp, id", (tid,)):
                    if len(prefix) != 12 or prefix[:2] not in (b"\x00\x01", b"\x00\x00"):
                        raise ValueError("Invalid original CDR header")
                    sec, ns = struct.unpack(("<" if prefix[1] else ">") + "iI", prefix[4:12])
                    stamps.append(sec + ns * 1e-9)
        if topics != {info["topic"]} or stamps != info["stamps"] or len(stamps) != info["expected_frames"]:
            raise ValueError(f"Volume cloud inventory differs: {bag}")
        actual[bag] = {"expected_frames": len(stamps), "topic": topics.pop(), "files": dbs,
                       "metadata_sha256": file_sha256(folder / bag / "metadata.yaml")}
    if identity(actual) != identity(expected):
        raise ValueError("Full database/metadata SHA256 or size mismatch")
    return {"verified": True, "inventory_digest": inventory_digest(actual), "bags": identity(actual)}


def container_job(docker, image, root, volume, mode, run_id, source=None, *, host_api):
    """Bounded, networkless copy/verification; verification mount is always read-only."""
    s1 = host_api

    name = "rs-s1-volume-" + mode + "-" + uuid.uuid4().hex[:12]
    args = ["run", "-d", "--name", name, "--network", "none", "--cpus", "4", "--memory", "512m",
            "--label", f"resense.startup.run={run_id}", "--entrypoint", "python3", "--mount",
            f"type=bind,src={root},dst=/job,readonly", "--mount",
            f"type=volume,src={volume},dst=/data,volume-nocopy" + (",readonly" if mode == "verify" else "")]
    if source is not None:
        args += ["--mount", f"type=bind,src={source},dst=/source,readonly"]
    args += [image, "/job/bags_volume.py", mode, "--expected", "/job/volume_expected.json", "--data", "/data"]
    if source is not None:
        args += ["--source", "/source"]
    receipt = {"name": name, "mode": mode, "volume": volume, "read_only": mode == "verify"}
    try:
        docker.call(*args, timeout=45)
        s1.wait_until(lambda: not docker.state(name)["State"]["Running"], 1800, f"Volume {mode} timeout")
        inspected = docker.state(name)
        receipt.update(container_id=inspected["Id"], image_id=inspected["Image"], state=inspected["State"],
                       mounts=inspected.get("Mounts", []))
        logs = docker.call("logs", name)
        with (root / (mode + ".log")).open("x", encoding="utf-8") as f:
            f.write(logs.stdout + logs.stderr)
        if inspected["State"]["ExitCode"] != 0 or inspected["State"].get("OOMKilled"):
            raise RuntimeError(f"Volume {mode} failed: {logs.stdout}{logs.stderr}")
        receipt["result"] = s1.strict_json(logs.stdout)
        return receipt
    finally:
        cleanup = docker.call("rm", "--force", name, check=False)
        receipt["cleanup_ok"] = cleanup.returncode == 0
        s1.write_json(root / (mode + ".receipt.json"), receipt)


def stage(args):
    repo = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo))
    from scripts import startup_acceptance as s1

    root = args.out.resolve()
    if root.exists() or not root.parent.is_dir():
        raise ValueError("Stage evidence directory must be new under an existing parent")
    expected = {bag: s1.bag_inventory(Path(args.bags) / bag, count)
                for bag, count in {v[0]: v[1] for v in s1.CONDITIONS.values()}.items()}
    reference = None
    if args.reference_manifest:
        reference = s1.read_json(args.reference_manifest)
        if identity(expected) != identity(reference["bags"]):
            raise ValueError("Host original bag hashes differ from the published Windows manifest")
    # Refuse existing volumes: re-use is only through a fresh read-only driver verification.
    if s1.command(["docker", "volume", "inspect", args.volume], check=False).returncode == 0:
        raise ValueError("Stage requires a NEW uniquely named Docker volume")
    root.mkdir()
    s1.write_json(root / "volume_expected.json", expected)
    shutil.copyfile(__file__, root / "bags_volume.py")
    docker = s1.Docker(root)
    image = s1.strict_json(docker.call("image", "inspect", args.image).stdout)[0]["Id"]
    run_id = "stage-" + uuid.uuid4().hex
    digest = inventory_digest(expected)
    docker.call("volume", "create", "--label", f"resense.startup.volume_owner={run_id}",
                "--label", f"resense.startup.expected_inventory={digest}", args.volume)
    result = {"run_id": run_id, "volume_name": args.volume, "image_id": image, "source": str(Path(args.bags).resolve()),
              "inventory_digest": digest, "t_start": time.time(), "verified": False}
    if reference is not None:
        result["reference_manifest"] = {"path": str(args.reference_manifest.resolve()),
                                        "sha256": file_sha256(args.reference_manifest), "matched": True}
    try:
        result["copy"] = container_job(docker, image, root, args.volume, "copy", run_id, Path(args.bags).resolve(), host_api=s1)
        result["verification"] = container_job(docker, image, root, args.volume, "verify", run_id, host_api=s1)
        result["verified"] = result["verification"]["result"]["verified"]
    finally:
        result["t_end"] = time.time()
        result["volume_inspect"] = s1.strict_json(docker.call("volume", "inspect", args.volume).stdout)[0]
        s1.write_json(root / "stage.json", result)
    print(json.dumps(result, indent=2, allow_nan=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("stage", "copy", "verify"))
    ap.add_argument("--image")
    ap.add_argument("--volume")
    ap.add_argument("--bags")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--reference-manifest", type=Path, help="Require host bag hashes to match an earlier published manifest")
    ap.add_argument("--expected", type=Path)
    ap.add_argument("--data", type=Path)
    ap.add_argument("--source", type=Path)
    a = ap.parse_args()
    if a.mode == "stage":
        if not all((a.image, a.volume, a.bags, a.out)):
            ap.error("stage requires --image --volume --bags --out")
        stage(a)
    else:
        expected = json.loads(a.expected.read_text(encoding="utf-8"))
        result = copy_bags(a.source, a.data, expected) if a.mode == "copy" else verify_bags(a.data.resolve(), expected)
        print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
