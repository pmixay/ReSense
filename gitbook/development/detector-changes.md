# Changing the detector

The detector is sealed: `docs/evidence/detector_freeze_2026-09-27.json` lists every file that
determines its output (`resense/`, `native/`, `configs/`, the ROS parameter copy, the learned model)
by SHA256, and CI's `checks` job fails when one changes without a new seal. A detector change
therefore needs evidence that it does not make anything worse.

## The regression gate

One command re-runs the real-data rows (the six recordings), the organizers' synthetic objects
(set O), the 20-minute ride and the long-range synthetic set, and compares every gated metric with
the committed baseline:

```bash
python scripts/regression_gate.py --cache /data/cache \
    --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json
```

Exit 0 = every gated metric identical or better. It needs the frames cached once
([Offline analysis](../guides/offline-analysis.md#the-real-data-report-card)); the ride and set F
need `/data/cache/new_data` (streamed split by split as in
[`docs/VM_GUIDE.md` §2.3](https://github.com/pmixay/ReSense/blob/main/docs/VM_GUIDE.md#23-the-20-minute-ride-split-by-split)).
Without them their rows fail as "missing in this run"; name them with
`--allow 'ride.*' --allow 'set_F_straight.*'` and say so in the pull request.

## The procedure

1. Pre-register the candidate and its acceptance criteria before running it.
2. Run the gate; put its JSON and table in the pull request. A worse metric is either accepted
   explicitly with `--allow` and a stated trade-off, or the change is "tried, not shipped" and
   recorded in `docs/EXPERIMENTS.md`.
3. A change meant to move the numbers commits a new baseline and a new seal
   (`python scripts/detector_freeze.py create --evidence <full gate JSON> --manifest <new seal>`), and the documents that quote numbers are updated from
   `docs/EXPERIMENTS.md`.
4. Safety-relevant changes get an independent review before merging.

The dated history of every accepted and rejected candidate:
[`docs/EXPERIMENTS.md`](https://github.com/pmixay/ReSense/blob/main/docs/EXPERIMENTS.md),
[`docs/DETECTOR_FREEZE.md`](https://github.com/pmixay/ReSense/blob/main/docs/DETECTOR_FREEZE.md).
