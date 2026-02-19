from pydantic_ai import Agent, RunContext
from pydantic_ai.tools import Tool
from typing import Annotated
import os

def _read(
    ctx: RunContext[any], 
    path: Annotated[str, Field(description="The path of the file to read")]
) -> Optional[str]:
    """
    Reads the content of a file at the given path.
    """
    with open(path, 'rb') as f:
        return f.read()

read = Tool(_read, name="read_file", description="Read the content of a file", takes_ctx=True, sequential=True, requires_approval=True)

def write(
    ctx: RunContext[any], 
    path: Annotated[str, Field(description="The path of the file to write to")],
    content: Annotated[bytes, Field(description="The content to write to the file")]
) -> None:
    """
    Writes the given content to a file at the specified path.
    """
    with open(path, 'wb') as f:
        f.write(content)

def mkdir(
    ctx: RunContext[any], 
    path: Annotated[str, Field(description="The path of the directory to create")]
) -> None:
    """
    Creates a directory at the specified path.
    """
    os.makedirs(path, exist_ok=True)

def delete(
    ctx: RunContext[any], 
    path: Annotated[str, Field(description="The path of the file to delete")]
) -> None:
    """
    Deletes the file at the specified path.
    """
    os.remove(path)

def exec(
    ctx: RunContext[any], 
    command: Annotated[str, Field(description="The shell command to execute")]
) -> str:
    """
    Executes a shell command and returns its output.
    """
    result = os.popen(command).read()
    return result