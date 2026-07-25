# Evo Design System — v1 Design

Date: 2026-07-19
Status: Approved (design phase); ready for implementation planning.

## Purpose

Build a standalone React component library that models Evo's browser UI in a new visual language, so that Claude Design's design agent (claude.ai/design) can rapidly mock up and iterate Evo screens and flows using Evo's real, on-brand parts. The library is pushed to Claude Design with the `/design-sync` skill; from then on every design that agent produces is made of Evo components and maps back to a coherent system.

This is a **mockup kit first**: its job is high-fidelity visual building blocks for design exploration, not production browser code. Patterns proven here can later be re-implemented as Chromium WebUI, but that promotion is out of scope for this spec.

## Goals

- A single source-of-truth **token system** (color, type, space, radius, elevation, motion) expressed as CSS variables plus a typed TS export.
- A **balanced-hybrid visual language**: Zen's calm, floating, translucent, rounded shell as the neutral base, plus Arc's per-space accent as the identity layer.
- **~40 components across four surfaces** — primitives, window shell + sidebar, command bar, and the AI (Sidekick/Agent) panel — each styled entirely from tokens.
- **Storybook** as the preview and verification surface, with a per-space accent toolbar control, ready for `/design-sync` (storybook shape).
- The **loop closes**: components here → Storybook → `/design-sync` → Claude Design agent builds Evo screens with these parts.

## Non-goals (v1)

- Light mode. Every reference is dark and Evo's brand is dark; light mode is deferred to backlog.
- Shipping into Chromium. No changes to `evo-chromium/`, the patch series, or the submodules.
- Functional browser behavior. Components are presentational; interactivity is only what a mockup needs (hover/selected states, open/closed panels).
- Heavy test coverage. Visual correctness in Storybook is the bar.

## Design language

Chosen direction: **balanced hybrid** on the Arc↔Zen spectrum.

- **From Zen:** a floating, translucent shell — web content inset with a large corner radius and the theme bleeding behind it; minimal top chrome; favorites as rounded icon tiles; calm, sparse, low density.
- **From Arc:** per-space color theming as the core identity — each Space carries its own accent that tints the sidebar, the command-bar selection, and the AI panel; a richer sidebar with pinned favorites over nested folders; an optional left icon rail; a bottom space switcher.
- **Command bar (Arc/Ora):** a centered, floating, rounded modal — search/URL input, favicon result rows, the selected row filled with the Space accent, muted URL subtitles.

### Brand

The brand mark is Evo's app icon: a luminous **cyan→violet gradient orb** on deep near-black. This drives two things:

- The **default (Agent) accent** is that cyan→violet gradient (`#57dcd6 → #8f7bf3`).
- The **orb is a reusable motif** representing AI/Agent presence — it appears, scaled down, wherever Evo is thinking or listening: the AI panel header, the command bar's "Ask Evo" row, agent status, and the new-tab hero. The shipping kit uses the **real icon artwork** for the mark — the exported asset lives at the repo root as `evo-browser-icon-1024.png` and is copied into the package's `src/brand/assets/`. The brand mark's cyan→violet is a **fixed constant**; per-space accent themes the surrounding chrome, not the mark. (A CSS approximation of the orb is acceptable only as a fallback inside Storybook mockups.)

### Per-space accent model

- A Space carries **one seed hue**. The system derives the two-stop accent gradient (`--accent-1`, `--accent-2`) from the seed with a fixed hue-shift, so every Space stays balanced and legible.
- The user can open an **Arc-style color picker** and set the seed to any hue to customize a Space.
- An **advanced escape hatch** lets a Space author both gradient stops directly.
- Default Space (Agent) seeds cyan→violet.

## Architecture

A new self-contained package at repo root. It does not touch Chromium or the submodules and has its own `package.json`.

```
evo-design-system/
  package.json          # React 18 + Vite + Storybook (storybook-react-vite)
  src/
    tokens/             # source of truth → emits CSS vars + typed TS
    primitives/         # Button, Input, ListRow, Chip, Toggle, Menu, ...
    shell/              # WindowFrame, Sidebar, TabItem, SpaceSwitcher, ...
    command/            # CommandBar, CommandResultRow, ...
    ai/                 # AIPanel, Message, Composer, AgentOrb, ...
    brand/              # the Agent orb asset + wordmark
  stories/              # one *.stories.tsx per component + composed scenes
  .storybook/           # main.ts + preview (dark canvas, per-space accent toolbar)
```

Principles:

