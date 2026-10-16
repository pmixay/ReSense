"""Small recovery-contract tests; all synthetic scratch files are retained outside the worktree."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import preserve_raw as owner


class RecoveryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = Path(os.environ["WEB_RETIRE_TEST_PARENT"])
        owner.require(parent.is_dir(), "Test scratch parent must exist")
        cls.scratch = Path(tempfile.mkdtemp(prefix="web-retirement-contracts-", dir=parent))

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="case-", dir=self.scratch))
        self.zip = self.root / "synthetic.zip"
        self.payload = {f"{owner.PREFIX}raw-{i}.log": b"CRLF\r\nNUL\0exact\xff\n" + bytes([i]) for i in range(owner.COUNT)}
        with zipfile.ZipFile(self.zip, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            for path, data in self.payload.items():
                zipped.writestr(path, data)
        self.manifest = {
            "schema": 1, "source_worktree": "C:/original/web", "archive": owner.identity(self.zip.read_bytes()),
            "files": [{"path": path, "original_absolute_path": "C:/original/web/" + path,
                       **owner.identity(data), "mtime_ns": 1792132400000000000} for path, data in self.payload.items()],
            "branch_archive": {"worktree_entry": {"status": [
                {"path": path, "status": "!!", "kind": "file", "bytes": len(data), "mtime_ns": 1792132400000000000}
                for path, data in self.payload.items()
            ]}},
        }

    def test_verbatim_restore_without_original_source(self):
        destination = self.root / "restored"
        result = owner.restore(self.manifest, self.zip, destination)
        self.assertEqual(result["verified_files"], owner.COUNT)
        self.assertFalse(result["reads_original_worktree"])
        for path, data in self.payload.items():
            self.assertEqual((destination / path).read_bytes(), data)

    def test_corrupt_archive_rejected_before_destination_creation(self):
        self.zip.write_bytes(self.zip.read_bytes()[:-8])
        destination = self.root / "must-not-exist"
        with self.assertRaisesRegex(ValueError, "ZIP identity"):
            owner.restore(self.manifest, self.zip, destination)
        self.assertFalse(destination.exists())

    def test_missing_manifest_entry_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["files"].pop()
        with self.assertRaisesRegex(ValueError, "19 unique"):
            owner.validate(bad, self.zip)

    def test_wrong_per_file_hash_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Raw file identity"):
            owner.validate(bad, self.zip)

    def test_existing_destination_untouched(self):
        destination = self.root / "existing"
        destination.mkdir()
        sentinel = destination / "sentinel"
        sentinel.write_bytes(b"retain this")
        with self.assertRaisesRegex(ValueError, "destination must be new"):
            owner.restore(self.manifest, self.zip, destination)
        self.assertEqual(sentinel.read_bytes(), b"retain this")

    def test_unsafe_member_rejected(self):
        bad = copy.deepcopy(self.manifest)
        path = owner.PREFIX + "../outside.log"
        bad["files"][0]["path"] = path
        bad["branch_archive"]["worktree_entry"]["status"][0]["path"] = path
        with self.assertRaisesRegex(ValueError, "Invalid payload path"):
            owner.validate(bad, self.zip)


if __name__ == "__main__":
    unittest.main()
