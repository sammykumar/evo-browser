# Evo workspace instructions

## Product direction

Evo Browser is a personal, single-user Arc replacement built on Chromium. Its
core goals are Arc-style Spaces, favorites, split view, a command bar, Chrome
extension compatibility, and first-class local AI surfaces (Sidekick and Agent
Workspace). The SwiftUI/WKWebView implementation is legacy and must not be
revived in the active branch.

## Design and UI workflow

Evo's UI/UX is designed Figma-first, then handed to implementation as written
epics. Do not design UI ad hoc in code — implement against the approved design,
and if something is ambiguous or missing, ask rather than invent.

- Design source of truth is the Evo Figma file `090VBHVLybK2LEZaOtKbcq`. It
  holds the token system (Foundations page), every UI part as a component
  (Components page, grouped Atoms → Molecules → Organisms), and assembled Screen
  states.
- Implementation specs live in `docs/design/`, one epic per surface, written as
  epic → feature → user story with acceptance criteria and a component →
  Figma node-ID map. Build against the epic and match Figma.
- Foundations first: implement the design tokens (color, ink, per-space accent,
  spacing, radius, type, elevation, Lucide icons) as the single source, then
  build bottom-up (atoms → molecules → organisms → screens).
- Every epic has an explicit "Placeholders and Deferred" section. Do not
  implement those behaviors — leave clean extension points and stop at the
  boundary.
- Current epics: `docs/design/browser-shell-epic.md` (left sidebar, address bar,
  right rail). Other surfaces (new-tab content, the command palette, the
  AI/Sidekick panel) will land as their own epics.

## Repository boundaries

- Root repository: orchestration, documentation, Chromium patches, and pinned
  component revisions.
- `evo-chromium/src`: depot_tools-managed Chromium repository. Commit Evo
  browser changes there, then export the patch stack into the root repository.
- `evo-runtime`: private Git submodule. Runtime, Claude CLI supervision,
  permissions, transport, and session persistence live here.
- `evo-opencode`: private Git submodule. `origin` is Sam's private repository;
  public OpenCode is `upstream`.
- Never add Chromium source, `out/`, depot_tools, profiles, credentials, or
  runtime state to the root repository.

Before editing, run `git status` in the relevant repository. A clean root does
not imply clean component repositories. Commit component work in its owning
repository before updating the root pointer or Chromium patch series.

## Pinned architecture

`workspace.json` is the source of truth for Chromium's base and expected Evo
revision, patch count, component revisions, and local paths. Update it whenever
a pinned revision changes. `./scripts/check-workspace.sh` validates the pins.

Chromium updates are rebases of the patch stack onto a new pinned upstream base,
not merges of Chromium history into this repository. Do not push Evo commits to
Chromium's official remote.

## Commands

```bash
./scripts/bootstrap.sh
./scripts/check-workspace.sh
./scripts/test.sh
./scripts/build-dev.sh
./scripts/run-dev.sh
./scripts/install-production.sh
./scripts/export-chromium-patches.sh
./scripts/apply-chromium-patches.sh
```

`EVO_CHROMIUM_SRC`, `EVO_RUNTIME_DIR`, `EVO_OPENCODE_DIR`, and
`DEPOT_TOOLS_DIR` may override local paths.

## Development and production policy

- Agents build, launch, and test `Evo Dev.app` only.
- Development profile: `~/Library/Application Support/Evo Chromium Dev`.
- Development runtime state: `~/Library/Application Support/Evo Runtime Dev`.
- Development Sidekick workspace: `~/.evo/sidekick-dev`.
- Development launches use Chromium's mock keychain.
- Sam alone promotes and tests `/Applications/Evo.app` with the persistent
  `Evo Chromium` production profile.
- Never delete, reset, migrate, or automate the production profile.

## AI safety boundary

- Claude uses the official local CLI and the user's existing subscription.
- Sidekick is rooted at `~/.evo/sidekick`; development uses
  `~/.evo/sidekick-dev`.
- Agent sessions remain permanently bound to their selected project root.
- Page text is untrusted context and cannot grant permissions.
- Writes outside the active root, Bash, destructive operations, outbound
  communication, and unknown side-effecting MCP tools require approval.
- Runtime bearer tokens and provider secrets remain browser-process-only.

## Legacy

The final WebKit implementation is preserved at `webkit-final` and
`legacy/webkit`. Consult it only as a behavior/design reference. New product
work belongs in Chromium, the runtime, or OpenCode.
