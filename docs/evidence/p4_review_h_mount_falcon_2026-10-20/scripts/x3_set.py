"""X3 (``scripts/robustness_battery.py``, unchanged) with config overrides, for the switch-off runs of a P4 review:
the battery's own main and comparison; only its worker subprocess is started through this file, which installs
the overrides on the judge's ``NodeReplica`` (as ``p4_handoff_2026-10-20/scripts/judge_runner_set.py`` does for
``judge_runner.py``) before the battery's unmodified ``worker`` loads the judge probe. Every worker writes the
effective overrides and the replica's resulting config values to its process.log (``x3_set overrides``), so a
run can be checked to have used them.

    RESENSE_REPO=<tree> X3_SET='{"cluster.mount_cross_tol": 0}' python x3_set.py --repo <tree> --cache <decoded> --out <json> -j 2
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(os.environ["RESENSE_REPO"]).resolve()
sys.path.insert(0, str(REPO / "scripts"))
import robustness_battery as rb  # noqa: E402

SETS = json.loads(os.environ.get("X3_SET", "{}"))

if len(sys.argv) == 3 and sys.argv[1] == "--worker":
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(rb.JUDGE))
    import judge_runner as jr  # noqa: E402  (the module probe.py imports NodeReplica from)
    _Replica = jr.NodeReplica

    def replica(*a, **k):
        rep = _Replica(*a, overrides={**SETS, **(k.pop("overrides", None) or {})}, **k)
        got = {key: getattr(getattr(rep.cfg, key.split(".", 1)[0]), key.split(".", 1)[1]) for key in SETS}
        print("x3_set overrides", json.dumps(SETS), "effective", json.dumps(got), flush=True)
        return rep
    jr.NodeReplica = replica
    rb.worker(sys.argv[2])
else:
    if not SETS:
        raise SystemExit("X3_SET is empty: run scripts/robustness_battery.py itself")
    here = str(Path(__file__).resolve())
    _run = rb.subprocess.run

    def run(cmd, *a, **k):
        if len(cmd) == 4 and cmd[2] == "--worker" and Path(cmd[1]).name == "robustness_battery.py":
            cmd = [cmd[0], here, "--worker", cmd[3]]
            k["env"] = {**k["env"], "X3_SET": json.dumps(SETS)}
        return _run(cmd, *a, **k)
    rb.subprocess.run = run
    sys.exit(rb.main())
