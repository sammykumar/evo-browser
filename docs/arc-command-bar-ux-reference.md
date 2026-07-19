# Arc Command Bar UX — behavioral reference for the Evo (Chromium) rebuild

## §0 Context

### Purpose

This document specifies the **observable behavior** of Arc's **Command Bar** — the floating "Search or Enter URL…" overlay that is Arc's primary way to navigate, switch tabs, and run actions — so the Evo (Chromium) implementation can rebuild it. It is written as user stories with acceptance criteria and contains **no implementation guidance**: no mention of Chromium's omnibox, AutocompleteProvider, views, or prefs. Describe *what the user sees and does*; the implementing agent decides *how*.

This is a sibling to `arc-spaces-ux-reference.md`. The Command Bar is the surface that *ties Spaces together* — it searches across all Spaces, switches to open tabs anywhere, and creates Spaces/folders/pins — so it reuses that document's vocabulary (Space, Favorites, Pinned tabs, Folders, Today tabs). Read the two together.

### Source of truth

1. **A screenshot** from Sam's daily-driver Arc: the Command Bar open over a page, showing the "Search or Enter URL…" input with a ranked suggestion list — a highlighted top result that is a **pinned/open tab** ("Data Access – Google Auth Platform – Perch Agents"), several **history/URL** suggestions with globe icons and their URLs shown greyed (`leads.fastlease.org/nova/resources/leads`, `dev-leads.fastlease.org`), an **app-icon** suggestion ("Microsoft Azure — portal.azure.com/…"), and a **tab** suggestion with a chat glyph ("Contact the Team"). This is authoritative for result *types* and layout.
2. **Arc's official Command Bar (⌘T) action catalog** (`start.arc.net/command-bar-actions`) — authoritative for the *commands* the bar can run.
3. **General knowledge of Arc's behavior** for interaction detail (invocation modes, URL-vs-search detection, switch-to-tab dedup, keyboard navigation). Labeled **Arc behavior notes**; the softest part of the spec — verify against live Arc if load-bearing.

### Scope

Six slices, all in scope:

- **Slice A — Invocation & modes** — the several ways the bar opens and how each behaves (new-tab entry, edit-current-URL, quick-lookup / Little Arc).
- **Slice B — Unified input** — one field that resolves to a URL *or* a search, with the right default action.
- **Slice C — Switch-to-tab & de-duplication** — find and focus an already-open tab across all Spaces instead of opening a duplicate.
- **Slice D — Suggestions & result types** — what appears in the ranked list (open tabs, pinned tabs, favorites, history, bookmarks, Spaces, search suggestions) and how it's ordered.
- **Slice E — Command actions** — the command-palette behavior: running actions like New Space, Focus on [Space], Pin to…, New Folder, Copy URL, Clear Today.
- **Slice F — Ask-AI entry** — routing a query to an AI answer from the same bar.

### Non-goals

- The Spaces/sidebar surfaces themselves — see `arc-spaces-ux-reference.md`.
- Search-engine *settings* management (adding custom engines, per-site search) beyond what the bar needs to function — a separate preferences feature.
- History/bookmark *storage and management UI* — the bar *reads* from history/bookmarks; managing them is elsewhere.
- Any Chromium-internal mechanism (omnibox, autocomplete providers). If you catch yourself naming one, you've left this document's remit.

### Backlog status

`evo/BACKLOG.md` has **no browser Command Bar line today** — the only "command palette" entry is under the EvoWork tasks/sessions epic (a different surface). This epic is therefore a **gap**: recommend adding a "Command Bar" line under "Arc-style browser shell." The Ask-AI slice (§F) relates to the existing AI item "Page-aware Evo AI entry point."

### Arc-primary, with Ora notes

Grounded in the live Arc behavior above. Known Ora differences appear as **Ora divergence** call-outs; Ora could not be inspected live, so treat them as leads to verify. Where Arc and Ora disagree on a user-facing default, the choice is surfaced in **§7 Open decisions** rather than silently picked.

---

## §1 Vocabulary

Terms specific to this document (Space, Favorites, Pinned tabs, Folder, Today tabs come from `arc-spaces-ux-reference.md`).

