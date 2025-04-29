import requests
import json

def place_amo(access_token, client_id, security_id, transaction_type, quantity, price=None, order_type="LIMIT"):
    """
    Place an After Market Order (AMO) using DhanHQ API
    
    Parameters:
    - access_token: Your authentication token
    - client_id: Your Dhan client ID
    - security_id: Exchange standard ID for the scrip
    - transaction_type: 'BUY' or 'SELL'
    - quantity: Number of shares to trade
    - price: Price at which order is placed (required for LIMIT orders)
    - order_type: Order type ('LIMIT', 'MARKET', 'STOP_LOSS', 'STOP_LOSS_MARKET')
    
    Returns:
    - API response
    """
    # API endpoint
    url = "https://api.dhan.co/v2/orders"
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'access-token': access_token
    }
    
    # Request payload
    payload = {
        "dhanClientId": client_id,
        "correlationId": f"AMO-{security_id}-{transaction_type}",  # Optional: you can create your own tracking ID
        "transactionType": transaction_type,
        "exchangeSegment": "NSE_EQ",  # Modify as needed
        "productType": "CNC",  # Modify as needed (CNC, INTRADAY, MARGIN, etc.)
        "orderType": order_type,
        "validity": "DAY",
        "securityId": security_id,
        "quantity": quantity,
        "afterMarketOrder": True,  # Flag for AMO
        "amoTime": "OPEN"  # Options: PRE_OPEN, OPEN, OPEN_30, OPEN_60
    }
    
    # Add price if it's a LIMIT order
    if order_type == "LIMIT" and price is not None:
        payload["price"] = price
    
    # Add trigger price if it's a STOP_LOSS or STOP_LOSS_MARKET order
    if "STOP_LOSS" in order_type and price is not None:
        payload["triggerPrice"] = price
    
    # Make the API request
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# Example usage
if __name__ == "__main__":
    # Replace these values with your actual credentials and order details
    ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"
    CLIENT_ID = "1106534888"
    SECURITY_ID = "10794"  # Example: TCS
    
    # Place a BUY AMO LIMIT order
    result = place_amo(
        access_token=ACCESS_TOKEN,
        client_id=CLIENT_ID,
        security_id=SECURITY_ID,
        transaction_type="BUY",
        quantity=1,
        price=87,
        order_type="MARKET"
    )
    
    print(json.dumps(result, indent=2))