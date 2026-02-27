#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scheduler — Vixie-cron-style minute-boundary loop.

Wakes every minute at :00 seconds, scans the crons table, and fires
matching entries by running the target agent with the configured message.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from croniter import croniter
from sqlmodel import Session as DBSession, select

from core.db import engine
from models.cron import Cron
from models.agent import Agent as AgentRow
from models.session import Sender, Session, Category

log = logging.getLogger(__name__)

# Prevent the same cron row from running concurrently
_running: set[int] = set()


# ---------------------------------------------------------------------------
# Schedule evaluation
# ---------------------------------------------------------------------------

def _should_fire(row: Cron, now: datetime) -> bool:
    """Check whether *row* should fire at *now* (truncated to the minute)."""
    cfg: dict = json.loads(row.schedule)
    minute = now.replace(second=0, microsecond=0)
    fired = False

    # cron expression — match current minute
    if "cron" in cfg:
        try:
            fired = fired or croniter.match(cfg["cron"], minute)
        except (ValueError, KeyError):
            log.warning("scheduler: invalid cron expression in cron#%s: %s", row.id, cfg["cron"])

    # explicit time list — any entry <= now that hasn't been fired yet
    if "at" in cfg:
        for t in cfg["at"]:
            try:
                at_dt = datetime.fromisoformat(t).replace(tzinfo=timezone.utc) if "Z" not in t else datetime.fromisoformat(t.replace("Z", "+00:00"))
                at_minute = at_dt.replace(second=0, microsecond=0)
                if at_minute <= minute:
                    fired = True
                    break
            except (ValueError, TypeError):
                log.warning("scheduler: invalid at entry in cron#%s: %s", row.id, t)

    # Guard against re-firing within the same minute
    if fired and row.fired:
        try:
            last = datetime.fromisoformat(row.fired.replace("Z", "+00:00"))
            if last.replace(second=0, microsecond=0) >= minute:
                return False
        except (ValueError, TypeError):
            pass

    return fired


def _after_fire(row: Cron, now: datetime, db: DBSession) -> None:
    """Post-fire bookkeeping: prune consumed `at` entries, update `fired`."""
    cfg: dict = json.loads(row.schedule)
    minute = now.replace(second=0, microsecond=0)

    if "at" in cfg:
        cfg["at"] = [
            t for t in cfg["at"]
            if _parse_at(t) is not None and _parse_at(t).replace(second=0, microsecond=0) > minute  # type: ignore[union-attr]
        ]
        row.schedule = json.dumps(cfg)

        # If no cron and at-list is exhausted → delete the row
        if not cfg["at"] and "cron" not in cfg:
            db.delete(row)
            db.flush()
            db.commit()
            return

    row.fired = now.isoformat()
    row.update = now
    db.add(row)
    db.flush()
    db.commit()


def _parse_at(t: str) -> datetime | None:
    try:
        if "Z" in t:
            return datetime.fromisoformat(t.replace("Z", "+00:00"))
        return datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Fire an agent
# ---------------------------------------------------------------------------

async def _fire(row: Cron) -> None:
    """Run the target agent with row.message."""
    # Import here to avoid circular imports
    from api.agents import _get_agent

    cron_id = row.id
    agent_id = row.agent
    if cron_id in _running:
        log.debug("scheduler: cron#%s already running, skip", cron_id)
        return
    _running.add(cron_id)
    try:
        agent = _get_agent(agent_id)
        with DBSession(engine) as db:
            agent_row = db.get(AgentRow, agent_id)
            agent_name = agent_row.name if agent_row else agent_id
        sender = Sender(id=agent_id, name=agent_name, category=Category.system)
        session = Session(id=str(uuid.uuid4()), sender=sender)
        log.info("scheduler: firing cron#%s → agent '%s': %.60s…", cron_id, agent_id, row.message)
        await agent.run(row.message, deps=session)
    except Exception as exc:
        log.error("scheduler: cron#%s fire error: %s", cron_id, exc)
    finally:
        _running.discard(cron_id)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

_task: asyncio.Task | None = None


async def _scheduler_loop() -> None:
    """Sleep until the next minute boundary, then scan & fire."""
    log.info("scheduler: started")
    while True:
        now = datetime.now(timezone.utc)
        # Sleep until next minute :00
        sleep_sec = 60 - now.second - now.microsecond / 1_000_000
        if sleep_sec < 0.1:
            sleep_sec += 60  # guard against edge-case overshoot
        await asyncio.sleep(sleep_sec)

        now = datetime.now(timezone.utc)
        try:
            with DBSession(engine) as db:
                rows = db.exec(select(Cron)).all()
                for row in rows:
                    if _should_fire(row, now):
                        # Capture values before session closes
                        cron_id = row.id
                        asyncio.create_task(_fire_and_bookkeep(cron_id, now))
        except Exception as exc:
            log.error("scheduler: scan error: %s", exc)


async def _fire_and_bookkeep(cron_id: int, now: datetime) -> None:
    """Fire the cron, then do post-fire bookkeeping in a fresh DB session."""
    with DBSession(engine) as db:
        row = db.get(Cron, cron_id)
        if not row:
            return
        await _fire(row)
        # Re-fetch in case the row was modified during fire
        row = db.get(Cron, cron_id)
        if row:
            _after_fire(row, now, db)


def start_scheduler() -> None:
    """Start the scheduler background task. Call from lifespan startup."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_scheduler_loop())
        log.info("scheduler: background task created")


def stop_scheduler() -> None:
    """Cancel the scheduler. Call from lifespan shutdown."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        _task = None
        log.info("scheduler: stopped")
