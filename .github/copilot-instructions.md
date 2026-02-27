# Folio — Copilot Project Context

## Stack
- **Backend**: FastAPI + pydantic-ai + SQLite (SQLModel ORM)
- **Frontend**: SolidJS (Vite + TypeScript + Tailwind)
- **Run**: `uv run python3 -m main` on port 8000
- **Branch**: `feature/timeline`

## DB Patterns (strict)
- Always `db.flush() + db.commit()` — NEVER `db.refresh()`
- `PRAGMA foreign_keys=ON`, `check_same_thread=False`
- Engine defined in `core/db.py`; session via `get_db()` dependency

## Architecture Overview

```
main.py                  FastAPI app, lifespan, _seed_db, router mounts
core/
  agent.py               build_agent() → pydantic-ai Agent from DB rows
  capabilities.py        CAPABILITY_MAP — CapKind.BUILTIN / CUSTOM
  scheduler.py           Vixie-cron minute-boundary loop (croniter 6.0.0)
  auth.py                JWT creation/verification, get_current_sender
  db.py                  SQLite engine + get_db()
  config.py              HOST, PORT
api/
  agents.py              Agent CRUD + /agent/{id}/chat (SSE stream)
  journal.py             Memo CRUD (9 endpoints)
  crons.py               Cron CRUD
  providers.py           Provider CRUD
  skills.py              Skill CRUD
  tokens.py              Token CRUD
  timeline.py            Timeline post CRUD
models/
  agent.py               Agent(id, provider, model, name, prompt, capabilities, model_params, concurrency)
  journal.py             Journal(id, agent→FK, abstract, body, pinned, timestamp, update)
  cron.py                Cron(id, agent→FK, name, schedule JSON, message, enabled, last_run)
  provider.py            Provider(id, name, kind, config JSON)
tools/
  foundation.py          foundation_tools — always given to every agent (identity, approve, etc.)
  journal.py             memo_tools — 7 tools: write/read/rewrite/forget/pin/unpin/search
  cron.py                cron_tools — CRUD for agent's own cron schedules
  post.py                post tool — timeline posting
templates/
  Agent.md               Default system prompt template
  Profile.md             Default profile template
ui/src/
  AgentDetail.tsx        Agent detail page including Memories section
```

## Provider Kinds (5)
`openai-chat`, `openai-responses`, `google`, `anthropic`, `xai`

Seed provider: **local** (Apple On-Device, `http://127.0.0.1:11535/v1`, kind=`openai-chat`)

## Tool Pattern
Every custom toolset calls the **own API** via `httpx` with a per-request JWT:
```python
token = create_jwt(sender)
async with httpx.AsyncClient() as client:
    resp = await client.post(f"http://localhost:{PORT}/agent/{sender.id}/memo", ...)
```

## Capabilities System
`core/capabilities.py` → `CAPABILITY_MAP: dict[str, Capability]`

| id | kind | description |
|----|------|-------------|
| `memo` | CUSTOM | Persistent memory with pin/unpin |
| `cron` | CUSTOM | Manage own cron schedules |
| `timeline` | CUSTOM | Post to timeline |
| `reasoning` | flag | Extended thinking (o-series, etc.) |
| `web-search` | BUILTIN | pydantic-ai WebSearchTool |
| `web-fetch` | BUILTIN | pydantic-ai WebFetchTool |
| etc. | BUILTIN | other pydantic-ai builtins |

`foundation_tools` (identity, approval, etc.) are given to **every agent unconditionally** — NOT in CAPABILITY_MAP.

## Memo System (NTM-inspired design)

Philosophy: agent has **full autonomy** over memory. No magic numbers, no importance scoring.

### Storage
`models/journal.py` → table `journals` (abstract, body, pinned bool)

### Toolset (tools/journal.py → `memo_tools`)
| tool | purpose |
|------|---------|
| `memo_write(content, abstract)` | Create unpinned memo |
| `memo_read(memo_id)` | Read full body |
| `memo_rewrite(memo_id, content, abstract)` | Update memo |
| `memo_forget(memo_id)` | Delete permanently |
| `memo_pin(memo_id)` | Pin → abstract appears in every system prompt |
| `memo_unpin(memo_id)` | Unpin → stays in storage, not injected |
| `memo_search()` | Returns ALL abstracts (no keyword arg) for LLM to evaluate |

### Injection (core/agent.py `_inject_pinned_memos`)
When `"memo"` is in agent capabilities, every run injects:
```
📌 Pinned memories:
 [2] Tech stack overview
 [5] User language preference

🗄️ 3 other memories available (use memo_search to find them)
```

### Design decisions
- **No keywords in search**: LLM may hallucinate keywords → returns ALL abstracts, LLM reads directly
- **Pin = always visible**: agent chooses what's "currently relevant"
- **Unpin ≠ delete**: demoted to searchable storage
- **Forget = delete**: irreversible, agent's pruning decision

## Scheduler (core/scheduler.py)
Vixie-cron: wakes every minute at `:00`, scans `crons` table, fires matching rows.

Schedule JSON format:
```json
{ "cron": "0 9 * * 1" }      // cron expression
{ "at": ["09:00", "18:00"] }  // daily time list
{ "interval": 30 }            // interval in minutes
```
- `_running: set[int]` prevents concurrent runs of same cron row
- Uses `croniter.match(expr, minute)`

## SPA Routing
API paths that must NOT fall through to SPA catch-all (in `main.py`):
`"agent", "auth", "approval", "cron", "memo", "provider", "skill", "timeline", "token", "capabilit", "identit"`

## Future Work (not yet implemented)
1. **Session system**: Mission-based multi-agent collaborative task execution
   - Agent assigns roles → spawns sub-agents → collects results
   - Like: Web analyst → Strategy analyst → Coder
2. **Agent-to-agent send tool**: trigger another agent's run from within a run
3. **Event-driven reactions**: agents react to timeline posts, approvals, etc.

## Key Rules
- Model/DB: `db.flush() + db.commit()` always, never `db.refresh()`
- Tools: always FunctionToolset calling own REST API via httpx+JWT
- Capabilities: NEVER double-register a toolset (was a bug: pyfoundations both in foundation_tools unconditionally AND in CAPABILITY_MAP → removed from map)
- LLM autonomy: tools should empower agent decisions, not make decisions for the agent
