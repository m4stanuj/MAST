# M4ST

Local-first AI operator infrastructure created by Mast Anuj.

M4ST helps AI coding assistants work less like cold chat sessions and more like practical operators: inspect context, choose the right workflow, use tools, run safe automation, verify output, and leave reusable artifacts.

## What It Does

- Reads project context before acting.
- Uses MCP tools and reusable skills.
- Routes tasks through free/local-first model fallback.
- Keeps useful project and operator memory.
- Supports browser and file workflows with human handoff for sensitive steps.
- Produces proof artifacts, logs, reports, and repeatable commands.
- Keeps security and OSINT work authorized, scoped, defensive, and evidence-based.

## Core Loop

```text
request -> context -> route -> execute -> verify -> artifact -> improve
```

## Main Components

| Component | Purpose |
|---|---|
| MCP tools | File, shell, browser, memory, research, scheduling, and security-safe tool access |
| Skills | Reusable workflow instructions for coding, research, browser work, safety, docs, and debugging |
| Routing | Task-aware free/local-first model fallback |
| Memory | Project facts, operator preferences, handoffs, and recovery context |
| Browser automation | Logged-in workflow support with CAPTCHA/OTP/payment/legal handoff |
| Safety layer | Secret redaction, approval gates, authorized-only security scope, and public-safe wording |
| Verification | Doctor checks, smoke tests, proof files, and reusable artifacts |

## Quick Start

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

Then configure local secrets through environment files. Do not commit API keys, passwords, tokens, or private account data.

## Project Shape

```text
M4ST/
  mcp_servers/     tool servers and routing helpers
  skills/          reusable operator workflows
  commands/        repeatable command recipes
  agents/          role and worker definitions
  config/          local config templates
  runtime modules/ local execution helpers
```

## Safety Boundary

Security and OSINT features are intended only for owned, approved, or explicitly authorized targets.

M4ST does not support unauthorized access, credential abuse, stealth, malware, or bypassing protections.

For OTP, CAPTCHA, payments, legal approval, account recovery, irreversible changes, or public posting, the operator pauses for human handoff.

## Current Focus

- Cleaner setup diagnostics.
- Runtime-lite task routing.
- Rolling multi-agent workflows.
- Public-safe documentation.
- Browser handoff rules.
- Proof artifacts and dashboards.

## Philosophy

```text
Bigger model? Useful.
Better context? Necessary.
Verified execution? Non-negotiable.
```

M4ST is built for practical systems that compound: small reusable tools, clear logs, local-first defaults, free-first routing, human approval gates, and safe automation.
