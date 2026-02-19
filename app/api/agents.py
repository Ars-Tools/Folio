#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelRequest, ModelResponse
from pydantic import BaseModel
from pathlib import Path
from collections import defaultdict
import tomllib
import uuid
import jwt
import json

from ..core.agent import _agent
from ..core.auth import get_current_sender, SECRET_KEY, ALGORITHM
from ..schema.session import Sender, Session, Category

agents: dict[str, Agent] = {}
agents_config: dict[str, dict] = {}
agents_dir = Path(__file__).parent.parent.parent / "agents"

# In-memory chat history: key = (user_id, agent_id) → list[ModelMessage]
chat_histories: dict[tuple[str, str], list[ModelMessage]] = defaultdict(list)

if not agents_dir.exists():
    raise FileNotFoundError(f"Agents directory not found: {agents_dir}")

for agent_dir in agents_dir.iterdir():
    toml_path = agent_dir / "contract.toml"
    if not toml_path.exists():
        continue
    with open(toml_path, "rb") as f:
        config = tomllib.load(f)
        agents[agent_dir.name] = _agent(config)
        agents_config[agent_dir.name] = config

router = APIRouter()
# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.get("/agents", dependencies=[Depends(get_current_sender)])
async def get_available_agents():
    result = []
    for agent_id, config in agents_config.items():
        avatar_file = config.get("behavior", {}).get("avatar", None)
        has_avatar = False
        if avatar_file:
            avatar_path = agents_dir / agent_id / avatar_file
            has_avatar = avatar_path.exists()
        display_name = config.get("identity", {}).get("name", agent_id.capitalize())
        result.append({
            "id": agent_id,
            "name": display_name,
            "initial": agent_id[0].upper(),
            "hasAvatar": has_avatar,
        })
    return {"agents": result}

@router.get("/agent/{agent_id}/avatar")
async def get_agent_avatar(agent_id: str):
    from fastapi.responses import FileResponse as FR
    if agent_id not in agents_config:
        raise HTTPException(status_code=404, detail="Agent not found")
    avatar_file = agents_config[agent_id].get("behavior", {}).get("avatar", None)
    if not avatar_file:
        raise HTTPException(status_code=404, detail="No avatar configured")
    avatar_path = agents_dir / agent_id / avatar_file
    if not avatar_path.exists():
        raise HTTPException(status_code=404, detail="Avatar file not found")
    media_type = "image/svg+xml" if avatar_file.endswith(".svg") else None
    return FR(str(avatar_path), media_type=media_type)

@router.get("/agent/{agent_id}/files", dependencies=[Depends(get_current_sender)])
async def get_agent_files(agent_id: str):
    """List markdown files for an agent."""
    if agent_id not in agents_config:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_path = agents_dir / agent_id
    md_files = sorted([f.name for f in agent_path.glob("*.md")])
    return {"files": md_files}

@router.get("/agent/{agent_id}/file/{filename}", dependencies=[Depends(get_current_sender)])
async def get_agent_file(agent_id: str, filename: str):
    """Read a markdown file for an agent."""
    if agent_id not in agents_config:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are supported")
    file_path = agents_dir / agent_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"filename": filename, "content": file_path.read_text(encoding="utf-8")}

class FileContent(BaseModel):
    content: str

@router.put("/agent/{agent_id}/file/{filename}", dependencies=[Depends(get_current_sender)])
async def update_agent_file(agent_id: str, filename: str, body: FileContent):
    """Write a markdown file for an agent."""
    if agent_id not in agents_config:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are supported")
    file_path = agents_dir / agent_id / filename
    file_path.write_text(body.content, encoding="utf-8")
    return {"status": "ok"}

@router.post("/agent/{agent_id}/reload", dependencies=[Depends(get_current_sender)])
async def reload_agent(agent_id: str):
    """Reload an agent's configuration."""
    if agent_id not in agents_config:
        raise HTTPException(status_code=404, detail="Agent not found")
    # TODO: re-read contract.toml and rebuild agent
    return {"status": "ok"}

# -----------------------------------------------------------------------------
# Chat history
# -----------------------------------------------------------------------------

def _extract_display_messages(messages: list[ModelMessage]) -> list[dict]:
    """Convert pydantic-ai ModelMessages to simple {sender, content, timestamp} dicts for the frontend."""
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
async def get_chat_history(agent_id: str, current_sender: Sender = Depends(get_current_sender)):
    """Return chat history for the current user + agent."""
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    key = (current_sender.id, agent_id)
    history = chat_histories.get(key, [])
    return {"messages": _extract_display_messages(history)}

@router.delete("/agent/{agent_id}/history")
async def clear_chat_history(agent_id: str, current_sender: Sender = Depends(get_current_sender)):
    """Clear chat history for the current user + agent."""
    key = (current_sender.id, agent_id)
    chat_histories.pop(key, None)
    return {"status": "ok"}

@router.websocket("/agent/{agent_id}/chat")
async def websocket_chat(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
             await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
             return
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if agent_id not in agents:
         await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
         return

    agent = agents[agent_id]
    sender = Sender(id=user_id, name=user_id, category=Category.user)
    session_instance = Session(id=str(uuid.uuid4()), sender=sender)
    history_key = (user_id, agent_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_history = chat_histories.get(history_key, [])
                async with agent.run_stream(data, deps=session_instance, message_history=message_history) as result:
                    async for chunk in result.stream_text(delta=True):
                        await websocket.send_text(chunk)
                    await websocket.send_text("\x00")  # end-of-stream signal
                    # Store the full conversation history
                    chat_histories[history_key] = result.all_messages()
            except Exception as e:
                error_msg = f"[Error] {type(e).__name__}: {e}"
                await websocket.send_text(error_msg)
                await websocket.send_text("\x00")
    except WebSocketDisconnect:
        pass


