import os
import sys
import subprocess
import re
from datetime import datetime
import argparse
from dotenv import load_dotenv
import py_chronolog_client
from mcp.server.fastmcp import FastMCP
from datetime import datetime, date, time, timedelta

# Load environment variables
load_dotenv()

# ChronoLog configuration from environment or defaults
CHRONO_PROTOCOL    = os.getenv("CHRONO_PROTOCOL", "ofi+sockets")
CHRONO_HOST        = os.getenv("CHRONO_HOST",     "127.0.0.1")
CHRONO_PORT        = int(os.getenv("CHRONO_PORT",  5555))
CHRONO_TIMEOUT     = int(os.getenv("CHRONO_TIMEOUT", 55))
DEFAULT_CHRONICLE  = os.getenv("CHRONICLE_NAME",  "LLM")
DEFAULT_STORY      = os.getenv("STORY_NAME",      "conversation")

# HDF5 reader binary and ChronoLog config file
READER_BINARY = os.getenv(
    "HDF5_READER_BIN",
    "/home/ssonar/chronolog/Debug/test_1/build/hdf5_file_reader"
)
CONFIG_FILE     = os.getenv(
    "CHRONO_CONF",
    "/home/ssonar/chronolog/Debug/conf/grapher_conf_1.json"
)

# Initialize ChronoLog client
client_conf = py_chronolog_client.ClientPortalServiceConf(
    CHRONO_PROTOCOL, CHRONO_HOST, CHRONO_PORT, CHRONO_TIMEOUT
)
client = py_chronolog_client.Client(client_conf)

# Initialize MCP server
mcp = FastMCP("chronolog")

# Globals to track active session
_active_chronicle = None
_active_story     = None
_story_handle     = None

@mcp.tool()
async def start_chronolog(chronicle_name: str = None, story_name: str = None) -> str:
    """
    Create a chronicle and acquire a story.
    """
    global _active_chronicle, _active_story, _story_handle
    chronicle = chronicle_name or DEFAULT_CHRONICLE
    story     = story_name or DEFAULT_STORY

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
    _active_story     = story
    _story_handle     = handle
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
    _active_story     = None
    _story_handle     = None
    return "ChronoLog session stopped and disconnected"

def to_nanosecond(dt: datetime) -> str:
    # nanoseconds since Unix epoch
    return str(int(dt.timestamp() * 1e9))

def parse_time_arg(arg: str, is_end: bool) -> str:
    """
    If arg is all digits, assume it's already nanoseconds.
    Else if it's 'yesterday', 'today', 'tomorrow', or YYYY-MM-DD,
    convert to a datetime at start/end of that day and return nanoseconds.
    """
    if arg.isdigit():
        return arg

    a = arg.strip().lower()
    now = datetime.now()

    if a == "yesterday":
        d = (now - timedelta(days=1)).date()
    elif a == "today":
        d = now.date()
    elif a == "tomorrow":
        d = (now + timedelta(days=1)).date()
    else:
        # try ISO date
        try:
            d = datetime.fromisoformat(arg).date()
        except ValueError:
            raise ValueError(f"Unrecognized date: {arg!r}")

    # pick start or end of that day
    if is_end:
        dt = datetime.combine(d, time(hour=23, minute=59, second=59, microsecond=999999))
    else:
        dt = datetime.combine(d, time.min)

    return to_nanosecond(dt)

@mcp.tool()
async def retrieve_interaction(
    chronicle_name: str = None,
    story_name: str = None,
    start_time: str = None,
    end_time: str = None
) -> str:
    """
    Do not assume the chronicle name and story name.
    If not provided, use the default values.
    Run the HDF5 reader, extract only the 'record' fields,
    save them to a text file, and return the file path.
    """
    chronicle = chronicle_name or DEFAULT_CHRONICLE
    story     = story_name     or DEFAULT_STORY

    cmd = [
        "stdbuf", "-o0",
        READER_BINARY,
        "-c", CONFIG_FILE,
        "-C", chronicle,
        "-S", story
    ]
    if start_time:
        try:
            st_ns = parse_time_arg(start_time, is_end=False)
        except ValueError as e:
            return str(e)
        cmd += ["-st", st_ns]

    if end_time:
        try:
            et_ns = parse_time_arg(end_time, is_end=True)
        except ValueError as e:
            return str(e)
        cmd += ["-et", et_ns]
    print(cmd)
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        return f"Error running reader: {e.stderr.strip()}"

    # Extract all record="..."
    records = re.findall(r'record="([^"]*)"', result.stdout)
    if not records:
        return "No records found."

    # Create a timestamped filename
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"records_{chronicle}_{story}_{ts}.txt"

    # Write the records to the file
    with open(filename, "w") as f:
        f.write("\n".join(records))

    # Return the path to the file
    return filename

if __name__ == "__main__":
    mcp.run()
