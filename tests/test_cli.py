import contextlib
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from password_manager.cli import _countdown, _generate, main
from password_manager.vault import Vault


class CliTests(unittest.TestCase):
    def test_generation_prompt_explains_groups_and_length(self):
        prompts = []

        def answer(prompt):
            prompts.append(prompt)
            return ""

        with patch("builtins.input", side_effect=answer):
            password = _generate()
        self.assertEqual(len(password), 20)
        self.assertIn("Include uppercase letters (A-Z)", prompts[1])
        self.assertIn("Password length in characters (4-1024", prompts[-1])

    def test_create_add_reopen_and_view(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.json"
            output = StringIO()
            with patch("password_manager.cli._countdown", return_value=True), \
                 patch("password_manager.cli.getpass", side_effect=["master", "master", "sample-secret"]), \
                 patch("builtins.input", side_effect=["3", "Mail", "demo@example.invalid", "6"]), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(main(["--vault", str(path)]), 0)
            self.assertEqual(Vault.open(path, "master").entries[0]["password"], "sample-secret")
            output = StringIO()
            with patch("password_manager.cli._countdown", return_value=True), \
                 patch("password_manager.cli.getpass", return_value="master"), \
                 patch("builtins.input", side_effect=["2", "1", "6"]), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(main(["--vault", str(path)]), 0)
            self.assertIn("Password: sample-secret", output.getvalue())

    def test_three_wrong_passwords_then_close(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.json"
            Vault.create(path, "master")
            output = StringIO()
            with patch("password_manager.cli.getpass", side_effect=["wrong", "wrong", "wrong"]), \
                 patch("password_manager.cli._countdown", return_value=True) as countdown, \
                 contextlib.redirect_stdout(output):
                self.assertEqual(main(["--vault", str(path)]), 1)
            self.assertEqual(output.getvalue().count("Master password incorrect"), 3)
            countdown.assert_called_once()

    def test_escape_after_three_wrong_passwords_stays_locked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.json"
            Vault.create(path, "master")
            output = StringIO()
            with patch("password_manager.cli.getpass", side_effect=["wrong"] * 3) as password_prompt, \
                 patch("password_manager.cli._countdown", return_value=False), \
                 patch("builtins.input", return_value="") as close_prompt, \
                 contextlib.redirect_stdout(output):
                self.assertEqual(main(["--vault", str(path)]), 1)
            self.assertEqual(password_prompt.call_count, 3)
            close_prompt.assert_called_once_with("Vault remains locked. Press Enter to close.")
            self.assertTrue(path.exists())

    def test_reset_requires_confirmation_and_master_password(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.json"
            Vault.create(path, "master")
            with patch("password_manager.cli.getpass", side_effect=["master", "wrong", "master"]), \
                 patch("builtins.input", side_effect=["7", "RESET", "7", "RESET"]), \
                 patch("password_manager.cli._countdown", return_value=True), \
                 contextlib.redirect_stdout(StringIO()):
                self.assertEqual(main(["--vault", str(path)]), 0)
            self.assertFalse(path.exists())

    def test_escape_cancels_countdown_and_reset(self):
        with patch("password_manager.cli.msvcrt.kbhit", return_value=True), \
             patch("password_manager.cli.msvcrt.getwch", return_value="\x1b"), \
             contextlib.redirect_stdout(StringIO()):
            self.assertFalse(_countdown("Goodbye!"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.json"
            Vault.create(path, "master")
            with patch("password_manager.cli.getpass", side_effect=["master", "master"]), \
                 patch("builtins.input", side_effect=["7", "RESET", "6"]), \
                 patch("password_manager.cli._countdown", side_effect=[False, True]), \
                 contextlib.redirect_stdout(StringIO()):
                self.assertEqual(main(["--vault", str(path)]), 0)
            self.assertTrue(path.exists())

    def test_escape_cancels_lock_and_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.json"
            Vault.create(path, "master")
            with patch("password_manager.cli.getpass", return_value="master"), \
                 patch("builtins.input", side_effect=["6", "6"]), \
                 patch("password_manager.cli._countdown", side_effect=[False, True]) as countdown, \
                 contextlib.redirect_stdout(StringIO()):
                self.assertEqual(main(["--vault", str(path)]), 0)
            self.assertEqual(countdown.call_count, 2)

    def test_countdown_expires_after_three_seconds(self):
        clock = [0.0]

        def advance(seconds):
            clock[0] += seconds

        output = StringIO()
        with patch("password_manager.cli.time.monotonic", side_effect=lambda: clock[0]), \
             patch("password_manager.cli.time.sleep", side_effect=advance), \
             patch("password_manager.cli.msvcrt.kbhit", return_value=False), \
             contextlib.redirect_stdout(output):
            self.assertTrue(_countdown("Closing."))
        self.assertGreaterEqual(clock[0], 3)
        self.assertIn("Closing in 3", output.getvalue())
        self.assertIn("Closing in 1", output.getvalue())


if __name__ == "__main__":
    unittest.main()
