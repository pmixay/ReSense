"""Audit real DDS capture against SQLite CDR and independent reviewed person anchors."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("capture", type=Path)
parser.add_argument("bag", type=Path)
parser.add_argument("--name", required=True)
args = parser.parse_args()
execution = json.loads((args.capture / "execution.json").read_text())
records = [json.loads(l) for l in (args.capture / "status.jsonl").read_text().splitlines()]
inputs = [r for r in records if "input_cdr_sha256" in r]
statuses = [r for r in records if "status" in r]
db = sqlite3.connect(f"file:{args.bag.resolve()}?mode=ro", uri=True)
expected, stamps = [], []
for timestamp, payload in db.execute("SELECT timestamp,data FROM messages ORDER BY timestamp"):
    expected.append(hashlib.sha256(payload).hexdigest())
    sec, nano = struct.unpack_from("<iI", payload, 4)
    stamps.append(sec + nano / 1e9)
assert [r["input_cdr_sha256"] for r in inputs] == expected, "DDS inputs differ from bag"
assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
processed = [r for r in statuses if 'frames' in r['status'].get('node', {})]
assert len(processed) == len(stamps)
assert all(abs(r['status']['stamp'] - stamp) < 1e-6 for r,stamp in zip(processed,stamps))
first_input = inputs[0]["received_wall"]
stops = [r for r in processed if r["status"]["decision"] == "STOP"]
assert stops, "no STOP"
first = stops[0]
assert first['received_wall'] - execution['player_started_wall'] <= 30
assert execution['node_returncode_during_playback'] is None
result = {"source": execution['source'], "profile": execution['profile'], "rate": execution['rate'],
          "input_cdr_count": len(inputs), "all_input_cdr_identical": True,
          "all_frame_status_stamps_match_input": True, "frame_status_count": len(processed),
          "first_stop_after_player_command_s": first['received_wall'] - execution['player_started_wall'],
          "first_stop_after_first_input_s": first['received_wall'] - first_input,
          "first_stop_distance_m": first['status']['nearest_distance'],
          "decisions_in_status_stream": dict(Counter(r['status']['decision'] for r in processed)),
          "frame_freshness_reasons": dict(Counter(r['status']['freshness']['reason'] for r in processed)),
          "counter_note": "node.frames is published before increment (detector_node.py:1053–1057); last index is N-1",
          "final_node_stats": processed[-1]['status']['node'],
          "sqlite_integrity": "ok"}
if args.name == 'falcon':
    receipt = json.loads((HERE / 'falcon_bag.json').read_text())
    anchors = json.loads((ROOT / 'docs/evidence/n2_falcon_2026-10-18/raw_person_review/atlas_proposals.json').read_text())['anchors']
    index = min(range(len(stamps)), key=lambda i: abs(stamps[i] - first['status']['stamp']))
    assert abs(stamps[index] - first['status']['stamp']) < 1e-6
    frame = receipt['rows'][index]['source_frame']
    before = max((a for a in anchors if a['frame'] <= frame), key=lambda a: a['frame'])
    after = min((a for a in anchors if a['frame'] >= frame), key=lambda a: a['frame'])
    t = (frame - before['frame']) / (after['frame'] - before['frame']) if after['frame'] != before['frame'] else 0
    center = [x + t*(y-x) for x,y in zip(before['discovery_center'], after['discovery_center'])]
    detections = first['status']['detections']
    match = [d for d in detections if all(abs(a-b) < tol for a,b,tol in zip(d['center'], center, (1.5,.8,1.0)))]
    assert match, 'first STOP does not match independent reviewed person trajectory'
    # Positive/negative controls of the identity gate: known person passes; displaced structure fails.
    assert not all(abs(a-b) < tol for a,b,tol in zip([115,8,-7], center, (1.5,.8,1.0)))
    result['person_check'] = {'source_frame': frame, 'reviewed_anchor_frames': [before['frame'],after['frame']],
                              'interpolated_raw_center': center, 'detection': match[0],
                              'tolerance_xyz_m': [1.5,.8,1.0], 'displaced_structure_rejected': True,
                              'scope': 'first STOP identity; not a new full-window accuracy score'}
video = args.capture / 'capture.mp4'
probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
stream = probe['streams'][0]
assert (stream['width'],stream['height']) == (1920,1080)
subprocess.run(['ffmpeg','-hide_banner','-v','error','-xerror','-i',str(video),'-f','null','-'], check=True)
result['video'] = {'duration_s': float(probe['format']['duration']), 'size_bytes': video.stat().st_size,
                   'sha256': hashlib.sha256(video.read_bytes()).hexdigest(), 'full_decode': 'PASS', 'size': [1920,1080]}
(HERE / f'{args.name}_playback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
