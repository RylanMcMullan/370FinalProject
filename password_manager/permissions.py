"""Set vault file modes when files are created or opened."""

import os
from pathlib import Path


def restrict_access(path: Path) -> None:
    path = Path(path)
    os.chmod(path, 0o700 if path.is_dir() else 0o600)
