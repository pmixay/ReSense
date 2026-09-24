#!/usr/bin/env python3
"""Experiment (P4, 24.09), not shipped behaviour: the ``elevated`` and ``floating``
infrastructure signatures demote only clusters that are long along the track or far away.

In the organizers' synthetic-obstacle recording (``labels/cloud_with_fake_obj.json``) these two
signatures demote real test obstacles to advisory. Hit: the 0.3 m cube floating mid-envelope at
47-52 m (``floating``, lateral 0.70-0.78 m), and the 2 x 2 m box hanging 0.2-0.8 m into the
top of the envelope (``elevated``). The false alarms they suppress on the organizers' station
recording are one structure ~104 m ahead of the stopped train, 3.9-5.7 m long. Keeping the
demotion for clusters longer than ``SIG_MAXLEN`` m or farther than ``SIG_MAXDIST`` m separates
the two on these data. The results are in docs/P4_AUDIT.md "Organizer synthetic-obstacle
recording". The rule lives in ``resense/clustering.py`` (P3); this script patches it in memory
so that the measurement can be repeated before anyone changes the detector:

    python scripts/short_signature_experiment.py run --npy /data/cache/cloud_with_fake_obj --out out/fake-short.jsonl --quiet
    python scripts/short_signature_experiment.py eval_real --cache /data/cache --out out/eval/short --bags <six bags>

The first argument selects ``resense <args>`` or ``scripts/eval_real.py <args>``; the patch is
inherited by eval_real's worker processes (fork). ``SIG_MAXLEN`` (default 3.0) and
``SIG_MAXDIST`` (default 100.0) are read from the environment.
"""
import os
import runpy
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import resense.clustering as clustering  # noqa: E402

MAX_LENGTH = float(os.environ.get("SIG_MAXLEN", "3.0"))
MAX_DISTANCE = float(os.environ.get("SIG_MAXDIST", "100.0"))
_original = clustering._advisory_reason


def _short_signatures(b, dist, lateral, zone, dy, h, cfg, axis_valid, height_valid):
    reason = _original(b, dist, lateral, zone, dy, h, cfg, axis_valid, height_valid)
    if reason in ("elevated", "floating") and float(b.size[0]) <= MAX_LENGTH and dist <= MAX_DISTANCE:
        return ""
    return reason


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "eval", "eval_real"):
        raise SystemExit(__doc__)
    mode = sys.argv.pop(1)
    clustering._advisory_reason = _short_signatures
    if mode == "eval_real":
        sys.argv = [os.path.join(os.path.dirname(__file__), "eval_real.py")] + sys.argv[1:]
        runpy.run_path(sys.argv[0], run_name="__main__")
    else:
        from resense.cli import main as cli_main
        sys.argv = ["resense", mode] + sys.argv[1:]
        cli_main()


if __name__ == "__main__":
    main()
