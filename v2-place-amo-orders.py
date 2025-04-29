from mcp.server.fastmcp import FastMCP
import requests
import json
import os
from datetime import datetime
import re

# Create MCP server
mcp = FastMCP("Advanced Stock Trading Assistant")

# Your Dhan credentials - replace with your actual values
CLIENT_ID = "1106534888"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"

# Constants
DHAN_API_BASE = "https://api.dhan.co/v2"
STOCKS_FILE = "/Users/mayankthole/Desktop/dhan-trade/stocks.json"  # Path to your stocks.json file

# Default values for stop loss and target
DEFAULT_STOPLOSS_PERCENT = 1.0  # 1% of current price
DEFAULT_TARGET_PERCENT = 1.0    # 1% of current price

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

def extract_quantity(text):
    """Extract quantity from text, default to 1 if not found"""
    quantity_match = re.search(r'(\d+)\s*(share|shares|quantity|qty)', text.lower())
    if quantity_match:
        return int(quantity_match.group(1))
    return 1

# Advanced stock finder with detailed matching
def find_stock_by_query(query):
    """Find a stock using advanced matching techniques"""
    query = query.lower().strip()
    stocks_data = load_stocks()
    
    # Check for common brand/product references
    brand_mapping = {
        "fevicol": "PIDILITE",
        "hdfc": "HDFCBANK",
        "airtel": "bharti airtel",
        "jio": "reliance",
        "reliance": "reliance industries",
        "maruti": "maruti suzuki"
    }
    
    if query in brand_mapping:
        query = brand_mapping[query]
    
    # Look for exact matches first
    best_matches = []
    for stock in stocks_data.get("companies", []):
        stock_name_lower = stock["stock_name"].lower()
        company_name_lower = stock["company_name"].lower()
        
        # Exact matches get highest score
        if query == stock_name_lower or query == company_name_lower:
            return stock, 1.0
        
        # Check if query is contained in stock name or company name
        if query in stock_name_lower or query in company_name_lower:
            score = 0.8
            best_matches.append((stock, score))
            continue
            
        # Check description for keyword presence
        description_lower = stock["description"].lower()
        if query in description_lower:
            # Calculate relevance score based on word position and frequency
            words = description_lower.split()
            if query in words:
                # Exact word match is better than substring
                score = 0.7
            else:
                score = 0.6
            best_matches.append((stock, score))
            continue
        
        # Partial word matching
        for word in query.split():
            if len(word) > 3 and (word in stock_name_lower or word in company_name_lower):
                score = 0.5
                best_matches.append((stock, score))
                break
                
    # Sort by score and return best match
    if best_matches:
        best_matches.sort(key=lambda x: x[1], reverse=True)
        return best_matches[0][0], best_matches[0][1]
    
    return None, 0.0

# Make stocks data available as a resource
@mcp.resource("stocks://data")
def get_stocks_data() -> str:
    """Return the entire stocks database"""
    return json.dumps(load_stocks(), indent=2)

@mcp.resource("stocks://{query}")
def find_stock(query: str) -> str:
    """Find a stock by name, code, or using fuzzy matching"""
    stock, confidence = find_stock_by_query(query)
    
    if stock is None:
        return json.dumps({"error": f"No stock found matching '{query}'"})
    
    # Add confidence score to the result
    result = stock.copy()
    result["match_confidence"] = confidence
    return json.dumps(result, indent=2)

