# Focused-run continuation — registered before repeating the affected check

`run-001` reached and passed the independent tracker, paired-labelled selected
components, H2 boundaries, axis/health matrix and full-detector reachability.
It exited 1 at the final runtime AST check: the review adapter expected a method
named `publish_markers`; the actual original and selected method is `make_markers`.
The complete changed-method list was exactly the six reviewed methods, including
`make_markers`. This is an adapter naming error, not a detector failure or a
relaxed behavior assertion. Its traceback, commands and partial JSON remain intact.

Continuation uses the same private Linux volume/checkouts/native build. Change
only that expected method name, repeat the runtime check, then run the previously
unreached focused committed suites, sealed-side components/tracker and paired
comparison. Do not repeat the already passing selected geometry/health work.
Keep new results in `run-002`, with explicit provenance to `run-001`.

`run-002` also exited 1: two patch sections for `probes.py` caused only the
argument-slice edit to survive. The method-name and runtime-only branching edits
were absent, so the same check failed again after the unchanged earlier checks.
No detector result changed. Apply those edits together in one file section and
continue as `run-003`, again repeating only runtime and the unreached work.
