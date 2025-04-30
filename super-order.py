# super_order_tool.py
import json
import os
import requests
from mcp.server.fastmcp import FastMCP
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, DHAN_API_BASE_URL

# Create the MCP server
mcp = FastMCP("DhanHQ Super Order")

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
def place_super_order(
    stock_name, 
    quantity, 
    transaction_type,
    price=None,
    target_type="value",  # "value" or "percentage"
    target_value=None,
    stoploss_type="value",  # "value" or "percentage"
    stoploss_value=None,
    trailing_jump=0,
    product_type="INTRADAY",
    order_type="LIMIT"
):
    """
    Place a super order with target and stop loss.
    
    Args:
        stock_name: The name of the stock (e.g., "ADANIENT")
        quantity: Number of shares to buy/sell
        transaction_type: "BUY" or "SELL"
        price: Order price (if None, will use market order)
        target_type: "value" for absolute price, "percentage" for percentage gain/loss
        target_value: Target value (either absolute price or percentage)
        stoploss_type: "value" for absolute price, "percentage" for percentage gain/loss
        stoploss_value: Stop loss value (either absolute price or percentage)
        trailing_jump: Price jump for trailing stop loss (0 for no trailing)
        product_type: Product type (default: "INTRADAY")
        order_type: Order type (default: "LIMIT")
    
    Returns:
        Order status information
    """
    # Validate transaction type
    if transaction_type.upper() not in ["BUY", "SELL"]:
        return {
            "status": "error",
            "message": "Transaction type must be either 'BUY' or 'SELL'"
        }
    
    # Set order_type to MARKET if price is None
    if price is None:
        order_type = "MARKET"
        price = 0
    
    # Find the stock code
    stock_code = find_stock_code(stock_name)
    if not stock_code:
        return {
            "status": "error",
            "message": f"Stock '{stock_name}' not found in stocks.json"
        }
    
    # Get current market price (for percentage calculations)
    # In a real scenario, you would fetch this from market data API
    # For now, we'll use the provided price if available
    current_price = price
    if current_price is None or current_price == 0:
        return {
            "status": "error",
            "message": "For percentage targets/stoploss, a valid price must be provided"
        }
    
    # Calculate target price
    target_price = None
    if target_value is not None:
        if target_type == "percentage":
            if transaction_type.upper() == "BUY":
                # For buy, target is higher than entry price
                target_price = current_price * (1 + target_value / 100)
            else:
                # For sell, target is lower than entry price
                target_price = current_price * (1 - target_value / 100)
        else:  # "value"
            target_price = target_value
    
    # Calculate stop loss price
    stoploss_price = None
    if stoploss_value is not None:
        if stoploss_type == "percentage":
            if transaction_type.upper() == "BUY":
                # For buy, stop loss is lower than entry price
                stoploss_price = current_price * (1 - stoploss_value / 100)
            else:
                # For sell, stop loss is higher than entry price
                stoploss_price = current_price * (1 + stoploss_value / 100)
        else:  # "value"
            stoploss_price = stoploss_value
    
    # Prepare super order request
    url = f"{DHAN_API_BASE_URL}/super/orders"
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
        "securityId": stock_code,
        "quantity": quantity,
        "price": price
    }
    
    # Add target and stop loss if provided
    if target_price is not None:
        order_data["targetPrice"] = target_price
    
    if stoploss_price is not None:
        order_data["stopLossPrice"] = stoploss_price
    
    # Add trailing jump if provided
    if trailing_jump > 0:
        order_data["trailingJump"] = trailing_jump
    
    try:
        response = requests.post(url, headers=headers, json=order_data)
        
        if response.status_code in [200, 201, 202]:
            return {
                "status": "success",
                "message": f"Super order placed successfully for {quantity} shares of {stock_name}",
                "order_details": {
                    "entry_price": price,
                    "target_price": target_price,
                    "stoploss_price": stoploss_price,
                    "trailing_jump": trailing_jump,
                    "response": response.json()
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to place super order. Status code: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error placing super order: {str(e)}"
        }

@mcp.tool()
def list_super_orders():
    """
    List all super orders.
    
    Returns:
        List of all super orders
    """
    url = f"{DHAN_API_BASE_URL}/super/orders"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return {
                "status": "success",
                "orders": response.json()
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to fetch super orders. Status code: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error fetching super orders: {str(e)}"
        }

@mcp.tool()
def cancel_super_order(order_id, leg_name="ENTRY_LEG"):
    """
    Cancel a super order or specific leg.
    
    Args:
        order_id: ID of the order to cancel
        leg_name: Leg to cancel (ENTRY_LEG, TARGET_LEG, or STOP_LOSS_LEG)
    
    Returns:
        Cancellation status
    """
    url = f"{DHAN_API_BASE_URL}/super/orders/{order_id}/{leg_name}"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.delete(url, headers=headers)
        
        if response.status_code in [200, 202]:
            return {
                "status": "success",
                "message": f"Successfully cancelled {leg_name} of order {order_id}",
                "response": response.json()
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to cancel order. Status code: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error cancelling order: {str(e)}"
        }

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()