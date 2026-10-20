# Material and transition visual review

## Verdict: visual pass

Reviewed the real production-build Player at 1280×720, 1366×768, 1440×900 and
1920×1080, with all three decisions represented at 1440×900. Reviewed shared Upload
chrome, open side telemetry, closed/moving navigation doors and the isolated
outside-camera carriage geometry. Source fingerprints and capture provenance are
recorded with the gallery.

- Door leaves cover the exact viewport from top to bottom and meet across the
  center. Window corners are fully backed. Every visible material, seal, light,
  grip and kick plate travels with its leaf. There is no stationary doorframe.
- Neutral frosted glass keeps destination text and shapes unrecognizable while
  retaining broad ceiling reflections. Rendered contrast attenuation passes.
- Clear-coated wall/seat shells, brushed trim, polished bronze and graphite glass
  read as distinct materials; woven upholstery remains matte. The original
  display, fixed-door and foreground-rail positions are retained.
- Active image, native labels, telemetry and bottom controls remain readable and
  within the first viewport. Measured document overflow is false at every size.
- The new carriage has actual rounded geometry, discrete glazing and door leaves,
  recessed running lights, roof fairing and bogies. Its inspection screenshot is
  explicitly marked diagnostic rather than presented as a new application view.
- The final keyboard pass restores the inherited white/ink rings above control
  sheen/shadows. Source-colored image light, black baseline, exact cached neutral
  return, renderer-state restoration and disposal checks all pass.

The design detector reports no findings. The glossy finishes are brief-pinned;
the frosted panes are functional route occlusion rather than a generic glass UI.

## Functional verification

- Production TypeScript/Vite build passes, including the final focus-ring CSS.
- All 342 frontend unit/component tests pass.
- The combined Player/navigation browser run passes 21 scenarios. Three scenarios
  fail while other SwiftShader capture/probe browsers are active: Escape/history,
  fullscreen run switching and the loading/error path. All three pass in isolated
  reruns on the final production build, without application or assertion changes.
- Navigation coverage includes all four desktop sizes, exact full-height leaf
  bounds, absence of stationary framing, history, focus release and reduced motion.
- The final keyboard check covers telemetry, the selected camera, selected speed
  and primary playback controls; all retain the full inherited focus ring.
- GPU lighting/frost and geometry/texture lifetime checks pass with no browser or
  shader errors. Rendering remains on demand with the existing pixel budget.
