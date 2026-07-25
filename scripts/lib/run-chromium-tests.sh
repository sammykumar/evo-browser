#!/usr/bin/env bash

set -euo pipefail

out_dir="${EVO_OUT_DIR:?EVO_OUT_DIR is required}"
depot_tools_dir="${DEPOT_TOOLS_DIR:?DEPOT_TOOLS_DIR is required}"
unit_filter=""
browser_filter=""
targets=()

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
            echo "Unknown Chromium test option: $1" >&2
            exit 2
            ;;
    esac
done

if ((${#targets[@]} == 0)); then
    echo "At least one Chromium build target is required." >&2
    exit 2
fi

export PATH="${depot_tools_dir}:/usr/bin:/bin:/usr/sbin:/sbin"
autoninja -C "${out_dir}" --quiet -heartbeat_period=30s "${targets[@]}"

for target in "${targets[@]}"; do
    case "${target}" in
        unit_tests)
            if [[ -n "${unit_filter}" ]]; then
                "${out_dir}/unit_tests" "--gtest_filter=${unit_filter}"
            fi
            ;;
        browser_tests)
            if [[ -n "${browser_filter}" ]]; then
                "${out_dir}/browser_tests" "--gtest_filter=${browser_filter}"
            fi
            ;;
    esac
done
