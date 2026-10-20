#!/usr/bin/env python3
"""Bundle complete author evidence, with a verifiable member inventory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
WORK = Path("/tmp/opencode")
TAGS = ("gate-baseline", "gate-final", "ride-final", "physical-baseline-v2", "physical-final-v2",
        "falcon-baseline", "falcon-final", "tests-final", "full-tests", "x3-final")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = set()
    receipts = {}
    for tag in TAGS:
        receipt = WORK / f"f1a-b1-{tag}-receipt.json"
        data = json.loads(receipt.read_text())
        assert data["source_unchanged"], tag
        receipts[tag] = {"returncode": data["returncode"], "source_unchanged": True,
                         "receipt_sha256": sha(receipt)}
        paths.update([receipt, WORK / f"f1a-b1-{tag}.log"])
    for tag in ("base-plain", "base-traced", "ride-final", "falcon-baseline", "falcon-final"):
        paths.add(WORK / f"f1a-b1-{tag}.jsonl")
    for tag in ("base-plain", "base-traced", "ride-final"):
        paths.add(WORK / f"f1a-b1-{tag}.meta.json")
    paths.add(WORK / "f1a-b1-ride-episodes.json")
    for tag in ("tests", "physical-baseline", "physical-final"):
        paths.update([WORK / f"f1a-b1-{tag}.log", WORK / f"f1a-b1-{tag}-receipt.json"])
    for tag in ("gate-baseline", "gate-final", "physical-baseline-v2", "physical-final-v2", "x3-final"):
        paths.add(WORK / f"f1a-b1-{tag}.json")
    for tag in ("gate-baseline", "gate-final"):
        paths.add(WORK / f"f1a-b1-{tag}-source.tar.gz")
        paths.update(p for p in (WORK / f"f1a-b1-{tag}-work").rglob("*") if p.is_file())
    paths.update(p for p in (WORK / "f1a-b1-x3-final.raw").rglob("*") if p.is_file())
    reference = WORK / "h1-publication/x3.json"
    paths.add(reference)
    for entry in json.loads(reference.read_text())["entries"].values():
        raw = Path(entry["raw_path"])
        paths.update([raw, raw.with_suffix(".complete.json")])
    paths.update(p for p in (WORK / "f1a-b1-compact-snapshots").rglob("*") if p.is_file())
    paths.add(WORK / "f1a-b1-compact-audit.json")
    for frame in (2666, 2668, 2671, 5709, 5712, 5714, 7360, 10484):
        paths.add(WORK / "f1a-b1-snapshots" / f"frame_{frame:05d}.npz")
    tests = {}
    for tag in ("tests-final", "full-tests"):
        path = WORK / f"f1a-b1-{tag}.xml"
        paths.add(path)
        xml = ET.parse(path).getroot()
        tests[tag] = {"suites": [s.attrib for s in xml.iter("testsuite")],
                      "failures": [{"class": case.get("classname"), "test": case.get("name"),
                                    "failure": case.find("failure").text}
                                   for case in xml.iter("testcase") if case.find("failure") is not None]}
    # Include any completed quiet failure rechecks without relabelling the original full run.
    for path in WORK.glob("f1a-b1-recheck-*"):
        if path.is_file():
            paths.add(path)
    members = {str(p.relative_to(WORK)): p for p in paths}
    root = HERE.parents[2]
    for p in [*HERE.glob("*.py"), root / "tests/test_f1a_b1.py", root / "tests/test_f1_false_alarms.py",
              root / "labels/cloud_with_fake_obj.json", root / "labels/doubleT_obstacle.json"]:
        members["verification/" + str(p.relative_to(root))] = p
    inventory = [{"path": name, "bytes": p.stat().st_size, "sha256": sha(p)}
                 for name, p in sorted(members.items())]
    archive_path = HERE / "raw-evidence.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, p in sorted(members.items()):
            archive.add(p, arcname=name)
    # Verify the archive independently of the source-file hashing pass.
    with tarfile.open(archive_path, "r:gz") as archive:
        assert len(archive.getmembers()) == len(inventory)
        for item in inventory:
            assert hashlib.sha256(archive.extractfile(item["path"]).read()).hexdigest() == item["sha256"]
        control = archive.extractfile(inventory[0]["path"]).read()
        assert control
        mutated = bytes([control[0] ^ 1]) + control[1:]
        assert hashlib.sha256(mutated).hexdigest() != inventory[0]["sha256"]
    (HERE / "raw-manifest.json").write_text(json.dumps(inventory, indent=2) + "\n")
    report = {"archive_sha256": sha(archive_path), "archive_bytes": archive_path.stat().st_size,
              "members": len(members), "mutated_member_positive_control": True,
              "receipts": receipts, "tests": tests}
    (HERE / "package.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["archive_bytes"], report["members"], receipts)


if __name__ == "__main__":
    main()
