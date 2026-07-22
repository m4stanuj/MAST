# Security Policy

MAST is a local-first AI operator stack. Security-related functionality in this repository is intended for defensive, authorized, and scope-gated use only.

## Supported Scope

MAST is designed for:

- Local development environments.
- User-owned machines and workspaces.
- Explicitly authorized security labs, CTFs, and audits.
- MCP tools that run with clear local control and visible configuration.

MAST is not intended for unauthorized scanning, credential abuse, stealth persistence, or activity against systems you do not own or do not have written permission to test.

## Reporting a Vulnerability

If you find a security issue:

1. Do not open a public issue with exploit details, secrets, or live target information.
2. Email `mast.jarvis@gmail.com` with a short description, affected component, reproduction steps, and expected impact.
3. Include whether the issue affects local-only usage, MCP tool execution, browser automation, API key handling, or security workflow boundaries.

Reports that can expose secrets, execute unsafe commands, bypass authorization checks, or affect user data should be treated as high priority.

## Secrets and API Keys

- Keep API keys in `.env` files only.
- Never commit real keys, tokens, cookies, session storage, or browser profiles.
- Use `.env.example` for placeholders.
- Rotate any key immediately if it was committed by mistake.

## Safety Boundaries

Security-related tools must remain:

- Authorized only.
- Defensive by default.
- Scope-gated before active scanning.
- Logged enough for review.
- Designed with human approval for risky actions.

## Preferred Fix Style

For security fixes, prefer small focused patches that:

- Add validation before execution.
- Fail closed when scope is missing.
- Mask secrets in logs and UI.
- Keep localhost bindings unless a user explicitly configures otherwise.
- Add tests or a short verification note when practical.
