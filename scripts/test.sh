#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/workspace.sh"

PYTHONPATH="${workspace_root}${PYTHONPATH:+:${PYTHONPATH}}" python3 -m unittest discover \
    -s "${workspace_root}/scripts/tests" \
    -p 'test_*.py' \
    -v

"${workspace_root}/scripts/check-workspace.sh"

if ! read_pinned_chromium_file \
    "chrome/browser/ui/evo_shell/evo_shell_features.cc" | rg -q \
    'BASE_FEATURE\(kEvoHybridBrowserShell, base::FEATURE_ENABLED_BY_DEFAULT\)'; then
    echo "Production promotion requires EvoHybridBrowserShell to be enabled by default." >&2
    exit 1
fi

bun_bin="${BUN_BIN:-/opt/homebrew/bin/bun}"
if [[ ! -x "${bun_bin}" ]]; then
    echo "Bun was not found at ${bun_bin}." >&2
    exit 1
fi

if [[ ! -d "${runtime_dir}/node_modules" || ! -d "${opencode_dir}/node_modules" ]]; then
    "${workspace_root}/scripts/bootstrap.sh"
fi

"${bun_bin}" run --cwd "${runtime_dir}" test
"${bun_bin}" run --cwd "${runtime_dir}" typecheck

if [[ -f "${opencode_dir}/packages/opencode/package.json" ]]; then
    "${bun_bin}" run --cwd "${opencode_dir}/packages/opencode" typecheck
fi

echo "Evo workspace tests passed."
