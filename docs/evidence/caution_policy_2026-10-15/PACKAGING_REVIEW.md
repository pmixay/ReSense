# C1 independent-review fixes: packaging and observer imports

Review follow-up on the combined `p1/start-2026-10-15` worktree, starting at
`4e4d5a9`. Both reported C1 import findings are fixed. Policy semantics/defaults
are unchanged: v1 is default, and the measured v2 acceptance failures in
`EVIDENCE.md` remain failures.

## Installed backend dependency

`webapp/backend/pyproject.toml` now declares `resense-ros>=1.0.0`. This is the
existing distribution built from `ros2_ws/src/resense_ros`, not another copy of
the policy. Its package initializer / pure policy do not require ROS; no change
to the ROS setup, root packaging, detector seal, node or launch was needed.

`scripts/run_webapp.sh --install` and the CI webapp install step provide root,
ROS Python package and backend in the same pip invocation. The launcher checks
the actual pure policy import. Local wheel commands and the older same-version
overlay reinstall case are documented in `webapp/backend/README.md`.

`scripts/check_webapp_wheels.py` is a repeatable CI check:

1. Copy the three build projects to temporary build directories; build actual
   wheels without editing the checkout or installing into a shared environment.
2. Inspect backend wheel METADATA for its ROS Python dependency.
3. Create a fresh non-editable venv and install the root/backend wheel paths.
   **Do not explicitly install the ROS wheel**: pip must resolve it from the
   supplied wheelhouse using the backend's dependency declaration.
4. `pip check`; run an isolated `python -I` outside the repository. Assert the
   source `ros2_ws` namespace and `rclpy` / `launch` / `launch_ros` are unavailable,
   and install an import blocker for ROS / `resense_ros.detector_node`.
5. Import the real backend application, create it, check decision precedence /
   v2 opt-in and backend/shared-callable identity, and run the installed CLI help.
   All three package origins must be inside the new venv's site-packages.

**PASS** on Linux Python 3.10.22, with `resense==1.0.0`,
`resense-ros==1.0.0`, `resense-web==0.1.0`. The actual wheel hashes, dependency
metadata and import origins are saved in `wheel_import_review.json`. These are
verification-build artifacts from the combined working tree, not release/seal
artifacts. The temporary wheel venv and container were removed after the check.

## Source observer imports / historical detector checkouts

`scripts/decision_policy_import.py` resolves the observer checkout's policy by
absolute source path. It reuses a normally imported module only when its file
resolves to that exact path; otherwise it loads the file under a private,
path-keyed name. It never replaces an already imported node's canonical module
or class. A missing source file uses the installed distribution.

The four original script consumers and rescorer use this helper. The backend
uses its declared installed policy first, with an explicit source fallback when
running from a checkout with an absent / old ROS overlay. The synthetic observer
keeps `DETECTOR_ROOT` first for **detector** imports and source hashes; the policy
comes from **ROOT** independently. Its source identity now also records the
observer policy's path, version and hash, outside the detector file hash set.

New regression cases in `tests/test_decision_policy.py` cover:

- Different observer/detector roots, both with historical regular ROS packages,
  and an installed older overlay missing the policy submodule.
- A conflicting detector-local policy that must never execute.
- An already imported older node policy whose class and behavior must survive
  observer import unchanged.
- A regular `ros2_ws` package shadowing the old namespace fallback, across all
  other source consumers and the backend.
- Real installed-module versus source-observer origin expectations.

## Linux targeted suite: no Windows exclusions

**148 passed, 0 skipped, 0 deselected**, final run 15.74 s. Executed outside the
checkout (`/tmp`), with the combined worktree mounted read-only at `/src`, in an
ephemeral `python:3.10-slim` container, image digest
`sha256:6ff506466f8b1e981719b468cc0023b8ef000b983cdec0eafe119d01f379e31d`.
The dependency environment was container-local; the real-wheel check used a
separate fresh venv without system site-packages. No shared venv was modified.

Source-test dependencies: git, pytest, numpy 1.26.4, scipy 1.13.1,
scikit-learn 1.5.2, pyyaml, fastapi, uvicorn[standard], python-multipart,
rosbags and httpx. BLAS/OpenMP/MKL/numexpr threads were set to 1.

```bash
PYTHONPATH=/src:/src/ros2_ws/src/resense_ros:/src/webapp/backend \
RESENSE_REPO=/src python -m pytest -q -rs -p no:cacheprovider \
  --basetemp /tmp/c1-tests \
  /src/tests/test_decision_policy.py /src/tests/test_rescore_decisions.py \
  /src/tests/test_quality_acceptance.py /src/tests/test_synthetic_sensitivity.py \
  /src/tests/test_synthetic_import_layout.py /src/tests/test_thin_monitoring.py \
  /src/webapp/backend/tests/test_pure.py /src/webapp/backend/tests/test_evaluation.py
```

This includes all three tests previously deselected on Windows: source identity
path formatting, backend cloud reads and results paging. They pass on Linux.
The first slim-container attempt lacked git for existing provenance tests:
145 passed / 3 failed. Installing that test dependency resolved those failures;
none was excluded or changed to pass. The targeted Windows import/policy suite
also passed (59 tests) before the final import-identity refinement.

Ruff on changed Python files: **PASS**. Owned-path diff checks: **PASS**.
Launcher `bash -n` on LF-normalized Git content: **PASS** (the Windows bind-mounted
working file has CRLF line endings, which Bash cannot parse directly).

## E2 fixture handoff and remaining acceptance

Dataset-free image tests need these pure backend source fixtures:

- `webapp/backend/resense_web/__init__.py`
- `webapp/backend/resense_web/decision.py`

They also need the new `scripts/decision_policy_import.py` (covered by the
existing full scripts copy), plus the existing ROS package initializer and
`decision_policy.py` source files. The wheel check belongs to CI's webapp job
with the complete checkout; it is not invoked by the image's unit-test suite.
E2 owns the Dockerfile / ignore-list fixture integration.

Both C1 review findings are resolved by the isolated checks above. Final v2
acceptance still requires the final-1.1.0 judge-path CAUTION/retention targets and
captain acceptance; the previous 30.46% CAUTION / alert-loss measurements were
not tuned or rerun. The full integrated CI / Docker acceptance remains the
parent's integration check.
