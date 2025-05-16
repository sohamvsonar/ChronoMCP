# ChronoLog MCP Server

An MCP (Model Context Protocol) server that integrates with ChronoLog, a scalable, high-performance distributed shared log store. This server exposes tools to manage interactions between LLM's and User's, making it easy to capture and retrieve events in a structured format.

## Detailed Description

The MCP server provides a unified architecture for both real-time capturing of conversation (prompts and responses) and long-term playback of structured event sequences using custom tools, along with additional features such as semantic search, and automated generation and storage of session summaries.
MCP servers allow teams to rapidly spin up domain-specific logging interfaces—whether for  R&D notebooks, mental-health tracking, or real-time chat systems—without reinventing the I/O layer.

The MCP server isn’t limited to a single LLM or user session—multiple clients and LLM instances can connect simultaneously, read from one another’s chronicles, and share context in real time

## Features

- **start_chronolog**: Creates a chronicle and acquires a story handle.
- **record_interaction**: Appends log events to the active story.
- **stop_chronolog**: Releases the story and disconnects the client.
- **retrieve_interaction**: Returns the logs or messages from the past.

## Prerequisites

- Python 3.11
- [py_chronolog_client](https://github.com/grc-iit/ChronoLog) Python package
- [mcp-server](https://github.com/sohamvsonar/chronoMCP) package
- `python-dotenv` for environment variable management
- Command-line runner `uv` (install with `pip install uv`)
- .env file in the src folder for the client.

## ChronoLog Deployment

For ChronoLog Installation and Deployment, refer to [ChronoLog Setup](https://github.com/sohamvsonar/ChronoMCP/Chronolog_setup.md).

## Custom MCP Client

A command-line client that connects to the ChronoLog MCP server, uses Google Gemini as the LLM, and automatically records every user ↔ assistant exchange back into ChronoLog.

With the Custom MCP Client you do not need to invoke the record_interaction tool as it automatically invokes the tool and stores each conversation between the user and assistant in real time.

**.env example**
   ```bash
   GEMINI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```


### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sohamvsonar/ChronoMCP.git
   ```

2. **Install UV runner**
   ```bash
   pip install uv
   ```
3. **Running the Client**
   ```bash
   uv run client.py
   ```

### Usage

1. Start Chronolog
2. Have Conversation
3. Retrieve Interaction
4. Stop Chronolog

 ![](https://github.com/sohamvsonar/ChronoMCP/blob/main/assets/mcp-client.png)

## Open Source MCP Client

You can connect the mcp server with any of the open source MCP Clients such as Microsoft Visual Studio Copilot, Claude AI, Windsurf,etc.
Simply add the configuration below to your Clients settings.json and start the server, the tools will automatically get loaded in your client.

### Configuration

Add the following to your `settings.json` file on Claude or any other client:

```json
{
  "chronolog-mcp": {
    "command": "uv",
    "args": [
      "--directory",
      "/path/to/the/directory",
      "run",
      "server.py"
    ]
  }
}
```

Some Samples from Visual Studio Copilot:

 ![](https://github.com/sohamvsonar/ChronoMCP/blob/main/assets/mcp-retievecopilot.png)

 ![](https://github.com/sohamvsonar/ChronoMCP/blob/main/assets/mcp-retrieve-diseasepred.png)

## Usage

Run the MCP server or client to register the ChronoLog tools:

By default, the server listens for MCP tool invocations and exposes:

1. **start_chronolog()**
   - **Description**: Connects to ChronoLog, creates a chronicle, and acquires a story handle.
   - **Returns**: Confirmation message with chronicle and story identifiers.

2. **record_interaction(event: str)**
   - **Description**: Logs the given event string of user message and LLM output message to the acquired story.
   - **Args**:
     - `event` (str): The event name or message to record.
   - **Returns**: Confirmation of event logging.

3. **stop_chronolog()**
   - **Description**: Releases the story handle and disconnects from ChronoLog.
   - **Returns**: Confirmation of clean shutdown.

4. **retrieve_interaction()**
   - **Description**: Extracts only the records from a specified chronicle and story, writes them to a timestamped text file. Supports both raw nanosecond timestamps and human-readable dates (e.g. “yesterday”, “2025-04-30”).
   - **Returns**: Generated text file (e.g. records_LLM_conversation_20250502123045.txt), or an error message if the reader fails or finds no record
   - **Use Case samples**: 
      - Prompt "retrieve our interaction from yesterday and add  it with the session chat to make a summary."
      - Prompt "retrieve yesterday's interaction with chronicle name research and story name systems"

## Extending

We’re actively working on additional improvements (search, summaries, analytics, etc.). Contributions and feature requests are welcome!
