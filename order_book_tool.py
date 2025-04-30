# order_book_tool.py
import requests
from mcp.server.fastmcp import FastMCP
from config import DHAN_ACCESS_TOKEN, DHAN_API_BASE_URL

# Create the MCP server
mcp = FastMCP("DhanHQ Order Book")

@mcp.tool()
def get_order_book():
    """
    Get a list of all orders for the day
    
    Returns:
        Dictionary containing order book information
    """
    url = f"{DHAN_API_BASE_URL}/orders"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        orders_data = response.json()
        
        return {
            "status": "success",
            "orders_count": len(orders_data),
            "orders": orders_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch order book: {str(e)}"
        }

@mcp.tool()
def get_order_status(order_id):
    """
    Get status of a specific order
    
    Args:
        order_id: ID of the order to check
    
    Returns:
        Dictionary containing order status information
    """
    url = f"{DHAN_API_BASE_URL}/orders/{order_id}"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        order_data = response.json()
        
        return {
            "status": "success",
            "order": order_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch order status: {str(e)}"
        }

@mcp.tool()
def get_trade_book():
    """
    Get a list of all trades for the day
    
    Returns:
        Dictionary containing trade book information
    """
    url = f"{DHAN_API_BASE_URL}/trades"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        trades_data = response.json()
        
        return {
            "status": "success",
            "trades_count": len(trades_data),
            "trades": trades_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch trade book: {str(e)}"
        }

@mcp.tool()
def get_order_trades(order_id):
    """
    Get all trades associated with a specific order
    
    Args:
        order_id: ID of the order
    
    Returns:
        Dictionary containing trades information for the order
    """
    url = f"{DHAN_API_BASE_URL}/trades/{order_id}"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        trades_data = response.json()
        
        return {
            "status": "success",
            "order_id": order_id,
            "trades": trades_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch order trades: {str(e)}"
        }

@mcp.tool()
def cancel_order(order_id):
    """
    Cancel a pending order
    
    Args:
        order_id: ID of the order to cancel
    
    Returns:
        Status of the cancellation request
    """
    url = f"{DHAN_API_BASE_URL}/orders/{order_id}"
    headers = {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN
    }
    
    try:
        response = requests.delete(url, headers=headers)
        
        if response.status_code in [200, 202]:
            return {
                "status": "success",
                "message": f"Successfully cancelled order {order_id}",
                "order_status": "CANCELLED" if response.status_code == 200 else "CANCELLATION_REQUESTED"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to cancel order. Status code: {response.status_code}",
                "details": response.text
            }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to cancel order: {str(e)}"
        }

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()