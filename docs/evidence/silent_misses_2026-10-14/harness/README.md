# Harness of the silent-miss rounds (13–15.10)

Scratch scripts of the agent session, committed as `.txt` so the work can be reproduced and
continued elsewhere. They are not part of the detector and not run by CI. They assume the session's
sandbox layout: the repository at `/home/user/ReSense`, a virtualenv at `/tmp/claude-0/venv`, gate
caches (`scripts/cache_frames.py` / `scripts/cache_extended_ride.py` format) in
`/tmp/claude-0/fixdata/cache/<recording>` and node-decoded judge caches
(`docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py`) in `/tmp/claude-0/judge_data/cache/<bag>`.
Edit `env.sh` (or the paths at the top of a script) before running anything.

To run a candidate worktree's detector set **both** `PYTHONPATH=<worktree>` and
`RESENSE_REPO=<worktree>` and check `resense.__file__`: the editable install otherwise imports the
main checkout silently.

| folder | what | used for |
|---|---|---|
| `safety_review/` | the independent safety review of 14.10: `wallbox_rt.py` (the judge's range test with objects anchored per frame to the wall seen in the background, D m proud of it, optionally yawed parallel to the wall or with a non-returning "dark" band: `--o L,W,H:wall+:D`, usage in its docstring), `battery*.sh` / `chain*.sh` (S and B dropout / pitch / dedup / 5 Hz batteries, wall-anchored probes, the dark-band what-if), `hooks.py` (observation-only hooks on the free-top test and the structure cut), `grun.py` (the gate's 8 ride pieces), `jrep.py`, `cmp.py`, `wbsum.py` (summaries) | re-checking the column free-top test and the structure cut against false STOPs (round 3, the BACKLOG review steps) |
| `r3_axis/` | round 3's curve-entry axis work: `axhooks.py` (hooks on `estimate_axis_from_walls`), `cf*.py` / `cflib.py` (offline fits of the wall-vs-axis error), `run_obs.py` / `run_gobs.py` (wall observations per frame), `rt_clear.py` (range test that also records `clear_distance`: silent frames), `wd_*.py` (the wall-drift cap's cost on the gate and ride), `ride_err.py`; data `obs_C.json.gz` (per-frame wall observations on C, frames 0–267) and `B_true_axis.json.gz` (a wall-referenced true axis on B) | card K2 (the axis fix tried on branch `r3/axis-B-trial` and the honest range on `r3/axis`) |
| `investigate_curve/` | `true_axis_all.py`: the wall-referenced true axis on C (error 0.3–0.4 m, checked at frame 120) | the reference for every curve-entry axis measurement |
