#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/workspace.sh"

if (($#)); then
    echo "Usage: ./scripts/build-release.sh" >&2
    exit 2
fi

git -C "${workspace_root}" fetch --quiet origin main
python3 "${workspace_root}/scripts/evo-build-lane.py" validate-release-root \
    --workspace-root "${workspace_root}"
"${workspace_root}/scripts/check-workspace.sh"

expected_chromium="$(manifest_value chromium.evoRevision)"
actual_chromium="$(git -C "${chromium_src}" rev-parse HEAD)"
if [[ "${actual_chromium}" != "${expected_chromium}" ]]; then
    echo "Release Chromium is at ${actual_chromium}; main pins ${expected_chromium}." >&2
    exit 1
fi

python3 "${workspace_root}/scripts/evo-build-lane.py" run \
    --requesting-root "${workspace_root}" \
    --requesting-chromium "${chromium_src}" \
    --runtime-dir "${runtime_dir}" \
    --operation "build and verify release" \
    --record-target chrome \
    --record-target unit_tests \
    --record-target browser_tests \
    --record-suite workspace \
    --record-suite 'unit:EvoShell*:*EvoSpaceTheme*' \
    --record-suite 'browser:EvoShellUIBrowserTest.*' \
    --record-suite 'codesign:strict' \
    --verified-for-production \
    --require-release-root \
    --bundle-path "${canonical_out_dir}/Evo Release.app" \
    -- "${workspace_root}/scripts/lib/build-release-operation.sh" "${workspace_root}"

echo "Verified production artifact: ${canonical_out_dir}/Evo Release.app"
