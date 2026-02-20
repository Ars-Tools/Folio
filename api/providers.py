#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Providers API — CRUD for LLM provider management."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select
from typing import Optional
from datetime import datetime, timezone
import httpx

from core.auth import get_current_sender
from core.db import get_db
from models.provider import Provider

router = APIRouter()


@router.get("/providers", dependencies=[Depends(get_current_sender)])
async def list_providers(db: DBSession = Depends(get_db)):
    rows = db.exec(select(Provider)).all()
    return {"providers": [{
        "id": r.id,
        "name": r.name,
        "kind": r.kind,
        "endpoint": r.endpoint,
        "apikey_masked": r.apikey[:4] + "..." if len(r.apikey) > 4 else "***",
        "update": r.update.isoformat(),
    } for r in rows]}


@router.get("/provider/{provider_id}", dependencies=[Depends(get_current_sender)])
async def get_provider(provider_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Provider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {
        "id": row.id,
        "name": row.name,
        "kind": row.kind,
        "endpoint": row.endpoint,
        "apikey_masked": row.apikey[:4] + "..." if len(row.apikey) > 4 else "***",
        "update": row.update.isoformat(),
    }


class ProviderCreate(BaseModel):
    id: str
    name: str
    kind: str = "openai-responses"
    endpoint: str = ""
    apikey: str = ""


@router.post("/providers", dependencies=[Depends(get_current_sender)])
async def create_provider(data: ProviderCreate, db: DBSession = Depends(get_db)):
    if not data.id.strip():
        raise HTTPException(status_code=400, detail="ID is required")
    if db.get(Provider, data.id):
        raise HTTPException(status_code=409, detail="Provider already exists")
    row = Provider(
        id=data.id.strip(),
        name=data.name.strip() or data.id.strip(),
        kind=data.kind,
        endpoint=data.endpoint,
        apikey=data.apikey,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "id": row.id}


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    endpoint: Optional[str] = None
    apikey: Optional[str] = None


@router.put("/provider/{provider_id}", dependencies=[Depends(get_current_sender)])
async def update_provider(provider_id: str, data: ProviderUpdate, db: DBSession = Depends(get_db)):
    row = db.get(Provider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    if data.name is not None:
        row.name = data.name
    if data.kind is not None:
        row.kind = data.kind
    if data.endpoint is not None:
        row.endpoint = data.endpoint
    if data.apikey is not None:
        row.apikey = data.apikey
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok"}


@router.delete("/provider/{provider_id}", dependencies=[Depends(get_current_sender)])
async def delete_provider(provider_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Provider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    # Cascade deletes all agents (and their children) referencing this provider via FK
    from models.agent import Agent as AgentRow
    from api.agents import evict_agent
    # Evict affected agents from cache
    agents = db.exec(select(AgentRow).where(AgentRow.provider == provider_id)).all()
    for a in agents:
        evict_agent(a.id)
    db.delete(row)
    db.commit()
    return {"status": "ok"}


@router.get("/provider/{provider_id}/models", dependencies=[Depends(get_current_sender)])
async def list_provider_models(provider_id: str, db: DBSession = Depends(get_db)):
    """Proxy to provider's /models endpoint (OpenAI-compatible)."""
    row = db.get(Provider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    if not row.endpoint:
        return {"models": []}
    url = row.endpoint.rstrip("/") + "/models"
    headers = {}
    if row.apikey:
        headers["Authorization"] = f"Bearer {row.apikey}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # OpenAI format: { data: [{ id: "model-name", ... }] }
            models = []
            if isinstance(data, dict) and "data" in data:
                for m in data["data"]:
                    mid = m.get("id", "") if isinstance(m, dict) else str(m)
                    if mid:
                        models.append({"id": mid})
            return {"models": models}
    except Exception:
        return {"models": []}
