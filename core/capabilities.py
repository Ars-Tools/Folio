#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Predefined agent capability tags.

Each capability has a *kind* that determines how it is resolved at runtime
when building an agent:

  flag    – API-level feature (e.g. vision, reasoning). Applied via model
            settings or request parameters; no tool object needed.
  builtin – Maps 1-to-1 to a PydanticAI built-in Tool class.  The tool is
            instantiated and appended to the agent's tool list.
  custom  – Folio-original tool resolved from the ``tools/`` package.
"""

from dataclasses import dataclass
from enum import Enum


class CapKind(str, Enum):
    FLAG = "flag"
    BUILTIN = "builtin"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Capability:
    id: str           # canonical slug stored in DB  (e.g. "web-search")
    label: str        # human-readable short name
    description: str  # tooltip / help text
    kind: CapKind     # dispatch selector


# fmt: off
CAPABILITIES: list[Capability] = [
    # ── Flags (API-level) ─────────────────────────────────────────────
    Capability("vision",           "Vision",           "Process and analyse images",               CapKind.FLAG),
    Capability("reasoning",        "Reasoning",        "Extended chain-of-thought reasoning",      CapKind.FLAG),

    # ── PydanticAI Built-in Tools ─────────────────────────────────────
    Capability("web-search",       "Web Search",       "Search the web for information",           CapKind.BUILTIN),
    Capability("code-execution",   "Code Execution",   "Run code in a sandboxed environment",      CapKind.BUILTIN),
    Capability("image-generation", "Image Generation", "Generate images from text prompts",        CapKind.BUILTIN),
    Capability("web-fetch",        "Web Fetch",        "Fetch and read web pages",                 CapKind.BUILTIN),
    Capability("memory",           "Memory",           "Persistent memory across conversations",   CapKind.BUILTIN),
    Capability("mcp",              "MCP",              "Connect to Model Context Protocol servers", CapKind.BUILTIN),
    Capability("file-search",      "File Search",      "Search and retrieve file contents",        CapKind.BUILTIN),

    # ── Folio Custom Tools ────────────────────────────────────────────
    Capability("shell",            "Shell",            "Execute shell commands",                   CapKind.CUSTOM),
    Capability("timeline",         "Timeline",         "Read and write timeline entries",          CapKind.CUSTOM),
    Capability("memo",             "Memo",             "Persistent memory with pin/unpin for autonomous recall", CapKind.CUSTOM),
    Capability("cron",             "Cron",             "Self-register scheduled tasks to be prompted at specific times", CapKind.CUSTOM),
]
# fmt: on

CAPABILITY_MAP: dict[str, Capability] = {c.id: c for c in CAPABILITIES}
CAPABILITY_IDS: set[str] = set(CAPABILITY_MAP)


def capability_list() -> list[dict]:
    """Return serialisable list for the REST API."""
    return [
        {"id": c.id, "label": c.label, "description": c.description, "kind": c.kind.value}
        for c in CAPABILITIES
    ]
