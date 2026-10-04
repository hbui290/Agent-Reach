# -*- coding: utf-8 -*-
"""
Agent Reach MCP Server — expose doctor/status as MCP tool.

Run: python -m agent_reach.integrations.mcp_server

Agent Reach is an installer + doctor tool. For actual reading/searching,
agents should call upstream tools directly (twitter-cli, yt-dlp, mcporter, etc.).
"""

import asyncio
import json
import sys
import threading

from rich.text import Text

from agent_reach.config import Config
from agent_reach.core import AgentReach
from agent_reach.utils.text import scrub_url_credentials

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


_doctor_lock = threading.Lock()


def _doctor_report(eyes: AgentReach) -> str:
    """Serialize access to shared channel instances used by Doctor."""
    with _doctor_lock:
        return eyes.doctor_report()


def create_server():
    if not HAS_MCP:
        print(
            "MCP not installed. Install: python -m pip install "
            "'agent-reach[mcp] @ "
            "https://github.com/hbui290/Agent-Reach/archive/refs/heads/main.zip'",
            file=sys.stderr,
        )
        sys.exit(1)

    server = Server("agent-reach")
    config = Config(read_only=True)
    eyes = AgentReach(config)

    @server.list_tools()
    async def list_tools():
        return [
            Tool(name="get_status",
                 description="Get Agent Reach status: which channels are installed and active.",
                 inputSchema={"type": "object", "properties": {}}),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        # Raising lets the MCP SDK mark the result isError=True.
        if name != "get_status":
            raise ValueError(f"Unknown tool: {name}")
        try:
            result = await asyncio.to_thread(_doctor_report, eyes)
        except Exception as e:
            raise RuntimeError(f"Error: {scrub_url_credentials(e)}") from None

        if isinstance(result, (dict, list)):
            text = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            # Doctor renders Rich markup for terminals; agents need plain text.
            text = Text.from_markup(str(result)).plain
        return [TextContent(type="text", text=text)]

    return server


async def main():
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
