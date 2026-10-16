# Integration Docker fixture repair — 16 October 2026

The P4 Docker CI run `38840524998` reported two failures and 1,291 passes: the
image lacked `docs/evidence/judgement_2026-10-13/scripts/probe.py`, needed by the
merged X3 robustness tooling. This evidence records the focused packaging repair.

## Minimal dependency closure

- `probe.py` imports `judge_runner.NodeReplica` / `record` and `range_test.run_frame`.
- `judge_runner.py` imports the installed `resense` package and the existing ROS
  source `resense_ros.fastcloud`; it reads `configs/default.yaml` with
  `RESENSE_REPO=/opt/resense`. Its other imports are Python standard library and NumPy.
- `range_test.py` additionally imports installed `resense.frame` / `resense.track`;
  its range CLI uses the already-pinned SciPy. It does not import the odometry or
  cache-generation scripts.
- `score_objects.py` is a standard-library CLI, executing at module load; regression
  coverage invokes it as a subprocess rather than importing it with fake arguments.
- `judge_geom.py` is a detector-independent NumPy helper, checked on generated rails.
- The existing `labels/doubleT_obstacle.json` is the label-schema/envelope fixture.
  Other label files and recorded clouds are excluded from the Docker context.

All five judge scripts have exact `.dockerignore` exceptions and production `COPY`
sources. The shared-policy backend and small startup fixtures retain their exact
allowlists. The image tests run the real judge import closure and real detector on
generated clouds, proving same-seed repeatability, different dropout seeds, aligned
point attributes, and an unchanged NumPy RNG factory outside the probe. Only the
worker's git-checkout identity function is replaced by installed-runtime metadata
inside this dataset-free test; the image contains no `.git` directory.

## Reproduction

Run the context helper with an explicit frozen commit and fresh output/tag:

```powershell
python docs/evidence/offline_rebuild_2026-10-15/context_check.py --source-ref f8c088d --image resense:integration-fixtures-f8c088d-20261016 --out docs/evidence/integration_docker_fixtures_2026-10-16/run-f8c088d
```

The helper uses `git archive`, overlays only its named owned packaging files, and
reuses the production offline clean uninstall/native recompile/ROS rebuild recipe.
It retains pinned dependencies from `resense:p1-combined-tools-7d3d5a05c258`, whose
installed detector is older than this integration. Build and test networking are
disabled. The old installed/source/fixture trees are removed before copying the
frozen sources. It verifies every core/native/config/ROS source hash, every installed
package source hash, the native binary, Open3D import, and exact fixture/context
inventory. Selected tests run from `/` with the installed package imported first
and `RESENSE_REQUIRE_SYNTHETIC=1` (any skip fails).

The retained logs and `result.json` report focused unit counts. This measurement
does not certify the final integrated image, the full test suite, or ROS runtime
acceptance; those checks belong to the parent after all integration sources freeze.

## Measured result

[`run-f8c088d/result.json`](run-f8c088d/result.json): **PASS**.

| Focused Linux group | Passed | Skipped | Deselected |
| --- | ---: | ---: | ---: |
| Existing X3 robustness battery | 18 | 0 | 0 |
| Docker fixtures, metrics/labels, shared policy, startup harness | 215 | 0 | 0 |
| Native kernels, fastcloud, core synthetic tests | 105 | 0 | 0 |
| **Total** | **338** | **0** | **0** |

- Frozen source: `f8c088dc4f3243fbd15a3aae9be0459e8a0aa941` (combined H1/H2 core).
- Evidence image: `resense:integration-fixtures-f8c088d-20261016`, ID
  `sha256:333863304533e543b875bfc49c52344c1b41d560797bb3152de31a741a630024`.
- Installed import: `/usr/local/lib/python3.10/dist-packages/resense/__init__.py`.
- Native extension enabled; rebuilt binary SHA-256:
  `dc549d0583f92c3acd93c455bf94bab4bbedae35a9580d82ad24786473661d5c`.
- Open3D `0.19.0`; all 46 core/native/config/ROS input files verified by hash.
- All 24 production fixtures match the filtered context and image copies byte for
  byte; their total is 1,363,127 bytes, including pre-existing residual inventory.
  The five added judge scripts total 34,730 bytes in this archived context.
- The retained dependency image's ID is unchanged before/after the check.
- Focused Ruff check of the fixture tests and context helper passed.

No additional packaging or dependency blocker was observed in these focused
checks. Concurrent node/launch/test-node edits are excluded by the frozen archive;
the parent still needs the final full image/CI run once those edits are committed.
