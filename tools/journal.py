#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Memo toolset — lets an agent write, read, pin/unpin, and search memory slots."""
from pydantic_ai import RunContext, FunctionToolset
from pydantic import Field
from typing import Annotated
import httpx

from models.session import Session
from core.auth import create_jwt
from core.config import PORT

memo_tools = FunctionToolset[Session]()


@memo_tools.tool
async def memo_write(
    ctx: RunContext[Session],
    content: Annotated[str, Field(description="The content to store — any text you want to remember.")],
    abstract: Annotated[str, Field(description=(
        "A one-line summary (≤80 chars) that helps you decide whether to open "
        "this memo later. Write it so future-you can quickly judge relevance."
    ))] = "",
) -> str:
    """Create a new memory slot.

Use this when you want to remember something beyond the current conversation —
facts, observations, interim results, or anything you might need later.
The memo is created unpinned; call memo_pin to keep it visible in your context.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)
    payload: dict = {"body": content}
    if abstract:
        payload["abstract"] = abstract

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{PORT}/agent/{sender.id}/memo",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        data = resp.json()
        return f"Memo saved (id={data.get('id', '?')}). Use memo_pin to keep it visible."
    return f"Failed ({resp.status_code}): {resp.text}"


@memo_tools.tool
async def memo_read(
    ctx: RunContext[Session],
    memo_id: Annotated[int, Field(description="The memo id to read (from pinned list or search results)")],
) -> str:
    """Read the full content of a memory slot.

Call this after seeing an abstract in your pinned list or search results.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{PORT}/agent/{sender.id}/memo/{memo_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code != 200:
        return f"Failed ({resp.status_code}): {resp.text}"

    e = resp.json()
    header = f"[{e['id']}] {e['abstract'] or '(no abstract)'}"
    if e["pinned"]:
        header += " 📌"
    return f"{header}\n\n{e['body']}"


@memo_tools.tool
async def memo_rewrite(
    ctx: RunContext[Session],
    memo_id: Annotated[int, Field(description="The memo id to rewrite")],
    content: Annotated[str, Field(description="New content to replace the existing body")] = "",
    abstract: Annotated[str, Field(description="New one-line summary")] = "",
) -> str:
    """Rewrite an existing memory slot — update its content and/or abstract.

Useful for consolidating multiple memos into one, correcting outdated
information, or refining a rough note into something more precise.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)
    payload: dict = {}
    if content:
        payload["body"] = content
    if abstract:
        payload["abstract"] = abstract
    if not payload:
        return "Nothing to update — provide content or abstract."

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"http://localhost:{PORT}/agent/{sender.id}/memo/{memo_id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        return f"Memo {memo_id} rewritten."
    return f"Failed ({resp.status_code}): {resp.text}"


@memo_tools.tool
async def memo_forget(
    ctx: RunContext[Session],
    memo_id: Annotated[int, Field(description="The memo id to delete permanently")],
) -> str:
    """Permanently delete a memory slot. This is irreversible.

Use for temporary working notes you no longer need, or after consolidating
multiple memos into one.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"http://localhost:{PORT}/agent/{sender.id}/memo/{memo_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        return f"Memo {memo_id} forgotten."
    return f"Failed ({resp.status_code}): {resp.text}"


@memo_tools.tool
async def memo_pin(
    ctx: RunContext[Session],
    memo_id: Annotated[int, Field(description="The memo id to pin")],
) -> str:
    """Pin a memory so its abstract is always visible to you at the start of
every conversation.

Pin memories that are currently relevant — things you need to keep in mind
right now. When something becomes second nature or no longer urgent, unpin it.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"http://localhost:{PORT}/agent/{sender.id}/memo/{memo_id}/pin",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        return f"Memo {memo_id} pinned — it will appear in your context from now on."
    return f"Failed ({resp.status_code}): {resp.text}"


@memo_tools.tool
async def memo_unpin(
    ctx: RunContext[Session],
    memo_id: Annotated[int, Field(description="The memo id to unpin")],
) -> str:
    """Unpin a memory — it stays in storage but won't appear in your context
automatically. You can still find it later with memo_search.

Unpin things that have become second nature or are no longer immediately relevant.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"http://localhost:{PORT}/agent/{sender.id}/memo/{memo_id}/unpin",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        return f"Memo {memo_id} unpinned — still in storage, findable via search."
    return f"Failed ({resp.status_code}): {resp.text}"


@memo_tools.tool
async def memo_search(
    ctx: RunContext[Session],
) -> str:
    """List all your memory abstracts — both pinned and unpinned.

Read through the list yourself and decide which entries are relevant
to your current context, then use memo_read to get the full content.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{PORT}/agent/{sender.id}/memo/search",
            params={"q": "", "limit": 200},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code != 200:
        return f"Failed ({resp.status_code}): {resp.text}"

    entries = resp.json().get("entries", [])
    if not entries:
        return "You have no memories stored."

    lines: list[str] = []
    for e in entries:
        pin = " 📌" if e.get("pinned") else ""
        lines.append(f"[{e['id']}]{pin} {e['abstract'] or '(no abstract)'}")
    return "\n".join(lines)
