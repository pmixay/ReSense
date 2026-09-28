# Oracle source-motion accumulation protocol

Registered before executing the diagnostic. Base: `167c6da`. One CPU worker.
Production code and thresholds remain unchanged. No score or real-odometry claim.

## Fixed inputs and motion rule

- Organizer set O frames **295–338 inclusive**, including every repeated position and
  timestamp. Frames 295–298 supply context; report all frames with available support.
  The selected approach spans small-center source points above 100 m through about 55 m.
- Extract explicit organizer points from the raw message's final zero delimiter; use
  labels only to name the source group. Match exact quantized XYZ/intensity/ring copies
  into the full cached frame. Remove **all** organizer source groups for the paired
  background. Preserve original source sampling, coordinates and timestamps.
- Read historical serialized track fits only for conditional corridor membership and
  cluster shape tests. These fits never set source placement, motion or sampling.
- Estimate a causal source-relative X speed using the latest five source minima and
  original message timestamps: median of all pairwise approach slopes whose observations
  are at least two frames apart. Until three observations exist, use the available
  adjacent slope; first frame speed is unknown. Clip to [0, 30] m/s and record raw values.
  Repeated positions remain in the fit; no frame is removed or retimed. This rule is fixed
  independently of detection results. It is oracle relative motion, not vehicle odometry.
- Use each estimated speed over the current measured timestamp interval, accumulating
  displacement across intervals. Apply identical motion to targets and paired backgrounds.
  Report actual source displacement residuals and Y/Z span, including duplicate positions.

## Fixed comparisons

Windows of 1, 2, 3, 4 and 5 consecutive frames; production range-normalized voxelization
throughout. Compare the original neighbor graph with the conservative physical-edge
filter defined in the preceding metric diagnostic. No radial voxel subdivision here.

1. **Source-only physical translation:** shift previous source XYZ along vehicle X by
   the accumulated oracle displacement. Re-evaluate membership against the current
   historical geometry. Count occupied voxels, strict occupied voxels, contributing frames,
   physical extents, DBSCAN support, and surviving source clusters with all current count,
   shape, far-height and smear rules applied. Do not register Y/Z using the detector axis.
2. **Production accumulation conditional on historical geometry:** feed each historical
   corridor and the same supplied speed into the existing candidate buffer, preserving its
   track-coordinate re-embedding and historical strict flags. Compare full source-present
   and all-source-removed inputs. Report source-supported and background-only surviving
   gauge clusters. Keep current-frame/source identities through the observer.

At five frames the current count multiplier is 1.5 (strict bar 3→5, ordinary total bar
5→8 below 100 m). Keep weak-far eligibility and smear fallback unchanged. Report raw
support before the count multiplier, effective thresholds, and rejection conditions so
that a gain erased by existing safeguards is visible. DBSCAN clusters and gauge candidates
are not confirmed STOPs; no tracker run is required in this phase.

## Decision rule and controls

Require repeatable source-supported gauge candidates above 70 m (separately above 100 m),
with at least three contributing frames where accumulation is the source of the gain.
Two source points copied across identical observations are not independent evidence.
Any new background-only gauge candidates relative to the one-frame paired background
must be reported with range and shape; they invalidate a claim of a clean improvement
until a full chronological false-alarm test resolves them.

If ideal source-relative motion fails source-only support or the existing count/shape
tests, stop and report the limiting stage. If physical source alignment helps but the
production buffer does not, inspect reference-coordinate drift and smear fallback before
suggesting more frames or weaker thresholds. If both help, the next gate needs real
ego-motion/pose and unseen synthetic trajectories plus full ride/empty controls.

No new production defaults, reduced gauge/count thresholds, or post-result motion-fit
changes are authorized by this protocol. Any later experiment receives a new protocol.