- **Command Bar** — the floating, keyboard-launched overlay with a single text input ("Search or Enter URL…") and a ranked suggestion list beneath it. Arc's primary navigation and action surface.
- **Query** — whatever the user types. Resolves to one of: a URL to open, a web search, a switch-to-existing-tab, or a command to run.
- **Result / suggestion** — one row in the list. Each has a **type** (open tab, pinned tab, favorite, history, bookmark, Space, search suggestion, or command), an icon, a primary label, and optional secondary text (e.g. the URL).
- **Default action** — what pressing Enter does given the current query and the highlighted result (open URL, run search, switch to tab, or execute command).
- **New-tab mode / edit-URL mode / quick-lookup mode** — the three invocation contexts in Slice A.
- **Ask-AI** — routing the query to an AI answer rather than a web navigation (Slice F).

---

## §2 Slice A — Invocation & modes

### Narrative

The bar opens several ways, and the invocation determines the *default behavior* — the same overlay, but seeded differently. Opening it "to make a new tab" starts empty. Opening it "to edit where I am" pre-fills the current URL, selected, so typing replaces it in place. A separate quick-lookup mode opens a lightweight single-page window from anywhere in the OS without disturbing the current Space.

### User stories

**A1 — Open the bar for a new tab.**
As a user, I want a shortcut that opens the Command Bar with an empty field, so that I can type a destination and open it as a new tab in the current Space.
- Acceptance:
  - The shortcut (Arc: `Cmd+T`) opens the overlay centered, focused, with an empty input and the cursor ready.
  - Pressing Enter on a typed URL/search opens the result as a **new tab** in the active Space (subject to switch-to-tab dedup, §4/C).
  - Escape (or clicking outside) dismisses the bar with no change.

**A2 — Open the bar to edit the current URL.**
As a user, I want a shortcut that opens the bar pre-filled with the current page's URL (fully selected), so that I can edit or replace where the *current* tab points.
- Acceptance:
  - The shortcut (Arc: `Cmd+L`) opens the overlay with the active tab's URL shown and selected.
  - Pressing Enter navigates the **current tab** to the new destination (replace-in-place), not a new tab.
  - Typing immediately replaces the selected URL.

