# Hybrid Evo Shell Spike

## Decision

Evo’s visible browser chrome will be a trusted browser-owned WebUI. Chromium
continues to own navigation, tabs, rendering, extensions, profile data, and
security-sensitive browser services. The macOS frame continues to own native
traffic lights and window behavior.

## Goal

Prove that a Figma-matched Evo shell can replace the stock Chromium toolbar
without losing real browser navigation or the development extension/profile
lane.

## Scope

The spike creates a third `chrome://evo-shell/` surface for the address bar,
alongside the existing sidebar and right rail. It renders the approved 44px
AddressBar component, including Back, Forward, Reload, editable URL/search
input, and the right-rail toggle.

The browser process exposes a small, typed bridge:

- Browser state: URL, title, loading, back availability, forward availability,
  and right-rail visibility.
- Browser commands: navigate, back, forward, reload, and toggle right rail.

The WebUI never receives profile secrets, extension APIs, runtime tokens, or
arbitrary browser-process access. It is trusted only because it is an Evo
browser-owned `chrome://` surface.

The macOS frame uses the shell layout’s traffic-light reservation for the
native controls. Those controls remain native and functional; the WebUI does
not emulate them.

## Explicitly excluded

This spike does not redesign or add product behavior. Existing Spaces/sidebar
data, extension compatibility, and Dev profile behavior stay intact. The spike
does not add Space persistence, Sidekick behavior, context menus, drag/drop,
or folder management.

## Acceptance

1. No stock Chromium toolbar or omnibox is visible in the normal Evo Dev
   window.
2. The shell WebUI renders the Figma-sized address bar and receives live
   browser state.
3. Back, Forward, Reload, URL navigation, and right-rail visibility operate
   through the bridge against the active Chromium tab.
4. Native traffic lights occupy the shell’s reserved header area.
5. The Dev app launches using only `Evo Chromium Dev` and mock keychain.
6. The existing Chrome-extension setup continues to be available in the Dev
   profile.

## Evaluation

The spike is successful only if all six acceptance items work in the signed
Dev build. If it succeeds, this code becomes the foundation for the browser
shell rather than a throwaway implementation. If it fails, the branch remains
isolated and no production or mainline shell is changed.
