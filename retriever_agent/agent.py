from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import  StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
# Use the Streamable HTTP endpoint, as server_dummy.py runs with transport="streamable-http" on port 8001
MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"

# Create the MCP toolset for the agent
mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPServerParams(url=MCP_SERVER_URL)
)

root_agent = LlmAgent(
    model="gemini-2.0-flash",  # You can change to your preferred model
    name="retriever_agent",
    instruction=(
        "You are a helpful agent that can use the Dummy Post Tool via the MCP server. "
        "When you use this tool, always show the user all available details for each hit, "
        "including the score, title, summary, document_url, section_url, and any other fields. "
        "Format the output as a readable list or table."
    ),
    tools=[mcp_toolset],
)
