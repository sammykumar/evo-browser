#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/workspace.sh"

if (($#)); then
    echo "Usage: ./scripts/install-production.sh" >&2
    exit 2
fi

git -C "${workspace_root}" fetch --quiet origin main
python3 "${workspace_root}/scripts/evo-build-lane.py" promote \
    --workspace-root "${workspace_root}" \
    --install-path "${EVO_INSTALL_PATH:-/Applications/Evo.app}"
