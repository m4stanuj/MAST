# Contributing to MAST

MAST is a local-first AI operator system built around MCP tooling, routing, memory, automation, and defensive workflows. Contributions should make the stack more reliable, reproducible, and safe to run.

## Good Contribution Types

- Documentation that makes setup, safety, or architecture easier to understand.
- Small tests for routing, memory, safety checks, and config loading.
- Safer defaults for command execution, browser automation, API key handling, and scan scope.
- Examples that use placeholders and local/demo targets only.
- CI improvements that verify syntax, tests, and secret hygiene.
- Bug fixes that are narrow, explained, and easy to review.

## Safety Rules

- Do not add code or docs that enable unauthorized access, stealth, credential theft, or scanning third-party systems without permission.
- Security examples must use localhost, owned lab targets, CTFs, or clearly authorized scopes.
- Never commit real API keys, tokens, cookies, browser profiles, session files, or private target data.
- Keep risky actions behind explicit user confirmation or scope checks.

## Development Flow

1. Fork or branch from `main`.
2. Keep the change small and focused.
3. Run the relevant checks locally when possible.
4. Add or update docs/tests when behavior changes.
5. Open a pull request with:
   - What changed.
   - Why it matters.
   - How it was tested.
   - Any safety or compatibility notes.

## Local Checks

```bash
python -m compileall mcp_servers bridge_core
```

If you add tests:

```bash
pytest tests -q
```

## Commit Style

Use clear, simple commit messages:

- `docs: clarify MCP setup`
- `test: add router safety checks`
- `fix: mask provider keys in logs`
- `ci: add secret scan`

## Review Priorities

MAST favors changes that improve:

- Reproducibility.
- Local-first operation.
- Defensive security posture.
- Setup clarity.
- Runtime resilience under free-tier APIs and consumer hardware.
