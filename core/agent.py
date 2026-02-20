#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build pydantic-ai Agent instances from DB rows."""
from __future__ import annotations

from pydantic_ai import Agent as PydanticAgent, ConcurrencyLimiter, ConcurrencyLimitedModel
from pydantic_ai.builtin_tools import (
    CodeExecutionTool,
    FileSearchTool,
    ImageGenerationTool,
    MCPServerTool,
    MemoryTool,
    WebFetchTool,
    WebSearchTool,
)
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from sqlmodel import Session as DBSession, select
import json

from models.agent import Agent as AgentRow
from models.provider import Provider
from models.skill import Skill
from models.equip import Equip
from models.session import Session
from core.capabilities import CAPABILITY_MAP, CapKind


# ── Built-in tool factories ────────────────────────────────────────
# Maps capability id → callable that returns a PydanticAI Tool instance.
# Kept as lazy lambdas so we only import heavy modules when actually needed.

_BUILTIN_FACTORIES: dict[str, callable] = {
    "web-search":       lambda: WebSearchTool(),
    "code-execution":   lambda: CodeExecutionTool(),
    "image-generation": lambda: ImageGenerationTool(),
    "web-fetch":        lambda: WebFetchTool(),
    "memory":           lambda: MemoryTool(),
    "mcp":              lambda: MCPServerTool(),
    "file-search":      lambda: FileSearchTool(),
}

# ── Custom (Folio) tool factories ──────────────────────────────────

_CUSTOM_FACTORIES: dict[str, callable] = {
    # "shell":          lambda: ...,
    # "pyfoundations":  lambda: ...,
}


def build_model(agent_row: AgentRow, provider_row: Provider) -> Model:
    """Build a pydantic-ai Model from DB rows."""
    if provider_row.kind == "openai-responses":
        provider = OpenAIProvider(base_url=provider_row.endpoint, api_key=provider_row.apikey)
        return OpenAIResponsesModel(agent_row.model, provider=provider)
    if provider_row.kind in ("openai-chat", "openai-completions"):
        provider = OpenAIProvider(base_url=provider_row.endpoint, api_key=provider_row.apikey)
        return OpenAIChatModel(agent_row.model, provider=provider)
    raise ValueError(f"Unsupported provider kind: {provider_row.kind}")


def build_prompt(agent_row: AgentRow, db: DBSession) -> str:
    """Build system prompt from agent's own prompt + equipped skills."""
    parts: list[str] = []
    if agent_row.prompt:
        parts.append(agent_row.prompt)
    equips = db.exec(select(Equip).where(Equip.agent == agent_row.id)).all()
    for equip in equips:
        skill = db.get(Skill, equip.skill)
        if skill and skill.body:
            parts.append(skill.body)
    return "\n".join(parts)


def _build_settings(agent_row: AgentRow, caps: set[str]) -> ModelSettings | None:
    """Build ModelSettings from stored params + flag capabilities."""
    raw_params = json.loads(agent_row.model_params) if agent_row.model_params else {}
    ms: ModelSettings = {}

    # Numeric params
    for key, cast in [
        ("temperature", float), ("top_p", float),
        ("max_tokens", int), ("seed", int),
        ("presence_penalty", float), ("frequency_penalty", float),
    ]:
        if key in raw_params:
            ms[key] = cast(raw_params[key])

    # ── Flag capabilities ──────────────────────────────────────────
    if "reasoning" in caps:
        # Providers that support extended thinking (o-series, DeepSeek-R1, …)
        # expose it under different keys; pydantic-ai normalises to these:
        ms["thinking"] = {"type": "enabled", "budget_tokens": 10000}

    return ms or None


def _build_tools(caps: set[str]) -> tuple[list, list]:
    """Instantiate tools for every builtin/custom capability enabled.
    
    Returns (builtin_tools, custom_tools) — builtin tools go to Agent(builtin_tools=...),
    custom tools go to Agent(tools=...).
    """
    builtin: list = []
    custom: list = []
    for cap_id in caps:
        cap = CAPABILITY_MAP.get(cap_id)
        if cap is None:
            continue
        if cap.kind == CapKind.BUILTIN:
            factory = _BUILTIN_FACTORIES.get(cap_id)
            if factory:
                builtin.append(factory())
        elif cap.kind == CapKind.CUSTOM:
            factory = _CUSTOM_FACTORIES.get(cap_id)
            if factory:
                custom.append(factory())
    return builtin, custom


def build_agent(agent_row: AgentRow, provider_row: Provider, db: DBSession) -> PydanticAgent:
    """Build a complete pydantic-ai Agent from DB rows."""
    model = build_model(agent_row, provider_row)

    if agent_row.concurrency:
        model = ConcurrencyLimitedModel(
            model,
            limiter=ConcurrencyLimiter(max_running=agent_row.concurrency, name=f"pool-{agent_row.id}"),
        )

    prompt = build_prompt(agent_row, db)

    # Parse capability set
    caps: set[str] = set(json.loads(agent_row.capabilities)) if agent_row.capabilities else set()

    settings = _build_settings(agent_row, caps)
    builtin_tools, custom_tools = _build_tools(caps)

    return PydanticAgent(
        model,
        system_prompt=prompt,
        deps_type=Session,
        model_settings=settings,
        builtin_tools=builtin_tools if builtin_tools else [],
        tools=custom_tools if custom_tools else [],
    )