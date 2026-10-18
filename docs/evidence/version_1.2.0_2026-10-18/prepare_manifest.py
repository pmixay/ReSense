"""Bind a reviewable candidate; never assert P4 acceptance or authorize release."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]

from scripts import detector_freeze as freeze  # noqa: E402
from scripts import release_meta  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    target = ROOT / 'docs/evidence/detector_freeze_2026-10-18_1.2.0_candidate.json'
    assert not target.exists(), 'Refuse to overwrite a candidate manifest'
    assert set(release_meta.declared_versions(ROOT).values()) == {'1.2.0'}
    acceptance = read(HERE / 'gate_acceptance.json')
    assert acceptance['status'] == 'COMPLETE_GATE_AND_VERSION_ONLY_PARITY_PASS'
    review_path = ROOT / 'docs/evidence/p4_followup_2026-10-18/version_gate_review.json'
    review = read(review_path)
    assert review['status'] == 'INDEPENDENT_VERSION_GATE_REVIEW_PASS'
    previous_path = ROOT / 'docs/evidence/detector_freeze_2026-10-18_lidar.json'
    previous = read(previous_path)
    baseline_path = ROOT / previous['baseline']['path']
    manifest = freeze.create_manifest(ROOT, baseline_path, HERE / 'gate.json')
    assert manifest['measured_commit'] == 'e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569'
    assert manifest['source_sha256'] == acceptance['source_sha256']
    assert review['source_commit'] == manifest['measured_commit']
    assert review['source_sha256'] == manifest['source_sha256']
    for receipt in (review, acceptance):
        for name, digest in receipt['input_sha256'].items():
            assert sha(Path(name)) == digest, f'Stale reviewed input: {name}'
    prefix = 'docs/evidence/version_1.2.0_2026-10-18/'
    followup = 'docs/evidence/p4_followup_2026-10-18/'
    references = [prefix + name for name in ('PLAN.md', 'gate_execution.json',
                  'gate_frame_review.json', 'gate_acceptance.json', 'raw/gate_manifest.json',
                  'raw/gate.tar.gz', 'junit-release.xml', 'main_j1_target.json')]
    references += [followup + name for name in ('source_continuity.json', 'p4_intake_manifest.json',
                   'version_gate_review.json', 'check_source_continuity.py', 'review_version_gate.py')]
    references += ['docs/evidence/lidar_adaptation_2026-10-18/default_off/x3.json',
                   'docs/evidence/lidar_adaptation_2026-10-18/default_off/independent_x3_archive.json',
                   'docs/evidence/lidar_adaptation_2026-10-18/default_off/independent_acceptance.json',
                   'docs/evidence/lidar_adaptation_2026-10-18/default_off/INDEPENDENT_DDS_REVIEW.md']
    evidence_commit = manifest['source_commit']
    previous_blob = subprocess.check_output(
        ['git', 'show', f'{evidence_commit}:{previous_path.relative_to(ROOT)}'], cwd=ROOT)
    assert hashlib.sha256(previous_blob).hexdigest() == sha(previous_path)
    refs = []
    for relative in references:
        path = ROOT / relative
        digest = sha(path)
        blob = subprocess.check_output(['git', 'show', f'{evidence_commit}:{relative}'], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == digest, f'Uncommitted supporting evidence: {relative}'
        refs.append({'path': relative, 'sha256': digest})
    manifest['authorization'] = (
        'User requested locally actionable P4 follow-up on 2026-10-18: prepare a separately '
        'versioned LiDAR candidate and its reviewable integrity seal. The captain selected '
        'sealed main 1.1.0 for next J1. No release/tag/deployment is authorized.')
    manifest['lineage'] = {'previous_manifest': str(previous_path.relative_to(ROOT)),
                           'previous_manifest_sha256': sha(previous_path),
                           'previous_authorization': previous['authorization'],
                           'selected_measured_commit': manifest['measured_commit'],
                           'evidence_commit': evidence_commit,
                           'change': 'Exactly four 1.1.0 to 1.2.0 declaration lines; two inside frozen scope. No runtime behavior change.'}
    manifest['decisions'] = {**previous['decisions'],
        'package_version': '1.2.0 unreleased candidate; four declarations synchronized.',
        'next_J1_target': 'Captain selected sealed main 1.1.0 at 3b7d7aa7cbbf238c21f84330497697da131b7cb9.',
        'review_scope': 'This manifest freezes bytes for review; final P4 candidate acceptance is pending.'}
    manifest['reviewed_supporting_evidence'] = refs
    manifest['release_review'] = {
        'kind': 'candidate_integrity_only', 'P4_final_acceptance': 'PENDING',
        'P3_coordination_acknowledgement': 'PENDING', 'release_authorized': False,
        'integrity_review': 'Local agent source and raw-evidence reviews; not P4 final approval.',
        'P4_development_check': 'b423562 only; original report1b88016 preserved without relabeling.',
        'supporting_run_identity': 'X3, full Falcon and Docker/DDS remain cecab1b runs; source continuity is proven separately.'}
    manifest['limits'] = list(previous['limits']) + [
        'Standard status frozen denotes source/evidence integrity, not a released or P4-approved candidate.',
        'New 1.2.0 gate is measured at e9d8fc6; earlier X3/Falcon/DDS captures are not newly run 1.2.0 evidence.',
        'Automatic sideways orientation and curve-axis bias remain unresolved; explicit mapping controls do not prove universal automatic orientation.',
        'Final P4 acceptance, P3 coordination, hosted CI and release remain pending.']
    manifest['created_utc'] = datetime.now(timezone.utc).isoformat()
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    assert not freeze.verify_manifest(ROOT, manifest)
    print(json.dumps({'manifest': str(target.relative_to(ROOT)), 'sha256': sha(target),
                      'source_sha256': manifest['source_sha256'], 'source_files': len(manifest['files']),
                      'P4_final_acceptance': 'PENDING', 'release_authorized': False}))


if __name__ == '__main__':
    main()
