"""Fail-closed immutable evidence lint contract, independent of archived evaluations or Git history."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('archived_lint', Path(__file__).resolve().parents[1]
                                            / 'scripts/check_archived_lint.py')
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class ArchivedLintContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = 'docs/evidence/frozen'
        self.helper = self.folder + '/helper.py'
        self.index = self.folder + '/HASHES.json'
        (self.root / self.folder).mkdir(parents=True)
        self.data = b'import unused\n'
        (self.root / self.helper).write_bytes(self.data)
        index = json.dumps({'files': [{'path': 'helper.py', 'sha256': policy.sha256(self.data)}]}).encode()
        (self.root / self.index).write_bytes(index)
        self.lock = {'schema': 'resense-archived-lint-v1', 'ruff': '0.15.8', 'python_roots': [self.folder],
                     'files': [self.record(self.helper), self.record(self.index)],
                     'exclusions': [{'path': self.helper, 'provenance': {
                         'kind': 'package-sha256', 'path': self.index, 'pointer': ['files', 0, 'sha256']}}]}

    def record(self, path):
        data = (self.root / path).read_bytes()
        return dict(path=path, bytes=len(data), sha256=policy.sha256(data), git_blob=policy.git_blob(data))

    def test_exact_package_hash_and_git_blob_pass(self):
        self.assertEqual(policy.verify(self.root, self.lock), [self.helper])

    def test_changed_helper_fails(self):
        (self.root / self.helper).write_bytes(b'import fixed\n')
        with self.assertRaisesRegex(ValueError, 'changed immutable'):
            policy.verify(self.root, self.lock)

    def test_line_ending_rewrite_is_not_silently_normalized(self):
        (self.root / self.helper).write_bytes(self.data.replace(b'\n', b'\r\n'))
        with self.assertRaisesRegex(ValueError, 'changed immutable'):
            policy.verify(self.root, self.lock)

    def test_missing_helper_fails(self):
        (self.root / self.helper).unlink()
        with self.assertRaises(FileNotFoundError):
            policy.verify(self.root, self.lock)

    def test_rewritten_package_index_fails(self):
        (self.root / self.index).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed immutable'):
            policy.verify(self.root, self.lock)

    def test_git_blob_mismatch_fails_even_with_correct_sha256(self):
        self.lock['files'][0]['git_blob'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'changed immutable'):
            policy.verify(self.root, self.lock)

    def test_wrong_historical_hash_fails_even_with_relocked_index(self):
        (self.root / self.index).write_text(json.dumps({'files': [{'sha256': '0' * 64}]}))
        self.lock['files'][1] = self.record(self.index)
        with self.assertRaisesRegex(ValueError, 'package hash mismatch'):
            policy.verify(self.root, self.lock)

    def test_unlisted_python_in_frozen_package_fails(self):
        (self.root / self.folder / 'new.py').write_text('pass\n')
        with self.assertRaisesRegex(ValueError, 'unlisted/missing'):
            policy.verify(self.root, self.lock)

    def test_nested_unlisted_python_fails(self):
        path = self.root / self.folder / 'nested'
        path.mkdir()
        (path / 'new.py').write_text('pass\n')
        with self.assertRaisesRegex(ValueError, 'unlisted/missing'):
            policy.verify(self.root, self.lock)

    def test_uninventoried_exclusion_fails(self):
        self.lock['exclusions'][0]['path'] = self.folder + '/other.py'
        with self.assertRaisesRegex(ValueError, 'exclusion inventory'):
            policy.verify(self.root, self.lock)

    def test_duplicate_exclusion_fails(self):
        self.lock['exclusions'] *= 2
        with self.assertRaisesRegex(ValueError, 'exclusion inventory'):
            policy.verify(self.root, self.lock)

    def test_duplicate_file_fails(self):
        self.lock['files'].append(copy.deepcopy(self.lock['files'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate snapshot'):
            policy.verify(self.root, self.lock)

    def test_paths_cannot_escape_or_be_patterns(self):
        for name in ('../helper.py', '/tmp/helper.py', 'C:/helper.py', 'docs/*.py', 'docs/**', 'docs/[ab].py'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                policy.safe_path(self.root, name)

    def test_existing_git_pinned_launch_provenance(self):
        command = f"git checkout {'a' * 40}; python {self.helper}"
        (self.root / self.index).write_text(json.dumps({'argv': [command]}))
        self.lock['files'][1] = self.record(self.index)
        provenance = {'kind': 'git-pinned-launch', 'path': self.index, 'pointer': ['argv', 0],
                      'commit': 'a' * 40, 'source_blob': policy.git_blob(self.data)}
        self.lock['exclusions'][0]['provenance'] = provenance
        self.assertEqual(policy.verify(self.root, self.lock), [self.helper])
        provenance['commit'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'launch provenance'):
            policy.verify(self.root, self.lock)

    def test_live_full_path_reference_fails(self):
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/live.py').write_text(f'path = {self.helper!r}\n')
        with self.assertRaisesRegex(ValueError, 'live reference'):
            policy.audit_live_references(self.root, self.lock)

    def test_live_module_import_fails(self):
        (self.root / 'resense').mkdir()
        (self.root / 'resense/live.py').write_text('from docs.evidence.frozen.helper import value\n')
        with self.assertRaisesRegex(ValueError, 'live import'):
            policy.audit_live_references(self.root, self.lock)

    def test_live_from_package_import_fails(self):
        (self.root / 'resense').mkdir()
        (self.root / 'resense/live.py').write_text('from docs.evidence.frozen import helper\n')
        with self.assertRaisesRegex(ValueError, 'live import'):
            policy.audit_live_references(self.root, self.lock)

    def test_removed_exclusion_cannot_bypass_policy_lock(self):
        path = self.root / 'lock.json'
        original = json.dumps(self.lock).encode()
        changed = copy.deepcopy(self.lock)
        changed['exclusions'] = []
        path.write_text(json.dumps(changed))
        with patch.object(policy, 'ROOT', self.root), patch.object(policy, 'MANIFEST', 'lock.json'), \
                patch.object(policy, 'LOCK_SHA256', policy.sha256(original)):
            with self.assertRaisesRegex(ValueError, 'snapshot policy changed'):
                policy.main([])

    def test_missing_policy_lock_fails(self):
        with patch.object(policy, 'ROOT', self.root), patch.object(policy, 'MANIFEST', 'absent.json'):
            with self.assertRaises(FileNotFoundError):
                policy.main([])

    def test_live_search_path_addition_fails(self):
        (self.root / 'tests').mkdir()
        (self.root / 'tests/live.py').write_text(f'import sys\nsys.path.insert(0, {self.folder!r})\n')
        with self.assertRaisesRegex(ValueError, 'live reference'):
            policy.audit_live_references(self.root, self.lock)

    def test_json_witness_stays_a_live_linted_consumer(self):
        (self.root / 'tests').mkdir()
        (self.root / 'tests/live.py').write_text(f'witness = {self.folder + "/witness.json"!r}\n')
        self.assertEqual(policy.audit_live_references(self.root, self.lock), ['tests/live.py'])

    def test_live_shell_invocation_fails(self):
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/live.sh').write_text(f'python {self.helper}\n')
        with self.assertRaisesRegex(ValueError, 'live invocation'):
            policy.audit_live_references(self.root, self.lock)

    def test_exclusions_are_exact_absolute_paths_not_directory_rules(self):
        cmd = policy.lint_command(self.root, [self.helper], 'ruff')
        self.assertEqual(cmd[cmd.index('--extend-exclude') + 1], str((self.root / self.helper).resolve()))
        self.assertNotIn('--ignore', cmd)
        self.assertEqual(cmd[-1], str(self.root))


if __name__ == '__main__':
    unittest.main()
