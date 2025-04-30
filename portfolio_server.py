# portfolio_server.py
import requests
from mcp.server.fastmcp import FastMCP
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, DHAN_API_BASE_URL

# Create the MCP server
mcp = FastMCP("DhanHQ Portfolio")

# Holdings Tool
@mcp.tool()
def get_holdings():
    """Get a list of all holdings in your demat account"""
    url = f"{DHAN_API_BASE_URL}/holdings"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    response = requests.get(url, headers=headers)
    return response.json()

# Positions Tool
@mcp.tool()
def get_positions():
    """Get a list of all open positions for the day"""
    url = f"{DHAN_API_BASE_URL}/positions"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    response = requests.get(url, headers=headers)
    return response.json()

# Position Conversion Tool
@mcp.tool()
def convert_position(
    from_product_type,
    to_product_type,
    exchange_segment,
    position_type,
    security_id,
    convert_qty,
    trading_symbol=""
):
    """
    Convert a position from one product type to another
    
    Args:
        from_product_type: Current product type (CNC, INTRADAY, MARGIN, CO, BO)
        to_product_type: Target product type (CNC, INTRADAY, MARGIN, CO, BO)
        exchange_segment: Exchange and segment (NSE_EQ, NSE_FNO, etc.)
        position_type: Type of position (LONG, SHORT)
        security_id: Exchange standard ID for the security
        convert_qty: Number of shares to convert
        trading_symbol: Trading symbol (optional)
    """
    url = f"{DHAN_API_BASE_URL}/positions/convert"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    data = {
        "dhanClientId": DHAN_CLIENT_ID,
        "fromProductType": from_product_type,
        "exchangeSegment": exchange_segment,
        "positionType": position_type,
        "securityId": security_id,
        "tradingSymbol": trading_symbol,
        "convertQty": str(convert_qty),
        "toProductType": to_product_type
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 202:
        return {"status": "success", "message": "Position conversion successful"}
    else:
        return {"status": "error", "message": response.text}

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()