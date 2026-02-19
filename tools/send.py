from pydantic_ai import Agent as RunContext
from typing import Annotated, Any
from pydantic import Field
import httpx
import os

async def relay(
    ctx: RunContext[Any], 
    target: Annotated[str, Field(description="The target agent ID to invoke")],
    message: Annotated[str, Field(description="The message to send to the agent")]
) -> str:
    """
    Relays a message to another agent by invoking its API endpoint.
    """
    # Base URL defaults to localhost:8000 if not set
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    url = f"{base_url}/agent/{target}/invoke"
    
    async with httpx.AsyncClient() as client:
        try:
            # Setting a reasonable timeout for inter-agent communication
            response = await client.post(
                url, 
                json={"message": message},
                timeout=30.0 
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return str(data.get("response", data))
                except:
                    return response.text
            else:
                return f"Error ({response.status_code}): {response.text}"
                
        except Exception as e:
            return f"Failed to send message: {str(e)}"

async def reply(
    ctx: RunContext[Any], 
    message: Annotated[str, Field(description="The message to send to the sender")]
) -> str:
    """
    Your reply message will never reach the sender directly.
    Use this tool to send messages back to the sender if you need.
    """
    print(f"[Tool: Reply] {message} (Sender: {ctx.deps.sender if hasattr(ctx.deps, 'sender') else 'Unknown'})")
    return "Message sent."
