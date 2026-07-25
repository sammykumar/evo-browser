# Browser Shell Functional Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the functional gaps in the approved Browser Shell epic while preserving the promoted hybrid WebUI/native architecture and leaving visual pixel tuning for the next slice.

**Architecture:** Chromium remains authoritative for tabs, tab groups, navigation classification, preferences, and the native wallpaper. The three trusted `chrome://evo-shell` WebUIs remain transient projections of one browser-process snapshot. Per-Space appearance is resolved by a focused `EvoSpaceTheme` module and applied atomically to both the snapshot and native host.

**Tech Stack:** Chromium C++/Views, trusted WebUI TypeScript, profile preferences, Chromium autocomplete classifier, Skia colors, WebUI Mocha, Chromium unit/browser tests.

## Global Constraints

- Work only in an isolated root and Chromium worktree; do not alter `/Applications/Evo.app` or the production profile.
- Use the Figma epic `docs/design/browser-shell-epic.md` as the UI authority.
- Keep the approved WebUI toolbar; the separate Cmd+L command-bar epic remains unchanged.
- Do not add folder management, Space management, drag/drop, context menus, Clear semantics, omnibox suggestions, AI panel behavior, or visual material tuning.
- Folder state is browser-owned and persisted, but this slice does not seed invented user links.
- Every behavior change follows red-green testing and lands as a focused Chromium commit before patch export.

---

### Task 1: Complete Space header and reversible sidebar controls

**Files:**
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/components/badge.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/components/space_header.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/components/toolbar.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/evo_shell.css`
- Test: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_components_test.ts`

**Interfaces:**
- Consumes: `EvoShellSnapshot.sidebarCollapsed`, `EvoShellSpace.name`, and active CSS `--accent-*` variables.
- Produces: `badge(label: string, ariaLabel?: string)`, an accent-bound `.space-avatar`, and toolbar dispatch of `{type: 'setSidebarCollapsed', collapsed: false}`.

- [ ] **Step 1: Write failing component tests**

Add tests which assert the header contains `.space-avatar`, visible text `Default`, and a collapse button; expanded toolbar has no `.sidebar-expand`; collapsed toolbar has exactly one `.sidebar-expand` which dispatches `setSidebarCollapsed(false)`.

```ts
test('SpaceHeaderUsesActiveAccentAndProfileBadge', () => {
  const view = sidebar(snapshot(), () => {});
  assertTrue(view.querySelector('.space-avatar') !== null);
  assertEquals('Default', view.querySelector('.profile-badge')!.textContent);
});

test('CollapsedToolbarCanReopenSidebar', () => {
  const state = snapshot();
  state.sidebarCollapsed = true;
  const actions: EvoShellAction[] = [];
  const view = toolbar(state, action => actions.push(action));
  (view.querySelector('.sidebar-expand') as HTMLButtonElement).click();
  assertEquals('setSidebarCollapsed', actions[0]!.type);
  assertEquals(false, actions[0]!.collapsed);
});
```

- [ ] **Step 2: Run the WebUI test and verify RED**

Run the focused WebUI component test from the configured Chromium output. Expected: failure because the avatar, profile badge, and collapsed expand button do not exist.

- [ ] **Step 3: Implement the minimal components**

Make `badge` accept display text, render the active Space avatar with `linear-gradient(135deg, var(--accent-1), var(--accent-2))`, append a `Default` badge in `spaceHeader`, and prepend the `panel-left` button only when `snapshot.sidebarCollapsed` is true.

- [ ] **Step 4: Run focused tests and verify GREEN**

Expected: the new tests and the existing component tests pass.

- [ ] **Step 5: Commit Chromium work**

```bash
git add chrome/browser/resources/evo_shell chrome/test/data/webui/evo_shell/evo_shell_components_test.ts
git commit -m "evo: complete shell header and sidebar controls"
```

---

### Task 2: Give the WebUI address field Chromium navigation semantics

**Files:**
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/components/toolbar.ts`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/BUILD.gn`
- Test: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_components_test.ts`
- Test: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_browsertest.cc`

