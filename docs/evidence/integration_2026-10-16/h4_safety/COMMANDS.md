# H4 commands and execution record

Host working directory:
`C:/Users/alikh/AppData/Local/Temp/opencode/rs-integration-20261016`.
`P` below abbreviates `docs/evidence/integration_2026-10-16/h4_safety`.
External run root is the dedicated H4 scratch `.../resense-integration-h4-safety-20261016/run-001`.

Workers were executed sequentially, awaiting Docker exit 0 before the next:

```text
python P/launch.py replay sealed --mode all
python P/launch.py replay candidate --mode all
python P/launch.py replay candidate --mode dark
python P/launch.py components candidate --mode all
python P/launch.py components sealed --mode all
python P/launch.py replay candidate --mode dark-inherited
python P/launch.py components candidate --mode span
python P/launch.py components candidate --mode beam
python P/launch.py components sealed --mode beam
```

All nine: container/process exit 0, no OOM; see `results/runtime.json` for full
unabbreviated Docker commands and mount modes, and `results/verification.json`
for per-worker completion/wall times. Each command uses the pinned image and
the read-only retained checkout of the named source. Measurements and worker
stdout/stderr are retained under their external output subdirectories.

Final derivation (Windows Python; no detector imported or measured by these):

```text
python P/derive.py C:/Users/alikh/AppData/Local/Temp/opencode/resense-integration-h4-safety-20261016/run-001
python P/analyze.py --root C:/Users/alikh/AppData/Local/Temp/opencode/resense-integration-h4-safety-20261016/run-001 --out P/results
python P/finalize.py --root C:/Users/alikh/AppData/Local/Temp/opencode/resense-integration-h4-safety-20261016/run-001 --out P/results
python P/package.py
git diff --check
```

`derive.py` retained initial erroneous component summary fields and wrote separate
derived summaries. `analyze.py` was rerun as workers completed and comparison
audits were added; it does not replay or tune the detector. `finalize.py` checks
source/native/image identity, read-only mounts, complete worker exits, exact
inherited 9+5 frame sets, ordinary descriptors, promotion object identity, H2 span
boundary and cache oracle. `package.py` normalizes generated compact JSON line
endings and writes hashes; raw external bytes remain hash-indexed unchanged.

Before the local evidence-only commit: inspect status, staged diff and recent log;
stage only P's new evidence. The already committed protocol is unchanged.
