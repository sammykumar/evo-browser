# Hybrid Evo Shell Spike Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that trusted Evo WebUI can own the complete browser chrome while Chromium retains browser-engine behavior and macOS retains native window controls.

**Architecture:** Extend the existing `chrome://evo-shell/` WebUI to a third `toolbar` surface. Extend `EvoShellHostView` to host and lay out that WebView above active browser content, and extend `EvoShellCoordinator` with a minimal typed toolbar snapshot and five navigation actions. Existing sidebars remain unchanged. Stock `ToolbarView` is hidden only while the spike feature is active.

**Tech Stack:** Chromium Views/C++, WebUI TypeScript/CSS, existing Evo shell token layer, macOS native frame.

## Global Constraints

- Work only in `/Users/samkumar/Development/SK-Productions-LLC/evo-browser-hybrid-shell-spike` on `codex/hybrid-shell-spike`.
- Build, launch, and test `Evo Dev.app` only with `Evo Chromium Dev` and mock keychain.
- Do not touch `/Applications/Evo.app`, production profile, provider credentials, runtime tokens, or extensions.
- Keep the browser bridge limited to URL/title/loading/back/forward/rail state plus navigate/back/forward/reload/toggle-rail commands.
- Preserve the existing untracked `siso_result.json` in other Chromium checkouts.

---

### Task 1: Add toolbar WebUI surface and layout contract

**Files:**
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view.h`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view_unittest.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/layout/browser_view_tabbed_layout_impl.cc`

**Interfaces:**
- Produces: `EvoShellSurface::kToolbar`, `EvoShellLayout::toolbar_bounds`, and `toolbar_web_view_for_testing()`.
- Consumes: existing `content_bounds`, 44px tokenized toolbar height, and sidebar/rail readiness lifecycle.

- [ ] **Step 1: Write a failing layout test**

Add an `EvoShellHostView::CalculateLayout` test that asserts a non-empty `toolbar_bounds` is positioned at the top of `content_bounds`, has height 44, and preserves the content region below it.

- [ ] **Step 2: Run the focused test and verify RED**

Build the smallest target containing `evo_shell_host_view_unittest.cc`. The new assertion must fail because `toolbar_bounds` and `kToolbar` do not exist.

- [ ] **Step 3: Implement the surface contract**

Add the toolbar enum value, WebView creation, transparent rounded-surface layer configuration, `surface=toolbar` URL, layout assignment, readiness state, failure behavior, and test accessor. Subtract toolbar height plus the design gap from browser-content bounds only while the hybrid shell is active.

- [ ] **Step 4: Run the focused test and verify GREEN**

Re-run the focused test; verify sidebar, rail, and toolbar bounds are non-overlapping and tokenized.

- [ ] **Step 5: Commit**

Commit Chromium changes as `evo: host WebUI toolbar surface`.

### Task 2: Add the browser-owned toolbar bridge

**Files:**
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_types.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_types.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/webui/evo_shell/evo_shell_ui.cc`
- Modify: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_browsertest.cc`

**Interfaces:**
- Produces: snapshot fields `toolbar.url`, `toolbar.title`, `toolbar.loading`, `toolbar.canGoBack`, `toolbar.canGoForward`, and `rightRailVisible`; actions `navigate`, `goBack`, `goForward`, `reload`, and `setRightRailVisible`.
- Consumes: active `WebContents`, `Browser`, `TabStripModel`, and existing snapshot notification callback.

- [ ] **Step 1: Write failing browser-side behavior tests**

Add browser tests asserting a toolbar-surface request receives the new snapshot fields and that each permitted action updates the active tab or right-rail state. Assert sidebar and rail surfaces reject toolbar-only actions.

- [ ] **Step 2: Run the browser tests and verify RED**

Build and run the smallest available Evo shell browser test target. The tests must fail because the toolbar surface and action allowlist do not exist.

- [ ] **Step 3: Implement the minimal bridge**

Populate state from the active `WebContents` and `TabStripModel`. Normalize navigation input through Chromium’s existing URL-fixup/search command path; reject empty input. Dispatch navigation commands only for the toolbar surface. Subscribe snapshot updates to tab selection, navigation, title, and loading changes.

- [ ] **Step 4: Run the browser tests and verify GREEN**

Re-run the focused browser tests. Confirm the sidebar and rail continue to accept only their existing actions.

