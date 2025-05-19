# server.py
import utils.config as config
from capabilities.start_handler    import start_chronolog as _start
from capabilities.record_handler import record_interaction as _record
from capabilities.stop_handler     import stop_chronolog  as _stop
from capabilities.retrieve_handler import retrieve_interaction as _retrieve

mcp = config.mcp

@mcp.tool()
async def start_chronolog(chronicle_name: str = None, story_name: str = None):
    """
    Create a chronicle and acquire a story.
    """
    return await _start(chronicle_name, story_name)

@mcp.tool()
async def record_interaction(user_message: str, assistant_message: str):
    """
    Append logs into the acquired story.
    """
    return await _record(user_message, assistant_message)

@mcp.tool()
async def stop_chronolog():
    """
    Release the story and disconnect from ChronoLog.
    """
    return await _stop()

@mcp.tool()
async def retrieve_interaction(
    chronicle_name: str = None,
    story_name: str = None,
    start_time: str = None,
    end_time: str = None
):
    """
    Retrieve all records from a chronicle and story within the specified time range.
    """
    return await _retrieve(chronicle_name, story_name, start_time, end_time)

if __name__ == "__main__":
    mcp.run()
