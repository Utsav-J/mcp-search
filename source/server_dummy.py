from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

mcp = FastMCP(
    name="dummy-server",
    host="127.0.0.1",
    port=8001,
)

DUMMY_POST_API_URL = "https://httpbin.org/post"

async def make_dummy_post_request(data: dict) -> dict:
    """Make a POST request to a dummy endpoint for testing."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(DUMMY_POST_API_URL, json=data, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to contact dummy API: {str(e)}"}

@mcp.tool(name="Dummy Post Tool")
async def dummy_post_tool(message: str) -> Any:
    """Send a message to a dummy POST endpoint and return the response.

    Args:
        message: Any string to send in the payload.
    """
    try:
        payload = {"message": message}
        return await make_dummy_post_request(payload)
    except:
        return {"Error":"But OK"}

# Add a custom GET /health route for health checks 
@mcp.custom_route("/health", methods=['GET',"POST"])
async def health_check(request:Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

@mcp.resource("app://details", name="Application details")
def get_config() -> str:
    """Static configuration data"""
    return "Welcome to Tachyon Search API"


if __name__ == "__main__":
    transport = "sse"
    if transport == "stdio":
        print("Running dummy server with stdio transport")
        mcp.run(transport="stdio")
    elif transport == "sse":
        print("Running dummy server with SSE transport")
        mcp.run(transport="streamable-http")
    else:
        raise ValueError(f"Unknown transport: {transport}") 