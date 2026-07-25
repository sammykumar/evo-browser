# Evo Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone React + Storybook component library (`evo-design-system/`) that models Evo's browser UI in a dark, balanced-hybrid visual language, ready to push to claude.ai/design via `/design-sync`.

**Architecture:** A self-contained Vite package at repo root. A single token source compiles to CSS custom properties plus a typed TS export; every component styles itself only from those variables, so swapping a Space's seed hue re-themes the whole system. Storybook is the preview and verification surface, with a toolbar control that switches the per-space accent. Components are presentational mockup parts — interactivity is limited to visual states.

**Tech Stack:** React 18, TypeScript, Vite, Storybook 8 (`@storybook/react-vite`), Vitest + `@testing-library/react`, CSS Modules + CSS custom properties.

## Global Constraints

- Package lives at `evo-design-system/` at repo root; never modify `evo-chromium/`, `patches/`, `evo-runtime/`, or `evo-opencode/`.
- React 18, TypeScript strict mode.
- **Dark-only.** No light-mode variants in v1.
- **Tokens-only styling.** No component may hardcode a color, radius, shadow, or blur value — all visual values come from CSS custom properties defined in the token layer. This is a hard review-gate on every component task.
- Default Space accent is the cyan→violet Agent gradient: `--accent-1 #57dcd6`, `--accent-2 #8f7bf3`, `--accent-core #bff4ff`.
- Neutral surfaces: `--surface-canvas #0d0f13`, `--surface-sidebar #14171d`, `--surface-panel #1a1e26`, `--surface-overlay #20242e`. Ink ramp: `#eef1f6 / #b7bec9 / #828b98 / #5b6472`.
- Radius scale `8 / 12 / 18 / 26`. Every component is verified visually against the Arc/Zen reference screenshots captured in the spec.
- Each component ships a `*.stories.tsx` file; Storybook must build cleanly (`npm run build-storybook`) after every component task.

---

## File Structure

```
evo-design-system/
  package.json
  tsconfig.json
  vite.config.ts
  vitest.config.ts
  .storybook/
    main.ts                # framework config, stories glob
    preview.tsx            # dark canvas, imports tokens.css, wraps in ThemeProvider
    accent-decorator.tsx   # toolbar globalType -> sets Space seed on decorator
  src/
    tokens/
      tokens.css           # all CSS custom properties (surfaces, ink, radius, elevation, motion, semantic)
      accent.ts            # deriveAccent(seedHue) -> {accent1, accent2, core}
      accent.test.ts
      tokens.ts            # typed TS export of token names/values
    theme/
      ThemeProvider.tsx    # sets --accent-* vars from a Space seed on a wrapper
      useSpaceAccent.ts
    test/
      renderWithTheme.tsx  # test util: render a component inside ThemeProvider
    primitives/
      Button/ Button.tsx Button.module.css Button.stories.tsx Button.test.tsx
      ... (one folder per primitive)
    shell/    ... (WindowFrame, Sidebar, TabItem, ...)
    command/  ... (CommandBar, CommandResultRow, ...)
    ai/       ... (AIPanel, Message, Composer, AgentOrb, ...)
    brand/
      assets/evo-icon.png                # copied from repo-root evo-browser-icon-1024.png
      AgentOrb.tsx AgentOrb.module.css   # renders the real icon asset (CSS orb = fallback only)
      Wordmark.tsx
    scenes/
      Window.scene.stories.tsx
      CommandBar.scene.stories.tsx
      AIPanel.scene.stories.tsx
```

---

## Task 1: Scaffold the package

**Files:**
- Create: `evo-design-system/package.json`
- Create: `evo-design-system/tsconfig.json`
- Create: `evo-design-system/vite.config.ts`
- Create: `evo-design-system/vitest.config.ts`
- Create: `evo-design-system/.storybook/main.ts`
- Create: `evo-design-system/.storybook/preview.tsx`
- Create: `evo-design-system/src/tokens/tokens.css` (placeholder body filled in Task 2)
- Create: `evo-design-system/src/index.ts`

**Interfaces:**
- Produces: an installable, buildable package. `npm run storybook`, `npm run build-storybook`, and `npm run test` all resolve.

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "evo-design-system",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "storybook": "storybook dev -p 6007",
    "build-storybook": "storybook build",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@storybook/react-vite": "^8.4.0",
    "@storybook/addon-essentials": "^8.4.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "storybook": "^8.4.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2021",
    "lib": ["ES2021", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", ".storybook"]
}
```

- [ ] **Step 3: Create `vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({ plugins: [react()] });
```

- [ ] **Step 4: Create `vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", globals: true, setupFiles: [] },
});
```

- [ ] **Step 5: Create `.storybook/main.ts`**

```ts
import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(tsx)"],
  addons: ["@storybook/addon-essentials"],
  framework: { name: "@storybook/react-vite", options: {} },
};
export default config;
```

- [ ] **Step 6: Create `.storybook/preview.tsx`** (accent decorator wired in Task 4; minimal for now)

```tsx
import type { Preview } from "@storybook/react";
import "../src/tokens/tokens.css";

