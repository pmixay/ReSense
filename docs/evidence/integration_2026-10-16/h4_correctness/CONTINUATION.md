# Continuation registration — before independent probes

The adopted `resense-h4-correctness-20261016-01` exited 0 at
2026-10-16T08:13:05Z. `run-001` completed all 22 registered test files:
572 passed, no skips. It was not cancelled. Its scripts and outputs are preserved.

Continue using its existing `/work/target` and `/work/control` volume, without
cloning or rebuilding again. A continuation container uses `--volumes-from` the
exited original container, the same immutable image and one-thread environment.
The original container, volume and evidence remain retained.

`independent_checks.py` implements the already registered checks: explicit
boundary tables, an independent health min-property matrix, actual Track spare /
vote / clear-cap truth tables, exact cached-window comparisons and lifecycle
instrumentation, strict v1/node projection, baseline AST comparison, and new
deterministic matched straight/constant/transition scenes. Scene families use
both signs, unequal wall offsets/reaches, and a dense near box on/off; eight
successive frames per scene. No production test helper generates these scenes.
Only the other added mechanisms (free-top, surface-cut, spare requirement) are
disabled for the isolated control differential. Target axis on/off is also
compared independently. Raw arrays are hashed with dtype/shape; other values
are compared exactly, with only timing and additive metadata/ranges separated.

`evidence_audit.py` authenticates packaged H3 files, relevant external files and
copy/normalization mappings; reads retained raw H3 results and the candidate
promotion trace; independently recomputes cap/count properties. No gate,
held-out protocol or held-out data is executed/read. The external evidence mount
is read-only; the original point-cloud cache is not mounted.

Each subprocess writes a separate new output; failures remain retained and
must be investigated against the registered geometry before classification.
Source inventories are checked again after all probes. Exact launch argv,
container identity and original-container adoption are saved by the host runner.

Launch attempt `-02` failed before any Python probe: the tools image's default
entrypoint treated the Python pathname as a shell script. No `run-002` was
created. Preserve the container and launch records. Retry `-03` explicitly sets
`--entrypoint python3`; all source, volume, probe and oracle choices are unchanged.
