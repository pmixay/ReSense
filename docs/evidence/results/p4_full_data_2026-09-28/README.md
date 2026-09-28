# P4 full-data evidence packet — 28 September 2026

This packet records the complete replay of the frozen 27.09 detector at commit
`43a0e7d9dc6a8683b1656de7b9d9c9cf601a58f1` and a final detector/config gate replay at evidence
commit `1ee45726e9c21523cdeeff31426b60ab272c4cfd`. The effective config is `configs/default.yaml`
with SHA-256 `de5c7fd6dfa74c1e656af6e233efd625e3e552736534e32efa625e5e8ff57f47`; native kernels
were loaded. The reference and final replays took 614.0 s and 618.5 s on the one-CPU-limited Linux
VM. All data caches remain outside Git. `artifact_manifest.json` gives byte lengths and SHA-256
hashes for every file in this packet.

## Results

The full strict regression gate passed against
[`regression_baseline_2026-09-27_quality.json`](../regression_baseline_2026-09-27_quality.json):
**208 enforced metrics were unchanged**, with no missing, worse, better or waived rows. Sixteen
informational latency values changed with the VM workload. The ride portion has 130 alarm frames,
32 track-ID events and 31 STOP episodes over 11,271 frames. Five obstacle-free recordings have 40
alarm frames, 11 events and 13 episodes over 229.776 recorded seconds. Track events, STOP episodes
and alarm frames are distinct measures.

The final detector/config replay also passed the same strict gate: **208 enforced metrics were
unchanged**, with no missing, worse, better or waived rows. Sixteen latency rows changed and remain
informational. The final raw JSON is [`final_regression_gate.json`](final_regression_gate.json);
the original [`regression_gate.json`](regression_gate.json) preserves the frozen-reference run.

Set O has STOP on 8/8 in-envelope objects and 411/801 visible object-frames. The six false STOP
frames match the labelled outside object `big_outside` (track 202, frames 563–568, 132.68–142.35 m);
there are no background STOPs. The clear-distance scorer reports 19/505 target-envelope overclaims,
154/801 intent overclaims and 123 GO-judge frames. The empty suffix, frames 804–1509, has no STOP;
it was previously inspected and is not unseen validation.

| Check | Result |
|---|---|
| Set O #4 `small_edge_inside` | 18/83 STOP frames; first STOP 35.0 m; held from 38.7 m |
| Set O #6 `big_edge_inside` | 7/125; first STOP 18.3 m; held from 10.3 m |
| Set O #8 `big_above` | 56/124; first STOP 111.4 m; held from 123.6 m |
| Startup census, 40 frames per start | 17/221 ride splits with STOP; 115 STOP frames, 33 events, 28 episodes; 0 starts within 10 m |
| Five empty bags, recorded rate | 11 events / 13 episodes |
| Five empty bags, 5 Hz | 8 / 9 |
| Five empty bags, +3° roll | 10 / 11 |
| Five empty bags, +3° pitch | 11 / 12 |
| Empty-bag starts at offsets 0/10/20/30/40 | events / episodes: 11/13, 10/11, 11/11, 6/6, 5/7 |
| Set F straight, paired legacy → anchored | person 149.9→154.1 m; 1 m box 116.1→109.9 m; 0.5 m box 1/5→2/5; trolley 148.1→148.1 m; cable 103.9→101.7 m |
| Set F curve/edge, six paired approaches per kind | no 100–150 m hits; median first person 75.2→69.6 m and 1 m box 75.3→81.3 m |
| Set S, 108 paired placements | bed 22/67 visible in-gauge matches; legacy 31/68; 22 hit in both, 9 legacy-only, 0 bed-only |

Set F placement and Set S bed/legacy comparisons use identical recorded backgrounds and paired
synthetic samples. Anchoring is not surveyed ground truth; the ride has no real obstacles. These
checks measure reproducibility and sensitivity, not real long-range recall.

## Candidate decisions and false alarms

Registered candidates A, B and C were each evaluated independently on all 1,510 set O frames.
For each candidate, every per-frame detector, decision, warning, track, health and clear-distance
field matched the frozen gate output; only wall-clock timing, the timing-only health value and the
cache filename suffix were normalized. Each target metric and every false-STOP / clear-distance
metric stayed unchanged. All were rejected at the registered stage-1 target check, so later gates
were not run. The full protocol and decisions are included in this packet. The frozen detector is
retained; this run claims no score gain.

