# Development Instructions

Build a small, maintainable local password manager following `README.md` and `SECURITY.md`. Prefer working functionality and understandable code over additional features.

## Working approach
- Work within this repository. Make routine implementation choices independently, including dependencies, structure, tests, and fixes.
- Ask for approval before changing the agreed application scope, user interface, or cryptographic design, and before making **any Git commit or push**. Do not commit or push until authorized.
- Treat `AGENTS.md`, `README.md`, and `SECURITY.md` as owner-maintained: do not edit them without explicit approval.
- Run relevant tests when possible. Clearly distinguish executed checks from assumptions or proposed tests.
- Keep changes easy to review, with concise explanations of noteworthy choices.

## Agent-maintained records
Create and maintain these files under `docs/`:
- `CURRENT_STATE.md` — implemented features, known limitations, verified tests, and next steps.
- `CHANGELOG.md` — dated summary of work, fixes, and test outcomes; add commit references after approved commits.
- `DECISIONS.md` — important choices, options, rationale, and whether owner approval was requested, given, or pending. Do not invent approvals.

Update these records as work progresses. Keep them concise and factual, without claiming work was completed when it was not.
