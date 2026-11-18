"""Checks for new master passwords; existing vaults remain unlockable."""

from zxcvbn import zxcvbn


def validate_new_master_password(password: str) -> None:
    if len(password) < 12:
        raise ValueError("Use at least 12 characters for the master password.")
    if len(password) > 1024:
        raise ValueError("Master password is too long (maximum 1024 characters).")
    if zxcvbn(password)["score"] < 3:
        raise ValueError("Master password is too easy to guess. Try a longer, unusual passphrase.")
