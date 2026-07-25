# Evo architecture

Evo uses a superproject rather than a conventional source monorepo. The root
coordinates three independently versioned systems while keeping each system's
native tooling intact.

```text
Evo Browser (Chromium UI and trusted WebUI)
    |
    | browser-process authenticated loopback transport
    v
Evo Runtime (session supervisor, policy, streaming, secure broker)
    |
    | externally-agentic provider contract
    v
Evo OpenCode fork ----> official local Claude CLI and user subscription
```

## Browser

Chromium owns rendering, extension compatibility, profiles, tabs, Spaces, split
view, Sidekick WebUI, and Agent Workspace WebUI. Browser-process code owns the
runtime token; ordinary pages and WebUI JavaScript never receive it.

## Runtime

Evo Runtime starts with the browser, binds to loopback on a random port, and
requires a per-launch bearer token. It supervises Claude sessions, streams
events, applies workspace policy, and persists only non-secret mappings.

## OpenCode fork

The fork adds an externally-agentic provider contract so Claude owns its tool
loop and conversation state. OpenCode remains the engine/model abstraction;
Evo does not create a competing tool loop around Claude.

## Source management

Runtime and OpenCode are normal submodules. Chromium is reconstructed from a
pinned upstream revision plus `patches/chromium`. This avoids storing a massive
upstream checkout in the root Git repository while keeping every Evo-specific
Chromium change reviewable and reproducible.

## Build lane

All root worktrees share the primary checkout's `evo-chromium/src/out/Evo`.
The coordinator derives that checkout from Git's common directory, locks the
machine-wide lane, detaches the primary Chromium checkout at the caller's
committed revision, executes the build or test, and restores its original
branch even after failure or interruption. Feature worktrees never own an
`out/` directory.

The cache identity is the pinned Xcode path/build plus the hash of `evo/args.gn`.
Successful operations atomically update `evo-build-manifest.json` with exact
Chromium/runtime revisions, completed targets and verification suites, and a
fingerprint of the complete signed release bundle. Production promotion
revalidates that fingerprint and uses a macOS atomic exchange without invoking
the compiler or a mutable signing script. See [build-lane.md](build-lane.md).
