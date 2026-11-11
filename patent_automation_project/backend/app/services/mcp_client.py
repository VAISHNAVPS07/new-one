\"\"\"MCP discovery adapter.

This deliberately lists tools before any search call. Tool names and schemas differ
between MCP servers; configure the actual tool only after inspecting this output.
\"\"\"
import json
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.config import settings

def _server_args():
    try:
        value = json.loads(settings.mcp_server_args or "[]")
        return value if isinstance(value, list) else []
    except json.JSONDecodeError as exc:
        raise ValueError("MCP_SERVER_ARGS must be a JSON array") from exc

async def list_mcp_tools() -> list[dict]:
    if not settings.mcp_server_command:
        raise RuntimeError("Configure MCP_SERVER_COMMAND before using MCP")
    params = StdioServerParameters(
        command=settings.mcp_server_command,
        args=_server_args(),
        env=None,
    )
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        result = await session.list_tools()
        return [
            {"name": tool.name, "description": tool.description,
             "inputSchema": tool.inputSchema}
            for tool in result.tools
        ]

async def call_configured_search_tool(query: str) -> dict:
    if not settings.mcp_search_tool:
        raise RuntimeError("Set MCP_SEARCH_TOOL only after inspecting the available tool list")
    template = json.loads(settings.mcp_search_arguments_template or "{}")
    if not isinstance(template, dict):
        raise ValueError("MCP_SEARCH_ARGUMENTS_TEMPLATE must be a JSON object")
    # Convention: replace this placeholder only if it matches your server's schema.
    args = {k: (query if v == "__QUERY__" else v) for k, v in template.items()}
    params = StdioServerParameters(
        command=settings.mcp_server_command, args=_server_args(), env=None
    )
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        result = await session.call_tool(settings.mcp_search_tool, args)
        return {"isError": result.isError, "content": [
            getattr(item, "text", str(item)) for item in result.content
        ]}
