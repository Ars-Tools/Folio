from pydantic_ai import Agent as RunContext
from typing import Annotated
from pydantic import Field
import asyncio

async def git(
    ctx: RunContext[any], 
    command: Annotated[str, Field(description="The git command to execute")]
) -> str:
    """
    Executes a git command and returns its output.
    """
    proc = await asyncio.create_subprocess_shell(
        f"git {command}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return f"Error: {stderr.decode().strip()}"
    return stdout.decode().strip()

async def gh(
    ctx: RunContext[any], 
    command: Annotated[str, Field(description="The GitHub CLI command to execute")]
) -> str:
    """
    Executes a GitHub CLI command and returns its output.
    """
    proc = await asyncio.create_subprocess_shell(
        f"gh {command}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return f"Error: {stderr.decode().strip()}"
    return stdout.decode().strip()