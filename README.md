# Folio - AI Agent Task Executor

Folio is a system that assigns AI agents to HTTP endpoints and allows them to work autonomously by sending Markdown-formatted task definitions (`TASK.md`).

## Overview

- **HTTP API Driven**: Each agent functions as a RESTful API endpoint.
- **Task Oriented**: Receives instructions in a standardized format called `TASK.md`.
- **Secure Execution Environment**: Agent code execution is performed within a Docker sandbox, minimizing impact on the host system.
- **Web Management**: Agent management, log checking, and user management can be done via the Web UI.
- **Extensibility**: Users can define new agents and tools simply by adding configuration files and Python code.

## Directory Structure (Ideal)

This project recommends the following structure:

```
Folio/
├── agents/             # [User Extension Area] Agent Definitions (TOML config, prompts, etc.)
│   └── default/
│       ├── contract.toml
│       └── RULE.md
├── skills/             # [User Extension Area] Reusable Skill Sets / Knowledge Base
├── tools/              # [System Extension Area] Tool Implementations (Python Code)
│   ├── system.py
│   ├── docker.py
│   └── web.py
├── app/                # Application Core
│   ├── api/            # HTTP API Endpoint Definitions
│   ├── core/           # Core Logic (Auth, DB, Sandbox Control)
│   ├── models/         # Database Models
│   └── ui/             # Web UI for Management
├── sessions/           # Execution Logs / Session Data Storage
├── pyproject.toml      # [Root] Project dependencies and configuration
├── .venv/              # [Created by uv] Python virtual environment
├── .env                # Environment Variables
└── README.md
```

## Components

### Agents & Skills
Users can define new agents or extend capabilities by adding files to the `agents/` and `skills/` directories. These can also be managed independently as Git repositories.

### Tools (in `tools/`)
A collection of tools implemented in Python. Placing them in the root `tools/` directory allows for easy extension and integration. These tools can be referenced from agent configurations.

### Docker Sandbox
When agents execute code, it runs in isolation within a Docker container. This prevents unintended changes to the system and mitigates security risks.

## Setup

1. **Prepare LLM Backend**: Have an OpenAI API compatible server or an OpenAI API key ready.
2. **Configure Environment Variables**: Create a `.env` file and set the necessary API keys and secrets.
3. **Start**:
    ```bash
    uv run python app/main.py
    ```

## Usage

1. Create a new agent directory in `agents/` and define a `contract.toml`.
2. Access the Web UI (`http://localhost:8000/ui`) to verify the agent is recognized.
3. POST the content of `TASK.md` to the agent's endpoint.

```bash
curl -X POST http://localhost:8000/api/agents/{agent_id}/invoke \
  -H "Content-Type: text/plain" \
  --data-binary @TASK.md
```
