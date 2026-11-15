import json
from pathlib import Path
import tempfile
import unittest

from password_manager.vault import Vault, VaultError


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "vault.json"

    def test_create_save_reopen_and_delete(self):
        vault = Vault.create(self.path, "correct horse battery staple")
        vault.add("Mail", "demo@example.invalid", "sample-secret")
        saved = self.path.read_text()
        self.assertNotIn("sample-secret", saved)
        self.assertNotIn("demo@example.invalid", saved)
        reopened = Vault.open(self.path, "correct horse battery staple")
        self.assertEqual(reopened.entries, [{"name": "Mail", "username": "demo@example.invalid", "password": "sample-secret"}])
        reopened.delete(0)
        self.assertEqual(Vault.open(self.path, "correct horse battery staple").entries, [])

    def test_wrong_password_and_tampering(self):
        Vault.create(self.path, "master")
        with self.assertRaisesRegex(VaultError, "Incorrect master password or damaged vault"):
            Vault.open(self.path, "wrong")
        document = json.loads(self.path.read_text())
        document["ciphertext"] = document["ciphertext"][:-4] + "AAAA"
        self.path.write_text(json.dumps(document))
        with self.assertRaises(VaultError):
            Vault.open(self.path, "master")

    def test_invalid_format_and_exclusive_creation(self):
        Vault.create(self.path, "master")
        with self.assertRaises(FileExistsError):
            Vault.create(self.path, "new master")
        self.path.write_text("not json")
        with self.assertRaises(VaultError):
            Vault.open(self.path, "master")

    def test_save_uses_fresh_nonce(self):
        vault = Vault.create(self.path, "master")
        first = json.loads(self.path.read_text())["nonce"]
        vault.save()
        second = json.loads(self.path.read_text())["nonce"]
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
