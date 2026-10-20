# Organizer dataset update: object markers — 19 October 2026

Read-only intake for H1 development. No detector replay, tuning, held-out run or
release action was performed. The input is the public organizer folder
<https://disk.yandex.ru/d/SfBeRHbs8bNJAQ>.

## What is actually new

The public API lists six files, independently confirmed against the public web
page. The four previously known archives retain their recorded SHA-256 values:
`cloud_with_fake_obj.zst`, `new_data.zst`, `new_synth_data.zst` and
`falcon_test.zst`. The latter two were already examined on 17–18 October.

Two additional files are dated **19 October**, not 17 October:

| File | Bytes | SHA-256, downloaded and verified against the API |
|---|---:|---|
| `new_synth_data_with_markers.zst` | 2,533,631,921 | `04d176b49526e5da55a0481cf92d8442604dc0fb9f69c31680482b21d8682760` |
| `obstacles.md` | 1,024 | `db62201d049da4f16063abceab8a918f7091335e41a093fcb9211863df687558` |

The new archive contains three rosbag2 bags, each with `/lidar_points`
(`sensor_msgs/msg/PointCloud2`) and `/synthetic_obstacle_markers`
(`visualization_msgs/msg/MarkerArray`).

| Bag | Point clouds | MarkerArray messages | Total messages |
|---|---:|---:|---:|
| `synthetic_platform_cloud_with_markers` | 386 | 386 | 772 |
| `synthetic_switch_cloud_with_markers` | 736 | 736 | 1,472 |
| `synthetic_tunnels_cloud_with_markers` | 545 | 545 | 1,090 |

Every one of the **1,667 serialized PointCloud2 messages is byte-identical to
the original `new_synth_data.zst`**, with identical bag receive times. The old
archive was downloaded again and its complete SHA-256 independently verified as
`e09336cb939e6b5a6fdb35ccacce59f3808d875a4084142a02cbd1cf88a26bc7`.
This is new annotation of existing scans, not new cloud scenes.

## Useful content for H1

The organizer description explicitly identifies:

* Platform: dust on both sides / another cloud, two small cubes, a person.
* Switch: small cubes including one on the left rail, an inclined hanging cable,
  four dust clouds.
* Tunnels: small cubes, four dust clouds, a **2 × 2 × 2 m cube**, and a beam
  across the rails.

The markers provide oriented wireframe boxes (`LINE_LIST`, 24 local endpoints),
position, quaternion, namespace and ID in `hesai_lidar`. There are also DELETE
messages: **a DELETE is not a visible object**. The person uses several body-part
markers, so a marker ID is not necessarily a physical object ID. `text` is empty;
the prose object order is not a ready-made mapping to numeric marker IDs.

Examples checked against raw returns:

| Bag / marker | Local dimensions | Raw check |
|---|---|---|
| Switch ID 1 | 0.11 × 0.11 × 2.40 m, rotated | frame 354, centre forward 98.9 m: 10 returns inside the box |
| Tunnels ID 0 | 2 × 2 × 2 m | frame 375, centre forward 124.7 m: 134 returns inside the box |
| Tunnels ID 1 | 2.25 × 0.14 × 0.14 m | beam geometry, 50 active rows have raw support |
| Platform ID 17 | 0.38 × 0.24 × 0.64 m | one person component; frame 170 at 99.6 m has 14 returns |

All active markers in all three recordings were checked for raw points inside
their oriented boxes; every active row has support at a 0.1 mm boundary tolerance.
This verifies geometric support, **not exact point segmentation for every box**.
The original point order, duplicates and distances are retained. Some synthetic
returns are hundreds of metres away (the large cube has a sparse row around
738 m), so marker range must not be presented as real sensor obstacle range.

This enables organizer-based geometry, visibility and detection matching, including
sparse rows missed by earlier team annotation. The intended relationship to
the rails still requires a separate check, especially on far curves and for
rail-adjacent boxes. The markers should be frozen and interpreted before scoring;
new scores and improvements are not established by this intake.

## Correction: earlier dust-absence claim was too strong

The earlier [17 October intake](../extended_data_2026-10-17/README.md) said there
was no dust, and the exact-reference annotation excluded 31 near-field differing
points as non-object differences. The organizer now labels centimetre-scale
particles in these very scans as dust. Their selected returns do not have
intensity 1, explaining why that cue could not identify them.

An independent exact float32 XYZ comparison on **all platform frames 0–314**
against original Set O frames 1195–1509 finds:

| Quantity | Raw return count, duplicates retained |
|---|---:|
| Newly added XYZ, no 250 m cutoff | 137,841 |
| Added XYZ within the previous 2.5–250 m radial window | **119,377**, reproducing the earlier count |
| Added XYZ covered by the union of organizer markers | **137,841** |
| Added XYZ outside that union | **0** |
| Original/reference returns also selected by that union | 2 |
| Dust-selected returns | **31**, all are exactly-new XYZ |

Thus the historical blanket absence statement is superseded. The supported
finding is **very sparse, tiny dust particles**, not a dense sustained dust cloud.
No claim of dust robustness follows without evaluation. The broader switch/tunnel
markers also include small near-field particles with non-intensity-1 returns.

## What is still missing

All SQLite topics, total counts and orphan counts were checked; metadata counts
agree. There are exactly the two topics above in each bag, **no rail-axis or pose
reference topic**. The same inventory detects the known nonzero marker and cloud
counts, providing a positive control for that absence. Archive members are only
the three database files and their metadata, with no extra trajectory/axis file.

These are obstacle annotations. They do **not** supply a surveyed far rail axis,
synchronized validated ego poses, or calibrated rail-axis uncertainty. They
therefore help finish H1 object diagnosis and validation, but do not automatically
remove the [far-axis reference blocker](../h1_reference_2026-10-19/README.md).

## Verification and retained artifacts

Working artifacts are retained under
`/tmp/opencode/yadisk-markers-2026-10-19/`:

* `listing.json`, archive/text download receipts and complete downloaded archives;
* extracted raw bags, `members.json`, `inventory.json`;
* per-bag `*.markers.json`, `*.clouds.json`, `*.original-clouds.json`, `*.support.json`;
* `cloud-comparison.json`, `marker-summary.json`, `marker-validation.json`;
* `platform-exact-reference.json` and visually inspected `marker-raw-examples.png`
  (person component, inclined cable and large cube, top/side views).

Tools retained in `/tmp/opencode/`:
`inspect_yadisk_update.py`, `analyze_yadisk_markers.py`,
`compare_yadisk_clouds.py`, `validate_yadisk_markers.py`,
`validate_platform_reference_markers.py`.
They use the existing Python environment at
`/tmp/opencode/resense-b4-venv/bin/python`. Intake creates its output exclusively;
use a fresh output path when reproducing. Raw bags are opened SQLite read-only.

Quaternion transforms were independently checked with the quaternion-vector
identity. Each marker ID with support had a same-frame positive selection and a
10 km shifted negative control. The 315-frame exact source subtraction is
independent of marker geometry and reproduces the previously verified 119,377
point count before testing complete marker coverage. All 1,667 frame header
times/frame IDs and paired bag timestamps agree. No detector-derived axis or
output enters these checks.
