from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import uuid
from datetime import datetime, timezone

# Create an MCP server
mcp = FastMCP(
    name="tachyon-search",
    host="0.0.0.0",  # only used for SSE transport (localhost)
    port=8000,        # only used for SSE transport (set this to any port)
)

# Constants (placeholders)
TACHYON_SEARCH_API_URL = "https://placeholder.tachyon.api/search"
APP_ID = "YOUR_APP_ID"
API_KEY = "YOUR_API_KEY"
APIGEE_TOKEN = "YOUR_APIGEE_ACCESS_TOKEN"
USECASE_ID = "test_search_v1"  # Hardcoded as per requirements

async def make_tachyon_request(query: str) -> dict[str, Any] | None:
    """Make a request to the TachyonSearchAPI with proper headers and error handling."""
    now = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    headers = {
        "x-request-id": request_id,
        "x-wf-request-date": now,
        "x-correlation-id": correlation_id,
        "x-wf-client-id": APP_ID,
        "x-wf-api-key": API_KEY,
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APIGEE_TOKEN}",
    }
    payload = {
        "query": query,
        "usecaseId": USECASE_ID,
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(TACHYON_SEARCH_API_URL, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to contact TachyonSearchAPI: {str(e)}"}

@mcp.tool()
async def semantic_search(query: str) -> Any:
    """Perform a semantic search using the TachyonSearchAPI.

    Args:
        query: The search input query string.
    """
    if not query:
        return {"error": "Query string is required."}
    result = await make_tachyon_request(query)
    return result

# Run the server
if __name__ == "__main__":
    transport = "sse"
    if transport == "stdio":
        print("Running server with stdio transport")
        mcp.run(transport="stdio")
    elif transport == "sse":
        print("Running server with SSE transport")
        mcp.run(transport="sse")
    else:
        raise ValueError(f"Unknown transport: {transport}")
