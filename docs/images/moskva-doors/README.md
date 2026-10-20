# Moskva-2020 doors and lateral section navigation

The current smoother, bidirectional intermediate-page journey is documented in
[`../directional-travel/`](../directional-travel/). This gallery remains the door
material/proportion and optical-transmission reference.

## Reference and finish

The supplied [`IMG_8349.jpeg`](../references/IMG_8349.jpeg), [`IMG_8350.jpeg`](../references/IMG_8350.jpeg) and [`1591221.jpeg`](../references/1591221.jpeg) guide the
Moskva-2020 / 81-775 leaves: near-full-height glazing, narrow black enamel stiles,
layered center seals, slim red edge LEDs and a small lower glazing bead. The
previous invented recessed handles and broad metal kick plates are removed.
Every visible part travels with a leaf. The user's screen is the frame.

The requested matte glazing uses real 20px backdrop diffusion with only 26–32%
warm-neutral tint. It transmits the actual page's light, color and motion, rather
than covering it with an opaque panel. Reference photograph pixels are not used
in the application or these screenshots.

## Authored sequence

1. Close both leaves in 350ms; settle for 10ms.
2. Move the current page and shared chrome right in 160ms, with blur peaking at
   12px as it accelerates.
3. Commit the selected route in its offscreen-left pose. After a 25ms handover,
   bring it in from the left in 220ms, decelerating and clearing its 10px blur.
4. Open the leaves in 450ms once arrival finishes.

One live routed page is rendered at a time. A lazy destination waits offscreen
for up to one additional second; recovery is bounded across the full sequence.
Focus/input is inert until the overlay ends, then main regains focus. History
navigation shares the sequence; run, camera and query changes within a section
remain immediate. Reduced motion uses the existing short fade with no lateral
travel, page blur or moving leaves.

## Capture provenance

Real production-build screenshots from Chromium at `http://127.0.0.1:4178`, using
the local live API and DPR 1. Source fingerprint, exact route, viewport, leaf
bounds and computed motion samples are in `capture.json`.

- `closed-{1280,1366,1440,1920}.png`: 1280×720, 1366×768, 1440×900 and 1920×1080.
- `closing-1440.png`: 180ms into leaf travel.
- `departing-right-1440.png`: actual outgoing page, sampled 80ms into departure.
- `arriving-left-1440.png`: actual incoming page, sampled 55ms into arrival.
- `opening-1440.png`: 225ms into opening over the arrived destination.

All captures navigate from `/runs` to `/upload`. Browser time and native CSS
animation interpolation are held at the specified authored moments for repeatable
review. Images are actual browser renders, not photographic composites or static
substitutes for application pages.

## Optical and motion verification

The closed real panes are rendered over white/black backings and a 32px
checkerboard. Removing tint/diffusion supplies a positive control.

- Mean black/white backing difference is **165.72/255**, demonstrating substantial
  transmission instead of the earlier near-opaque frost.
- Checkerboard neighbor contrast drops from **119.22 to 0.67**, a **99.44%**
  attenuation of fine structure while broad light/color still passes through.
- At every desktop size the outgoing main surface has positive X displacement
  and approximately 12px blur. The incoming surface has negative X displacement
  and approximately 5px blur at its inspection sample.
- Leaves fill the exact viewport. Resting main has no transform/filter, normal
  document width and restored focus. Browser captures report no page/console errors.

The production build and all 344 frontend tests pass, including route timing,
history, immediate within-section navigation, last-request-wins behavior,
reduced motion and a bounded persistent-loading state.
All six focused browser scenarios also pass: Player-to-Runs/history at each of
the four desktop sizes, the reduced-motion fade, and actual right-departure /
left-arrival with motion blur. The design detector reports no findings.

## Visual review: pass

Reviewed every supported desktop size and all five sequence moments against the
supplied references. Tall glazing, narrow dark surrounds, center seals and red
LEDs remain legible as moving train leaves. The glass reveals the blurred page's
light and colored regions; the page swap's fine detail is obscured. Both leaves
meet across the viewport center, with no stationary framing or exposed window
corners. Arrival settles before opening, and the native page returns to a sharp,
untransformed, interactive state.
