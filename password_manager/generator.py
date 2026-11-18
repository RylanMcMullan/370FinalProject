"""Password generation utilities."""

import random
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
    if length < 4 or length > 20:
        raise ValueError("Password length must be between 4 and 20 characters.")
    alphabet = "".join(groups)
    chars = [random.choice(group) for group in groups]
    chars.extend(random.choice(alphabet) for _ in range(length - len(groups)))
    random.shuffle(chars)
    return "".join(chars)
