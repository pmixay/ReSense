"""The freeze fails closed on source drift and on incomplete or altered validation evidence."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "detector_freeze", Path(__file__).resolve().parents[1] / "scripts/detector_freeze.py")
assert SPEC and SPEC.loader
freeze = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(freeze)


class TestDetectorFreeze(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        contents = {
            "resense/detector.py": "def detect(): return False\n",
            "native/resense_native.cpp": "// detector kernel\n",
            freeze.CONFIG: "resense: {}\n",
            freeze.ROS_CONFIG: "resense: {}\n",
            **{p: "# build input\n" for p in freeze.BUILD_FILES},
        }
        for rel, data in contents.items():
            self.write(rel, data)
        self.measured_sources = {p: (self.root / p).read_bytes() for p in contents}
        self.baseline_path = self.root / "docs/baseline.json"
        self.evidence_path = self.root / "docs/gate.json"
        self.baseline = {
            "schema": "resense-regression-gate-v1",
            "code": {"commit": "a" * 40, "uncommitted_detector_changes": []},
            "config": {"sha256": "effective", "file_sha256": freeze.sha256(self.root / freeze.CONFIG), "set": []},
            "recordings": {p: {} for p in freeze.RECORDINGS},
            "set_O": {"objects": {"person": {}}},
            "ride": {"available": True}, "set_F_straight": {"available": True},
        }
        self.evidence = copy.deepcopy(self.baseline)
        self.evidence["gate"] = {
            "passed": True, "allow": [], "worse_gated": [], "missing_gated": [],
            "worse_allowed": [], "missing_allowed": [],
            "baseline_config_sha256": "effective", "baseline_commit": "a" * 40,
        }
        self.write("docs/baseline.json", json.dumps(self.baseline))
        self.write("docs/gate.json", json.dumps(self.evidence))
        with patch.object(freeze, "_git", side_effect=self.git):
            self.manifest = freeze.create_manifest(self.root, self.baseline_path, self.evidence_path)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def git(self, root, *args):
        if args[0] == "ls-tree":
            return "\n".join(self.measured_sources).encode()
        if args[0] == "show":
            return self.measured_sources[args[1].partition(":")[2]]
        if args[0] == "rev-parse":
            return b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
        raise AssertionError(args)

    def verify(self):
        return freeze.verify_manifest(self.root, self.manifest)

    def test_intact_archive_verifies_without_git(self):
        with patch.object(freeze, "_git", side_effect=AssertionError("Git should not be needed")):
            self.assertEqual(self.verify(), [])

    def test_changed_detector_is_rejected(self):
        self.write("resense/detector.py", "def detect(): return True\n")
        self.assertIn("changed detector file: resense/detector.py", self.verify())

    def test_missing_detector_is_rejected(self):
        (self.root / "resense/detector.py").unlink()
        self.assertIn("missing detector file: resense/detector.py", self.verify())

    def test_added_untracked_detector_is_rejected(self):
        self.write("resense/late_rule.py", "# a new rule\n")
        self.assertIn("added detector file: resense/late_rule.py", self.verify())

    def test_generated_cache_and_native_binary_are_excluded(self):
        self.write("resense/__pycache__/detector.cpython-310.pyc", "cache")
        self.write("native/resense_native.so", "build output")
        self.assertEqual(self.verify(), [])

    def test_changed_validation_evidence_is_rejected(self):
        self.evidence["recordings"]["doubleT_obstacle"]["alarm_frames"] = 999
        self.write("docs/gate.json", json.dumps(self.evidence))
        self.assertIn("changed validation evidence: docs/gate.json", self.verify())

    def test_incomplete_or_waived_gate_cannot_be_sealed(self):
        for field, value in (("allow", ["ride.*"]), ("missing_gated", ["ride.alarm_events"]),
                             ("passed", False), ("worse_allowed", ["set_O.person.stop_frames"])):
            with self.subTest(field=field):
                evidence = copy.deepcopy(self.evidence)
                evidence["gate"][field] = value
                with self.assertRaises(ValueError):
                    freeze.check_gate(self.baseline, evidence, self.manifest["config_file_sha256"])
        evidence = copy.deepcopy(self.evidence)
        evidence["ride"]["available"] = False
        with self.assertRaisesRegex(ValueError, "missing ride"):
            freeze.check_gate(self.baseline, evidence, self.manifest["config_file_sha256"])

    def test_config_override_and_dirty_detector_cannot_be_sealed(self):
        for key, value in (("config", {**self.evidence["config"], "set": ["tracking.min_hits=1"]}),
                           ("code", {**self.evidence["code"], "uncommitted_detector_changes": ["M resense/detector.py"]})):
            with self.subTest(key=key):
                evidence = {**self.evidence, key: value}
                with self.assertRaises(ValueError):
                    freeze.check_gate(self.baseline, evidence, self.manifest["config_file_sha256"])

    def test_changed_source_since_measurement_cannot_be_sealed(self):
        self.write("resense/detector.py", "# unmeasured change\n")
        with patch.object(freeze, "_git", side_effect=self.git):
            with self.assertRaisesRegex(ValueError, "differs from the measured commit"):
                freeze.create_manifest(self.root, self.baseline_path, self.evidence_path)

    def test_removed_source_since_measurement_cannot_be_sealed(self):
        (self.root / "resense/detector.py").unlink()
        with patch.object(freeze, "_git", side_effect=self.git):
            with self.assertRaisesRegex(ValueError, "inventory differs"):
                freeze.create_manifest(self.root, self.baseline_path, self.evidence_path)

    def test_manifest_inventory_tampering_is_rejected(self):
        self.manifest["files"]["resense/detector.py"] = "0" * 64
        self.assertIn("manifest source digest disagrees with its inventory", self.verify())

    def test_symlink_in_detector_scope_is_rejected(self):
        (self.root / "resense/late_rule.py").symlink_to(self.root / "resense/detector.py")
        self.assertTrue(any("symlink" in e for e in self.verify()))


if __name__ == "__main__":
    unittest.main()