**A3 — Quick-lookup window (Little Arc).**
As a user, I want to open a minimal single-page window from anywhere, so that I can look something up without switching into a Space or cluttering my tabs.
- Acceptance:
  - A global shortcut (Arc: `Cmd+Option+N`) opens a small, frameless, single-page window with its own command input.
  - The window holds one page at a time and is dismissible without affecting my main window's Spaces or tabs.
  - There is an affordance to promote its page into a real tab in a chosen Space if I decide to keep it.
  - *(Whether Evo ships this in v1 is an **open decision**, §7 — it's the most separable piece.)*

### Arc behavior notes

- `Cmd+T` and `Cmd+L` open the *same* overlay; the difference is seeding (empty vs. current-URL-selected) and the Enter default (new tab vs. replace-in-place).
- Little Arc pages opened from links in *other apps* land here too, so it doubles as Arc's external-link handler surface.

### Ora divergence

- Confirm Ora's shortcut set — it broadly mirrors Arc (`Cmd+T`/`Cmd+L`) but may not ship a Little-Arc equivalent. If it doesn't, that supports deferring A3.

### Open decision → §7

- Ship Little Arc (A3) in v1 or defer; exact key assignments vs. Evo's existing map.

---

## §3 Slice B — Unified input (URL or search)

### Narrative

One field does both jobs. The bar decides, as the user types, whether the query is a place to *go* (a URL) or a thing to *search*, and makes the correct thing the default action — while always leaving the other reachable. This is why the placeholder reads "Search or Enter URL…".

### User stories

**B1 — Enter a URL.**
As a user, I want to type a URL and press Enter to go there, so that navigation is direct.
- Acceptance:
  - Input recognized as a URL (has a scheme, a known TLD, is `localhost`, an IP, or a port) resolves to navigation to that URL.
  - A top result reflects the URL destination so I can confirm before committing.

**B2 — Search the web.**
As a user, I want to type words and press Enter to search, so that I don't have to visit a search engine first.
- Acceptance:
  - Input that isn't URL-like resolves to a web search with the configured default engine.
  - The bar shows live search suggestions as I type (see §5/D) and running the search opens (or replaces, per mode §2) a results tab.

**B3 — Unambiguous default action.**
As a user, I want the highlighted result to make the Enter behavior obvious, so that I'm never surprised by where Enter takes me.
- Acceptance:
  - At all times exactly one result is highlighted, and its type (URL / search / switch-to-tab / command) is visually clear.
  - The default action for the current query is deterministic and documented (URL-like → navigate; else → search; a matching open tab may take precedence per §4/C — decide and be consistent).

### Arc behavior notes

- Arc treats `localhost:PORT` and bare hosts as URLs — important for Sam's dev workflow (his Spaces are full of `localhost:3000`, `dev-leads.fastlease.org`, etc.). Get the URL-vs-search heuristic right for dev hosts.

### Ora divergence

- Same unified-input concept. No known meaningful divergence.

### Open decision → §7

- Whether an exact-match open tab (switch-to-tab) outranks a typed-URL navigation as the Enter default (§4/C interaction).

---

## §4 Slice C — Switch-to-tab & de-duplication

### Narrative

Arc's signature behavior: the bar searches *across all Spaces* for tabs you already have open (and pinned tabs), and offers to **switch to** them rather than opening a second copy. "Type three letters, the right tab, hit Enter, you're there." This is what keeps tab count sane and is the highlighted top result in the screenshot.

### User stories

**C1 — Find an open tab from anywhere.**
As a user, I want the bar to surface tabs I already have open in *any* Space, so that I can jump to one without hunting through sidebars.
- Acceptance:
  - Typing matches against titles and URLs of open tabs across every Space (not just the active one).
  - A matching open tab appears as a **switch-to-tab** result, visually distinct from a "navigate to URL" result.

**C2 — Switch instead of duplicate.**
As a user, I want activating a switch-to-tab result to focus the existing tab, so that I don't accumulate duplicates of the same page.
- Acceptance:
  - Activating a switch-to-tab result focuses that tab — **switching Spaces if the tab lives in another Space** — rather than opening a new one.
  - When a query has both an exact open-tab match and a URL interpretation, the switch-to-tab behavior is offered clearly (default-vs-secondary is the §3/B3 open decision).

**C3 — Reveal in sidebar.**
As a user, I want to locate a found tab in its Space's sidebar, so that I can act on it in context.
- Acceptance:
  - A result offers a "Reveal Tab in Sidebar" affordance (an Arc command) that selects the tab in its Space.

### Arc behavior notes

- Matching includes **pinned tabs** and **favorites**, not only live/ephemeral tabs — the screenshot's top result is a pinned tab ("…Perch Agents"), and "Microsoft Azure" is a favorite/pinned entry.
- Cross-Space switching is the point: focusing a result in another Space makes that Space active.

### Ora divergence

- Ora also does cross-Space tab search; verify whether Ora scopes results to the current Space by default with an opt-in to widen (a plausible difference worth checking).

### Open decision → §7

- Default scope of switch-to-tab matching: all Spaces (Arc) vs. current Space first. Recommend **all Spaces**.

---

## §5 Slice D — Suggestions & result types

### Narrative

Beneath the input is a short, ranked list mixing several sources. The screenshot shows the mix: a pinned/open tab (top, highlighted), history/typed-URL entries (globe icon + greyed URL), a favorite (app icon), and a labeled tab. Ranking favors what you're most likely to want: exact open-tab and pinned matches, then history/bookmarks, then live search suggestions.

### User stories

**D1 — Mixed, ranked results.**
As a user, I want the most relevant destinations first regardless of source, so that Enter usually does what I mean.
- Acceptance:
  - Results draw from: open tabs, pinned tabs, favorites, history, bookmarks, Spaces, and web search suggestions.
  - Each result shows an icon indicating its type (favicon/app icon for tabs & favorites, globe for history/URL, a distinct glyph for commands and Spaces) and, where useful, secondary text (the URL).
  - The list is bounded to a small number of rows (no endless scroll); the strongest match is highlighted by default.

**D2 — Jump to a Space.**
As a user, I want to type a Space's name and jump to it, so that the bar also navigates my organization.
- Acceptance:
  - Space names match and appear as a **Focus on [Space]** result; activating it makes that Space active.

**D3 — Distinct result affordances.**
As a user, I want each result type to behave predictably on Enter, so that navigation, switching, and commands don't blur together.
- Acceptance:
  - Navigate results open/replace a URL; switch-to-tab results focus a tab (§4/C); Space results switch Spaces; command results run an action (§6/E); search-suggestion results run a search.

### Arc behavior notes

- History/typed-URL results show the URL greyed beside the title (as in the screenshot). Favorites and pinned tabs show their site/app icon rather than a globe.

### Ora divergence

- Result taxonomy is broadly the same. No known meaningful divergence.

### Open decision → §7

- Ranking policy specifics (how aggressively open-tab/pinned matches outrank fresh search suggestions) — recommend biasing toward already-open/pinned first.

---

## §6 Slice E — Command actions

### Narrative

The same bar is a command palette. Typing an action's name (or a page-context action) surfaces it as a runnable command — no menu-diving. Arc's catalog is broad; the point for Evo is that the *bar can run actions*, and a core set is available. The full Arc list is large; the required subset below is what ties into Spaces/tabs.

### User stories

**E1 — Run a command by name.**
As a user, I want to type a command and run it from the bar, so that I can act without leaving the keyboard.
- Acceptance:
  - Typing a command's name surfaces it as a command-type result; Enter executes it.
  - Command results are visually distinguished from navigation results (distinct glyph, no URL).

**E2 — Core command set.**
As a user, I want the Spaces/tab-related commands available from the bar, so that organization is keyboard-driven.
- Acceptance — at minimum these run from the bar (names mirror Arc's catalog):
  - **Spaces/org:** New Space, Select Next/Previous Space, Focus on [Space], New Folder, Pin to [Space/Folder], Pin to [New Folder], Unpin Tab, Favorite Tab, Replace Pin with Current Page.
  - **Tab lifecycle:** New Tab, Close Tab, Archive Tab, Reopen Last Closed Tab, Duplicate Current Tab, Rename Current Tab, Reveal Tab in Sidebar, Reset Tab.
  - **Session/window:** New Window, New Incognito Window, Little Arc, Toggle Sidebar, Clear Today, Copy Current URL, Downloads.
  - **Content tools (if the corresponding features exist in Evo):** New Note, New Easel, Capture Page, Add/Remove Split View.
  - *(Not every Arc command must ship day one; the required subset is the Spaces/tab/session groups. Content-tool commands are gated on those features existing — an **open decision**, §7.)*

**E3 — Context-aware commands.**
As a user, I want commands that act on the current page to appear when relevant, so that "Pin to…", "Copy Current URL", or "Archive Tab" are one keystroke away.
- Acceptance:
  - Page-context commands operate on the active tab and only surface when there is an applicable target.

### Arc behavior notes

- Arc's catalog also includes preferences, dev tools, zoom, print, appearance switching, and "create new document in external tools (Notion, Figma, Google Docs…)". These are *nice-to-have*, not core to the Spaces tie-in; treat as an extended set.

### Ora divergence

- Ora exposes fewer bespoke commands than Arc. The required core subset above is a safe intersection.

### Open decision → §7

- Which commands ship in v1 vs. later; whether external-tool document creation is in scope at all.

---

## §7 Slice F — Ask-AI entry

### Narrative

From the same field, a query can be routed to an AI answer instead of a web navigation — Arc surfaces an "Ask on…" option. For Evo this is the natural hook into the existing **page-aware Evo AI entry point** (backlog), letting the Command Bar be the front door to Evo's AI rather than only a URL/search box.

### User stories

**F1 — Route a query to AI.**
As a user, I want to send my typed query to Evo's AI from the Command Bar, so that I can get an answer without opening a chat surface first.
- Acceptance:
  - When a query is present, the bar offers an **Ask [Evo AI]** result (analogous to Arc's "Ask on…").
  - Activating it routes the query to Evo's AI answer surface rather than performing a web search/navigation.
  - The AI option is clearly distinct from the web-search result so the two are never confused.

**F2 — Preserve web search.**
As a user, I want the plain web search to remain the obvious default, so that adding AI doesn't hijack ordinary navigation.
- Acceptance:
  - Ask-AI is an explicit, secondary choice (a distinct row / modifier), never the silent default for a bare query.

### Arc behavior notes

- Arc's version routes to third-party engines (ChatGPT/Perplexity). Evo's equivalent should route to Evo's own AI per the backlog's AI direction, not a hardcoded third party.

### Ora divergence

- Ora's AI entry differs by product; not a reliable reference. Follow Evo's AI direction instead.

### Open decision → §8

- Whether Ask-AI ships with the Command Bar epic or lands with the broader Evo AI work; how it's triggered (dedicated row vs. modifier key vs. prefix).

---

## §8 Cross-cutting requirements

**Keyboard-first navigation within the bar.** Up/Down move the highlight; Enter runs the default action of the highlighted result; Escape dismisses without change; Tab behavior (accept/complete vs. next result) is defined and consistent. The bar is fully operable without the mouse.

**Per-Space context.** The bar opens in the context of the active Space: new tabs/pins default to that Space, and results reflect cross-Space state (switch-to-tab spans all Spaces per §4/C). Little Arc (§2/A3) is the deliberate exception — it's Space-less.

**Dismissal & non-destructiveness.** Opening and closing the bar without choosing a result changes nothing (no stray tab, no navigation). Clicking outside the overlay dismisses it.

**Live suggestions & responsiveness.** Suggestions update as the user types with no perceptible lag; the highlighted default keeps up with the query so Enter is always predictable.

**Theming & legibility.** The overlay adopts the active Space's/app appearance and remains legible in light and dark, including result icons, greyed secondary URLs, and the highlighted row.

**Empty state.** Opening the bar with an empty field shows a useful default (e.g. recent/frequent destinations or nothing but the placeholder) rather than a broken panel; the placeholder reads like Arc's "Search or Enter URL…".

**No engine chrome leakage.** As with Spaces, none of this may expose raw Chromium omnibox/autocomplete UI. The Command Bar is the only such surface the user sees.

---

## §9 Open decisions for Sam

Recommended defaults included so the implementing agent isn't blocked.

1. **Little Arc in v1?** (§2/A3) Most separable piece. *Recommend: defer to a later slice; ship `Cmd+T`/`Cmd+L` first.*
2. **Switch-to-tab vs. typed-URL as Enter default** when both match. (§3/B3, §4/C) *Recommend: exact open-tab/pinned match wins for switch-to-tab; otherwise typed URL navigates.*
3. **Switch-to-tab scope.** All Spaces vs. current Space first. (§4/C) *Recommend: all Spaces (Arc behavior).*
4. **Ranking policy.** How hard already-open/pinned outrank fresh search suggestions. (§5/D) *Recommend: bias to open/pinned first, then history/bookmarks, then search.*
5. **Command subset for v1.** (§6/E) *Recommend: ship the Spaces/tab/session core groups; gate content-tool commands on those features existing; external-tool document creation out of scope.*
6. **Ask-AI timing & trigger.** Ship with this epic or with broader Evo AI; dedicated row vs. modifier vs. prefix. (§7/F) *Recommend: reserve a dedicated "Ask Evo AI" row, wire it when the AI surface is ready; never the silent default.*
7. **Keyboard assignments.** Reconcile `Cmd+T`/`Cmd+L`/`Cmd+Option+N` with Evo's existing shortcut map. (§8)

---

## Appendix — relationship to other specs & backlog

- **Companion spec:** `arc-spaces-ux-reference.md` — the Command Bar consumes its concepts (Spaces, Favorites, Pinned tabs, Folders, Today tabs) and drives several of its actions (New Space, Focus on [Space], Pin to…, New Folder).
- **Backlog gap:** no browser Command Bar line exists in `evo/BACKLOG.md` today. Recommend adding one under "Arc-style browser shell." The Ask-AI slice (§7/F) attaches to the existing AI item "Page-aware Evo AI entry point."

| Concept | Source |
|---|---|
| Command catalog (New Space, Focus on [Space], Pin to…, Clear Today, Reveal Tab in Sidebar, etc.) | Arc official Command Bar (⌘T) actions list |
| Result types & layout (switch-to-tab, history w/ greyed URL, favorite app icon) | Sam's live Arc screenshot |
| Invocation modes (`Cmd+T` new tab, `Cmd+L` edit URL, `Cmd+Option+N` Little Arc) | Arc knowledge + web research |
