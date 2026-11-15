import contextlib
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from password_manager.cli import main
from password_manager.vault import Vault


class CliTests(unittest.TestCase):
    def test_create_add_reopen_and_view(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.json"
            output = StringIO()
            with patch("password_manager.cli.getpass", side_effect=["master", "master", "sample-secret"]), \
                 patch("builtins.input", side_effect=["3", "Mail", "demo@example.invalid", "6"]), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(main(["--vault", str(path)]), 0)
            self.assertEqual(Vault.open(path, "master").entries[0]["password"], "sample-secret")
            output = StringIO()
            with patch("password_manager.cli.getpass", return_value="master"), \
                 patch("builtins.input", side_effect=["2", "1", "6"]), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(main(["--vault", str(path)]), 0)
            self.assertIn("Password: sample-secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
