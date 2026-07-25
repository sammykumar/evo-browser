#!/usr/bin/env bash

set -euo pipefail

workspace_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest="${workspace_root}/workspace.json"

manifest_value() {
    python3 - "${manifest}" "$1" <<'PY'
import json
import sys

value = json.load(open(sys.argv[1], encoding="utf-8"))
for key in sys.argv[2].split("."):
    value = value[key]
print(value)
PY
}

require_directory() {
    if [[ ! -d "$1" ]]; then
        echo "$2 was not found at $1" >&2
        exit 1
    fi
}

require_git_repository() {
    if ! git -C "$1" rev-parse --git-dir >/dev/null 2>&1; then
        echo "$2 was not found at $1" >&2
        exit 1
    fi
}

git_common_dir="$(git -C "${workspace_root}" rev-parse --git-common-dir)"
if [[ "${git_common_dir}" != /* ]]; then
    git_common_dir="$(cd "${workspace_root}/${git_common_dir}" && pwd -P)"
fi
canonical_workspace_root="$(cd "$(dirname "${git_common_dir}")" && pwd -P)"
chromium_checkout_path="$(manifest_value chromium.checkoutPath)"
canonical_chromium_src="${EVO_CANONICAL_CHROMIUM_SRC:-${canonical_workspace_root}/${chromium_checkout_path}}"
canonical_out_dir="${canonical_chromium_src}/$(manifest_value build.canonicalOutput)"
chromium_src="${EVO_CHROMIUM_SRC:-${workspace_root}/${chromium_checkout_path}}"

default_runtime_dir="${workspace_root}/$(manifest_value components.runtime.path)"
if [[ ! -d "${default_runtime_dir}" && "${workspace_root}" != "${canonical_workspace_root}" ]]; then
    default_runtime_dir="${canonical_workspace_root}/$(manifest_value components.runtime.path)"
fi
runtime_dir="${EVO_RUNTIME_DIR:-${default_runtime_dir}}"

default_opencode_dir="${workspace_root}/$(manifest_value components.opencode.path)"
if [[ ! -d "${default_opencode_dir}" && "${workspace_root}" != "${canonical_workspace_root}" ]]; then
    default_opencode_dir="${canonical_workspace_root}/$(manifest_value components.opencode.path)"
fi
opencode_dir="${EVO_OPENCODE_DIR:-${default_opencode_dir}}"
depot_tools_dir="${DEPOT_TOOLS_DIR:-${canonical_workspace_root}/depot_tools}"
