from pydantic_ai import Agent as RunContext
from typing import Annotated
from pydantic import Field
import asyncio

async def gemini(
    ctx: RunContext[any], 
    command: Annotated[str, Field(description="The Gemini CLI command to execute")]
) -> str:
    """
    Executes a Gemini CLI command and returns its output.
    """
    proc = await asyncio.create_subprocess_shell(
        f"gemini {command}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return f"Error: {stderr.decode().strip()}"
    return stdout.decode().strip()

async def codex(
    ctx: RunContext[any], 
    command: Annotated[str, Field(description="The Codex CLI command to execute")]
) -> str:
    """
    Executes a Codex CLI command and returns its output.
    """
    proc = await asyncio.create_subprocess_shell(
        f"codex {command}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return f"Error: {stderr.decode().strip()}"
    return stdout.decode().strip()

async def claude(
    ctx: RunContext[any], 
    command: Annotated[str, Field(description="The Claude CLI command to execute")]
) -> str:
    """
    Executes a Claude CLI command and returns its output.
    """
    proc = await asyncio.create_subprocess_shell(
        f"claude {command}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return f"Error: {stderr.decode().strip()}"
    return stdout.decode().strip()