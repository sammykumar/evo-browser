# WebUI Space Swipe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a two-finger horizontal trackpad gesture originating over Evo's trusted sidebar select exactly one adjacent Space without triggering Chromium history navigation or hiding the sidebar.

**Architecture:** A focused TypeScript gesture helper attaches a non-passive `wheel` listener to each rendered sidebar root. It accumulates horizontal and vertical deltas, dispatches the existing `selectSpace` action after an 80px horizontal-dominant threshold, clamps traversal at the ordered Space endpoints, and resets after a 180ms idle period.

**Tech Stack:** Chromium trusted WebUI, TypeScript, DOM `WheelEvent`, existing Evo shell browser/Mocha tests, shared Chromium build lane.

## Global Constraints

- The gesture originates over the trusted sidebar WebUI only.
- Swipe left selects the next Space; swipe right selects the previous Space.
- Traversal clamps at the first and last Space and never wraps.
- Only one Space is selected per 180ms wheel-event burst.
- The recognition threshold is 80 CSS pixels and horizontal movement must dominate vertical movement.
- Vertical sidebar scrolling is not cancelled.
- Space selection uses the existing `{type: 'selectSpace', spaceId}` action.
- Existing `overscroll-behavior-x: none` remains in place.
- Build and test only the isolated Evo Dev lane; never modify or launch production.

---

### Task 1: Specify sidebar swipe behavior with failing component tests

**Files:**
- Modify: `evo-chromium/src/chrome/test/data/webui/evo_shell/evo_shell_components_test.ts`

**Interfaces:**
- Consumes: `sidebar(snapshot, dispatch): HTMLElement` and `EvoShellAction`.
- Produces: executable expectations for thresholding, direction, clamping, vertical rejection, and burst locking.

- [ ] **Step 1: Add a cancelable WheelEvent helper**

```ts
function wheel(
    target: HTMLElement, deltaX: number, deltaY = 0): WheelEvent {
  const event = new WheelEvent('wheel', {
    deltaX,
    deltaY,
    bubbles: true,
    cancelable: true,
  });
  target.dispatchEvent(event);
  return event;
}
```

- [ ] **Step 2: Add the five behavior tests**

```ts
test('SidebarSwipeAccumulatesToNextSpace', () => {
  const actions: EvoShellAction[] = [];
  const view = sidebar(snapshot(), action => actions.push(action));
  wheel(view, 40);
  assertEquals(0, actions.length);
  const threshold = wheel(view, 41);
  assertTrue(threshold.defaultPrevented);
  assertEquals('selectSpace', actions[0]!.type);
  assertEquals('work', (actions[0] as {type: 'selectSpace', spaceId: string}).spaceId);
});

test('SidebarSwipeRightSelectsPreviousSpace', () => {
  const state = snapshot();
  state.activeSpaceId = 'work';
  const actions: EvoShellAction[] = [];
  const view = sidebar(state, action => actions.push(action));
  wheel(view, -81);
  assertEquals('default', (actions[0] as {type: 'selectSpace', spaceId: string}).spaceId);
});

test('SidebarSwipeClampsAtSpaceEnds', () => {
  const actions: EvoShellAction[] = [];
  const view = sidebar(snapshot(), action => actions.push(action));
  wheel(view, -81);
  assertEquals(0, actions.length);
});

test('SidebarSwipeLeavesVerticalScrollAlone', () => {
  const actions: EvoShellAction[] = [];
  const view = sidebar(snapshot(), action => actions.push(action));
  const event = wheel(view, 40, 60);
  assertFalse(event.defaultPrevented);
  assertEquals(0, actions.length);
});

test('SidebarSwipeSelectsOnlyOncePerBurst', () => {
  const actions: EvoShellAction[] = [];
  const view = sidebar(snapshot(), action => actions.push(action));
  wheel(view, 81);
  wheel(view, 81);
  assertEquals(1, actions.length);
});
```

- [ ] **Step 3: Commit the test-only Chromium revision**

```bash
git -C evo-chromium/src add chrome/test/data/webui/evo_shell/evo_shell_components_test.ts
git -C evo-chromium/src commit -m "test: specify WebUI Space swipes"
```

- [ ] **Step 4: Run the component test through the shared lane and verify red**

Run:

```bash
./scripts/test-chromium.sh --target browser_tests \
  --browser-filter 'EvoShellUIBrowserTest.Components'
```

Expected: FAIL because sidebar wheel events do not dispatch `selectSpace` and are not prevented.

### Task 2: Implement and integrate the sidebar gesture recognizer

**Files:**
- Create: `evo-chromium/src/chrome/browser/resources/evo_shell/components/space_swipe.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/components/sidebar.ts`
- Modify: `evo-chromium/src/chrome/browser/resources/evo_shell/BUILD.gn`

