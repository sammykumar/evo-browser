#!/usr/bin/env python3
"""Coordinator primitives for Evo's shared Chromium build lane."""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Mapping, Sequence


class BuildLaneError(RuntimeError):
    """A user-actionable shared build-lane failure."""


def _git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True
    ).strip()


def discover_primary_checkout(requesting_root: Path) -> Path:
    """Return the primary checkout that owns a root repository's common dir."""
    common_dir = Path(_git(requesting_root, "rev-parse", "--git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = requesting_root / common_dir
    return common_dir.resolve().parent


def requested_revision(
    requesting_chromium: Path,
    *,
    allowed_untracked_prefixes: tuple[str, ...] = ("third_party/llvm-libclang/",),
) -> str:
    """Resolve a revision only when every relevant caller input is committed."""
    status = _git(
        requesting_chromium,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    unexpected: list[str] = []
    for line in status.splitlines():
        path = line[3:]
        if line.startswith("?? ") and path.startswith(allowed_untracked_prefixes):
            continue
        unexpected.append(line)
    if unexpected:
        details = "\n".join(unexpected)
        raise BuildLaneError(
            "The requesting Chromium worktree must be fully committed before "
            f"using the shared build lane:\n{details}"
        )
    return _git(requesting_chromium, "rev-parse", "HEAD")


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class BuildLock:
    """Machine-wide, inspectable, stale-owner-aware build serialization."""

    def __init__(
        self,
        state_dir: Path,
        metadata: Mapping[str, object],
        *,
        poll_interval: float = 30,
        pid_is_alive: Callable[[int], bool] = _pid_is_alive,
        sleeper: Callable[[float], None] = time.sleep,
        reporter: Callable[[str], None] = print,
    ) -> None:
        self.state_dir = state_dir
        self.lock_dir = state_dir / "lock"
        self.owner_path = self.lock_dir / "owner.json"
        self.metadata = dict(metadata)
        self.poll_interval = poll_interval
        self.pid_is_alive = pid_is_alive
        self.sleeper = sleeper
        self.reporter = reporter
        self.acquired = False

    def _read_owner(self) -> dict[str, object]:
        try:
            return json.loads(self.owner_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def acquire(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.lock_dir.mkdir()
            except FileExistsError:
                owner = self._read_owner()
                owner_pid = owner.get("pid")
                if isinstance(owner_pid, int) and not self.pid_is_alive(owner_pid):
                    reclaimed = self.state_dir / (
                        f"lock.stale.{os.getpid()}.{uuid.uuid4().hex}"
                    )
                    try:
                        os.replace(self.lock_dir, reclaimed)
                    except FileNotFoundError:
                        continue
                    shutil.rmtree(reclaimed, ignore_errors=True)
                    continue
                command = owner.get("command", "unknown operation")
                worktree = owner.get("requestingWorktree", "unknown worktree")
                self.reporter(
                    f"Evo build lane is busy with {command} from {worktree}; "
                    f"waiting {self.poll_interval:g} seconds."
                )
                self.sleeper(self.poll_interval)
                continue

            owner = {"pid": os.getpid(), **self.metadata}
            _write_json_atomic(self.owner_path, owner)
            self.acquired = True
            return

    def release(self) -> None:
        if not self.acquired:
            return
        owner = self._read_owner()
        if owner.get("pid") == os.getpid():
            shutil.rmtree(self.lock_dir, ignore_errors=True)
        self.acquired = False

    def __enter__(self) -> "BuildLock":
        self.acquire()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.release()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        _git(repo, "status", "--porcelain=v1", "--untracked-files=no").strip()
    )


@contextmanager
def temporary_checkout(repo: Path, target_revision: str) -> Iterator[None]:
    """Detach at a build revision and always restore the canonical checkout."""
    if _tracked_changes(repo):
        raise BuildLaneError(
            f"Canonical Chromium checkout has tracked modifications: {repo}"
        )
    original_revision = _git(repo, "rev-parse", "HEAD")
    original_branch = _git(repo, "branch", "--show-current")
    _git(repo, "cat-file", "-e", f"{target_revision}^{{commit}}")
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "--quiet", "--detach", target_revision],
        check=True,
    )
    try:
        yield
    finally:
        unexpected_changes = _tracked_changes(repo)
        if unexpected_changes:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "stash",
                    "push",
                    "--message",
                    "evo-build-lane-recovery",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        destination = original_branch or original_revision
        subprocess.run(
            ["git", "-C", str(repo), "checkout", "--quiet", destination],
            check=True,
        )
        if unexpected_changes:
            raise BuildLaneError(
                "The build operation changed tracked files. The original checkout "
                "was restored and the unexpected changes were preserved in stash "
                "evo-build-lane-recovery for inspection."
            )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_cache_identity(
    out_dir: Path,
    source_args: Path,
    *,
    xcode_version: str,
    xcode_build: str,
    allow_migration: bool = False,
) -> None:
    """Reject an output cache created for another toolchain or GN config."""
    migration = (
        "Run ./scripts/migrate-build-cache.sh to perform the intentional "
        "one-time cache migration."
    )
    manifest_path = out_dir / "evo-build-manifest.json"
    if allow_migration:
        return
    if out_dir.exists() and any(out_dir.iterdir()) and not manifest_path.exists():
        raise BuildLaneError(
            "The existing Chromium cache has no build manifest, so its toolchain "
            f"identity is unknown. {migration}"
        )
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise BuildLaneError(
                "The Chromium cache manifest is malformed; cache migration is "
                f"required. {migration}"
            ) from error
        toolchain = manifest.get("toolchain", {})
        if (
            toolchain.get("xcodeVersion") != xcode_version
            or toolchain.get("xcodeBuild") != xcode_build
        ):
            raise BuildLaneError(
                "The Chromium cache was created by a different Xcode toolchain; "
                f"cache migration is required. {migration}"
            )

    output_args = out_dir / "args.gn"
    if output_args.exists() and sha256_file(output_args) != sha256_file(source_args):
        raise BuildLaneError(
            "evo/args.gn changed since this Chromium cache was configured; "
            f"cache migration is required. {migration}"
        )


def _verify_signature(app_path: Path) -> bool:
    return (
        subprocess.run(
            ["codesign", "--verify", "--deep", "--strict", str(app_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def read_bundle_metadata(
    app_path: Path,
    *,
    signature_verifier: Callable[[Path], bool] = _verify_signature,
) -> dict[str, object]:
    info_path = app_path / "Contents" / "Info.plist"
    if not info_path.is_file():
        raise BuildLaneError(f"App bundle metadata was not found at {info_path}.")
    with info_path.open("rb") as source:
        info = plistlib.load(source)
    return {
        "path": str(app_path),
        "bundleIdentifier": info.get("CFBundleIdentifier", ""),
        "version": info.get("CFBundleShortVersionString", ""),
        "buildVersion": info.get("CFBundleVersion", ""),
        "signatureVerified": signature_verifier(app_path),
    }


def read_xcode_identity(developer_dir: Path) -> tuple[str, str]:
    environment = os.environ.copy()
    environment["DEVELOPER_DIR"] = str(developer_dir)
    output = subprocess.check_output(
        ["/usr/bin/xcodebuild", "-version"], text=True, env=environment
    ).splitlines()
    if len(output) < 2 or not output[0].startswith("Xcode "):
        raise BuildLaneError("Unable to determine the active Xcode version.")
    version = output[0].removeprefix("Xcode ").strip()
    build = output[1].removeprefix("Build version ").strip()
    return version, build


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def execute_lane(
    *,
    requesting_root: Path,
    requesting_chromium: Path,
    runtime_dir: Path,
    operation: str,
    command: Sequence[str],
    build_targets: Sequence[str] = (),
    verification_suites: Sequence[str] = (),
    bundle_path: Path | None = None,
    verified_for_production: bool = False,
    allow_cache_migration: bool = False,
    state_dir: Path | None = None,
    toolchain_reader: Callable[[Path], tuple[str, str]] = read_xcode_identity,
    timestamp_factory: Callable[[], str] = utc_timestamp,
) -> int:
    """Execute one committed Chromium revision in the canonical build lane."""
    requesting_root = requesting_root.resolve()
    requesting_chromium = requesting_chromium.resolve()
    runtime_dir = runtime_dir.resolve()
    workspace_manifest = _load_json(requesting_root / "workspace.json")
    chromium_config = workspace_manifest.get("chromium", {})
    build_config = workspace_manifest.get("build", {})
    xcode_config = build_config.get("xcode", {})
    try:
        checkout_path = chromium_config["checkoutPath"]
        output_relative = build_config["canonicalOutput"]
        developer_dir = Path(xcode_config["developerDir"])
        expected_xcode_version = xcode_config["version"]
        expected_xcode_build = xcode_config["build"]
    except (KeyError, TypeError) as error:
        raise BuildLaneError(
            "workspace.json is missing the shared Chromium build configuration."
        ) from error

    target_revision = requested_revision(requesting_chromium)
    runtime_revision = requested_revision(
        runtime_dir, allowed_untracked_prefixes=()
    )
    canonical_root = discover_primary_checkout(requesting_root)
    canonical_chromium = (canonical_root / str(checkout_path)).resolve()
    out_dir = (canonical_chromium / str(output_relative)).resolve()
    manifest_path = out_dir / "evo-build-manifest.json"
    if not canonical_chromium.is_dir():
        raise BuildLaneError(
            f"Canonical Chromium checkout was not found at {canonical_chromium}."
        )

    actual_xcode_version, actual_xcode_build = toolchain_reader(developer_dir)
    if (
        actual_xcode_version != expected_xcode_version
        or actual_xcode_build != expected_xcode_build
    ):
        raise BuildLaneError(
            "The active Xcode does not match the pinned build lane: expected "
            f"Xcode {expected_xcode_version} ({expected_xcode_build}), found "
            f"Xcode {actual_xcode_version} ({actual_xcode_build})."
        )

    state_dir = state_dir or Path(
        os.environ.get(
            "EVO_BUILD_STATE_DIR",
            str(Path.home() / "Library" / "Application Support" / "Evo Build"),
        )
    )
    started_at = timestamp_factory()
    lock_metadata = {
        "requestingWorktree": str(requesting_root),
        "targetCommit": target_revision,
        "command": operation,
        "startTime": started_at,
    }

    manifest_payload: dict[str, object] | None = None
    with BuildLock(state_dir, lock_metadata):
        with temporary_checkout(canonical_chromium, target_revision):
            source_args = canonical_chromium / "evo" / "args.gn"
            validate_cache_identity(
                out_dir,
                source_args,
                xcode_version=actual_xcode_version,
                xcode_build=actual_xcode_build,
                allow_migration=allow_cache_migration,
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "DEVELOPER_DIR": str(developer_dir),
                    "EVO_BUILD_LANE_ACTIVE": "1",
                    "EVO_CANONICAL_WORKSPACE_ROOT": str(canonical_root),
                    "EVO_CANONICAL_CHROMIUM_SRC": str(canonical_chromium),
                    "EVO_OUT_DIR": str(out_dir),
                    "EVO_DEV_OUT_DIR": str(canonical_chromium / "out" / "EvoDev"),
                    "EVO_RUNTIME_DIR": str(runtime_dir),
                    "DEPOT_TOOLS_DIR": str(canonical_root / "depot_tools"),
                }
            )
            if allow_cache_migration:
                out_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_args, out_dir / "args.gn")
                gn = canonical_root / "depot_tools" / "gn"
                generated = subprocess.run(
                    [str(gn), "gen", str(out_dir)],
                    cwd=canonical_chromium,
                    env=environment,
                    check=False,
                )
                if generated.returncode != 0:
                    return generated.returncode

            completed = subprocess.run(
                list(command),
                cwd=canonical_chromium,
                env=environment,
                check=False,
            )
            if completed.returncode != 0:
                return completed.returncode

            identity: dict[str, object] = {
                "chromiumRevision": target_revision,
                "runtimeRevision": runtime_revision,
                "gnArgumentsHash": sha256_file(source_args),
                "toolchain": {
                    "developerDir": str(developer_dir),
                    "xcodeVersion": actual_xcode_version,
                    "xcodeBuild": actual_xcode_build,
                },
            }
            previous = _load_json(manifest_path)
            bundle = read_bundle_metadata(bundle_path) if bundle_path else None
            if verified_for_production:
                validate_production_bundle({"bundle": bundle or {}})
            manifest_payload = next_manifest(
                previous,
                identity,
                build_targets=build_targets,
                verification_suites=verification_suites,
                verified_for_production=verified_for_production,
                timestamp=timestamp_factory(),
                bundle=bundle,
            )
            manifest_payload["lastOperation"] = operation

        if manifest_payload is not None:
            _write_json_atomic(manifest_path, manifest_payload)
    return 0


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as destination:
            json.dump(payload, destination, indent=2, sort_keys=True)
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


_IDENTITY_KEYS = (
    "chromiumRevision",
    "runtimeRevision",
    "gnArgumentsHash",
    "toolchain",
)


def _same_identity(
    manifest: Mapping[str, object], identity: Mapping[str, object]
) -> bool:
    return all(manifest.get(key) == identity.get(key) for key in _IDENTITY_KEYS)


def next_manifest(
    previous: Mapping[str, object] | None,
    identity: Mapping[str, object],
    *,
    build_targets: Sequence[str],
    verification_suites: Sequence[str],
    verified_for_production: bool,
    timestamp: str,
    bundle: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Merge successful results without carrying proof across cache identities."""
    previous = previous or {}
    same_identity = _same_identity(previous, identity)
    old_targets = previous.get("completedBuildTargets", []) if same_identity else []
    old_suites = (
        previous.get("completedVerificationSuites", []) if same_identity else []
    )
    result: dict[str, object] = {
        "schemaVersion": 1,
        **identity,
        "completedBuildTargets": sorted(set(old_targets) | set(build_targets)),
        "completedVerificationSuites": sorted(
            set(old_suites) | set(verification_suites)
        ),
        "verifiedForProduction": verified_for_production
        or bool(previous.get("verifiedForProduction", False) and same_identity),
        "timestamp": timestamp,
    }
    if bundle is not None:
        result["bundle"] = dict(bundle)
    elif same_identity and "bundle" in previous:
        result["bundle"] = previous["bundle"]
    return result


def validate_release_manifest(
    manifest: Mapping[str, object],
    expected_identity: Mapping[str, object],
    *,
    required_targets: Sequence[str],
    required_suites: Sequence[str],
) -> None:
    if not _same_identity(manifest, expected_identity):
        raise BuildLaneError(
            "The shared artifact does not match the revisions and cache identity "
            "pinned by main. Run ./scripts/build-release.sh first."
        )
    missing_targets = sorted(
        set(required_targets) - set(manifest.get("completedBuildTargets", []))
    )
    missing_suites = sorted(
        set(required_suites)
        - set(manifest.get("completedVerificationSuites", []))
    )
    if missing_targets or missing_suites:
        missing = ", ".join(missing_targets + missing_suites)
        raise BuildLaneError(
            f"The shared artifact lacks required release verification: {missing}. "
            "Run ./scripts/build-release.sh first."
        )
    if not manifest.get("verifiedForProduction"):
        raise BuildLaneError(
            "The shared artifact is not verified for production. "
            "Run ./scripts/build-release.sh first."
        )


def validate_production_bundle(manifest: Mapping[str, object]) -> None:
    bundle = manifest.get("bundle", {})
    if (
        not isinstance(bundle, Mapping)
        or bundle.get("bundleIdentifier") != "com.skproductions.evo"
        or bundle.get("signatureVerified") is not True
    ):
        raise BuildLaneError(
            "The manifest does not describe a strictly signed production bundle. "
            "Run ./scripts/build-release.sh first."
        )


def git_blob_sha256(repo: Path, revision: str, relative_path: str) -> str:
    contents = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{revision}:{relative_path}"]
    )
    return hashlib.sha256(contents).hexdigest()


def expected_identity_from_workspace(
    workspace_manifest: Mapping[str, object], canonical_chromium: Path
) -> dict[str, object]:
    chromium = workspace_manifest["chromium"]
    components = workspace_manifest["components"]
    build = workspace_manifest["build"]
    revision = chromium["evoRevision"]
    xcode = build["xcode"]
    return {
        "chromiumRevision": revision,
        "runtimeRevision": components["runtime"]["revision"],
        "gnArgumentsHash": git_blob_sha256(
            canonical_chromium, str(revision), "evo/args.gn"
        ),
        "toolchain": {
            "developerDir": xcode["developerDir"],
            "xcodeVersion": xcode["version"],
            "xcodeBuild": xcode["build"],
        },
    }


def validate_release_root(root: Path) -> None:
    branch = _git(root, "branch", "--show-current")
    if branch != "main":
        raise BuildLaneError(
            f"Release builds require the main branch; current branch is {branch or 'detached'}."
        )
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise BuildLaneError("Release builds require a clean local main worktree.")
    local = _git(root, "rev-parse", "HEAD")
    try:
        remote = _git(root, "rev-parse", "refs/remotes/origin/main")
    except subprocess.CalledProcessError as error:
        raise BuildLaneError(
            "origin/main is unavailable; fetch it before building a release."
        ) from error
    if local != remote:
        raise BuildLaneError(
            "Local main must be synchronized exactly with origin/main before a release."
        )


def _ditto(source: Path, destination: Path) -> None:
    subprocess.run(
        ["/usr/bin/ditto", str(source), str(destination)], check=True
    )


def promote_app(
    source_app: Path,
    out_dir: Path,
    install_app: Path,
    *,
    signer: Callable[[Path], None],
    signature_verifier: Callable[[Path], bool] = _verify_signature,
    copier: Callable[[Path, Path], None] = _ditto,
) -> None:
    """Stage, sign, verify, and atomically replace a production app bundle."""
    if not source_app.is_dir():
        raise BuildLaneError(f"Verified source app was not found at {source_app}.")
    install_app.parent.mkdir(parents=True, exist_ok=True)
    nonce = uuid.uuid4().hex
    staging = install_app.parent / f".{install_app.name}.staging.{nonce}"
    backup = install_app.parent / f".{install_app.name}.backup.{nonce}"
    replaced_existing = False
    try:
        copier(source_app, staging)
        frameworks = staging / "Contents" / "Frameworks"
        frameworks.mkdir(parents=True, exist_ok=True)
        for library in out_dir.glob("*.dylib"):
            copier(library, frameworks / library.name)
        signer(staging)
        if not signature_verifier(staging):
            raise BuildLaneError(
                f"Staged production app failed strict signature verification: {staging}"
            )
        if install_app.exists():
            os.replace(install_app, backup)
            replaced_existing = True
        os.replace(staging, install_app)
        if not signature_verifier(install_app):
            raise BuildLaneError(
                f"Installed production app failed strict signature verification: {install_app}"
            )
        if backup.exists():
            shutil.rmtree(backup)
    except BaseException:
        if replaced_existing and backup.exists():
            if install_app.exists():
                shutil.rmtree(install_app, ignore_errors=True)
            os.replace(backup, install_app)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if backup.exists() and install_app.exists():
            shutil.rmtree(backup, ignore_errors=True)
