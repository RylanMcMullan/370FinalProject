# Changelog

## 2026-11-17

- Repeated new master password setup after empty or mismatched entries instead of exiting.
- Set password generation to 4–20 characters in both menu paths; Enter chooses 20. Invalid lengths now retry without resetting character choices.
- Changed the entry name prompt and view label to identify it as the user's name, distinct from the login username.
- Added tests for these flows; all 17 tests passed. No agent-made commit or push for these changes.
- The owner committed the preceding clarity and functionality update as `316a5b6` (`Implementation #2: Clarity and functionality`).
- Clarified CLI help, entry prompts, and password generation settings and length range.
- Added three unlock attempts, a three-second exit countdown, and Esc cancellation that leaves the vault locked after the third failure.
- Added confirmed vault reset with master password re-entry; Esc before the countdown ends preserves the vault file.
- Added tests for lockout, reset, prompt clarity, and countdown cancellation; all 14 tests passed.

## 2026-11-15

- Added installable Python package, interactive menu, encrypted vault storage, password generator, and automated tests.
- Added `.gitignore` for Python build artifacts, the local virtual environment, and the default vault file.
- Installed declared dependencies in `.venv`; all 7 tests passed, including the CLI flow test.
- Confirmed module help and compiled source/tests successfully.
- Initial implementation was later committed by the owner as `18e0e73` (`Implementation #1: Initial program`).