- **Tokens-only styling.** No component hardcodes a color, radius, or shadow; everything reads CSS custom properties. This is what makes swapping the per-space seed re-theme the whole system, and what a clean `/design-sync` export requires.
- **Storybook is the preview + verification surface.** Every component has a story; `/design-sync` renders those to build the Claude Design cards.
- **One source of truth.** Tokens compile to CSS variables (consumed by components) and a typed TS export (typed access), so an eventual Chromium WebUI can read the same values.

## Token system

- **Surfaces (neutral):** `canvas #0d0f13`, `sidebar #14171d`, `panel #1a1e26`, `overlay #20242e`, plus hairline borders (`rgba(255,255,255,.08)` and a stronger `.14`).
- **Ink ramp:** `#eef1f6 / #b7bec9 / #828b98 / #5b6472`.
- **Accent (per-space):** `--seed` (hue-picked) → derived `--accent-1` / `--accent-2` gradient + `--accent-core`; default seed cyan→violet. Interaction state layers (`hover` / `active` / `selected`) are accent-mixed, not separate palette entries.
- **Semantic:** danger, success, warning.
- **Type:** display, title, body, label, mono, with a small weight set.
- **Shape & depth:** radius `8 / 12 / 18 / 26`; elevation `e1 / e2 / e3`; backdrop-blur levels for the glass/translucency treatment.
- **Motion:** a small set of durations and easings that produce the calm, floaty feel.
- **Output:** CSS variables + a typed TS export from a single token source.

## Component inventory (v1)

Build order follows the grouping: primitives → shell → command bar → AI panel. All four surfaces are specified now so the plan is complete; the clean cut line if v1 must shrink is "primitives + shell first, command bar + AI panel second."

### Primitives

`Button` (primary / ghost / subtle, sizes, icon-only), `IconButton`, `Input`, `SearchField`, `ListRow` (favicon + title + subtitle + hover/selected states), `Chip` / `Badge`, `Kbd`, `Toggle`, `Tooltip`, `Menu` / `ContextMenu`, `Avatar`, `Scrim`, `Icon`.

### Shell + sidebar

`WindowFrame` (traffic-light title area, floating chrome, inset rounded content region), `Toolbar` (minimal back / forward / reload / split), `Sidebar` (per-space themed container), `SpaceHeader` (name + profile badge), `SpaceSwitcher` (bottom dots/tabs), `FavoritesGrid` + `FavoriteTile`, `TabItem` (active / hover / loading / pinned / close), `TabList` + `Folder` (collapsible, nested), `LeftRail` (Spaces / Media / Boosts / Archived), `SplitView` (two content panes).

### Command bar

`CommandBar` (modal + scrim), `CommandInput`, `CommandResultRow` (icon, title, muted URL subtitle, accent-filled selection), `CommandGroup`, `CommandEmptyState`, `AskEvoRow` (orb AI entry).

### AI panel (Sidekick / Agent)

`AIPanel` (docked side panel), `AIPanelHeader` (orb + controls), `ConversationThread`, `Message` (user / assistant / tool), `Composer` (textarea + send + context chips), `ContextChip` (@page, workspace), `WorkspacePicker`, `RuntimeControls` / `PermissionControl`, `AgentOrb` / `AgentStatus` (thinking / running), `ToolCallCard`.

## Preview, sync & verification

- **Stories:** one `*.stories.tsx` per component, plus a few composed **scene** stories — a full themed window, the command bar open over a page, the AI panel mid-conversation. Scenes are what make the Claude Design cards sell the system.
- **Per-space accent control:** a Storybook toolbar switch re-themes any story into any Space's hue, proving the token system works.
- **`/design-sync`:** a separate step after the kit is built. It runs against this Storybook (storybook shape), creates a new Claude Design project, and produces verified component and scene cards.
- **Testing:** light but real. A token unit test asserts that a seed hue derives a gradient within a legible contrast range; each component story renders without error via Storybook's test runner. No broad coverage — this is a mockup kit.

## Backlog / deferred

- Light mode across the system.
- Promoting proven patterns to Chromium WebUI (`chrome/browser/resources/`).
- Locating and wiring the real Evo app-icon asset as the brand mark (CSS orb is the interim stand-in for mockups).
- Additional surfaces beyond the v1 four (settings, new-tab customization, split-view management, extensions UI).

## Open questions

- Whether the small in-UI agent presence (agent status dot, "Ask Evo" glyph) stays the fixed brand cyan→violet or tints to the active Space accent. Default assumption: brand-fixed, with an optional `tint` prop.
- Whether the `LeftRail` (Arc-style icon rail) is in the shipping Evo UX or purely a mockup affordance — spec includes it as a component; product decision can drop it later.
