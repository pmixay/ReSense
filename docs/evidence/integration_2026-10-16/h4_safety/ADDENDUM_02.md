# Follow-up registration after initial measurements, before follow-up measurement

Initial outputs are retained under external `run-001`; none are overwritten.

1. The independent addendum-01 dark mask measured 23 / 12 STOP frames on ride
   pieces 1 / 3 versus plain sealed 14 / 2. This is 9 / 10 excess, not the inherited
   9 / 5. Inspection **after** this measurement of the H1-only archived observer
   (`column_hardening_2026-10-15/scripts/hooks.py.txt`, lines 54–68) shows that its
   mask uses azimuth padding 0.02 degrees and range tolerance max(0.5 m, 2%)
   **plus 0.5 m**, rather than the independently specified 0.12 degrees / no extra
   range margin. Register a separate `dark-inherited` replay of both complete
   pieces with those exact published boundaries, implemented independently.
   It will compare against the already measured plain controls. No other input,
   configuration, seed or source changes. Keep both mask experiments in the report.
2. Initial direct span fixtures returned no part even at 0.101 degrees: their
   x=111 m face did not clear the lateral-residual bar over enough height. They
   therefore cannot establish the horizontal-support boundary. Register a separate
   `span` fixture at x=93 m (same smooth surface, heights, angles, echoes, voxel
   settings) where its entire vertical face is >1.3 m in front of the surface.
   Report actual float32 span and all results, including the initial inconclusive
   fixture. This fixes the probe geometry, without changing any production bar or
   assertion. No physical ray-scene conclusion follows from this direct extractor.
