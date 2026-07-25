# Evo shared Chromium build lane

Evo keeps one Chromium compiler cache at
`evo-chromium/src/out/Evo` in the primary root checkout. Git worktrees remain
useful for isolated source editing, but they do not compile into local `out/`
directories.

## Normal development

1. Commit Chromium changes in the feature Chromium worktree.
2. Run `./scripts/build-dev.sh` or `./scripts/run-dev.sh` from the matching root
   worktree.
3. Run focused Chromium verification through `./scripts/test-chromium.sh`.

The coordinator finds the primary checkout through the root Git common
directory. It acquires the lock at
`~/Library/Application Support/Evo Build/lock`, temporarily detaches the
primary Chromium checkout at the requested commit, and always restores the
previous branch/revision. A waiting caller prints the active PID, request, and
operation status every 30 seconds. A stale lock is reclaimed only after its
recorded process no longer exists.

The default focused suite is:

```bash
./scripts/test-chromium.sh
```

Custom build targets and filters are supported without exposing a worktree
output path:

```bash
./scripts/test-chromium.sh \
  --target unit_tests \
  --unit-filter 'EvoShell*:*EvoSpaceTheme*'
```

## Cache identity and migration

`workspace.json` pins `/Applications/Xcode.app/Contents/Developer`, Xcode 26.6
build 17F113, and `out/Evo`. The lane also hashes `evo/args.gn`. An unidentified
legacy cache, different Xcode build, or changed GN hash is rejected instead of
being silently regenerated.

Use the explicit one-time migration command when either pin intentionally
changes:

```bash
./scripts/migrate-build-cache.sh
```

Migration regenerates GN in the canonical output and keeps compatible object
files so completed compilation is not discarded.

## Manifest

After a successful operation, `out/Evo/evo-build-manifest.json` is replaced
atomically. It records:

- exact Chromium and runtime revisions;
- GN-arguments hash and Xcode path/version/build;
- completed build targets and verification suites;
- bundle identifier, version, signature result, and timestamp;
- whether the artifact is verified for production.

A failed or interrupted operation leaves the previous known-good manifest
unchanged. Verification is never carried across a changed cache identity.

## Production

Production creation and installation are separate:

```bash
./scripts/build-release.sh
./scripts/install-production.sh
```

The release command requires a clean local `main` exactly synchronized with
`origin/main`, validates workspace pins, builds the pinned revisions, runs the
workspace and focused Chromium suites, and records strict code-signing proof.

The install command never runs Ninja. It rejects missing, stale, mismatched, or
unverified artifacts; stages and signs a temporary bundle; verifies it; and
then atomically replaces `/Applications/Evo.app`. It does not launch Evo or
read, reset, migrate, or modify the production profile.

## Diagnostics and cleanup

The current lock owner is readable at:

```bash
cat "$HOME/Library/Application Support/Evo Build/lock/owner.json"
```

Do not manually delete a live lock. If its PID is gone, the next supported
command reclaims it. Raw Chromium commands remain available for exceptional
diagnosis, but they are outside Evo's supported workflow and must not target a
feature worktree's `out/` directory.

## Initial migration measurements

Measured on the initial Xcode 26.6 migration on July 25, 2026:

| Operation | Result | Wall time |
|---|---:|---:|
| Stable-Xcode migration and warm-up | 22,396 actions | 2h 16m 49.7s |
| Immediate no-op Dev build/package | 0 compile actions | 23.9s |
| One-file Evo feature commit | 3 actions | 26.3s |
| Feature commit back to pinned main | 3 actions | 25.0s |

The canonical cache occupies 9.0 GB. Removing the validated noncanonical
spaces and hybrid outputs reclaimed about 11 GB and left one Chromium output
cache. Production promotion was not timed during agent verification because
only Sam may operate `/Applications/Evo.app`; the promotion implementation is
covered with a temporary-app integration test and never invokes Ninja.
