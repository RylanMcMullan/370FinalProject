"""Default vault location for the local Windows application."""

import os
from pathlib import Path


def default_vault_path() -> Path:
    # Keep an existing project-folder vault at its current path.
    legacy = Path("vault.json")
    if legacy.exists():
        return legacy
    local_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_data) if local_data else Path.home() / "AppData" / "Local"
    return base / "LocalPasswordManager" / "vault.json"