- [ ] **Step 5: Commit**

Commit Chromium changes as `evo: bridge browser state to WebUI toolbar`.

### Task 3: Render the Figma toolbar and suppress stock toolbar chrome

**Files:**
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/address_bar.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/surface.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/types.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.css`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/BUILD.gn`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/browser_proxy.ts`
- Modify: `evo-chromium/src/chrome/browser/ui/views/toolbar/toolbar_view.cc`
- Modify: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_components_test.ts`

**Interfaces:**
- Consumes: `toolbar` snapshot data and toolbar actions from Task 2.
- Produces: a 44px `AddressBar` WebUI with Back, Forward, Reload, editable URL/search field, and right-rail toggle.

- [ ] **Step 1: Write failing WebUI component tests**

Add tests that mount `surface=toolbar`, assert exactly five controls, assert URL/title/loading state renders, and assert click/Enter events dispatch the respective typed actions.

- [ ] **Step 2: Run the WebUI tests and verify RED**

Run the Evo shell WebUI test target. The toolbar test must fail because no toolbar component or surface resolver exists.

- [ ] **Step 3: Implement the Figma address-bar component**

Render one 44px solid `--surface-overlay` control at `--radius-sm`. Use existing Evo icon primitives. Bind input Enter to `navigate`, disabled state to `canGoBack`/`canGoForward`, reload state to `loading`, and right-rail toggle to `setRightRailVisible`. Do not add autocomplete, AI, or command-palette behavior.

- [ ] **Step 4: Hide only the stock toolbar in hybrid-shell mode**

Make `ToolbarView` non-visible when the Evo toolbar surface is ready and restore it on shell fallback. Preserve hidden native toolbar ownership for browser shortcuts and existing fallback behavior.

- [ ] **Step 5: Run WebUI tests and compile target**

Run the component test target, `git diff --check`, and build `chrome`. Verify the production toolbar is unchanged when the feature is off.

- [ ] **Step 6: Commit**

Commit Chromium changes as `evo: render Figma WebUI address bar`.

### Task 4: Integrate native traffic-light placement and Dev QA

**Files:**
- Modify: macOS BrowserFrameView implementation identified by `BrowserFrameViewMac::GetCaptionButtonBounds()`.
- Modify: relevant macOS frame test.
- Modify: root `workspace.json` and Chromium patch series through export.

**Interfaces:**
- Consumes: `EvoShellHostView::traffic_light_reserved_bounds()`.
- Produces: native macOS controls placed in the sidebar-header reservation while sidebar is expanded and in the toolbar-leading reservation when collapsed.

- [ ] **Step 1: Write failing macOS frame geometry test**

Assert the hybrid-shell caption-button bounds equal the shell traffic-light reservation in expanded and collapsed sidebar states.

- [ ] **Step 2: Run the focused test and verify RED**

Build and run the smallest macOS frame test target. Confirm native caption bounds still use stock titlebar geometry.

- [ ] **Step 3: Implement native geometry consumption**

Use the active BrowserView shell layout in `BrowserFrameViewMac::GetCaptionButtonBounds()` and preserve stock behavior when the hybrid feature is disabled, during fallback, or when no shell host exists.

- [ ] **Step 4: Build and visually verify Evo Dev**

Run `DEPOT_TOOLS_DIR=/Users/samkumar/Development/SK-Productions-LLC/evo-browser/depot_tools EVO_RUNTIME_DIR=/Users/samkumar/Development/SK-Productions-LLC/evo-browser-spaces-ux/evo-runtime EVO_OPENCODE_DIR=/Users/samkumar/Development/SK-Productions-LLC/evo-browser-spaces-ux/evo-opencode ./scripts/build-dev.sh`. Launch only through the same overrides and inspect the signed Dev app.

- [ ] **Step 5: Verify acceptance**

Verify signed Dev app, `./scripts/check-workspace.sh` with component overrides, `./scripts/test.sh` with component overrides, `git diff --check`, Figma toolbar appearance, native traffic-light position, navigation commands, right-rail toggle, and the existing Dev extension profile.

- [ ] **Step 6: Export and commit**

Commit Chromium work, export the patch stack, update `workspace.json` revision and patch count, rerun workspace validation, and commit root changes as `evo: spike hybrid WebUI browser shell`.
