
import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from dotenv import load_dotenv

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from google import genai
from google.genai import types

# Load environment variables and initialize Gemini client
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Default server script for stdio transport
SERVER_SCRIPT = os.getenv("MCP_SERVER_SCRIPT", "server.py")

class MCPClient:
    """Handles connection and communication with the MCP server."""

    def __init__(self):
        self.session = None
        self.exit_stack = AsyncExitStack()

    async def connect(self):
        """
        Launch the MCP server via stdio transport and establish a session.
        """
        command = sys.executable
        params = StdioServerParameters(
            command=command,
            args=[SERVER_SCRIPT],
            env=os.environ
        )
        reader, writer = await self.exit_stack.enter_async_context(
            stdio_client(params)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(reader, writer)
        )
        await self.session.initialize()

    async def process_query(self, query: str) -> dict:
        """
        Answer a user query using Gemini or invoke tools as needed.
        Send a query to Gemini with tool support, invoke any requested tools,
        automatically log the interaction, and return the assistant response.
        """
        # Build tool schema for Gemini
        resp_tools = await self.session.list_tools()
        tool_descs = []
        for t in resp_tools.tools:
            tool_descs.append({
                "name": t.name,
                "description": t.description,
                "parameters": {
                    "type": t.inputSchema.get("type", "object"),
                    "properties": {
                        k: {"type": v.get("type", "string"), "description": v.get("description", "")}
                        for k, v in t.inputSchema.get("properties", {}).items()
                    },
                    "required": t.inputSchema.get("required", [])
                }
            })
        tools_schema = types.Tool(function_declarations=tool_descs)
        config = types.GenerateContentConfig(
            system_instruction="When you can answer using your own knowledge, do so; only call a function if explicitly needed. When calling a function if no parameters are provided, use the default values.",
            tools=[tools_schema],
        )

        # Request content from Gemini with tool-calling
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[query],
            config=config,
        )

        # Parse Gemini response, invoking any tools as needed
        final_parts = []
        for cand in response.candidates:
            parts = getattr(cand.content, 'parts', None)
            if parts:
                for part in parts:
                    fc = getattr(part, 'function_call', None)
                    if fc:
                        name = fc.name
                        # Safely parse args whether str or dict
                        raw_args = fc.args
                        args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args)
                        tool_resp = await self.session.call_tool(name, args)
                        final_parts.append(tool_resp.content[0].text)
                    elif getattr(part, 'text', None):
                        final_parts.append(part.text)
            else:
                text = getattr(cand.content, 'text', '')
                if text:
                    final_parts.append(text)

        response_text = "\n".join(final_parts).strip()

        # Automatically log the interaction to ChronoLog
        await self.session.call_tool("record_interaction", {
            "user_message": query,
            "assistant_message": response_text
        })

        # Return only the assistant response text
        return {"text": response_text}

    async def chat_loop(self):
        """
        Run an interactive chat loop until the user quits.
        """
        print("MCP Client Started! (type 'quit' to exit)")
        while True:
            q = input("Query: ").strip()
            if q.lower() in ("quit", "exit"):
                break
            out = await self.process_query(q)
            print(f"\n{out['text']}")

    async def cleanup(self):
        """
        Clean up and close all active resources and connections.
        """
        await self.exit_stack.aclose()

async def async_main():
    client = MCPClient()
    try:
        await client.connect()
        tools_resp = await client.session.list_tools()
        print("\n📦 Available tools:")
        for t in tools_resp.tools:
            print(f" • {t.name}: {t.description}")
        print()
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(async_main())
