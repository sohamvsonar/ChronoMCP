import os
from dotenv import load_dotenv
import py_chronolog_client
from mcp.server.fastmcp import FastMCP
import subprocess
import re

# Load environment variables\load_dotenv()

# ChronoLog configuration from environment or defaults
CHRONO_PROTOCOL = os.getenv("CHRONO_PROTOCOL", "ofi+sockets")
CHRONO_HOST = os.getenv("CHRONO_HOST", "127.0.0.1")
CHRONO_PORT = int(os.getenv("CHRONO_PORT", 5555))
CHRONO_TIMEOUT = int(os.getenv("CHRONO_TIMEOUT", 55))
DEFAULT_CHRONICLE = os.getenv("CHRONICLE_NAME", "LLM")
DEFAULT_STORY = os.getenv("STORY_NAME", "conversation")

HDF5_READER_BIN = os.getenv("HDF5_READER_BIN", "/home/ssonar/chronolog/Debug/test_1/build/hdf5_file_reader")
CONF_FILE       = os.getenv("CHRONO_CONF",     "/home/ssonar/chronolog/Debug/conf/grapher_conf_1.json")

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

@mcp.tool()
async def retrieve_interaction(
    chronicle_name: str = None,
    story_name:     str = None,
    start:          int = None,
    end:            int = None
) -> str:
    """
    Run the C++ HDF5 reader and return its output.
    """
    # Determine parameters
    chronicle = chronicle_name or "LLM"
    story     = story_name     or "conversation"
    #HDF5_READER_BIN = os.getenv("HDF5_READER_BIN", "/home/ssonar/chronolog/Debug/test_1/build/hdf5_file_reader")

    # Build command
    cmd = [HDF5_READER_BIN, "-c", CONF_FILE, "-C", chronicle, "-S", story]
    if start is not None:
        cmd += ["-st", str(start)]
    if end is not None:
        cmd += ["-et", str(end)]

    try:
        # Run the reader
        proc = subprocess.run(
            cmd,
            cwd=os.path.dirname(HDF5_READER_BIN),
            capture_output=True,
            text=True,
            #check=True
            encoding="utf-8",
            errors="replace",
        )
        return proc.stdout
    except subprocess.CalledProcessError as e:
        return f"Error running hdf5 reader: {e.stderr or e.stdout}"


if __name__ == "__main__":
    mcp.run()