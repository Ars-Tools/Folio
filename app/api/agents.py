#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from pydantic_ai import Agent, RunContext
from pydantic_ai import (
    Agent,
    ApprovalRequired,
    DeferredToolRequests,
    DeferredToolResults,
    RunContext,
    ToolDenied,
)
from pathlib import Path
import tomllib
import uuid
import jwt

from ..core.agent import _agent
from ..schema.agent import Invoke
from ..core.auth import get_current_sender, SECRET_KEY, ALGORITHM
from ..schema.session import Sender, Session, Category

agents: dict[str, Agent] = {}
agents_dir = Path(__file__).parent.parent.parent / "agents"

if not agents_dir.exists():
    raise FileNotFoundError(f"Agents directory not found: {agents_dir}")

for agent_dir in agents_dir.iterdir():
    toml_path = agent_dir / "contract.toml"
    if not toml_path.exists():
        continue
    with open(toml_path, "rb") as f:
        agents[agent_dir.name] = _agent(tomllib.load(f))

router = APIRouter()
# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.get("/agents", dependencies=[Depends(get_current_sender)])
async def get_available_agents():
    return {"agents": list(agents.keys()) + ['master']}

@router.post("/agent/{agent_id}/invoke")
async def invoke_agent(
    agent_id: str, 
    invoke: Invoke,
    current_sender: Sender = Depends(get_current_sender)
):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create PydanticAI dependencies object (Session)
    session_instance = Session(
        id=str(uuid.uuid4()), 
        sender=current_sender
    )
    result = await agents[agent_id].run(invoke.task, deps=session_instance)
    if result.output is None:
        raise HTTPException(status_code=500, detail="Agent did not return any output")
    elif isinstance(result.output, DeferredToolRequests):
        raise HTTPException(status_code=403, detail="Agent requires approval to execute this task")

    messages = result.all_messages()
    assert isinstance(result.output, DeferredToolRequests)
    requests = result.output
    print(requests)
    # Here you would typically enqueue the task for the agent to process
    # For now, we just return a placeholder response
    return {"status": "accepted", "message": "Task has been queued for processing."}

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
    
    try:
        while True:
            data = await websocket.receive_text()
            async with agent.run_stream(data, deps=session_instance) as result:
                async for chunk in result.stream():
                    await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass


