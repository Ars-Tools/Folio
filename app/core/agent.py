#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated
from pydantic_ai import Agent, ConcurrencyLimiter, ConcurrencyLimitedModel, RunContext
from pydantic_ai.models import Model
from pydantic_ai.providers import Provider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pydantic_ai.builtin_tools import WebSearchTool, WebFetchTool, CodeExecutionTool, ImageGenerationTool
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

from tools.expr import expr

from ..schema.session import Session
from ..schema.session import Sender

def _model(config: dict[str, any]) -> Model:
    if not u'name' in config:
        raise ValueError("Model name is required in the 'model' table of the TOML config.")
    if not u'endpoint' in config:
        raise ValueError("Model endpoint is required in the 'model' table of the TOML config.")
    if not u'provider' in config:
        raise ValueError("Model provider is required in the 'model' table of the TOML config.")
    return OpenAIChatModel(
        config.get('name'), 
        provider=OpenAIProvider(base_url=config.get('endpoint', ''), api_key=config.get('apikey', ''))
    ) if config.get('provider') in ['openai-completions', 'openai-responses'] else None # Extendable for other providers        
    
def _identity(config: dict[str, any]) -> str:
    identities: [str] = []
    if u'soul' in config:
        with open(config['soul'], 'r') as f:
            identities.append(f.read())
    if u'rule' in config:
        with open(config['rule'], 'r') as f:
            identities.append(f.read())
    if u'user' in config:
        with open(config['user'], 'r') as f:
            identities.append(f.read())
    if u'memory' in config:
        with open(config['memory'], 'r') as f:
            identities.append(f.read())
    return u'\r\n'.join(identities)

def _agent(config: dict[str, any]) -> Agent:
    behavior = config.get('behavior', {})
    return Agent(
        ConcurrencyLimitedModel(_model(config.get('model', {})), limiter=ConcurrencyLimiter(max_running=behavior.get('concurrency', 1), name='pool')) if u'concurreny' in behavior else _model(config.get('model', {})),
        tools=[
            WebSearchTool,
            WebFetchTool,
            CodeExecutionTool, 
            ImageGenerationTool,
            expr,
            duckduckgo_search_tool()
        ],
        deps_type=Session, 
        system_prompt=_identity(config.get('identity', {})),
    )

class Agentt(Agent):
    def __init__(self, toml: any, *args, **kwargs):
        self._home = toml.parent
        self._id = self._home.name
        super().__init__(*args, **kwargs)

if __name__ == '__main__':
    from pydantic import Field
    import asyncio
    import tomllib
    test_toml = """
    [model]
    provider = "openai-completions"
    endpoint = "http://192.168.2.75:1234/v1"
    name = "lfm2.5-1.2b"
    apikey = "sk-lm-waZJK7KG:Ng26SBWHSiPgW5r0thye"
    [behavior]
    concurrency = 4
    """
    
    config = tomllib.loads(test_toml)
    agent = _agent(config)

    # @agent.tool
    # async def reply(ctx: RunContext[Session], message: str):
    #     """
    #     Replies to the user with a message.
    #     """
    #     print(f"[Tool:Reply] {message} (User: {ctx.deps})")
    #     return "Message sent."
    
    # @agent.tool
    # async def relay(
    #     ctx: RunContext[Session], 
    #     message: Annotated[str, Field(description="The message to relay")], 
    #     target: Annotated[str, Field(description="The target to relay the message to")]
    # ):
    #     """
    #     Relays a message to another system component.
    #     """
    #     print(f"[Tool:Relay] {message} (Target: {target})")
    #     return "Message relayed."
    
    # @agent.tool
    # def get_weather(
    #     ctx: RunContext[Session], 
    #     city: Annotated[str, Field(description="The name of the city for which to retrieve the weather.")]
    # ) -> str:
    #     """
    #     Retrieves the current weather for the specified city.

    #     Returns a string containing the weather condition and temperature.
    #     """
    #     # In reality, this would involve calling an external API.
    #     print(f"[Tool Used] get_weather called for {city} by user {ctx.deps}")

    #     # Dummy response
    #     if city in ["東京", "Tokyo"]:
    #         return "Sunny, 25°C"
    #     elif city in ["大阪", "Osaka"]:
    #         return "Cloudy, 22°C"
    #     else:
    #         return "Unknown city"

    async def run_test():
        deps = Session(
            id="test-session",
            sender=Sender(id="user-123", name="Kota", category="user")
        )
        # print("[Question] 明日の東京の天気は？")
        # result = await agent.run("明日の東京の天気は？", deps=deps)
        # print("[Answer]", result.output)


        print("[Question] What your name?")
        result = await agent.run("solve x for x**3 = y", deps=deps)
        print("[Answer]", result.output)
        print("[Answer]", result)

    asyncio.run(run_test())