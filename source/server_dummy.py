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

@mcp.tool(name="dummyPostTool")
async def dummy_post_tool(message: str) -> Any:
    """Send a message to a dummy POST endpoint and return the response.

    Args:
        message: Any string to send in the payload.
    """
    try:
        payload = {"message": message}
        dum_response = {
            "result": {
                "hits": [
                    {
                        "score": 0.9821,
                        "record": {
                            "raw_context": "Wells Fargo offers various credit card benefits such as cash back and reward points.",
                            "presentation_context": "Financial Services - Credit Cards",
                            "book": "CreditCardBenefits_2023",
                            "document_url": "https://docs.wellsfargo.com/cc-benefits2023.pdf",
                            "section_url": "https://docs.wellsfargo.com/cc-benefits2023.pdf#section1",
                            "procedure_identifier": "CCB-001",
                            "procedure_revision_number": "rev-5",
                            "summary": "Overview of Wells Fargo credit card benefits.",
                            "title": "Wells Fargo Credit Card Benefits",
                            "chunk_id": "chunk-001",
                        },
                    },
                    {
                        "score": 0.9473,
                        "record": {
                            "raw_context": "The Wells Fargo Active Cash® Card provides unlimited 2% cash rewards on purchases.",
                            "presentation_context": "Product Information - Active Cash Card",
                            "book": "ActiveCashGuide",
                            "document_url": "https://docs.wellsfargo.com/active-cash.pdf",
                            "section_url": "https://docs.wellsfargo.com/active-cash.pdf#benefits",
                            "procedure_identifier": "ACC-003",
                            "procedure_revision_number": "rev-2",
                            "summary": "Benefits of the Wells Fargo Active Cash® Card.",
                            "title": "Active Cash® Card Rewards",
                            "chunk_id": "chunk-009",
                        },
                    },
                ]
            }
        }
        return dum_response
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
