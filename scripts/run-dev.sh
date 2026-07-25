#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/workspace.sh"

"${workspace_root}/scripts/build-dev.sh"

dev_app="${canonical_chromium_src}/out/EvoDev/Evo Dev.app"
dev_profile_dir="${EVO_DEV_PROFILE_DIR:-${HOME}/Library/Application Support/Evo Chromium Dev}"
open -n "${dev_app}" --args \
    "--user-data-dir=${dev_profile_dir}" \
    --enable-features=EvoHybridBrowserShell \
    --use-mock-keychain \
    --no-first-run \
    "$@"
