# margin_calculator_tool.py
import json
import os
import requests
from mcp.server.fastmcp import FastMCP
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, DHAN_API_BASE_URL

# Create the MCP server
mcp = FastMCP("DhanHQ Margin Calculator")

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
def calculate_margin_by_stock_name(
    stock_name, 
    transaction_type, 
    quantity, 
    product_type="INTRADAY", 
    price=None, 
    trigger_price=None
):
    """
    Calculate margin requirement for a stock by name
    
    Args:
        stock_name: Name of the stock (e.g., "ADANIENT")
        transaction_type: "BUY" or "SELL"
        quantity: Number of shares
        product_type: Product type (INTRADAY, CNC, etc.)
        price: Order price (optional)
        trigger_price: Trigger price for SL orders (optional)
    
    Returns:
        Dictionary containing margin requirements
    """
    # Validate transaction type
    if transaction_type.upper() not in ["BUY", "SELL"]:
        return {
            "status": "error",
            "message": "Transaction type must be either 'BUY' or 'SELL'"
        }
    
    # Find the stock code
    stock_code = find_stock_code(stock_name)
    if not stock_code:
        return {
            "status": "error",
            "message": f"Stock '{stock_name}' not found in stocks.json"
        }
    
    url = f"{DHAN_API_BASE_URL}/margincalculator"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    data = {
        "dhanClientId": DHAN_CLIENT_ID,
        "exchangeSegment": "NSE_EQ",
        "transactionType": transaction_type.upper(),
        "quantity": quantity,
        "productType": product_type.upper(),
        "securityId": stock_code
    }
    
    # Add price if provided
    if price is not None:
        data["price"] = price
    
    # Add trigger price if provided
    if trigger_price is not None:
        data["triggerPrice"] = trigger_price
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        margin_data = response.json()
        
        return {
            "status": "success",
            "stock_info": {
                "name": stock_name,
                "code": stock_code
            },
            "order_details": {
                "transaction_type": transaction_type.upper(),
                "quantity": quantity,
                "product_type": product_type.upper(),
                "price": price,
                "trigger_price": trigger_price
            },
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