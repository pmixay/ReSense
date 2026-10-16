"""External observer: preserve complete frame results without editing measured Git source.

Only wraps completed Detector.process calls in the two offline gate entry points.
The original result is returned unmodified. Capturing/serialization is outside its timing.
Any capture failure terminates the run (never silently falls back to missing evidence).
"""
import os
import sys

if os.environ.get("RESENSE_CAPTURE_DIR") and os.path.basename(sys.argv[0]) in ("regression_gate.py", "far_range_eval.py"):
    try:
        import dataclasses
        import hashlib
        import json
        from pathlib import Path
        import numpy as np
        from resense.detector import Detector

        original = Detector.process

        def plain(value):
            if dataclasses.is_dataclass(value):
                return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
            if isinstance(value, np.ndarray):
                return value.tolist()
            if isinstance(value, np.generic):
                return value.item()
            if isinstance(value, dict):
                return {k: plain(v) for k, v in value.items()}
            if isinstance(value, (tuple, list)):
                return [plain(v) for v in value]
            return value

        def observed(self, frame, *args, **kwargs):
            result = original(self, frame, *args, **kwargs)
            caller = sys._getframe(1)
            loc = caller.f_locals
            if caller.f_code.co_name == "run_piece":
                name = Path(loc["out_path"]).stem
                key = {"recording": loc["name"], "frame_id": loc["stem"], "piece": name,
                       "index": loc["i"]}
            elif caller.f_code.co_name == "run_sequence":
                job = loc["job"]
                seq = dict(file0=Path(job[0][0]).name, kind=job[3], d0=job[4], lateral=job[5],
                           reflectivity=job[6], seed=job[7], place=job[11], placement_mode=job[12])
                ident = hashlib.sha256(json.dumps(seq, sort_keys=True).encode()).hexdigest()[:20]
                name = "setF_" + seq["kind"] + "_" + seq["file0"].split("_0000")[0] + "_" + ident
                key = {"sequence": seq, "frame_id": loc["stem"], "index": loc["k"]}
            else:
                raise RuntimeError(f"unexpected gate process caller: {caller.f_code.co_name}")
            raw = {f.name: plain(getattr(result, f.name)) for f in dataclasses.fields(result)
                   if f.name not in ("xyz", "corridor_idx")}
            # Point-cloud contents are input/derived arrays, not serialized result fields.
            # Retain exact corridor membership identity without copying entire clouds.
            raw["corridor_idx"] = dict(shape=list(result.corridor_idx.shape), dtype=str(result.corridor_idx.dtype),
                sha256=hashlib.sha256(result.corridor_idx.tobytes()).hexdigest())
            row = dict(key=key, serialized=result.to_dict(), raw=raw)
            with (Path(os.environ["RESENSE_CAPTURE_DIR"]) / (name + ".jsonl")).open("a") as f:
                f.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            return result

        Detector.process = observed
    except BaseException:
        import traceback
        traceback.print_exc()
        os._exit(93)
