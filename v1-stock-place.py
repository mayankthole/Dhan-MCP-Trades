from mcp.server.fastmcp import FastMCP
import requests
import json
import os

# Create MCP server
mcp = FastMCP("Stock Trading Assistant")

# Your Dhan credentials - replace with your actual values
CLIENT_ID = "1106534888"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"

# Constants
DHAN_API_BASE = "https://api.dhan.co/v2"
STOCKS_FILE = "stocks.json"  # Path to your stocks.json file

def load_stocks():
    """Load the stocks data from stocks.json file"""
    try:
        with open(STOCKS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Stock data file {STOCKS_FILE} not found!")
        return {"companies": []}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {STOCKS_FILE}!")
        return {"companies": []}

# Make stocks data available as a resource
@mcp.resource("stocks://data")
def get_stocks_data() -> str:
    """Return the entire stocks database"""
    return json.dumps(load_stocks(), indent=2)

@mcp.resource("stocks://{query}")
def find_stock(query: str) -> str:
    """Find a stock by name, code, or using fuzzy matching"""
    stocks_data = load_stocks()
    query = query.lower()
    
    # Try to find exact matches first
    for stock in stocks_data.get("companies", []):
        if (stock["stock_name"].lower() == query or 
            stock["company_name"].lower() == query or
            stock["stock_code"] == query):
            return json.dumps(stock, indent=2)
    
    # Try fuzzy matches in company name, stock name and description
    matches = []
    for stock in stocks_data.get("companies", []):
        if (query in stock["stock_name"].lower() or 
            query in stock["company_name"].lower() or
            query in stock["description"].lower()):
            matches.append(stock)
    
    if matches:
        return json.dumps(matches[0], indent=2)  # Return the first match
    else:
        return json.dumps({"error": f"No stock found matching '{query}'"})

@mcp.tool()
def get_account_balance() -> str:
    """Get the available balance in the Dhan account"""
    headers = {
        "Content-Type": "application/json",
        "access-token": ACCESS_TOKEN
    }
    
    try:
        response = requests.get(f"{DHAN_API_BASE}/fundlimit", headers=headers)
        if response.status_code == 200:
            balance = response.json()
            return f"""
ACCOUNT BALANCE

Client ID: {balance.get('dhanClientId', 'Not Available')}
Available Balance: ₹{balance.get('availabelBalance', 'Not Available')}
Total Balance: ₹{balance.get('sodLimit', 'Not Available')}
"""
        else:
            return f"Failed to get balance: {response.status_code}\n{response.text}"
    except Exception as e:
        return f"Error fetching balance: {str(e)}"

@mcp.tool()
def buy_stock(
    stock_query: str, 
    quantity: int = 1,
    price_type: str = "MARKET",
    product_type: str = "CNC"  # CNC for delivery, INTRADAY for intraday
) -> str:
    """
    Buy a stock on Dhan
    
    Parameters:
    - stock_query: Stock name, company name or description
    - quantity: Number of shares to buy
    - price_type: MARKET or LIMIT
    - product_type: CNC (delivery) or INTRADAY
    """
    try:
        # First, find the stock
        stock_data_str = find_stock(stock_query)
        stock_data = json.loads(stock_data_str)
        
        # Check if we got an error
        if "error" in stock_data:
            return f"Error: {stock_data['error']}"
        
        # Now place the order
        headers = {
            "Content-Type": "application/json",
            "access-token": ACCESS_TOKEN
        }
        
        order_data = {
            "dhanClientId": CLIENT_ID,
            "correlationId": "123abc678",
            "transactionType": "BUY",
            "exchangeSegment": "NSE_EQ",  # Assuming NSE equities
            "productType": product_type,
            "orderType": price_type,
            "validity": "DAY",
            "securityId": stock_data["stock_code"],
            "quantity": str(quantity),
            "disclosedQuantity": "",
            "price": "",
            "triggerPrice": "",
            "afterMarketOrder": False
        }
        
        response = requests.post(f"{DHAN_API_BASE}/orders", headers=headers, json=order_data)
        
        if response.status_code in (200, 201, 202):
            result = response.json()
            return f"""
ORDER PLACED SUCCESSFULLY

Stock: {stock_data['company_name']} ({stock_data['stock_name']})
Quantity: {quantity}
Type: {price_type}
Product: {product_type}

Order ID: {result.get('orderId', 'Unknown')}
Status: {result.get('orderStatus', 'Unknown')}
"""
        else:
            try:
                error_data = response.json()
                return f"""
ORDER FAILED

Stock: {stock_data['company_name']} ({stock_data['stock_name']})
Error Type: {error_data.get('errorType', 'Unknown')}
Error Code: {error_data.get('errorCode', 'Unknown')}
Error Message: {error_data.get('errorMessage', 'Unknown error occurred')}
"""
            except:
                return f"Order failed with status code {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error placing order: {str(e)}"

@mcp.tool()
def sell_stock(
    stock_query: str, 
    quantity: int = 1,
    price_type: str = "MARKET",
    product_type: str = "CNC"  # CNC for delivery, INTRADAY for intraday
) -> str:
    """
    Sell a stock on Dhan
    
    Parameters:
    - stock_query: Stock name, company name or description
    - quantity: Number of shares to sell
    - price_type: MARKET or LIMIT
    - product_type: CNC (delivery) or INTRADAY
    """
    try:
        # First, find the stock
        stock_data_str = find_stock(stock_query)
        stock_data = json.loads(stock_data_str)
        
        # Check if we got an error
        if "error" in stock_data:
            return f"Error: {stock_data['error']}"
        
        # Now place the order
        headers = {
            "Content-Type": "application/json",
            "access-token": ACCESS_TOKEN
        }
        
        order_data = {
            "dhanClientId": CLIENT_ID,
            "correlationId": "123abc678",
            "transactionType": "SELL",
            "exchangeSegment": "NSE_EQ",  # Assuming NSE equities
            "productType": product_type,
            "orderType": price_type,
            "validity": "DAY",
            "securityId": stock_data["stock_code"],
            "quantity": str(quantity),
            "disclosedQuantity": "",
            "price": "",
            "triggerPrice": "",
            "afterMarketOrder": False
        }
        
        response = requests.post(f"{DHAN_API_BASE}/orders", headers=headers, json=order_data)
        
        if response.status_code in (200, 201, 202):
            result = response.json()
            return f"""
SELL ORDER PLACED SUCCESSFULLY

Stock: {stock_data['company_name']} ({stock_data['stock_name']})
Quantity: {quantity}
Type: {price_type}
Product: {product_type}

Order ID: {result.get('orderId', 'Unknown')}
Status: {result.get('orderStatus', 'Unknown')}
"""
        else:
            try:
                error_data = response.json()
                return f"""
SELL ORDER FAILED

Stock: {stock_data['company_name']} ({stock_data['stock_name']})
Error Type: {error_data.get('errorType', 'Unknown')}
Error Code: {error_data.get('errorCode', 'Unknown')}
Error Message: {error_data.get('errorMessage', 'Unknown error occurred')}
"""
            except:
                return f"Order failed with status code {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error placing sell order: {str(e)}"

@mcp.tool()
def get_holdings() -> str:
    """Get holdings from Dhan account"""
    headers = {
        "Content-Type": "application/json",
        "access-token": ACCESS_TOKEN
    }
    
    try:
        response = requests.get(f"{DHAN_API_BASE}/holdings", headers=headers)
        if response.status_code == 200:
            holdings = response.json()
            if not holdings:
                return "You don't have any holdings in your account."
            
            result = "YOUR HOLDINGS\n\n"
            for holding in holdings:
                result += f"""
Symbol: {holding.get('tradingSymbol', 'Unknown')}
ISIN: {holding.get('isin', 'Unknown')}
Quantity: {holding.get('totalQty', 0)}
Available Qty: {holding.get('availableQty', 0)}
Avg. Cost: ₹{holding.get('avgCostPrice', 0.0)}
-----------------------------
"""
            return result
        else:
            return f"Failed to get holdings: {response.status_code}\n{response.text}"
    except Exception as e:
        return f"Error fetching holdings: {str(e)}"

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()