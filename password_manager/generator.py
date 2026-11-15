"""Password generation using the standard library's cryptographic RNG."""

import secrets
import string


def generate_password(
    length: int = 20,
    *,
    lowercase: bool = True,
    uppercase: bool = True,
    digits: bool = True,
    symbols: bool = True,
) -> str:
    groups = [
        alphabet
        for enabled, alphabet in (
            (lowercase, string.ascii_lowercase),
            (uppercase, string.ascii_uppercase),
            (digits, string.digits),
            (symbols, "!@#$%^&*()-_=+[]{}:,.?"),
        )
        if enabled
    ]
    if not groups:
        raise ValueError("Select at least one character group.")
    if length < len(groups) or length > 1024:
        raise ValueError(f"Length must be between {len(groups)} and 1024.")
    alphabet = "".join(groups)
    chars = [secrets.choice(group) for group in groups]
    chars.extend(secrets.choice(alphabet) for _ in range(length - len(groups)))
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
