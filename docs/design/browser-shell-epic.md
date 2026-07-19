# Epic: Browser Shell (Left Sidebar · Address Bar · Right Rail)

Status: Ready for implementation (design complete). Date: 2026-07-19. Owner of design: Sam. Implementer: Codex.

## 1. Summary

Replace Evo's current browser chrome with the new **balanced-hybrid shell** — a floating, translucent window (Zen-style) with per-space accent identity (Arc-style). The shell has three regions: a **left sidebar** (spaces, favorites, pinned tabs/folders, open tabs), a **floating address bar / toolbar**, and a **right rail** (icon+label tool switcher). This epic covers the shell chrome and its interactions that are defined today. New-tab content, the ⌘K command palette, and the AI/Sidekick panel are **separate epics** and out of scope here (the right rail's `Ask Evo` item will eventually open that AI panel).

The visual source of truth is the Figma file — build against the components and tokens there, not against this prose where they disagree.

## 2. Source of truth (Figma)

- **File:** `090VBHVLybK2LEZaOtKbcq` — https://www.figma.com/design/090VBHVLybK2LEZaOtKbcq
- **Pages:** `Foundations` (tokens, type, icons), `Components` (every part as a real component, grouped Atoms → Molecules → Organisms), `Screens` (assembled states), `Archive`.
- **Screens to match:** `Screen — Home` (`19:3`, sidebar expanded), `Screen — Home · Sidebar Collapsed` (`23:91`), `Screen — Home · Command Bar` (`25:25`, palette open — command palette itself is a separate epic).
- **Key component node IDs:** Sidebar `78:136`, AddressBar `78:49`, RightRail `93:190`, RailItem `91:90`, TabItem `11:23`, ListRow `9:18`, FaviconTile `72:31`, FavoritesGrid `76:33`, SpaceHeader `77:37`, SpaceSwitcher `77:45`, Badge `72:23`, SectionLabel `72:27`, IconButton `72:6`, SidebarToggle `72:10`, TrafficLights `72:19`, AgentOrb v2 `61:177`, Icon set `87:90`.

## 3. Design foundations (must be implemented first)

All chrome reads from tokens; nothing hardcodes a color, radius, or space. Tokens already carry WEB code-syntax (CSS custom properties) in Figma, so a WebUI implementation can consume them directly. Values below are authoritative (exported from Figma).

### 3.1 Color — neutral surfaces & ink (primitives)

| Token (CSS var) | Value |
| --- | --- |
| `--evo-neutral-canvas` | `#0d0f13` |
| `--evo-neutral-sidebar` | `#14171d` |
| `--evo-neutral-panel` | `#1a1e26` |
| `--evo-neutral-overlay` | `#20242e` |
| `--evo-ink-1` | `#eef1f6` |
| `--evo-ink-2` | `#b7bec9` |
| `--evo-ink-3` | `#828b98` |
| `--evo-ink-4` | `#5b6472` |
| `--evo-ink-on-accent` | `#0b0d13` |
| `--evo-alpha-hairline` | `rgba(255,255,255,.08)` |
| `--evo-alpha-hairline-strong` | `rgba(255,255,255,.14)` |
| `--evo-alpha-fill-subtle` | `rgba(255,255,255,.06)` |
| `--evo-alpha-fill-hover` | `rgba(255,255,255,.10)` |
| `--evo-status-red` `--evo-status-green` `--evo-status-amber` | `#e5484d` `#46b578` `#f2a65a` |

### 3.2 Color — semantic (theme-aware; resolved per active Space mode)

Semantic tokens alias primitives. `accent/*` is the only family that changes per Space; everything else is constant across modes.

- `--surface-canvas` → neutral/canvas · `--surface-sidebar` → neutral/sidebar · `--surface-panel` → neutral/panel · `--surface-overlay` → neutral/overlay
- `--surface-subtle` → alpha/fill-subtle · `--surface-hover` → alpha/fill-hover
- `--hairline` → alpha/hairline · `--hairline-strong` → alpha/hairline-strong
- `--ink-1..4` → ink/1..4 · `--on-accent` → ink/on-accent
- `--danger` `--success` `--warning` → status red/green/amber
- `--accent-1` `--accent-2` `--accent-core` → the active Space seed (see §7)

### 3.3 Per-space accent seeds (drive `--accent-1/2/core`)

