# Local Password Manager

A small Python password manager for Windows, with a command-line menu and local encrypted vault storage. A standalone executable is a packaging goal after the Python application works reliably.

## Planned features
- Create an encrypted vault protected by a master password.
- Unlock, view, add, and delete saved credential entries.
- Generate random passwords with user-selectable settings.
- Save the vault locally and reopen it in later sessions.
- Handle incorrect master passwords and invalid or damaged vault data appropriately.

## Planned design
- **Key derivation:** Argon2id with a per-vault random salt; choose and document practical parameters.
- **Vault encryption:** AES-256-GCM using a unique nonce for each encryption with a given key.
- **Password generation:** Python's `secrets` module.
- **Dependencies:** Prefer maintained, established libraries; do not implement cryptographic primitives from scratch.
- **Scope:** Local, single-user application; no accounts, synchronization service, cloud backend, or external database required.

## Security goal
Protect the confidentiality and integrity of stored credentials if someone obtains a copy of the locked vault file but does not know the master password. Compromise of the running, unlocked computer is outside this primary threat model.

## Status
Design established; implementation not yet started. See `docs/CURRENT_STATE.md` once development begins.