"""Map a node capture onto the frame indices of a recording (the re-judgement of 26.09).

``status.jsonl`` of ``scripts/dry_run.sh`` holds one FrameResult JSON per processed frame with the
message's header stamp in ``stamp``; ``setO_header_stamps.jsonl`` holds ``{"frame", "stamp"}`` per
message of ``cloud_with_fake_obj`` (its header stamps, read with rosbags). The output adds ``frame``
so that ``scripts/score_fake_objects.py`` can grade what the node published through ROS. Frames the
node did not process are absent (the scorer grades the processed frames).

    python node_to_frames.py setO_header_stamps.jsonl status.jsonl frames.jsonl
"""
import json
import sys


def main(stamps_path, capture_path, out_path):
    by_stamp = {}
    with open(stamps_path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            by_stamp[round(float(r["stamp"]), 4)] = int(r["frame"])
    n = miss = 0
    seen = set()
    with open(capture_path, encoding="utf-8") as fh, open(out_path, "w", encoding="utf-8") as fo:
        for line in fh:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "stamp" not in r or "detections" not in r:
                continue
            f = by_stamp.get(round(float(r["stamp"]), 4))
            if f is None:
                miss += 1
                continue
            if f in seen:
                continue
            seen.add(f)
            r["frame"] = f
            fo.write(json.dumps(r) + "\n")
            n += 1
    print(f"mapped {n} node frames onto the recording's frame indices, {miss} unmapped")


if __name__ == "__main__":
    main(*sys.argv[1:4])