| Space (mode) | accent-1 | accent-2 | accent-core |
| --- | --- | --- | --- |
| Agent (default) | `#57dcd6` | `#8f7bf3` | `#bff4ff` |
| Personal | `#7c8cff` | `#9b7bf3` | `#cdd4ff` |
| Work | `#5fd3a3` | `#4fb8d8` | `#b8f5df` |
| Media | `#f286a6` | `#b06ff0` | `#ffd0de` |
| Focus | `#6ea8f5` | `#57dcd6` | `#cfe6ff` |

Users can override a Space's seed hue with a picker (Arc-style); the system derives `accent-1/2` from the seed. The brand orb (`AgentOrb`) is **fixed** cyan→violet and does **not** recolor per space.

### 3.4 Spacing & radius

- Spacing (`--space-*`): 2xs 2 · xs 4 · sm 8 · md 12 · lg 16 · xl 24 · 2xl 32 · 3xl 48.
- Radius (`--radius-*`): sm 8 · md 10 · lg 14 · xl 20 · full 999. Usage: controls (address bar, buttons, inputs, rows, tabs, chips, badges) = **8**; cards/tiles = **10**; large floating surfaces (window, sidebar, right rail, panels) = **14**; circles (avatars, dots, orb) = full.

### 3.5 Typography (Inter; ships as system-ui / SF Pro on macOS, JetBrains Mono for mono)

| Style | Font | Size / Line | Tracking | Use |
| --- | --- | --- | --- | --- |
| Display | Inter Semi Bold | 24 / 28 | -3% | new-tab greeting |
| Title | Inter Semi Bold | 16 / 22 | -1% | space name, section titles |
| Body | Inter Regular | 13 / 19 | 0 | tab/row titles, URL |
| Label | Inter Medium | 11 / 14 | +8% | eyebrows (FAVORITES/PINNED), rail labels |
| Mono | JetBrains Mono | 12 / 18 | 0 | code/URL detail |

### 3.6 Materials & elevation

- **Liquid Glass** (floating surfaces: sidebar, address bar, right rail, command modal): translucent surface fill (~0.26 alpha over the wallpaper), backdrop blur (~40–56px), 1px inside stroke at `--hairline`, a white top inner-shadow edge highlight (~6% alpha, y+1), radius/lg (14), plus a soft drop shadow.
- **Elevation** drop shadows: `e1` y1 blur2 · `e2` y8 blur24 · `e3` y24 blur60.
- **Wallpaper:** a generated aurora gradient (violet→blue→teal) behind the window; the window floats on it with ~18px gap padding so the glass refracts color. Re-themeable per space.

### 3.7 Icons — Lucide

Standardize on **Lucide** (MIT). Icons are 24px source / 2px stroke, stroke color = `--ink-2` by default, brighten to `--ink-1` on active/hover. Ship at least the set used by the shell: `chevron-left`, `chevron-right`, `rotate-cw`, `panel-left`, `panel-right`, `plus`, `x`, `search`, `sparkles`, `columns-2`, `file-text`, `bookmark`, `download`, `clock`, `puzzle`, `settings-2`, `ellipsis`, `folder`, `star`, `globe`, `lock`, `house`, `layout-grid`, `archive`. Icon rendering must accept `currentColor` so per-context recolor works.

## 4. Feature A — Window Shell & Layout

The frame that hosts the three regions.

- **A1 — Floating window on wallpaper.** As a user, I see the browser window float on the aurora wallpaper with a rounded outer frame (radius/lg) and ~18px inset gap, so the chrome feels light and the accent bleeds behind the glass. AC: window content region is inset with rounded corners; wallpaper is visible in the gap; wallpaper re-themes with the active space.
- **A2 — Three-column layout.** The window is a horizontal layout of `[Left Sidebar] [Content] [Right Rail]` with ~18px gaps. Content (webview + toolbar) fills remaining width. AC: sidebar fixed 276px; right rail fixed 72px; content flexes; collapsing the sidebar (Feature B) widens content; hiding the right rail (Feature D) widens content.
- **A3 — Traffic lights.** macOS window controls (close/min/zoom, 12px) render at the top-left. When the sidebar is expanded they sit in the sidebar header row; when collapsed they sit in the toolbar's left inset. AC: controls are functional window controls (native), positioned per sidebar state. Figma: `TrafficLights` `72:19`.

Non-goals: Windows/Linux window-control styling (macOS-first for v1; other platforms follow platform convention).

## 5. Feature B — Left Sidebar

Figma organism `Sidebar` `78:136`. Top-to-bottom: traffic row → space header → FAVORITES → favorites grid → PINNED → pinned tabs & folders → Clear divider → New Tab → open tabs → (flex spacer) → space switcher.

