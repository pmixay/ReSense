# Final pinned CI lint, 16 October

**PASS with Ruff 0.15.8**, the version pinned by `.github/workflows/ci.yml`.
The final seven E701 single-line statements in `tests/test_node.py` were expanded;
`FINALIZATION.json` verifies the test AST is identical to the full Linux suite's source.
No production source changed after that suite.

Actual successful check, in a disposable Linux container with a read-only checkout:

```powershell
docker run --rm --network bridge -v 'C:\Users\alikh\AppData\Local\Temp\opencode\rs-p1-start:/workspace:ro' -w /workspace resense:p1-combined-tools-7d3d5a05c258 bash -lc 'python3 -m pip install --quiet --target /tmp/ruff-check ruff==0.15.8 && PYTHONPATH=/tmp/ruff-check python3 -m ruff --version && PYTHONPATH=/tmp/ruff-check python3 -m ruff check --no-cache --exclude docs/evidence/cycle_2026-09-28/complete_timing/default/run_gate.py .'
```

Output: `ruff 0.15.8`, `All checks passed!`; exit **0**. The only excluded archived
runner is the same one excluded by CI. `--no-cache` changes cache writes, not diagnostics.
The dependency download is confined to this lint container; it is separate from the
network-disabled image rebuild and pytest proofs.

An initial invocation without `--no-cache` exited 2 because Ruff tried to create its cache
under the read-only mount. The successful retry changed only that cache option. Host Ruff
0.11.13 separately passes the same diagnostic scope and is recorded by the finalization tool.