**Interfaces:**
- Consumes: `AutocompleteClassifierFactory::GetForProfile(profile)->Classify(...)`.
- Produces: URL/query destination resolution identical to Chromium’s omnibox default match, with `AutocompleteMatch::SanitizeString` applied before classification.

- [ ] **Step 1: Write failing tests**

Add a component test which focuses `.toolbar-url-input` and asserts the entire value is selected. Add a browser test which dispatches `navigate` with a multi-word query and asserts the resulting committed URL is the profile default search provider destination rather than a synthesized host or hardcoded Google fallback.

- [ ] **Step 2: Run focused tests and verify RED**

Expected: selection range remains collapsed and navigation does not use the autocomplete classifier.

- [ ] **Step 3: Implement focus selection and classifier routing**

```ts
input.addEventListener('focus', () => input.select());
```

In the coordinator, sanitize UTF-16 input, classify with `metrics::OmniboxEventProto::INVALID_SPEC`, and load `match.destination_url` only when valid. Remove `url_formatter::FixupURL` and the hardcoded Google query URL.

- [ ] **Step 4: Run tests and verify GREEN**

Expected: URL and query inputs follow Chromium’s classifier; focus selects the whole field.

- [ ] **Step 5: Commit Chromium work**

```bash
git add chrome/browser/resources/evo_shell/components/toolbar.ts \
  chrome/browser/ui/evo_shell/evo_shell_coordinator.cc chrome/browser/ui/BUILD.gn \
  chrome/test/data/webui/evo_shell
git commit -m "evo: use Chromium navigation semantics in shell toolbar"
```

---

### Task 3: Add a browser-owned persisted folder snapshot model

**Files:**
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_types.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_types.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.cc`
- Test: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_components_test.ts`

**Interfaces:**
- Produces profile pref `evo.shell.folders`, a list of `{id,title,children:[{id,title,url}]}` dictionaries.
- Consumes that pref into `FolderSnapshot` values; invalid/missing IDs, titles, or URLs are ignored without mutating the pref.

- [ ] **Step 1: Write failing folder rendering and validation tests**

Extend the WebUI fixture with one folder and two children, including one URL subtitle. Assert the folder header, indentation container, titles, and subtitle render and that no collapse button/handler exists.

- [ ] **Step 2: Run and verify RED where the snapshot contract is incomplete**

Expected: the fixture exposes any missing folder contract or styling behavior.

- [ ] **Step 3: Register and consume the browser-owned pref**

Register `kFolders` with `RegisterListPref`. Parse only valid dictionaries into snapshots, generate favicons through the existing `FaviconUrl`, force children to pinned presentation, and leave the default list empty.

- [ ] **Step 4: Run component and workspace checks**

Expected: folder fixture passes; an empty pref produces no folder; malformed entries do not crash or render.

- [ ] **Step 5: Commit Chromium work**

```bash
git add chrome/browser/ui/evo_shell chrome/browser/resources/evo_shell/components/list_row.ts \
  chrome/test/data/webui/evo_shell/evo_shell_components_test.ts
git commit -m "evo: persist browser shell folder snapshots"
```

---

### Task 4: Implement stable per-Space theme and seed plumbing

**Files:**
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_space_theme.h`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_space_theme.cc`
- Create: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_space_theme_unittest.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_prefs.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_types.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_types.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.h`
- Modify: `evo-chromium/src/chrome/browser/ui/evo_shell/evo_shell_coordinator.cc`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view.h`
- Modify: `evo-chromium/src/chrome/browser/ui/views/frame/evo_shell_host_view.cc`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/types.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/surface.ts`
- Modify: `evo-chromium/src/chrome/browser/ui/BUILD.gn`
- Modify: `evo-chromium/src/chrome/test/BUILD.gn`
- Test: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_components_test.ts`