- **B1 — Space header.** Shows an accent avatar dot + space name (Title) + a `Default` profile Badge. AC: avatar fill uses `--accent-1/2`; renders `SpaceHeader` `77:37`.
- **B2 — Favorites grid.** A 6-column grid of favorite tiles (34px cells, rounded 10, 17px favicon, hairline border). AC: real favicons render; clicking opens the site; grid wraps to rows. Figma: `FavoritesGrid` `76:33`, `FaviconTile` `72:31`. (Add/remove/reorder favorites = deferred, §9.)
- **B3 — Section labels.** `FAVORITES` and `PINNED` eyebrows (Label style, `--ink-3`, +8% tracking, uppercase). Figma: `SectionLabel` `72:27`.
- **B4 — Pinned tabs.** Persistent tab rows (36px), each favicon + title, using `TabItem` `11:23`. States: Default, Active (accent-tinted row fill), Loading (spinner ring). AC: active tab shows the accent-gradient selection fill; favicons are real; clicking activates the tab. Close affordance (✕) shows on hover for non-pinned; pinned tabs show no close.
- **B5 — Pinned folder.** A collapsible folder groups pinned links: a folder header (Lucide `folder` in accent, bold uppercase name) + indented child rows (favicon + title + optional URL subtitle) using `ListRow` `9:18`. Example in Figma: `AI IMAGE TOOLS` → `[PROD] TanStack`, `[LOCAL] TanStack` (`localhost:3005`). AC: header renders with folder glyph + label; children are indented; a child with a subtitle shows the URL beneath the title. (Expand/collapse animation + drag-into-folder = deferred, §9.)
- **B6 — Clear divider.** A hairline rule with a right-aligned `Clear` action separating pinned items from ephemeral open tabs. AC: `Clear` is a control (hover affordance) that will clear the open-tabs list.
- **B7 — New Tab.** A `+ New Tab` row (Lucide `plus` + label) below the Clear divider. AC: opens a new tab (new-tab content is a separate epic); hover shows `--surface-hover` fill at radius/sm.
- **B8 — Open tabs.** The ephemeral (non-pinned) tabs list below New Tab, each a `TabItem` (favicon + title, hover close ✕). AC: reflects the window's live open tabs in order; active open tab shows the active state; closing removes it. Figma examples: `Stats | AI Video Utils`, `GitHub · evo #42`.
- **B9 — Space switcher.** Bottom-pinned dots indicating available spaces, current space highlighted. AC: renders `SpaceSwitcher` `77:45`; clicking a dot switches space and re-themes accent (§7). (Full space management = deferred.)
- **B10 — Collapse / expand.** The `panel-left` `SidebarToggle` toggles the sidebar. When collapsed: sidebar hides, content widens, traffic lights move to the toolbar, and the toggle appears at the left of the address bar (Feature C). AC: toggling is reversible and animates; collapsed state matches `Screen — Home · Sidebar Collapsed` (`23:91`).

## 6. Feature C — Address Bar / Toolbar

Figma organism `AddressBar` `78:49`, a 44px-tall control (radius/sm) that fills the toolbar width and floats on the wallpaper.

- **C1 — Navigation controls.** Leading `chevron-left` (back), `chevron-right` (forward), `rotate-cw` (reload) as `IconButton`s (`72:6`), stroke `--ink-2`, disabled state at `--ink-4`. AC: wired to browser back/forward/reload; disabled when unavailable.
- **C2 — URL / search field.** A single field showing the current URL or `Search or enter URL` placeholder (`--ink-3`). AC: focus selects all; entering a URL navigates, a query searches; the field is the primary omnibox. (Autocomplete/suggestions dropdown = deferred or its own epic.)
- **C3 — Sidebar toggle when collapsed.** A boolean-controlled leading `panel-left` toggle appears at the address bar's left **only when the sidebar is collapsed** (Figma: `AddressBar` `Sidebar Toggle` boolean = true on the collapsed screen). AC: hidden when sidebar expanded; shown when collapsed; clicking re-expands the sidebar.
- **C4 — Right-rail toggle.** A trailing `panel-right` control toggles the right rail's visibility. AC: reflects rail visibility; hidden rail widens content.
- **C5 — Solid (non-glass) when sidebar expanded.** Per Sam's direction, the address bar uses the solid `--surface-overlay` treatment (not glass) when the sidebar is open, matching the collapsed look, for consistency. AC: address-bar background is consistent across expanded/collapsed states.

Note: the old inline "Ask Evo" chip has been **removed** from the address bar — that affordance now lives only in the right rail (Feature D).

