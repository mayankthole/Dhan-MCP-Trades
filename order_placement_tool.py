# order_placement_tool.py
import json
import os
import requests
from mcp.server.fastmcp import FastMCP
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, DHAN_API_BASE_URL

# Create the MCP server
mcp = FastMCP("DhanHQ Order Placement")

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
def place_order(stock_name, quantity, transaction_type, product_type="INTRADAY", order_type="MARKET"):
    """
    Place a new order for a stock.
    
    Args:
        stock_name: The name of the stock (e.g., "ADANIENT")
        quantity: Number of shares to buy/sell
        transaction_type: "BUY" or "SELL"
        product_type: Product type (default: "INTRADAY")
        order_type: Order type (default: "MARKET")
    
    Returns:
        Order status information
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
        "disclosedQuantity": "",
        "price": "",
        "triggerPrice": "",
        "afterMarketOrder": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=order_data)
        
        if response.status_code in [200, 201, 202]:
            return {
                "status": "success",
                "message": f"Order placed successfully for {quantity} shares of {stock_name}",
                "order_details": response.json()
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to place order. Status code: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error placing order: {str(e)}"
        }

@mcp.tool()
def list_available_stocks():
    """
    List all available stocks in the stocks.json file.
    
    Returns:
        List of available stocks with their names and codes
    """
    stocks = load_stocks_data()
    stock_list = [{"name": stock.get('stock_name'), "code": stock.get('stock_code')} 
                 for stock in stocks]
    
    return {
        "status": "success",
        "message": f"Found {len(stock_list)} stocks",
        "stocks": stock_list
    }

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()