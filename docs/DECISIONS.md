# Decisions

## 2026-11-17 — Security review implementation

The owner requested fixes for the pasted findings. The owner then chose to leave existing project-folder vaults in place and show the authenticated last-saved time without a separate rollback warning record. Those choices do not establish rollback protection. No approval for a Git commit or push was given.

| Choice | Rationale and limit |
| --- | --- |
| Require 12 characters and `zxcvbn` score of at least 3 for newly set master passwords | Rejects short and obvious choices without a network breach lookup. Existing weak vaults can still be opened and upgraded. A strength estimator cannot guarantee resistance to guessing. |
| Use Windows console key input with a five-minute idle timeout | Avoids `getpass` echo fallback and closes idle sessions. A nonterminal password prompt fails closed; this Windows-focused implementation is not portable to other operating systems. |
| Clear the console on lock and reset | Reduces exposure of displayed passwords; terminal scrollback or captures may persist. |
| Store `saved_at` inside authenticated payload, retaining support for older payloads | Shows when the file claims it was last saved. Restored old copies remain valid; this is not rollback detection. |
| Default new vaults to `%LOCALAPPDATA%` and replace Windows DACLs with the Win32 security API | Avoids creating new vaults in a public repository or shared launch folder. Existing `./vault.json` stays in place as requested and receives a protected file ACL after successful unlock. |
| Use a Windows lock file plus a content fingerprint on write | Prevents two live sessions from silently overwriting each other's saved changes. |
| Pin direct dependencies and provide a hash-checked Windows/Python 3.14 runtime lock | Reproducible runtime install on the tested platform; other Python/platform combinations need their own lock. |

## 2026-11-17 — Follow-up usability fixes

The owner explicitly requested these interface changes on 2026-11-17. No cryptographic design change was requested or made.

| Choice | Rationale |
| --- | --- |
| Repeat both master password setup fields after a mismatch or empty password | Keeps the creation flow open and makes the correction path clear. Closing the program still stops setup. |
| Fix generated password length at 4–20 characters for every character selection, with Enter choosing 20 | Applies the owner's requested range consistently to standalone generation and generation while adding an entry. |
| Retry only the length after an invalid length entry | Preserves the user's chosen character groups. |
| Label the stored `name` field as the user's name in the CLI | Distinguishes it from the login username without changing vault format or existing entries. |

## 2026-11-17 — Requested CLI changes

The owner explicitly requested clearer prompts, three unlock attempts, a countdown before closing, and a confirmed vault reset. These changes were authorized in the 2026-11-17 request. The owner clarified that Esc after the third failed unlock should stop automatic closing while leaving the vault locked, with manual closing required.

| Choice | Rationale |
| --- | --- |
| Show selected character groups before asking for length | Initially allowed a group-dependent minimum; the later owner request fixed the range at 4–20. |
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
