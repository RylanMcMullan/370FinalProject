# Decisions

## 2026-11-17 — Requested CLI changes

The owner explicitly requested clearer prompts, three unlock attempts, a countdown before closing, and a confirmed vault reset. These changes were authorized in the 2026-11-17 request. The owner clarified that Esc after the third failed unlock should stop automatic closing while leaving the vault locked, with manual closing required.

| Choice | Rationale |
| --- | --- |
| Show selected character groups before asking for length | The minimum valid length is the number of selected groups, so the prompt can show the actual range. |
| Three failed unlocks per run, with no persistent counter | Fits the local CLI and avoids a new storage mechanism. Restarting can allow more attempts; this is a usability limit, not a security rate limit. |
| Reset only after `RESET`, master password re-entry, and an uncanceled countdown | Gives the user multiple chances to prevent deletion. Esc during the countdown leaves the vault file intact. |
| Delete the vault file to reset | On the next run, the existing creation flow asks for a new master password. Filesystem copies and backups are outside this operation. |
| Use Windows console key polling for Esc | The project targets Windows, and `msvcrt` reads Esc during the countdown without requiring Enter. |

## 2026-11-15 — Initial implementation

These choices implement the design already stated in `README.md`. They are recorded as routine implementation decisions; no additional owner approval was requested or given. No scope, interface, or cryptographic design change is proposed.

| Choice | Options considered | Reason |
| --- | --- | --- |
| `argon2-cffi` low-level Argon2id with 16-byte salt, 64 MiB memory, 3 iterations, 1 lane, 32-byte output | Argon2id library defaults; other work factors | Explicit, portable parameters with a meaningful memory cost and simple fixed-format implementation. |
| `cryptography` AES-256-GCM with a fresh random 12-byte nonce per encryption | Custom crypto; deterministic nonce counter | Established implementation; random nonce is simple for a small local vault. Reuse is extremely unlikely at this scale but cannot be mathematically excluded. |
| Versioned JSON envelope with base64 salt, nonce, ciphertext; encrypted JSON entries | Binary format; database | Easy to inspect structure and maintain without exposing entry contents. Unknown versions are rejected. |
| Save on each change with same-directory temporary file and `os.replace` | In-place updates; delayed saves | Reduces risk of a partial update and keeps the CLI simple. |
| `secrets.choice` plus secure shuffle, including one character from each selected group | Pure random draws without group guarantee | Meets selected settings while using the standard library cryptographic RNG. |
| `unittest` and `pyproject.toml` | External test framework; script-only distribution | Keeps test dependencies minimal and provides an installable CLI. |

Standalone executable packaging remains a future goal from `README.md`; it was not implemented in this initial Python application.
