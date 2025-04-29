from mcp.server.fastmcp import FastMCP
import requests
import json
from datetime import datetime, time
import pytz

# Create MCP server
mcp = FastMCP("Comprehensive Trading System")

# Get credentials from user
CLIENT_ID = "1106534888"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"

# Define constants
STOCKS_FILE = "/Users/mayankthole/Desktop/dhan-trade/stocks.json"
IST = pytz.timezone('Asia/Kolkata')

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

def find_stocks_by_description(description: str, stocks: list) -> list:
    """Find stocks matching the description"""
    matches = []
    description = description.lower()
    
    # Split for multiple stocks
    descriptions = [d.strip() for d in description.split(',')] 
    
    for desc in descriptions:
        best_match = None
        highest_confidence = 0
        
        for stock in stocks:
            confidence = 0
            
            # Exact matches in company name or stock name
            if desc == stock['company_name'].lower() or desc == stock['stock_name'].lower():
                confidence = 1.0
            
            # Brand/product matches in description 
            elif desc in stock['description'].lower():
                confidence = 0.8
                
            # Partial matches in company name
            elif desc in stock['company_name'].lower():
                confidence = 0.6
                
            # Handle special cases like "HDFC" matching "HDFC Bank" 
            if stock['company_name'].lower().startswith(desc):
                confidence = max(confidence, 0.7)
                
            if confidence > highest_confidence:
                highest_confidence = confidence 
                best_match = stock
        
        if best_match and highest_confidence > 0.5:  # Confidence threshold
            matches.append(best_match)
    
    return matches

def get_market_status():
    """Check if market is open"""
    now = datetime.now(IST)
    
    # Check if weekend
    if now.weekday() >= 5:
        return "CLOSED"
    
    # Check if before 9:15 AM or after 3:30 PM
    if now.time() < time(9, 15) or now.time() > time(15, 30):
        return "CLOSED"
    
    return "OPEN"

