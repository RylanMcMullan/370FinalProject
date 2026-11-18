# Security review disposition

Reviewed: 2026-11-17. These are responses to the 14 findings supplied by the owner. Tests and limitations are summarized in `CURRENT_STATE.md`.

| # | Disposition |
| --- | --- |
| 1 | New master passwords require 12+ characters and a local strength score; existing vaults remain unlockable. Offline guessing remains possible if a weak existing master password is used. |
| 2 | The screen is cleared on lock, reset, timeout, and handled errors. A crash or some terminals' scrollback and captures may still leave text visible. |
| 3 | Interactive Windows console input times out after five minutes without a keypress. |
| 4 | Unlock shows the authenticated last-saved time, as requested. This cannot detect a restored older copy. |
| 5 | New default vaults use a per-user local app-data folder. The Windows file DACL is replaced with a protected current-user grant, including for an existing vault after successful unlock. Existing project-folder vaults stay in place. |
| 6 | Three attempts remain a per-run user-interface limit. It does not restrict offline guessing or a restarted app; the master-password policy addresses some of that risk. |
| 7 | The help example no longer suggests a repository-local file. Vault JSON patterns are ignored, and new default vaults are outside the repository. |
| 8 | Empty unlock input counts as a failed attempt; empty reset input cancels reset without exiting the program. |
| 9 | Menu option 8 verifies the current master password and re-encrypts entries with a new strong master password and salt. |
| 10 | Deletion removes the current file or entry only. Backups, filesystem snapshots, and old encrypted copies cannot be reliably erased by this program. |
| 11 | A lock file and on-disk fingerprint prevent stale sessions from silently overwriting newer changes. |
| 12 | Password prompts require a real terminal and use non-echoing Windows console input. Unsupported environments receive an error. |
| 13 | Direct dependencies are pinned; the tested Windows/Python 3.14 runtime wheels have hashes in `requirements-windows-py314.lock`. |
| 14 | The local `yo2.txt` file was removed. History still contains the named commits; no history rewrite, GitHub access change, branch protection, or push was made. Repository rules need a connected GitHub account with administrative rights. |
