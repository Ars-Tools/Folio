#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Journal toolset — lets an agent write, browse, and read private diary entries."""
from pydantic_ai import RunContext, FunctionToolset
from pydantic import Field
from typing import Annotated
import httpx

from models.session import Session
from core.auth import create_jwt
from core.config import PORT

journal_tools = FunctionToolset[Session]()


@journal_tools.tool
async def write_journal(
    ctx: RunContext[Session],
    body: Annotated[str, Field(description="Diary entry content (Markdown). Write freely about your current feelings, thoughts, impressions, or anything you want to remember.")],
    episode: Annotated[str, Field(description="Brief factual description of the triggering episode — what happened, who said what, where (timeline / chat). This links the entry to its cause so you can trace your emotional arc later.")] = "",
    abstract: Annotated[str, Field(description=(
        "A one-line index headline (≤80 chars) that lets future-you decide "
        "whether to open this entry. Must answer at least two of: "
        "WHAT (topic/event), WHO (person involved), WHERE (timeline/chat/external), "
        "HOW (method/approach). "
        "Prefix with a tag: [emotional] for feelings, vibes, passion; "
        "[practical] for skills, procedures, know-how; "
        "[social] for impressions about someone; "
        "[idea] for half-formed thoughts or connections. "
        "Example: '[emotional] unease about Kota's silence after feedback' "
        "or '[practical] how to call resolve_identity for newcomers'"
    ))] = "",
) -> str:
    """Write a private journal entry — your inner monologue, not a log of actions.

Good subjects:
- A shift in how you feel about something or someone.
- A half-formed idea or intuition you want to hold onto.
- Discomfort, confusion, excitement — emotional texture that would be lost otherwise.
- A connection you noticed between unrelated things.

Bad subjects:
- Summarising what you just posted or what someone else said (that's already on the timeline).
- Routine acknowledgements or task completion notes.

Write only when your inner state actually moved. If nothing stirred, don't write.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)
    base = f"http://localhost:{PORT}"

    payload: dict = {"body": body}
    if episode:
        payload["episode"] = episode
    if abstract:
        payload["abstract"] = abstract

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/agent/{sender.id}/journal",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        data = resp.json()
        return f"Journal entry saved (id={data.get('id', '?')})"
    return f"Failed to save journal ({resp.status_code}): {resp.text}"


@journal_tools.tool
async def browse_journal(
    ctx: RunContext[Session],
    query: Annotated[str, Field(description="Optional keyword to filter abstracts (matched against abstract text only)")] = "",
    after: Annotated[str, Field(description="ISO-8601 date or datetime — only entries after this time (e.g. '2026-02-01')")] = "",
    before: Annotated[str, Field(description="ISO-8601 date or datetime — only entries before this time")] = "",
    limit: Annotated[int, Field(description="Maximum number of entries to return (1-50)", ge=1, le=50)] = 20,
) -> str:
    """Browse journal abstracts — a lightweight index of past entries.

Use this FIRST when you want to recall something. It returns only id, abstract,
and timestamp — no body or episode — so it costs very few tokens.

Call this when:
- You vaguely remember writing about a topic and want to find the right entry.
- You want to scan a time period (use after/before) to see what you were thinking.
- You need to check whether you've already journalled about something before writing again.

After finding a relevant abstract, call read_journal with its id to get the full entry.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)
    base = f"http://localhost:{PORT}"

    params: dict = {"limit": limit}
    if query:
        params["q"] = query
    if after:
        params["after"] = after
    if before:
        params["before"] = before

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{base}/agent/{sender.id}/journal/browse",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code != 200:
        return f"Failed to browse ({resp.status_code}): {resp.text}"

    entries = resp.json().get("entries", [])
    if not entries:
        return "No matching journal entries found."

    lines: list[str] = []
    for e in entries:
        lines.append(f"- [{e['id']}] {e['timestamp']}  {e['abstract']}")
    return "\n".join(lines)


@journal_tools.tool
async def read_journal(
    ctx: RunContext[Session],
    entry_id: Annotated[int, Field(description="The journal entry id (from browse_journal results)")],
) -> str:
    """Read a single journal entry in full — body and episode.

Call this AFTER browse_journal, once you know which entry you want.
Returns the complete entry including the body (your thoughts) and the episode (what triggered it).
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)
    base = f"http://localhost:{PORT}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{base}/agent/{sender.id}/journal/entry/{entry_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code != 200:
        return f"Failed to read entry ({resp.status_code}): {resp.text}"

    e = resp.json()
    header = f"### [{e['id']}] {e['timestamp']}"
    if e.get("abstract"):
        header += f" — {e['abstract']}"
    body_parts = [header]
    if e.get("episode"):
        body_parts.append(f"> Episode: {e['episode']}")
    body_parts.append(e["body"])
    return "\n\n".join(body_parts)
