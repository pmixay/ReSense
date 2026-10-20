# Ported copy: markdown records only (20.10 evening, P1)

This directory is the **markdown part** of P2's/P3's K1/K2 author-repair record, copied from branch
`fix/k1-k2-repair-20261020` at commit `4d218ed` (https://github.com/pmixay/ReSense/tree/4d218ed/docs/evidence/k1_k2_repair_2026-10-20).

* **Not here:** the raw outputs (about 29 MB: traces, replays, `*.tar.xz`, audits, scripts) and the detector code and tests of the repairs
  (`resense/clustering.py`, `config.py`, `detector.py`, `egomotion.py`, `track.py`, `tests/test_k1_*`, `tests/test_k2_*`). Links in these files to
  those files are dead in this tree; follow the commit link above. The branch is kept for that reason.
* **Why not merged:** the repairs change seven frozen detector files (the seal fails), they are not accepted (their own record: enablement NO-GO),
  and they have no full strict gate on a final source and no independent review. K1/K2 stay off in 1.2.0 ([`BACKLOG.md`](../../BACKLOG.md), [`DECISIONS.md`](../../DECISIONS.md) row 48).
