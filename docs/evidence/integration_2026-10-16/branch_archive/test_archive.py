"""Failure-mode tests for the archive's independently checkable contract."""

import copy
import json
from pathlib import Path
import unittest

from archive import parse_bundle_header, validate_contract


HERE = Path(__file__).resolve().parent


class ArchiveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
        cls.header = parse_bundle_header(HERE / "retired-heads.bundle")

    def validate(self, manifest=None, header=None, sha=None, size=None):
        bundle = self.manifest["bundle"]
        validate_contract(manifest if manifest is not None else self.manifest,
                          header if header is not None else self.header,
                          sha if sha is not None else bundle["sha256"],
                          size if size is not None else bundle["bytes"])

    def test_real_header_matches_frozen_inventory(self):
        self.validate()

    def test_corrupted_or_truncated_payload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "hash/size"):
            self.validate(sha="0" * 64)
        with self.assertRaisesRegex(ValueError, "hash/size"):
            self.validate(size=self.manifest["bundle"]["bytes"] - 1)

    def test_unmerged_head_cannot_be_silently_dropped_or_retargeted(self):
        for mutation in ("drop", "retarget"):
            with self.subTest(mutation=mutation):
                manifest = copy.deepcopy(self.manifest)
                entry = next(e for e in manifest["retirement_refs"] if e["preservation"] == "advertised-in-bundle")
                if mutation == "drop":
                    manifest["retirement_refs"].remove(entry)
                else:
                    entry["sha"] = "0" * 40
                with self.assertRaises(ValueError):
                    self.validate(manifest=manifest)

    def test_current_integration_cannot_enter_retirement_inventory(self):
        manifest = copy.deepcopy(self.manifest)
        entry = copy.deepcopy(manifest["retirement_refs"][0])
        entry["archive_ref"] = "refs/heads/integration/2026-10-15-16"
        manifest["retirement_refs"].append(entry)
        with self.assertRaisesRegex(ValueError, "excluded"):
            self.validate(manifest=manifest)

    def test_seed_cannot_drift_away_from_ancestry_claims(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["prerequisite"]["sha"] = "1" * 40
        with self.assertRaisesRegex(ValueError, "prerequisite"):
            self.validate(manifest=manifest)

    def test_merged_head_cannot_be_dropped_even_if_count_is_adjusted(self):
        manifest = copy.deepcopy(self.manifest)
        entry = next(e for e in manifest["retirement_refs"] if e["preservation"] == "ancestor-of-frozen-prerequisite")
        manifest["retirement_refs"].remove(entry)
        manifest["counts"]["retirement_refs"] -= 1
        with self.assertRaisesRegex(ValueError, "inventory is incomplete"):
            self.validate(manifest=manifest)

    def test_original_remote_namespace_is_preserved(self):
        manifest = copy.deepcopy(self.manifest)
        entry = next(e for e in manifest["retirement_refs"] if e["location"] == "origin")
        entry["original_ref"] = "refs/heads/unrelated"
        with self.assertRaisesRegex(ValueError, "namespace"):
            self.validate(manifest=manifest)


if __name__ == "__main__":
    unittest.main()
