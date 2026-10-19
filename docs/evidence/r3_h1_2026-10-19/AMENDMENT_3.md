# Current-frame support correction, before revision3

Full gate and X3 on `1f93141` pass; all former matched STOP rows are retained.
Source inspection found a coverage gap: an ordinary corridor cluster can contain
ego-compensated historical points, even when it is not marked `weak` or `thin`.
Its n/n_gauge and size then do not prove current-frame vertical support. The
first implementation's docstring was too strong for that case.

Revision3 requires `n_raw == len(points_idx)` for the shortcut. `_corridor_cluster`
sets n_raw to the entire described raw blob and points_idx to its current-frame
indices only; the existing smear fallback re-describes a blob from current
points and legitimately passes. `find_hanging` is always current-frame. No new
cluster metadata or historical evidence is invented. Add accumulated-cluster
negative controls before the production edit, then repeat committed-source
candidate gate/X3; retain all v2 evidence under its actual source identity.
