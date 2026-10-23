"""judge_runner.py (judgement_2026-10-13) with config overrides, for evaluation runs of an off-by-default switch
without editing configs/: the same NodeReplica, decoding, continuity rules and record format; every
``--set section.key=value`` (YAML value) is applied after the YAML is read, as the replica's own ``overrides``.

    RESENSE_REPO=<checkout> python judge_runner_set.py --bag <bag> --out <prefix> --set track.axis_joint_fit=true ...
"""
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../../judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402

sets = {}
argv = []
it = iter(sys.argv[1:])
for a in it:
    if a == "--set":
        k, v = next(it).split("=", 1)
        sets[k] = yaml.safe_load(v)
    else:
        argv.append(a)
_Replica = jr.NodeReplica
jr.NodeReplica = lambda *a, **k: _Replica(*a, overrides=sets, **k)
print("overrides:", sets, file=sys.stderr)
sys.argv = [sys.argv[0]] + argv
jr.main()
