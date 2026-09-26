# Ride false-event scene review

The frozen detector's fresh replay contains **45 false event IDs, 183 alarm frames and 38 STOP
episodes in 11,271 frames**. These reproduce the strict P3d gate. Events are keyed by replay
piece and track ID, exactly as in the gate; identities can restart at a piece boundary.

[inventory.json](inventory.json) records every event's original frame identities, timestamps,
reported distance range, midpoint STOP frame, manual scene label, confidence, reviewer and visual
reason. It also records SHA256 hashes of the eight source JSONL files and eight contact sheets.

| Near-sensor scene appearance | Event IDs |
|---|---:|
| Platform or station | 20 |
| Tunnel | 16 |
| Uncertain | 9 |
| Confidently identified switch or junction | 0 |
| Total | 45 |

**Interpretation.** Labels chiefly describe the sensor's 3–20 m cross-section, with top-down and
angular views for context. Reported false targets lie 20.7–158.3 m ahead, potentially in a
different scene. Actual alarm causes and scene labels at the target locations remain unassigned.
The nine uncertain labels are retained; zero confident switch labels does not establish absence
of switch-related alarms. Scene distances and durations have not been annotated, so there is no
per-scene false-event rate. Event-frame memberships total 217 because multiple event IDs can
share a single alarm frame.

## Visual evidence

Each row shows the midpoint STOP cloud: top-down points below 1.5 m in the fixed sensor vehicle
frame, the full near cross-section, and the angular sensor view. Plotting thins the cloud
deterministically; scoring uses the full cached data. No detector reason code assigns a scene.

- [Events 1–6](contact_01.png), [7–12](contact_02.png), [13–18](contact_03.png), [19–24](contact_04.png): reviewed by the coordinating agent.
- [Events 25–30](contact_05.png), [31–36](contact_06.png), [37–42](contact_07.png), [43–45](contact_08.png): reviewed by P4.

## Reproduce the inventory and views

Use the full gate's eight `new_data_*.jsonl` files and the complete ride cache:

```bash
python scripts/ride_event_scenes.py --run /path/to/gate \
  --cache /path/to/cache/new_data --out /path/to/new-review
```

The command refuses incomplete rides or duplicate frame identities. Its generated scene labels
start as `unreviewed`; the manual review above is preserved in this committed inventory. Two
tests cover event scope, overlapping alarm-frame accounting and duplicate-frame rejection.
