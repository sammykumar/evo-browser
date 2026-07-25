#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/workspace.sh"

targets=()
unit_filter=""
browser_filter=""
while (($#)); do
    case "$1" in
        --target)
            targets+=("$2")
            shift 2
            ;;
        --unit-filter)
            unit_filter="$2"
            shift 2
            ;;
        --browser-filter)
            browser_filter="$2"
            shift 2
            ;;
        *)
            echo "Usage: ./scripts/test-chromium.sh [--target NAME] [--unit-filter FILTER] [--browser-filter FILTER]" >&2
            exit 2
            ;;
    esac
done

if ((${#targets[@]} == 0)); then
    targets=(unit_tests browser_tests)
    unit_filter='EvoShell*:*EvoSpaceTheme*'
    browser_filter='EvoShellUIBrowserTest.*'
fi

lane_args=()
test_args=()
for target in "${targets[@]}"; do
    lane_args+=(--record-target "${target}")
    test_args+=(--target "${target}")
done
if [[ -n "${unit_filter}" ]]; then
    lane_args+=(--record-suite "unit:${unit_filter}")
    test_args+=(--unit-filter "${unit_filter}")
fi
if [[ -n "${browser_filter}" ]]; then
    lane_args+=(--record-suite "browser:${browser_filter}")
    test_args+=(--browser-filter "${browser_filter}")
fi

python3 "${workspace_root}/scripts/evo-build-lane.py" run \
    --requesting-root "${workspace_root}" \
    --requesting-chromium "${chromium_src}" \
    --runtime-dir "${runtime_dir}" \
    --operation "Chromium tests" \
    "${lane_args[@]}" \
    -- "${workspace_root}/scripts/lib/run-chromium-tests.sh" "${test_args[@]}"
