#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cron toolset — lets an agent self-register scheduled tasks.

Provides tools to create, list, and delete cron entries so the agent
can autonomously decide "I need to be prompted at time X" or
"I want a recurring check every morning".
"""
from pydantic_ai import RunContext, FunctionToolset
from pydantic import Field
from typing import Annotated
import httpx

from models.session import Session
from core.auth import create_jwt
from core.config import PORT

cron_tools = FunctionToolset[Session]()


@cron_tools.tool
async def schedule_task(
    ctx: RunContext[Session],
    message: Annotated[str, Field(description="The prompt that will be sent to you when the schedule fires.")],
    name: Annotated[str, Field(description="Short human-readable label for this schedule (e.g. 'Morning briefing')")] = "",
    cron: Annotated[str, Field(description=(
        "Cron expression for recurring schedule (5 fields: min hour dom month dow). "
        "Examples: '0 9 * * *' = every day 09:00 UTC, '*/30 * * * *' = every 30 min, "
        "'0 9 * * 1' = every Monday 09:00 UTC. "
        "Leave empty if using 'at' instead."
    ))] = "",
    at: Annotated[str, Field(description=(
        "Comma-separated ISO-8601 UTC timestamps for one-shot or specific-time firing. "
        "Examples: '2026-03-01T09:00:00Z' or '2026-03-01T09:00:00Z,2026-04-01T09:00:00Z'. "
        "Leave empty if using 'cron' instead. Can be combined with cron."
    ))] = "",
) -> str:
    """Register a scheduled task that will prompt you at specified times.

Use this when:
- You realise you need to check on something later (schedule a one-shot).
- You want a recurring prompt (e.g. daily summary, periodic check).
- Someone asks you to do something at a future time.

You must provide at least one of 'cron' or 'at'. Both can be set together.
All times are in UTC.
    """
    schedule: dict = {}
    if cron.strip():
        schedule["cron"] = cron.strip()
    if at.strip():
        schedule["at"] = [t.strip() for t in at.split(",") if t.strip()]
    if not schedule:
        return "Error: must provide at least one of 'cron' or 'at'."

    sender = ctx.deps.sender
    token = create_jwt(sender)
    base = f"http://localhost:{PORT}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/agent/{sender.id}/crons",
            json={"name": name, "schedule": schedule, "message": message},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        data = resp.json()
        parts = []
        if "cron" in schedule:
            parts.append(f"cron='{schedule['cron']}'")
        if "at" in schedule:
            parts.append(f"at={schedule['at']}")
        return f"Scheduled task created (id={data.get('id', '?')}, {', '.join(parts)})"
    return f"Failed to create schedule ({resp.status_code}): {resp.text}"


@cron_tools.tool
async def list_schedules(
    ctx: RunContext[Session],
) -> str:
    """List all your scheduled tasks.

Returns id, name, schedule, and last-fired time for each task.
Use this to check what you already have scheduled before creating duplicates.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)
    base = f"http://localhost:{PORT}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{base}/agent/{sender.id}/crons",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code != 200:
        return f"Failed to list schedules ({resp.status_code}): {resp.text}"

    crons = resp.json().get("crons", [])
    if not crons:
        return "No scheduled tasks."

    lines: list[str] = []
    for c in crons:
        sched = c["schedule"]
        parts = []
        if "cron" in sched:
            parts.append(f"cron='{sched['cron']}'")
        if "at" in sched:
            parts.append(f"at={sched['at']}")
        fired = f", last fired: {c['fired']}" if c.get("fired") else ""
        name = f" ({c['name']})" if c.get("name") else ""
        lines.append(f"- [{c['id']}]{name} {', '.join(parts)}{fired} → {c['message'][:80]}")
    return "\n".join(lines)


@cron_tools.tool
async def delete_schedule(
    ctx: RunContext[Session],
    schedule_id: Annotated[int, Field(description="The id of the scheduled task to delete (from list_schedules)")],
) -> str:
    """Delete a scheduled task by its id.

Use this when:
- A one-shot task is no longer needed.
- You want to stop a recurring schedule.
- You're replacing an old schedule with a new one.
    """
    sender = ctx.deps.sender
    token = create_jwt(sender)
    base = f"http://localhost:{PORT}"

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{base}/cron/{schedule_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    if resp.status_code == 200:
        return f"Schedule {schedule_id} deleted."
    return f"Failed to delete schedule ({resp.status_code}): {resp.text}"
