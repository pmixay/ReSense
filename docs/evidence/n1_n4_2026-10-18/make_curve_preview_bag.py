#!/usr/bin/env python3
"""RViz-only reconstruction of decoded points from curve frames130–199.

The geometry is original; transport serialization and empty slots are recreated.
This preview is not used for detector quality scoring or performance acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from rosbags.typesys import Stores, get_typestore

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import make_smoke_bag as smoke  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    meta = json.loads((args.cache/'meta.json').read_text())[130:200]
    ts = get_typestore(Stores.ROS2_HUMBLE)
    smoke.FRAME_ID, smoke.TOPIC = meta[0]['frame_id'], meta[0]['topic']
    def messages():
        for item in meta:
            with np.load(args.cache/f"f_{item['i']:05d}.npz") as data:
                payload = smoke.make_message(ts, data['xyz'], data['inten'], data['ring'],
                                             int(item['stamp']*1e9), item['stamp'],
                                             np.random.default_rng(item['i']))
            if not item['has_ring']:
                parsed = ts.deserialize_cdr(payload, smoke.MSGTYPE)
                parsed.fields = [field for field in parsed.fields if field.name != 'ring']
                payload = ts.serialize_cdr(parsed, smoke.MSGTYPE)
            yield payload
    smoke.write_bag(str(args.out), messages(), int(meta[0]['bag_t']*1e9), 100_000_000)
    receipt = {'purpose':'RViz visual preview only; regenerated CDR/empty slots, original decoded points',
               'source_recording':args.cache.name, 'source_frames':[130,199], 'frames':len(meta),
               'cache_metadata_sha256':hashlib.sha256((args.cache/'meta.json').read_bytes()).hexdigest()}
    (Path(__file__).parent/'curve_preview_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
