import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from _support import load


replay = load("install-maintenance", "replay")


class InstallationIsolationTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        base = Path(self.scratch.name).resolve()
        self.root = base / "sandbox"
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.external = base / "external"
        for directory in (self.home, self.project, self.external):
            directory.mkdir(parents=True)
        self.env = replay.isolated_environment(self.home)

    def test_parent_client_and_lock_paths_are_not_inherited(self):
        inherited = {name: str(self.external / name) for name in (
            "HOME", "CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")}
        with patch.dict(os.environ, inherited):
            env = replay.isolated_environment(self.home)
            replay.validate_cli_destinations(self.root, self.project, env)
            self.assertEqual(env["CLAUDE_CONFIG_DIR"], str(self.home / ".claude"))
            self.assertEqual(env["XDG_STATE_HOME"], str(self.home / ".local/state"))
            for name, original in inherited.items():
                self.assertNotEqual(env[name], original)
                self.assertEqual(os.environ[name], original)

    def test_escaped_environment_paths_block_process_start(self):
        for name in ("HOME", "CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            with self.subTest(name=name), patch.object(replay.subprocess, "run") as launch:
                env = {**self.env, name: str(self.external)}
                with self.assertRaisesRegex(ValueError, "outside temporary root"):
                    replay.run_command(("node", "fixture-cli.mjs", "add", "fixture", "-g", "-y"),
                                       cwd=self.project, env=env, root=self.root)
                launch.assert_not_called()

    def test_symlinked_client_destination_blocks_process_start(self):
        for destination in (self.home / ".claude", self.project / ".claude",
                            self.project / ".agents"):
            with self.subTest(destination=destination):
                destination.symlink_to(self.external, target_is_directory=True)
                try:
                    with patch.object(replay.subprocess, "run") as launch:
                        with self.assertRaisesRegex(ValueError, "outside temporary root"):
                            replay.run_command(("node", "fixture-cli.mjs", "add", "fixture", "-y"),
                                               cwd=self.project, env=self.env, root=self.root)
                        launch.assert_not_called()
                finally:
                    destination.unlink()

    def test_external_working_directory_blocks_process_start(self):
        with patch.object(replay.subprocess, "run") as launch:
            with self.assertRaisesRegex(ValueError, "outside temporary root"):
                replay.run_command(("node", "fixture-cli.mjs", "add", "fixture", "-y"),
                                   cwd=self.external, env=self.env, root=self.root)
            launch.assert_not_called()

    def test_normal_project_and_global_commands_keep_the_isolated_environment(self):
        for scope in ((), ("-g",)):
            with self.subTest(scope=scope), patch.object(replay.subprocess, "run") as launch:
                launch.return_value = subprocess.CompletedProcess([], 0, "fixture output\n", "")
                command = ("node", "fixture-cli.mjs", "add", "fixture", *scope, "-y")
                self.assertEqual(replay.run_command(command, cwd=self.project, env=self.env,
                                                    root=self.root), "fixture output\n")
                self.assertEqual(launch.call_args.kwargs["env"], self.env)
                self.assertEqual(launch.call_args.kwargs["cwd"], self.project)


if __name__ == "__main__":
    unittest.main()