## 7. Feature D — Right Rail (tool switcher)

Figma organism `RightRail` `93:190`, a 72px glass rail on the right of the window; a vertical list of icon+label items (`RailItem` `91:90`, State = Default/Active, with a swappable `Icon` and `Label`). This is ClickUp-style: every item shows an icon **and** a text label so its purpose is obvious.

- **D1 — Rail items.** A top group of tool items and a bottom-pinned group (`Settings`, `More`). Current Figma set: `Ask Evo` (active), `Split`, `Notes`, `Saved`, `Downloads`, `History`, `Extensions` / `Settings`, `More`. AC: renders icon + label per item; the active item shows the highlight (rounded fill + `--ink-1` icon/label); others are `--ink-3`.
- **D2 — Selection.** Clicking an item activates it (moves the active highlight) and opens the corresponding panel/surface. AC: exactly one item is active; active state persists per window.
- **D3 — Collapse (optional).** The `panel-right` toolbar control (C4) hides/shows the rail. AC: hidden rail reclaims content width.

**IMPORTANT — placeholder:** the right rail's **item set, icons, labels, and order are placeholders** in Figma. Do **not** treat `Ask Evo / Split / Notes / Saved / Downloads / History / Extensions / Settings / More` as the final information architecture. Implement the rail as a **data-driven list of {icon, label, target}** so the final items can be defined later without structural change. What each item opens (AI panel, split view, notes, etc.) is **not yet specified** and is out of scope here.

## 8. Feature E — Per-Space Theming (supporting)

- **E1 — Accent modes.** The active Space sets `--accent-1/2/core` (§3.3); all accent-bound chrome (active tab fill, space avatar, selection states, AskChip/orb affordances) re-themes when the space changes. AC: switching space via B9 updates every accent-bound element and the wallpaper; non-accent tokens stay constant.
- **E2 — Seed override.** A Space's accent can be set to any hue via a color picker; `accent-1/2` derive from the seed. AC: choosing a seed persists per space and re-themes live. (Picker UI can be a follow-up; the token plumbing is required now.)

## 9. Explicit placeholders & deferred behaviors (future sessions)

These are intentionally **not** specified yet — do not invent them; leave clean extension points.

- Right-rail final IA (items/icons/labels/order) and what each item opens (§7 D-note).
- Right rail icons are placeholder art in Figma.
- **Context menus / right-click:** on a pinned tab, folder, favorite, open tab, or space (rename, unpin, close others, move to folder, etc.).
- **Drag & drop:** reorder tabs/favorites, drag a tab into/out of a folder, drag to pin/unpin.
- **Folder expand/collapse** interaction + animation; creating/renaming folders.
- **Favorites management:** add/remove/reorder; edit tiles.
- **Clear action** exact semantics (which tabs it clears; confirmation).
- **Omnibox suggestions/autocomplete** dropdown.
- **New-tab content**, **⌘K command palette**, and the **AI/Sidekick panel** — separate epics.
- **Space management:** creating/deleting/reordering spaces; profiles.
- Keyboard shortcuts, hover/focus-visible/animation timing polish, Windows/Linux chrome parity, light mode.

## 10. Technical notes for the implementer

- Evo is Chromium-based (`evo-chromium`). This shell **replaces** Chromium's default top tabstrip + toolbar with a vertical-sidebar layout — a significant chrome change, not a theme. Decide native-Views vs WebUI for the sidebar/right-rail; tokens ship as CSS custom properties (WEB code syntax already set in Figma), which favors a WebUI approach for the sidebar/right-rail content with the native window frame around it. Record the decision before building.
- Implement the **token layer first** (§3) as the single source; every subsequent story consumes tokens. Theme switching = swapping the active Space mode's `--accent-*` values (and wallpaper), nothing else.
- Build **bottom-up** to mirror Figma: atoms (IconButton, Badge, FaviconTile, SidebarToggle, TrafficLights) → molecules (TabItem, ListRow, FavoritesGrid, SpaceHeader, SpaceSwitcher, RailItem) → organisms (Sidebar, AddressBar, RightRail) → assembled shell. Match component structure and the three Screen states pixel-for-pixel.
- Favicons in the mockup are illustrative; wire real favicons from the tab/site.

## 11. Acceptance for the epic

The epic is done when: the three Screen states (`19:3`, `23:91`, `25:25` minus the palette) render from tokenized components and match Figma; sidebar collapse/expand, tab activation, right-rail selection, and space-accent theming work; and all §9 items are left as clean, unimplemented extension points (no placeholder behavior silently shipped as final).
