# Evo Dev Sunrise Icon

## Decision

Production Evo continues to use the approved `evo-icon-4f-agent.svg` artwork.
Evo Dev uses the approved `evo-icon-4a-sunrise.svg` artwork with the existing
small `DEV` badge retained.

## Scope

- Update only the generated Evo Dev macOS icon assets.
- Preserve the production icon assets and `/Applications/Evo.app` bundle.
- Preserve the Dev bundle identifier, isolated profile, runtime state, and
  Sidekick workspace.
- Refresh macOS Launch Services and Dock icon caches so the installed
  production app displays its current agent icon.
- Do not add a Dev Dock item or launcher wrapper.

## Acceptance

1. The generated Dev icon is derived from
   `docs/design-assets/evo-icons-svg/evo-icon-4a-sunrise.svg`.
2. The Dev icon visibly retains its `DEV` badge at Finder, Dock, and app-switcher
   sizes.
3. Production icon sources remain derived from the agent variant.
4. Both generated icon catalogs and signed app bundles remain valid.
5. The Dock continues to target only `/Applications/Evo.app`.
