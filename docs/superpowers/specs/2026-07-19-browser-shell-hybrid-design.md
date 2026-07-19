# Evo Browser Shell Hybrid Architecture

Status: Approved for implementation on 2026-07-19.

## Purpose

Implement the browser shell defined by `docs/design/browser-shell-epic.md` and
the Evo Design System Figma file `090VBHVLybK2LEZaOtKbcq`. The shell comprises
the left sidebar, native address bar/toolbar, right rail, floating window layout,
and per-Space theme plumbing. Figma is authoritative when it differs from prose.

This implementation is an evaluation build. The current native shell remains
available as a fallback until Sam accepts the hybrid shell after testing.

## Inputs

- Repository rules: `AGENTS.md`, including the Design and UI workflow.
- Product epic: `docs/design/browser-shell-epic.md`.
- Architecture boundary: `docs/architecture.md`.
- Figma screens: Home `19:3`, Home Sidebar Collapsed `23:91`, and Home Command
  Bar `25:25` with the command modal excluded.
- Figma organisms: Sidebar `78:136`, AddressBar `78:49`, RightRail `93:190`.
- Current Chromium shell at revision `76a7e3182c`, including vertical tabs,
  tab-group-backed Spaces, split view, Sidekick, and Agent Workspace.

## Decision

Use a balanced hybrid architecture:

- Chromium Views owns the native macOS frame, functional traffic lights,
  browser content, split view, toolbar/omnibox, outer wallpaper, window layout,
  and the trusted WebUI hosts.
- Trusted WebUI owns the visual component trees for the left sidebar and right
  rail. Both surfaces consume one shared CSS token layer and component library.
- A browser-process coordinator is the only bridge between the WebUIs and
  Chromium tab, favorite, Space, and window state.
- The native toolbar keeps Chromium's navigation, omnibox, focus, security, and
  extension behavior while receiving Evo-specific layout and styling.

An all-native shell was rejected because it would duplicate Figma's CSS token
system in custom C++ painting and make pixel fidelity expensive to maintain. An
all-WebUI shell was rejected because rebuilding the omnibox and native window
behavior would weaken mature Chromium functionality and enlarge the security
surface.

## Rollout and reversibility

Add a Chromium feature named `EvoHybridBrowserShell`.

- Evo Dev enables the feature for evaluation.
- Production behavior does not change until Sam explicitly promotes it.
- Disabled means the existing native vertical-tab sidebar and current native
  rail remain the shell.
- A WebUI initialization failure disables the hybrid surfaces for that window
  and restores the native shell. It must never leave navigation or tabs
  inaccessible.
- Do not delete the native implementation during this epic. Removal is a
  separate decision after evaluation.

The current uncommitted bottom-alignment adjustment in
`vertical_tab_strip_bottom_container.cc` is not a standalone deliverable. Its
visible result is superseded by the WebUI sidebar's flex-spacer and bottom
SpaceSwitcher. Keep it only if the fallback native shell still requires the
fix, and fold it into Feature B rather than committing it separately.

## Component boundaries

### Native shell host

Introduce an Evo-specific layout host owned by `BrowserView`, rather than
adding more inline shell classes to `browser_view.cc`. It owns:

- the aurora wallpaper and 18px outer padding;
- the 18px inter-region gaps;
- the 276px expanded sidebar host;
- the flexible content/toolbar column;
- the 72px right-rail host;
- sidebar and rail visibility transitions;
- functional macOS traffic-light placement in expanded and collapsed states;
- fallback activation when either WebUI does not become ready.

The host lays out existing browser contents rather than wrapping or replacing
`WebContents`. Split view, extension surfaces, devtools, infobars, and dialogs
continue using Chromium's existing content pipeline.

### Browser-process coordinator

Create one `EvoShellCoordinator` per browser window. It observes the browser's
`TabStripModel`, tab groups used as Spaces, vertical-tab collapse state,
navigation state, favicon updates, and Evo shell preferences.

The coordinator produces immutable snapshots and incremental events. WebUI
renderers never receive pointers, profile paths, cookies, headers, runtime
tokens, or arbitrary page data.

