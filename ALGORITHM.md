# MAST Algorithm

MAST is built around one control loop: understand the request, protect the operator, choose the right toolchain, execute, remember, and recover if something fails.

## 1. Request Intake

```text
User message
  -> SOUL_MAST.md identity
  -> project context
  -> recent memory
  -> active agent mode
```

The system keeps the personality and operating policy separate from tool code. Editing `SOUL_MAST.md` changes behavior without rewriting MCP servers.

## 2. Safety Gate

```text
Command / task
  -> destructive pattern scan
  -> localhost-only network policy
  -> pentest target authorization
  -> key/secrets boundary
```

High-risk operations are blocked before execution. Pentest flows must pass authorized-target checks in code, not only in comments or prompts.

## 3. Skill-First Routing

```text
Request
  -> search learned skills + SKILL.md workflows
  -> if match: run known workflow
  -> if no match: classify task
```

Skills are reusable behavior packs. They keep repeated work fast and consistent.

## 4. Task Classification

MAST routes requests into task families:

| Task | Typical Signal | Primary MCP |
|------|----------------|-------------|
| `speed` | quick answer, short summary | `task_router_mcp.py` |
| `code` | implement, debug, refactor | `coding.py`, `file_mcp.py`, `shell_mcp.py` |
| `research` | find, compare, deep dive | `research_mcp.py` |
| `vision` | screenshot, GUI, OCR | `vision_mcp.py` |
| `agent` | multi-step workflow | `m4st_agent_mcp.py` |
| `pentest` | scan, recon, CVE | `pentest_mcp.py` |
| `hinglish` | Hindi/Hinglish explanation | `llm_fallback.py` |
| `write` | docs, reports, captions | `llm_fallback.py` |

## 5. Provider Fallback Loop

```text
Selected chain
  -> provider 1
  -> if 429/auth/empty/error: cool down key
  -> provider 2
  -> provider 3
  -> final fallback pool
```

The routing policy is free-first: use local models and approved free/provider fallbacks where appropriate, then log the chosen route and reason.

## 6. Agent Orchestration

```text
Goal
  -> Orchestrator
  -> break into subtasks
  -> assign Developer / Browser / Document / Multimodal / Pentest
  -> parallel execution where safe
  -> critique + synthesize
```

This is the OMO Sisyphus loop: plan, execute, critique, refine, and checkpoint.

## 7. Memory Lifecycle

```text
Session start -> memory_get_context
Important fact -> memory_add_fact
Task complete -> memory_log_task
Project switch -> memory_set current_project
```

MAST uses layered memory: short context, SQLite recall, ChromaDB semantic search, and future Graphiti temporal memory.

## 8. Failure Recovery

| Failure | Recovery |
|---------|----------|
| Provider rate limit | Rotate key, cool down provider, fallback |
| Tool missing dependency | Return fix command and continue with degraded path |
| Vision model offline | Use text fallback or ask for screen description |
| Agent subtask fails | Retry, replace agent, skip, or return partial result |
| Unsafe command | Block and explain safer route |

## Design Rule

MAST optimizes for useful shipped capability over theoretical completeness:

> Working > Perfect. Shipped > Planned. Free-first. Local when privacy demands it.
