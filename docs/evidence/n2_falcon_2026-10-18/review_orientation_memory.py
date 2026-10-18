"""Independent scaled history-bound probe; does not modify source or datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def owned_size(value, seen=None):
    """Count each owned object once; ndarray getsizeof includes its owned buffer."""
    if seen is None:
        seen = set()
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        return size + sum(owned_size(key, seen) + owned_size(item, seen)
                          for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return size + sum(owned_size(item, seen) for item in value)
    return size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source.resolve()))
    import numpy as np

    from resense.calibration import OrientationReplayBuffer
    from resense.frame import Frame

    original_bound = OrientationReplayBuffer.MAX_BYTES
    OrientationReplayBuffer.MAX_BYTES = 65536
    frame = Frame(np.empty((0, 3), np.float32), np.empty(0, np.float32), stamp=1,
                  meta={"nested": [[0] * 5 for _ in range(600)]})
    buffer = OrientationReplayBuffer(4)
    accepted = buffer.capture(frame, None)
    actual = None
    if accepted:
        saved = buffer.frames[0][0]
        actual = owned_size((saved.xyz, saved.intensity, saved.ring, saved.meta,
                             saved.stamp, saved.frame_id, None))
    result = {
        "source": str(args.source.resolve()),
        "calibration_sha256": hashlib.sha256(
            (args.source / "resense/calibration.py").read_bytes()).hexdigest(),
        "scaled_limit_bytes": OrientationReplayBuffer.MAX_BYTES,
        "original_limit_bytes": original_bound,
        "accepted": accepted, "reason": buffer.reason,
        "charged_bytes": buffer.used_bytes,
        "actual_retained_payload_bytes_excluding_frame_header": actual,
        "within_bound": not accepted or actual <= OrientationReplayBuffer.MAX_BYTES,
        "method": "600 unique five-element nested lists; source lists use96bytes each, "
                  "deepcopy may use120. The source-memory estimate must bound retained copies. "
                  "This scales the limit for a small deterministic probe, not a detector replay.",
    }
    OrientationReplayBuffer.MAX_BYTES = original_bound
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