def get_live_price(security_id: str) -> float:
    """Get live price for a stock"""
    url = f"https://api.dhan.co/v2/marketquote/{security_id}"
    headers = {
        'Content-Type': 'application/json',
        'access-token': ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return float(data['ltp'])
    except requests.exceptions.RequestException as e:
        print(f"Error getting live price: {e}")
    except (KeyError, ValueError):
        print("Error parsing live price response")
        
    return None

def validate_price_for_order(stock: dict, order_type: str, price: float = None) -> bool:
    """Validate if the price is within allowed range for an order"""
    current_price = get_live_price(stock['stock_code'])
    
    if not current_price:
        return False
    
    if order_type == 'MARKET':
        return True
    
    if not price:
        return False
    
    # Check if price is within 10% of current price
    if price < current_price * 0.9 or price > current_price * 1.1:
        return False
    
    return True

def place_regular_order(stock: dict, quantity: int, order_type: str, price: float = None):
    """Place a regular order"""
    data = {
        "exchangeSegment": "NSE_EQ",  
        "productType": "INTRADAY",
        "price": price,
        "orderType": order_type,
        "quantity": quantity,
        "disclosedQuantity": 0,
        "orderValidity": "DAY",
        "afterMarketOrder": False,
        "orderSide": "BUY",
        "dhanClientId": CLIENT_ID,
        "securityId": stock['stock_code'],
        "source": "API"
    }
    
    url = "https://api.dhan.co/v2/orders"
    headers = {
        'Content-Type': 'application/json', 
        'access-token': ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error placing order: {e}")
    except json.JSONDecodeError:
        print("Error parsing order response")
        
    return None
        
def place_super_order(stock: dict, quantity: int, target_percent: float, stoploss_percent: float):
    """Place a super order with target and stoploss"""
    price = get_live_price(stock['stock_code'])
    
    if not price:
        print("Error getting live price for super order")
        return
    
    target = round(price * (1 + target_percent/100), 2)
    stoploss = round(price * (1 - stoploss_percent/100), 2)
    
    data = {
        "ex": "NSE",
        "dhanClientId": CLIENT_ID,
        "securityId": stock['stock_code'],
        "quantity": quantity,
        "targetPrice": target,
        "superOrder": "SO",
        "stopLoss": stoploss
    }

    url = "https://api.dhan.co/v2/superorder"
    headers = {
        'Content-Type': 'application/json',
        'access-token': ACCESS_TOKEN 
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error placing super order: {e}")
    except json.JSONDecodeError:
        print("Error parsing super order response")
        
    return None
        
def get_holdings():
    """Get current holdings"""
    url = "https://api.dhan.co/v2/portfolio/holdings"
    headers = {
        'Content-Type': 'application/json',
        'access-token': ACCESS_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers) 
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting holdings: {e}")
    except json.JSONDecodeError:
        print("Error parsing holdings response")
        
    return None

def get_positions():
    """Get current positions"""  
    url = "https://api.dhan.co/v2/portfolio/positions"
    headers = {
        'Content-Type': 'application/json',
        'access-token': ACCESS_TOKEN 
    }
    
    try:
        response = requests.get(url, headers=headers)
        return response.json() 
    except requests.exceptions.RequestException as e:
        print(f"Error getting positions: {e}")
    except json.JSONDecodeError:
        print("Error parsing positions response")
        
    return None
        
def exit_all_positions():
    """Exit all positions"""
    positions = get_positions()
    
    if not positions:
        return
    
    for position in positions:
        quantity = position['netQuantity']
        if quantity == 0:
            continue
        
        stock = next((s for s in stocks if s['stock_code'] == position['security']), None)
        
        if not stock:
            print(f"Error finding stock for position {position['security']}")
            continue
        
        if quantity > 0:
            action = "SELL"
        else:
            action = "BUY"
            quantity = abs(quantity)
            
        print(f"Exiting position for {stock['company_name']}, Quantity: {quantity}, Action: {action}")
        place_regular_order(stock, quantity, 'MARKET', action)

# Load stock data at startup 
stocks = load_stock_data()


@mcp.tool()
def identify_stock(description: str) -> dict:
    """Identify stocks from description"""
    if not stocks:
        return "Error loading stock data"
    
    matches = find_stocks_by_description(description, stocks)
    
    if not matches:
        return "No matching stocks found"
    elif len(matches) == 1:
        stock = matches[0]
        return f"Found stock: {stock['company_name']} ({stock['stock_name']})\nDescription: {stock['description']}"
    else:
        output = "Found multiple matching stocks:\n"
        for stock in matches:
            output += f"- {stock['company_name']} ({stock['stock_name']})\n"
        return output

@mcp.tool()
def check_market_status() -> str:
    """Check current market status""" 
    status = get_market_status()
    
    if status == "OPEN":
        return "The market is currently OPEN for trading"
    else:
        return f"The market is currently CLOSED.\nRegular market hours are Monday to Friday, 9:15 AM to 3:30 PM"

@mcp.tool()
def get_stock_price(description: str) -> str:
    """Get current market price for a stock"""
    matches = find_stocks_by_description(description, stocks)
    
    if not matches:
        return "No matching stock found"
    elif len(matches) > 1:
        return "Found multiple stocks, please be more specific"
    
    stock = matches[0]
    price = get_live_price(stock['stock_code'])
    
    if not price:
        return "Error getting current price"
    
    return f"The current market price of {stock['company_name']} is ₹{price:.2f}"

@mcp.tool()
def regular_order(description: str, quantity: str, order_type: str = 'MARKET', price: str = None) -> str:
    """Place a regular order"""
    quantity = int(quantity)
    if price:
        price = float(price)
    
    matches = find_stocks_by_description(description, stocks)
    
    if not matches:
        return "No matching stock found"
    elif len(matches) > 1:
        return "Found multiple stocks, please be more specific"
    
    stock = matches[0]
    
    if not validate_price_for_order(stock, order_type, price):
        return f"Invalid price {price} for {order_type} order on {stock['company_name']}"
    
    order_response = place_regular_order(stock, quantity, order_type, price) 
    
    if not order_response:
        return "Error placing order"
    
    if order_response.get('status') == 'PENDING':
        return f"Order placed successfully for {quantity} shares of {stock['company_name']}.\nOrder ID: {order_response['orderId']}"
    else:
        return f"Order failed with message: {order_response.get('message', 'Unknown error')}"

@mcp.tool()   
def super_order(description: str, quantity: str, target_percent: str, stoploss_percent: str) -> str:
    """Place a super order"""
    quantity = int(quantity)
    target_percent = float(target_percent)
    stoploss_percent = float(stoploss_percent)
    
    matches = find_stocks_by_description(description, stocks)
    
    if not matches:
        return "No matching stock found"
    elif len(matches) > 1:
        return "Found multiple stocks, please be more specific"
    
    stock = matches[0]
    
    order_response = place_super_order(stock, quantity, target_percent, stoploss_percent)
    
    if not order_response:
        return "Error placing super order"
    
    if order_response.get('status') == 'PENDING':
        return f"Super order placed for {quantity} shares of {stock['company_name']} with {target_percent}% target and {stoploss_percent}% stoploss.\nOrder ID: {order_response['id']}"
    else:
        return f"Super order failed with message: {order_response.get('message', 'Unknown error')}" 
        
@mcp.tool()
def view_holdings() -> str:
    """View current holdings"""
    holdings = get_holdings()
    
    if not holdings:
        return "Error getting holdings"
    
    if len(holdings) == 0:
        return "No holdings found"
    
    output = "Current Holdings:\n"
    for holding in holdings:
        output += f"- {holding['name']} ({holding['exchange']}): {holding['quantity']} shares at avg price ₹{holding['averagePrice']:.2f}\n"
        
    return output

@mcp.tool()
def view_positions() -> str:  
    """View current positions"""
    positions = get_positions()
    
    if not positions:
        return "Error getting positions"
    
    if len(positions) == 0:
        return "No open positions found"
    
    output = "Current Positions:\n"
    for position in positions:
        stock = next((s for s in stocks if s['stock_code'] == position['security']), None)
        if stock:
            stock_name = stock['company_name']
        else:
            stock_name = position['security']
        
        output += f"- {stock_name}: {position['netQuantity']} shares\n"
        
    return output

@mcp.tool()  
def exit_positions(confirm: str) -> str:
    """Exit all positions"""
    if confirm.lower() != 'confirm':
        return "To exit all positions, please run this command again with the argument 'confirm'"
    
    exit_all_positions()
    
    return "Initiated exit for all positions"

if __name__ == "__main__":
    mcp.run()