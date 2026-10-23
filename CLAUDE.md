# Working rules for Claude in this repository

ReSense is a ROS 2 Humble node (CPU only, shipped as a Docker image) that reads LiDAR point clouds
and tells a driverless metro train whether anything is inside its 2.1 x 3.0 m clearance gauge
(`/resense/decision`: GO / CAUTION / STOP / FAULT, plus `/resense/nearest_distance`). Case 05 of
LCT 2026, team "Molotok". This file holds only rules that stay true. Current version, release state,
open work and results change daily; they live in the documents named under "Where things are".

## Where things are

| Need | Look at |
|---|---|
| What the project is, the jury command path | `README.md`, `docs/ARCHITECTURE.md` |
| Index of every document, status conventions, glossary | `docs/README.md` |
| How the detector decides | `docs/ALGORITHM.md`; parameters in `configs/default.yaml` |
| Current plan, open cards, priorities | `docs/BACKLOG.md` ("Current plan"), `docs/DECISIONS.md` |
| Results (the one place for numbers) | `docs/EXPERIMENTS.md`, independent score in `docs/SCORECARD.md` |
| Seal, gate, how a detector change is accepted | `docs/DETECTOR_FREEZE.md`, `docs/CAPTAIN.md` §6 |
| Who owns which file, contracts (topics, status JSON) | `docs/CAPTAIN.md` §7, §8 |
| Data, recordings, caches, labels | `docs/DATASET.md`, `docs/VM_GUIDE.md` |
| Raw run records (dated, never rewritten) | `docs/evidence/` (index: `docs/evidence/README.md`) |
| Deploying the web prototype | `AGENTS.md`, `deploy/README.md` |

Code: `resense/` (library, no ROS dependency), `ros2_ws/src/resense_ros/` (node, launch, RViz),
`native/` (optional C++ kernels), `configs/`, `docker/`, `scripts/` (index: `scripts/README.md`),
`tests/` (pytest on a ray-cast synthetic tunnel, no dataset needed), `web/` (dashboard),
`webapp/` (jury web prototype: FastAPI + React), `gitbook/` (user guide, Russian).
The version is in `pyproject.toml` and must match the other three declarations (see `scripts/release_meta.py`).

## Working in the repo

* **The detector is sealed.** `resense/`, `native/`, `configs/`, `ros2_ws/src/resense_ros/config/detector.yaml`,
  `setup.py`, `pyproject.toml` and `scripts/build_native.sh` are hashed by the manifest named in
  `DEFAULT_MANIFEST` of `scripts/detector_freeze.py`. Do not edit them unless the task is a detector
  change; that goes on its own branch through the process in `docs/DETECTOR_FREEZE.md` (protocol first,
  full `scripts/regression_gate.py` against the registered baseline with exit 0 and no `--allow`,
  independent review, reseal by the captain). The ROS node code is outside the seal but is P1's.
* **Checks before a commit** (what CI runs; see `.github/workflows/ci.yml`):
  `python3 scripts/detector_freeze.py verify` (stdlib only, integrity), `./scripts/sync_params.sh --check`
  (ROS copy of the parameters equals `configs/default.yaml`; run without `--check` to sync),
  `python -m pytest -rs -q` after `pip install -e ".[dev]"`, and `ruff check .` (CI pins the version
  through `scripts/check_archived_lint.py --lint`). In CI no test may be skipped; tests needing the
  recorded cache carry `@pytest.mark.realdata(path)` and are deselected, not skipped, where it is absent.
  Web changes also have `webapp/backend` pytest, `webapp/frontend` `npm test && npm run build`,
  `web/demo` and `webapp/e2e`.
* **Documents.** Every team document starts with the header block of `docs/README.md` §4 (purpose,
  audience, owner, language, last verified, status); update "last verified" only for what you actually
  re-checked. One fact, one place: numbers go in `docs/EXPERIMENTS.md` and the README summary, other
  documents link to them. Every number carries its kind (real / synthetic), in-sample or out-of-sample,
  and the path of its evidence. Dated evidence and archive files are records: a new run gets a new
  file or folder, old ones are not edited. Write in the language the file's header names (most
  documents, `gitbook/` and the evidence READMEs are Russian; `CHANGELOG.md`, `BACKLOG.md`,
  `CAPTAIN.md` and code comments are English).
