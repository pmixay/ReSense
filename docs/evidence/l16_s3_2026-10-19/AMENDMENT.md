# P3 author amendment: retain the newly supported directional startup — 19.10

The first directional-FOV candidate is REJECTED. On complete actual Falcon
case 4/5 it loses 19 STOP rows vs the correctly oriented control, including
person-period rows 2988–2994, 3003, 3007–3008 and 4382. It also adds 16 rows.
The rejected source patch and all partial/full raw outputs remain in `run2/`.
No aggregate STOP count is accepted in place of matched/frame retention.

Full-state prefix snapshots compare correctly oriented input, automatic side
recovery and an explicit correct side mapping. Voting observations alone do
not reproduce the correct startup model/history. The new prospective candidate
may reconstruct the bounded startup ONLY for a newly recoverable ring-free
directional up-axis contradiction on the first frame. Existing upright/yaw
recoveries and configured mappings keep their exact default-off replay path.

Use the existing <=4-frame / 32-MiB owned buffer and current-stamp-only replay
implementation; do not enable the global `orientation_replay_frames` default.
No replay attempt after a discontinuity or missed budget. The narrow automatic
case must have explicit provenance in its event. Keep normal and supported
eight-family automatic Falcon outputs equal to the same-runtime main control.

Before acceptance require: exact STOP/detection preservation vs correct side
control, loss-free real person period, no extra empty Pandar alarms, unchanged
existing B4 channel behaviour, bounded memory and search, affected tests, fresh
combined full author gate against the completed matched-runtime reference.
The registered 360-degree ring-free Pandar control has only ~94% forward-sign
concentration and supplies no directional cue; it remains an explicit inherited
L16 limitation, as required by the original abstention criterion.

All results remain uncommitted author evidence. Formal X3, independent review
and P1 resealing still require the actual committed candidate.
