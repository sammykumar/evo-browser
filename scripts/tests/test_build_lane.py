#!/usr/bin/env python3

import json
import plistlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.lib import build_lane


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True
    ).strip()


def create_repo(path: Path) -> tuple[str, str]:
    path.mkdir()
    git(path, "init", "-b", "main")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test User")
    (path / "tracked.txt").write_text("first\n", encoding="utf-8")
    git(path, "add", "tracked.txt")
    git(path, "commit", "-m", "first")
    first = git(path, "rev-parse", "HEAD")
    (path / "tracked.txt").write_text("second\n", encoding="utf-8")
    git(path, "commit", "-am", "second")
    return first, git(path, "rev-parse", "HEAD")


class BuildLaneTests(unittest.TestCase):
    def test_workspace_shell_reads_pinned_chromium_source_from_canonical_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            primary = base / "primary"
            feature = base / "feature"
            (primary / "scripts" / "lib").mkdir(parents=True)
            workspace_shell = Path(__file__).resolve().parents[1] / "lib" / "workspace.sh"
            (primary / "scripts" / "lib" / "workspace.sh").write_text(
                workspace_shell.read_text(encoding="utf-8"), encoding="utf-8"
            )

            chromium = primary / "evo-chromium" / "src"
            chromium.mkdir(parents=True)
            git(chromium, "init", "-b", "main")
            git(chromium, "config", "user.email", "test@example.com")
            git(chromium, "config", "user.name", "Test User")
            (chromium / "feature.cc").write_text("enabled by default\n", encoding="utf-8")
            git(chromium, "add", "feature.cc")
            git(chromium, "commit", "-m", "feature")
            revision = git(chromium, "rev-parse", "HEAD")

            (primary / "workspace.json").write_text(
                json.dumps(
                    {
                        "chromium": {
                            "checkoutPath": "evo-chromium/src",
                            "evoRevision": revision,
                        },
                        "build": {"canonicalOutput": "out/Evo"},
                        "components": {
                            "runtime": {"path": "evo-runtime"},
                            "opencode": {"path": "evo-opencode"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            git(primary, "init", "-b", "main")
            git(primary, "config", "user.email", "test@example.com")
            git(primary, "config", "user.name", "Test User")
            git(primary, "add", "scripts/lib/workspace.sh", "workspace.json")
            git(primary, "commit", "-m", "workspace")
            git(primary, "worktree", "add", "-b", "feature", str(feature))

            output = subprocess.check_output(
                [
                    "bash",
                    "-c",
                    'source "$1"; read_pinned_chromium_file feature.cc',
                    "bash",
                    str(feature / "scripts" / "lib" / "workspace.sh"),
                ],
                text=True,
            )

            self.assertEqual(output, "enabled by default\n")

    def test_workspace_shell_falls_back_from_empty_submodule_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            primary = base / "primary"
            feature = base / "feature"
            (primary / "scripts" / "lib").mkdir(parents=True)
            workspace_shell = Path(__file__).resolve().parents[1] / "lib" / "workspace.sh"
            (primary / "scripts" / "lib" / "workspace.sh").write_text(
                workspace_shell.read_text(encoding="utf-8"), encoding="utf-8"
            )
            (primary / "workspace.json").write_text(
                json.dumps(
                    {
                        "chromium": {"checkoutPath": "evo-chromium/src"},
                        "build": {"canonicalOutput": "out/Evo"},
                        "components": {
                            "runtime": {"path": "evo-runtime"},
                            "opencode": {"path": "evo-opencode"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            git(primary, "init", "-b", "main")
            git(primary, "config", "user.email", "test@example.com")
            git(primary, "config", "user.name", "Test User")
            git(primary, "add", "scripts/lib/workspace.sh", "workspace.json")
            git(primary, "commit", "-m", "workspace")
            git(primary, "worktree", "add", "-b", "feature", str(feature))

            for component in ("evo-runtime", "evo-opencode"):
                create_repo(primary / component)
                (feature / component).mkdir()

            output = subprocess.check_output(
                [
                    "bash",
                    "-c",
                    'source "$1"; printf "%s\\n%s\\n" "$runtime_dir" "$opencode_dir"',
                    "bash",
                    str(feature / "scripts" / "lib" / "workspace.sh"),
                ],
                text=True,
            ).splitlines()

            self.assertEqual(
                output,
                [
                    str((primary / "evo-runtime").resolve()),
                    str((primary / "evo-opencode").resolve()),
                ],
            )

    def test_release_root_cli_reports_guard_failure_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            create_repo(repo)
            git(repo, "checkout", "-b", "feature")
            cli = Path(__file__).resolve().parents[1] / "evo-build-lane.py"

            result = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "validate-release-root",
                    "--workspace-root",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("Release builds require the main branch", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_discovers_primary_checkout_from_a_linked_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            primary = base / "primary"
            feature = base / "feature"
            primary.mkdir()
            git(primary, "init", "-b", "main")
            git(primary, "config", "user.email", "test@example.com")
            git(primary, "config", "user.name", "Test User")
            (primary / "README.md").write_text("baseline\n", encoding="utf-8")
            git(primary, "add", "README.md")
            git(primary, "commit", "-m", "baseline")
            git(primary, "worktree", "add", "-b", "feature", str(feature))

            self.assertEqual(
                build_lane.discover_primary_checkout(feature), primary.resolve()
            )

    def test_refuses_a_request_with_uncommitted_source_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            create_repo(repo)
            (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")

            with self.assertRaisesRegex(
                build_lane.BuildLaneError, "must be fully committed"
            ):
                build_lane.requested_revision(repo)

    def test_refuses_a_request_with_untracked_source_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            create_repo(repo)
            (repo / "new-source.cc").write_text("// not committed\n", encoding="utf-8")

            with self.assertRaisesRegex(
                build_lane.BuildLaneError, "new-source.cc"
            ):
                build_lane.requested_revision(repo)

    def test_stale_lock_is_reclaimed_and_context_exit_releases_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir)
            lock_dir = state_dir / "lock"
            lock_dir.mkdir()
            (lock_dir / "owner.json").write_text(
                json.dumps({"pid": 999_999, "command": "old build"}),
                encoding="utf-8",
            )

            lock = build_lane.BuildLock(
                state_dir,
                {"command": "new build", "targetCommit": "abc"},
                pid_is_alive=lambda _pid: False,
            )
            with lock:
                owner = json.loads((lock_dir / "owner.json").read_text())
                self.assertEqual(owner["command"], "new build")
                self.assertEqual(owner["targetCommit"], "abc")

            self.assertFalse(lock_dir.exists())

    def test_live_lock_waits_and_reports_owner_before_acquiring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir)
            lock_dir = state_dir / "lock"
            lock_dir.mkdir()
            (lock_dir / "owner.json").write_text(
                json.dumps({"pid": 1234, "command": "first build"}),
                encoding="utf-8",
            )
            reports: list[str] = []

            def release_owner(_seconds: float) -> None:
                (lock_dir / "owner.json").unlink()
                lock_dir.rmdir()

            lock = build_lane.BuildLock(
                state_dir,
                {"command": "second build"},
                poll_interval=0,
                pid_is_alive=lambda pid: pid == 1234,
                sleeper=release_owner,
                reporter=reports.append,
            )
            with lock:
                self.assertTrue(lock_dir.exists())

            self.assertEqual(len(reports), 1)
            self.assertIn("first build", reports[0])

    def test_checkout_is_restored_after_an_interrupted_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            first, second = create_repo(repo)

            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                with build_lane.temporary_checkout(repo, first):
                    self.assertEqual(git(repo, "rev-parse", "HEAD"), first)
                    self.assertEqual(git(repo, "branch", "--show-current"), "")
                    raise RuntimeError("interrupted")

            self.assertEqual(git(repo, "branch", "--show-current"), "main")
            self.assertEqual(git(repo, "rev-parse", "HEAD"), second)

    def test_checkout_restores_branch_and_preserves_unexpected_changes_in_stash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            first, second = create_repo(repo)

            with self.assertRaisesRegex(build_lane.BuildLaneError, "preserved in stash"):
                with build_lane.temporary_checkout(repo, first):
                    (repo / "tracked.txt").write_text(
                        "unexpected build edit\n", encoding="utf-8"
                    )

            self.assertEqual(git(repo, "branch", "--show-current"), "main")
            self.assertEqual(git(repo, "rev-parse", "HEAD"), second)
            self.assertIn("evo-build-lane-recovery", git(repo, "stash", "list"))

    def test_cache_rejects_changed_xcode_or_gn_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            args_file = base / "source-args.gn"
            out_dir = base / "out" / "Evo"
            out_dir.mkdir(parents=True)
            args_file.write_text("is_debug=false\n", encoding="utf-8")
            (out_dir / "args.gn").write_text("is_debug=true\n", encoding="utf-8")
            (out_dir / "evo-build-manifest.json").write_text(
                json.dumps(
                    {
                        "toolchain": {
                            "xcodeVersion": "26.5",
                            "xcodeBuild": "17E999",
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                build_lane.BuildLaneError, "cache migration"
            ):
                build_lane.validate_cache_identity(
                    out_dir,
                    args_file,
                    xcode_version="26.6",
                    xcode_build="17F113",
                )

    def test_existing_unidentified_cache_requires_explicit_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            args_file = base / "source-args.gn"
            out_dir = base / "out" / "Evo"
            out_dir.mkdir(parents=True)
            args_file.write_text("is_debug=false\n", encoding="utf-8")
            (out_dir / "args.gn").write_text("is_debug=false\n", encoding="utf-8")
            (out_dir / "obj").mkdir()

            with self.assertRaisesRegex(build_lane.BuildLaneError, "no build manifest"):
                build_lane.validate_cache_identity(
                    out_dir,
                    args_file,
                    xcode_version="26.6",
                    xcode_build="17F113",
                )

            build_lane.validate_cache_identity(
                out_dir,
                args_file,
                xcode_version="26.6",
                xcode_build="17F113",
                allow_migration=True,
            )

    def test_malformed_cache_manifest_has_actionable_migration_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            args_file = base / "source-args.gn"
            out_dir = base / "out" / "Evo"
            out_dir.mkdir(parents=True)
            args_file.write_text("is_debug=false\n", encoding="utf-8")
            (out_dir / "args.gn").write_text("is_debug=false\n", encoding="utf-8")
            (out_dir / "evo-build-manifest.json").write_text(
                "not-json\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(build_lane.BuildLaneError, "malformed"):
                build_lane.validate_cache_identity(
                    out_dir,
                    args_file,
                    xcode_version="26.6",
                    xcode_build="17F113",
                )

    def test_manifest_accumulates_results_only_for_the_same_cache_identity(self) -> None:
        previous = {
            "chromiumRevision": "chromium-a",
            "runtimeRevision": "runtime-a",
            "gnArgumentsHash": "args-a",
            "toolchain": {"xcodeVersion": "26.6", "xcodeBuild": "17F113"},
            "completedBuildTargets": ["chrome"],
            "completedVerificationSuites": ["unit:A"],
            "verifiedForProduction": True,
        }
        identity = {
            "chromiumRevision": "chromium-a",
            "runtimeRevision": "runtime-a",
            "gnArgumentsHash": "args-a",
            "toolchain": {"xcodeVersion": "26.6", "xcodeBuild": "17F113"},
        }

        result = build_lane.next_manifest(
            previous,
            identity,
            build_targets=["browser_tests"],
            verification_suites=["browser:EvoShell*"],
            verified_for_production=False,
            timestamp="2026-07-25T12:00:00Z",
        )

        self.assertEqual(
            result["completedBuildTargets"], ["browser_tests", "chrome"]
        )
        self.assertEqual(
            result["completedVerificationSuites"],
            ["browser:EvoShell*", "unit:A"],
        )
        self.assertTrue(result["verifiedForProduction"])

    def test_manifest_drops_stale_verification_when_revision_changes(self) -> None:
        previous = {
            "chromiumRevision": "chromium-a",
            "runtimeRevision": "runtime-a",
            "gnArgumentsHash": "args-a",
            "toolchain": {"xcodeVersion": "26.6", "xcodeBuild": "17F113"},
            "completedBuildTargets": ["chrome", "browser_tests"],
            "completedVerificationSuites": ["release"],
            "verifiedForProduction": True,
        }
        identity = {
            "chromiumRevision": "chromium-b",
            "runtimeRevision": "runtime-a",
            "gnArgumentsHash": "args-a",
            "toolchain": {"xcodeVersion": "26.6", "xcodeBuild": "17F113"},
        }

        result = build_lane.next_manifest(
            previous,
            identity,
            build_targets=["chrome"],
            verification_suites=[],
            verified_for_production=False,
            timestamp="2026-07-25T12:00:00Z",
        )

        self.assertEqual(result["completedBuildTargets"], ["chrome"])
        self.assertEqual(result["completedVerificationSuites"], [])
        self.assertFalse(result["verifiedForProduction"])

    def test_release_validation_requires_exact_verified_identity(self) -> None:
        manifest = {
            "chromiumRevision": "chromium-a",
            "runtimeRevision": "runtime-a",
            "gnArgumentsHash": "args-a",
            "toolchain": {"xcodeVersion": "26.6", "xcodeBuild": "17F113"},
            "completedBuildTargets": ["chrome"],
            "completedVerificationSuites": ["workspace", "unit:EvoShell"],
            "verifiedForProduction": False,
        }
        expected_identity = {
            "chromiumRevision": "chromium-a",
            "runtimeRevision": "runtime-a",
            "gnArgumentsHash": "args-a",
            "toolchain": {"xcodeVersion": "26.6", "xcodeBuild": "17F113"},
        }

        with self.assertRaisesRegex(
            build_lane.BuildLaneError, "not verified for production"
        ):
            build_lane.validate_release_manifest(
                manifest,
                expected_identity,
                required_targets=["chrome"],
                required_suites=["workspace", "unit:EvoShell"],
            )

    def test_release_bundle_must_be_signed_production_identity(self) -> None:
        manifest = {
            "bundle": {
                "bundleIdentifier": "com.skproductions.evo.dev",
                "signatureVerified": True,
            }
        }

        with self.assertRaisesRegex(build_lane.BuildLaneError, "production bundle"):
            build_lane.validate_production_bundle(manifest)

    def test_release_root_must_be_clean_main_and_synced_with_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            remote = base / "origin.git"
            repo = base / "repo"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True)
            create_repo(repo)
            git(repo, "remote", "add", "origin", str(remote))
            git(repo, "push", "-u", "origin", "main")

            build_lane.validate_release_root(repo)

            (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(build_lane.BuildLaneError, "clean local main"):
                build_lane.validate_release_root(repo)
            git(repo, "restore", "tracked.txt")

            other = base / "other"
            subprocess.run(
                ["git", "clone", "--branch", "main", str(remote), str(other)],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            git(other, "config", "user.email", "test@example.com")
            git(other, "config", "user.name", "Test User")
            (other / "remote.txt").write_text("ahead\n", encoding="utf-8")
            git(other, "add", "remote.txt")
            git(other, "commit", "-m", "remote ahead")
            git(other, "push", "origin", "main")
            git(repo, "fetch", "origin", "main")

            with self.assertRaisesRegex(build_lane.BuildLaneError, "synchronized"):
                build_lane.validate_release_root(repo)

    def test_bundle_metadata_records_identity_version_and_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = Path(temp_dir) / "Evo.app"
            contents = app / "Contents"
            contents.mkdir(parents=True)
            with (contents / "Info.plist").open("wb") as plist_file:
                plistlib.dump(
                    {
                        "CFBundleIdentifier": "com.skproductions.evo",
                        "CFBundleShortVersionString": "150.0.7871.129",
                        "CFBundleVersion": "7871.129",
                    },
                    plist_file,
                )

            metadata = build_lane.read_bundle_metadata(
                app, signature_verifier=lambda _app: True
            )

            self.assertEqual(metadata["bundleIdentifier"], "com.skproductions.evo")
            self.assertEqual(metadata["version"], "150.0.7871.129")
            self.assertEqual(metadata["buildVersion"], "7871.129")
            self.assertTrue(metadata["signatureVerified"])

    def test_execute_lane_builds_feature_commit_in_canonical_output_and_restores(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            primary_root = base / "evo-browser"
            feature_root = base / "evo-browser-feature"
            primary_root.mkdir()
            git(primary_root, "init", "-b", "main")
            git(primary_root, "config", "user.email", "test@example.com")
            git(primary_root, "config", "user.name", "Test User")
            workspace = {
                "chromium": {"checkoutPath": "evo-chromium/src"},
                "build": {
                    "canonicalOutput": "out/Evo",
                    "xcode": {
                        "developerDir": "/Applications/Xcode.app/Contents/Developer",
                        "version": "26.6",
                        "build": "17F113",
                    },
                },
            }
            (primary_root / "workspace.json").write_text(
                json.dumps(workspace), encoding="utf-8"
            )
            git(primary_root, "add", "workspace.json")
            git(primary_root, "commit", "-m", "workspace")
            git(
                primary_root,
                "worktree",
                "add",
                "-b",
                "feature",
                str(feature_root),
            )

            canonical_chromium = primary_root / "evo-chromium" / "src"
            canonical_chromium.parent.mkdir(parents=True)
            create_repo(canonical_chromium)
            (canonical_chromium / "evo").mkdir()
            (canonical_chromium / "evo" / "args.gn").write_text(
                "is_debug=false\n", encoding="utf-8"
            )
            git(canonical_chromium, "add", "evo/args.gn")
            git(canonical_chromium, "commit", "-m", "add args")
            canonical_original = git(canonical_chromium, "rev-parse", "HEAD")

            requesting_chromium = feature_root / "evo-chromium" / "src"
            requesting_chromium.parent.mkdir(parents=True)
            git(
                canonical_chromium,
                "worktree",
                "add",
                "-b",
                "chromium-feature",
                str(requesting_chromium),
            )
            (requesting_chromium / "feature.cc").write_text(
                "// feature\n", encoding="utf-8"
            )
            git(requesting_chromium, "add", "feature.cc")
            git(requesting_chromium, "commit", "-m", "feature")
            target = git(requesting_chromium, "rev-parse", "HEAD")

            runtime = base / "runtime"
            _runtime_first, runtime_revision = create_repo(runtime)
            result_path = base / "command-result.json"
            command = [
                sys.executable,
                "-c",
                (
                    "import json, os, pathlib, subprocess; "
                    f"pathlib.Path({str(result_path)!r}).write_text(json.dumps({{"
                    "'cwd': str(pathlib.Path.cwd()), "
                    "'head': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(), "
                    "'out': os.environ['EVO_OUT_DIR']}))"
                ),
            ]

            exit_code = build_lane.execute_lane(
                requesting_root=feature_root,
                requesting_chromium=requesting_chromium,
                runtime_dir=runtime,
                operation="test build",
                command=command,
                build_targets=["chrome"],
                verification_suites=["fake-suite"],
                state_dir=base / "state",
                toolchain_reader=lambda _developer_dir: ("26.6", "17F113"),
                timestamp_factory=lambda: "2026-07-25T12:00:00Z",
            )

            self.assertEqual(exit_code, 0)
            command_result = json.loads(result_path.read_text())
            self.assertEqual(command_result["cwd"], str(canonical_chromium.resolve()))
            self.assertEqual(command_result["head"], target)
            self.assertEqual(
                command_result["out"],
                str((canonical_chromium / "out" / "Evo").resolve()),
            )
            self.assertEqual(
                git(canonical_chromium, "rev-parse", "HEAD"), canonical_original
            )
            manifest = json.loads(
                (canonical_chromium / "out" / "Evo" / "evo-build-manifest.json").read_text()
            )
            self.assertEqual(manifest["chromiumRevision"], target)
            self.assertEqual(manifest["runtimeRevision"], runtime_revision)
            self.assertEqual(manifest["completedBuildTargets"], ["chrome"])
            self.assertFalse((feature_root / "evo-chromium" / "src" / "out").exists())

            manifest_path = (
                canonical_chromium / "out" / "Evo" / "evo-build-manifest.json"
            )
            previous_manifest = manifest_path.read_bytes()
            failed_exit = build_lane.execute_lane(
                requesting_root=feature_root,
                requesting_chromium=requesting_chromium,
                runtime_dir=runtime,
                operation="failed test build",
                command=["/usr/bin/false"],
                build_targets=["browser_tests"],
                state_dir=base / "state",
                toolchain_reader=lambda _developer_dir: ("26.6", "17F113"),
                timestamp_factory=lambda: "2026-07-25T12:01:00Z",
            )
            self.assertEqual(failed_exit, 1)
            self.assertEqual(manifest_path.read_bytes(), previous_manifest)
            self.assertEqual(list(manifest_path.parent.glob("*.tmp")), [])

    def test_promotion_stages_signs_and_atomically_replaces_the_app(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            out_dir = base / "out" / "Evo"
            source_app = out_dir / "Evo.app"
            source_contents = source_app / "Contents"
            source_contents.mkdir(parents=True)
            (source_contents / "payload.txt").write_text("new\n", encoding="utf-8")
            (out_dir / "libfeature.dylib").write_text("library\n", encoding="utf-8")
            install_app = base / "Applications" / "Evo.app"
            (install_app / "Contents").mkdir(parents=True)
            (install_app / "Contents" / "payload.txt").write_text(
                "old\n", encoding="utf-8"
            )

            signed: list[Path] = []

            def signer(app: Path) -> None:
                signed.append(app)
                (app / "Contents" / "signed.txt").write_text("yes\n", encoding="utf-8")

            build_lane.promote_app(
                source_app,
                out_dir,
                install_app,
                signer=signer,
                signature_verifier=lambda app: (
                    app / "Contents" / "signed.txt"
                ).is_file(),
            )

            self.assertEqual(
                (install_app / "Contents" / "payload.txt").read_text(), "new\n"
            )
            self.assertEqual(
                (
                    install_app
                    / "Contents"
                    / "Frameworks"
                    / "libfeature.dylib"
                ).read_text(),
                "library\n",
            )
            self.assertEqual(len(signed), 1)
            self.assertEqual(list(install_app.parent.glob(".Evo.app.*")), [])


if __name__ == "__main__":
    unittest.main()
