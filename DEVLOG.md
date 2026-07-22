# MAST Devlog

MAST is the flagship local-first operator stack in the M4ST ecosystem. This log tracks meaningful public upgrades to trust, safety, setup clarity, and operator reliability.

## Build Direction

MAST combines MCP servers, task routing, fallback LLM chains, memory, browser automation, scheduler workflows, local model fallback, and defensive security tooling.

The target environment is intentionally practical:

- Consumer hardware.
- Local-first config.
- Free-tier provider routing before paid escalation.
- Windows/Kali workflows.
- Human-readable setup and recovery paths.

## Trust Layer Upgrade

The repo now includes a clearer trust and contribution surface:

- `SECURITY.md` for vulnerability reporting and authorized-use boundaries.
- `CONTRIBUTING.md` for safe contribution types and review expectations.
- `.env.example` for placeholder-based setup without leaking real keys.
- `docs/SAFETY.md` for local-first safety, scope checks, and risky-action guidance.
- README resource links pointing to the new trust docs.

## Contribution Style

MAST contributions should be small, useful, and easy to review.

Good changes include:

- Setup documentation.
- Safety checks.
- Tests around routing, memory, and scope validation.
- CI and secret-scan improvements.
- Examples that use localhost, demo data, or authorized lab targets.
- Demo scripts and walkthroughs.

## Safety Direction

Security and OSINT workflows stay:

- Authorized only.
- Defensive by default.
- Scope-gated.
- Human-reviewed for risky actions.
- Localhost/local-first unless explicitly configured otherwise.

## Next Up

- Add a lightweight secret-scan CI step.
- Add a setup verification script.
- Add minimal tests for config loading and safety boundaries.
- Add clearer demo commands for the main routing loop.
- Add a release note for the trust-surface upgrade.
