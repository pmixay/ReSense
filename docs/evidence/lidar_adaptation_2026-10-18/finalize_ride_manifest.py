"""Finalize a streamed intake receipt only after source metadata and all arrays validate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.cache_extended_ride import PUBLIC_URL, resolve_yadisk_asset  # noqa: E402
from scripts.cache_frames import _atomic_json  # noqa: E402
from scripts.cache_io import validate_extended_ride_cache, validate_ride_intake_manifest  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    if not receipt.get('verified') or receipt.get('mode') != 'ride':
        raise ValueError('a verified full-archive ride receipt is required')
    source = resolve_yadisk_asset()
    if not source.get('sha256') or (receipt['sha256'], receipt['bytes']) != (source['sha256'], source['size']):
        raise ValueError('verified archive receipt differs from published source metadata')
    expected = {f'new_data_{n}': 51 for n in range(221)}
    if receipt.get('frame_counts') != expected or receipt.get('total_frames') != 11271:
        raise ValueError('receipt must contain exactly221 complete51-frame splits')
    print('Published archive hash/size and complete receipt match; validating every array.', flush=True)
    validation = validate_extended_ride_cache(str(args.cache), load_arrays=True)
    if validation['arrays_read'] != 11271:
        raise ValueError('every cached array must be read and validated')
    report = {
        'schema': 'resense-extended-ride-intake-v1', 'status': 'complete',
        'source_url': PUBLIC_URL, 'source_member': source['name'], 'source_modified': source.get('modified'),
        'archive_bytes': receipt['bytes'], 'archive_size_published': source['size'],
        'archive_size_verified': True, 'archive_checksum_published': True,
        'archive_sha256_published': source['sha256'], 'archive_sha256_actual': receipt['sha256'],
        'archive_sha256_verified': True, 'metadata_sha256': None,
        'metadata_note': 'Original metadata.yaml was not retained by the streaming intake; frame stamps are retained.',
        'cache_location': str(args.cache.resolve()),
        'encoding': 'compact16 NPY, each frame independently zstd level3 (.npy.zst)',
        'cache_splits': validation['splits'], 'cache_frames': validation['frames'],
        'cache_bytes': validation['compressed_bytes'], 'arrays_validated': validation['arrays_read'],
        'timestamp_coverage': {key: validation[key] for key in
                               ('first_frame', 'first_stamp', 'last_frame', 'last_stamp', 'duration_s',
                                'max_interval_s', 'intervals_over_0_15_s')},
        'verified_stream_receipt_sha256': hashlib.sha256(args.receipt.read_bytes()).hexdigest(),
        'finalizer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'provenance': 'Finalized from the separately retained full compressed-stream checksum receipt; no data regeneration.',
    }
    _atomic_json(str(args.cache / 'intake_manifest.json'), report)
    validate_ride_intake_manifest(str(args.cache), validation)
    args.evidence.write_text(json.dumps(report, indent=2) + '\n')
    print('Verified canonical intake manifest complete.', flush=True)


if __name__ == '__main__':
    main()
