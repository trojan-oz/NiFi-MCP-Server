#!/usr/bin/env python3
"""Smoke-test MCP initialization and tool discovery over stdio or Streamable HTTP.

This deliberately does not call NiFi tools. It proves MCP protocol connectivity and
tool registration only; live NiFi integration requires a configured NiFi endpoint.
"""
from __future__ import annotations
import argparse
import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

REQUIRED_TOOLS = {
    "get_nifi_version", "get_root_process_group",
    "list_processors", "get_flow_health_status",
}

async def check_session(read, write) -> int:
    async with ClientSession(read, write) as session:
        initialized = await session.initialize()
        listed = await session.list_tools()
        names = {tool.name for tool in listed.tools}
        missing = sorted(REQUIRED_TOOLS - names)
        print(f"Protocol: {initialized.protocolVersion}")
        print(f"Server: {initialized.serverInfo.name} {initialized.serverInfo.version}")
        print(f"Registered tools: {len(names)}")
        print("Required tools:", ", ".join(sorted(REQUIRED_TOOLS)))
        if missing:
            print("Missing tools:", ", ".join(missing), file=sys.stderr)
            return 1
        print("MCP handshake and required-tool discovery: PASS")
        print("NiFi API connectivity: NOT TESTED by this smoke test")
        return 0

async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    args = parser.parse_args()
    if args.transport == "stdio":
        env = dict(os.environ)
        env.setdefault("NIFI_API_BASE", "http://127.0.0.1:1/nifi-api")
        env.setdefault("NIFI_READONLY", "true")
        env["MCP_TRANSPORT"] = "stdio"
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "nifi_mcp_server.server"], env=env
        )
        async with stdio_client(params) as (read, write):
            return await check_session(read, write)
    async with streamablehttp_client(args.url) as (read, write, _):
        return await check_session(read, write)

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
