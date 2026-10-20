# Candidate B: independent boundary hypotheses (before production edits)

Candidate A is rejected. Full gate: five empty bags 8->10 events /12->14
episodes; ride 27->38 events /30->41 episodes, 126->203 STOP frames. The
source archive and full raw outputs remain under `/tmp/opencode/h1-core`.

Chronological replay of all252 roundT_doubleT frames reproduced **every detection
and warning exactly**. Six new STOP rows occur. At frame236 the last cluster is
not a positive core; earlier core observations removed column history, then the
ordinary vote reported it. Track92 has several successive cores while the fitted
axis moves over its raw Y~-1.2 m structure. These observations rule out accepting
an eroded fitted axis as sufficient independent geometry.

Add current-frame **two-sided boundary hypotheses** before permitting a core:

* From raw points outside |rail-relative dy|1.4 m, up to5 m, in separate
  height bands0.4..1.4 and1.4..2.4 m; the candidate's interior points cannot fit
  these boundaries. Bin along X at2 m, at least4 returns per bin.
* Anchor each boundary's lateral residual at8..28 m (at least4 populated bins),
  independently on both sides and heights. At the object use a window
  +/-max(6 m,16% of distance), at least2 populated bins per profile. Missing any
  profile supplies no proof. No fixed tunnel width or assumed symmetry.
* Each profile proposes the median local-minus-near residual, expanded by the
  maximum observed near/local deviations plus0.10 m. Keep the hull of **all**
  proposals and the original fitted axis, not their average. Supporting core
  voxels must remain inside the eroded polygon at both hull endpoints.

This is a conservative multi-hypothesis consistency guard, not a statistically
calibrated guarantee on true track error. Near-rail anchor errors and common-mode
boundary displacement remain limitations. Physical positive controls, shifted
axis controls and real empty-recording replays decide acceptance.

Keep tracker unchanged in B to isolate geometry. If temporal transfer remains,
register its correction separately with a failing history witness.
