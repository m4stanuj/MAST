# MAST v1.0 Presentation

## Slide 1: Title

```text
MAST
Mast Autonomous System Terminal

Unified AI operator:
M4STCLAW v3 + OpenWork v12 + EIGENT v4.1
```

## Slide 2: Problem

```text
AI coding tools are powerful, but fragmented.

One tool has memory.
One has browser automation.
One has file access.
One has pentest flow.
One has skills.
One has routing.

The operator becomes the integration layer.
```

## Slide 3: Solution

```text
MAST turns the workspace into the integration layer.

21 MCP servers
28 hot-reloadable skills
11 provider routes
6 specialized agents
1 SOUL identity file
```

## Slide 4: System Architecture

```text
┌──────────────────────────────────────────────┐
│                 User / Operator              │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│ SOUL_MAST.md: identity, policy, routing rules │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│ task_router + skills + memory + safety        │
└──────────────┬───────────────┬───────────────┘
               │               │
        ┌──────▼──────┐ ┌──────▼──────┐
        │ MCP servers │ │  6 agents   │
        └──────┬──────┘ └──────┬──────┘
               │               │
        ┌──────▼───────────────▼──────┐
        │  Provider chains + fallback  │
        └──────────────────────────────┘
```

## Slide 5: Routing Algorithm

```text
Request
  -> safety gate
  -> skill search
  -> task classification
  -> MCP selection
  -> provider chain
  -> fallback / key rotation
  -> memory log
  -> response
```

## Slide 6: MCP Server Layer

```text
Core:
shell, file, memory, task_router, skills, research

Operator:
browser, vision, notify, scheduler, setup, doctor

Advanced:
react, m4st_agent, llm_fallback, scrapling, composio

Security:
pentest, safety, coding, bridge_core recon/vuln
```

## Slide 7: Agent Layer

| Agent | Role | Primary Work |
|-------|------|--------------|
| Developer | code execution | debug, refactor, implement |
| Browser | web tasks | navigation, research, forms |
| Document | writing | reports, docs, summaries |
| Multimodal | visual tasks | screenshots, OCR, GUI context |
| Pentest | authorized security | CEH labs, recon, reports |
| Orchestrator | OMO loop | plan, assign, critique, synthesize |

## Slide 8: Provider Strategy

```text
Free-first routing:
Groq -> Cerebras -> OpenRouter -> NVIDIA NIM -> Gemini
Mistral -> SambaNova -> DeepSeek -> Together -> Grok -> HuggingFace

Local model:
privacy/offline fallback for sensitive work
```

## Slide 9: Safety Model

```text
P0 guard blocks destructive commands.
Pentest requires authorized targets.
Secrets stay in .env.
Servers bind localhost only.
Telegram accepts allowed chat IDs only.
```

## Slide 10: Why It Matters

```text
MAST is not just a bot.
It is an operator stack:

memory + tools + routing + skills + agents + safety

Built for one developer moving fast under constraints.
```

## Slide 11: Demo Flow

```text
1. Install MAST
2. Add free API keys
3. Ask a Hinglish coding task
4. Trigger research + file edit
5. Show memory logging
6. Run MCP doctor
7. Show agent orchestration plan
```

## Slide 12: Closing

```text
MAST v1.0
Working > Perfect
Shipped > Planned
Jugaad-first, free-first, local when needed

github.com/m4stanuj/MAST
```
