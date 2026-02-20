#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent API — all agents loaded from DB, chat via WebSocket."""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, status
from fastapi.responses import Response
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelRequest, ModelResponse
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select
from typing import Optional
from datetime import datetime, timezone
import json
import uuid
import base64
from pathlib import Path

from ..core.agent import build_agent
from ..core.auth import get_current_sender, get_session, authenticate_websocket
from ..core.capabilities import capability_list
from ..core.db import get_db, engine
from ..models.session import Sender, Session, Category
from ..models.agent import Agent as AgentRow
from ..models.provider import Provider
from ..models.chat import Chat
from ..models.equip import Equip
from ..models.skill import Skill

router = APIRouter()

# ---------------------------------------------------------------------------
# Capability tags
# ---------------------------------------------------------------------------

@router.get("/capabilities", dependencies=[Depends(get_current_sender)])
async def list_capabilities():
    return {"capabilities": capability_list()}


# ---------------------------------------------------------------------------
# In-memory cache of pydantic-ai Agent instances (populated at startup)
# ---------------------------------------------------------------------------
_agents: dict[str, PydanticAgent] = {}
_agent_errors: dict[str, str] = {}  # agent_id -> error message


def load_agents():
    """Load all agents from DB and build pydantic-ai instances. Call at startup."""
    with DBSession(engine) as db:
        rows = db.exec(select(AgentRow)).all()
        for row in rows:
            provider = db.get(Provider, row.provider)
            if not provider:
                _agent_errors[row.id] = f"Provider '{row.provider}' not found"
                continue
            try:
                _agents[row.id] = build_agent(row, provider, db)
                _agent_errors.pop(row.id, None)
            except Exception as e:
                _agent_errors[row.id] = str(e)


def reload_agent(agent_id: str):
    """Rebuild a single agent from DB."""
    with DBSession(engine) as db:
        row = db.get(AgentRow, agent_id)
        if not row:
            _agents.pop(agent_id, None)
            _agent_errors.pop(agent_id, None)
            return
        provider = db.get(Provider, row.provider)
        if not provider:
            _agent_errors[agent_id] = f"Provider '{row.provider}' not found"
            _agents.pop(agent_id, None)
            return
        try:
            _agents[agent_id] = build_agent(row, provider, db)
            _agent_errors.pop(agent_id, None)
        except Exception as e:
            _agent_errors[agent_id] = str(e)
            _agents.pop(agent_id, None)


def _get_agent(agent_id: str) -> PydanticAgent:
    """Get agent from cache, building on-the-fly from DB if missing."""
    if agent_id in _agents:
        return _agents[agent_id]
    # Try building from DB
    with DBSession(engine) as db:
        row = db.get(AgentRow, agent_id)
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        provider = db.get(Provider, row.provider)
        if not provider:
            raise HTTPException(status_code=400, detail="Agent provider not found")
        agent = build_agent(row, provider, db)
        _agents[agent_id] = agent
        return agent


# -----------------------------------------------------------------------------
# Agent list & detail
# -----------------------------------------------------------------------------

@router.get("/agents", dependencies=[Depends(get_current_sender)])
async def get_available_agents(db: DBSession = Depends(get_db)):
    rows = db.exec(select(AgentRow)).all()
    return {"agents": [{
        "id": r.id,
        "name": r.name,
        "initial": r.id[0].upper(),
        "hasAvatar": bool(r.avatar),
        "status": "error" if r.id in _agent_errors else "active" if r.id in _agents else "inactive",
        "error": _agent_errors.get(r.id, ""),
    } for r in rows]}


_AGENT_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "Agent.md"


def _load_prompt_template(agent_id: str, agent_name: str) -> str:
    """Load Agent.md template and interpolate placeholders."""
    if _AGENT_TEMPLATE.exists():
        text = _AGENT_TEMPLATE.read_text(encoding="utf-8")
        return text.replace("{{ID}}", agent_id).replace("{{NAME}}", agent_name)
    return ""


class AgentCreate(BaseModel):
    id: str


