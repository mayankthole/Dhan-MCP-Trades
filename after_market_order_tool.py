# after_market_order_tool.py
import json
import os
import requests
from mcp.server.fastmcp import FastMCP
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, DHAN_API_BASE_URL

# Create the MCP server
mcp = FastMCP("DhanHQ After Market Order")

# Helper function to load stocks data
def load_stocks_data():
    """Load the stocks data from stocks.json file"""
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the path to stocks.json
        stocks_file_path = os.path.join(script_dir, "stocks.json")
        
        with open(stocks_file_path, 'r') as file:
            data = json.load(file)
            return data.get('companies', [])
    except Exception as e:
        print(f"Error loading stocks data: {e}")
        return []

# Find stock code by name
def find_stock_code(stock_name):
    """Find the stock code for a given stock name"""
    stocks = load_stocks_data()
    for stock in stocks:
        if stock.get('stock_name', '').lower() == stock_name.lower():
            return stock.get('stock_code')
    return None

@mcp.tool()
def place_after_market_order(
    stock_name, 
    quantity, 
    transaction_type,
    amo_time="OPEN",
    product_type="CNC",
    order_type="LIMIT",
    price=None,
    trigger_price=None,
    disclosed_quantity=None
):
    """
    Place an After Market Order (AMO) to be executed on the next trading day.
    
    Args:
        stock_name: Name of the stock (e.g., "ADANIENT")
        quantity: Number of shares to buy/sell
        transaction_type: "BUY" or "SELL"
        amo_time: When to execute the order
            - "PRE_OPEN" (Pre-market session)
            - "OPEN" (Market open)
            - "OPEN_30" (30 mins after market open)
            - "OPEN_60" (60 mins after market open)
        product_type: Product type (default: "CNC")
        order_type: Order type (default: "LIMIT")
        price: Order price (required for LIMIT orders)
        trigger_price: Trigger price (required for STOP_LOSS orders)
        disclosed_quantity: Number of shares to be disclosed (optional)
    
    Returns:
        Status of the order placement
    """
    # Validate transaction type
    if transaction_type.upper() not in ["BUY", "SELL"]:
        return {
            "status": "error",
            "message": "Transaction type must be either 'BUY' or 'SELL'"
        }
    
    # Validate order type and required parameters
    if order_type.upper() == "LIMIT" and price is None:
        return {
            "status": "error",
            "message": "Price is required for LIMIT orders"
        }
    
    if order_type.upper() in ["STOP_LOSS", "STOP_LOSS_MARKET"] and trigger_price is None:
        return {
            "status": "error",
            "message": "Trigger price is required for STOP_LOSS orders"
        }
    
    # Validate AMO time
    valid_amo_times = ["PRE_OPEN", "OPEN", "OPEN_30", "OPEN_60"]
    if amo_time not in valid_amo_times:
        return {
            "status": "error",
            "message": f"AMO time must be one of {valid_amo_times}"
        }
    
    # Find the stock code
    stock_code = find_stock_code(stock_name)
    if not stock_code:
        return {
            "status": "error",
            "message": f"Stock '{stock_name}' not found in stocks.json"
        }
    
    # Prepare order request
    url = f"{DHAN_API_BASE_URL}/orders"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    order_data = {
        "dhanClientId": DHAN_CLIENT_ID,
        "transactionType": transaction_type.upper(),
        "exchangeSegment": "NSE_EQ",
        "productType": product_type.upper(),
        "orderType": order_type.upper(),
        "validity": "DAY",
        "securityId": stock_code,
        "quantity": str(quantity),
        "afterMarketOrder": True,
        "amoTime": amo_time
    }
    
    # Add price if provided
    if price is not None:
        order_data["price"] = str(price)
    else:
        order_data["price"] = ""
    
    # Add trigger price if provided
    if trigger_price is not None:
        order_data["triggerPrice"] = str(trigger_price)
    else:
        order_data["triggerPrice"] = ""
    
    # Add disclosed quantity if provided
    if disclosed_quantity is not None:
        order_data["disclosedQuantity"] = str(disclosed_quantity)
    else:
        order_data["disclosedQuantity"] = ""
    
    try:
        response = requests.post(url, headers=headers, json=order_data)
        
        if response.status_code in [200, 201, 202]:
            return {
                "status": "success",
                "message": f"After Market Order placed successfully for {quantity} shares of {stock_name}",
                "order_details": {
                    "amo_time": amo_time,
                    "transaction_type": transaction_type,
                    "product_type": product_type,
                    "order_type": order_type,
                    "price": price,
                    "trigger_price": trigger_price,
                    "response": response.json()
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to place After Market Order. Status code: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error placing After Market Order: {str(e)}"
        }

@mcp.resource("dhan://amo/help")
def amo_help():
    """
    Provides information about After Market Orders (AMO)
    """
    return """
    # After Market Orders (AMO)
    
    After Market Orders are orders placed outside regular market hours that get executed
    during the next trading session.
    
    ## AMO Execution Times
    
    - **PRE_OPEN**: During pre-market session (9:00 AM - 9:15 AM)
    - **OPEN**: At market open (9:15 AM)
    - **OPEN_30**: 30 minutes after market open (9:45 AM)
    - **OPEN_60**: 60 minutes after market open (10:15 AM)
    
    ## Important Notes
    
    1. AMOs can be placed with any product type (CNC, INTRADAY, etc.)
    2. For LIMIT orders, price must be specified
    3. For STOP_LOSS orders, trigger price must be specified
    4. AMOs can be modified or cancelled before market open on the next trading day
    5. The default validity for AMOs is DAY
    """

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()