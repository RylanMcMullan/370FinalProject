"""Versioned JSON vault with authenticated encryption and atomic updates."""

import base64
import binascii
import json
import os
from pathlib import Path
import secrets
import tempfile

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


VERSION = 1
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32
ARGON_TIME = 3
ARGON_MEMORY_KIB = 65536
ARGON_PARALLELISM = 1
AAD = b"local-password-manager:v1"


class VaultError(Exception):
    """Vault data is invalid or cannot be decrypted."""


def _encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _decode(value: object) -> bytes:
    if not isinstance(value, str):
        raise VaultError("Invalid vault data.")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise VaultError("Invalid vault data.") from exc


def _key(password: str, salt: bytes) -> bytes:
    if not password:
        raise ValueError("Master password cannot be empty.")
    return hash_secret_raw(
        password.encode("utf-8"), salt, time_cost=ARGON_TIME,
        memory_cost=ARGON_MEMORY_KIB, parallelism=ARGON_PARALLELISM,
        hash_len=KEY_BYTES, type=Type.ID,
    )


class Vault:
    def __init__(self, path: Path, key: bytes, salt: bytes, entries: list[dict[str, str]]):
        self.path = Path(path)
        self._key = key
        self._salt = salt
        self.entries = entries

    @classmethod
    def create(cls, path: Path, password: str) -> "Vault":
        path = Path(path)
        salt = secrets.token_bytes(SALT_BYTES)
        vault = cls(path, _key(password, salt), salt, [])
        data = vault._serialize()
        # Exclusive creation prevents replacing an existing vault.
        with path.open("xb") as output:
            os.chmod(path, 0o600)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        return vault

    @classmethod
    def open(cls, path: Path, password: str) -> "Vault":
        try:
            raw = Path(path).read_bytes()
            if len(raw) > 10_000_000:
                raise VaultError("Vault file is too large.")
            document = json.loads(raw)
            if not isinstance(document, dict) or set(document) != {"version", "salt", "nonce", "ciphertext"}:
                raise VaultError("Invalid vault data.")
            if type(document["version"]) is not int or document["version"] != VERSION:
                raise VaultError("Unsupported vault version.")
            salt = _decode(document["salt"])
            nonce = _decode(document["nonce"])
            ciphertext = _decode(document["ciphertext"])
            if len(salt) != SALT_BYTES or len(nonce) != NONCE_BYTES or len(ciphertext) < 16:
                raise VaultError("Invalid vault data.")
            key = _key(password, salt)
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, AAD)
            payload = json.loads(plaintext)
            if not isinstance(payload, dict) or set(payload) != {"entries"} or not isinstance(payload["entries"], list):
                raise VaultError("Invalid vault contents.")
            entries = payload["entries"]
            if any(
                not isinstance(entry, dict)
                or set(entry) != {"name", "username", "password"}
                or any(not isinstance(value, str) for value in entry.values())
                for entry in entries
            ):
                raise VaultError("Invalid vault contents.")
            return cls(Path(path), key, salt, entries)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, RecursionError) as exc:
            raise VaultError("Invalid vault data.") from exc
        except InvalidTag as exc:
            raise VaultError("Incorrect master password or damaged vault.") from exc

    def add(self, name: str, username: str, password: str) -> None:
        if not name.strip() or not password:
            raise ValueError("Entry name and password cannot be empty.")
        self.entries.append({"name": name, "username": username, "password": password})
        try:
            self.save()
        except Exception:
            self.entries.pop()
            raise

    def delete(self, index: int) -> None:
        removed = self.entries.pop(index)
        try:
            self.save()
        except Exception:
            self.entries.insert(index, removed)
            raise

    def _serialize(self) -> bytes:
        nonce = secrets.token_bytes(NONCE_BYTES)
        plaintext = json.dumps({"entries": self.entries}, ensure_ascii=False).encode("utf-8")
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext, AAD)
        document = {"version": VERSION, "salt": _encode(self._salt),
                    "nonce": _encode(nonce), "ciphertext": _encode(ciphertext)}
        return (json.dumps(document, separators=(",", ":")) + "\n").encode("utf-8")

    def save(self) -> None:
        data = self._serialize()
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=self.path.parent, prefix=self.path.name + ".",
                suffix=".tmp", delete=False,
            ) as output:
                temporary = Path(output.name)
                os.chmod(temporary, 0o600)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
