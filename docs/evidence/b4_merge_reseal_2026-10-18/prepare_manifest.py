"""Create the requested B4 integration seal from committed measured evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]

from scripts import detector_freeze as freeze  # noqa: E402
from scripts import release_meta  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    acceptance = json.loads((HERE / 'acceptance.json').read_text())
    assert acceptance['status'] == 'PAIRED_MERGED_SOURCE_CHECKS_PASS'
    assert set(release_meta.declared_versions(ROOT).values()) == {'1.2.0'}
    for name, digest in acceptance['input_sha256'].items():
        assert sha(ROOT / name) == digest, name
    previous_path = ROOT / 'docs/evidence/detector_freeze_2026-10-18_1.2.0_candidate.json'
    previous = json.loads(previous_path.read_text())
    manifest = freeze.create_manifest(ROOT, ROOT / previous['baseline']['path'], HERE / 'gate.json')
    assert manifest['source_sha256'] == acceptance['source_sha256']
    assert manifest['measured_commit'] == acceptance['measured_commit']
    evidence_commit = manifest['source_commit']
    references = []
    # Bind every retained run receipt, raw archive, comparator and human-readable
    # integration record. The manifest and its later verification are separate.
    for path in sorted(HERE.iterdir()):
        if path.is_file():
            name = str(path.relative_to(ROOT))
            digest = sha(path)
            blob = subprocess.check_output(['git', 'show', f'{evidence_commit}:{name}'], cwd=ROOT)
            assert hashlib.sha256(blob).hexdigest() == digest, f'uncommitted evidence: {name}'
            references.append({'path': name, 'sha256': digest})
    for name in ('docs/evidence/p4_audit_b4_6cc27be_2026-10-18/README.md',
                 'docs/evidence/p4_audit_b4_6cc27be_2026-10-18/raw_6cc27be.tar.xz',
                 'docs/evidence/p4_review_1.2.0_2026-10-18/README.md',
                 'docs/evidence/p4_review_1.2.0_2026-10-18/x3_raw_1.2.0.tar.xz',
                 'scripts/check_archived_lint.py', 'tests/test_archived_lint.py',
                 'docs/evidence/integration_ci_2026-10-16/lint_record/snapshot_lock.json'):
        digest = sha(ROOT / name)
        blob = subprocess.check_output(['git', 'show', f'{evidence_commit}:{name}'], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == digest
        references.append({'path': name, 'sha256': digest})
    manifest['authorization'] = (
        'User explicitly requested switching to det/b4-orientation, merging main, resealing '
        'and checking the seal in a clean checkout before/after native build on 2026-10-18. '
        'User additionally requested merging P4 branch ccr-027997e8-kqywat and deleting it. '
        'No release, deployment, tag or merge back to main is authorized by this seal.')
    manifest['lineage'] = {
        'previous_manifest': str(previous_path.relative_to(ROOT)),
        'previous_manifest_sha256': sha(previous_path),
        'measured_merge_commit': manifest['measured_commit'],
        'main_merged': '9917851', 'b4_parent': '6cc27be', 'p4_merged': '8a0af65',
        'evidence_commit': evidence_commit,
        'change': 'B4 channel-axis mount check and voting cadence combined with main readiness guard; 1.2.0 defaults retained.'}
    manifest['decisions'] = {**previous['decisions'],
        'B4': 'Recover tested transformed Pandar mounts with channel-axis evidence; preserve readiness and obstacle STOP precedence.',
        'default_replay': '0; remains opt-in per user decision.',
        'review_scope': 'Candidate source/evidence integrity; parent P4 reviews retained, final merged-source P4 acceptance pending.'}
    manifest['reviewed_supporting_evidence'] = references
    manifest['release_review'] = {
        'kind': 'candidate_integrity_only', 'P4_final_acceptance': 'PENDING_FOR_MERGED_SOURCE',
        'release_authorized': False,
        'P4_parent_reviews': '0bbc6ed: no blocking finding; 6cc27be: B1 closed, B4/X3 pass, fresh gate required.',
        'integration_measurements': 'Fresh same-native paired gates/X3/B4; raw-frame audits and affected tests on committed merge.'}
    manifest['limits'] = [
        'Integrity verification is not a recording replay, release or independent P4 approval.',
        'B4 covers transformed upright-Pandar clouds with usable genuine channel evidence, not physical horizontal scanners or ring-free Falcon.',
        'Late/missing channel evidence can leave the original wrong-mount failure; P4 S1-S4 availability/coverage findings remain documented.',
        'Curves, N3 dust robustness and N6 60 m acceptance remain open; experimental suppression/extension remain off.',
        'No new Docker/DDS or full Falcon run is claimed for the merged B4 source.',
        'Historical missing Windows Set O frame 332 remains a provenance limit; X3 uses the verified Linux reference.'
    ]
    target = ROOT / 'docs/evidence/detector_freeze_2026-10-18_b4_merged.json'
    assert not target.exists(), 'refuse to overwrite an existing seal'
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    assert freeze.verify_manifest(ROOT, manifest) == []
    print(json.dumps({'manifest': str(target.relative_to(ROOT)), 'sha256': sha(target),
                      'files': len(manifest['files']), 'source_sha256': manifest['source_sha256'],
                      'supporting_references': len(references)}))


if __name__ == '__main__':
    main()