@mcp.tool()
def get_current_market_price(stock_query: str) -> str:
    """Get current market price for a stock"""
    stock, confidence = find_stock_by_query(stock_query)
    
    if stock is None:
        return f"Could not identify stock matching '{stock_query}'"
    
    try:
        headers = {
            "Content-Type": "application/json",
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID
        }
        
        # Prepare request for market feed
        payload = {
            "NSE_EQ": [stock["stock_code"]]
        }
        
        response = requests.post(f"{DHAN_API_BASE}/marketfeed/ltp", 
                                 headers=headers, 
                                 json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                price_data = data["data"]["NSE_EQ"].get(stock["stock_code"], {})
                price = price_data.get("last_price", "Not available")
                
                return f"""
CURRENT MARKET PRICE

Stock: {stock["company_name"]} ({stock["stock_name"]})
Price: ₹{price}
"""
            else:
                return f"Error fetching price data: {data.get('message', 'Unknown error')}"
        else:
            return f"Failed to get market price: {response.status_code}\n{response.text}"
    except Exception as e:
        return f"Error fetching market price: {str(e)}"

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
def place_order(
    stock_query: str,
    transaction_type: str = "BUY",
    quantity: int = 1,
    order_type: str = "MARKET",
    product_type: str = "CNC",
    price: float = None,
    trigger_price: float = None,
    after_market_order: bool = False,
    amo_time: str = "OPEN",
    set_stoploss: bool = False,
    stoploss_percent: float = DEFAULT_STOPLOSS_PERCENT,
    set_target: bool = False,
    target_percent: float = DEFAULT_TARGET_PERCENT
) -> str:
    """
    Place a stock order with full customization options
    
    Parameters:
    - stock_query: Stock name, company name or description
    - transaction_type: BUY or SELL
    - quantity: Number of shares
    - order_type: MARKET, LIMIT, STOP_LOSS, STOP_LOSS_MARKET
    - product_type: CNC (delivery) or INTRADAY
    - price: For LIMIT orders
    - trigger_price: For STOP_LOSS orders
    - after_market_order: Whether this is an AMO order
    - amo_time: When to execute AMO (PRE_OPEN, OPEN, OPEN_30, OPEN_60)
    - set_stoploss: Whether to set a stop loss
    - stoploss_percent: Percentage below buy price for stop loss
    - set_target: Whether to set a target
    - target_percent: Percentage above buy price for target
    """
    try:
        # Find the stock
        stock, confidence = find_stock_by_query(stock_query)
        
        if stock is None:
            return f"Could not identify a stock matching '{stock_query}'. Please provide a more specific stock name."
        
        if confidence < 0.6:
            return f"""
Low confidence match ({confidence:.2f}) for '{stock_query}'. 
Found: {stock['company_name']} ({stock['stock_name']})
Please confirm this is the correct stock or provide a more specific query.
"""
        
        # Validate transaction type
        transaction_type = transaction_type.upper()
        if transaction_type not in ["BUY", "SELL"]:
            return f"Invalid transaction type: {transaction_type}. Must be BUY or SELL."
        
        # Get current market price for target/stoploss if needed
        current_price = None
        if (set_stoploss or set_target) and not price:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "access-token": ACCESS_TOKEN,
                    "client-id": CLIENT_ID
                }
                
                payload = {
                    "NSE_EQ": [stock["stock_code"]]
                }
                
                response = requests.post(f"{DHAN_API_BASE}/marketfeed/ltp", 
                                        headers=headers, 
                                        json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    if data["status"] == "success":
                        price_data = data["data"]["NSE_EQ"].get(stock["stock_code"], {})
                        current_price = price_data.get("last_price")
                
            except Exception as e:
                return f"Error fetching current price for stop loss/target calculation: {str(e)}"
        
        # Use the provided price or current price
        reference_price = price or current_price
        
        # Now place the order
        headers = {
            "Content-Type": "application/json",
            "access-token": ACCESS_TOKEN
        }
        
        # Generate a correlation ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        correlation_id = f"{transaction_type}-{stock['stock_name']}-{timestamp}"
        
        order_data = {
            "dhanClientId": CLIENT_ID,
            "correlationId": correlation_id,
            "transactionType": transaction_type,
            "exchangeSegment": "NSE_EQ",
            "productType": product_type,
            "orderType": order_type,
            "validity": "DAY",
            "securityId": stock["stock_code"],
            "quantity": str(quantity),
            "disclosedQuantity": "",
            "afterMarketOrder": after_market_order
        }
        
        # Add price if it's a LIMIT order
        if order_type == "LIMIT" and price is not None:
            order_data["price"] = str(price)
        
        # Add trigger price if it's a STOP_LOSS or STOP_LOSS_MARKET order
        if order_type in ["STOP_LOSS", "STOP_LOSS_MARKET"] and trigger_price is not None:
            order_data["triggerPrice"] = str(trigger_price)
        
        # Add AMO time if it's an after market order
        if after_market_order:
            order_data["amoTime"] = amo_time
        
        # Place the main order
        response = requests.post(f"{DHAN_API_BASE}/orders", headers=headers, json=order_data)
        
        if response.status_code not in (200, 201, 202):
            try:
                error_data = response.json()
                return f"""
ORDER FAILED

Stock: {stock['company_name']} ({stock['stock_name']})
Error Type: {error_data.get('errorType', 'Unknown')}
Error Code: {error_data.get('errorCode', 'Unknown')}
Error Message: {error_data.get('errorMessage', 'Unknown error occurred')}
"""
            except:
                return f"Order failed with status code {response.status_code}: {response.text}"
        
        result = response.json()
        order_result = f"""
ORDER PLACED SUCCESSFULLY

Stock: {stock['company_name']} ({stock['stock_name']})
Type: {transaction_type} - {order_type}
Quantity: {quantity}
Product: {product_type}

Order ID: {result.get('orderId', 'Unknown')}
Status: {result.get('orderStatus', 'Unknown')}
"""
        
        # If we need to set stop loss/target for a BUY order and have a price reference
        stoploss_order_result = ""
        target_order_result = ""
        
        # Only attempt to place stop loss/target if the main order was successful 
        # AND we either have a limit price or current market price
        if reference_price is not None:
            # Set stop loss if requested (opposite of main transaction)
            if set_stoploss:
                sl_price = None
                if transaction_type == "BUY":
                    # For buy orders, stop loss is below purchase price
                    sl_price = round(reference_price * (1 - stoploss_percent/100), 2)
                    sl_transaction = "SELL"
                else:
                    # For sell orders, stop loss is above selling price
                    sl_price = round(reference_price * (1 + stoploss_percent/100), 2)
                    sl_transaction = "BUY"
                
                # Create stop loss order data
                sl_order_data = order_data.copy()
                sl_order_data["transactionType"] = sl_transaction
                sl_order_data["orderType"] = "STOP_LOSS"
                sl_order_data["price"] = str(sl_price)
                sl_order_data["triggerPrice"] = str(sl_price)
                sl_order_data["correlationId"] = f"SL-{correlation_id}"
                
                # Place stop loss order
                sl_response = requests.post(f"{DHAN_API_BASE}/orders", headers=headers, json=sl_order_data)
                
                if sl_response.status_code in (200, 201, 202):
                    sl_result = sl_response.json()
                    stoploss_order_result = f"""
STOP LOSS ORDER PLACED

Type: {sl_transaction} - STOP_LOSS
Price: ₹{sl_price}
Order ID: {sl_result.get('orderId', 'Unknown')}
Status: {sl_result.get('orderStatus', 'Unknown')}
"""
                else:
                    stoploss_order_result = "\nFailed to place stop loss order"
            
            # Set target if requested (opposite of main transaction)
            if set_target:
                target_price = None
                if transaction_type == "BUY":
                    # For buy orders, target is above purchase price
                    target_price = round(reference_price * (1 + target_percent/100), 2)
                    target_transaction = "SELL"
                else:
                    # For sell orders, target is below selling price
                    target_price = round(reference_price * (1 - target_percent/100), 2)
                    target_transaction = "BUY"
                
                # Create target order data
                target_order_data = order_data.copy()
                target_order_data["transactionType"] = target_transaction
                target_order_data["orderType"] = "LIMIT"
                target_order_data["price"] = str(target_price)
                target_order_data["correlationId"] = f"TARGET-{correlation_id}"
                
                # Place target order
                target_response = requests.post(f"{DHAN_API_BASE}/orders", headers=headers, json=target_order_data)
                
                if target_response.status_code in (200, 201, 202):
                    target_result = target_response.json()
                    target_order_result = f"""
TARGET ORDER PLACED

Type: {target_transaction} - LIMIT
Price: ₹{target_price}
Order ID: {target_result.get('orderId', 'Unknown')}
Status: {target_result.get('orderStatus', 'Unknown')}
"""
                else:
                    target_order_result = "\nFailed to place target order"
        
        # Return combined result
        return order_result + stoploss_order_result + target_order_result
        
    except Exception as e:
        return f"Error placing order: {str(e)}"

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

@mcp.tool()
def place_amo(
    stock_query: str,
    transaction_type: str = "BUY",
    quantity: int = 1,
    order_type: str = "LIMIT",
    price: float = None,
    amo_time: str = "OPEN",  # PRE_OPEN, OPEN, OPEN_30, OPEN_60
    set_stoploss: bool = False,
    stoploss_percent: float = DEFAULT_STOPLOSS_PERCENT,
    set_target: bool = False,
    target_percent: float = DEFAULT_TARGET_PERCENT
) -> str:
    """
    Place an After Market Order (AMO)
    
    Parameters:
    - stock_query: Stock name, company name or description
    - transaction_type: BUY or SELL
    - quantity: Number of shares
    - order_type: LIMIT or MARKET
    - price: For LIMIT orders (required)
    - amo_time: When to execute AMO (PRE_OPEN, OPEN, OPEN_30, OPEN_60)
    - set_stoploss: Whether to set a stop loss
    - stoploss_percent: Percentage below buy price for stop loss
    - set_target: Whether to set a target
    - target_percent: Percentage above buy price for target
    """
    
    if order_type == "LIMIT" and price is None:
        return "Price is required for LIMIT orders"
    
    return place_order(
        stock_query=stock_query,
        transaction_type=transaction_type,
        quantity=quantity,
        order_type=order_type,
        product_type="CNC",  # AMO is typically for delivery
        price=price,
        after_market_order=True,
        amo_time=amo_time,
        set_stoploss=set_stoploss,
        stoploss_percent=stoploss_percent,
        set_target=set_target,
        target_percent=target_percent
    )

@mcp.tool()
def analyze_stock_description(description: str) -> str:
    """Analyze a user's description to identify which stock they're referring to"""
    stock, confidence = find_stock_by_query(description)
    
    if stock is None:
        return f"I couldn't identify a stock matching the description: '{description}'"
    
    result = f"""
STOCK IDENTIFICATION ANALYSIS

Based on your description: "{description}"

I identified: {stock['company_name']} ({stock['stock_name']})
Security ID: {stock['stock_code']}
Confidence: {confidence:.2f} (on a scale of 0-1)

Brief Description:
{stock['description'][:200]}...
"""
    return result

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()