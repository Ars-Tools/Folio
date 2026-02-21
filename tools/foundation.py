#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Foundation tools — core utilities available to every Folio agent."""
from pydantic_ai import RunContext, FunctionToolset
from pydantic import Field
from typing import Annotated
import httpx

from models.session import Session
from core.auth import create_jwt
from core.config import PORT

foundation_tools = FunctionToolset[Session]()


@foundation_tools.tool
async def resolve_identity(
    ctx: RunContext[Session],
    sender_id: Annotated[str, Field(description="The sender ID (user token or agent ID) to look up")],
    category: Annotated[str, Field(description="The sender category: 'user', 'node', 'service', or 'agent'")] = "user",
) -> str:
    """Look up a sender's profile by their ID when you need more context than the message header provides. Only call this when you genuinely need to learn about an unfamiliar sender — the message header already tells you the sender's name and role."""
    me = ctx.deps.sender

    # Self-reference
    if sender_id == me.id:
        return "myself"

    token = create_jwt(me)
    base = f"http://localhost:{PORT}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/identity/resolve",
            json={"id": sender_id, "category": category},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 404:
        return f"Unknown sender: {sender_id} (category={category})"
    if resp.status_code != 200:
        return f"Failed to resolve identity ({resp.status_code}): {resp.text}"

    data = resp.json()
    return f"name: {data['name']}\nprofile: {data['profile'] or '(none)'}"
