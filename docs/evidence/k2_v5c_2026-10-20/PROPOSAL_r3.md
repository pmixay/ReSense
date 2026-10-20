# K2 v5c: proposal for revision 3 and the decision (20.10, after the data run)

> **For:** P3 (review) and the captain (decision) · **From:** P4 · **Status:** proposal. Everything here was written
> **after** the measurement of §6 of [`README.md`](README.md); it cannot change those registered results, only inform
> the decision. No detector change is proposed or made by P4 (detector changes are P3's). Every switch stays off.

## 1. Where v5c-15 stands

| row (revision 2) | result | what is behind it |
|---|---|---|
| G-1 gate | pass | ride STOP episodes 24 → 10, five empty and squareT_platform 11 → 0; only set O `small_center` (accepted exception) |
| ID | pass | switches off = parent, gate and Falcon, every row |
| K1-2 | reported | 0 / 259 (K2 off 90 / 259, 65 of them on a static structure per the package) |
| F-1 | fail as scored | the scorer's definition, §2 |
| M-1 | fail | the tunnels cube: an edge object that K2-off's axis error carries into its gauge, §3 |
| G-2 (X3) | same 6 failures as B, one passing comparison worse by one episode | edge sensitivity of 5–9 cm, §4 |

v5c-30 is not proposed: it adds a loss on a marked object (platform cube 23, 38 → 31 STOP frames, first STOP
86.8 → 76.4 m) and gains only the person's first 8 STOP frames at 127 m.

## 2. F-1: score the person by where it is (proposed for registration)

`score_falcon_pos.py` counts a candidate STOP only in the frames where K2 off STOPs; a STOP on the person in any other
frame is "new", and the first person STOP is the first such shared frame. [`scripts/score_falcon_person.py`](scripts/score_falcon_person.py)
follows the person instead: its position per frame from K2 off's STOP detections (continuity; a 2–4 m merge with
structure keeps its length), its warnings in between, and the fitted line before the first and after the last STOP.

| run (`main` `8c2bf51`; B: committed `c9e8daa`) | first person STOP | person STOP frames | STOP frames not on the person |
|---|---|---|---|
| K2 off (positive control) | 124.84 m (frame 2972) | 1,360 | 4: 159, 2312–2314 (the attributed false STOPs) |
| variant B | 122.27 m (2994) | 1,330 | 2: 4410–4411 |
| **v5c-15** | **124.02 m (2979)** | **1,366** | 2: 4410–4411 |
| v5c-30 | 127.18 m (2950) | 1,374 | 2: 4410–4411 |

Checks: K2 off scores itself exactly as the registered scorer defines its reference (1,360 frames, 124.84 m, only the
4 false STOPs left over). Every leftover frame of the first versions of the script was looked at and was the person
(3033–3039 and 3135: K2 off's cluster is a 2–4 m merge whose near face is ~2.4 m before the person, v5c STOPs on the
person itself, 0.8 m wide; 4280–4320: a second STOP object at 8.8–11.5 m in the same frames; 4373–4379: the person at
6.4–6.7 m, Y 0.1–0.2 m, where K2 off has dropped to CAUTION). So the "9 new near STOP frames" of README §1 are 7 frames
on the person and **2 not attributed** (4410–4411, 3.0 m, after the person's last position at 5.7 m; every K2 variant).

Proposed F-1 for revision 3: first person STOP ≥ 124.0 m by position; person STOP frames ≥ K2 off's; no STOP frame off
the person beyond K2 off's 4 and variant B's 2. v5c-15 passes it, but by **0.02 m** on the first criterion, less than one
frame of the person's approach (~0.12 m per frame): it STOPs 7 frames (0.82 m) after K2 off. The 124.0 m threshold was
set before this reading existed; the margin should not be read as more than a tie with the threshold.

## 3. M-1: the tunnels cube is an edge object (decision needed)

Measured against the rails ([`README.md`](README.md) §7), the cube is 0.05–0.08 m inside the strict envelope, and over the
lost frames K2 off's axis is displaced towards it by a median 0.21 m, B's by 0.11 m. K2 off's STOPs at 30–55 m rest on
its axis error. No rule restores them without trusting the more displaced axis; the OR-of-gauges rule would also bring
back the ride's strict detections at 30–60 m that the gate counts as false (whose true axis could not be measured).
**Proposed:** the captain treats M-1's tunnels row as explained (not a K2 regression), and future marker rows report
an object's margin to the strict edge measured from the rails beside its gate result.

## 4. X3: the crossing person entering at the gauge edge (open, not K2-specific in kind)

The person-crossing rows lost under +2° roll, 30 % dropout and dedup are frames 8–12 of `doubleT_obstacle`, the person
walking into the gauge from the left at 55.5 m. Replays of X3's own probe with a read-only dump
([`scripts/edge_probe_dump.py`](scripts/edge_probe_dump.py); records equal X3's raw records, 60 rows × 4 cases, every
field but timing / latency): B's axis at 55.5 m is **0.05–0.09 m** right of K2 off's, the person's cluster centre
4–8 cm farther from it; K2 off's cluster is `gauge` from frame 9 under the roll, B's stays `warning` until 12 and STOPs
from 13. Without the roll both STOP from frame 8 (61 / 61 rows). The rails resolve only to ~25–35 m in these frames, so
which axis is right at 55.5 m cannot be measured; the difference is below what the data resolve. Set O `small_center`
(the gate's accepted exception) is the other X3 failure.
**Proposed for P3 (outside K2):** look at how many frames an entering edge track needs to turn from `warning` to
`gauge`: a 5 cm axis difference costs four frames here.

## 5. If the captain wants K2 on

Candidate: v5c-15. For: the ride's false STOP episodes 24 → 10 and the empty recordings 11 → 0 (G-1), the person kept
(§2, as proposed). Against: the tunnels cube 55 m → 27.6 m (explained in §3, still a later STOP on a marked object),
the standing person at 150 m 90 → 0 (65 of K2 off's 90 on a structure), X3's edge-entry delay (§4), set O
`small_center` 55.8 → 52.5 m. Before any default change: P3's or a fresh agent's review of this proposal and of the
§2 scorer, the captain's decision, and P3's own sealing.