The false-alarm inventory lists each current empty-bag and ride event by recording piece, track ID,
frame intervals, range and detector-reported zone/reason/kind. All 32 current ride midpoint clouds
were reviewed in the contact sheets. Tunnel and trackside structures are visible, but event causes
remain **uncertain** because the event clusters lack independent labels and were not traced to exact
point support. Repeated hits in an event are correlated observations. Set O's six false STOP
frames are attributed to the outside organizer object by its labels.

At the time this P4 packet was published, the latest paired score was **66.5/100** on `806b6c4`.
The P4 carry-forward assigned zero detector points because the detector and all 208 gated values
were unchanged. A later single-review model assessment of `a2f9122` assigns **69/100**, crediting
newer launch and evidence work; it does not claim a P4 detector gain. See the current
[scorecard](../../../SCORECARD.md) for the distinction between the single-review estimate and the
historical paired score.

## Reproduction commands

Run from the repository root with `/tmp/resense-p4-venv` (or an equivalent environment with the
project's pinned packages, Open3D and native kernels) and verified caches in `/data/cache`.

```bash
python scripts/regression_gate.py \
  --cache /data/cache --jobs 1 --chunks 8 \
  --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json \
  --work out/p4/reference/gate --out out/p4/reference/gate.json

python scripts/regression_gate.py \
  --cache /data/cache --jobs 1 --chunks 8 \
  --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json \
  --work out/p4/final_gate --out out/p4/final_gate.json

python scripts/score_fake_objects.py out/p4/reference/gate/cloud_with_fake_obj.jsonl \
  --gt labels/cloud_with_fake_obj.json --out out/p4/reference/seto_score.json
python scripts/score_clear_distance.py out/p4/reference/gate/cloud_with_fake_obj.jsonl \
  --gt labels/cloud_with_fake_obj.json --out out/p4/reference/seto_clear_distance.json
python scripts/startup_census.py --cache /data/cache --frames 40 --chunks 8 --jobs 1 \
  --rows out/p4/reference/startup.jsonl --out out/p4/reference/startup.json
python scripts/robustness_check.py --cache /data/cache --every 1 --mount as_recorded \
  --jobs 1 --out out/p4/reference/robustness_as_recorded
python scripts/robustness_check.py --cache /data/cache --every 2 --mount as_recorded \
  --jobs 1 --out out/p4/reference/robustness_5hz
python scripts/robustness_check.py --cache /data/cache --every 1 --mount roll_3 \
  --jobs 1 --out out/p4/reference/robustness_roll_3
python scripts/robustness_check.py --cache /data/cache --every 1 --mount pitch_3 \
  --jobs 1 --out out/p4/reference/robustness_pitch_3
python scripts/start_offsets.py --cache /data/cache --starts 0,10,20,30,40 --jobs 1 \
  --json out/p4/reference/start_offsets.json
```

The candidate screen command shape is:

```bash
python scripts/eval_real.py --cache /data/cache --bags cloud_with_fake_obj --jobs 1 \
  --set tracking.near_escalate_distance=40 --out out/p4/candidate_A
python scripts/eval_real.py --cache /data/cache --bags cloud_with_fake_obj --jobs 1 \
  --set tracking.near_escalate_voxels=8 --out out/p4/candidate_B
python scripts/eval_real.py --cache /data/cache --bags cloud_with_fake_obj --jobs 1 \
  --set cluster.wall_keep_gauge_voxels=8 --out out/p4/candidate_C
```

Set F commands use the `far_range_eval.py` settings embedded in the paired JSON: straight files
`46,68,98,140,168,172`, start 220 m, 110 frames, kinds person/box0.5/box1.0/trolley/cable,
lateral −0.6:0.6, seed 0; curve/edge files `127,129,131,160,164,175,177`, start 160 m, 220
frames, kinds person/box1.0, lateral −1:1, seed 0. Run both `--placement-mode legacy` and
`--placement-mode anchored`, then compare with `scripts/compare_setf.py`. Set S uses backgrounds
`roundT_doubleT`, `roundT_pressureGate_roundT`, `roundT_squareT_pressureGate_squareT`; every 10th
frame; person, box0.5, box1.0, plank and trolley; 10–250 m; one object per frame; negative
fraction 0.2; seed 1. The paired GT files and per-frame outputs are retained under
`raw/setS/`.

Raw per-frame gate and stress JSONL, Set F outputs, Set S GT and detector outputs, current false
alarm contact sheets, candidate effective configs, and the run summaries are retained here. The
large injected `.npz` frames and all organizer cache data remain in local ignored storage and can
be regenerated from the stated seeds, labels and verified backgrounds.
