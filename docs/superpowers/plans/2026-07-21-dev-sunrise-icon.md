# Evo Dev Sunrise Icon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate Evo Dev's signed macOS icon assets from the approved sunrise artwork with the existing `DEV` badge, while leaving production on the agent artwork and refreshing the production Dock icon cache.

**Architecture:** Keep two explicit canonical SVG inputs in Chromium's Evo branding layer. The existing deterministic generator renders production from the agent SVG and composes the badge onto the sunrise SVG for Dev, then regenerates both icon catalogs, CAR files, and ICNS fallbacks. The Dev packaging step continues to replace only the copied Dev bundle's icon resources.

**Tech Stack:** SVG, Bash, Python 3, librsvg, ImageMagick, Xcode `actool`, Chromium macOS packaging, `codesign`.

## Global Constraints

- Production remains derived from `evo-icon-4f-agent.svg`.
- Development is derived from `evo-icon-4a-sunrise.svg` and retains the existing `DEV` badge.
- Do not alter or launch the production profile.
- Do not add Evo Dev to the Dock or create a launcher wrapper.
- The Dock target remains `/Applications/Evo.app`.

---

### Task 1: Make the icon generator use separate approved sources

**Files:**
- Create: `evo-chromium/src/evo/branding/evo-icon-4a-sunrise.svg`
- Modify: `evo-chromium/src/evo/generate-mac-app-icons.sh`
- Regenerate: `evo-chromium/src/chrome/app/theme/chromium/mac/AppIcon_dev.icon/**`
- Regenerate: `evo-chromium/src/chrome/app/theme/chromium/mac/Assets_dev.xcassets/**`
- Regenerate: `evo-chromium/src/chrome/app/theme/chromium/mac/Assets_dev.car`
- Regenerate: `evo-chromium/src/chrome/app/theme/chromium/mac/app_dev.icns`

**Interfaces:**
- Consumes: approved root assets `docs/design-assets/evo-icons-svg/evo-icon-4f-agent.svg` and `evo-icon-4a-sunrise.svg`.
- Produces: deterministic production and Dev icon resources consumed by `evo/build-dev.sh`.

- [ ] **Step 1: Add the canonical sunrise SVG and select it for Dev rendering**

Add `dev_canonical_svg="${evo_dir}/branding/evo-icon-4a-sunrise.svg"`, validate both canonical files, and call `make_dev_svg "${dev_canonical_svg}" "${dev_source}"`. Keep production rendering on `canonical_svg`.

- [ ] **Step 2: Run the generator check to verify RED**

Run: `./evo/generate-mac-app-icons.sh --check`

Expected: FAIL with stale Dev outputs because the checked-in Dev catalogs still contain the agent-derived artwork.

- [ ] **Step 3: Regenerate the deterministic icon outputs**

Run: `./evo/generate-mac-app-icons.sh`

Expected: `Generated Evo production and development macOS icons.` Production outputs remain pixel-identical; Dev outputs change to sunrise plus badge.

- [ ] **Step 4: Run the generator check to verify GREEN**

Run: `./evo/generate-mac-app-icons.sh --check`

Expected: exit 0 with no stale-output diagnostics, and `app.icns` differs from `app_dev.icns`.

- [ ] **Step 5: Commit the Chromium asset change**

Commit the canonical SVG, generator change, and generated outputs as `evo: use sunrise icon for Dev`.

### Task 2: Export and validate the Chromium patch stack

**Files:**
- Modify: `patches/chromium/*.patch`
- Create: next numbered Chromium patch for the Dev sunrise commit.
- Modify: `workspace.json`

**Interfaces:**
- Consumes: the committed Chromium revision from Task 1.
- Produces: a root patch stack whose revision and patch count match the Chromium checkout.

- [ ] **Step 1: Export patches and update workspace pins**

Run: `./scripts/export-chromium-patches.sh`, then set `chromium.evoRevision` to the new Chromium commit and increment `chromium.patchCount` by one.

- [ ] **Step 2: Run workspace tests**

Run: `./scripts/test.sh`

Expected: patch validation succeeds, 15 runtime tests pass, and runtime/OpenCode type checks exit 0.

- [ ] **Step 3: Commit the root integration**

Commit the patch series and workspace pin as `evo: use sunrise icon for Dev`.

### Task 3: Package Dev and refresh the production icon cache

**Files:**
- Build output: `evo-chromium/src/out/EvoDev/Evo Dev.app`
- Existing production bundle: `/Applications/Evo.app` (content unchanged)

**Interfaces:**
- Consumes: `app_dev.icns` and `Assets_dev.car` from Task 1.
- Produces: a signed Dev bundle with the sunrise badge and a refreshed macOS cache entry for the existing production bundle.

- [ ] **Step 1: Build the isolated Dev bundle from the shared incremental output**

Run the existing Dev build with the configured shared depot-tools and runtime paths.

Expected: Chromium is incremental, the Dev bundle receives `app_dev.icns` and `Assets_dev.car`, and signing exits 0.

- [ ] **Step 2: Verify both bundle identities and signatures**

Run `codesign --verify --deep --strict` on Evo Dev and `/Applications/Evo.app`; verify bundle identifiers are `com.skproductions.evo.dev` and `com.skproductions.evo` respectively.

Expected: both bundles are valid; production remains the direct Dock target.

- [ ] **Step 3: Refresh Launch Services, Finder, and Dock caches**

Re-register `/Applications/Evo.app`, touch only the bundle directory metadata, and restart Finder and Dock. Do not launch production.

Expected: the Dock resolves `/Applications/Evo.app` with the current agent icon; no Dev Dock item is created.

- [ ] **Step 4: Final verification**

Run `git diff --check`, verify the root and Chromium repositories are clean except pre-existing unrelated untracked build dependencies, and confirm no `/Applications/Evo.app/Contents/MacOS/Evo` process is running.
