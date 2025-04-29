# dhan_balance.py
from Dhan_Tradehull import Tradehull

# Credentials
CLIENT_CODE = "1106534888"
TOKEN_ID = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"

def get_balance():
    """Check Dhan account balance"""
    try:
        # Initialize Tradehull client
        dhan_client = Tradehull(CLIENT_CODE, TOKEN_ID)
        
        # Get balance
        balance = dhan_client.get_balance()
        
        return f"Current Account Balance: {balance}"
    except Exception as e:
        return f"Error fetching balance: {str(e)}"
    







