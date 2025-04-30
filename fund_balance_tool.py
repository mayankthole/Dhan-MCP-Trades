# fund_balance_tool.py
import requests
from mcp.server.fastmcp import FastMCP
from config import DHAN_ACCESS_TOKEN, DHAN_API_BASE_URL

# Create the MCP server
mcp = FastMCP("DhanHQ Fund Balance")

@mcp.tool()
def check_fund_balance():
    """
    Get trading account fund information including available balance and margin details
    
    Returns:
        Dictionary containing fund information
    """
    url = f"{DHAN_API_BASE_URL}/fundlimit"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "status": "success",
            "funds": {
                "available_balance": data.get("availabelBalance"),
                "start_of_day_limit": data.get("sodLimit"),
                "collateral_amount": data.get("collateralAmount"),
                "receiveable_amount": data.get("receiveableAmount"),
                "utilized_amount": data.get("utilizedAmount"),
                "blocked_payout_amount": data.get("blockedPayoutAmount"),
                "withdrawable_balance": data.get("withdrawableBalance")
            }
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch fund balance: {str(e)}"
        }

@mcp.tool()
def calculate_margin(
    security_id, 
    exchange_segment, 
    transaction_type, 
    quantity, 
    product_type, 
    price, 
    trigger_price=None
):
    """
    Calculate margin requirement for a potential order
    
    Args:
        security_id: Exchange standard ID for the security
        exchange_segment: Exchange segment (NSE_EQ, NSE_FNO, etc.)
        transaction_type: BUY or SELL
        quantity: Number of shares
        product_type: Product type (CNC, INTRADAY, etc.)
        price: Order price
        trigger_price: Trigger price for SL orders (optional)
    
    Returns:
        Dictionary containing margin requirements
    """
    url = f"{DHAN_API_BASE_URL}/margincalculator"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    data = {
        "dhanClientId": "",  # This will be taken from the token
        "exchangeSegment": exchange_segment,
        "transactionType": transaction_type,
        "quantity": quantity,
        "productType": product_type,
        "securityId": security_id,
        "price": price
    }
    
    # Add trigger price if provided
    if trigger_price is not None:
        data["triggerPrice"] = trigger_price
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        margin_data = response.json()
        
        return {
            "status": "success",
            "margin_details": {
                "total_margin": margin_data.get("totalMargin"),
                "span_margin": margin_data.get("spanMargin"),
                "exposure_margin": margin_data.get("exposureMargin"),
                "available_balance": margin_data.get("availableBalance"),
                "variable_margin": margin_data.get("variableMargin"),
                "insufficient_balance": margin_data.get("insufficientBalance"),
                "brokerage": margin_data.get("brokerage"),
                "leverage": margin_data.get("leverage")
            }
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to calculate margin: {str(e)}"
        }

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()