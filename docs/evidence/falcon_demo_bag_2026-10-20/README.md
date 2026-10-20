# Short Falcon demo bag with the walking person (pitch 23.10) — built and checked 20.10

> **For:** the captain (P1), P2, P4 · **From:** an agent session of 20.10, work-list item "Short Falcon demo bag with the person"
> ([`BACKLOG`](../../BACKLOG.md), P2 table), worktree branch `worktree-agent-ad2c2dfae030c1140` at `f56ad5e` · **Detector code:** not touched ·
> **Data:** the organizers' `falcon_test.zst` ([folder](https://disk.yandex.ru/d/SfBeRHbs8bNJAQ), archive sha256
> `90dea27d…5611`, [receipt](../extended_data_2026-10-17/README.md)) — development data, **not** the held-out G3 set (G3 was not touched).
>
> **Status:** the bag exists and is verified **offline**. **`ros2 bag play` on it was NOT run: UNVERIFIED** (no ROS 2 and no Docker
> daemon in the session, [section 7](#7-ros-2-check-unverified)). The bag itself is **not in the repository** (1.97 GB, `*.db3` is git-ignored); the captain keeps a copy on Google Drive ([`falcon_demo_0.db3`](https://drive.google.com/file/d/1D9LdNcyu9QwgM6Wn738rOxvU-5PwyQyU/view?usp=drivesdk), 20.10 evening; [section 8](#8-where-the-bag-is-and-how-to-move-it)) and it is rebuilt by one command in 4.4–4.7 minutes ([section 4](#4-how-to-regenerate-it)). `bag/metadata.yaml` (967 B) is in this directory: put the downloaded `falcon_demo_0.db3` next to it.

## 1. What it is

| | |
|---|---|
| Content | frames **2719–3150** of the recording (432 `sensor_msgs/msg/PointCloud2` messages on **`/iv_points`**, `frame_id` `seyond`) |
| Time | receive time **271.90–315.00 s** after the first message of the recording; header stamps 3377.298–3420.399 s (sensor clock); **43.10 s**, receive gap 0.094–0.109 s |
| Frame numbering | frame *k* = the *k*-th `/iv_points` message by receive time, the same number as row `i` of the whole-recording detector record [`l16.jsonl.xz`](../l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz) (4,443 rows, the record of the current source) |
| Files | `falcon_demo_0.db3` **1,971,884,032 B**, sha256 `b2c4a8261692c35a4e1289e4a4a9cce656fb89a514ff24e792800ab804185735`; `metadata.yaml` **967 B**, sha256 `542c7549db2e05e1f040b6b4f412d807c5f47604871bb9f68b591eb847af4119` ([`BAG_SHA256SUMS`](BAG_SHA256SUMS)) |
| Format | rosbag2 `version: 5`, `storage_identifier: sqlite3`, as the source (Humble); page size 4096, rollback journal (no WAL, so a read-only mount works as with the source) |
| Unchanged from the source | every message payload (4.5 MB each, all point fields, header stamps) and its **receive time** (the `timestamp` column); the `/iv_points` topic row (name, type, `cdr`, QoS string); the `schema` table (`3, humble`); the table DDL |
| Not carried | the `/rosout` driver log (215 messages in the recording; the recovery code finds PointCloud2 only) and the six other topics (0 messages in the recording; `metadata.yaml` lists `/iv_points` only). Message ids are renumbered 1..N (rosbag2 reads by timestamp) |

## 2. Why this window

**The person** (read from the record, not from a label — there is none): an object on the track that approaches at **1.13 m/s**
(straight-line fit of 173 detections/warnings between frames 2800 and 3030, each within 1.5 m of the line; a walking pace). It is first a
warning in the record at frame 2803 (280.3 s, 144.5 m, lateral −1.2 m, 5 points) and steady from frame 2839 (283.9 s, 139.6 m; the deck's
"appears at ~284 s"), reaches the static 115 m structure at frame 3033 (303.3 s, detection 115.08 m, lateral −0.22 m, 32 points), and walks on
(97–100 m between 320 and 360 s, 6 m at 438 s). In the raw points it is a compact isolated cluster of 30–40 points, 0.4–0.9 m across and about
1.4 m tall (the part the beams hit at 125 m), moving between frames
([`pictures/person_full_run_objects.png`](pictures/person_full_run_objects.png)). The whole-recording record has its first STOP on it at
frame 2972 (297.2 s, **124.84 m**, 4 frames; the slide's "first STOP ~125 m"), then intermittent STOP until 306 s, continuous from frame 3059.
The full record has no STOP off the person between frames 2600 and 3400 (385 STOP frames, all within 3.5 m of the fitted person). Its other
STOP frames are 159 and 2312–2314 (the static 115 m structure, before the person appears) and 4380–4382 (6 m, not examined here).

**The window:** 2719 to 3150 (43.1 s). It ends 9 s after the STOP becomes continuous (a short bag; the person keeps approaching to the end of
the recording). It starts 253 frames (25.3 s) before the full run's first STOP, **chosen by cold-start replays, not by the
BACKLOG's 280 s**, for the reason in [section 6](#6-cold-start-on-the-cut-bag): the bag starts in the middle of a recording, the node starts
cold, and **no lead-in reproduces the full-run decisions frame by frame**. What a start frame does change is (a) whether the first 192
frames (19.2 s, mount calibration) end before the person's STOP, and (b) whether a *false* STOP on a static structure appears during
the cold start. The start was picked by the following rule on a scan of 89 starts. The rule was written after the coarse scan (every 10th frame) and before the
two fine scans; it is a judgment, not a registered protocol:

1. no STOP frame off the person (a STOP frame is *off the person* if none of its detections is within 3.5 m of the person's fitted distance;
   frames 3114/3115 are excepted: there the person and the 105.6 m structure merge into one detection, a STOP at the person's place with a
   wrong distance); 2. the same for the starts 5 frames either side (a live node can start a few frames later than the bag); 3. the mount
   confirmed (bag frame 192) before the person's first STOP and at most 2 non-STOP frames in the person's continuous phase (frames ≥ 3060, where
   the full run has none); 4. a first STOP on the person within 5 m of 124.84 m; 5. of those, the shortest bag.

Of the starts scanned every frame (2695–2745) only 2717–2720 meet 1–2; of these only 2719 meets 4 (first STOP 127.18 m, against 130.5–130.8 m for
2717, 2718 and 2720; all four meet 3).
The full table is [`out/start_scan.tsv`](out/start_scan.tsv) (columns in [section 9](#9-files)); in short:

| scan | starts | with a false STOP frame | clean (rule 1) |
|---|---:|---:|---:|
| every 10th frame, 2560–2980 | 43 | 23 | 20 |
| every frame, 2695–2745 | 51 | 18 | 33 |
| both (5 starts in both) | **89** | **40** | **49** |

The false STOPs are the same few frames in many starts. All but one kind are the static 115 m structure (lateral +0.7 … +1.1 m, 8–13 points) while the mount is
still unconfirmed: frames 2926–2927 (15 starts), 2847–2852 (5–13 starts each), and single frames 2644–2645, 2764, 2830, 2929, 3002, 3092, 3114, 3136; the other is the
153 m structure at frame 2895 (4 starts, mount confirmed). The merge frame 3115 (the person with the 105.6 m structure, STOP at 101.4 m) is in 79 of 89 replays.
The full record has 4 false STOP frames on the 115 m structure in 4,443 (frames 159, 2312–2314).
**This is a selection of a window by the detector's own cold-start behaviour. It says nothing about the detector's false-alarm rate** (on the whole
recording the current record has 4 false STOP frames; the deck's numbers are in `docs/PRESENTATION.md`).

## 3. Sizes and throughput (measured first, as asked)

| step | measured |
|---|---|
| raw download, one connection, 301 MB | **18.7 MB/s** (16.1 s); link resolve 5.7 s |
| download + zstd + tar (first 1.01 GB of the split, 336 MB compressed) | 60.5 MB/s decompressed (20.2 MB/s compressed) |
| the same + the message recovery | **52.5 MB/s decompressed** (recovery 8.2 s per GB) |
| estimate to the end of 330 s (frame 3300 = 15.3 GB of the 20.28 GB split, 75 %) | 15.3 GB / 52.5 MB/s = **4.9 min** (limit set: 60 min) |
| measured, wide window frames 2500–3300 (15.30 GB read, 3.66 GB bag) | 406.8 s wall (a compile and package installs were running beside it) |
| measured, this bag, build 1 / build 2 (14.63 GB read each) | **261.3 s / 282.8 s** wall (4.4 / 4.7 min), 222.9 / 248.2 s CPU, 1.1 GB RSS |

## 4. How to regenerate it

```bash
pip install zstandard pyyaml          # the script needs nothing else; no ROS, no numpy
python3 scripts/make_falcon_demo_bag.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ /data/FALCON_DEMO_BAG \
    --first-frame 2719 --last-frame 3150 --manifest frames.tsv --receipt build_receipt.json
cd /data/FALCON_DEMO_BAG && sha256sum -c <repo>/docs/evidence/falcon_demo_bag_2026-10-20/BAG_SHA256SUMS
```

4.4–4.7 min measured (two builds) on 4 vCPU with an 18–20 MB/s link, 2.0 GB of disk (allow 5–7 min); the archive is streamed, nothing else is stored; the script stops reading
after frame 3150 (it reads the first 72 % of the split). A local `falcon_test.zst`, an unpacked `.db3` split or a bag written by this script
are accepted instead of the link; `--start-s/--end-s` (seconds after the first message) instead of frame numbers. It exits non-zero and
removes what it wrote if a message was lost on the way (the frame numbers would not match), if the stream ends before the window,
if the window is empty, or if the read-back of the written bag differs. [`scripts/make_falcon_demo_bag.py`](../../../scripts/make_falcon_demo_bag.py)
reuses `scripts/stream_falcon.py` (`Recover`, `byte_stream`) and, through it, `window_bag.py` by import.
**Two builds from the archive link gave a byte-identical `falcon_demo_0.db3` and an identical manifest** (the first build's
`metadata.yaml` had YAML anchors, see [section 10](#10-what-was-corrected-on-the-way); [`out/build_receipt_first_build.json`](out/build_receipt_first_build.json)).

## 5. Verification

Method and counts (the scripts are in [`scripts/`](scripts/); every check has a control that fails when it should):

| check | result |
|---|---|
| **Payloads equal the source.** The cutting script re-reads the written bag through sqlite and compares timestamp and sha256 of every message with what the recovery returned | 432 / 432 equal; `PRAGMA quick_check` ok |
| **Three separate recoveries agree.** Payload sha256 of frames 2719–3150: build 1, build 2, and the wide 801-frame bag (frames 2500–3300, streamed separately) | 432 / 432 equal in all three; db3 files of build 1 and 2 byte-identical |
| **An independent source for the content.** [`n2_falcon_2026-10-18/cache_inventory.json`](../n2_falcon_2026-10-18/cache_inventory.json) holds the sha256 of the `.npz` that `cache_falcon.py` wrote for each frame from the *extracted* 20.3 GB split read by sqlite itself. The same decode and `np.savez_compressed` call on the cut bag's messages | **432 / 432 sha256 equal** (801 / 801 for the wide bag). Covers every decoded point (xyz, intensity); it does not cover the header and the fields the decode skips, which the other checks cover |
| **Receive time, header stamp, point count vs the whole-recording record** ([`verify_bag.py`](scripts/verify_bag.py), the bag read through sqlite only) | 432 / 432 each (receive time and stamp to the record's 4 decimals; points the node decodes = the record's `n_points`) |
| **`metadata.yaml`** vs the bag, and the `/iv_points` topic entry (name, type, `cdr`, QoS string) vs the organizers' own `metadata.yaml` (sha256 `44aac464…7287`, = the committed [source receipt](../n2_falcon_2026-10-18/source_receipt.json)) | message count, start, duration, file name consistent; topic entry **equal**; version 5 / sqlite3 equal; no YAML anchors |
| **db3 structure vs the source** ([`out/db3_header_compare.json`](out/db3_header_compare.json)): header fields (page size, versions, encoding), the five DDL statements, the `schema` row, the topic row | equal (only the page count differs: 481,417 against 4,951,550); `PRAGMA integrity_check` ok |
| **A second, independent rosbag2 reader.** `rosbags` 0.11.5 (pure Python) opens the bag from `metadata.yaml` and deserializes every message with the Humble definitions ([`rosbags_check.py`](scripts/rosbags_check.py)) | 432 / 432 deserialize as PointCloud2, `seyond`, 48-byte points, `width×48` data bytes, receive times increase, stamps equal the record; its count, topic and start time equal `metadata.yaml` |
| **Control of the checker:** the same `verify_bag.py` with the frame number shifted by one | 432 / 432 mismatches in every category, exit 1 |
| **Look at the data** | [`pictures/`](pictures): top-down and side views of the raw points around the record's objects at frames 2972, 3000, 3100 (a compact, person-sized, moving cluster) and of the cold run's first STOP and the merge frame 3115 |
| **Physical plausibility** | walking pace 1.13 m/s; about 95,000 points and 4.57 MB per frame; receive gap 0.1 s ± 0.01; 1.4 m of the person visible at 125 m; the cold run's STOP distances 127 → 124 → 109 m fall with time |
| **The test** ([`tests/test_make_falcon_demo_bag.py`](../../../tests/test_make_falcon_demo_bag.py)) | 22 tests on a synthetic 12-frame split, no data, no network, none skipped (11 are deselected, not skipped, in the runtime image, see [section 10](#10-what-was-corrected-on-the-way)). Mutation controls: 7 deliberate breaks of the script (a flipped payload byte with and without the read-back, last frame exclusive, ids not renumbered, wrong metadata count, shared YAML objects, no reorder window) each fail the suite |

**Not checked:** a byte-for-byte comparison with the source split's own rows (the 20.3 GB split is not stored and only its first 72 % was
read; the cache `.npz` hashes are the independent substitute); that `ros2 bag play` opens the bag (section 7).

## 6. Cold start on the cut bag

The node starts without the 2,719 earlier frames (`play_bag.sh` calls `reset_replay.py` before each bag, the node's `reset_input` builds a new
`Detector`, `detector_node.py`; `NodeReplica` starts a new `Detector` too).
Replayed with the judge's `NodeReplica` through the unmodified `judge_runner.py` on a clean export of `f56ad5e` with the native kernels
built, Python 3.12.3, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`
(`RESENSE_REPO` = that export; the worktree's `resense/`, `native/`, `configs/` were not run from or changed). Every frame is processed;
the live node's freshness and catch-up are **not** modelled (stale results are UNVERIFIED).

| | whole recording (warm, record rows 2719–3150) | **cut bag, cold start** |
|---|---|---|
| first STOP | frame 2972, 297.2 s, **124.84 m**, 4 frames | **frame 2950, 23.1 s after the bag's first frame (295.0 s), 127.18 m**, 3 frames |
| STOP runs | 2972–2975, 2994–3002, 3009–3038, **3059–3150** | 2950–2952, 2981–2989, 2993–3003, 3007–3038, **3058–3106, 3108–3150** |
| STOP frames in the window | 135 | 147 (146 on the person; 3115 merged with the 105.6 m structure, STOP at 101.4 m) |
| FAULT | frame 0 of the recording only | the bag's first frame only (frame 2719: "6 of 6 central sectors without returns: view blocked", as frame 0 of the recording); no FAULT after it |
| GO | none in the window | 9: frames 2720–2724 right after the first frame (the recording has GO at its frames 1–4) and 2911–2914 at the mount confirmation (its frames 192–195) |
| mount confirmed | (before the window) | bag frame 192 = frame 2911, 19.2 s after the start, 3.9 s before the first STOP |
| decision differs from the record | — | **32 of 432** (CAUTION→STOP 17, STOP→CAUTION 5: 2972–2975 and 3107, CAUTION→GO 9, CAUTION→FAULT 1); **identical from frame 3108 on** |
| detections after frame 3108 | — | distance equal (median difference 0.00 m; the 3115 merge 6.0 m), lateral median 0.04 m, track centre median 0.01 m (max 0.05 m) |
| replay cost per frame | 21 ms detector median (the deck's number, another machine) | 29.9 ms median decode + detect, 83.7 max (this machine, 4 vCPU, 1 job) |

* **Resets:** none inside the replay. **Rows:** all 432 rows differ from the record in some non-timing field (warnings, track centre, curvature,
  clear distance): the detector's state is built from the whole history. [`out/coldstart.jsonl.xz`](out/coldstart.jsonl.xz) holds the rows.
* **Is a lead-in needed?** No lead-in reproduces the full-run decisions: starts 412, 372 and 272 frames before the first STOP still leave 24, 35 and 44 frames
  with another decision (to frame 3150; scan table), mostly in the person's STOP/CAUTION alternation between 297 and 306 s, which depends on the whole history.
  A lead-in of **192 frames plus a few** is what the cold start needs for the *calibration* (mount confirmed before the person's STOP): starts 2880 and later
  have 10–45 non-STOP frames (runs of 6–18 frames, up to 1.8 s of CAUTION or GO) in the phase where the full run has STOP continuously, because the
  person's STOP then falls into the unconfirmed phase. The chosen bag has a 253-frame lead-in; a longer one would only make the bag longer.
* **The live run will not show 124.8 m.** The cold run's first STOP is 127.2 m at 23.1 s, and "frame 2950, 127.18 m" is the first person STOP of 18 of the
  89 cold starts (median over the starts with a first STOP later than 5 s: 127.2 m, range 120.2–138.8 m). The slide's "124.8 m at 297 s" is the whole-recording
  number; for the live run say "about 125–130 m".
* **Time to the first STOP in the live demo** (not measured on the node): bag time 23.1 s, plus the player's `--delay 3` of `play_bag.sh`
  → about 26 s at `--rate 1.0` (inside the "STOP ≤ 30 s from the start of playback" criterion), about 49 s at `--rate 0.5` (outside).
* **Instrumentation control:** the unmodified `judge_runner.py` on the final bag and `coldstart_compare.py` give identical rows
  (432 / 432, every field but timing; [`compare_rows.py`](scripts/compare_rows.py)); the replay of the cut bag equals the replay of the same frames
  out of the wide bag (432 / 432). The same comparator reports 432 / 432 differing rows for a start one frame later (control).
* **Label control:** every STOP row of the chosen replay is attributed by distance to the fitted person
  ([`person_track.py`](scripts/person_track.py)); the record's own 385 STOP frames in 2600–3400 all come out "on the person", the false frames
  found in other starts (2847–2852, 2926–2927, 2830, 2895, 3002, …) come out "off the person" and were checked against the record (the person was then at
  129–142 m; the objects are the static structures at 115 m, lateral +0.7…+1.1, and 153 m that the record lists as warnings at those frames), and frame 3115 was looked at in the
  raw points ([`pictures/person_cold_run_objects.png`](pictures/person_cold_run_objects.png): two clusters, the person and the 105.6 m structure, one detection).
  There is no ground truth; this is an attribution aid.

## 7. ROS 2 check: UNVERIFIED

`ros2` is not installed here and `docker info` fails (`dial unix /var/run/docker.sock: no such file`; `dockerd` exists but no daemon runs, and the
repo's image `resense:*` is not present; building or pulling it needs Docker Hub and apt downloads, which this task did not allow). **So
`ros2 bag info` and `ros2 bag play` were not run on this bag, and it is not claimed that they open it.** What was checked instead is in section 5
(format and structure equal to the organizers' bag; an independent pure-Python rosbag2 reader opens it).

Commands for someone with the image (modelled on the CI steps "ROS 2 smoke test" and "the jury wrapper plays two bags"; `BAG` = the bag directory, `IMAGE` = the
image tag, run from the repository root):

```bash
BAG=/data/FALCON_DEMO_BAG IMAGE=resense:1.2.0-aec88d2
(cd "$BAG" && sha256sum -c <repo>/docs/evidence/falcon_demo_bag_2026-10-20/BAG_SHA256SUMS)
docker run --rm -v "$BAG":/data/bag:ro "$IMAGE" ros2 bag info /data/bag
#   expect: Storage id: sqlite3 · Duration: about 43.1 s · Messages: 432 · Topic: /iv_points | sensor_msgs/msg/PointCloud2 | Count: 432 | cdr
docker run --rm -v "$BAG":/data/bag:ro "$IMAGE" bash -lc \
  "ros2 bag play /data/bag --rate 1.0 --delay 1 --read-ahead-queue-size 10 --disable-keyboard-controls"      # plays 43 s without error
# one run through the node, headless, as the jury wrapper does (prints every decision change; one node, reset boundary, profile falcon_ros):
IMAGE=$IMAGE PLAYER_USER=1000:1000 scripts/play_bag.sh --rate 1.0 --sensor-profile falcon_ros "$BAG" | tee out_falcon_demo.txt
grep -q STOP out_falcon_demo.txt && grep 'profile=falcon_ros' out_falcon_demo.txt | head
```

Acceptance to record (PRESENTATION's "Falcon-бэг" paragraph): `ros2 bag info` opens it; one run through the node shows STOP on the person not later than 30 s
from the start of playback; first line `profile=falcon_ros`; FAULT only on the first frame; record the first STOP and its distance (expect
~127 m near 23 s of bag time, i.e. ~26 s after the player starts at `--rate 1.0`; a different value is a finding, not necessarily a failure).

## 8. Where the bag is and how to move it

The bag is 1.97 GB and is development data of the organizers. **Where it is (20.10 evening):** the captain's Google Drive,
[`falcon_demo_0.db3`](https://drive.google.com/file/d/1D9LdNcyu9QwgM6Wn738rOxvU-5PwyQyU/view?usp=drivesdk) (1,971,884,032 B). It was streamed back from that link on 20.10 and hashed: sha256 `b2c4a8261692c35a4e1289e4a4a9cce656fb89a514ff24e792800ab804185735`,
equal to `BAG_SHA256SUMS`. The Drive file was readable without a login at that time: whoever has the link can download it, and this
repository is public; the owner can restrict the Drive sharing, and the checksum below stays the check.
*Edit of 20.10 evening by P1's session: this section said "never to a cloud folder or the repository". That was the building agent's own
caution (no organizers' rule was found in the repository); the captain decided to keep a Drive copy. Other copies: direct, as below.*
The temporary anonymous upload that carried the file from the build session to the Drive (21:20 to about 21:55 MSK) was deleted after the
check; the host's API answered `ok`, the removal itself could not be confirmed (its page is a script shell).

To use the Drive copy: download it into `bag/` (next to `bag/metadata.yaml`), then check:

```bash
cd docs/evidence/falcon_demo_bag_2026-10-20/bag && sha256sum -c ../BAG_SHA256SUMS      # both files: OK
```

Direct copy between machines:

```bash
# from the machine that holds it (LAN, ssh) — or copy the directory to a USB stick (ext4/exFAT) and carry it:
rsync -a --info=progress2 falcon_demo_bag/ captain@demo-machine:/data/FALCON_DEMO_BAG/
# on the demo machine, before the rehearsal, and again after any copy:
cd /data/FALCON_DEMO_BAG && sha256sum -c <repo>/docs/evidence/falcon_demo_bag_2026-10-20/BAG_SHA256SUMS
cat /data/FALCON_DEMO_BAG/*.db3 > /dev/null          # into the disk cache, as the Pandar bag (PRESENTATION)
```

If the copy is lost, the command in section 4 rebuilds it (needs the internet and 2 GB).

## 9. Files

Everything here is committed except the bag (`bag/` holds only its `metadata.yaml`). Scripts take the evaluated tree from `RESENSE_REPO` and need numpy 1.26 / scipy 1.13 / scikit-learn 1.5 (the
image's stack) and, for `rosbags_check.py`, `pip install rosbags==0.11.5`.

| file | what |
|---|---|
| [`../../../scripts/make_falcon_demo_bag.py`](../../../scripts/make_falcon_demo_bag.py), [`../../../tests/test_make_falcon_demo_bag.py`](../../../tests/test_make_falcon_demo_bag.py) | the cutting script and its test |
| `BAG_SHA256SUMS` | sha256 of the two bag files (run inside the bag directory) |
| `bag/metadata.yaml` | the bag's metadata (967 B), copied from the build; the `.db3` goes next to it (section 8) |
| `SHA256SUMS` | sha256 of every file in this directory but itself (`sha256sum -c SHA256SUMS` from here) |
| `frames.tsv` | per frame: number, receive time (ns), header stamp, bytes, sha256 of the payload (the manifest of the bag) |
| `build_receipt.json`, `out/build_receipt_first_build.json` | the two archive builds: window, counts (found 3205, recovered 3205, lost 0), bytes read, wall/CPU, file sizes and sha256 |
| `out/verify_bag.json`, `out/rosbags_check.json`, `out/db3_header_compare.json` | section 5 |
| `out/coldstart.summary.json`, `out/coldstart.jsonl.xz`, `out/judge_runner_plain.meta.json` | section 6: the cold replay of the final bag (summary and the 432 rows) |
| `out/start_scan.tsv` | the scan of 89 starts: `start`, `frames` (to frame 3150), `lead_in_frames_before_record_first_stop` (2972 − start), `mount_ok_frame`, `fault_frames`, `stop_frames`, `stop_person/mixed/other` (by the person attribution), `other_frames` (first 12), first STOP and first person STOP (frame, m, s from the start), `go_after_first_stop`, `non_stop_frames_from_3060`, `longest_non_stop_run_from_3060`, frames with another decision than the record, `[GO, CAUTION, STOP, FAULT]` counts, `clean` (rule 1) |
| `out/throughput_measure.log` | section 3 |
| `scripts/coldstart_compare.py` | cold replay of a bag and comparison with the record (`--skip K` for a later start in a wider bag) |
| `scripts/scan_starts.py` | many cold replays and the table above (`--starts A:B:STEP`, `--jobs`) |
| `scripts/person_track.py` | the person's distance by frame from the record, and the STOP attribution |
| `scripts/verify_bag.py`, `scripts/rosbags_check.py`, `scripts/compare_rows.py`, `scripts/plot_person.py` | the checks of section 5, the row comparator, the pictures |
| `pictures/` | raw-point views (orange = within 1.5 m × 1.2 m of the object, the height window is centred on it) |

Commands used (all `RESENSE_REPO=<clean export of f56ad5e, native kernels built> OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `python3 -I`):
`make_falcon_demo_bag.py` (sections 3–4); `verify_bag.py --bag B --first-frame 2719 --record l16.jsonl.xz --manifest frames.tsv --inventory cache_inventory.json
--original-metadata <the organizers' metadata.yaml> --out out/verify_bag.json`; `rosbags_check.py B --first-frame 2719 --record l16.jsonl.xz`;
`coldstart_compare.py --bag B --record l16.jsonl.xz --first-frame 2719 --out out/coldstart`; `judge_runner.py --bag B --out …`;
`scan_starts.py --bag <wide bag 2500–3300> --first-frame 2500 --record l16.jsonl.xz --starts 2560:2980:10 --last-frame 3200 --end-frame 3150 --out-dir D`
(and `2695:2725:1`, `2726:2745:1`).

## 10. What was corrected on the way

* The first build's `metadata.yaml` contained YAML anchors and aliases (`&id001`, `*id001`: PyYAML emits them for a dict used twice). The tests had read it
  with a YAML loader and passed. Found by reading the file; the writer now builds separate objects, the test asserts no anchors, a mutation that
  brings them back fails 6 tests. The bag was rebuilt from the archive (the db3 did not change).
* The first picture showed nothing: the record's object centres are in the detector's vehicle frame (mount pitch −2.39° removed, 4 m of height at 100 m), the cloud was
  in the sensor frame. Only x and y are taken from the record now, the height window is centred on the points.
* The first person classifier assumed the person stops at the 115 m structure; it called 1,300 STOP frames "other" (the person walks on to 6 m). It follows the record's
  objects now; the record's own 385 STOP frames in 2600–3400 all come out on the person.
* The plan "find the lead-in that reproduces the full run" cannot be met (section 6); the window was chosen by the scan instead, with the false-STOP risk stated.
* The worktree is at `f56ad5e`, not at `fe08f4f` as the task said (`fe08f4f` is one commit ahead; only `docs/BACKLOG.md` differs). The BACKLOG row exists at both.
* Python packages had to be installed from PyPI into scratch virtual environments (the session had no `zstandard`, `scipy`, `scikit-learn`, `pytest`): the image's pinned stack
  (numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, pyyaml 6.0.2), `zstandard` 0.25.0, `pytest` 8.4.2, `rosbags` 0.11.5, `Pillow`, `ruff` 0.15.8 (the CI's lint version). No other data
  was downloaded than the `falcon_test.zst` stream.
* In the runtime image (`.dockerignore` leaves `docs/` out) `stream_falcon.py`'s import of `window_bag.py` does not exist; the 11 tests that run the recovery carry
  `@pytest.mark.realdata` on that directory (deselected there, run in the `pytest` job on a checkout); the other 11 run everywhere. Adding `window_bag.py` to the
  Dockerfile's fixture block and `.dockerignore` would run them in the image too; `docker/` was outside the files this task could change.

## 11. PATCH-READY text (not applied)

`docs/PRESENTATION.md`, `web/DEMO_HANDOFF.md` and `docs/BACKLOG.md` were not edited. Language of the files: Russian.

### 11.1 `docs/PRESENTATION.md`

**(a) line 17**, replace

```
> **Статус:** колода и речь к защите готовы к репетиции 1 (20.10); Falcon-бэг для показа ещё не подготовлен.
```

with

```
> **Статус:** колода и речь к защите готовы к репетиции 1 (20.10); Falcon-бэг для показа собран 20.10 и проверен офлайн
> ([`evidence/falcon_demo_bag_2026-10-20`](evidence/falcon_demo_bag_2026-10-20/README.md)); `ros2 bag play` на нём не проверен.
```

**(b) line 27** (table row «Живой показ 1.2.0»), replace `**Falcon-бэг с человеком для показа ещё не подготовлен и не проверен**` with

```
Falcon-бэг с человеком собран и проверен офлайн (432 кадра, 1,97 ГБ, SHA-256 в [README](evidence/falcon_demo_bag_2026-10-20/README.md)); **`ros2 bag play` на нём не проверен**
```

**(c) lines 208–218**, replace the whole paragraph «**Falcon-бэг для показа (`FALCON_DEMO_BAG`) — не готов, подготовить к репетиции 1.** …» through «…Falcon — по слайду 14.» with

```
**Falcon-бэг для показа (`FALCON_DEMO_BAG`) — собран 20.10, `ros2 bag play` на нём не проверен.** Окно записи `falcon_test`:
кадры 2719–3150 (t = 271,9–315,0 с от первого сообщения), 432 кадра, 43,1 с, 1,97 ГБ, один топик `/iv_points`; без `/rosout`.
Человек идёт к поезду со скоростью ~1,1 м/с. В реплике узла на **холодном** старте (бэг начинается с середины записи) первый STOP
по человеку — на 23,1 с бэга, **127,2 м** (в полной записи — 124,8 м на 297 с: это число слайда, не живого прогона; живое — «около
125–130 м»), затем STOP с перерывами до ~34 с и непрерывно после. Первый кадр бэга — FAULT («view blocked», как первый кадр полной
записи), 5 кадров GO, затем CAUTION: первые 192 кадра (19 с) узел подтверждает крепление. Ложных STOP в реплике на этом старте нет
(кроме кадра 3115: человек и конструкция на 105,6 м слиты в одну деталь, STOP на 101 м вместо 107 м). Старт выбран сканом 89 стартов:
на холодном старте ложные STOP на конструкциях в 115 и 153 м есть у 40 из них, у этого и у пяти соседей с каждой стороны их нет — это
свойство повтора на реплике узла, не детектора и не живого узла. Сборка (4,4–4,7 мин) и проверки — в
[`evidence/falcon_demo_bag_2026-10-20`](evidence/falcon_demo_bag_2026-10-20/README.md). SHA-256: `falcon_demo_0.db3`
`b2c4a826…5735`, `metadata.yaml` `542c7549…4119` (полные — в `BAG_SHA256SUMS`; проверка `cd /data/FALCON_DEMO_BAG && sha256sum -c …/BAG_SHA256SUMS`).
Приёмка на репетиции 1: `ros2 bag info` открывает (432 сообщения, 43,1 с); один прогон через узел при `--rate 1,0` — STOP по человеку не позже
30 с от начала воспроизведения (по реплике 23,1 с + 3 с задержки плеера; при `--rate 0,5` это ~49 с, не проходит), первая строка
`profile=falcon_ros`, FAULT только на первом кадре; записать SHA-256, первый STOP и дистанцию. **Не использовать** для показа первые 100 кадров
записи (`falcon_first100`): в них ложный STOP на конструкции в 115 м. Если бэг не прошёл репетицию 2 (22.10) — живой показ только Pandar, Falcon — по слайду 14.
```

**(d) lines 238–241** («**Что показать:** …»), replace the sentence «Затем без перезапуска — Falcon: первая строка `profile=falcon_ros`, первый кадр — FAULT/CAUTION (ориентация ещё не подтверждена; так и задумано), затем зелёный 3D-бокс габарита, CAUTION у конструкций на 105,6 и 115 м, STOP по человеку.» with

```
Затем без перезапуска — Falcon: первая строка `profile=falcon_ros`, первый кадр — FAULT, потом CAUTION (крепление ещё не подтверждено
первые 19 с; так и задумано), зелёный 3D-бокс габарита, CAUTION у конструкций на 105,6 и 115 м, и около 23-й секунды бэга — STOP по человеку
(~127 м), с перерывами до ~34 с, дальше непрерывно.
```

**(e) line 177** (speech row 10), replace «Если Falcon-бэг не готов — только Pandar, Falcon — на слайде 14.» with «Если Falcon-бэг не прошёл репетицию — только Pandar, Falcon — на слайде 14.»

### 11.2 `web/DEMO_HANDOFF.md`

At this commit the file has **no** Falcon lines (it describes the v1.0.0 show: one Pandar bag; its header sends the reader to PRESENTATION for 1.2.0), so this is an
insertion, after the paragraph «Без ROS 2 на хосте плеер — из образа: … скриншот на слайде 10.» in «Показ (слайд 10, ~50 с)»:

```
**Falcon (только 1.2.0; порядок — `docs/PRESENTATION.md` «Демонстрация»).** Второй бэг в том же узле: короткий бэг `/data/FALCON_DEMO_BAG`
(432 кадра, 43 с, 1,97 ГБ; собран 20.10, [README](../docs/evidence/falcon_demo_bag_2026-10-20/README.md)). До показа:
`cd /data/FALCON_DEMO_BAG && sha256sum -c BAG_SHA256SUMS` (файл — в каталоге evidence) и `cat /data/FALCON_DEMO_BAG/*.db3 > /dev/null`. Показ:
`scripts/run_demo.sh --rate 1.0 --sensor-profile pandar128 /data/for_hackathon/doubleT_obstacle --sensor-profile falcon_ros /data/FALCON_DEMO_BAG`.
Ожидается: FAULT на первом кадре, STOP по человеку около 23-й секунды бэга (~127 м; число слайда 124,8 м относится к полной записи). `ros2 bag play`
на этом бэге не проверен: проверить на репетиции 1 и записать результат в `P2_STATUS.md`.
```
