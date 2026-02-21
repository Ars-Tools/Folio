#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Timeline API — cursor-based paginated feed with WebSocket pub/sub.

Broadcast is completely uniform.  Every subscriber — human or agent —
receives the same events through the same queue.  This module has no
knowledge of subscriber types.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
    ModelMessagesTypeAdapter,
)
from sqlmodel import Session as DBSession, select, col
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import json
import logging

from core.auth import get_current_sender, authenticate_websocket
from core.db import get_db
from models.post import Post
from models.session import Sender

router = APIRouter()
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subscriber registry
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class Subscriber:
    ws: Optional[WebSocket]
    sender: Sender
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=256))


_subscribers: set[Subscriber] = set()


def _broadcast(event: dict) -> None:
    """Put *event* into every subscriber's queue."""
    for sub in _subscribers:
        try:
            sub.queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("timeline: dropping event for slow subscriber %s", sub.sender.id)


def subscribe(sender: Sender, ws: Optional[WebSocket] = None) -> Subscriber:
    """Add a subscriber and return it.  Works for any sender type."""
    sub = Subscriber(ws=ws, sender=sender)
    _subscribers.add(sub)
    log.info("timeline: subscribed %s", sender.id)
    return sub


def unsubscribe(sub: Subscriber) -> None:
    _subscribers.discard(sub)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_dict(p: Post) -> dict:
    return {
        "id": p.id,
        "sender": p.sender,
        "author": p.author,
        "category": p.category,
        "body": p.body,
        "update": p.update.isoformat() + "Z",
    }


def posts_to_message_history(posts: list[Post], sender: str) -> list[ModelMessage]:
    """Convert timeline posts into pydantic-ai message_history for *sender*."""
    messages: list[ModelMessage] = []
    for post in posts:
        if post.sender == sender:
            messages.append(ModelResponse(parts=[TextPart(content=post.body)]))
        else:
            label = f"[{post.author} ({post.category}:{post.sender})] " if post.author else ""
            messages.append(
                ModelRequest(parts=[UserPromptPart(content=f"{label}{post.body}")])
            )
    return messages


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/timeline", dependencies=[Depends(get_current_sender)])
async def list_posts(
    cursor: Optional[int] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: DBSession = Depends(get_db),
):
    stmt = select(Post).order_by(col(Post.id).desc()).limit(limit)
    if cursor is not None:
        stmt = stmt.where(col(Post.id) < cursor)
    rows = db.exec(stmt).all()
    next_cursor = rows[-1].id if rows else None
    return {"posts": [_post_dict(p) for p in rows], "next_cursor": next_cursor}


class PostCreate(BaseModel):
    body: str


@router.post("/timeline")
async def create_post(
    data: PostCreate,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    post = Post(
        sender=sender.id,
        author=sender.name,
        category=sender.category.value,
        body=data.body,
    )
    db.add(post)
    db.flush()   # assigns auto-generated id before commit
    db.commit()
    d = _post_dict(post)
    _broadcast({"type": "new", "post": d})
    return d


@router.get("/timeline/{post_id}", dependencies=[Depends(get_current_sender)])
async def get_post(post_id: int, db: DBSession = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _post_dict(post)


class PostUpdate(BaseModel):
    body: str


@router.put("/timeline/{post_id}")
async def update_post(
    post_id: int,
    data: PostUpdate,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.sender != sender.id:
        raise HTTPException(status_code=403, detail="Not the post owner")
    post.body = data.body
    post.update = datetime.now(timezone.utc)
    db.add(post)
    db.flush()
    db.commit()
    return _post_dict(post)


@router.delete("/timeline/{post_id}")
async def delete_post(
    post_id: int,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.sender != sender.id:
        raise HTTPException(status_code=403, detail="Not the post owner")
    db.delete(post)
    db.commit()
    _broadcast({"type": "delete", "id": post_id})
    return {"status": "ok"}


@router.get("/timeline/history/{sender}", dependencies=[Depends(get_current_sender)])
async def get_timeline_as_history(
    sender: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: DBSession = Depends(get_db),
):
    stmt = select(Post).order_by(col(Post.id).desc()).limit(limit)
    rows = list(reversed(db.exec(stmt).all()))
    messages = posts_to_message_history(rows, sender)
    raw = ModelMessagesTypeAdapter.dump_json(messages).decode()
    return {"sender": sender, "count": len(messages), "messages": raw}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@router.websocket("/timeline/ws")
async def timeline_ws(websocket: WebSocket):
    await websocket.accept()
    sender = await authenticate_websocket(websocket)
    if not sender:
        return

    sub = subscribe(sender, ws=websocket)

    async def _drain() -> None:
        while True:
            event = await sub.queue.get()
            await sub.ws.send_text(json.dumps(event))

    task = asyncio.create_task(_drain())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        unsubscribe(sub)