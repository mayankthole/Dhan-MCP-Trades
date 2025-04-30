# holdings_positions_tool.py
import requests
from mcp.server.fastmcp import FastMCP
from config import DHAN_ACCESS_TOKEN, DHAN_API_BASE_URL

# Create the MCP server
mcp = FastMCP("DhanHQ Holdings & Positions")

@mcp.tool()
def get_holdings():
    """
    Get a list of all holdings in your demat account
    
    Returns:
        Dictionary containing holdings information
    """
    url = f"{DHAN_API_BASE_URL}/holdings"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        holdings_data = response.json()
        
        return {
            "status": "success",
            "holdings_count": len(holdings_data),
            "holdings": holdings_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch holdings: {str(e)}"
        }

@mcp.tool()
def get_positions():
    """
    Get a list of all open positions for the day
    
    Returns:
        Dictionary containing positions information
    """
    url = f"{DHAN_API_BASE_URL}/positions"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        positions_data = response.json()
        
        return {
            "status": "success",
            "positions_count": len(positions_data),
            "positions": positions_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch positions: {str(e)}"
        }

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
    
    Returns:
        Status of the position conversion
    """
    url = f"{DHAN_API_BASE_URL}/positions/convert"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    data = {
        "dhanClientId": "",  # Will be taken from token
        "fromProductType": from_product_type.upper(),
        "exchangeSegment": exchange_segment.upper(),
        "positionType": position_type.upper(),
        "securityId": security_id,
        "tradingSymbol": trading_symbol,
        "convertQty": str(convert_qty),
        "toProductType": to_product_type.upper()
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 202:
            return {
                "status": "success",
                "message": f"Successfully converted {convert_qty} shares from {from_product_type} to {to_product_type}"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to convert position. Status code: {response.status_code}",
                "details": response.text
            }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to convert position: {str(e)}"
        }

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()