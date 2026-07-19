# Codex prompt — Browser Shell

Paste the block below into Codex to kick off implementation of the browser-shell epic. It is intentionally self-contained but points Codex at the committed docs so the details stay in one place.

---

Implement the **Browser Shell** for Evo Browser (the Chromium-based Arc replacement in this repo): the left sidebar, the address bar / toolbar, and the right rail.

**Read first, in this order:**
1. `AGENTS.md` — repository boundaries, the dev/prod policy, and the "Design and UI workflow" section (Evo is designed Figma-first; implement against the approved epic, don't design UI ad hoc).
2. `docs/design/browser-shell-epic.md` — the full spec: authoritative design tokens, features A–E with user stories + acceptance criteria, the component → Figma node-ID map, and the §9 "Placeholders & Deferred" list.
3. `docs/architecture.md` — how Evo's chrome and Chromium integration are structured today.

**Design source of truth:** the Figma file `090VBHVLybK2LEZaOtKbcq` (node IDs are in the epic). Match it; where this prompt and Figma disagree, Figma wins.

**How to build:**
1. Decide the implementation surface (native Views vs WebUI) for the sidebar and right rail, and record the decision in the PR. The tokens ship as CSS custom properties (WEB code syntax is already set in Figma), which favors a WebUI approach for those regions with the native window frame around them.
2. Implement the **token layer first** (epic §3) as the single source of truth — color/ink, the five per-space accent seeds, spacing, radius, type ramp, glass/elevation, and the Lucide icon set. Theme switching must be nothing more than swapping the active Space's `--accent-*` values (plus wallpaper).
3. Build **bottom-up** to mirror Figma: atoms → molecules → organisms → assembled shell. Match the component structure and the three Screen states (`Screen — Home` `19:3`, `… Sidebar Collapsed` `23:91`, `… Command Bar` `25:25` minus the palette).
4. **Respect §9 (Placeholders & Deferred).** Do NOT implement right-click/context menus, drag-to-reorder, folder expand/collapse, favorites management, omnibox suggestions, the Clear semantics, new-tab content, the ⌘K palette, the AI/Sidekick panel, or space management. Leave clean extension points and stop at those boundaries. The **right rail's items/icons/labels are placeholders** — implement it as a data-driven list of `{icon, label, target}` so the final IA can be defined later without structural change.

**Repository & process rules (from `AGENTS.md`):**
- Make Chromium changes in `evo-chromium/src`, then export the patch stack; never add Chromium source, `out/`, or profiles to the root repo. Update `workspace.json` pins if a pinned revision changes.
- Build, launch, and test `Evo Dev.app` only. Never touch the production profile.
- Run `./scripts/check-workspace.sh` and `./scripts/test.sh`.
- Work in small, reviewable commits, ideally one per feature (A → B → C → D → E). Open a PR that maps what you built to the epic's stories and lists exactly what was intentionally deferred.

If a requirement is ambiguous or missing from the epic/Figma, ask — do not invent UI or behavior.

---
