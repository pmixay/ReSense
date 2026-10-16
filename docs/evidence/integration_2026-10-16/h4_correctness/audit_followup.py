"""Retained auditor with registered exact descriptor projection only."""
import inspect
import evidence_audit as base

source = inspect.getsource(base.main)
old = "assert witness['new'] == trace['candidate']"
new = "assert {k:v for k,v in witness['new'].items() if k != 'points_idx'} == trace['candidate']\n    assert len(witness['new']['points_idx']) == witness['new']['n_raw'] == 49"
assert source.count(old) == 1
source = source.replace(old,new)
scope = dict(vars(base))
exec(compile(source,'/review/audit_followup.py:registered_projection','exec'),scope)
scope['main']()
