# About the System — decluttered reading view

The user's correction asks for fewer competing elements/icons and text that fits.
The page now leads with the purpose, a quiet text workflow and all four readable
decision explanations. The seven large stage icons, repeated question-mark
buttons, colored metric cards and cramped lower dashboard grid are removed.

Native expandable sections retain the complete stage explanations, six historical
measurement values with their conditions, copyable ROS commands and UDP setup,
web launch/server versions/features, and team responsibilities. Documentation
links stay directly reachable. The default page has no visible SVG icons; expanded
command-copy buttons retain their action icons. Enter/Space toggles details and
the main page scrolls naturally as content grows.

## Screenshot provenance

Real production-build screenshots from headless Chromium at
`http://127.0.0.1:4183/about`, DPR 1, using the local live API. `capture.json`
records the time, exact frontend source fingerprint, viewport and measured bounds.

- `overview-{1280,1366,1440,1920}.png`: 1280×720, 1366×768, 1440×900 and
  1920×1080, with all reference disclosures initially closed.
- `measurements-1440.png`, `commands-1440.png`, `stand-1440.png`: reference
  element screenshots of the real expanded sections, captured at 1440×900
  desktop layout. These browser crops expose complete section content in normal
  main-page flow; additional content is reached by scrolling the page rather
  than tiny internal panels.
- `offline-1440.png`: the actual query-boundary error state after `/api/system`
  is deliberately aborted. The static introduction/docs remain available.

These are actual running application renders, not static images substituted for
the page. The page's historical measurement content is reorganized, not recomputed
or promoted to a fresh detector evaluation.

## Acceptance

- All original seven workflow explanations, four decision rules, six result
  values/conditions, documentation links, team descriptions and five ROS commands
  remain accessible. The UDP prerequisite is now a copyable command too.
- Opening details grows the page. Overflow checks inspect all visible descendants
  in the fully expanded state at every supported desktop size, rejecting horizontal
  overflow or hidden/clipped/scrolling text areas.
- The browser verifies keyboard opening/closing, exact clipboard content, dynamic
  server capabilities/versions, offline behavior, demo navigation and history.
- Long version content is checked for wrapping; the rendered default page has
  zero visible content icons versus the earlier repeated icon/help field.
- TypeScript/Vite build, frontend tests and About-focused browser scenarios are
  verified: all **354 frontend tests** and **five About browser scenarios** pass.

Visual verdict: pass. Reviewed the overview at all four desktop sizes and the
expanded measurements, commands, server information and offline state. No text
is ellipsized or clipped into fixed-height cards. Documentation remains reachable
through the main page, and full keyboard focus/copy/recovery paths are verified.
