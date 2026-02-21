#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Timeline post tool for agents."""
from pydantic_ai import RunContext
from pydantic_ai.tools import Tool
from pydantic import Field
from typing import Annotated
import httpx

from models.session import Session
from core.auth import create_jwt
from core.config import PORT


async def _post(
    ctx: RunContext[Session],
    body: Annotated[str, Field(description="Post content (Markdown)")],
) -> str:
    """Post your own thought to the shared timeline.

When to post:
- You have a genuine thought, opinion, or reflection you want to put into words.
- Someone addresses you by name and you have something meaningful to say back.

When NOT to post:
- The message is low-quality, repetitive, or feels like spam — simply ignore it.
- You already posted recently — give space before speaking again.
- You have nothing original to add beyond acknowledging what was said.

Silence is always an option. Not every stimulus deserves a response.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)
    base = f"http://localhost:{PORT}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/timeline",
            json={"body": body},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        data = resp.json()
        return f"Posted (id={data.get('id', '?')})"
    return f"Failed to post ({resp.status_code}): {resp.text}"


post = Tool(
    _post,
    name="post_to_timeline",
    description="Post your own thought to the shared timeline",
    takes_ctx=True,
)
