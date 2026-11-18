"""Versioned JSON vault with authenticated encryption and atomic updates."""

import base64
import binascii
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import msvcrt
import os
from pathlib import Path
import secrets
import tempfile

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .security import validate_new_master_password
from .permissions import restrict_access


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


class VaultAuthenticationError(VaultError):
    """The master password was wrong, or authenticated data was changed."""


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


@contextmanager
def _file_lock(path: Path):
    """Serialize vault changes across Windows processes."""
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+b") as lock_file:
        lock_file.seek(0)
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise VaultError("Vault is busy in another process. Try again.") from exc
        try:
            yield
        finally:
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


class Vault:
    def __init__(self, path: Path, key: bytes, salt: bytes, entries: list[dict[str, str]],
                 fingerprint: bytes | None = None, last_saved_at: str | None = None,
                 password_check: str | None = None):
        self.path = Path(path)
        self._key = key
        self._salt = salt
        self.entries = entries
        self._fingerprint = fingerprint
        self.last_saved_at = last_saved_at
        self._password_check = password_check

    @classmethod
    def create(cls, path: Path, password: str) -> "Vault":
        path = Path(path)
        validate_new_master_password(password)
        salt = secrets.token_bytes(SALT_BYTES)
        vault = cls(path, _key(password, salt), salt, [],
                    password_check=hashlib.sha256(password.encode("utf-8")).hexdigest())
        data, saved_at = vault._serialize()
        with _file_lock(path):
            # Exclusive creation prevents replacing an existing vault.
            created = False
            try:
                with path.open("xb") as output:
                    created = True
                    restrict_access(path)
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
            except Exception:
                if created:
                    path.unlink(missing_ok=True)
                raise
        vault._fingerprint = hashlib.sha256(data).digest()
        vault.last_saved_at = saved_at
        return vault

    @classmethod
    def open(cls, path: Path, password: str) -> "Vault":
        if not password:
            raise VaultAuthenticationError("Incorrect master password or damaged vault.")
        try:
            raw = Path(path).read_bytes()
            if len(raw) > 10_000_000:
                raise VaultError("Vault file is too large.")
            document = json.loads(raw)
            expected = {"version", "salt", "nonce", "ciphertext"}
            if not isinstance(document, dict) or set(document) not in (expected, expected | {"password_check"}):
                raise VaultError("Invalid vault data.")
            if type(document["version"]) is not int or document["version"] != VERSION:
                raise VaultError("Unsupported vault version.")
            salt = _decode(document["salt"])
            nonce = _decode(document["nonce"])
            ciphertext = _decode(document["ciphertext"])
            if len(salt) != SALT_BYTES or len(nonce) != NONCE_BYTES or len(ciphertext) < 16:
                raise VaultError("Invalid vault data.")
            password_check = document.get("password_check")
            if password_check is not None:
                if not isinstance(password_check, str) or len(password_check) != 64:
                    raise VaultError("Invalid vault data.")
                candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()
                if not hmac.compare_digest(candidate, password_check):
                    raise VaultAuthenticationError("Incorrect master password or damaged vault.")
            key = _key(password, salt)
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, AAD)
            payload = json.loads(plaintext)
            if not isinstance(payload, dict) or set(payload) not in ({"entries"}, {"entries", "saved_at"}) or not isinstance(payload["entries"], list):
                raise VaultError("Invalid vault contents.")
            saved_at = payload.get("saved_at")
            if saved_at is not None:
                if not isinstance(saved_at, str):
                    raise VaultError("Invalid vault contents.")
                try:
                    datetime.fromisoformat(saved_at)
                except ValueError as exc:
                    raise VaultError("Invalid vault contents.") from exc
            entries = payload["entries"]
            if any(
                not isinstance(entry, dict)
                or set(entry) != {"name", "username", "password"}
                or any(not isinstance(value, str) for value in entry.values())
                for entry in entries
            ):
                raise VaultError("Invalid vault contents.")
            restrict_access(Path(path))
            return cls(Path(path), key, salt, entries, hashlib.sha256(raw).digest(), saved_at,
                       password_check)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, RecursionError) as exc:
            raise VaultError("Invalid vault data.") from exc
        except InvalidTag as exc:
            raise VaultAuthenticationError("Incorrect master password or damaged vault.") from exc

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

    def change_master_password(self, current_password: str, new_password: str) -> None:
        """Re-encrypt all entries with a fresh salt after verifying the old password."""
        Vault.open(self.path, current_password)
        validate_new_master_password(new_password)
        old_key, old_salt, old_check = self._key, self._salt, self._password_check
        self._salt = secrets.token_bytes(SALT_BYTES)
        self._key = _key(new_password, self._salt)
        self._password_check = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
        try:
            self.save()
        except Exception:
            self._key, self._salt, self._password_check = old_key, old_salt, old_check
            raise

    def reset(self, current_password: str) -> None:
        """Remove only the vault version this session opened and authenticated."""
        Vault.open(self.path, current_password)
        with _file_lock(self.path):
            if hashlib.sha256(self.path.read_bytes()).digest() != self._fingerprint:
                raise VaultError("Vault changed on disk. Reopen it before resetting.")
            self.path.unlink()

    def _serialize(self) -> tuple[bytes, str]:
        nonce = secrets.token_bytes(NONCE_BYTES)
        saved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        plaintext = json.dumps({"entries": self.entries, "saved_at": saved_at}, ensure_ascii=False).encode("utf-8")
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext, AAD)
        document = {"version": VERSION, "salt": _encode(self._salt),
                    "nonce": _encode(nonce), "ciphertext": _encode(ciphertext)}
        if self._password_check is not None:
            document["password_check"] = self._password_check
        return (json.dumps(document, separators=(",", ":")) + "\n").encode("utf-8"), saved_at

    def save(self) -> None:
        data, saved_at = self._serialize()
        temporary = None
        with _file_lock(self.path):
            try:
                try:
                    current = self.path.read_bytes()
                except FileNotFoundError as exc:
                    raise VaultError("Vault file was removed; changes were not saved.") from exc
                if hashlib.sha256(current).digest() != self._fingerprint:
                    raise VaultError("Vault changed on disk. Reopen it before saving.")
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=self.path.parent, prefix=self.path.name + ".",
                    suffix=".tmp", delete=False,
                ) as output:
                    temporary = Path(output.name)
                    restrict_access(temporary)
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, self.path)
                self._fingerprint = hashlib.sha256(data).digest()
                self.last_saved_at = saved_at
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
