#!/usr/bin/env bash

set -euo pipefail

workspace_root="${1:?workspace root is required}"
chromium_src="${EVO_CANONICAL_CHROMIUM_SRC:?canonical Chromium source is required}"
out_dir="${EVO_OUT_DIR:?EVO_OUT_DIR is required}"

"${chromium_src}/evo/build.sh"
EVO_CHROMIUM_SRC="${chromium_src}" \
EVO_RUNTIME_DIR="${EVO_RUNTIME_DIR}" \
DEPOT_TOOLS_DIR="${DEPOT_TOOLS_DIR}" \
    "${workspace_root}/scripts/test.sh"
"${workspace_root}/scripts/lib/run-chromium-tests.sh" \
    --target unit_tests \
    --target browser_tests \
    --unit-filter 'EvoShell*:*EvoSpaceTheme*' \
    --browser-filter 'EvoShellUIBrowserTest.*'
codesign --verify --deep --strict "${out_dir}/Evo.app"