The initial snapshot contains:

```text
ShellSnapshot
  activeSpaceId
  sidebarCollapsed
  rightRailVisible
  activeRailTarget
  theme
  spaces[]
  favorites[]
  pinnedEntries[]
  openTabs[]
  railItems[]
```

`theme` contains only the active accent triplet, wallpaper values, and stable
mode identifier. A tab entry contains a stable tab identifier, title, visible
URL for the optional folder subtitle, favicon data source, active/loading state,
pinned state, and Space identifier. A rail item is exactly
`{icon, label, target, group}`; `group` is `top` or `bottom`.

The coordinator accepts a fixed action vocabulary:

```text
activateTab(tabId)
closeTab(tabId)
createTab()
openFavorite(favoriteId)
activateSpace(spaceId)
setSidebarCollapsed(collapsed)
setRightRailVisible(visible)
selectRailTarget(target)
```

No generic command execution or arbitrary URL dispatch is exposed. Deferred
behaviors have no handlers in this epic.

### Trusted WebUI application

Build one shared `chrome://evo-shell/` resource bundle with a surface query:

- `?surface=sidebar` renders the Sidebar organism.
- `?surface=rail` renders the RightRail organism.

The two hosts share TypeScript models, browser proxy, token CSS, icon wrapper,
atoms, and molecules. The resource bundle follows Chromium WebUI conventions
and uses no Tailwind runtime. Figma's generated React/Tailwind output is a
measurement reference only.

The sidebar WebUI reserves the Figma traffic-row space but does not draw fake
window buttons. The native macOS traffic lights are positioned over that row by
the shell host so close, minimize, and zoom retain platform behavior.

The sidebar component order is fixed by the epic:

```text
Traffic row
SpaceHeader
FAVORITES label
FavoritesGrid
PINNED label
Pinned tabs and static expanded folders
Clear divider
New Tab
Open tabs
Flexible spacer
SpaceSwitcher
```

`Clear` renders as a hoverable control but has no action because its semantics
are deferred. Folder children render expanded with no collapse handler.
Favorites can be opened but cannot be added, removed, or reordered. Space
creation, deletion, renaming, and reordering are absent.

The right rail renders a data-driven top group, flexible spacer, and bottom
group. Selection changes the active target. Targets whose panel behavior is
undefined update selection only; they do not fabricate a panel. Existing
Sidekick and Agent Workspace code remains intact, but the hybrid rail does not
redesign or newly open those surfaces in this epic. Panel routing waits for the
separate surface epics.

### Native address bar and toolbar

Retain `ToolbarView` and Chromium's real omnibox. Add an Evo presentation layer
that matches AddressBar `78:49`:

- 44px height, 8px radius, solid `--surface-overlay` equivalent in both sidebar
  states, and a hairline border;
- back, forward, and reload controls wired to existing commands;
- native omnibox using the Figma placeholder and typography treatment;
- a leading sidebar toggle only while the sidebar is collapsed;
- a trailing right-rail toggle;
- traffic-light inset while the sidebar is collapsed.

Autocomplete remains Chromium-owned but its redesign is deferred. The command
bar and Sidekick chip are not added to this toolbar epic.

## Token and asset system

Implement the exact primitives and semantic aliases from epic section 3 as CSS
custom properties in the shared WebUI token sheet. Native Views receives a
small typed mirror only for values needed by the outer layout and toolbar.
There is one definition file for the token values; native values are generated
or mapped from it rather than independently copied throughout C++.

Theme switching changes only:

- `--accent-1`;
- `--accent-2`;
- `--accent-core`;
- wallpaper values.

All other semantic tokens remain stable. The Agent orb is brand-fixed and is
not recolored per Space.

Use exported Figma assets for glyphs that do not have an exact existing match.
Use Lucide assets for the epic's standardized icon set, committed locally and
rendered with `currentColor`. Never depend on Figma's expiring asset URLs at
runtime.

## State and persistence