**Interfaces:**
- Produces `EvoSpaceTheme ResolveSpaceTheme(const PrefService&, std::string_view space_id, std::string_view space_name)` and `bool SetSpaceSeed(PrefService&, std::string_view space_id, std::string_view css_seed)`.
- `EvoSpaceTheme` contains stable `mode`, `accent1`, `accent2`, `accentCore`, and three native wallpaper colors, plus CSS serialization.
- Adds coordinator method `SetSpaceSeedForFuturePicker(space_id, seed)` without exposing a renderer action.

- [ ] **Step 1: Write failing pure theme tests**

Test exact Agent/Personal/Work/Media/Focus preset colors, stable resolution for the same Space ID regardless of tab-group order, valid `#RRGGBB` normalization and persistence, deterministic custom derivation, rejection of malformed seeds, and neutral token independence.

- [ ] **Step 2: Run unit tests and verify RED**

Expected: target and types do not exist.

- [ ] **Step 3: Implement preset and custom theme resolution**

Use the exact epic preset triplets. Default Space is Agent; names matching Personal/Work/Media/Focus choose that preset; all other IDs choose a deterministic preset using `base::PersistentHash(space_id)`. Store custom seeds in dictionary pref `evo.shell.space_themes`. Derive custom endpoints with documented deterministic RGB mixing and serialize lowercase `#rrggbb` values.

- [ ] **Step 4: Apply one resolved theme across native and WebUI surfaces**

Add active theme values to `ShellSnapshot`. `surface.ts` sets `--accent-1`, `--accent-2`, and `--accent-core` from the snapshot before rendering. Replace index-based `host_->SetTheme(...)` calls with one `ApplyActiveSpaceTheme()` invoked in the coordinator constructor, `selectSpace`, `OnTabGroupFocusChanged`, and seed changes. The host accepts the resolved native wallpaper colors directly.

- [ ] **Step 5: Run theme, component, and host tests**

Expected: all presets match the epic, external focused-group changes update the host and snapshot, and repeated switching does not alter geometry.

- [ ] **Step 6: Commit Chromium work**

```bash
git add chrome/browser/ui/evo_shell chrome/browser/ui/views/frame/evo_shell_host_view.* \
  chrome/browser/resources/evo_shell chrome/test/BUILD.gn \
  chrome/test/data/webui/evo_shell
git commit -m "evo: complete persistent per-Space theming"
```

---

### Task 5: Functional integration, Dev build, and patch-stack update

**Files:**
- Modify: `evo-browser/patches/chromium/*`
- Modify: `evo-browser/workspace.json`

**Interfaces:**
- Consumes the four focused Chromium commits.
- Produces a pinned, reproducible root patch stack and a signed isolated `Evo Dev.app`.

- [ ] **Step 1: Run generated-source checks**

```bash
vpython3 chrome/browser/ui/evo_shell/generate_evo_shell_tokens.py --check
./evo/generate-mac-app-icons.sh --check
```

- [ ] **Step 2: Build and run focused Chromium tests**

```bash
autoninja -C out/Evo unit_tests browser_tests chrome/test:chrome_test_data
out/Evo/unit_tests --gtest_filter='EvoShell*:*EvoSpaceTheme*'
out/Evo/browser_tests --gtest_filter='EvoShell*'
```

Expected: all focused tests pass with zero failures.

- [ ] **Step 3: Build and smoke-test only Evo Dev**

Run `./scripts/build-dev.sh`; verify bundle ID `com.skproductions.evo.dev`, strict code signature, isolated profile arguments, address navigation, collapse/re-expand, folder fixture rendering, and Space accent/wallpaper synchronization. Do not launch production.

- [ ] **Step 4: Export and pin the Chromium patch stack**

Run `./scripts/export-chromium-patches.sh`, update `workspace.json` to the exact Chromium HEAD and patch count, then run `./scripts/check-workspace.sh`.

- [ ] **Step 5: Run root verification**

```bash
./scripts/test.sh
git diff --check
```

- [ ] **Step 6: Commit root integration**

```bash
git add patches/chromium workspace.json
git commit -m "evo: close browser shell functional gaps"
```

The next slice is visual acceptance only: material opacity, Figma screenshots for the three states, regression surfaces, and the acceptance record. No additional browser-shell functionality enters that slice.
