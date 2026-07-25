#!/usr/bin/env python3
"""Coordinator primitives for Evo's shared Chromium build lane."""

from __future__ import annotations

import hashlib
import ctypes
import fcntl
import json
import os
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager, nullcontext
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


class BuildLock:
    """Machine-wide serialization backed by a kernel lock inherited by builds."""

    def __init__(
        self,
        state_dir: Path,
        metadata: Mapping[str, object],
        *,
        poll_interval: float = 30,
        sleeper: Callable[[float], None] = time.sleep,
        reporter: Callable[[str], None] = print,
    ) -> None:
        self.state_dir = state_dir
        self.lock_path = state_dir / "lane.lock"
        self.owner_path = state_dir / "owner.json"
        self.metadata = dict(metadata)
        self.poll_interval = poll_interval
        self.sleeper = sleeper
        self.reporter = reporter
        self.acquired = False
        self.file_descriptor: int | None = None
        self.owner_token = uuid.uuid4().hex

    def _read_owner(self) -> dict[str, object]:
        try:
            return json.loads(self.owner_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def acquire(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.file_descriptor = os.open(
            self.lock_path, os.O_RDWR | os.O_CREAT, 0o600
        )
        os.set_inheritable(self.file_descriptor, True)
        while True:
            try:
                fcntl.flock(
                    self.file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB
                )
            except BlockingIOError:
                owner = self._read_owner()
                command = owner.get("command", "unknown operation")
                worktree = owner.get("requestingWorktree", "unknown worktree")
                owner_pid = owner.get("pid", "unknown")
                target = owner.get("targetCommit", "unknown")
                started = owner.get("startTime", "unknown")
                phase = owner.get("phase", "unknown")
                self.reporter(
                    f"Evo build lane is busy: {command}; PID {owner_pid}; "
                    f"worktree {worktree}; target {target}; started {started}; "
                    f"phase {phase}. Waiting {self.poll_interval:g} seconds."
                )
                self.sleeper(self.poll_interval)
                continue
            break

        owner = {
            **self.metadata,
            "pid": os.getpid(),
            "ownerToken": self.owner_token,
            "phase": self.metadata.get("phase", "acquired"),
        }
        try:
            _write_json_atomic(self.owner_path, owner)
        except BaseException:
            fcntl.flock(self.file_descriptor, fcntl.LOCK_UN)
            os.close(self.file_descriptor)
            self.file_descriptor = None
            raise
        self.acquired = True

    def fileno(self) -> int:
        if self.file_descriptor is None:
            raise BuildLaneError("The build lane lock is not acquired.")
        return self.file_descriptor

    @property
    def pass_fds(self) -> tuple[int, ...]:
        return (self.fileno(),)

    def update_phase(self, phase: str) -> None:
        if not self.acquired:
            raise BuildLaneError("Cannot update an unacquired build lane lock.")
        owner = {
            **self.metadata,
            "pid": os.getpid(),
            "ownerToken": self.owner_token,
            "phase": phase,
        }
        _write_json_atomic(self.owner_path, owner)

    def release(self) -> None:
        if not self.acquired:
            return
        owner = self._read_owner()
        if owner.get("ownerToken") == self.owner_token:
            _unlink_durable(self.owner_path)
        if self.file_descriptor is not None:
            fcntl.flock(self.file_descriptor, fcntl.LOCK_UN)
            os.close(self.file_descriptor)
            self.file_descriptor = None
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


def _run_git(
    repo: Path, *args: str, pass_fds: Sequence[int] = ()
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
        pass_fds=tuple(pass_fds),
    )


def recover_checkout_from_journal(
    repo: Path,
    journal_path: Path,
    *,
    pass_fds: Sequence[int] = (),
) -> None:
    """Restore a checkout left detached by a terminated coordinator."""
    if not journal_path.is_file():
        return
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal_repo = Path(str(journal["repository"])).resolve()
        original_revision = str(journal["originalRevision"])
        original_branch = str(journal.get("originalBranch", ""))
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise BuildLaneError(
            f"Checkout recovery journal is malformed: {journal_path}"
        ) from error
    if journal_repo != repo.resolve():
        raise BuildLaneError(
            f"Checkout recovery journal targets {journal_repo}, not {repo.resolve()}."
        )
    unexpected_changes = _tracked_changes(repo)
    if unexpected_changes:
        _run_git(
            repo,
            "stash",
            "push",
            "--message",
            "evo-build-lane-recovery",
            pass_fds=pass_fds,
        )
    destination = original_branch or original_revision
    _run_git(repo, "checkout", "--quiet", destination, pass_fds=pass_fds)
    if _git(repo, "rev-parse", "HEAD") != original_revision:
        raise BuildLaneError(
            "The canonical Chromium branch moved while checkout recovery was "
            "pending; manual inspection is required."
        )
    _unlink_durable(journal_path)
    if unexpected_changes:
        raise BuildLaneError(
            "A terminated build changed tracked files. The original checkout was "
            "restored and those changes were preserved in stash "
            "evo-build-lane-recovery for inspection."
        )


@contextmanager
def temporary_checkout(
    repo: Path,
    target_revision: str,
    *,
    journal_path: Path | None = None,
    pass_fds: Sequence[int] = (),
) -> Iterator[None]:
    """Detach at a build revision and always restore the canonical checkout."""
    if _tracked_changes(repo):
        raise BuildLaneError(
            f"Canonical Chromium checkout has tracked modifications: {repo}"
        )
    original_revision = _git(repo, "rev-parse", "HEAD")
    original_branch = _git(repo, "branch", "--show-current")
    _git(repo, "cat-file", "-e", f"{target_revision}^{{commit}}")
    if journal_path is not None:
        _write_json_atomic(
            journal_path,
            {
                "repository": str(repo.resolve()),
                "originalBranch": original_branch,
                "originalRevision": original_revision,
                "targetRevision": target_revision,
                "coordinatorPid": os.getpid(),
                "createdAt": utc_timestamp(),
            },
        )
    try:
        _run_git(
            repo,
            "checkout",
            "--quiet",
            "--detach",
            target_revision,
            pass_fds=pass_fds,
        )
        yield
    finally:
        if journal_path is not None:
            recover_checkout_from_journal(
                repo, journal_path, pass_fds=pass_fds
            )
        else:
            unexpected_changes = _tracked_changes(repo)
            if unexpected_changes:
                _run_git(
                    repo,
                    "stash",
                    "push",
                    "--message",
                    "evo-build-lane-recovery",
                    pass_fds=pass_fds,
                )
            destination = original_branch or original_revision
            _run_git(
                repo, "checkout", "--quiet", destination, pass_fds=pass_fds
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


def _hash_field(digest: "hashlib._Hash", value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def artifact_sha256(root: Path) -> str:
    """Hash an app tree's paths, types, modes, symlinks, and file contents."""
    if not root.is_dir():
        raise BuildLaneError(f"App artifact was not found at {root}.")
    digest = hashlib.sha256()
    entries = [root, *sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix())]
    for path in entries:
        relative = "." if path == root else path.relative_to(root).as_posix()
        metadata = path.lstat()
        _hash_field(digest, relative.encode("utf-8"))
        _hash_field(digest, f"{stat.S_IMODE(metadata.st_mode):o}".encode("ascii"))
        if stat.S_ISDIR(metadata.st_mode):
            _hash_field(digest, b"directory")
        elif stat.S_ISLNK(metadata.st_mode):
            _hash_field(digest, b"symlink")
            _hash_field(digest, os.readlink(path).encode("utf-8"))
        elif stat.S_ISREG(metadata.st_mode):
            _hash_field(digest, b"file")
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            raise BuildLaneError(f"Unsupported artifact entry type: {path}")
    return digest.hexdigest()


def validate_cache_identity(
    out_dir: Path,
    source_args: Path,
    *,
    developer_dir: str,
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
        expected_gn_hash = sha256_file(source_args)
        if (
            toolchain.get("developerDir") != developer_dir
            or toolchain.get("xcodeVersion") != xcode_version
            or toolchain.get("xcodeBuild") != xcode_build
            or manifest.get("gnArgumentsHash") != expected_gn_hash
        ):
            raise BuildLaneError(
                "The Chromium cache identity does not match the pinned Xcode path, "
                f"version, build, and GN arguments; cache migration is required. {migration}"
            )

    output_args = out_dir / "args.gn"
    if manifest_path.exists() and not output_args.exists():
        raise BuildLaneError(
            "The Chromium cache is missing out/Evo/args.gn; cache migration is "
            f"required. {migration}"
        )
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
        "artifactSha256": artifact_sha256(app_path),
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


def _remove_snapshot_worktree(
    repository: Path, snapshot: Path, *, pass_fds: Sequence[int]
) -> None:
    result = subprocess.run(
        ["git", "-C", str(repository), "worktree", "remove", "--force", str(snapshot)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        pass_fds=tuple(pass_fds),
    )
    if result.returncode != 0 and snapshot.exists():
        shutil.rmtree(snapshot, ignore_errors=True)
        subprocess.run(
            ["git", "-C", str(repository), "worktree", "prune"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            pass_fds=tuple(pass_fds),
        )


def _contains_workspace_dependency_link(directory: Path, workspace: Path) -> bool:
    workspace = workspace.resolve()
    for current, directory_names, file_names in os.walk(directory):
        current_path = Path(current)
        for name in directory_names + file_names:
            candidate = current_path / name
            if not candidate.is_symlink():
                continue
            try:
                candidate.resolve().relative_to(workspace)
                return True
            except ValueError:
                pass
        directory_names[:] = [
            name for name in directory_names if not (current_path / name).is_symlink()
        ]
    return False


def _materialize_bun_cache(
    source_cache: Path, destination_cache: Path, workspace: Path
) -> None:
    destination_cache.mkdir()
    for source in source_cache.iterdir():
        destination = destination_cache / source.name
        if source.is_symlink():
            destination.symlink_to(
                os.readlink(source), target_is_directory=source.is_dir()
            )
        elif source.is_dir() and _contains_workspace_dependency_link(
            source, workspace
        ):
            shutil.copytree(source, destination, symlinks=True)
        else:
            destination.symlink_to(
                source.resolve(), target_is_directory=source.is_dir()
            )


def _materialize_snapshot_node_modules(repository: Path, snapshot: Path) -> None:
    root_modules = repository / "node_modules"
    if root_modules.is_dir() and not (snapshot / "node_modules").exists():
        snapshot_modules = snapshot / "node_modules"
        snapshot_modules.mkdir()
        for source in root_modules.iterdir():
            destination = snapshot_modules / source.name
            if source.name == ".bun" and source.is_dir():
                _materialize_bun_cache(
                    source, destination, repository / "packages"
                )
            elif source.is_symlink():
                destination.symlink_to(
                    os.readlink(source), target_is_directory=source.is_dir()
                )
            elif source.is_dir():
                shutil.copytree(source, destination, symlinks=True)
            else:
                shutil.copy2(source, destination)

    for current, directory_names, _ in os.walk(repository):
        current_path = Path(current)
        if "node_modules" in directory_names:
            directory_names.remove("node_modules")
            source = current_path / "node_modules"
            if current_path != repository:
                destination = snapshot / source.relative_to(repository)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, destination, symlinks=True)
        if ".git" in directory_names:
            directory_names.remove(".git")


@contextmanager
def immutable_git_snapshot(
    repository: Path,
    revision: str,
    snapshot_parent: Path,
    label: str,
    *,
    pass_fds: Sequence[int] = (),
) -> Iterator[Path]:
    """Materialize committed component inputs without building from mutable source."""
    snapshot_parent.mkdir(parents=True, exist_ok=True)
    for stale in snapshot_parent.glob(f"{label}-*"):
        _remove_snapshot_worktree(repository, stale, pass_fds=pass_fds)
    snapshot = snapshot_parent / f"{label}-{os.getpid()}-{uuid.uuid4().hex}"
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "worktree",
            "add",
            "--detach",
            "--quiet",
            str(snapshot),
            revision,
        ],
        check=True,
        pass_fds=tuple(pass_fds),
    )
    _materialize_snapshot_node_modules(repository, snapshot)
    try:
        yield snapshot
    finally:
        _remove_snapshot_worktree(repository, snapshot, pass_fds=pass_fds)


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
    require_release_root: bool = False,
    state_dir: Path | None = None,
    toolchain_reader: Callable[[Path], tuple[str, str]] = read_xcode_identity,
    timestamp_factory: Callable[[], str] = utc_timestamp,
) -> int:
    """Execute one committed Chromium revision in the canonical build lane."""
    if verified_for_production and not require_release_root:
        raise BuildLaneError(
            "Production verification is release-only and requires synchronized main."
        )
    requesting_root = requesting_root.resolve()
    requesting_chromium = requesting_chromium.resolve()
    runtime_dir = runtime_dir.resolve()
    preflight_target_revision = requested_revision(requesting_chromium)
    preflight_runtime_revision = requested_revision(
        runtime_dir, allowed_untracked_prefixes=()
    )
    canonical_root = discover_primary_checkout(requesting_root)
    state_dir = state_dir or Path(
        os.environ.get(
            "EVO_BUILD_STATE_DIR",
            str(Path.home() / "Library" / "Application Support" / "Evo Build"),
        )
    )
    started_at = timestamp_factory()
    lock_metadata = {
        "requestingWorktree": str(requesting_root),
        "targetCommit": preflight_target_revision,
        "command": operation,
        "startTime": started_at,
    }

    manifest_payload: dict[str, object] | None = None
    with BuildLock(state_dir, lock_metadata) as lane_lock:
        lane_lock.update_phase("revalidating committed inputs")
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
        if target_revision != preflight_target_revision:
            raise BuildLaneError(
                "The requesting Chromium revision changed while waiting for the build lane."
            )
        if runtime_revision != preflight_runtime_revision:
            raise BuildLaneError(
                "The Evo Runtime revision changed while waiting for the build lane."
            )
        release_root_revision: str | None = None
        if require_release_root:
            validate_release_root(requesting_root)
            release_root_revision = _git(requesting_root, "rev-parse", "HEAD")
            components = workspace_manifest.get("components", {})
            if target_revision != chromium_config.get("evoRevision"):
                raise BuildLaneError(
                    "Release Chromium does not match the revision pinned by main."
                )
            if runtime_revision != components.get("runtime", {}).get("revision"):
                raise BuildLaneError(
                    "Release Evo Runtime does not match the revision pinned by main."
                )

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

        lane_lock.update_phase("recovering canonical checkout")
        checkout_journal = state_dir / "checkout-recovery.json"
        recover_checkout_from_journal(
            canonical_chromium,
            checkout_journal,
            pass_fds=lane_lock.pass_fds,
        )
        snapshot_parent = state_dir / "snapshots"
        opencode_dir: Path | None = None
        opencode_revision: str | None = None
        if require_release_root:
            opencode_config = workspace_manifest["components"]["opencode"]
            opencode_dir = (canonical_root / opencode_config["path"]).resolve()
            opencode_revision = requested_revision(
                opencode_dir, allowed_untracked_prefixes=()
            )
            if opencode_revision != opencode_config["revision"]:
                raise BuildLaneError(
                    "Release Evo OpenCode does not match the revision pinned by main."
                )

        with immutable_git_snapshot(
            runtime_dir,
            runtime_revision,
            snapshot_parent,
            "runtime",
            pass_fds=lane_lock.pass_fds,
        ) as runtime_snapshot:
            opencode_context = (
                immutable_git_snapshot(
                    opencode_dir,
                    opencode_revision,
                    snapshot_parent,
                    "opencode",
                    pass_fds=lane_lock.pass_fds,
                )
                if opencode_dir is not None and opencode_revision is not None
                else nullcontext(None)
            )
            with opencode_context as opencode_snapshot:
                lane_lock.update_phase("checking out Chromium target")
                with temporary_checkout(
                    canonical_chromium,
                    target_revision,
                    journal_path=checkout_journal,
                    pass_fds=lane_lock.pass_fds,
                ):
                    source_args = canonical_chromium / "evo" / "args.gn"
                    validate_cache_identity(
                        out_dir,
                        source_args,
                        developer_dir=str(developer_dir),
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
                            "EVO_RUNTIME_DIR": str(runtime_snapshot),
                            "DEPOT_TOOLS_DIR": str(canonical_root / "depot_tools"),
                        }
                    )
                    if opencode_snapshot is not None:
                        environment["EVO_OPENCODE_DIR"] = str(opencode_snapshot)
                    if allow_cache_migration:
                        lane_lock.update_phase("regenerating GN cache")
                        out_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_args, out_dir / "args.gn")
                        gn = canonical_root / "depot_tools" / "gn"
                        generated = subprocess.run(
                            [str(gn), "gen", str(out_dir)],
                            cwd=canonical_chromium,
                            env=environment,
                            check=False,
                            pass_fds=lane_lock.pass_fds,
                        )
                        if generated.returncode != 0:
                            return generated.returncode

                    lane_lock.update_phase(operation)
                    if verified_for_production:
                        if release_root_revision is None:
                            raise BuildLaneError(
                                "Release root revision was not captured under the lane lock."
                            )
                        with immutable_git_snapshot(
                            requesting_root,
                            release_root_revision,
                            snapshot_parent,
                            "workspace",
                            pass_fds=lane_lock.pass_fds,
                        ) as immutable_root:
                            completed = subprocess.run(
                                [
                                    str(
                                        immutable_root
                                        / "scripts"
                                        / "lib"
                                        / "build-release-operation.sh"
                                    ),
                                    str(immutable_root),
                                ],
                                cwd=canonical_chromium,
                                env=environment,
                                check=False,
                                pass_fds=lane_lock.pass_fds,
                            )
                    else:
                        completed = subprocess.run(
                            list(command),
                            cwd=canonical_chromium,
                            env=environment,
                            check=False,
                            pass_fds=lane_lock.pass_fds,
                        )
                    if completed.returncode != 0:
                        return completed.returncode

                    if require_release_root:
                        validate_release_root(requesting_root)
                        if _git(requesting_root, "rev-parse", "HEAD") != release_root_revision:
                            raise BuildLaneError(
                                "Main changed while the release was running; no production "
                                "verification was recorded."
                            )

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
            lane_lock.update_phase("writing verified manifest")
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
        _fsync_directory(path.parent)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _fsync_directory(path: Path) -> None:
    directory_descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def _unlink_durable(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    _fsync_directory(path.parent)


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
    previous_bundle = previous.get("bundle", {})
    artifact_unchanged = bool(
        same_identity
        and bundle is not None
        and isinstance(previous_bundle, Mapping)
        and previous_bundle.get("artifactSha256")
        == bundle.get("artifactSha256")
    )
    result: dict[str, object] = {
        "schemaVersion": 1,
        **identity,
        "completedBuildTargets": sorted(set(old_targets) | set(build_targets)),
        "completedVerificationSuites": sorted(
            set(old_suites) | set(verification_suites)
        ),
        "verifiedForProduction": verified_for_production
        or bool(
            previous.get("verifiedForProduction", False) and artifact_unchanged
        ),
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
        or not bundle.get("artifactSha256")
    ):
        raise BuildLaneError(
            "The manifest does not describe a strictly signed production bundle. "
            "Run ./scripts/build-release.sh first."
        )


def validate_artifact_fingerprint(
    manifest: Mapping[str, object], app_path: Path
) -> None:
    bundle = manifest.get("bundle", {})
    expected = bundle.get("artifactSha256") if isinstance(bundle, Mapping) else None
    if not isinstance(expected, str) or not expected:
        raise BuildLaneError(
            "The release manifest has no artifact fingerprint. "
            "Run ./scripts/build-release.sh first."
        )
    actual = artifact_sha256(app_path)
    if actual != expected:
        raise BuildLaneError(
            "The production artifact fingerprint no longer matches the verified "
            "manifest. Run ./scripts/build-release.sh again."
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


def atomic_exchange(first: Path, second: Path) -> None:
    """Atomically exchange two paths on macOS using renameatx_np."""
    if sys.platform != "darwin":
        raise BuildLaneError("Atomic app exchange is supported only on macOS.")
    renameatx_np = ctypes.CDLL(None, use_errno=True).renameatx_np
    renameatx_np.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameatx_np.restype = ctypes.c_int
    at_fdcwd = -2
    rename_swap = 0x00000002
    result = renameatx_np(
        at_fdcwd,
        os.fsencode(first),
        at_fdcwd,
        os.fsencode(second),
        rename_swap,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number), str(first), str(second))


def _install_staged_bundle(
    staging: Path,
    destination: Path,
    *,
    exchanger: Callable[[Path, Path], None] = atomic_exchange,
) -> bool:
    """Install staging atomically; return whether an existing bundle was swapped."""
    if destination.exists():
        exchanger(staging, destination)
        return True
    os.replace(staging, destination)
    return False


def package_release_artifact(
    source_app: Path,
    out_dir: Path,
    destination_app: Path,
    *,
    signer: Callable[[Path], None],
    signature_verifier: Callable[[Path], bool] = _verify_signature,
    copier: Callable[[Path, Path], None] = _ditto,
    exchanger: Callable[[Path, Path], None] = atomic_exchange,
) -> str:
    """Create the complete signed bundle whose exact bytes may be promoted."""
    if not source_app.is_dir():
        raise BuildLaneError(f"Production source app was not found at {source_app}.")
    nonce = uuid.uuid4().hex
    staging = destination_app.parent / f".{destination_app.name}.staging.{nonce}"
    swapped = False
    installed = False
    preserve_staging = False
    try:
        copier(source_app, staging)
        frameworks = staging / "Contents" / "Frameworks"
        frameworks.mkdir(parents=True, exist_ok=True)
        for library in sorted(out_dir.glob("*.dylib")):
            copier(library, frameworks / library.name)
        signer(staging)
        if not signature_verifier(staging):
            raise BuildLaneError(
                f"Packaged production app failed strict signature verification: {staging}"
            )
        fingerprint = artifact_sha256(staging)
        swapped = _install_staged_bundle(
            staging, destination_app, exchanger=exchanger
        )
        installed = True
        if artifact_sha256(destination_app) != fingerprint:
            raise BuildLaneError(
                "The packaged production app changed during atomic installation."
            )
        if not signature_verifier(destination_app):
            raise BuildLaneError(
                f"Packaged production app failed after installation: {destination_app}"
            )
        return fingerprint
    except BaseException:
        if swapped and staging.exists() and destination_app.exists():
            try:
                exchanger(staging, destination_app)
            except BaseException as rollback_error:
                preserve_staging = True
                raise BuildLaneError(
                    "Release packaging rollback failed; the previous bundle was "
                    f"preserved at {staging}."
                ) from rollback_error
        elif installed and destination_app.exists() and not staging.exists():
            os.replace(destination_app, staging)
        raise
    finally:
        if staging.exists() and not preserve_staging:
            shutil.rmtree(staging, ignore_errors=True)


def promote_app(
    source_app: Path,
    install_app: Path,
    *,
    expected_fingerprint: str,
    signature_verifier: Callable[[Path], bool] = _verify_signature,
    copier: Callable[[Path, Path], None] = _ditto,
    exchanger: Callable[[Path, Path], None] = atomic_exchange,
    pre_exchange_check: Callable[[], None] | None = None,
) -> None:
    """Stage and atomically promote the exact release artifact in the manifest."""
    if not source_app.is_dir():
        raise BuildLaneError(f"Verified source app was not found at {source_app}.")
    if artifact_sha256(source_app) != expected_fingerprint:
        raise BuildLaneError(
            "The production artifact fingerprint changed before staging."
        )
    install_app.parent.mkdir(parents=True, exist_ok=True)
    nonce = uuid.uuid4().hex
    staging = install_app.parent / f".{install_app.name}.staging.{nonce}"
    swapped = False
    installed = False
    preserve_staging = False
    try:
        copier(source_app, staging)
        if artifact_sha256(staging) != expected_fingerprint:
            raise BuildLaneError(
                "The staged production app does not match the verified fingerprint."
            )
        if not signature_verifier(staging):
            raise BuildLaneError(
                f"Staged production app failed strict signature verification: {staging}"
            )
        if pre_exchange_check is not None:
            pre_exchange_check()
        swapped = _install_staged_bundle(staging, install_app, exchanger=exchanger)
        installed = True
        if artifact_sha256(install_app) != expected_fingerprint:
            raise BuildLaneError(
                "Installed production app does not match the verified fingerprint."
            )
        if not signature_verifier(install_app):
            raise BuildLaneError(
                f"Installed production app failed strict signature verification: {install_app}"
            )
    except BaseException:
        if swapped and staging.exists() and install_app.exists():
            try:
                exchanger(staging, install_app)
            except BaseException as rollback_error:
                preserve_staging = True
                raise BuildLaneError(
                    "Production rollback failed; the previous app was preserved at "
                    f"{staging}."
                ) from rollback_error
        elif installed and install_app.exists() and not staging.exists():
            os.replace(install_app, staging)
        raise
    finally:
        if staging.exists() and not preserve_staging:
            shutil.rmtree(staging, ignore_errors=True)
