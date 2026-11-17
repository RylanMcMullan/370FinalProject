# Current State

Updated: 2026-11-17

## Implemented

- Interactive Python CLI with vault creation, unlocking, listing, viewing, adding, deleting, password generation, and locking by exit.
- Local JSON vault encrypted with AES-256-GCM; master password derived with Argon2id and a random per-vault salt. Each save uses a fresh random nonce.
- Saves after add/delete use a temporary file and atomic replacement. Initial creation refuses to overwrite an existing file.
- Automated tests cover vault persistence, wrong passwords, tampering, invalid formats, exclusive creation, fresh nonces, generator settings, and a CLI create/reopen flow.
- CLI prompts distinguish the user's name from the login username, explain generated password settings, and describe the vault path option. New master password setup repeats after empty or mismatched input.
- Both password generation flows use a fixed 4–20 character range with Enter selecting 20. Invalid lengths prompt again without clearing selected character groups.
- Unlock allows three attempts per run. After the third failure, the app shows a three-second close countdown; Esc stops automatic closing, but the vault stays locked until the user closes it manually.
- An authenticated user can reset the vault by choosing menu option 7, typing `RESET`, re-entering the master password, and letting the three-second countdown finish. Esc during the countdown cancels reset. Successful reset deletes the vault file, so the next launch creates a new vault.
- Lock and exit uses the same three-second countdown and can be canceled with Esc.

## Verified checks

- `python -m unittest discover -s tests -v` passed: 17 tests using `.venv`.
- `python -m password_manager --help` succeeded using `.venv`.
- `.venv\Scripts\password-manager.exe --help` succeeded.
- `python -m compileall -q password_manager tests` succeeded using `.venv`.

## Known limitations

- No independent security audit. This public project is intended for synthetic demonstration credentials, as described in `SECURITY.md`.
- A running, unlocked computer can expose credentials; Python does not reliably erase password strings or keys from memory.
- A forgotten master password cannot be recovered. Authentication failure cannot distinguish a wrong password from tampering.
- Concurrent writers, backups, and standalone executable packaging are not implemented. A full disk, power loss, or filesystem fault may still interrupt a save.
- File permission handling depends on the operating system; Windows ACLs are not explicitly managed.
- The three-attempt limit is local to one run; restarting allows another set of attempts. Deleting the vault file does not securely erase filesystem history or backups.

## Next steps

- Consider standalone executable packaging after the Python application has been reviewed.
- Owner review before any agent-made Git commit or push.
