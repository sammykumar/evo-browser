# Evo Hybrid Browser Shell Implementation Plan

> **Execution note:** Follow this plan slice by slice. Complete the red/green tests and commit the Chromium component at each Feature A–E checkpoint before exporting patches or changing the root pin.

**Goal:** Replace Evo Dev's current shell with the approved Figma-matched hybrid shell while retaining the existing native shell as a safe per-window fallback.

**Architecture:** Chromium Views continues to own the macOS frame, traffic lights, browser content, split view, toolbar, and omnibox. Two trusted `chrome://evo-shell/` WebUI instances render the left sidebar and right rail. A per-window browser-process coordinator is the only state/action bridge. A generated token contract keeps WebUI CSS and the small native color/layout mirror synchronized.

**Technology:** Chromium Views, `views::WebView`, trusted Chromium WebUI, TypeScript, CSS custom properties, `base::Value`, `TabStripModel`, `PrefService`, GoogleTest, `web_ui_mocha_test`, and Chromium browser tests.

**Authoritative inputs:** `AGENTS.md`, `docs/design/browser-shell-epic.md`, `docs/architecture.md`, `docs/superpowers/specs/2026-07-19-browser-shell-hybrid-design.md`, and Figma file `090VBHVLybK2LEZaOtKbcq`. Figma wins when these disagree.

**Development boundary:** Work only in `evo-chromium/src`, then export the patch stack into the root repository. Build and launch only `Evo Dev.app` with the mock keychain and development profile. Never touch `/Applications/Evo.app` or the production profile.

---

## Contract used by every slice

The browser process sends one immutable snapshot to either surface:

```ts
export type EvoShellSurface = 'sidebar'|'rail';
export type EvoRailGroup = 'top'|'bottom';

export interface EvoThemeSnapshot {
  modeId: string;
  accent1: string;
  accent2: string;
  accentCore: string;
  wallpaper: string;
}

export interface EvoSpaceSnapshot {
  id: string;
  name: string;
  profileLabel: string;
  active: boolean;
}

export interface EvoFavoriteSnapshot {
  id: string;
  title: string;
  faviconUrl: string;
}

export interface EvoTabSnapshot {
  id: number;
  title: string;
  visibleUrl: string;
  faviconUrl: string;
  active: boolean;
  loading: boolean;
  pinned: boolean;
  spaceId: string;
}

export interface EvoPinnedFolderSnapshot {
  kind: 'folder';
  id: string;
  title: string;
  children: EvoTabSnapshot[];
}

export interface EvoRailItemSnapshot {
  icon: string;
  label: string;
  target: string;
  group: EvoRailGroup;
  active: boolean;
}

export interface EvoShellSnapshot {
  activeSpaceId: string;
  sidebarCollapsed: boolean;
  rightRailVisible: boolean;
  activeRailTarget: string;
  theme: EvoThemeSnapshot;
  spaces: EvoSpaceSnapshot[];
  favorites: EvoFavoriteSnapshot[];
  pinnedTabs: EvoTabSnapshot[];
  pinnedFolders: EvoPinnedFolderSnapshot[];
  openTabs: EvoTabSnapshot[];
  railItems: EvoRailItemSnapshot[];
}
```

The WebUI may send only these commands:

```ts
type EvoShellAction =
  | {type: 'activateTab', tabId: number}
  | {type: 'closeTab', tabId: number}
  | {type: 'createTab'}
  | {type: 'openFavorite', favoriteId: string}
  | {type: 'activateSpace', spaceId: string}
  | {type: 'setSidebarCollapsed', collapsed: boolean}
  | {type: 'setRightRailVisible', visible: boolean}
  | {type: 'selectRailTarget', target: string};
```

There is deliberately no generic command name, generic URL navigation, Clear action, folder action, reorder action, or Space-management action.

---

## Task 1: Feature A foundation — flag, generated tokens, and trusted WebUI skeleton

**Files:**

- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_features.h`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_features.cc`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_tokens.json`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/generate_evo_shell_tokens.py`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/generate_evo_shell_tokens_test.py`
- Create generated: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_tokens.h`
- Create generated: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell_tokens.css`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/BUILD.gn`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.html`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.css`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/icons.ts`
- Create: `evo-chromium/src/chrome/browser/ui/webui/evo_shell/BUILD.gn`
- Create: `evo-chromium/src/chrome/browser/ui/webui/evo_shell/evo_shell_ui.h`
- Create: `evo-chromium/src/chrome/browser/ui/webui/evo_shell/evo_shell_ui.cc`
- Modify: `evo-chromium/src/chrome/browser/resources/BUILD.gn`
- Modify: `evo-chromium/src/chrome/browser/ui/webui/BUILD.gn`
- Modify: `evo-chromium/src/chrome/browser/ui/webui/chrome_web_ui_configs.cc`
- Modify: `evo-chromium/src/chrome/common/webui_url_constants.h`
- Modify: `evo-chromium/src/chrome/test/data/webui/BUILD.gn`
- Create: `evo-chromium/src/chrome/test/data/webui/evo_shell/BUILD.gn`
- Create: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_tokens_test.ts`
- Create: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_browsertest.cc`
- Copy canonical source: `evo-browser/docs/design-assets/evo-icons-svg/evo-icon-4f-agent.svg`
- Create: `evo-chromium/src/evo/branding/evo-icon-4f-agent.svg`
- Create: `evo-chromium/src/evo/generate-mac-app-icons.sh`
- Modify: `evo-chromium/src/chrome/app/theme/chromium/mac/AppIcon.icon/icon.json`
- Create: `evo-chromium/src/chrome/app/theme/chromium/mac/AppIcon.icon/Assets/EvoAgent.svg`
- Create: `evo-chromium/src/chrome/app/theme/chromium/mac/AppIcon_dev.icon/icon.json`
- Create: `evo-chromium/src/chrome/app/theme/chromium/mac/AppIcon_dev.icon/Assets/EvoAgentDev.svg`
- Modify generated fallback files: `evo-chromium/src/chrome/app/theme/chromium/mac/Assets.xcassets/AppIcon.appiconset/*`
- Create generated dev fallback catalog: `evo-chromium/src/chrome/app/theme/chromium/mac/Assets_dev.xcassets/**`
- Modify generated: `evo-chromium/src/chrome/app/theme/chromium/mac/app.icns`
- Modify generated: `evo-chromium/src/chrome/app/theme/chromium/mac/Assets.car`
- Create generated: `evo-chromium/src/chrome/app/theme/chromium/mac/app_dev.icns`
- Create generated: `evo-chromium/src/chrome/app/theme/chromium/mac/Assets_dev.car`
- Modify: `evo-chromium/src/evo/build-dev.sh`

### 1.1 Write failing token-generation tests

- [ ] Add Python tests that load `evo_shell_tokens.json` and assert every primitive, semantic alias, spacing, radius, typography, elevation, and all five Space accent modes from epic §3 exist.
- [ ] Assert generated CSS uses the exact custom-property names from the epic.
- [ ] Assert generated C++ exposes only the native values needed by layout/toolbar: outer inset `18`, inter-region gap `18`, sidebar width `276`, rail width `72`, toolbar height `44`, radii `8/10/14`, and native surface/hairline colors.
- [ ] Assert changing a Space mode changes only the accent triplet and wallpaper output.

Run:

```bash
cd evo-chromium/src
vpython3 chrome/browser/ui/evo_shell/generate_evo_shell_tokens_test.py
```

Expected: FAIL because the token source and generator do not exist yet.

### 1.2 Implement the canonical token source and generator

- [ ] Put all authoritative values in `evo_shell_tokens.json`; do not duplicate raw color or spacing literals in application files.
- [ ] Generate `evo_shell_tokens.css` with primitive variables, semantic aliases, and `[data-theme-mode="..."]` accent/wallpaper variables.
- [ ] Generate `evo_shell_tokens.h` with typed `inline constexpr` native metrics and color constants.
- [ ] Add `--check` mode that exits nonzero when either generated file differs from the JSON source.
- [ ] Add locally stored Lucide path data in `icons.ts` for exactly the epic §3.7 set. Render inline SVG with `fill="none"`, `stroke="currentColor"`, `stroke-width="2"`, and no network asset dependency.

Run the Python test again. Expected: PASS.

### 1.3 Register the feature and trusted WebUI

- [ ] Declare `evo::features::kEvoHybridBrowserShell`, disabled by default.
- [ ] Add a temporary Evo Dev enablement in the existing Evo development command-line setup; do not enable it for production launches. Locate the existing development-lane switch logic with `rg -n "Evo Chromium Dev|mock-keychain|EvoDev" chrome` and add the flag there rather than keying behavior on an arbitrary profile path.
- [ ] Register `chrome://evo-shell/` using the same resource and controller pattern as `chrome://evo-ai/`.
- [ ] Parse `?surface=sidebar|rail` in TypeScript; reject any other value by rendering an inert error surface.
- [ ] Render the tokenized empty sidebar/rail base surfaces and emit `evo-shell-ready` only after CSS and the root component are installed.

### 1.4 Add WebUI contract tests

- [ ] Use `build_webui_tests("build")` under `chrome/test/data/webui/evo_shell`.
- [ ] Test that every required CSS token resolves, both valid surface query values render, invalid values stay inert, and SVG icons inherit `currentColor`.

Run:

```bash
autoninja -C out/EvoDev chrome/test:chrome_test_data browser_tests
out/EvoDev/browser_tests --gtest_filter='EvoShellUIBrowserTest*'
```

Expected: PASS.

### 1.5 Replace the macOS app icon from the approved design asset

- [ ] Copy `/Users/samkumar/Development/SK-Productions-LLC/evo-browser/docs/design-assets/evo-icons-svg/evo-icon-4f-agent.svg` byte-for-byte into this worktree's `docs/design-assets/evo-icons-svg/` and into Chromium's `evo/branding/` directory. Treat that SVG as the canonical artwork; do not redraw or simplify it.
- [ ] Add `evo/generate-mac-app-icons.sh` that uses the locally available `rsvg-convert`, ImageMagick, Chromium's `tools/mac/icons/compile_car.py`, and Xcode `actool` to regenerate the production fallback PNG set, `AppIcon.icon`, `Assets.car`, and `app.icns` without network access.
- [ ] Generate a distinct development variant from the same artwork with a small, legible `DEV` corner badge. Build its parallel `AppIcon_dev.icon`, `Assets_dev.xcassets`, `Assets_dev.car`, and `app_dev.icns`; do not alter the central agent artwork.
- [ ] Add `--check` to the generator. It must render into a temporary directory and compare every checked-in output so stale or hand-edited icon artifacts fail verification.
- [ ] Update `evo/build-dev.sh` after the production app is copied: replace only `Evo Dev.app/Contents/Resources/app.icns` and `Assets.car` with `app_dev.icns` and `Assets_dev.car`, then perform the existing code-signing step. Production Chromium continues to consume `app.icns` and `Assets.car` through `chrome/BUILD.gn`.
- [ ] Verify the source SVG is 1024×1024, all fallback PNGs have their declared dimensions, both `.icns` files contain the expected icon representations, the generated asset catalogs compile without warnings, and the two final artifacts are not byte-identical.

Run:

```bash
cd evo-chromium/src
./evo/generate-mac-app-icons.sh --check
./evo/build-dev.sh
test -f "out/EvoDev/Evo Dev.app/Contents/Resources/app.icns"
codesign --verify --deep --strict "out/EvoDev/Evo Dev.app"
```

Expected: the generator check exits 0, Evo Dev builds and signs, and Finder/Dock show the new agent icon with the DEV marker. Do not install or launch the production app.

### 1.6 Commit Feature A foundation and branding

```bash
git add chrome/browser/ui/evo_shell chrome/browser/resources/evo_shell \
  chrome/browser/resources/BUILD.gn chrome/browser/ui/webui/evo_shell \
  chrome/browser/ui/webui/BUILD.gn chrome/browser/ui/webui/chrome_web_ui_configs.cc \
  chrome/common/webui_url_constants.h chrome/test/data/webui evo/branding \
  evo/generate-mac-app-icons.sh evo/build-dev.sh \
  chrome/app/theme/chromium/mac
git commit -m "evo: add browser shell token and WebUI foundation"
```

---

## Task 2: Feature A shell host — floating layout, traffic lights, and fallback

**Files:**

- Create: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view.h`
- Create: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view.cc`
- Create: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view_unittest.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/browser_view.h`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/browser_view.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/layout/browser_view_layout.h`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/layout/browser_view_tabbed_layout_impl.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/BUILD.gn`
- Modify: `evo-chromium/src/chrome/test/BUILD.gn`

### 2.1 Write failing native layout tests

- [ ] Add a table-driven `EvoShellHostViewTest` for `(sidebar expanded|collapsed) × (rail shown|hidden)`.
- [ ] Assert 18px window inset, 18px gaps, 276px sidebar, 72px rail, flexible nonnegative content width, and no one-pixel horizontal drift after ten repeated layouts.
- [ ] Assert collapsed sidebar and hidden rail each return their complete width plus gap to content.
- [ ] Assert the traffic-light reserved bounds are in the sidebar header while expanded and toolbar leading inset while collapsed.
- [ ] Assert a readiness timeout or either hosted WebUI destruction calls the fallback callback exactly once.

Run:

```bash
autoninja -C out/EvoDev unit_tests
out/EvoDev/unit_tests --gtest_filter='EvoShellHostViewTest.*'
```

Expected: FAIL because the host does not exist.

### 2.2 Implement `EvoShellHostView`

- [ ] Own two `views::WebView` children loading `chrome://evo-shell/?surface=sidebar` and `?surface=rail` with the active profile.
- [ ] Paint the generated per-Space aurora wallpaper and rounded 14px outer content frame.
- [ ] Expose `SetSidebarCollapsed(bool)`, `SetRightRailVisible(bool)`, `SetTheme(EvoNativeTheme)`, `MarkSurfaceReady(EvoShellSurface)`, and `ActivateFallback(EvoShellFallbackReason)`.
- [ ] Keep width allocation deterministic in one layout function; do not add independent x-offsets in `BrowserView` and `BrowserViewTabbedLayoutImpl`.
- [ ] Reserve but do not paint fake traffic lights; reposition the existing native caption buttons via the frame layout path.
- [ ] Use a bounded readiness timer. Before readiness show the tokenized empty surfaces; after timeout make the existing native vertical sidebar and native rail visible again.

### 2.3 Integrate the host without deleting the native shell

- [ ] Make `BrowserView` create the host only when `kEvoHybridBrowserShell` is enabled.
- [ ] Route the existing content, toolbar, split contents, infobars, devtools, and overlays through the existing layout objects; the host supplies bounds, not replacement `WebContents`.
- [ ] When hybrid is active, hide the native vertical sidebar and current native right rail only after both WebUIs signal readiness.
- [ ] On fallback, restore the native surfaces and relayout in the same task.
- [ ] Add testing accessors for the host, native fallback visibility, and traffic-light reserved bounds.

Run the unit test again. Expected: PASS.

### 2.4 Add a browser fallback test

- [ ] Add a browser test in `evo_shell_host_view_unittest.cc` only if it can stay view-local; otherwise create `evo_shell_host_view_browsertest.cc` and list it in `chrome/test/BUILD.gn`.
- [ ] Open a normal browser, wait for both surfaces, simulate sidebar WebContents destruction, and assert toolbar/content remain usable and the native shell becomes visible.

Run:

```bash
autoninja -C out/EvoDev browser_tests
out/EvoDev/browser_tests --gtest_filter='EvoShellHostBrowserTest.*'
```

Expected: PASS.

### 2.5 Commit Feature A layout

```bash
git add chrome/browser/ui/views/frame chrome/browser/ui/views/BUILD.gn chrome/test/BUILD.gn
git commit -m "evo: add hybrid browser shell host"
```

---

## Task 3: Feature B coordinator — typed snapshots and the fixed action boundary

**Files:**

- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_types.h`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_types.cc`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.h`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.cc`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator_unittest.cc`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.h`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.cc`
- Modify: `evo-chromium/src/chrome/browser/prefs/browser_prefs.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/browser_view.h`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/browser_view.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/webui/evo_shell/evo_shell_ui.h`
- Modify: `evo-chromium/src/chrome/browser/ui/webui/evo_shell/evo_shell_ui.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/BUILD.gn`
- Modify: `evo-chromium/src/chrome/test/BUILD.gn`

### 3.1 Write failing coordinator tests

- [ ] Build a test `TabStripModel` with pinned/unpinned/loading/active tabs across two focused tab groups and assert `BuildSnapshot()` matches the TypeScript contract field-for-field.
- [ ] Assert pinned tabs are absent from `openTabs`, open tabs stay in live tab order, the active group is `activeSpaceId`, and missing favicons return Chromium's globe data-source URL.
- [ ] Assert stale tab/Space/favorite identifiers are no-ops followed by a new snapshot.
- [ ] Assert the parser accepts only the eight explicit actions and rejects malformed types, wrong argument types, generic URLs, and unknown commands.
- [ ] Assert one tab-model change coalesces into one `evo-shell-snapshot-changed` event.

Run:

```bash
autoninja -C out/EvoDev unit_tests
out/EvoDev/unit_tests --gtest_filter='EvoShellCoordinatorTest.*'
```

Expected: FAIL.

### 3.2 Implement the per-window coordinator

- [ ] Construct one coordinator from `BrowserView` with `Browser*`, `Profile*`, and `EvoShellHostView*` non-owning references.
- [ ] Observe `TabStripModel`, group visual data, active navigation state, favicon/loading changes, and shell prefs.
- [ ] Serialize via explicit `ToValue()` methods in `evo_shell_types.cc`; never serialize profile paths, cookies, headers, page body, form state, or runtime credentials.
- [ ] Use Chromium's existing stable tab handles/IDs; do not use list indices as persistent identifiers.
- [ ] Model initial Favorites as a read-only profile-backed list seeded from the current Evo favorite set; opening a favorite resolves its stored ID in the browser process and never accepts a renderer-supplied URL.
- [ ] Keep folder data static/expanded and read-only for this epic.

### 3.3 Connect WebUI messages

- [ ] Add `getEvoShellSnapshot` and `dispatchEvoShellAction` handlers.
- [ ] Resolve the owning browser window from the WebUI host, then call its coordinator; do not expose a global coordinator.
- [ ] Push updates with `FireWebUIListener("evo-shell-snapshot-changed", snapshot)`.
- [ ] Require `evoShellReady(surface)` before host readiness is marked.
- [ ] Reject messages from a surface that attempts an action not used by that surface: sidebar handles tab/favorite/Space/sidebar actions; rail handles rail-selection only.

Run the coordinator tests again. Expected: PASS.

### 3.4 Commit the coordinator boundary

```bash
git add chrome/browser/ui/evo_shell chrome/browser/prefs/browser_prefs.cc \
  chrome/browser/ui/views/frame chrome/browser/ui/webui/evo_shell \
  chrome/browser/ui/views/BUILD.gn chrome/test/BUILD.gn
git commit -m "evo: bridge browser state to hybrid shell"
```

---

## Task 4: Feature B sidebar — atoms, molecules, live tabs, and bottom Spaces

**Files:**

- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/types.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/browser_proxy.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_icon.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/icon_button.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/badge.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/favicon_tile.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/section_label.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/tab_item.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/list_row.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/favorites_grid.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/space_header.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/space_switcher.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/sidebar.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.css`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/BUILD.gn`
- Create: `evo-chromium/src/chrome/test/data/webui/evo_shell/sidebar_test.ts`
- Modify: `evo-chromium/src/chrome/test/data/webui/evo_shell/BUILD.gn`
- Modify only if fallback needs it: `evo-chromium/src/chrome/browser/ui/views/tabs/vertical/vertical_tab_strip_bottom_container.cc`

### 4.1 Write failing WebUI component tests

- [ ] Test `TabItem` default, active, loading, pinned, and hover-close states; pinned items must never show close.
- [ ] Test a folder renders its header and indented children permanently expanded, including optional URL subtitle, with no collapse handler.
- [ ] Test six favorite cells per row, real favicon URLs, and click dispatch by favorite ID.
- [ ] Test the exact top-to-bottom organism order from the approved design.
- [ ] Give the organism a fixed-height test viewport and assert `SpaceSwitcher` remains at the bottom while tab content grows above it.
- [ ] Test clicks dispatch only typed proxy actions for activate, close, new tab, favorite, Space, and collapse.
- [ ] Assert Clear is focusable/hoverable but dispatches no action.

Run:

```bash
autoninja -C out/EvoDev chrome/test:chrome_test_data browser_tests
out/EvoDev/browser_tests --gtest_filter='EvoShellUIBrowserTest.Sidebar*'
```

Expected: FAIL.

### 4.2 Implement atoms and molecules from Figma

- [ ] Match IconButton `72:6`, Badge `72:23`, FaviconTile `72:31`, SectionLabel `72:27`, TabItem `11:23`, ListRow `9:18`, FavoritesGrid `76:33`, SpaceHeader `77:37`, and SpaceSwitcher `77:45`.
- [ ] Use only generated tokens for color, spacing, radius, typography, and elevation.
- [ ] Use 34px favorite cells in a six-column grid, 36px tab rows, real favicon data URLs, and the globe fallback.
- [ ] Keep the brand orb fixed cyan-to-violet; only Space-bound accents use theme variables.

### 4.3 Assemble and wire Sidebar `78:136`

- [ ] Render: traffic reservation, SpaceHeader, FAVORITES, FavoritesGrid, PINNED, pinned tabs/folders, Clear divider, New Tab, open tabs, flex spacer, SpaceSwitcher.
- [ ] Subscribe to complete snapshots and render from snapshot state only; never store authoritative tab/Space state in local storage.
- [ ] Make collapse reversible and coordinate readiness/fallback through the proxy.
- [ ] Preserve native trackpad Space cycling by keeping the existing browser/window gesture handler; do not implement a competing renderer gesture recognizer.
- [ ] Decide the existing uncommitted `vertical_tab_strip_bottom_container.cc` change now: retain and commit it only if manual fallback testing shows the native fallback selector is otherwise misplaced; otherwise restore that single line because the WebUI owns bottom placement.

Run the sidebar tests again. Expected: PASS.

### 4.4 Add browser round-trip tests

- [ ] Through the sidebar WebUI, activate a tab, close an unpinned tab, create a tab, open a favorite, and switch a focused-group Space.
- [ ] Assert the resulting complete snapshot and visible browser state agree.
- [ ] Assert collapse hides the WebUI sidebar only after its state is persisted and shows the native toolbar toggle location.

Run:

```bash
autoninja -C out/EvoDev browser_tests
out/EvoDev/browser_tests --gtest_filter='EvoShellBrowserTest.Sidebar*'
```

Expected: PASS.

### 4.5 Commit Feature B

```bash
git add chrome/browser/resources/evo_shell chrome/browser/ui/evo_shell \
  chrome/browser/ui/webui/evo_shell chrome/test/data/webui/evo_shell \
  chrome/test/BUILD.gn chrome/browser/ui/views/tabs/vertical/vertical_tab_strip_bottom_container.cc
git commit -m "evo: implement Figma browser sidebar"
```

If the native fallback file was intentionally restored and has no diff, omit it from `git add`.

---

## Task 5: Feature C native toolbar — Figma presentation with real omnibox behavior

**Files:**

- Create: `evo-chromium/src/chrome/browser/ui/views/toolbar/evo_toolbar_presenter.h`
- Create: `evo-chromium/src/chrome/browser/ui/views/toolbar/evo_toolbar_presenter.cc`
- Create: `evo-chromium/src/chrome/browser/ui/views/toolbar/evo_toolbar_presenter_unittest.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/toolbar/toolbar_view.h`
- Modify: `evo-chromium/src/chrome/browser/ui/views/toolbar/toolbar_view.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/location_bar/location_bar_view.h`
- Modify: `evo-chromium/src/chrome/browser/ui/views/location_bar/location_bar_view.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/toolbar/BUILD.gn`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view.cc`
- Modify: `evo-chromium/src/chrome/test/BUILD.gn`

### 5.1 Write failing presenter tests

- [ ] Test the hybrid toolbar has a fixed 44px height, 8px radius, generated overlay surface color, and hairline border in both sidebar states.
- [ ] Test back/forward enabled state mirrors existing command state and reload dispatches the existing Chromium command.
- [ ] Test the sidebar toggle is present only when collapsed and the rail toggle reflects rail visibility.
- [ ] Test collapsed traffic-light inset does not change omnibox width across repeated layout calls.
- [ ] Test the real `LocationBarView` remains the focused primary omnibox and `SelectAll()` behavior is unchanged.

Run:

```bash
autoninja -C out/EvoDev unit_tests
out/EvoDev/unit_tests --gtest_filter='EvoToolbarPresenterTest.*'
```

Expected: FAIL.

### 5.2 Implement an Evo presentation layer around existing toolbar controls

- [ ] Keep `ToolbarView`, `LocationBarView`, `OmniboxViewViews`, and existing navigation commands; do not implement a WebUI address field.
- [ ] In hybrid mode, show only the Figma-required leading controls, real omnibox, conditional sidebar toggle, and trailing rail toggle in the Evo control group. Preserve extensions and security affordances through the location bar's existing trailing content rather than deleting functionality.
- [ ] Style the native location bar using generated native tokens. Keep background solid and identical in expanded/collapsed states.
- [ ] Set the empty-text treatment to `Search or enter URL` without changing URL/search interpretation or Chromium autocomplete behavior.
- [ ] Connect shell toggles directly to the owning coordinator; do not round-trip native toolbar clicks through renderer JavaScript.

Run the presenter tests again. Expected: PASS.

### 5.3 Add toolbar browser tests

- [ ] Navigate forward/back, reload, collapse/expand sidebar, and hide/show rail.
- [ ] Assert controls enable/disable correctly and content bounds widen/reclaim the exact region widths without intermittent horizontal shift.

Run:

```bash
autoninja -C out/EvoDev browser_tests
out/EvoDev/browser_tests --gtest_filter='EvoShellBrowserTest.Toolbar*'
```

Expected: PASS.

### 5.4 Commit Feature C

```bash
git add chrome/browser/ui/views/toolbar chrome/browser/ui/views/location_bar \
  chrome/browser/ui/views/frame/evo_shell_host_view.cc chrome/test/BUILD.gn
git commit -m "evo: restyle native toolbar for hybrid shell"
```

---

## Task 6: Feature D right rail — data-driven rendering and per-window selection

**Files:**

- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/rail_item.ts`
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/right_rail.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.css`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/BUILD.gn`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.cc`
- Create: `evo-chromium/src/chrome/test/data/webui/evo_shell/right_rail_test.ts`
- Modify: `evo-chromium/src/chrome/test/data/webui/evo_shell/BUILD.gn`
- Modify: `evo-chromium/src/chrome/test/BUILD.gn`

### 6.1 Write failing rail tests

- [ ] Feed an arbitrary fixture list of `{icon,label,target,group}` and assert order is data-driven rather than hardcoded in the component.
- [ ] Assert top items render first, bottom items remain bottom-pinned, every 60×54 item shows icon plus label, and exactly one item is active.
- [ ] Assert click sends `selectRailTarget(target)` and a subsequent snapshot owns the active state.
- [ ] Assert an unknown target is rejected by the coordinator.
- [ ] Assert selection changes alone do not open a panel or invoke Sidekick/Agent Workspace code.

Run:

```bash
autoninja -C out/EvoDev chrome/test:chrome_test_data browser_tests unit_tests
out/EvoDev/browser_tests --gtest_filter='EvoShellUIBrowserTest.RightRail*'
out/EvoDev/unit_tests --gtest_filter='EvoShellCoordinatorTest.Rail*'
```

Expected: FAIL.

### 6.2 Implement the rail organism

- [ ] Match RailItem `91:90` and RightRail `93:190` using the Figma placeholder fixture from the browser process, not literals in the component.
- [ ] Use a top group, flex spacer, and bottom group; active is ink-1 with rounded fill, inactive is ink-3.
- [ ] Persist rail visible state and active target in Evo-owned per-window/session browser state. Renderer state is a transient projection only.
- [ ] Keep existing Sidekick and Agent Workspace implementation intact. Undefined targets update selection only, as approved.
- [ ] Hide/show the rail via the native toolbar action and return its exact 72px plus gap to content.

Run the rail tests again. Expected: PASS.

### 6.3 Add one browser persistence test

- [ ] Select a second rail target, reload the rail WebUI, and assert the snapshot restores exactly that target without opening a surface.
- [ ] Hide and show the rail and assert the active target remains selected.

Run:

```bash
autoninja -C out/EvoDev browser_tests
out/EvoDev/browser_tests --gtest_filter='EvoShellBrowserTest.RightRail*'
```

Expected: PASS.

### 6.4 Commit Feature D

```bash
git add chrome/browser/resources/evo_shell chrome/browser/ui/evo_shell \
  chrome/test/data/webui/evo_shell chrome/test/BUILD.gn
git commit -m "evo: implement data-driven browser right rail"
```

---

## Task 7: Feature E per-Space accents and wallpaper

**Files:**

- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_space_theme.h`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_space_theme.cc`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_space_theme_unittest.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view.cc`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.ts`
- Create: `evo-chromium/src/chrome/test/data/webui/evo_shell/theme_test.ts`
- Modify: `evo-chromium/src/chrome/test/data/webui/evo_shell/BUILD.gn`
- Modify: `evo-chromium/src/chrome/test/BUILD.gn`

### 7.1 Write failing derivation and persistence tests

- [ ] Test exact Agent, Personal, Work, Media, and Focus preset triplets from epic §3.3.
- [ ] Test a custom seed is normalized, persisted by stable Space ID, and deterministically derives accent-1/accent-2/core plus wallpaper.
- [ ] Test sychronous switching changes only the four theme outputs; all neutral/semantic tokens remain byte-identical.
- [ ] Test a deleted/unknown Space seed is ignored and the stable mode default is used.
- [ ] Test AgentOrb styles do not consume Space accent variables.

Run:

```bash
autoninja -C out/EvoDev unit_tests chrome/test:chrome_test_data browser_tests
out/EvoDev/unit_tests --gtest_filter='EvoSpaceThemeTest.*'
out/EvoDev/browser_tests --gtest_filter='EvoShellUIBrowserTest.Theme*'
```

Expected: FAIL.

### 7.2 Implement theme plumbing without a picker UI

- [ ] Store a dictionary pref keyed by stable Space ID with normalized seed and mode.
- [ ] Derive colors in browser process using one deterministic color transform documented in `evo_space_theme.cc`; serialize final CSS colors in the snapshot.
- [ ] Apply theme variables to both WebUI roots and native wallpaper/toolbar in one coordinator update before relayout, preventing mixed-theme frames.
- [ ] Leave a typed `SetSpaceSeed(space_id, seed)` browser-process method for the future picker, but do not expose it as a WebUI action in this epic.

Run all theme tests again. Expected: PASS.

### 7.3 Add live switching browser test

- [ ] Switch among at least three Spaces and assert sidebar, rail, active-tab treatment, and native wallpaper all report the same mode in the same update.
- [ ] Repeat switching and layout ten times and assert content x/width do not change.

Run:

```bash
autoninja -C out/EvoDev browser_tests
out/EvoDev/browser_tests --gtest_filter='EvoShellBrowserTest.SpaceTheme*'
```

Expected: PASS.

### 7.4 Commit Feature E

```bash
git add chrome/browser/ui/evo_shell chrome/browser/ui/views/frame/evo_shell_host_view.cc \
  chrome/browser/resources/evo_shell chrome/test/data/webui/evo_shell chrome/test/BUILD.gn
git commit -m "evo: theme browser shell per Space"
```

---

## Task 8: Integration, visual acceptance, patch export, and PR

**Files:**

- Modify as needed for test-only fixes: files owned by Tasks 1–7
- Modify: `evo-browser/workspace.json`
- Modify: `evo-browser/patches/chromium/series`
- Create/update: exported patch files under `evo-browser/patches/chromium/`
- Create: `evo-browser/docs/testing/browser-shell-visual-acceptance.md`
- Create: `evo-browser/docs/design-assets/evo-icons-svg/evo-icon-4f-agent.svg`

### 8.1 Run focused and repository verification

- [ ] Verify generated tokens are current:

```bash
cd evo-chromium/src
vpython3 chrome/browser/ui/evo_shell/generate_evo_shell_tokens.py --check
./evo/generate-mac-app-icons.sh --check
```

- [ ] Run all focused tests:

```bash
autoninja -C out/EvoDev unit_tests browser_tests chrome/test:chrome_test_data
out/EvoDev/unit_tests --gtest_filter='EvoShell*:*EvoToolbar*:*EvoSpaceTheme*'
out/EvoDev/browser_tests --gtest_filter='EvoShell*'
```

- [ ] From the root worktree run:

```bash
./scripts/check-workspace.sh
./scripts/test.sh
./scripts/build-dev.sh
```

Expected: every command exits 0. Do not claim completion from compile progress; record the final exit status.

### 8.2 Regression-test Chromium-owned surfaces

- [ ] In Evo Dev, test a normal page, a `chrome://` page, an extension page, split view, an infobar, devtools docked/undocked, fullscreen exit, and a popup window.
- [ ] Confirm Evo Dev shows the new agent icon with the DEV badge in Finder, Dock, app switcher, and About surface; inspect the built bundle rather than the production installation.
- [ ] Kill/reload each shell WebUI and confirm native fallback restores tabs/navigation.
- [ ] Repeat navigation, window resize, sidebar collapse, rail hide, and Space switch; confirm no intermittent horizontal shift.
- [ ] Confirm Chrome extensions and production-profile data were never touched.

### 8.3 Capture the three Figma acceptance states

- [ ] Launch only with `./scripts/run-dev.sh`.
- [ ] Capture expanded `19:3`, collapsed `23:91`, and command-bar screen `25:25` with the command modal excluded.
- [ ] Compare region widths, 18px inset/gaps, radii, material opacity, toolbar height, typography, icon placement, traffic-light placement, bottom SpaceSwitcher, and rail grouping.
- [ ] Record screenshots, Figma node IDs, known pixel deltas, and pass/fail in `docs/testing/browser-shell-visual-acceptance.md`.
- [ ] Stop and ask Sam rather than inventing behavior if Figma exposes a design ambiguity that affects structure or behavior.

### 8.4 Confirm every deferred behavior remains absent

- [ ] Search the implementation for handlers or UI for context menus, drag/reorder, folder collapse, favorites editing, Clear execution, custom omnibox suggestions, new-tab content, command palette, AI panel redesign, Space management, keyboard polish, light mode, and Windows/Linux custom chrome.
- [ ] Confirm right-rail data is replaceable and undefined targets are selection-only.
- [ ] Confirm no Tailwind runtime, Figma CDN URL, renderer-supplied arbitrary URL action, profile path, runtime bearer token, cookie, header, page body, hidden field, or form value enters the shell bridge.

### 8.5 Export component work and update the root pin

- [ ] Confirm the Chromium worktree contains only intended committed changes:

```bash
cd evo-chromium/src
git status --short
git log --oneline --decorate -8
```

- [ ] From root, export and validate:

```bash
./scripts/export-chromium-patches.sh
./scripts/check-workspace.sh
./scripts/test.sh
git diff --check
```

- [ ] Review `workspace.json`, patch-series order, and root diff. Ensure Chromium source, `out/`, profiles, and runtime state are absent.
- [ ] Commit the root patch export and visual acceptance record:

```bash
git add workspace.json patches/chromium docs/testing/browser-shell-visual-acceptance.md \
  docs/design-assets/evo-icons-svg/evo-icon-4f-agent.svg
git commit -m "feat(shell): integrate hybrid Chromium browser shell"
```

### 8.6 Open the PR with an explicit story map

- [ ] PR summary maps A1–A3, B1–B10, C1–C5, D1–D3, and E1–E2 to the five Chromium commits.
- [ ] PR architecture section records the hybrid Views/WebUI decision and per-window fallback.
- [ ] PR test section lists exact successful commands and links the three visual captures.
- [ ] PR deferred section reproduces epic §9 and states that undefined rail targets are selection-only.
- [ ] PR rollout section says Evo Dev evaluation only; production promotion requires Sam's explicit acceptance.

---

## Final self-review checklist

### Story-to-task coverage

| Epic stories | Implemented and verified in |
| --- | --- |
| A1, A2, A3 | Tasks 1–2: tokens, wallpaper, three-region host, native traffic lights, fallback |
| B1, B2, B3, B4, B5 | Tasks 3–4: coordinator snapshot, SpaceHeader, FavoritesGrid, labels, tabs, static folder |
| B6, B7, B8, B9, B10 | Task 4: inert Clear, New Tab, open tabs, bottom switcher, collapse/expand |
| C1, C2, C3, C4, C5 | Task 5: native navigation, omnibox, conditional sidebar toggle, rail toggle, solid treatment |
| D1, D2, D3 | Task 6: data-driven rail, browser-owned selection, rail visibility |
| E1, E2 | Task 7: preset accents, persisted seed API, deterministic derivation, live theme update |
| Epic §9 | Task 8.4: explicit absence/security scan and PR deferred list |

- [ ] Confirm each table row has a passing focused test and evidence in the PR.

- [ ] Feature A: floating wallpaper, three-column layout, native traffic lights, all visibility combinations, fallback.
- [ ] Feature B: exact organism order, real favicons, pinned/open separation, static folder, inert Clear, New Tab, bottom Space dots, reversible collapse.
- [ ] Feature C: native back/forward/reload, real omnibox, conditional sidebar toggle, rail toggle, solid address bar.
- [ ] Feature D: 72px data-driven rail, icon+label, one active selection, top/bottom groups, no fabricated panels.
- [ ] Feature E: all presets, persisted seed plumbing, deterministic derivation, atomic live update, fixed brand orb.
- [ ] Security: fixed typed action vocabulary; no arbitrary renderer command or URL; no browser secrets or page data.
- [ ] Reversibility: feature off retains existing native shell; WebUI failure restores it per window.
- [ ] Scope: every epic §9 item is absent and documented.
- [ ] Process: component commits exist A→E, exported patches match, root pin validates, only Evo Dev was built/tested.
- [ ] Branding: the supplied SVG is canonical, production artifacts use it, and Evo Dev uses the clearly badged derivative.