* **Contracts** (`docs/CAPTAIN.md` §7: the 12 `/resense/*` topics, the status JSON, `Frame`,
  `configs/default.yaml`): add, never rename or remove. Mark such a PR `[contract]`.
* **Interface work** is desktop only, 1280 px minimum width; no narrow-screen layouts. After a
  requested application change, deploy and verify as `AGENTS.md` says.
* **Roles** are named P1 captain/ROS/Docker/CI/docs, P2 frontend, P3 detector, P4 data/evaluation.
  Do not edit another lane's files without need; ownership is `docs/CAPTAIN.md` §8. `main` changes
  only through a PR with CI green and a review, merged by the captain; do not open one unless asked.

## Evaluation and evidence runs

* Evaluation and judging runs (P4, J1, X-series) never modify detector code (`resense/`, `native/`,
  `configs/`, the ROS package); detector changes are P3's, made and sealed separately.
* Nobody runs or tunes on the held-out G3 set except the fresh agent of the final check.
* Set `RESENSE_REPO=<checkout> PYTHONPATH=<checkout>` to the checkout being evaluated, and
  `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`. Print `resense.__file__` once: with an editable
  install, a worktree silently imports the main checkout otherwise.
* Compare against the baseline of the current seal, not against numbers remembered from a document.

## Verify results, do not trust your own scripts

A number, label or "found nothing" printed by a script you just wrote is a claim, not a result.
Before reporting it, or building on it, check it:

1. **Against an independent source.** Re-derive the key result another way: from the raw points
   instead of your transform, with a second method (for example odometry from ICP vs. object
   steps), or against a case with a known answer. Example: intensity-1 "marker" labels looked
   plausible, but checked against an exact reference they found 57 % of the objects and made
   about 12 false objects per frame.
2. **With a positive control for every negative result.** "0 matches", "no dust" or "no
   difference" counts only after the same tool, on a case where the answer is known to be
   non-zero, finds it. Example: the source-frame search was trusted only after it matched
   252/252 frames of a known bag.
3. **Every label, not just its presence.** When rows get a cause or category, confirm the
   label from the full state (snapshots) on all rows, or on a stated sample per category.
   Record which branch or rule actually fired (trace it) rather than reconstructing it afterwards.
4. **By looking at the data.** Print or plot a few raw examples (`frame_*.png`, a few rows)
   and check that they show what the numbers say.
5. **For physical plausibility.** Speeds, sizes, distances and counts must make sense
   (a train does not move 3 m in 0.1 s; a person is about 1.7 m tall). An implausible value
   is a finding about the data or a bug in the script; find out which.
6. **Instrumentation must not change results.** A traced or hooked run must equal a plain
   run (every field except wall-clock timing) before its attribution is used.

When you report, say what was checked, how (method, how many rows or frames), and what failed
or was corrected. Anything not checked is reported as unverified.

## Practical traps in this container

* `pkill -f` / `pgrep -f` with a pattern that also appears in your own shell command matches
  that shell (exit 144, or a wait loop that never ends), including a pattern that only shows up
  later in the same compound command. Instead:
  * start the job with `cmd & echo $! > job.pid` and later `kill "$(cat job.pid)"`; or
  * look it up with a bracketed pattern, `ps -eo pid,etime,cmd | grep '[v]env/bin/pip'`, then
    `kill <pid>`; the bare text must appear nowhere else on that command line.
  Afterwards check the process is gone, after a second: `sleep 1; ps -p <pid>`.
* Background commands are killed at their `timeout`; give long jobs an explicit long timeout
  and write their output to a log file.
* The container has no recorded data (`/data/cache`) and may lack the Python dependencies; install
  with `pip install -e ".[dev]"` before running tests, and report data-dependent checks as not run.
