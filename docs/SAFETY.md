# MAST Safety Model

MAST is designed as a local-first operator stack. It can connect to files, shell tools, browsers, memory, schedulers, and security workflows, so safety must be part of the system design rather than an afterthought.

## Core Principles

1. **Local first:** prefer `127.0.0.1`, local files, and user-owned workspaces.
2. **Scope before action:** active security workflows require a clear allowed scope.
3. **Human approval for risky steps:** destructive file operations, external scans, credential changes, and outreach exports should require review.
4. **Secrets stay out of code:** use `.env` files and placeholder examples only.
5. **Fail closed:** if scope, config, or permissions are unclear, do not run the risky action.

## Defensive Security Boundary

Security and OSINT features are for:

- CTFs and labs.
- Your own infrastructure.
- Written-permission audits.
- Defensive visibility and report generation.

They are not for unauthorized scanning, exploitation, stealth, persistence, or credential collection.

## Recommended Guardrails

- Keep services bound to localhost by default.
- Maintain an explicit allowed-target list.
- Mask API keys and tokens in logs.
- Write logs for important actions without storing secrets.
- Prefer dry-run modes for workflows that touch external systems.
- Use sample/demo data in docs and tests.

## Example Safe Targets

```text
localhost
127.0.0.1
testphp.vulnweb.com only if used according to its published testing policy
CTF boxes you are currently authorized to attack
Your own staging domain
```

## Pull Request Checklist

Before merging changes that touch shell, browser, OSINT, routing, or memory:

- [ ] Does the change keep localhost/local-first defaults?
- [ ] Does it avoid committing secrets or private data?
- [ ] Does it require explicit scope for active scanning?
- [ ] Does it include a safe demo or test path?
- [ ] Does the README or relevant doc mention any new risk?
