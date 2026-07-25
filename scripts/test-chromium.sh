#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/workspace.sh"

targets=()
unit_filter=""
browser_filter=""
interactive_filter=""
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
        --interactive-filter)
            interactive_filter="$2"
            shift 2
            ;;
        *)
            echo "Usage: ./scripts/test-chromium.sh [--target NAME] [--unit-filter FILTER] [--browser-filter FILTER] [--interactive-filter FILTER]" >&2
            exit 2
            ;;
    esac
done

if ((${#targets[@]} == 0)); then
    if [[ -n "${unit_filter}" ]]; then
        targets+=(unit_tests)
    fi
    if [[ -n "${browser_filter}" ]]; then
        targets+=(browser_tests)
    fi
    if ((${#targets[@]} == 0)); then
        targets=(unit_tests browser_tests)
        unit_filter='EvoShell*:*EvoSpaceTheme*'
        browser_filter='EvoShellUIBrowserTest.*'
    fi
fi

has_unit_target=0
has_browser_target=0
has_interactive_target=0
for target in "${targets[@]}"; do
    [[ "${target}" == "unit_tests" ]] && has_unit_target=1
    [[ "${target}" == "browser_tests" ]] && has_browser_target=1
    [[ "${target}" == "interactive_ui_tests" ]] && has_interactive_target=1
done
if [[ -n "${unit_filter}" && "${has_unit_target}" != "1" ]]; then
    echo "--unit-filter requires --target unit_tests." >&2
    exit 2
fi
if [[ -n "${browser_filter}" && "${has_browser_target}" != "1" ]]; then
    echo "--browser-filter requires --target browser_tests." >&2
    exit 2
fi
if [[ -n "${interactive_filter}" && "${has_interactive_target}" != "1" ]]; then
    echo "--interactive-filter requires --target interactive_ui_tests." >&2
    exit 2
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
if [[ -n "${interactive_filter}" ]]; then
    lane_args+=(--record-suite "interactive:${interactive_filter}")
    test_args+=(--interactive-filter "${interactive_filter}")
fi

python3 "${workspace_root}/scripts/evo-build-lane.py" run \
    --requesting-root "${workspace_root}" \
    --requesting-chromium "${chromium_src}" \
    --runtime-dir "${runtime_dir}" \
    --operation "Chromium tests" \
    "${lane_args[@]}" \
    -- "${workspace_root}/scripts/lib/run-chromium-tests.sh" "${test_args[@]}"
