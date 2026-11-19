import contextlib
import base64
from io import StringIO
import json
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from password_manager.cli import IdleTimeout, _clear_screen, _console_input, _secret, main
from password_manager.paths import default_vault_path
from password_manager.vault import AAD, Vault, VaultAuthenticationError, VaultError, _key


MASTER = "purple comet river lantern 73"
NEW_MASTER = "t3stMe"


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "demo-vault.json"

    def test_new_master_requires_at_least_six_characters(self):
        for password in ("", "a", "first"):
            with self.subTest(password=password), self.assertRaises(ValueError):
                Vault.create(self.path, password)
            self.assertFalse(self.path.exists())

    def test_six_character_example_works_for_create_unlock_and_change(self):
        vault = Vault.create(self.path, "t3stMe")
        self.assertEqual(Vault.open(self.path, "t3stMe").entries, [])
        vault.change_master_password("t3stMe", "d3moMe")
        with self.assertRaises(VaultAuthenticationError):
            Vault.open(self.path, "t3stMe")
        self.assertEqual(Vault.open(self.path, "d3moMe").entries, [])

    def test_weak_older_vault_can_still_be_opened(self):
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(_key("a", salt)).encrypt(nonce, b'{"entries": []}', AAD)
        document = {"version": 1, "salt": base64.b64encode(salt).decode(),
                    "nonce": base64.b64encode(nonce).decode(),
                    "ciphertext": base64.b64encode(ciphertext).decode()}
        self.path.write_text(json.dumps(document))
        opened = Vault.open(self.path, "a")
        self.assertEqual(opened.entries, [])
        self.assertIsNone(opened.last_saved_at)

    def test_master_password_change_preserves_entries_and_changes_salt(self):
        vault = Vault.create(self.path, MASTER)
        vault.add("Alex", "alex@example.invalid", "synthetic-secret")
        old_salt = json.loads(self.path.read_text())["salt"]
        vault.change_master_password(MASTER, NEW_MASTER)
        self.assertNotEqual(json.loads(self.path.read_text())["salt"], old_salt)
        with self.assertRaises(VaultAuthenticationError):
            Vault.open(self.path, MASTER)
        reopened = Vault.open(self.path, NEW_MASTER)
        self.assertEqual(reopened.entries[0]["password"], "synthetic-secret")
        self.assertIsNotNone(reopened.last_saved_at)

    def test_stale_session_cannot_overwrite_or_reset_newer_vault(self):
        Vault.create(self.path, MASTER)
        first = Vault.open(self.path, MASTER)
        second = Vault.open(self.path, MASTER)
        first.add("Alex", "alex@example.invalid", "one")
        with self.assertRaisesRegex(VaultError, "changed on disk"):
            second.add("Ben", "ben@example.invalid", "two")
        with self.assertRaisesRegex(VaultError, "changed on disk"):
            second.reset(MASTER)
        self.assertEqual(len(Vault.open(self.path, MASTER).entries), 1)

    def test_default_path_preserves_legacy_vault(self):
        previous = Path.cwd()
        try:
            os.chdir(self.directory.name)
            with patch.dict(os.environ, {"LOCALAPPDATA": self.directory.name}):
                self.assertEqual(default_vault_path(), Path(self.directory.name) / "LocalPasswordManager" / "vault.json")
                Path("vault.json").write_text("synthetic")
                self.assertEqual(default_vault_path(), Path("vault.json"))
        finally:
            os.chdir(previous)

    def test_new_default_vault_is_outside_working_directory(self):
        previous = Path.cwd()
        try:
            os.chdir(self.directory.name)
            with patch.dict(os.environ, {"LOCALAPPDATA": self.directory.name}), \
                 patch("password_manager.cli._secret", side_effect=[MASTER, MASTER]), \
                 patch("builtins.input", return_value="6"), \
                 patch("password_manager.cli._countdown", return_value=True), \
                 contextlib.redirect_stdout(StringIO()):
                self.assertEqual(main([]), 0)
            self.assertFalse(Path("vault.json").exists())
            self.assertTrue((Path(self.directory.name) / "LocalPasswordManager" / "vault.json").exists())
        finally:
            os.chdir(previous)

    def test_secret_input_refuses_nonterminal(self):
        with patch("password_manager.cli.sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(VaultError, "real terminal"):
                _secret("Master password: ")

    def test_lock_clears_console_screen(self):
        with patch("password_manager.cli.sys.stdout.isatty", return_value=True), \
             patch("password_manager.cli.os.system", return_value=0) as command:
            _clear_screen()
        command.assert_called_once_with("cls")

    def test_empty_unlock_and_reset_do_not_crash(self):
        Vault.create(self.path, MASTER)
        output = StringIO()
        with patch("password_manager.cli._secret", side_effect=["", MASTER, ""]), \
             patch("builtins.input", side_effect=["7", "RESET", "6"]), \
             patch("password_manager.cli._countdown", return_value=True), \
             contextlib.redirect_stdout(output):
            self.assertEqual(main(["--vault", str(self.path)]), 0)
        self.assertTrue(self.path.exists())
        self.assertIn("2 attempts remaining", output.getvalue())
        self.assertIn("Reset canceled", output.getvalue())

    def test_console_input_hides_secret_and_times_out(self):
        output = StringIO()
        with patch("password_manager.cli.msvcrt.kbhit", return_value=True), \
             patch("password_manager.cli.msvcrt.getwch", side_effect=["s", "e", "c", "\r"]), \
             contextlib.redirect_stdout(output):
            self.assertEqual(_console_input("Secret: ", hidden=True), "sec")
        self.assertNotIn("sec", output.getvalue().lower().replace("secret", ""))

        clock = [0.0]
        with patch("password_manager.cli.IDLE_SECONDS", 0.1), \
             patch("password_manager.cli.time.monotonic", side_effect=lambda: clock[0]), \
             patch("password_manager.cli.time.sleep", side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)), \
             patch("password_manager.cli.msvcrt.kbhit", return_value=False), \
             contextlib.redirect_stdout(StringIO()):
            with self.assertRaises(IdleTimeout):
                _console_input("Choose: ", hidden=False)

    def test_cli_changes_master_password(self):
        Vault.create(self.path, MASTER)
        with patch("password_manager.cli._secret", side_effect=[MASTER, MASTER, NEW_MASTER, NEW_MASTER]), \
             patch("builtins.input", side_effect=["8", "6"]), \
             patch("password_manager.cli._countdown", return_value=True), \
             contextlib.redirect_stdout(StringIO()):
            self.assertEqual(main(["--vault", str(self.path)]), 0)
        self.assertEqual(Vault.open(self.path, NEW_MASTER).entries, [])


if __name__ == "__main__":
    unittest.main()
