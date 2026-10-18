"""Apply a measured input stress transform outside the sealed detector source.

The hook runs after Set F injection, on the frame actually passed to process.
It is deliberately absent from ordinary execution and freeze/gate evidence.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def install():
    source = Path(os.environ["RESENSE_N2_SOURCE"]).resolve()
    helper = Path(os.environ["RESENSE_N2_HELPER"]).resolve()
    receipt_dir = Path(os.environ["RESENSE_N2_PROXY_RECEIPTS"]).resolve()
    sys.path.insert(0, str(source))
    from resense.detector import Detector
    from resense.frame import Frame

    module = sys.modules[Detector.__module__]
    if not Path(module.__file__).resolve().is_relative_to(source):
        raise RuntimeError("N2 proxy loaded a detector outside the pinned source")
    if getattr(Detector.process, "n2_transformed_input", False):
        raise RuntimeError("N2 proxy hook must be installed exactly once")
    spec = importlib.util.spec_from_file_location("n2_pinned_input_variants", helper)
    variants = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(variants)
    original = Detector.process
    stream = None
    stream_pid = None
    source_frame_index = 0
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / f"activated_{os.getpid()}.json").write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "source": str(source),
                "detector_module": str(module.__file__),
                "helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
                "argv": sys.argv,
                "transformed_input_only": True,
            },
            indent=2,
        ) + "\n"
    )

    def process(detector, frame, *args, **kwargs):
        nonlocal stream, stream_pid, source_frame_index
        chosen = variants.falcon_proxy_indices(frame.xyz)
        transformed = Frame(
            xyz=frame.xyz[chosen],
            intensity=frame.intensity[chosen],
            ring=None,
            stamp=frame.stamp,
            frame_id=frame.frame_id,
            meta=dict(frame.meta),
        )
        pid = os.getpid()
        if stream_pid != pid:
            if stream is not None:
                stream.close()
            stream = (receipt_dir / f"frames_{pid}.jsonl").open("a", buffering=1)
            stream_pid = pid
            source_frame_index = 0
        stream.write(
            json.dumps(
                {
                    "__source_frame_index": source_frame_index,
                    "frame_id": frame.frame_id,
                    "stamp": frame.stamp,
                    "before_points": len(frame.xyz),
                    "after_points": len(chosen),
                    "source_had_ring": frame.ring is not None,
                    "output_has_ring": transformed.ring is not None,
                    "metadata_preserved": transformed.meta == frame.meta,
                }
            ) + "\n"
        )
        source_frame_index += 1
        return original(detector, transformed, *args, **kwargs)

    process.n2_transformed_input = True
    Detector.process = process
