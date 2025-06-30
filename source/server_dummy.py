from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

mcp = FastMCP(
    name="fisrt-server",
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


@mcp.tool(name="SemanticSearch")
async def dummy_post_tool(message: str) -> Any:
    """
    Perform a semantic search on the vector database to retrieve data about credit cards.

    Args:
        message: Any string to send in the payload.
    """
    print("TOOL CALL")
    try:
        payload = {"message": message}
        dum_response = {
            "result": {
                "hits": [
                    {
                        "score": 0.7569691,
                        "record": {
                            "usecase_id": "GENAI101_CEOPT",
                            "document_id": "https://wellsfargo.bluematrix.com/links2/link/pdf/397f1b17-e968-4bfa-b245-2c4cdedabb0b",
                            "chunk_id": "120e06dcfad4882afc8b",
                            "raw_context": "Economics Special Commentary - March 25, 2025 April Showers For Better or Worse",
                            "file_name": "d853d45b-7b74-4608-9863-22369a6846b1.pdf",
                            "title": "https://wellsfargo.bluematrix.com/links2/link/pdf/397f1b17-e968-4bfa-b245-2c4cdedabb0b",
                            "data_classification": "internal",
                            "sor_last_modified": "2025-05-17T00:01:53.551391",
                            "book": "d853d45b-7b74-4608-9863-22369a6846b1",
                            "page_number": 1,
                            "file_id": "29a6ce0d-26c2-4cf3-86c8-f8ce14b2bc71",
                            "chunk_insert_date": "2025-05-15T04:32:44.644586",
                        },
                    },
                    {
                        "score": 0.7535724,
                        "record": {
                            "data_classification": "internal",
                            "sor_last_modified": "2025-05-17T00:01:53.551391",
                            "book": "d853d45b-7b74-4608-9863-22369a6846b1",
                            "page_number": 1,
                            "file_id": "29a6ce0d-26c2-4cf3-86c8-f8ce14b2bc71",
                            "chunk_insert_date": "2025-05-15T04:32:44.644586",
                            "usecase_id": "GENAI101_CEOPT",
                            "document_id": "https://wellsfargo.bluematrix.com/links2/link/pdf/241420e9247a49aadfa4",
                            "title": "https://wellsfargo.bluematrix.com/links2/link/pdf/397f1b17-e968-4bfa-b245-2c4cdedabb0b",
                            "chunk_id": "241420e9247a49aadfa4",
                            "raw_context": "April Showers Economics incredibly challenging to back into estimates of the economy.",
                            "file_name": "d853d45b-7b74-4608-9863-22369a6846b1.pdf",
                        },
                    },
                ]
            }
        }
        print(dum_response)
        return dum_response
    except:
        return {"Error": "But OK"}


# Add a custom GET /health route for health checks
@mcp.custom_route("/health", methods=["GET", "POST"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


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
