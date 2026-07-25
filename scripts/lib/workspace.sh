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

is_git_worktree_root() {
    local path="$1"
    local top_level
    [[ -d "${path}" ]] || return 1
    top_level="$(git -C "${path}" rev-parse --show-toplevel 2>/dev/null)" || return 1
    [[ "$(cd "${path}" && pwd -P)" == "$(cd "${top_level}" && pwd -P)" ]]
}

require_git_repository() {
    if ! is_git_worktree_root "$1"; then
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

read_pinned_chromium_file() {
    local relative_path="$1"
    git -C "${canonical_chromium_src}" show \
        "$(manifest_value chromium.evoRevision):${relative_path}"
}

default_runtime_dir="${workspace_root}/$(manifest_value components.runtime.path)"
if ! is_git_worktree_root "${default_runtime_dir}" && [[ "${workspace_root}" != "${canonical_workspace_root}" ]]; then
    default_runtime_dir="${canonical_workspace_root}/$(manifest_value components.runtime.path)"
fi
runtime_dir="${EVO_RUNTIME_DIR:-${default_runtime_dir}}"

default_opencode_dir="${workspace_root}/$(manifest_value components.opencode.path)"
if ! is_git_worktree_root "${default_opencode_dir}" && [[ "${workspace_root}" != "${canonical_workspace_root}" ]]; then
    default_opencode_dir="${canonical_workspace_root}/$(manifest_value components.opencode.path)"
fi
opencode_dir="${EVO_OPENCODE_DIR:-${default_opencode_dir}}"
depot_tools_dir="${DEPOT_TOOLS_DIR:-${canonical_workspace_root}/depot_tools}"

dev_profile_dir="${EVO_DEV_PROFILE_DIR:-${HOME}/Library/Application Support/Evo Chromium Dev}"
dev_runtime_state_dir="${EVO_DEV_RUNTIME_STATE_DIR:-${HOME}/Library/Application Support/Evo Runtime Dev}"
dev_sidekick_workspace="${EVO_DEV_SIDEKICK_WORKSPACE:-${HOME}/.evo/sidekick-dev}"

require_safe_dev_paths() {
    python3 - \
        "${dev_profile_dir}" "${HOME}/Library/Application Support/Evo Chromium" \
        "${dev_runtime_state_dir}" "${HOME}/Library/Application Support/Evo Runtime" \
        "${dev_sidekick_workspace}" "${HOME}/.evo/sidekick" <<'PY'
import pathlib
import sys

labels = ("profile", "runtime state", "Sidekick workspace")
for index, label in enumerate(labels):
    candidate = pathlib.Path(sys.argv[1 + index * 2]).expanduser().resolve()
    protected = pathlib.Path(sys.argv[2 + index * 2]).expanduser().resolve()
    try:
        candidate.relative_to(protected)
    except ValueError:
        continue
    raise SystemExit(
        f"Evo Dev {label} resolves inside protected production state: {candidate}"
    )
PY
    export EVO_DEV_PROFILE_DIR="${dev_profile_dir}"
    export EVO_DEV_RUNTIME_STATE_DIR="${dev_runtime_state_dir}"
    export EVO_DEV_SIDEKICK_WORKSPACE="${dev_sidekick_workspace}"
}
