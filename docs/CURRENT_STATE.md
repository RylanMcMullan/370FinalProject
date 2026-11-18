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
- New master passwords require at least 12 characters and pass the local `zxcvbn` strength check. Older vaults remain unlockable so existing data is not stranded. Menu option 8 changes the master password and re-encrypts entries with a fresh salt.
- Password input requires a real Windows terminal and does not echo. Keyboard input times out after five minutes of inactivity; closing or locking clears the console screen where supported.
- New default vaults use `%LOCALAPPDATA%\LocalPasswordManager\vault.json`. Windows ACLs are replaced with a protected grant for the current user. An existing `./vault.json` remains in place and is opened by default. `--vault` still selects an explicit file.
- Each save and reset checks that the vault has not changed since this session opened it; a Windows lock file serializes writes. Unlock displays the authenticated last-saved time when available.
- Runtime dependencies are pinned in `pyproject.toml`, with a hash-checked CPython 3.14 Windows lock file.

## Verified checks

- `python -m unittest discover -s tests -q` passed: 28 tests using `.venv`.
- `python -m password_manager --help` succeeded using `.venv`.
- `.venv\Scripts\password-manager.exe --help` succeeded.
- `python -m compileall -q password_manager tests` succeeded using `.venv`.
- `pip download --require-hashes --no-index` verified the Windows lock file against the selected wheels; `git check-ignore my-demo-vault.json` confirmed the help example is ignored.
- Synthetic Windows ACL checks found no inherited grants and one full-control grant, and confirmed that opening an existing vault removed an extra read grant.

## Known limitations

- No independent security audit. This public project is intended for synthetic demonstration credentials, as described in `SECURITY.md`.
- A running, unlocked computer can expose credentials; Python does not reliably erase password strings or keys from memory.
- A forgotten master password cannot be recovered. Authentication failure cannot distinguish a wrong password from tampering.
- The five-minute idle timeout applies to keyboard input in a real Windows terminal. Screen clearing may not remove all terminal scrollback or external captures.
- A full disk, power loss, or filesystem fault may still interrupt a save. Standalone executable packaging is not implemented; the installed Scripts `.exe` is a Python entry point.
- An older copied vault can still be restored and opened. Last-saved time is informational and cannot prove that a file is the newest copy.
- The three-attempt limit is local to one run; restarting allows another set of attempts. Deleting the vault file does not securely erase filesystem history or backups.
- Changing the master password does not invalidate older vault copies encrypted under the previous master password.
- GitHub branch protection and collaborator access have not been changed; the GitHub integration is not connected in this session.

## Next steps

- Review the 14 findings and remaining limits in `docs/SECURITY_REVIEW.md`.
- Owner review before any agent-made Git commit or push.
