# WebUI Space Swipe Design

## Goal

Restore Arc-style two-finger Space switching in the hybrid Evo sidebar without
allowing Chromium's page-history gesture to translate or strand the sidebar
WebUI. This implements story B3 in `docs/arc-spaces-ux-reference.md` and keeps
its recommended clamp-at-the-ends behavior.

## Interaction

- The gesture must originate over the trusted sidebar WebUI. Horizontal
  gestures over page content remain available to the page and browser.
- A gesture is treated as a Space swipe only when its accumulated horizontal
  movement is dominant over vertical movement and reaches 80 CSS pixels.
- Swiping left selects the next Space in switcher order; swiping right selects
  the previous Space.
- Traversal clamps at the first and last Space. It never wraps.
- One Space may be selected per wheel-event burst. The recognizer resets after
  180 ms without another wheel event, preventing a single physical gesture
  from skipping multiple Spaces.
- Vertical and diagonal-dominant scrolling remains available to the sidebar.
- Space selection continues through the existing `selectSpace` action, so
  click and swipe share the same persistence, theme, tab-group, and snapshot
  behavior.

## Architecture

Add a small sidebar-only gesture helper under the Evo shell components. The
helper owns horizontal/vertical accumulation, the inactivity timer, endpoint
clamping, and action dispatch. `sidebar()` installs it on the sidebar root with
the current ordered Space snapshot and active Space ID.

The existing root-level `overscroll-behavior-x: none` remains the defense
against Chromium history navigation. No native Views gesture path, Space model,
or browser-process API is added.

## Failure and lifecycle behavior

- A missing active Space, fewer than two Spaces, an endpoint swipe, or a
  non-dominant gesture is a no-op.
- Re-rendering replaces the sidebar root and therefore discards the old
  listener and timer with it.
- The listener prevents default browser handling only after recognizing a
  horizontal-dominant sidebar gesture; ordinary vertical scrolling is not
  cancelled.

## Verification

- Component tests cover threshold accumulation, left/right traversal, endpoint
  clamping, vertical rejection, and one-selection-per-burst.
- The Evo shell browser suite continues to cover history-swipe suppression and
  trusted surface rendering.
- Live Evo Dev verification uses the isolated Dev profile and confirms: click
  switching still works, a sidebar trackpad gesture selects exactly one
  adjacent Space, reverse swipe returns, and the sidebar remains visible.

## Deferred

Continuous drag animation, theme cross-fade animation, gesture handling that
originates over webpage content, keyboard Space shortcuts, Space reordering,
and Space management remain outside this fix.
