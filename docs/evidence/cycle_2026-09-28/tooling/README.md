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
