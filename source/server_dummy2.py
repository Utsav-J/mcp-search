from typing import Any, Dict, List
import httpx
from litprinter import lit
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

mcp = FastMCP(
    name="second-server",
    host="127.0.0.1",
    port=8002,
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


@mcp.tool(name="ForeignExchangeLookup")
async def dummy_post_tool(currencyCode: str, date_range: str) -> Any:
    """
    Look up records for historical foreign exchange data.

    Args:
        currencyCode: String containing two currencies in the fashion currency1/currency2. Example: "USD/CAD".
        date_range: String denoting the date range. Example "2023/01/01-2024/01/01".
    """

    print("TOOL CALL")
    try:
        payload = {"ccyPair": currencyCode, "date_range": date_range}
        print(payload)
        return payload
    except:
        return {"Error": "But OK"}


@mcp.tool(name="GetForeignExchangeTransactionData")
async def get_foreign_exchange_transaction_data(
    settlement_status: str = "Approved",
) -> List[Dict[str, Any]]:
    """
    Retrieve Foreign Exchange Transaction Data for a specific Company ID and settlement status.
    Provides the company details, currency amount details, channels, account details,
    details about DTO and also personal details of people who made the transaction.
    If no settlement status provided use `Approved` as its value

    Args:
        settlement_status: Status code of the transaction in title case.
                           Value of settlement_status can be and is limited to the following options:
                           - 'All'
                           - 'Approved'
                           - 'Pending Approval'
                           - 'Rejected'
                           - 'Netted'
                           - 'Uninstructed'

    Returns:
        List of transaction data dictionaries
    """
    lit("GetForeignExchangeFXTransactionData")
    company_id: str = "SITCOMP2"
    value_date: str = "NA"
    if settlement_status.lower() == "settled":
        settlement_status = "Approved"
    payload = {
        "companyId": company_id,
        "valueDate": value_date,
        "settlement_status": settlement_status,
    }
    sample_response_for_get_transactions = {
        "transactionId": "94806599",
        "companyName": "FXOL 8TEST",
        "valueDate": "08-May-2025",
        "tradeDate": "07-May-2025",
        "allInRate": "No Contract",
        "buyCurrency": "CAD",
        "buyCurrencyAmount": "50.00",
        "sellCurrency": "USD",
        "sellCurrencyAmount": "No Contract",
        "spotRate": "No Contract",
        "forwardPoints": "No Contract",
        "productType": "FXSPOT",
        "channel": "FX Online",
        "settlementStatus": "Rejected",
        "templateDTO": {"beneName": "Name", "beneAccountNo": "213"},
        "accountDTO": {
            "accountType": "MCA",
            "accountNumber": "xx1414",
            "bankName": "Wells Fargo Bank",
            "swiftCode": None,
        },
        "historyDTO": [
            {
                "date": "08-May-2025",
                "time": "08:18:41 am ET",
                "activity": "Instructions rejected by Venky Dapulil<br /><b>Reject Reason: </b>Reject",
            },
            {
                "date": "07-May-2025",
                "time": "04:15:52 am ET",
                "activity": "Instructions submitted by Sai Sreekanth T",
            },
        ],
    }
    response = sample_response_for_get_transactions
    return response


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
