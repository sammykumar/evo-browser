#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/workspace.sh"

require_git_repository "${chromium_src}" "Requesting Chromium worktree"
require_directory "${canonical_chromium_src}/evo" "Canonical Evo Chromium layer"
require_directory "${runtime_dir}" "Evo Runtime"

echo "Regenerating the one shared Chromium cache with the pinned Xcode and GN arguments."
python3 "${workspace_root}/scripts/evo-build-lane.py" run \
    --requesting-root "${workspace_root}" \
    --requesting-chromium "${chromium_src}" \
    --runtime-dir "${runtime_dir}" \
    --operation "migrate shared cache and build Dev" \
    --allow-cache-migration \
    --record-target chrome \
    --bundle-path "${canonical_chromium_src}/out/EvoDev/Evo Dev.app" \
    -- "${canonical_chromium_src}/evo/build-dev.sh"