const preview: Preview = {
  parameters: {
    backgrounds: { disable: true },
    layout: "centered",
  },
  decorators: [
    (Story) => (
      <div style={{ background: "var(--surface-canvas)", color: "var(--ink-1)", padding: 24, minHeight: "100vh" }}>
        <Story />
      </div>
    ),
  ],
};
export default preview;
```

- [ ] **Step 7: Create placeholder `src/tokens/tokens.css`** (real values in Task 2)

```css
:root { --surface-canvas: #0d0f13; --ink-1: #eef1f6; }
```

- [ ] **Step 8: Create `src/index.ts`**

```ts
export {};
```

- [ ] **Step 9: Install and verify**

Run: `cd evo-design-system && npm install && npm run build-storybook`
Expected: install completes; `storybook build` finishes without error (there are no stories yet — a "found 0 stories" warning is acceptable).

- [ ] **Step 10: Commit**

```bash
git add evo-design-system/package.json evo-design-system/tsconfig.json evo-design-system/vite.config.ts evo-design-system/vitest.config.ts evo-design-system/.storybook evo-design-system/src
git commit -m "chore(design-system): scaffold React + Vite + Storybook package"
```

---

## Task 2: Token source (CSS variables + typed export)

**Files:**
- Modify: `evo-design-system/src/tokens/tokens.css` (full token set)
- Create: `evo-design-system/src/tokens/tokens.ts`
- Create: `evo-design-system/src/tokens/tokens.test.ts`

**Interfaces:**
- Produces: `tokens.css` defining every neutral/ink/radius/elevation/motion/semantic variable; `tokens.ts` exporting `TOKENS` (typed record) and `SURFACES`, `INK`, `RADIUS` constants for typed access.

- [ ] **Step 1: Write the failing test** — `src/tokens/tokens.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { RADIUS, SURFACES } from "./tokens";

describe("tokens", () => {
  it("exports the four neutral surfaces", () => {
    expect(SURFACES.canvas).toBe("#0d0f13");
    expect(SURFACES.sidebar).toBe("#14171d");
    expect(SURFACES.panel).toBe("#1a1e26");
    expect(SURFACES.overlay).toBe("#20242e");
  });

  it("exports the radius scale", () => {
    expect(RADIUS).toEqual([8, 12, 18, 26]);
  });

  it("every token constant is defined as a CSS variable", () => {
    const css = readFileSync(new URL("./tokens.css", import.meta.url), "utf8");
    expect(css).toContain("--surface-canvas: #0d0f13");
    expect(css).toContain("--radius-lg: 18px");
    expect(css).toContain("--ink-1: #eef1f6");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd evo-design-system && npm test -- tokens`
Expected: FAIL — `./tokens` has no `SURFACES`/`RADIUS` export.

- [ ] **Step 3: Write `src/tokens/tokens.ts`**

```ts
export const SURFACES = {
  canvas: "#0d0f13",
  sidebar: "#14171d",
  panel: "#1a1e26",
  overlay: "#20242e",
} as const;

export const INK = {
  1: "#eef1f6",
  2: "#b7bec9",
  3: "#828b98",
  4: "#5b6472",
} as const;

export const RADIUS = [8, 12, 18, 26] as const;

export const ELEVATION = {
  e1: "0 1px 2px rgba(0,0,0,.4)",
  e2: "0 8px 24px rgba(0,0,0,.45)",
  e3: "0 24px 60px rgba(0,0,0,.55)",
} as const;

export const SEMANTIC = { danger: "#e5484d", success: "#46b578", warning: "#f2a65a" } as const;

export const TOKENS = { SURFACES, INK, RADIUS, ELEVATION, SEMANTIC } as const;
```

- [ ] **Step 4: Write full `src/tokens/tokens.css`**

```css
:root {
  /* neutral surfaces */
  --surface-canvas: #0d0f13;
  --surface-sidebar: #14171d;
  --surface-panel: #1a1e26;
  --surface-overlay: #20242e;
  --hairline: rgba(255, 255, 255, 0.08);
  --hairline-strong: rgba(255, 255, 255, 0.14);

  /* ink ramp */
  --ink-1: #eef1f6;
  --ink-2: #b7bec9;
  --ink-3: #828b98;
  --ink-4: #5b6472;

  /* default (Agent) accent — overridden per-Space by ThemeProvider */
  --accent-1: #57dcd6;
  --accent-2: #8f7bf3;
  --accent-core: #bff4ff;
  --accent-gradient: linear-gradient(135deg, var(--accent-1), var(--accent-2));
  --accent-selected: color-mix(in srgb, var(--accent-1) 22%, transparent);

  /* semantic */
  --danger: #e5484d;
  --success: #46b578;
  --warning: #f2a65a;

  /* type */
  --font-ui: -apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, system-ui, sans-serif;
  --font-mono: "SF Mono", ui-monospace, "JetBrains Mono", monospace;
  --text-display: 24px;
  --text-title: 16px;
  --text-body: 13px;
  --text-label: 11px;
  --weight-regular: 400;
  --weight-medium: 600;

  /* shape & depth */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 18px;
  --radius-xl: 26px;
  --elevation-e1: 0 1px 2px rgba(0, 0, 0, 0.4);
  --elevation-e2: 0 8px 24px rgba(0, 0, 0, 0.45);
  --elevation-e3: 0 24px 60px rgba(0, 0, 0, 0.55);
  --blur-panel: blur(18px);
  --blur-overlay: blur(26px);

  /* motion */
  --dur-fast: 120ms;
  --dur-base: 200ms;
  --dur-slow: 320ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --ease-emphasized: cubic-bezier(0.3, 0, 0, 1);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd evo-design-system && npm test -- tokens`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add evo-design-system/src/tokens
git commit -m "feat(design-system): token source (CSS vars + typed export)"
```

---

## Task 3: Per-space accent derivation

**Files:**
- Create: `evo-design-system/src/tokens/accent.ts`
- Create: `evo-design-system/src/tokens/accent.test.ts`

**Interfaces:**
- Produces: `deriveAccent(seedHue: number): { accent1: string; accent2: string; core: string }` — pure HSL math, no deps. `accent1` = seed hue, `accent2` = seed hue + 40° (wrapped), `core` = light tint. Used by `ThemeProvider` (Task 4) and the Storybook accent decorator.

- [ ] **Step 1: Write the failing test** — `src/tokens/accent.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { deriveAccent } from "./accent";

describe("deriveAccent", () => {
  it("uses the seed hue for accent1 and a +40 shift for accent2", () => {
    const a = deriveAccent(180);
    expect(a.accent1).toBe("hsl(180 68% 62%)");
    expect(a.accent2).toBe("hsl(220 66% 66%)");
    expect(a.core).toBe("hsl(180 90% 85%)");
  });

  it("wraps hue past 360", () => {
    expect(deriveAccent(340).accent2).toBe("hsl(20 66% 66%)");
  });

  it("keeps derived lightness in a legible band (55–70%)", () => {
    for (let h = 0; h < 360; h += 30) {
      const { accent1, accent2 } = deriveAccent(h);
      const l1 = Number(accent1.match(/(\d+)%\)$/)![1]);
      const l2 = Number(accent2.match(/(\d+)%\)$/)![1]);
      expect(l1).toBeGreaterThanOrEqual(55);
      expect(l1).toBeLessThanOrEqual(70);
      expect(l2).toBeGreaterThanOrEqual(55);
      expect(l2).toBeLessThanOrEqual(70);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd evo-design-system && npm test -- accent`
Expected: FAIL — `deriveAccent` not defined.

- [ ] **Step 3: Write `src/tokens/accent.ts`**

```ts
export interface Accent {
  accent1: string;
  accent2: string;
  core: string;
}

const wrap = (h: number): number => ((h % 360) + 360) % 360;

/** Derive a two-stop accent gradient + core glow from a single seed hue (0–359). */
export function deriveAccent(seedHue: number): Accent {
  const h1 = wrap(seedHue);
  const h2 = wrap(seedHue + 40);
  return {
    accent1: `hsl(${h1} 68% 62%)`,
    accent2: `hsl(${h2} 66% 66%)`,
    core: `hsl(${h1} 90% 85%)`,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd evo-design-system && npm test -- accent`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add evo-design-system/src/tokens/accent.ts evo-design-system/src/tokens/accent.test.ts
git commit -m "feat(design-system): per-space accent derivation from seed hue"
```

---

## Task 4: ThemeProvider + Storybook accent control

**Files:**
- Create: `evo-design-system/src/theme/ThemeProvider.tsx`
- Create: `evo-design-system/src/theme/useSpaceAccent.ts`
- Create: `evo-design-system/src/theme/ThemeProvider.test.tsx`
- Create: `evo-design-system/src/test/renderWithTheme.tsx`
- Modify: `evo-design-system/.storybook/preview.tsx`

**Interfaces:**
- Produces:
  - `ThemeProvider({ seedHue?: number, accent?: Accent, children })` — sets `--accent-1/2/core` (and `--accent-gradient`, `--accent-selected` inherit) as inline style on a wrapping `div`. Default seed = 187 (the Agent cyan) when neither prop given.
  - `useSpaceAccent(): Accent` — reads the current accent from context.
  - `renderWithTheme(ui, { seedHue })` — testing-library render wrapped in `ThemeProvider`.
- Consumes: `deriveAccent` (Task 3).

- [ ] **Step 1: Write the failing test** — `src/theme/ThemeProvider.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { ThemeProvider } from "./ThemeProvider";

describe("ThemeProvider", () => {
  it("sets accent CSS variables from a seed hue", () => {
    const { container } = render(
      <ThemeProvider seedHue={180}>
        <span>hi</span>
      </ThemeProvider>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.style.getPropertyValue("--accent-1")).toBe("hsl(180 68% 62%)");
    expect(el.style.getPropertyValue("--accent-2")).toBe("hsl(220 66% 66%)");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd evo-design-system && npm test -- ThemeProvider`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `src/theme/ThemeProvider.tsx` and `useSpaceAccent.ts`**

```tsx
// ThemeProvider.tsx
import { createContext, useContext, useMemo, type ReactNode, type CSSProperties } from "react";
import { deriveAccent, type Accent } from "../tokens/accent";

const DEFAULT_SEED = 187; // Agent cyan
const AccentContext = createContext<Accent>(deriveAccent(DEFAULT_SEED));

export function ThemeProvider(props: { seedHue?: number; accent?: Accent; children: ReactNode }) {
  const accent = useMemo<Accent>(
    () => props.accent ?? deriveAccent(props.seedHue ?? DEFAULT_SEED),
    [props.accent, props.seedHue],
  );
  const style = {
    "--accent-1": accent.accent1,
    "--accent-2": accent.accent2,
    "--accent-core": accent.core,
  } as CSSProperties;
  return (
    <AccentContext.Provider value={accent}>
      <div style={style}>{props.children}</div>
    </AccentContext.Provider>
  );
}

export { AccentContext };
```

```ts
// useSpaceAccent.ts
import { useContext } from "react";
import { AccentContext } from "./ThemeProvider";
export const useSpaceAccent = () => useContext(AccentContext);
```

- [ ] **Step 4: Write `src/test/renderWithTheme.tsx`**

```tsx
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";
import { ThemeProvider } from "../theme/ThemeProvider";

export function renderWithTheme(ui: ReactElement, opts?: { seedHue?: number } & RenderOptions) {
  return render(<ThemeProvider seedHue={opts?.seedHue}>{ui}</ThemeProvider>, opts);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd evo-design-system && npm test -- ThemeProvider`
Expected: PASS.

- [ ] **Step 6: Wire the Storybook accent toolbar** — replace `.storybook/preview.tsx`

```tsx
import type { Preview } from "@storybook/react";
import "../src/tokens/tokens.css";
import { ThemeProvider } from "../src/theme/ThemeProvider";

const SPACES: Record<string, number> = { Agent: 187, Perch: 32, Work: 158, Media: 338, Focus: 232 };

const preview: Preview = {
  parameters: { backgrounds: { disable: true }, layout: "centered" },
  globalTypes: {
    space: {
      description: "Per-space accent",
      defaultValue: "Agent",
      toolbar: { icon: "paintbrush", items: Object.keys(SPACES), dynamicTitle: true },
    },
  },
  decorators: [
    (Story, ctx) => (
      <ThemeProvider seedHue={SPACES[ctx.globals.space] ?? 187}>
        <div style={{ background: "var(--surface-canvas)", color: "var(--ink-1)", fontFamily: "var(--font-ui)", padding: 24, minHeight: "100vh" }}>
          <Story />
        </div>
      </ThemeProvider>
    ),
  ],
};
export default preview;
```

- [ ] **Step 7: Verify Storybook builds**

Run: `cd evo-design-system && npm run build-storybook`
Expected: builds without error.

- [ ] **Step 8: Commit**

```bash
git add evo-design-system/src/theme evo-design-system/src/test evo-design-system/.storybook/preview.tsx
git commit -m "feat(design-system): ThemeProvider + Storybook per-space accent control"
```

---

## Task 5: Button (reference component — establishes the pattern)

This task is the **pattern exemplar**. Every later component follows this exact shape: `Component.tsx` (tokens-only CSS Module), `Component.module.css`, `Component.stories.tsx` (one story per variant + uses the accent toolbar), `Component.test.tsx` (render smoke test via `renderWithTheme`).

**Files:**
- Create: `evo-design-system/src/primitives/Button/Button.tsx`
- Create: `evo-design-system/src/primitives/Button/Button.module.css`
- Create: `evo-design-system/src/primitives/Button/Button.stories.tsx`
- Create: `evo-design-system/src/primitives/Button/Button.test.tsx`

**Interfaces:**
- Produces: `Button({ variant?: "primary" | "ghost" | "subtle"; size?: "sm" | "md"; iconOnly?: boolean; children; ...button })`. `primary` fills with `--accent-gradient`.
- Consumes: tokens (Task 2), `renderWithTheme` (Task 4).

- [ ] **Step 1: Write the failing test** — `Button.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithTheme } from "../../test/renderWithTheme";
import { Button } from "./Button";

describe("Button", () => {
  it("renders its label and applies the variant class", () => {
    renderWithTheme(<Button variant="primary">Ask Evo</Button>);
    const btn = screen.getByRole("button", { name: "Ask Evo" });
    expect(btn.className).toMatch(/primary/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd evo-design-system && npm test -- Button`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `Button.module.css`** (tokens-only)

```css
.base { border: 0; border-radius: 999px; font-family: var(--font-ui); font-weight: var(--weight-medium); cursor: pointer; display: inline-flex; align-items: center; gap: 8px; transition: filter var(--dur-fast) var(--ease-standard); }
.base:hover { filter: brightness(1.08); }
.sm { padding: 6px 12px; font-size: var(--text-label); }
.md { padding: 8px 15px; font-size: var(--text-body); }
.iconOnly { padding: 8px; border-radius: var(--radius-md); }
.primary { background: var(--accent-gradient); color: #0b0d13; box-shadow: 0 4px 18px color-mix(in srgb, var(--accent-2) 35%, transparent); }
.ghost { background: rgba(255,255,255,.06); color: var(--ink-1); border: 1px solid var(--hairline); }
.subtle { background: transparent; color: var(--ink-2); }
.subtle:hover { background: rgba(255,255,255,.05); }
```

- [ ] **Step 4: Write `Button.tsx`**

```tsx
import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.css";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "subtle";
  size?: "sm" | "md";
  iconOnly?: boolean;
  children: ReactNode;
}

export function Button({ variant = "primary", size = "md", iconOnly = false, children, className, ...rest }: ButtonProps) {
  const cls = [styles.base, styles[variant], styles[size], iconOnly && styles.iconOnly, className].filter(Boolean).join(" ");
  return <button className={cls} {...rest}>{children}</button>;
}
```

- [ ] **Step 5: Write `Button.stories.tsx`**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./Button";

const meta: Meta<typeof Button> = { title: "Primitives/Button", component: Button };
export default meta;
type S = StoryObj<typeof Button>;

export const Primary: S = { args: { variant: "primary", children: "Ask Evo" } };
export const Ghost: S = { args: { variant: "ghost", children: "Cancel" } };
export const Subtle: S = { args: { variant: "subtle", children: "Skip" } };
export const Small: S = { args: { variant: "primary", size: "sm", children: "New Tab" } };
```

- [ ] **Step 6: Run test + Storybook build**

Run: `cd evo-design-system && npm test -- Button && npm run build-storybook`
Expected: test PASS; Storybook builds. Open `npm run storybook`, confirm the Primary button shows the cyan→violet gradient and re-themes when the toolbar Space changes.

- [ ] **Step 7: Commit**

```bash
git add evo-design-system/src/primitives/Button
git commit -m "feat(design-system): Button primitive (pattern exemplar)"
```

---

## Task 6: Input primitives — `Input`, `SearchField`, `IconButton`

**Files (each its own folder, following the Task 5 pattern):**
- `src/primitives/Input/` (`Input.tsx`, `.module.css`, `.stories.tsx`, `.test.tsx`)
- `src/primitives/SearchField/`
- `src/primitives/IconButton/`

**Interfaces:**
- `Input(props: InputHTMLAttributes<HTMLInputElement>)` — pill, `--surface` fill, `--hairline` border, focus ring uses `--accent-1`.
- `SearchField({ value?, placeholder?, leading?: ReactNode, onValueChange?, ...})` — `Input` + a leading icon slot; used by the command bar and sidebar.
- `IconButton({ label: string; children: ReactNode; size?: "sm" | "md" } & ButtonHTMLAttributes)` — square, `--radius-md`, `aria-label` from `label`.

- [ ] **Step 1: For each component, write the render smoke test first** (mirror Task 5 Step 1). Example — `Input.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithTheme } from "../../test/renderWithTheme";
import { Input } from "./Input";

describe("Input", () => {
  it("renders with placeholder", () => {
    renderWithTheme(<Input placeholder="Search or enter URL…" />);
    expect(screen.getByPlaceholderText("Search or enter URL…")).toBeTruthy();
  });
});
```

Write equivalent smoke tests for `SearchField` (asserts placeholder + leading slot renders) and `IconButton` (asserts `aria-label` present).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd evo-design-system && npm test -- Input SearchField IconButton`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement each component** (tokens-only CSS Modules, following the Button pattern). `Input` focus ring: `.base:focus { outline: none; border-color: var(--accent-1); box-shadow: 0 0 0 3px var(--accent-selected); }`. `SearchField` composes `Input` with a leading `<span>` slot. `IconButton` maps `label`→`aria-label`.

- [ ] **Step 4: Write one story per component** with variants (Input: default/focused-via-autofocus; SearchField: with a magnifier leading glyph; IconButton: sm/md).

- [ ] **Step 5: Run tests + Storybook build**

Run: `cd evo-design-system && npm test -- Input SearchField IconButton && npm run build-storybook`
Expected: all PASS; Storybook builds. Visually confirm the focus ring picks up the accent and re-themes per Space.

- [ ] **Step 6: Commit**

```bash
git add evo-design-system/src/primitives/Input evo-design-system/src/primitives/SearchField evo-design-system/src/primitives/IconButton
git commit -m "feat(design-system): Input, SearchField, IconButton primitives"
```

---

## Task 7: `ListRow` + states

**Files:** `src/primitives/ListRow/` (component, css, stories, test).

**Interfaces:**
- `ListRow({ leading?: ReactNode; title: string; subtitle?: string; selected?: boolean; loading?: boolean; onClick?; })`. `selected` fills with `--accent-selected` and text `--ink-1`; default text `--ink-2`; `subtitle` muted `--ink-3`; `loading` shows a shimmer on the leading slot.

- [ ] **Step 1: Write smoke test** — asserts title renders, and `selected` adds the selected class.

```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithTheme } from "../../test/renderWithTheme";
import { ListRow } from "./ListRow";

describe("ListRow", () => {
  it("renders title/subtitle and marks selection", () => {
    const { container } = renderWithTheme(<ListRow title="Google" subtitle="google.com" selected />);
    expect(screen.getByText("Google")).toBeTruthy();
    expect(screen.getByText("google.com")).toBeTruthy();
    expect((container.querySelector("[data-selected='true']"))).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test — verify it fails.** Run: `cd evo-design-system && npm test -- ListRow` → FAIL.
- [ ] **Step 3: Implement `ListRow`** (tokens-only; root element carries `data-selected={selected}`; reference: the Arc command-bar result rows and sidebar tabs).
- [ ] **Step 4: Stories** — `Default`, `Selected`, `WithSubtitle`, `Loading`.
- [ ] **Step 5: Run test + Storybook build.** Run: `cd evo-design-system && npm test -- ListRow && npm run build-storybook` → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/primitives/ListRow && git commit -m "feat(design-system): ListRow primitive with states"`

---

## Task 8: `Chip`, `Badge`, `Kbd`

**Files:** `src/primitives/Chip/`, `src/primitives/Badge/`, `src/primitives/Kbd/`.

**Interfaces:**
- `Chip({ leading?: ReactNode; children; tone?: "neutral" | "accent" })` — pill, `--hairline` border; `accent` tone tints with `--accent-selected`.
- `Badge({ children; tone?: "neutral" | "success" | "danger" | "warning" })` — small status pill using semantic tokens.
- `Kbd({ children })` — keycap, mono, `--surface-overlay` fill (e.g. `⌘K`).

- [ ] **Step 1: Smoke test each** (assert children render; `Badge` danger adds tone class). Follow Task 5 Step 1 shape.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- Chip Badge Kbd` → FAIL.
- [ ] **Step 3: Implement all three** (tokens-only).
- [ ] **Step 4: Stories** — Chip: neutral + accent + with-dot; Badge: each tone; Kbd: `⌘K`, `Esc`.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/primitives/Chip evo-design-system/src/primitives/Badge evo-design-system/src/primitives/Kbd && git commit -m "feat(design-system): Chip, Badge, Kbd primitives"`

---

## Task 9: `Toggle`, `Tooltip`, `Avatar`, `Scrim`, `Icon`

**Files:** one folder each under `src/primitives/`.

**Interfaces:**
- `Toggle({ checked: boolean; onChange?: (v: boolean) => void; label: string })` — track fills `--accent-gradient` when checked; `role="switch"`, `aria-checked`, `aria-label={label}`.
- `Tooltip({ content: string; children: ReactNode })` — CSS-only hover tooltip, `--surface-overlay`, `--elevation-e2`.
- `Avatar({ src?: string; label: string; size?: number; shape?: "circle" | "squircle" })` — space/profile mark; falls back to initials from `label`.
- `Scrim({ onClick? })` — full-bleed dimmer for modals; `background: rgba(0,0,0,.45)` + `--blur-overlay`.
- `Icon({ name: string; size?: number })` — thin wrapper rendering an inline SVG from a small local set (`chevron`, `plus`, `close`, `search`, `split`, `back`, `forward`, `reload`, `sparkle`). Ships the SVG paths inline; no icon dependency.

- [ ] **Step 1: Smoke test each** (Toggle: `role=switch` + `aria-checked` flips with prop; Tooltip: children render; Avatar: initials fallback shows "G" for label "Google"; Scrim: calls `onClick`; Icon: renders an `<svg>`).
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- Toggle Tooltip Avatar Scrim Icon` → FAIL.
- [ ] **Step 3: Implement all five** (tokens-only).
- [ ] **Step 4: Stories** for each (Toggle on/off; Tooltip hover demo; Avatar image + initials + both shapes; Scrim over a placeholder; Icon gallery of the local set).
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/primitives/Toggle evo-design-system/src/primitives/Tooltip evo-design-system/src/primitives/Avatar evo-design-system/src/primitives/Scrim evo-design-system/src/primitives/Icon && git commit -m "feat(design-system): Toggle, Tooltip, Avatar, Scrim, Icon primitives"`

---

## Task 10: `Menu` / `ContextMenu`

**Files:** `src/primitives/Menu/` (`Menu.tsx`, `MenuItem`, css, stories, test).

**Interfaces:**
- `Menu({ items: MenuItemSpec[]; open?: boolean })` where `MenuItemSpec = { label: string; icon?: ReactNode; submenu?: MenuItemSpec[]; danger?: boolean; separatorBefore?: boolean }`.
- `ContextMenu({ items, children })` — wraps `children`, opens `Menu` on right-click at pointer position.
- Reference: Arc's Space right-click menu (Change Space Icon / Rename / Edit Theme Color / Set Profile ▸ / New Folder / … / Delete Space). Submenu opens to the side; `danger` items use `--danger`.

- [ ] **Step 1: Smoke test** — `Menu` with items renders each label; a `danger` item carries the danger class; a `submenu` item renders a chevron.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- Menu` → FAIL.
- [ ] **Step 3: Implement `Menu` + `ContextMenu`** (tokens-only; `--surface-overlay`, `--elevation-e3`, `--radius-md`; submenu on hover).
- [ ] **Step 4: Stories** — `SpaceContextMenu` reproducing the Arc menu including the `Set Profile` submenu; a plain `Menu`.
- [ ] **Step 5: Run test + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/primitives/Menu && git commit -m "feat(design-system): Menu / ContextMenu primitive"`

---

## Task 11: `AgentOrb` + `Wordmark` (brand)

**Files:** `src/brand/assets/evo-icon.png` (copied from repo root), `src/brand/AgentOrb/` (`AgentOrb.tsx`, `.module.css`, `.stories.tsx`, `.test.tsx`), `src/brand/Wordmark/`.

**Interfaces:**
- `AgentOrb({ size?: number; state?: "idle" | "thinking" | "listening"; tint?: boolean })` — renders the **real exported icon** (`evo-icon.png`) at `size`. `thinking` adds a slow accent bloom pulse behind the mark (`--dur-slow`). The mark itself is the fixed brand cyan→violet; `tint` (default `false`) is the escape hatch to recolor the surrounding glow to `--accent-1/2` for non-Agent Spaces (per the spec's open question). Consumed by `AIPanelHeader`, `AskEvoRow`, `AgentStatus`.
- `Wordmark({ height?: number })` — "Evo" wordmark beside the orb.

- [ ] **Step 1: Copy the asset**

Run: `cp evo-browser-icon-1024.png evo-design-system/src/brand/assets/evo-icon.png`
(Add a Vite/TS image module declaration if needed: `declare module "*.png";` in `src/vite-env.d.ts`.)

- [ ] **Step 2: Smoke test** — `AgentOrb` renders an `<img>` (query by `data-testid="agent-orb"` with the image inside); `thinking` adds the pulsing class.

```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithTheme } from "../../test/renderWithTheme";
import { AgentOrb } from "./AgentOrb";

describe("AgentOrb", () => {
  it("renders the brand mark and reflects the thinking state", () => {
    renderWithTheme(<AgentOrb state="thinking" />);
    const orb = screen.getByTestId("agent-orb");
    expect(orb.querySelector("img")).toBeTruthy();
    expect(orb.className).toMatch(/thinking/);
  });
});
```

- [ ] **Step 3: Run — verify fail.** `cd evo-design-system && npm test -- AgentOrb` → FAIL.
- [ ] **Step 4: Implement `AgentOrb`** — an `<img src={evoIcon}>` wrapped in a positioned container with a `thinking` bloom (an accent-colored blurred halo behind the mark, sized from `size`). The `bloom`/`tint` glow reads `--accent-1/2`; the icon image is untouched (brand-fixed). Implement `Wordmark`.
- [ ] **Step 5: Stories** — orb at 3 sizes × 3 states; a `tint` variant shown under a non-Agent Space; Wordmark.
- [ ] **Step 6: Run test + Storybook build** → PASS + builds. Confirm the real icon renders crisply and the thinking bloom animates.
- [ ] **Step 7: Commit.** `git add evo-design-system/src/brand && git commit -m "feat(design-system): AgentOrb (real icon) + Wordmark brand motif"`

---

## Task 12: `WindowFrame` + `Toolbar`

**Files:** `src/shell/WindowFrame/`, `src/shell/Toolbar/`.

**Interfaces:**
- `WindowFrame({ sidebar: ReactNode; content: ReactNode; toolbar?: ReactNode })` — macOS traffic-light dots top-left, floating chrome, and the **inset content region** (`--radius-xl`, `--elevation-e2`, sits on `--surface-canvas` with the theme bleeding behind). Reference: Zen's floated content.
- `Toolbar({ onBack?, onForward?, onReload?, onSplit?, children? })` — minimal control row using `IconButton` + `Icon` (`back`, `forward`, `reload`, `split`).

- [ ] **Step 1: Smoke test** — `WindowFrame` renders the sidebar + content slots; three traffic-light dots present. `Toolbar` renders back/forward/reload/split buttons (by `aria-label`).
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- WindowFrame Toolbar` → FAIL.
- [ ] **Step 3: Implement both** (tokens-only; `WindowFrame` is layout-only, no color hardcoding; content region uses `overflow: hidden` + big radius).
- [ ] **Step 4: Stories** — `WindowFrame` with placeholder sidebar + a page screenshot placeholder in content; `Toolbar` standalone.
- [ ] **Step 5: Run test + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/shell/WindowFrame evo-design-system/src/shell/Toolbar && git commit -m "feat(design-system): WindowFrame + Toolbar shell"`

---

## Task 13: `Sidebar` + `SpaceHeader` + `SpaceSwitcher`

**Files:** `src/shell/Sidebar/`, `src/shell/SpaceHeader/`, `src/shell/SpaceSwitcher/`.

**Interfaces:**
- `Sidebar({ header?: ReactNode; children: ReactNode; footer?: ReactNode })` — `--surface-sidebar` base with a subtle per-space gradient wash (`linear-gradient` mixing `--accent-1` into the sidebar surface, low opacity — the Arc tint).
- `SpaceHeader({ name: string; profile?: string })` — Space name + profile badge (reference: Arc "Perch · Default").
- `SpaceSwitcher({ spaces: { id: string; seedHue: number }[]; activeId: string; onSelect? })` — bottom row of dots/pills, each tinted by its own seed; active is emphasized.

- [ ] **Step 1: Smoke test each** (Sidebar renders header/children/footer; SpaceHeader shows name + profile; SpaceSwitcher renders one dot per space and marks active).
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- Sidebar SpaceHeader SpaceSwitcher` → FAIL.
- [ ] **Step 3: Implement all three** (tokens-only; the gradient wash must read from `--accent-1`, never a literal).
- [ ] **Step 4: Stories** — a themed `Sidebar` with header + a few `ListRow`s + `SpaceSwitcher` footer; confirm each toolbar Space re-tints the wash.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/shell/Sidebar evo-design-system/src/shell/SpaceHeader evo-design-system/src/shell/SpaceSwitcher && git commit -m "feat(design-system): Sidebar, SpaceHeader, SpaceSwitcher"`

---

## Task 14: `FavoritesGrid` + `FavoriteTile`

**Files:** `src/shell/FavoritesGrid/`, `src/shell/FavoriteTile/`.

**Interfaces:**
- `FavoriteTile({ label: string; icon?: ReactNode; color?: string })` — rounded icon tile (reference: Zen/Arc favorites grid).
- `FavoritesGrid({ children: ReactNode; columns?: number })` — grid wrapper (default 4 columns).

- [ ] **Step 1: Smoke test** — `FavoritesGrid` renders its tiles; `FavoriteTile` shows its label and an icon slot.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- FavoritesGrid FavoriteTile` → FAIL.
- [ ] **Step 3: Implement both** (tokens-only; tiles `--radius-md`, `--surface-panel`).
- [ ] **Step 4: Stories** — a grid of 6 tiles (mix of icon + initial fallback).
- [ ] **Step 5: Run test + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/shell/FavoritesGrid evo-design-system/src/shell/FavoriteTile && git commit -m "feat(design-system): FavoritesGrid + FavoriteTile"`

---

## Task 15: `TabItem` + `TabList` + `Folder`

**Files:** `src/shell/TabItem/`, `src/shell/TabList/`, `src/shell/Folder/`.

**Interfaces:**
- `TabItem({ title: string; favicon?: ReactNode; active?: boolean; pinned?: boolean; loading?: boolean; onClose? })` — sidebar tab row; `active` uses `--accent-selected` fill; `onClose` shows an `×` on hover; `loading` swaps favicon for a spinner; `pinned` hides the label (icon-only). Reference: Arc sidebar tabs.
- `TabList({ children })` — vertical list container.
- `Folder({ label: string; open?: boolean; children; onToggle? })` — collapsible group with a chevron (reference: Arc PROD/DEV/LOCAL folders).

- [ ] **Step 1: Smoke test** — `TabItem` shows title, `active` sets `data-active`, `onClose` fires; `Folder` toggles open state and renders children when open.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- TabItem TabList Folder` → FAIL.
- [ ] **Step 3: Implement all three** (tokens-only).
- [ ] **Step 4: Stories** — a `TabList` containing pinned tabs, active/hover/loading tabs, and two `Folder`s with nested `TabItem`s, matching the Arc reference.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/shell/TabItem evo-design-system/src/shell/TabList evo-design-system/src/shell/Folder && git commit -m "feat(design-system): TabItem, TabList, Folder"`

---

## Task 16: `LeftRail` + `SplitView`

**Files:** `src/shell/LeftRail/`, `src/shell/SplitView/`.

**Interfaces:**
- `LeftRail({ items: { id: string; icon: ReactNode; label: string }[]; activeId: string; onSelect? })` — Arc's slim icon rail (Spaces / Media / Boosts / Archived). `Tooltip` on each; active emphasized with accent.
- `SplitView({ left: ReactNode; right: ReactNode; ratio?: number })` — two content panes side by side with a hairline divider (reference: Evo split-view feature).

- [ ] **Step 1: Smoke test** — `LeftRail` renders one button per item and marks active (by `aria-label`); `SplitView` renders both panes.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- LeftRail SplitView` → FAIL.
- [ ] **Step 3: Implement both** (tokens-only).
- [ ] **Step 4: Stories** — `LeftRail` with 5 items; `SplitView` with two placeholder pages.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/shell/LeftRail evo-design-system/src/shell/SplitView && git commit -m "feat(design-system): LeftRail + SplitView"`

---

## Task 17: `CommandBar` + `CommandInput`

**Files:** `src/command/CommandBar/`, `src/command/CommandInput/`.

**Interfaces:**
- `CommandBar({ open: boolean; onClose?; children: ReactNode })` — centered floating modal over a `Scrim`; `--surface-overlay`, `--blur-overlay`, `--radius-lg`, `--elevation-e3`. Reference: the Arc/Ora command-bar screenshot.
- `CommandInput({ value?; placeholder?; leading?; onValueChange? })` — large borderless input inside the bar (composes `SearchField` styling at a larger size).

- [ ] **Step 1: Smoke test** — `CommandBar` renders children only when `open`; renders a `Scrim` that fires `onClose`. `CommandInput` shows placeholder.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- CommandBar CommandInput` → FAIL.
- [ ] **Step 3: Implement both** (tokens-only).
- [ ] **Step 4: Stories** — an open `CommandBar` with a `CommandInput` and a few placeholder rows.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/command/CommandBar evo-design-system/src/command/CommandInput && git commit -m "feat(design-system): CommandBar + CommandInput"`

---

## Task 18: `CommandResultRow` + `CommandGroup` + `CommandEmptyState` + `AskEvoRow`

**Files:** one folder each under `src/command/`.

**Interfaces:**
- `CommandResultRow({ icon?: ReactNode; title: string; url?: string; selected?: boolean; onClick? })` — reference row: favicon, title, muted URL subtitle, **selected row filled with `--accent-gradient`** (the warm Arc selection). Reuses `ListRow` semantics but with the accent fill.
- `CommandGroup({ label?: string; children })` — labeled section.
- `CommandEmptyState({ message?: string })` — centered muted empty message.
- `AskEvoRow({ query: string; onClick? })` — an `AgentOrb` + "Ask Evo: <query>" call-to-action row.

- [ ] **Step 1: Smoke test** — `CommandResultRow` shows title + url and sets `data-selected`; `AskEvoRow` renders the orb + query text; `CommandEmptyState` shows its message.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- CommandResultRow CommandGroup CommandEmptyState AskEvoRow` → FAIL.
- [ ] **Step 3: Implement all four** (tokens-only; selected fill from `--accent-gradient`).
- [ ] **Step 4: Stories** — a full results list (selected first row + several rows + an `AskEvoRow`), and an empty state. Match the command-bar reference screenshot.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/command/CommandResultRow evo-design-system/src/command/CommandGroup evo-design-system/src/command/CommandEmptyState evo-design-system/src/command/AskEvoRow && git commit -m "feat(design-system): command-bar result rows, groups, empty state, Ask Evo"`

---

## Task 19: `AIPanel` + `AIPanelHeader` + `AgentStatus`

**Files:** `src/ai/AIPanel/`, `src/ai/AIPanelHeader/`, `src/ai/AgentStatus/`.

**Interfaces:**
- `AIPanel({ header: ReactNode; children: ReactNode; composer?: ReactNode })` — docked side panel; `--surface-panel`, hairline left border, column layout (header / scrollable thread / composer).
- `AIPanelHeader({ title?: string; onClose?; controls?: ReactNode })` — `AgentOrb` + title + controls.
- `AgentStatus({ state: "idle" | "thinking" | "running"; label?: string })` — small orb + status label (drives the "thinking" motion).

- [ ] **Step 1: Smoke test** — `AIPanel` renders header/children/composer regions; `AIPanelHeader` shows the orb + title; `AgentStatus` reflects `state` via `data-state`.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- AIPanel AIPanelHeader AgentStatus` → FAIL.
- [ ] **Step 3: Implement all three** (tokens-only).
- [ ] **Step 4: Stories** — an `AIPanel` shell with header + placeholder thread + placeholder composer; `AgentStatus` in each state.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/ai/AIPanel evo-design-system/src/ai/AIPanelHeader evo-design-system/src/ai/AgentStatus && git commit -m "feat(design-system): AIPanel shell, header, agent status"`

---

## Task 20: `ConversationThread` + `Message`

**Files:** `src/ai/ConversationThread/`, `src/ai/Message/`.

**Interfaces:**
- `Message({ role: "user" | "assistant" | "tool"; children: ReactNode; author?: string })` — `user` right-aligned bubble with subtle accent tint; `assistant` left, `--surface-overlay`; `tool` a compact monospace card.
- `ConversationThread({ children: ReactNode })` — scrollable vertical stack with an empty-state hint ("Your continuing Claude conversation will appear here.").

- [ ] **Step 1: Smoke test** — `Message` sets `data-role`; `ConversationThread` renders children, and shows the empty hint when it has none.
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- ConversationThread Message` → FAIL.
- [ ] **Step 3: Implement both** (tokens-only).
- [ ] **Step 4: Stories** — a thread with a user message, an assistant message, and a tool card; plus the empty state.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/ai/ConversationThread evo-design-system/src/ai/Message && git commit -m "feat(design-system): ConversationThread + Message"`

---

## Task 21: `Composer` + `ContextChip` + `WorkspacePicker` + `RuntimeControls` + `ToolCallCard`

**Files:** one folder each under `src/ai/`.

**Interfaces:**
- `Composer({ value?; placeholder?; contextChips?: ReactNode; onSend?; onValueChange? })` — textarea + send `Button` + a row of context chips.
- `ContextChip({ label: string; kind?: "page" | "workspace"; onRemove? })` — e.g. `@page`, workspace name.
- `WorkspacePicker({ workspaces: { id: string; name: string }[]; activeId: string; onSelect? })` — compact dropdown (uses `Menu`).
- `RuntimeControls({ children })` + `PermissionControl({ label: string; enabled: boolean; onChange? })` — pill row using `Toggle`/`Chip` for runtime/permission state.
- `ToolCallCard({ tool: string; status: "running" | "done" | "error"; children? })` — mono card with a status `Badge`.

- [ ] **Step 1: Smoke test each** (Composer send button fires `onSend`; ContextChip shows label + remove; WorkspacePicker lists workspaces; PermissionControl toggles; ToolCallCard shows tool + status).
- [ ] **Step 2: Run — verify fail.** `cd evo-design-system && npm test -- Composer ContextChip WorkspacePicker RuntimeControls ToolCallCard` → FAIL.
- [ ] **Step 3: Implement all** (tokens-only; reuse `Button`, `Chip`, `Toggle`, `Menu`, `Badge`).
- [ ] **Step 4: Stories** — a full `Composer` with `@page` + workspace chips; `WorkspacePicker` open; `RuntimeControls` with two `PermissionControl`s; `ToolCallCard` in each status.
- [ ] **Step 5: Run tests + Storybook build** → PASS + builds.
- [ ] **Step 6: Commit.** `git add evo-design-system/src/ai/Composer evo-design-system/src/ai/ContextChip evo-design-system/src/ai/WorkspacePicker evo-design-system/src/ai/RuntimeControls evo-design-system/src/ai/ToolCallCard && git commit -m "feat(design-system): Composer, context chips, workspace picker, runtime controls, tool card"`

---

## Task 22: Composed scene stories

**Files:** `src/scenes/Window.scene.stories.tsx`, `src/scenes/CommandBar.scene.stories.tsx`, `src/scenes/AIPanel.scene.stories.tsx`.

**Interfaces:**
- Consumes every component built above. No new components — these assemble full screens that become the flagship Claude Design cards.

- [ ] **Step 1: Build the Window scene** — `WindowFrame` with a real `Sidebar` (`SpaceHeader` + `FavoritesGrid` + `TabList` with folders + `SpaceSwitcher`), `Toolbar`, and a placeholder page in the content region. Add a second story variant showing a non-Agent Space (e.g. Perch amber) to prove theming.
- [ ] **Step 2: Build the CommandBar scene** — the Window scene with a `CommandBar` open over it (scrim + input + result rows + `AskEvoRow`), matching the reference screenshot.
- [ ] **Step 3: Build the AIPanel scene** — the Window scene with the `AIPanel` docked right, mid-conversation (thread with user/assistant/tool messages + a `Composer` with context chips + `AgentStatus` thinking).
- [ ] **Step 4: Storybook build**

Run: `cd evo-design-system && npm run build-storybook`
Expected: builds; open `npm run storybook` and confirm all three scenes render and re-theme across every toolbar Space.

- [ ] **Step 5: Commit.**

```bash
git add evo-design-system/src/scenes
git commit -m "feat(design-system): composed Window / CommandBar / AIPanel scenes"
```

---

## Task 23: Barrel exports, README, and full verification

**Files:**
- Modify: `evo-design-system/src/index.ts` (export every component + tokens + theme)
- Create: `evo-design-system/README.md`

**Interfaces:**
- Produces: a public entry point so `/design-sync`'s converter (and any consumer) can import the library, plus a README documenting the token system, the per-space accent model, and how to run Storybook.

- [ ] **Step 1: Write `src/index.ts`** exporting every component, `ThemeProvider`, `useSpaceAccent`, `deriveAccent`, and the token constants. (Enumerate all — no wildcard-only barrels for the component folders that need named exports.)
- [ ] **Step 2: Write `README.md`** — quickstart (`npm install`, `npm run storybook`), the token/accent model, dark-only note, and a one-paragraph "synced to Claude Design via /design-sync" section.
- [ ] **Step 3: Full test + build gate**

Run: `cd evo-design-system && npm test && npm run build-storybook`
Expected: all Vitest tests PASS; Storybook builds with zero errors and every component + scene story present.

- [ ] **Step 4: Tokens-only audit**

Run: `cd evo-design-system && grep -rEn "#[0-9a-fA-F]{3,8}|[0-9]+px" src --include=*.module.css | grep -v "tokens.css"`
Expected: no matches (every literal color/size lives only in `tokens.css`; component CSS Modules reference `var(--*)` only). Fix any leaks before committing.

- [ ] **Step 5: Commit**

```bash
git add evo-design-system/src/index.ts evo-design-system/README.md
git commit -m "feat(design-system): barrel exports, README, full verification pass"
```

---

## Post-plan: sync to Claude Design (separate, out of this plan)

After the kit is built and Storybook is clean, run `/design-sync` from `evo-design-system/` to push it to a new Claude Design project (storybook shape). That step has its own skill and approvals and is intentionally **not** part of this implementation plan.

## Self-Review notes

- **Spec coverage:** tokens (T2–T3), theming/accent model (T4), all four surfaces — primitives (T5–T11), shell (T12–T16), command bar (T17–T18), AI panel (T19–T21) — scenes (T22), Storybook preview + accent control (T4, per-task builds), testing (token unit tests + per-component render smoke tests + Storybook compile gate + tokens-only audit in T23), dark-only + tokens-only constraints (Global Constraints + T23 audit). Brand orb (T11). `/design-sync` handoff documented as post-plan (matches spec's "separate step"). No spec requirement is unmapped.
- **Placeholder scan:** foundation tasks (T1–T5) carry full code; component-group tasks carry full prop interfaces, variant/state lists, reference mappings, exact test/build commands, and per-task commits. Repeated boilerplate (the four-file component pattern) is defined once in T5 and referenced structurally, not with "similar to Task N" for actual code — each task states its own interface contract.
- **Type consistency:** `deriveAccent` return shape `{accent1, accent2, core}` is consistent across T3/T4/T11; `--accent-1/2/core`/`--accent-gradient`/`--accent-selected` names match tokens.css (T2) everywhere they're referenced; `renderWithTheme` signature is stable from T4 onward.
