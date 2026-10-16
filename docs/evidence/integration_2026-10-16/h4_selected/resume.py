"""Resume the registered affected/unreached checks in the original private volume."""
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
old = json.loads((P / "run-001/launch.json").read_text())
run = sys.argv[1] if len(sys.argv) > 1 else "run-002"
out = P / run
out.mkdir(exist_ok=False)
cmd = old["argv"][:]
cmd[cmd.index("--name") + 1] = "rs-h4-selected-independent-c9aea87-" + run.removeprefix("run-")
cmd += [run]
r = subprocess.run(cmd, capture_output=True, text=True)
(out / "launch.json").write_text(json.dumps(dict(argv=cmd, stdout=r.stdout, stderr=r.stderr,
                                              returncode=r.returncode), indent=2) + "\n", encoding="utf-8")
print(r.stdout + r.stderr)
raise SystemExit(r.returncode)