**Interfaces:**
- Consumes: ordered `readonly EvoShellSpace[]`, active Space ID, sidebar root, and `(spaceId: string) => void`.
- Produces: `installSpaceSwipe(element, spaces, activeSpaceId, onSelect): void`.

- [ ] **Step 1: Implement the recognizer**

```ts
import type {EvoShellSpace} from '../types.js';

const THRESHOLD = 80;
const IDLE_RESET_MS = 180;

export function installSpaceSwipe(
    element: HTMLElement, spaces: readonly EvoShellSpace[],
    activeSpaceId: string, onSelect: (spaceId: string) => void): void {
  let horizontal = 0;
  let vertical = 0;
  let triggered = false;
  let resetTimer: number|undefined;

  const reset = () => {
    horizontal = 0;
    vertical = 0;
    triggered = false;
    resetTimer = undefined;
  };

  element.addEventListener('wheel', event => {
    if (resetTimer !== undefined) {
      window.clearTimeout(resetTimer);
    }
    resetTimer = window.setTimeout(reset, IDLE_RESET_MS);
    horizontal += event.deltaX;
    vertical += Math.abs(event.deltaY);

    if (Math.abs(horizontal) <= vertical) {
      return;
    }
    event.preventDefault();
    if (triggered || Math.abs(horizontal) < THRESHOLD) {
      return;
    }
    triggered = true;

    const activeIndex = spaces.findIndex(space => space.id === activeSpaceId);
    if (activeIndex < 0) {
      return;
    }
    const direction = horizontal > 0 ? 1 : -1;
    const target = spaces[activeIndex + direction];
    if (target) {
      onSelect(target.id);
    }
  }, {passive: false});
}
```

- [ ] **Step 2: Install it in `sidebar()`**

Import `installSpaceSwipe`, then call it before returning the shell:

```ts
  installSpaceSwipe(
      shell, snapshot.spaces, snapshot.activeSpaceId,
      spaceId => dispatch({type: 'selectSpace', spaceId}));
  return shell;
```

- [ ] **Step 3: Register the source in the WebUI build**

Add `"components/space_swipe.ts",` beside `space_switcher.ts` in the `ts_files` list.

- [ ] **Step 4: Run the component test and verify green**

Run the same `EvoShellUIBrowserTest.Components` command.

Expected: PASS with all prior component cases plus the five swipe cases.

- [ ] **Step 5: Commit the implementation**

```bash
git -C evo-chromium/src add \
  chrome/browser/resources/evo_shell/BUILD.gn \
  chrome/browser/resources/evo_shell/components/sidebar.ts \
  chrome/browser/resources/evo_shell/components/space_swipe.ts
git -C evo-chromium/src commit -m "feat: switch Spaces from WebUI trackpad swipes"
```

### Task 3: Verify, export, rebuild, and smoke-test Evo Dev

**Files:**
- Modify: `patches/chromium/*.patch`
- Modify: `workspace.json`

**Interfaces:**
- Consumes: committed Chromium test and implementation revisions.
- Produces: an updated root patch stack and isolated Evo Dev bundle.

- [ ] **Step 1: Run the full Evo shell browser suite**

```bash
./scripts/test-chromium.sh --target browser_tests \
  --browser-filter 'EvoShellUIBrowserTest.*'
```

Expected: all Evo shell browser tests pass, including history-swipe suppression, late-readiness recovery, accessibility-safe badges, and component swipes.

- [ ] **Step 2: Run workspace verification**

```bash
./scripts/test.sh
```

Expected: build-lane, workspace, runtime, and TypeScript checks all pass.

- [ ] **Step 3: Export and pin the Chromium revision**

```bash
./scripts/export-chromium-patches.sh
git -C evo-chromium/src rev-parse HEAD
```

Update `workspace.json` to the printed `evoRevision` and exported patch count, then run `./scripts/check-workspace.sh`.

- [ ] **Step 4: Commit the root patch stack**

```bash
git add workspace.json patches/chromium
git commit -m "feat: add WebUI Space swipe switching"
```

- [ ] **Step 5: Build the isolated Dev bundle**

```bash
./scripts/build-dev.sh
```

Expected: shared-cache incremental build completes and packages `out/EvoDev/Evo Dev.app`; production is untouched.

- [ ] **Step 6: Perform live Dev smoke verification**

Launch through `./scripts/run-dev.sh`. With two Spaces present:

1. Swipe left over the sidebar and confirm exactly one next Space becomes active.
2. Swipe right and confirm the previous Space returns.
3. Swipe toward an endpoint and confirm no wrap.
4. Scroll vertically in the sidebar and confirm it does not switch Spaces.
5. Confirm sidebar, toolbar, and right rail remain visible after every gesture.

- [ ] **Step 7: Record the final clean state**

```bash
git status --short
git -C evo-chromium/src status --short
```

Expected: both repositories are clean.
