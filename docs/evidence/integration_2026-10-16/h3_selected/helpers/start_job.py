#!/usr/bin/env python3
"""Detach a uniquely logged gate controller from the Windows terminal harness."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

root = Path(__file__).resolve().parent.parent
assert root.is_dir()
job = "controller-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
argv = [sys.executable, "-u", str(root / "helpers/gate_control.py"), *sys.argv[1:]]
flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
with (root / (job + ".stdout.log")).open("wb") as out, (root / (job + ".stderr.log")).open("wb") as err:
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                               creationflags=flags, close_fds=True)
record = dict(job=job, pid=process.pid, argv=argv)
(root / (job + ".json")).write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
