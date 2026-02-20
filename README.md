# Folio

An AI agent management and orchestration platform.
Built with a FastAPI backend and SolidJS frontend, enabling creation, configuration, and real-time interaction with multiple AI agents through a Web UI.

## Overview

- **DB-Driven Agent Management** — Agent definitions stored in SQLite. Create, edit, and delete via Web UI
- **PydanticAI Runtime** — Build LLM agents with [pydantic-ai](https://ai.pydantic.dev/). Separates built-in tools (Web Search, Code Execution, etc.) from custom tools
- **Multi-Provider Support** — Register OpenAI Responses API / Chat Completions API / local LLMs as Providers and switch per agent
- **Real-Time Chat** — Streaming responses via WebSocket. Conversation history persisted in DB
- **Capability Tag System** — Declaratively assign abilities using 3 kinds: Flag (vision, reasoning) / Builtin (web-search, code-execution) / Custom (shell)
- **Skill Equipment** — Extend agent knowledge by equipping reusable prompt fragments (Skills) to agents (Equip)
- **Approval Flow** — Manage tool-call approval requests before execution. Designed for extension to learned auto-approval
- **Token Auth** — Simple Bearer token authentication with 3 kinds: User / Node / Service

## Directory Structure

```
Folio/
├── main.py              # FastAPI entrypoint (startup, router registration, SPA serving)
├── api/                 # REST API endpoints
│   ├── agents.py        #   Agent CRUD + WebSocket chat + avatar upload
│   ├── approvals.py     #   Approval request management
│   ├── auth.py          #   Login authentication
│   ├── providers.py     #   LLM provider CRUD
│   ├── skills.py        #   Skill CRUD
│   └── tokens.py        #   Token CRUD
├── core/                # Core logic
│   ├── agent.py         #   pydantic-ai Agent builder (model, tools, prompt)
│   ├── auth.py          #   Bearer token authentication logic
│   ├── capabilities.py  #   Capability definitions (Flag / Builtin / Custom)
│   ├── channel.py       #   Async communication channel
│   └── db.py            #   SQLite engine and session management
├── models/              # SQLModel table definitions
│   ├── agent.py         #   Agent
│   ├── approval.py      #   Approval
│   ├── auth.py          #   Operator (internal auth model)
│   ├── chat.py          #   Chat
│   ├── cron.py          #   Cron
│   ├── equip.py         #   Equip (Agent <-> Skill join table)
│   ├── journal.py       #   Journal
│   ├── provider.py      #   Provider
│   ├── session.py       #   Session
│   ├── skill.py         #   Skill
│   └── token.py         #   Token
├── templates/           # Prompt templates
│   └── Agent.md         #   Agent system prompt template
├── tools/               # Custom tool implementations
│   ├── cli.py           #   CLI utilities
│   ├── docker.py        #   Docker container operations
│   ├── expr.py          #   Mathematical expression evaluation
│   ├── gh.py            #   GitHub integration
│   ├── send.py          #   Message sending
│   └── shell.py         #   Shell command execution
├── ui/                  # Frontend (SolidJS + TypeScript + Vite + Tailwind)
│   └── src/
│       ├── App.tsx          # Routing
│       ├── MainLayout.tsx   # Sidebar layout
│       ├── Dashboard.tsx    # Dashboard
│       ├── Agents.tsx       # Agent list
│       ├── AgentDetail.tsx  # Agent detail & editor
│       ├── Approvals.tsx    # Approval management
│       ├── Chats.tsx        # Chat interface
│       ├── Providers.tsx    # Provider management
│       ├── Skills.tsx       # Skill management
│       ├── Tokens.tsx       # Token management
│       ├── Sessions.tsx     # Session list
│       └── Timeline.tsx     # Timeline
├── schema.sql           # SQLite schema definition (9 tables)
├── pyproject.toml       # Python dependencies (uv)
└── app.db               # SQLite database (auto-generated)
```

## Setup

### Prerequisites

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) (package manager)
- Node.js >= 18 (for frontend build)

### Steps

```bash
# 1. Install dependencies
uv sync

# 2. Build frontend
cd ui && npm install && npm run build && cd ..

# 3. Start server
uv run python3 -m main
```

On first launch, `app.db` is auto-generated and an admin token is printed to the console.

### Default Provider

The initial seed registers a `local` provider (Apple On-Device / `http://127.0.0.1:11535/v1`).
To use external LLMs, add providers through the Web UI.

## Usage

1. **Open `http://localhost:8000` in a browser**
2. **Log in with the initial token** (the `fol_...` token printed to console)
3. **Register a Provider** — Configure LLM connection details
4. **Create an Agent** — Set model, prompt, and capabilities
5. **Chat** — Start a real-time conversation from the agent detail page

### API

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/capabilities` | List capability tags |
| GET/POST | `/agents` | List / create agents |
| GET/PUT/DELETE | `/agent/{id}` | Get / update / delete agent |
| WS | `/agent/{id}/chat` | WebSocket chat |
| POST | `/agent/{id}/avatar` | Upload avatar |
| GET/POST | `/providers` | List / create providers |
| GET/PUT/DELETE | `/provider/{id}` | Get / update / delete provider |
| GET/POST | `/skills` | List / create skills |
| GET/POST | `/approvals` | List / create approvals |
| PUT | `/approval/{id}` | Update approval status |
| GET/POST | `/tokens` | List / create tokens |
| DELETE | `/token/{id}` | Delete token |
| POST | `/auth/login` | Token authentication |

All endpoints require `Authorization: Bearer <token>` header (except `/auth/login`).

## Tech Stack

| Layer | Technology |
|-------|------------|
| LLM Runtime | pydantic-ai 1.62+ |
| Backend | FastAPI + Uvicorn |
| Database | SQLite (SQLModel / SQLAlchemy) |
| Frontend | SolidJS + TypeScript + Vite |
| Styling | TailwindCSS (achromatic design) |
| Package Management | uv (Python) / npm (Node.js) |
