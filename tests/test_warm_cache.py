"""Warm-cache evidence must not confuse a completed read with resident pages or playback success."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('warm_cache', Path(__file__).resolve().parents[1]
                                            / 'scripts/check_warm_cache.py')
cache = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cache)


def pages(resident=2, total=2):
    return {'pages': total, 'resident': resident, 'missing': total - resident,
            'page_size': 4096, 'fully_resident': total == resident}


class WarmCacheContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bag = Path(self.temp.name)
        (self.bag / 'metadata.yaml').write_text('storage_identifier: sqlite3\n')
        self.db = self.bag / 'bag_0.db3'
        self.db.write_bytes(b'x' * 8192)
        self.resource_patch = patch.object(cache, 'resources', return_value={'informational': True})
        self.resource_patch.start()
        self.addCleanup(self.resource_patch.stop)

    def test_complete_read_is_insufficient_when_pages_were_evicted(self):
        # Red witness for the previous cat-only policy: it succeeds despite nonresident pages.
        with self.db.open('rb') as file:
            self.assertEqual(cache.read_complete(file, 8192), 8192)
        with patch.object(cache, 'resident_pages', return_value=pages(1)):
            result = cache.inspect_bag(self.bag)
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['files'][0]['read_bytes'], 8192)
        self.assertIn('1 pages not resident', result['errors'][0])

    def test_warm_verified_requires_complete_read_and_residency(self):
        with patch.object(cache, 'resident_pages', side_effect=[pages(0), pages(2)]):
            result = cache.inspect_bag(self.bag)
        self.assertEqual(result['status'], 'WARM_VERIFIED')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['files'][0]['read_bytes'], self.db.stat().st_size)
        self.assertIn('not playback acceptance', result['scope'])

    def test_all_splits_rechecked_after_all_reads(self):
        (self.bag / 'bag_1.db3').write_bytes(b'y' * 8192)
        with patch.object(cache, 'resident_pages', side_effect=[pages(0), pages(0), pages(1), pages(2)]) as sampled:
            result = cache.inspect_bag(self.bag)
        self.assertEqual(sampled.call_count, 4)
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['files'][0]['after']['missing'], 1)
        self.assertTrue(result['files'][1]['after']['fully_resident'])

    def test_partial_read_fails(self):
        with self.assertRaisesRegex(ValueError, 'expected 8192, read 12'):
            cache.read_complete(io.BytesIO(b'x' * 12), 8192)

    def test_growing_read_fails(self):
        with self.assertRaisesRegex(ValueError, 'incomplete/changing'):
            cache.read_complete(io.BytesIO(b'x' * 8193), 8192)

    def test_changed_file_identity_fails(self):
        real_read = cache.read_complete

        def mutate(file, expected):
            read = real_read(file, expected)
            stamp = self.db.stat().st_mtime_ns + 1_000_000_000
            os.utime(self.db, ns=(stamp, stamp))
            return read
        with patch.object(cache, 'resident_pages', return_value=pages()), patch.object(cache, 'read_complete', mutate):
            result = cache.inspect_bag(self.bag)
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('file changed during warm read', result['errors'][0])

    def test_missing_metadata_fails(self):
        (self.bag / 'metadata.yaml').unlink()
        result = cache.inspect_bag(self.bag)
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('missing bag metadata', result['errors'][0])

    def test_missing_database_fails(self):
        self.db.unlink()
        result = cache.inspect_bag(self.bag)
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('no SQLite', result['errors'][0])

    def test_unavailable_residency_is_error_not_warm_claim(self):
        with patch.object(cache, 'resident_pages', side_effect=OSError('mincore denied')):
            result = cache.inspect_bag(self.bag)
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('mincore denied', result['errors'][0])

    def test_observation_neither_warms_nor_claims_warm(self):
        with patch.object(cache, 'resident_pages', return_value=pages(0)), patch.object(cache, 'read_complete') as read:
            result = cache.inspect_bag(self.bag, observe_only=True)
        read.assert_not_called()
        self.assertEqual(result['status'], 'OBSERVED')
        self.assertEqual(result['files'][0]['read_bytes'], 0)
        self.assertFalse(result['files'][0]['after']['fully_resident'])

    def test_error_receipt_is_retained_and_returns_nonzero(self):
        out = self.bag / 'receipt.json'
        with patch.object(cache, 'resident_pages', return_value=pages(1)):
            self.assertEqual(cache.main([str(self.bag), '--out', str(out)]), 1)
        self.assertEqual(json.loads(out.read_text())['status'], 'ERROR')
        with self.assertRaises(SystemExit):
            cache.main([str(self.bag), '--out', str(out)])

    def test_actual_linux_read_and_mincore_preserve_file_bytes(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        if sys.platform != 'linux':
            with self.db.open('rb') as file, self.assertRaisesRegex(RuntimeError, 'requires Linux'):
                cache.resident_pages(file)
            return
        result = cache.inspect_bag(self.bag)
        self.assertEqual(result['status'], 'WARM_VERIFIED', result['errors'])
        self.assertEqual(result['files'][0]['after']['missing'], 0)
        self.assertEqual(before, hashlib.sha256(self.db.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
