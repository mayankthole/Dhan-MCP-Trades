from mcp.server.fastmcp import FastMCP
import requests
import json
import os

# Create MCP server
mcp = FastMCP("Dhan Trading Server")

# Your Dhan credentials
CLIENT_ID = "1106534888"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"

# Your specific stocks.json path
STOCKS_FILE = "/Users/mayankthole/Desktop/dhan-trade/stocks.json"

def load_stock_data():
    """Load stock data from JSON file"""
    try:
        with open(STOCKS_FILE, 'r') as file:
            data = json.load(file)
            return data['companies']
    except FileNotFoundError:
        print(f"Error: stocks.json not found at {STOCKS_FILE}")
        return []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in stocks.json")
        return []
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def find_stock_by_description(description: str, stocks: list) -> dict:
    """Find stock by searching description"""
    description = description.lower()
    for stock in stocks:
        if (description in stock['description'].lower() or 
            description in stock['company_name'].lower() or
            description in stock['stock_name'].lower()):
            return stock
    return None

@mcp.tool()
def identify_stock(description: str) -> str:
    """Identify stock from user description"""
    stocks = load_stock_data()
    if not stocks:
        return "Error: Could not load stock data"
        
    stock = find_stock_by_description(description, stocks)
    
    if not stock:
        return "I couldn't find a stock matching that description. Could you be more specific?"
    
    return f"""I found this stock based on your description:
Company: {stock['company_name']}
Stock Symbol: {stock['stock_name']}
Security ID: {stock['stock_code']}

Would you like to:
1. Know more about this company
2. Place a trade for this stock
3. Look for a different stock"""

@mcp.tool()
def get_stock_info(description: str) -> str:
    """Get detailed stock information"""
    stocks = load_stock_data()
    if not stocks:
        return "Error: Could not load stock data"
        
    stock = find_stock_by_description(description, stocks)
    
    if not stock:
        return "I couldn't find information about that stock."
    
    return f"""Detailed Information:
Company: {stock['company_name']}
Stock Symbol: {stock['stock_name']}
Security ID: {stock['stock_code']}

Description:
{stock['description']}"""

@mcp.tool()
def execute_trade(description: str, quantity: str = "1", action: str = "BUY") -> str:
    """Execute the trade and show complete broker response"""
    try:
        stocks = load_stock_data()
        if not stocks:
            return "Error: Could not load stock data"
            
        stock = find_stock_by_description(description, stocks)
        if not stock:
            return "I couldn't identify the stock for trading."

        url = "https://api.dhan.co/v2/orders"
        order = {
            "dhanClientId": CLIENT_ID,
            "correlationId": "123abc678",
            "transactionType": action,
            "exchangeSegment": "NSE_EQ",
            "productType": "CNC",
            "orderType": "MARKET",
            "validity": "DAY",
            "securityId": stock['stock_code'],
            "quantity": quantity,
            "disclosedQuantity": "",
            "price": "",
            "triggerPrice": "",
            "afterMarketOrder": False
        }
        
        headers = {
            'Content-Type': 'application/json',
            'access-token': ACCESS_TOKEN
        }

        print("\n=== ORDER REQUEST ===")
        print(json.dumps(order, indent=2))

        response = requests.post(url, json=order, headers=headers)
        
        print("\n=== BROKER RESPONSE ===")
        print("Status Code:", response.status_code)
        print("Response Headers:", dict(response.headers))
        print("Raw Response:", response.text)

        try:
            response_json = response.json()
        except:
            response_json = {}

        # Handle specific error types
        if response.status_code != 200:
            error_type = response_json.get('errorType', '')
            error_code = response_json.get('errorCode', '')
            error_message = response_json.get('errorMessage', '')
            
            return f"""
ORDER FAILED

Trade Details:
Stock: {stock['company_name']} ({stock['stock_name']})
Action: {action}
Quantity: {quantity}

Broker Response:
Error Type: {error_type}
Error Code: {error_code}
Error Message: {error_message}

Raw Response:
Status Code: {response.status_code}
Full Response: {response.text}"""

        # Handle successful responses
        return f"""
ORDER ATTEMPT COMPLETED

Trade Details:
Stock: {stock['company_name']} ({stock['stock_name']})
Action: {action}
Quantity: {quantity}

Broker Response:
Status: {response_json.get('orderStatus', 'Unknown')}
Order ID: {response_json.get('orderId', 'Not Available')}

Raw Response:
Status Code: {response.status_code}
Full Response: {response.text}"""

    except requests.exceptions.RequestException as e:
        return f"""
CONNECTION ERROR
Type: {type(e).__name__}
Details: {str(e)}
"""
    except Exception as e:
        return f"""
SYSTEM ERROR
Type: {type(e).__name__}
Details: {str(e)}
"""

@mcp.tool()
def get_balance() -> str:
    """Get balance from Dhan API"""
    try:
        url = "https://api.dhan.co/v2/fundlimit"
        headers = {
            'Content-Type': 'application/json',
            'access-token': ACCESS_TOKEN
        }
        
        print("\n=== BALANCE REQUEST ===")
        print("URL:", url)
        
        response = requests.get(url, headers=headers)
        
        print("\n=== BROKER RESPONSE ===")
        print("Status Code:", response.status_code)
        print("Raw Response:", response.text)
        
        try:
            balance = response.json()
            return f"""
ACCOUNT BALANCE

Client ID: {balance.get('dhanClientId', 'Not Available')}
Available Balance: ₹{balance.get('availabelBalance', 'Not Available')}
Total Balance: ₹{balance.get('sodLimit', 'Not Available')}

Raw Response:
{response.text}"""
        except:
            return f"""
BALANCE CHECK FAILED
Status Code: {response.status_code}
Raw Response: {response.text}"""
            
    except Exception as e:
        return f"Error fetching balance: {str(e)}"

if __name__ == "__main__":
    mcp.run()