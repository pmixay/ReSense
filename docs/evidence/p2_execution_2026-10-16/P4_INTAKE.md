# P4 handoff intake — 16 October 2026

Fetched `origin/ccr-027997e8-kqywat` at `6d6aaca` after the user delivered P4's
completion notice. Reviewed its evaluation README, export FORMAT, raw archive
instructions and corrected LIMITATIONS. Evidence was inspected in an isolated
snapshot under `/tmp/opencode/p4-handoff-6d6aaca`; no P4 code was merged.

## Independent checks

* `python3 docs/evidence/p4_eval_1.1.0_2026-10-16/export/build_export.py --check`:
  **PASS**, 238 registered cases (X3 120, X1 22, J1 12, G3 84), 2,461 numbers
  (126 derived), zero source mismatches.
* Raw archive SHA-256 against committed `raw/SHA256SUMS`: **PASS**.
* Read archive members and checked both committed raw indexes: **819 indexed
  file references verified**, zero missing entries or hash mismatches.

## P2 disposition

Accept the proposed long-form export v1 as the P2 chart-input basis: source file,
JSON pointer/hash, explicit derived formulas, case register, status, scope and
runtime preserve the required provenance. P2 will adapt its local draft checker
to this supplied format rather than require P4 to adopt the earlier P2 scaffold.
This records P2's technical acceptance, not a dispatched message or P1 approval.

Closed requests: complete current case register, traceable numeric export,
durable existing raw outputs and confirmed limitation/caption guidance.
Unblocked P2 work: source-backed **prerelease draft** X1/range and X3 charts,
complete-case coverage review and caption preparation. Preserve stage/runtime
separation, in-sample labels, misses and unchanged-vs-control outcomes.

Still pending: **release J1 after H6/E1**, final release/image identity and P1
presentation approval. G3 is registered, not run. X3 is measured on the sealed
candidate, not on the final released image; all 40 cases equal the Linux control.
Cloud runtime timings do not close S5. The Set O Windows cache frame 332
discrepancy remains a P1/P3 input investigation. Shared-document caption edits
remain subject to their owners; historical older-detector values must not be
silently relabelled as 1.1.0 measurements.

This intake supersedes the earlier outstanding P4 export/archive requests in
HANDOFFS.md. Final charts/media still require the release-specific acceptance
recorded in ROLE_2_PLAN.md.
