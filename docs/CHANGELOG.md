# Changelog

## 2026-11-17

- Clarified CLI help, entry prompts, and password generation settings and length range.
- Added three unlock attempts, a three-second exit countdown, and Esc cancellation that leaves the vault locked after the third failure.
- Added confirmed vault reset with master password re-entry; Esc before the countdown ends preserves the vault file.
- Added tests for lockout, reset, prompt clarity, and countdown cancellation; all 14 tests passed.
- No agent-made commit or push for this update.

## 2026-11-15

- Added installable Python package, interactive menu, encrypted vault storage, password generator, and automated tests.
- Added `.gitignore` for Python build artifacts, the local virtual environment, and the default vault file.
- Installed declared dependencies in `.venv`; all 7 tests passed, including the CLI flow test.
- Confirmed module help and compiled source/tests successfully.
- Initial implementation was later committed by the owner as `18e0e73` (`Implementation #1: Initial program`).
