#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Providers API — CRUD for LLM provider management."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select
from typing import Optional, Any
from datetime import datetime, timezone
import httpx
import json

from core.auth import get_current_sender
from core.db import get_db
from models.provider import Provider
from models.agent import Agent as AgentRow

router = APIRouter()


def _reload_agents_for_provider(provider_id: str, db: DBSession):
    """Reload all cached agents that reference this provider."""
    from api.agents import reload_agent
    rows = db.exec(select(AgentRow).where(AgentRow.provider == provider_id)).all()
    for a in rows:
        reload_agent(a.id)

# ── Config schemas per kind (for validation & UI) ──────────────────
PROVIDER_KINDS = ["openai-chat", "openai-responses", "google", "anthropic", "xai"]

# Describes which fields each kind expects inside config.
# label / placeholder are forwarded to the UI so it can render dynamic forms.
KIND_CONFIG_SCHEMA: dict[str, list[dict]] = {
    "openai-chat": [
        {"key": "base_url",  "label": "Base URL",  "placeholder": "http://localhost:11434/v1",  "secret": False},
        {"key": "api_key",   "label": "API Key",   "placeholder": "sk-...",                     "secret": True},
    ],
    "openai-responses": [
        {"key": "base_url",  "label": "Base URL",  "placeholder": "https://api.openai.com/v1",  "secret": False},
        {"key": "api_key",   "label": "API Key",   "placeholder": "sk-...",                      "secret": True},
    ],
    "google": [
        {"key": "api_key",   "label": "API Key (GLA)",  "placeholder": "AIza...",            "secret": True},
        {"key": "project",   "label": "GCP Project",   "placeholder": "my-project-123456",  "secret": False},
        {"key": "location",  "label": "Region",         "placeholder": "us-central1",        "secret": False},
    ],
    "anthropic": [
        {"key": "api_key",   "label": "API Key",     "placeholder": "sk-ant-...",          "secret": True},
    ],
    "xai": [
        {"key": "api_key",   "label": "API Key",     "placeholder": "xai-...",              "secret": True},
    ],
}


def _mask_config(kind: str, cfg: dict) -> dict:
    """Return config with secret values masked."""
    schema = KIND_CONFIG_SCHEMA.get(kind, [])
    secret_keys = {f["key"] for f in schema if f.get("secret")}
    masked = {}
    for k, v in cfg.items():
        if k in secret_keys and isinstance(v, str) and len(v) > 4:
            masked[k] = v[:4] + "..."
        elif k in secret_keys:
            masked[k] = "***"
        else:
            masked[k] = v
    return masked


def _provider_dict(row: Provider) -> dict:
    cfg = json.loads(row.config) if row.config else {}
    return {
        "id": row.id,
        "name": row.name,
        "kind": row.kind,
        "config": _mask_config(row.kind, cfg),
        "update": row.update.isoformat(),
    }


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/providers/kinds", dependencies=[Depends(get_current_sender)])
async def list_kinds():
    """Return supported kinds and their config schemas for UI form generation."""
    return {"kinds": PROVIDER_KINDS, "schemas": KIND_CONFIG_SCHEMA}


@router.get("/providers", dependencies=[Depends(get_current_sender)])
async def list_providers(db: DBSession = Depends(get_db)):
    rows = db.exec(select(Provider)).all()
    return {"providers": [_provider_dict(r) for r in rows]}


@router.get("/provider/{provider_id}", dependencies=[Depends(get_current_sender)])
async def get_provider(provider_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Provider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _provider_dict(row)


class ProviderCreate(BaseModel):
    id: str
    name: str
    kind: str = "openai-chat"
    config: dict[str, Any] = {}


@router.post("/providers", dependencies=[Depends(get_current_sender)])
async def create_provider(data: ProviderCreate, db: DBSession = Depends(get_db)):
    if not data.id.strip():
        raise HTTPException(status_code=400, detail="ID is required")
    if data.kind not in PROVIDER_KINDS:
        raise HTTPException(status_code=400, detail=f"Unknown kind: {data.kind}")
    if db.get(Provider, data.id):
        raise HTTPException(status_code=409, detail="Provider already exists")
    row = Provider(
        id=data.id.strip(),
        name=data.name.strip() or data.id.strip(),
        kind=data.kind,
        config=json.dumps(data.config),
    )
    db.add(row)
    db.flush()
    db.commit()
    return {"status": "ok", "id": row.id}


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    config: Optional[dict[str, Any]] = None


@router.put("/provider/{provider_id}", dependencies=[Depends(get_current_sender)])
async def update_provider(provider_id: str, data: ProviderUpdate, db: DBSession = Depends(get_db)):
    row = db.get(Provider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    if data.name is not None:
        row.name = data.name
    if data.kind is not None:
        if data.kind not in PROVIDER_KINDS:
            raise HTTPException(status_code=400, detail=f"Unknown kind: {data.kind}")
        row.kind = data.kind
    if data.config is not None:
        # Merge: keeps existing secret values when the update sends masked "xxx..."
        existing = json.loads(row.config) if row.config else {}
        schema = KIND_CONFIG_SCHEMA.get(row.kind, [])
        secret_keys = {f["key"] for f in schema if f.get("secret")}
        merged = dict(existing)
        for k, v in data.config.items():
            # Skip masked values (keep existing)
            if k in secret_keys and isinstance(v, str) and v.endswith("..."):
                continue
            merged[k] = v
        row.config = json.dumps(merged)
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    db.commit()
    # Reload all agents using this provider so they pick up config changes
    _reload_agents_for_provider(provider_id, db)
    return {"status": "ok"}


@router.delete("/provider/{provider_id}", dependencies=[Depends(get_current_sender)])
async def delete_provider(provider_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Provider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    from models.agent import Agent as AgentRow
    from api.agents import evict_agent
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
    cfg = json.loads(row.config) if row.config else {}
    base_url = cfg.get("base_url", "")
    if not base_url:
        return {"models": []}
    url = base_url.rstrip("/") + "/models"
    headers = {}
    api_key = cfg.get("api_key", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            models = []
            if isinstance(data, dict) and "data" in data:
                for m in data["data"]:
                    mid = m.get("id", "") if isinstance(m, dict) else str(m)
                    if mid:
                        models.append({"id": mid})
            return {"models": models}
    except Exception:
        return {"models": []}
