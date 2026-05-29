# M4ST Ecosystem

MAST is the flagship operator stack. The surrounding repositories are modules, extraction points, or history layers that make the system easier to understand, install, and reuse.

## Repository Map

| Repository | Role | Status |
|------------|------|--------|
| [MAST](https://github.com/m4stanuj/MAST) | Flagship AI operator: 21 MCP servers, 28 skills, 11 provider routes, 6 agents | Active flagship |
| [mast-llm-router](https://github.com/m4stanuj/mast-llm-router) | Task-aware LLM router with fallback chains and semantic cache | Active module |
| [openwork](https://github.com/m4stanuj/openwork) | Universal MCP workspace/config layer for IDEs and assistants | Active control plane |
| [semantic-cache-engine](https://github.com/m4stanuj/semantic-cache-engine) | Drop-in semantic response cache for LLM calls | Active module |
| [m4stclaw-legacy-archive](https://github.com/m4stanuj/m4stclaw-legacy-archive) | Historical archive for the M4STCLAW line | Archive |
| [cai-osint](https://github.com/m4stanuj/cai-osint) | OSINT and authorized pentest automation layer | Related security layer |
| [m4stanuj.github.io](https://github.com/m4stanuj/m4stanuj.github.io) | Public portfolio and project showcase | Public site |

## Layer Model

```text
Portfolio / Public Story
  -> m4stanuj.github.io

Flagship Operator
  -> MAST

Reusable System Modules
  -> mast-llm-router
  -> semantic-cache-engine
  -> openwork

Security Layer
  -> cai-osint

History
  -> m4stclaw-legacy-archive
```

## How the Pieces Fit

```text
User request
  -> MAST SOUL + safety policy
  -> OpenWork MCP config/control plane
  -> mast-llm-router provider fallback
  -> semantic-cache-engine repeated prompt savings
  -> MAST memory + skills + agents
  -> response / action / report
```

## Positioning

MAST should be treated as the main product. The other repositories are supporting components:

- Use `MAST` for the complete operator system.
- Use `mast-llm-router` when you only need model fallback.
- Use `semantic-cache-engine` when you only need semantic caching.
- Use `openwork` when you need portable MCP workspace config.
- Use `m4stclaw-legacy-archive` for background and lineage.

## Release Discipline

Every active repo should keep:

- A clear README with its role in the ecosystem
- A working CI check
- A version tag and GitHub release
- No secrets or machine-local config
- A short path from clone to first useful run
