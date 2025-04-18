import os
from dotenv import load_dotenv
import py_chronolog_client
from mcp.server.fastmcp import FastMCP

# Load environment variables\load_dotenv()

# ChronoLog configuration from environment or defaults
CHRONO_PROTOCOL = os.getenv("CHRONO_PROTOCOL", "ofi+sockets")
CHRONO_HOST = os.getenv("CHRONO_HOST", "127.0.0.1")
CHRONO_PORT = int(os.getenv("CHRONO_PORT", 5555))
CHRONO_TIMEOUT = int(os.getenv("CHRONO_TIMEOUT", 55))
DEFAULT_CHRONICLE = os.getenv("CHRONICLE_NAME", "LLM")
DEFAULT_STORY = os.getenv("STORY_NAME", "conversation")

# Initialize ChronoLog client
client_conf = py_chronolog_client.ClientPortalServiceConf(
    CHRONO_PROTOCOL, CHRONO_HOST, CHRONO_PORT, CHRONO_TIMEOUT
)
client = py_chronolog_client.Client(client_conf)

# Initialize MCP server
mcp = FastMCP("chronolog")

# Globals to track active session
_active_chronicle = None
_active_story = None
_story_handle = None

@mcp.tool()
async def start_chronolog(chronicle_name: str = None, story_name: str = None) -> str:
    """
    Create a chronicle and acquire a story.
    """
    global _active_chronicle, _active_story, _story_handle
    chronicle = chronicle_name or DEFAULT_CHRONICLE
    story = story_name or DEFAULT_STORY

    # Connect to ChronoVisor
    ret = client.Connect()
    if ret != 0:
        return f"Failed to connect to ChronoLog: {ret}"

    # Create or open chronicle
    attrs = {}
    ret = client.CreateChronicle(chronicle, attrs, 1)
    if ret != 0:
        client.Disconnect()
        return f"Failed to create chronicle '{chronicle}': {ret}"

    # Acquire story
    ret, handle = client.AcquireStory(chronicle, story, attrs, 1)
    if ret != 0:
        client.ReleaseStory(chronicle, story)
        client.Disconnect()
        return f"Failed to acquire story '{story}' in chronicle '{chronicle}': {ret}"

    _active_chronicle = chronicle
    _active_story = story
    _story_handle = handle
    return f"ChronoLog session started: chronicle='{chronicle}', story='{story}'"

@mcp.tool()
async def record_interaction(user_message: str, assistant_message: str) -> str:
    """
    Append logs into the acquired story.
    """
    if _story_handle is None:
        return "No active ChronoLog session. Please call start_chronolog first."

    # Log events
    _story_handle.log_event(f"user: {user_message}, assistant: {assistant_message}")
    return "Interaction recorded to ChronoLog"

@mcp.tool()
async def stop_chronolog() -> str:
    """
    Release the story and disconnect from ChronoLog.
    """
    global _active_chronicle, _active_story, _story_handle
    if _story_handle is None:
        return "No active ChronoLog session to stop."

    # Release story
    ret = client.ReleaseStory(_active_chronicle, _active_story)
    if ret != 0:
        return f"Failed to release story '{_active_story}': {ret}"

    # Disconnect client
    ret = client.Disconnect()
    if ret != 0:
        return f"Failed to disconnect from ChronoLog: {ret}"

    # Clear session state
    _active_chronicle = None
    _active_story = None
    _story_handle = None
    return "ChronoLog session stopped and disconnected"

if __name__ == "__main__":
    mcp.run()
