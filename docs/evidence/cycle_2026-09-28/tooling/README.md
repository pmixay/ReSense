# Reproducible split-file intake

The pinned development image used `rosbags==0.10.11`, but the extended-ride intake
passes standalone `.db3` files to `rosbags.rosbag2.Reader`. Rebuilding the complete
archive exposed a `ReaderError` looking for `<split>.db3/metadata.yaml`.

The new real SQLite/CDR integration test fails with 0.10.11 and passes with 0.11.5.
It writes four PointCloud2 messages, compares directory and standalone-file reads,
removes metadata before the latter, and checks stride, limit, stamps, frame ID,
point arrays and topic selection. All nine cache/intake tests pass with the new pin.
The package's tooling minimum is now 0.11.0 and the Docker tools pin is 0.11.5.
Standalone storage support was added in 0.11.0:
[upstream changelog](https://ternaris.gitlab.io/rosbags/changes.html).

The score branch is also included in the existing full Docker CI path: original-bag
cold replay, remote viewer and downloadable offline image archive. These workflow
edits require a subsequent passing CI run; enabling a step is not validation evidence.

Full suite at `ba5e539`: 765 passed, six subtests passed, one data-availability
failure (`new_data_55_0013` absent from the older partial cache). The one affected
real-data test passed after selecting fresh, complete splits 55/56 through
`RESENSE_RIDE_CACHE=/cycle/rail_start_cache`: 766 unique tests passed across the
two runs, no unresolved failure. Both original and focused logs/JUnit are retained.
This run uses the persistent development container, not a newly built final image.

The exact image also needs the registered protocol file, used by the new synthetic
CLI and tests. Its Dockerfile now copies that file and explicitly installs the
`libusb-1.0-0` runtime dependency required to import the Open3D tools wheel.
