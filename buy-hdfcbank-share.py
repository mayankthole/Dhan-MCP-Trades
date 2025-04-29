import requests
import json

# Your credentials
client_id = "1106534888"    # Example: "1000000009" 
access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"

# Buy HDFC Bank shares
url = "https://api.dhan.co/v2/orders"

# Order details 
order = {
    "dhanClientId": client_id,
    "transactionType": "BUY",
    "exchangeSegment": "NSE_EQ",
    "productType": "CNC",
    "orderType": "MARKET",
    "validity": "DAY",
    "securityId": "1333",  # HDFC Bank security ID
    "quantity": "10",      # Change quantity as needed
    "disclosedQuantity": "",
    "price": "",
    "triggerPrice": "",
    "afterMarketOrder": False
}

# Place order
headers = {
    'Content-Type': 'application/json',
    'access-token': access_token
}

# Send request and get response
response = requests.post(url, json=order, headers=headers)

# Print full response
print("Response Status Code:", response.status_code)
print("Full Response:")
print(json.dumps(response.json(), indent=2))

# Try to access result safely
result = response.json()
if 'orderId' in result:
    print(f"Order ID: {result['orderId']}")
else:
    print("Error: No orderId in response")
    print("Available keys in response:", list(result.keys()))