"""Run chosen X3 cases through the committed battery worker under several OPENBLAS_CORETYPE values and
compare their metrics with the Windows baseline entries (environment calibration on the 707ea9c control).

Lint-clean reformat (16.10) of the script that produced coretype_result.json; the logic is unchanged and
the bytes that ran are in commit d656158.

    python coretype_probe.py Haswell SkylakeX
"""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

H = Path("/home/user/ReSense")
D = Path("/home/user/rs-data")
spec = importlib.util.spec_from_file_location("rb", H / "scripts/robustness_battery.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)
win = json.loads((H / "docs/evidence/p4_start_2026-10-15/battery_707ea9c.json").read_text())
lin = json.loads((D / "p4out/runtime_comparison.json").read_text())
cases = sorted(lin["differences"]) + ["doubleT_obstacle/nominal", "cloud_with_fake_obj/nominal"]
repo = Path("/home/user/rs-707ea9c")
out = D / "blas/coretype"
out.mkdir(parents=True, exist_ok=True)


def run(item):
    ct, key = item
    bag, var = key.split("/")
    folder = out / ct / bag / var
    folder.mkdir(parents=True, exist_ok=True)
    job = {"repo": str(repo), "cache": str(D / "decoded" / bag), "prefix": str(folder / "probe"),
           "args": rb.VARIANTS[var], "seed": int(var[-1]) if var.startswith("drop30_s") else 7}
    (folder / "job.json").write_text(json.dumps(job))
    env = dict(rb.environment(repo, None), OPENBLAS_CORETYPE=ct)
    subprocess.run([sys.executable, str(H / "scripts/robustness_battery.py"), "--worker", str(folder / "job.json")],
                   cwd=repo, env=env, check=True, capture_output=True)
    meta, _ = rb.cache_meta(D / "decoded" / bag, rb.BAGS[bag])
    labels = (json.loads((repo / f"labels/{bag}.json").read_text())
              if bag in ("doubleT_obstacle", "cloud_with_fake_obj") else None)
    m = rb.summarize(rb.checked_rows(Path(job["prefix"] + ".jsonl"), meta, 2 if var == "hz5" else 1), labels)
    return ct, key, m == win["entries"][key]["metrics"], m["stop_frames"], win["entries"][key]["metrics"]["stop_frames"]


items = [(ct, k) for ct in sys.argv[1:] for k in cases]
res = list(ThreadPoolExecutor(4).map(run, items))
for r in res:
    print(*r, flush=True)
json.dump([list(r) for r in res], open(out / "result.json", "w"), indent=1)
