# LangGraph Agent for MCP Server

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure your MCP server is running (default: http://127.0.0.1:8001).

3. (Optional) Set the MCP server URL:
   ```bash
   export MCP_SERVER_URL="http://127.0.0.1:8001"
   ```
   On Windows (cmd):
   ```cmd
   set MCP_SERVER_URL=http://127.0.0.1:8001
   ```

## Run the Agent

```bash
python agent.py
```

Type your message. If your message contains the word 'dummy', the agent will call the MCP server's dummy_post_tool. Otherwise, it will echo your message. 