@router.post("/agents", dependencies=[Depends(get_current_sender)])
async def create_agent(body: AgentCreate, db: DBSession = Depends(get_db)):
    if db.get(AgentRow, body.id):
        raise HTTPException(status_code=409, detail="Agent already exists")
    # Require at least one provider
    provider = db.exec(select(Provider)).first()
    if not provider:
        raise HTTPException(status_code=400, detail="No provider available")
    agent_name = body.id.capitalize()
    row = AgentRow(
        id=body.id,
        provider=provider.id,
        model="apple-on-device",
        name=agent_name,
        prompt=_load_prompt_template(body.id, agent_name),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # Build and cache (non-fatal if provider is unreachable)
    try:
        reload_agent(body.id)
    except Exception:
        pass
    return {"status": "ok", "id": row.id}


@router.get("/agent/{agent_id}", dependencies=[Depends(get_current_sender)])
async def get_agent_detail(agent_id: str, db: DBSession = Depends(get_db)):
    row = db.get(AgentRow, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "id": row.id,
        "name": row.name,
        "provider": row.provider,
        "model": row.model,
        "prompt": row.prompt,
        "avatar": bool(row.avatar),
        "capabilities": json.loads(row.capabilities),
        "params": json.loads(row.model_params),
        "concurrency": row.concurrency,
    }


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    capabilities: Optional[list[str]] = None
    params: Optional[dict] = None
    concurrency: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None


@router.put("/agent/{agent_id}", dependencies=[Depends(get_current_sender)])
async def update_agent(agent_id: str, body: AgentUpdate, db: DBSession = Depends(get_db)):
    row = db.get(AgentRow, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    if body.name is not None:
        row.name = body.name
    if body.prompt is not None:
        row.prompt = body.prompt
    if body.capabilities is not None:
        row.capabilities = json.dumps(body.capabilities)
    if body.params is not None:
        row.model_params = json.dumps(body.params)
    if body.concurrency is not None:
        row.concurrency = body.concurrency
    if body.provider is not None:
        row.provider = body.provider
    if body.model is not None:
        row.model = body.model
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    # Rebuild cached pydantic-ai agent
    reload_agent(agent_id)
    return {"status": "ok"}


@router.delete("/agent/{agent_id}", dependencies=[Depends(get_current_sender)])
async def delete_agent(agent_id: str, db: DBSession = Depends(get_db)):
    row = db.get(AgentRow, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    # Remove from cache
    _agents.pop(agent_id, None)
    _agent_errors.pop(agent_id, None)
    # Delete related equips
    for eq in db.exec(select(Equip).where(Equip.agent == agent_id)).all():
        db.delete(eq)
    # Delete related chats
    for ch in db.exec(select(Chat).where(Chat.agent == agent_id)).all():
        db.delete(ch)
    db.delete(row)
    db.commit()
    return {"status": "ok"}


@router.get("/agent/{agent_id}/avatar")
async def get_agent_avatar(agent_id: str, db: DBSession = Depends(get_db)):
    row = db.get(AgentRow, agent_id)
    if not row or not row.avatar:
        raise HTTPException(status_code=404, detail="No avatar")
    # Handle base64 data URI: data:image/png;base64,iVBOR...
    if row.avatar.startswith("data:"):
        header, b64data = row.avatar.split(",", 1)
        media_type = header.split(":")[1].split(";")[0]
        return Response(content=base64.b64decode(b64data), media_type=media_type)
    # Legacy: raw SVG string
    return Response(content=row.avatar, media_type="image/svg+xml")


@router.put("/agent/{agent_id}/avatar", dependencies=[Depends(get_current_sender)])
async def upload_agent_avatar(agent_id: str, file: UploadFile = File(...), db: DBSession = Depends(get_db)):
    row = db.get(AgentRow, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    content = await file.read()
    if len(content) > 512 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 512KB)")
    media_type = file.content_type or "image/png"
    b64 = base64.b64encode(content).decode()
    row.avatar = f"data:{media_type};base64,{b64}"
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    return {"status": "ok"}


@router.delete("/agent/{agent_id}/avatar", dependencies=[Depends(get_current_sender)])
async def delete_agent_avatar(agent_id: str, db: DBSession = Depends(get_db)):
    row = db.get(AgentRow, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    row.avatar = ""
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Equipped skills
# -----------------------------------------------------------------------------

@router.get("/agent/{agent_id}/skills", dependencies=[Depends(get_current_sender)])
async def list_equipped_skills(agent_id: str, db: DBSession = Depends(get_db)):
    row = db.get(AgentRow, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    equips = db.exec(select(Equip).where(Equip.agent == agent_id)).all()
    skills = []
    for eq in equips:
        skill = db.get(Skill, eq.skill)
        skills.append({"id": eq.skill, "exists": skill is not None})
    return {"skills": skills}


class EquipBody(BaseModel):
    skill: str


@router.post("/agent/{agent_id}/skills", dependencies=[Depends(get_current_sender)])
async def equip_skill(agent_id: str, body: EquipBody, db: DBSession = Depends(get_db)):
    if not db.get(AgentRow, agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    if not db.get(Skill, body.skill):
        raise HTTPException(status_code=404, detail="Skill not found")
    existing = db.get(Equip, (body.skill, agent_id))
    if existing:
        raise HTTPException(status_code=409, detail="Skill already equipped")
    eq = Equip(skill=body.skill, agent=agent_id)
    db.add(eq)
    db.commit()
    reload_agent(agent_id)
    return {"status": "ok"}


@router.delete("/agent/{agent_id}/skill/{skill_id}", dependencies=[Depends(get_current_sender)])
async def unequip_skill(agent_id: str, skill_id: str, db: DBSession = Depends(get_db)):
    eq = db.get(Equip, (skill_id, agent_id))
    if not eq:
        raise HTTPException(status_code=404, detail="Equip not found")
    db.delete(eq)
    db.commit()
    reload_agent(agent_id)
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Chat history helpers (SQLite)
# -----------------------------------------------------------------------------

def _load_history(db: DBSession, user_id: str, agent_id: str) -> list[ModelMessage]:
    """Load persisted message history from the DB."""
    row = db.exec(
        select(Chat).where(Chat.user == user_id, Chat.agent == agent_id)
    ).first()
    if not row or row.messages == "[]":
        return []
    return list(ModelMessagesTypeAdapter.validate_json(row.messages))


def _save_history(db: DBSession, user_id: str, agent_id: str, messages: list[ModelMessage]) -> None:
    """Upsert message history into the DB."""
    row = db.exec(
        select(Chat).where(Chat.user == user_id, Chat.agent == agent_id)
    ).first()
    json_bytes = ModelMessagesTypeAdapter.dump_json(messages)
    if row:
        row.messages = json_bytes.decode()
        row.update = datetime.now(timezone.utc)
    else:
        row = Chat(user=user_id, agent=agent_id, messages=json_bytes.decode())
        db.add(row)
    db.commit()


def _extract_display_messages(messages: list[ModelMessage]) -> list[dict]:
    """Convert pydantic-ai ModelMessages to frontend-friendly dicts."""
    out: list[dict] = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            text = msg.user_text_prompt
            if text:
                out.append({
                    "sender": "user",
                    "content": text,
                    "timestamp": msg.timestamp.strftime("%H:%M") if msg.timestamp else "",
                })
        elif isinstance(msg, ModelResponse):
            text = msg.text
            if text:
                out.append({
                    "sender": "agent",
                    "content": text,
                    "timestamp": "",
                })
    return out


@router.get("/agent/{agent_id}/history")
async def get_chat_history(agent_id: str, current_sender: Sender = Depends(get_current_sender), db: DBSession = Depends(get_db)):
    row = db.get(AgentRow, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    history = _load_history(db, current_sender.id, agent_id)
    return {"messages": _extract_display_messages(history)}


@router.delete("/agent/{agent_id}/history")
async def clear_chat_history(agent_id: str, current_sender: Sender = Depends(get_current_sender), db: DBSession = Depends(get_db)):
    row = db.exec(
        select(Chat).where(Chat.user == current_sender.id, Chat.agent == agent_id)
    ).first()
    if row:
        db.delete(row)
        db.commit()
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# WebSocket chat
# -----------------------------------------------------------------------------

@router.websocket("/agent/{agent_id}/chat")
async def websocket_chat(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    sender = await authenticate_websocket(websocket)
    if not sender:
        return

    try:
        agent = _get_agent(agent_id)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    session = Session(id=str(uuid.uuid4()), sender=sender)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                with DBSession(engine) as db:
                    message_history = _load_history(db, sender.id, agent_id)
                async with agent.run_stream(data, deps=session, message_history=message_history) as result:
                    async for chunk in result.stream_text(delta=True):
                        await websocket.send_text(chunk)
                    await websocket.send_text("\x00")
                    with DBSession(engine) as db:
                        _save_history(db, sender.id, agent_id, result.all_messages())
            except Exception as e:
                error_msg = f"[Error] {type(e).__name__}: {e}"
                await websocket.send_text(error_msg)
                await websocket.send_text("\x00")
    except WebSocketDisconnect:
        pass


