from mcp.server.fastmcp import FastMCP
import requests

# Create MCP server
mcp = FastMCP("Dhan Balance Server")

# Your Dhan credentials
CLIENT_ID = "1106534888"  
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"

@mcp.resource("dhan://balance")
def get_balance() -> dict:
    """Get balance from Dhan API"""
    url = "https://api.dhan.co/v2/fundlimit"
    headers = {
        'Content-Type': 'application/json',
        'access-token': ACCESS_TOKEN
    }
    
    response = requests.get(url, headers=headers)
    balance = response.json()
    
    return {
        'client_id': balance['dhanClientId'],
        'available_balance': balance['availabelBalance'],
        'total_balance': balance['sodLimit']
    }

@mcp.tool()
def check_balance() -> str:
    """Get formatted balance string"""
    balance = get_balance()
    return f"""
    Client ID: {balance['client_id']}
    Available Balance: ₹{balance['available_balance']}
    Total Balance: ₹{balance['total_balance']}
    """

if __name__ == "__main__":
    mcp.run()


