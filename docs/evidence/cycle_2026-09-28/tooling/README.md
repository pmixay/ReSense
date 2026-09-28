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

A focused Docker context build verifies the protocol and all 42 committed NumPy
fixture arrays reach the image (30 arrays used by the sequence controls).
`.dockerignore` now permits precisely that protocol and fixture subtree and
excludes the local Ruff cache. This is a build-context check, not the final image
replay. The newly added synthetic evaluator also has 24 focused passing tests.

## Fresh baseline image

The full tools image built successfully from `b78a500`, with image ID
`sha256:a3da7c28771a8ce2eb32f5e13e55c01ca59a12ad15719b40b3ba2cb7115b57f4`.
Outside the source directory, its installed package loads the native extension,
rosbags 0.11.5 and Open3D 0.19.0. ROS resolves `resense_ros detector_node` and the
launch description. The 31 cache, synthetic evaluator and range diagnostic tests
pass inside this image with networking disabled.

The retained logs are `image_tooling_tests.txt` and `image_import_launch.txt`.
This is the unchanged baseline detector, before candidate integration. A final
candidate image still needs its own suite and ROS replay checks. Both registered
protocol versions are now included by the Dockerfile and build context exceptions;
the v2 addition follows the baseline image build above.

The revised evaluator also passes all 40 focused checks using that freshly
installed baseline package, with current source tests mounted read-only outside
the working directory (`image_observer_tests.txt`). This includes installed-package
import layout and explicit measured-source guards. The two warnings concern only
pytest's inability to write its cache into the read-only test mount.
