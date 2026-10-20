"""Acquire raw split zero only; do not claim a new whole-archive checksum."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import urllib.request

import zstandard

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.cache_extended_ride import HashingReader, resolve_yadisk_asset  # noqa: E402

WORK = Path('/tmp/opencode/l16-open-air-work')
WORK.mkdir(exist_ok=True)
target = WORK / 'new_data_0.db3'
assert not target.exists()
prior_path = Path('/tmp/opencode/resense-b4-data/cache/new_data/intake_manifest.json')
prior = json.loads(prior_path.read_text())
source = resolve_yadisk_asset()
assert source['sha256'] == prior['archive_sha256_actual']
assert source['size'] == prior['archive_bytes']
assert prior['archive_sha256_verified'] and prior['archive_size_verified']
with urllib.request.urlopen(source['download_url'], timeout=180) as response:
    hashed = HashingReader(response)
    with zstandard.ZstdDecompressor().stream_reader(hashed, closefd=False) as reader:
        with tarfile.open(fileobj=reader, mode='r|') as archive:
            for member in archive:
                print(member.name, member.size, flush=True)
                if member.isfile() and member.name.endswith('/new_data_0.db3'):
                    digest, size = hashlib.sha256(), 0
                    with archive.extractfile(member) as raw, target.open('xb') as out:
                        while block := raw.read(4 * 1024 * 1024):
                            digest.update(block)
                            out.write(block)
                            size += len(block)
                    assert size == member.size
                    break
            else:
                raise ValueError('split zero not found')
receipt = {'source': {k: v for k, v in source.items() if k != 'download_url'},
           'prior_full_intake_sha256': hashlib.sha256(prior_path.read_bytes()).hexdigest(),
           'compressed_bytes_read': hashed.bytes_read, 'compressed_prefix_sha256': hashed.digest.hexdigest(),
           'new_full_archive_checksum_verified': False, 'member': member.name,
           'member_bytes': size, 'member_sha256': digest.hexdigest()}
(WORK / 'ride-acquisition.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2), flush=True)