- Existing Chromium tab and tab-group models remain authoritative.
- Existing focused tab groups remain the first implementation of Spaces.
- Sidebar collapsed state uses the existing vertical-tab state where possible.
- Rail visibility and active rail target persist per window using Evo-owned
  browser state; no renderer-local state is authoritative.
- Space accents persist by stable Space identifier in profile preferences.
- Seed-picker UI is deferred. The plumbing accepts persisted seeds and derives
  the two gradient endpoints deterministically.

Renderer reloads request a fresh complete snapshot. Browser state continues
without interruption while a surface reloads.

## Error handling

- Before readiness, each WebUI host renders its tokenized base surface without
  interactive data.
- Invalid identifiers and actions are rejected in the browser process and do
  not mutate state.
- Missing favicons use Chromium's globe fallback without failing a snapshot.
- A destroyed tab or Space between render and click produces a no-op followed
  by a fresh snapshot.
- WebUI crashes or readiness timeouts activate the native fallback for the
  affected window and record a diagnostic message without profile data.
- Toolbar and navigation remain functional even if both WebUI surfaces fail.

## Delivery slices

Work is committed in the epic's A-through-E order, with the token foundation
included in the first slice that consumes it:

1. Foundation and Feature A: tokens, assets, feature flag, native layout host,
   wallpaper, WebUI resource skeleton, and fallback behavior.
2. Feature B: sidebar atoms through organism, coordinator tab/Space/favorite
   snapshot, actions, collapse state, and bottom SpaceSwitcher.
3. Feature C: native address-bar presentation, navigation controls, and both
   shell toggles.
4. Feature D: data-driven right rail, selection persistence, and existing
   Sidekick/Agent Workspace targets where already defined.
5. Feature E: per-Space accent persistence, deterministic seed derivation, and
   live theme/wallpaper switching.

Each slice updates the Chromium component repository first. After component
verification, export the Chromium patch stack and update the root workspace
pin. Never commit `out/`, profiles, generated runtime state, or Chromium source
to the root repository.

## Testing

### Unit and component tests

- CSS/token contract tests verify every epic token and each accent mode.
- WebUI component tests cover default/active/loading tab states, folder
  subtitles, six-column favorite wrapping, bottom-pinned SpaceSwitcher,
  data-driven rail grouping, and collapsed/expanded rendering.
- Coordinator tests cover initial snapshot construction, event ordering, stale
  identifiers, Space filtering, theme changes, and the exact action allowlist.
- Native layout tests cover all combinations of sidebar expanded/collapsed and
  rail shown/hidden without horizontal content drift.
- Toolbar tests cover navigation enabled states and conditional toggle
  placement.

### Browser integration tests

- A real tab activation, close, and new-tab action round-trips through WebUI.
- Space selection filters visible tabs and updates accent-bound UI.
- Sidebar collapse moves traffic lights and exposes the toolbar toggle.
- Rail selection preserves exactly one active target per window.
- Killing or failing an Evo shell WebUI restores the native fallback.
- Split view, extension pages, infobars, and devtools still lay out correctly.

### Visual acceptance

Build and launch only `Evo Dev.app` with the mock keychain and development
profile. Capture the three target states at the Figma frame dimensions and
compare them against nodes `19:3`, `23:91`, and `25:25` with the command modal
excluded from this epic. Acceptance requires the shell regions, spacing,
radii, materials, typography, icons, and state placement to match Figma and no
intermittent horizontal shift during repeated layout, navigation, and Space
switches.

Run from the root worktree:

```bash
./scripts/check-workspace.sh
./scripts/test.sh
./scripts/build-dev.sh
./scripts/run-dev.sh
```

Never launch, reset, migrate, or automate `/Applications/Evo.app` or the
production `Evo Chromium` profile.

## Explicitly deferred

The implementation stops at epic section 9. It does not add context menus,
drag/reorder, folder collapsing, favorites management, Clear semantics,
omnibox suggestions redesign, new-tab content, command palette behavior,
AI-panel design, Space management, keyboard-shortcut polish, light mode, or
non-macOS window styling.
