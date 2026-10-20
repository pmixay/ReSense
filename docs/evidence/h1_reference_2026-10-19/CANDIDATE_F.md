# Candidate F screening: actual spatial boundary support

The complete D core trace shows that far A-axis misses at116..157 m have
current tall object returns but zero/one accepted local wall bins. Requiring
two different heights inside each2 m bin rejects a real wall sampled by only
one vertical channel at a station. Duplicate echoes cannot invent a distinct
along-track station, so raw return count is the wrong support unit here.

Screen a frame-local wall profile with one or more returns per station. Use
the median actual X, not the nominal bin centre, and require four near stations
spanning at least6 m and two local stations spanning at least1 m per each of
the four side/height profiles. Keep the maximum observed profile spread,0.10 m
padding, absolute fresh rail anchor and original fitted-axis hypothesis.

The one-metre local span rejects a single beam/noisy duplicate split over two
adjacent bins. This is a support correction, not a calibrated real-axis bound.
No tracker confirmation/continuation change is part of this screen.

Evaluate in a separate P3 worktree while E runs, preserving E source bytes.
Retain only if previous matched sets and physical/outside controls pass, then
freeze and run full gate/X3. Keep any failure; E remains the comparison point.
