#!/usr/bin/env python3
"""CLI for Evo's serialized, revision-aware Chromium build lane."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from lib import build_lane


def _run(args: argparse.Namespace) -> int:
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise build_lane.BuildLaneError("A build-lane command is required after --.")
    return build_lane.execute_lane(
        requesting_root=args.requesting_root,
        requesting_chromium=args.requesting_chromium,
        runtime_dir=args.runtime_dir,
        operation=args.operation,
        command=command,
        build_targets=args.record_target,
        verification_suites=args.record_suite,
        bundle_path=args.bundle_path,
        verified_for_production=args.verified_for_production,
        allow_cache_migration=args.allow_cache_migration,
    )


def _promote(args: argparse.Namespace) -> int:
    root = args.workspace_root.resolve()
    build_lane.validate_release_root(root)
    workspace = json.loads((root / "workspace.json").read_text(encoding="utf-8"))
    canonical_root = build_lane.discover_primary_checkout(root)
    canonical_chromium = (
        canonical_root / workspace["chromium"]["checkoutPath"]
    ).resolve()
    out_dir = (canonical_chromium / workspace["build"]["canonicalOutput"]).resolve()
    manifest_path = out_dir / "evo-build-manifest.json"
    identity = build_lane.expected_identity_from_workspace(
        workspace, canonical_chromium
    )
    release = workspace["build"]["release"]

    source_app = out_dir / "Evo.app"
    install_app = args.install_path.resolve()
    running = subprocess.run(
        ["pgrep", "-f", f"{install_app}/Contents/MacOS/Evo"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if running.returncode == 0:
        raise build_lane.BuildLaneError(
            "Quit the production Evo app before promoting a verified build."
        )

    state_dir = Path(
        os.environ.get(
            "EVO_BUILD_STATE_DIR",
            str(Path.home() / "Library" / "Application Support" / "Evo Build"),
        )
    )
    with build_lane.BuildLock(
        state_dir,
        {
            "requestingWorktree": str(root),
            "targetCommit": identity["chromiumRevision"],
            "command": "install production",
            "startTime": build_lane.utc_timestamp(),
        },
    ):
        if not manifest_path.is_file():
            raise build_lane.BuildLaneError(
                "No verified shared artifact exists. "
                "Run ./scripts/build-release.sh first."
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        build_lane.validate_release_manifest(
            manifest,
            identity,
            required_targets=release["requiredBuildTargets"],
            required_suites=release["requiredVerificationSuites"],
        )
        build_lane.validate_production_bundle(manifest)
        sign_script = canonical_chromium / "evo" / "sign.sh"

        def signer(app: Path) -> None:
            subprocess.run([str(sign_script), str(app)], check=True)

        build_lane.promote_app(
            source_app,
            out_dir,
            install_app,
            signer=signer,
        )
    print(f"Verified production app installed at {install_app}")
    return 0


def _validate_release_root(args: argparse.Namespace) -> int:
    build_lane.validate_release_root(args.workspace_root.resolve())
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    run = subparsers.add_parser("run", help="run a committed revision in the lane")
    run.add_argument("--requesting-root", type=Path, required=True)
    run.add_argument("--requesting-chromium", type=Path, required=True)
    run.add_argument("--runtime-dir", type=Path, required=True)
    run.add_argument("--operation", required=True)
    run.add_argument("--record-target", action="append", default=[])
    run.add_argument("--record-suite", action="append", default=[])
    run.add_argument("--bundle-path", type=Path)
    run.add_argument("--verified-for-production", action="store_true")
    run.add_argument("--allow-cache-migration", action="store_true")
    run.add_argument("command", nargs=argparse.REMAINDER)
    run.set_defaults(handler=_run)

    release_root = subparsers.add_parser(
        "validate-release-root", help="verify main is clean and synchronized"
    )
    release_root.add_argument("--workspace-root", type=Path, required=True)
    release_root.set_defaults(handler=_validate_release_root)

    promote = subparsers.add_parser(
        "promote", help="install an already verified production artifact"
    )
    promote.add_argument("--workspace-root", type=Path, required=True)
    promote.add_argument(
        "--install-path", type=Path, default=Path("/Applications/Evo.app")
    )
    promote.set_defaults(handler=_promote)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        return args.handler(args)
    except build_lane.BuildLaneError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as error:
        print(f"error: command failed with exit code {error.returncode}", file=sys.stderr)
        return error.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
