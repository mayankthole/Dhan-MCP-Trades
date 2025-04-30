# DhanHQ Trading Assistant

An AI-powered trading assistant for DhanHQ broker built with Model Context Protocol (MCP). This project enables natural language interaction with the DhanHQ trading platform, allowing you to place orders, check your portfolio, and manage your trading activities through simple conversational commands.

## Features

### Order Management
- Regular orders (market/limit) via `order_placement_tool.py`
- Super orders with target and stop-loss via `super-order.py`
- After-market orders via `after_market_order_tool.py`
- Access order book and trade history via `order_book_tool.py`

### Portfolio Management
- View holdings and positions via `holdings_positions_tool.py`
- Convert positions (e.g., intraday to delivery)

### Account Information
- Check fund balance via `fund_balance_tool.py`
- Calculate margin requirements via `margin_calculator_tool.py`

## Setup and Installation

### Prerequisites
- Python 3.9 or higher
- A DhanHQ trading account
- DhanHQ API credentials (client ID and access token)

### Installation

1. Clone this repository
   ```
   git clone https://github.com/yourusername/dhan-broker-mcp-trades.git
   cd dhan-broker-mcp-trades
   ```

2. Install required dependencies
   ```
   pip install -r requirements.txt
   ```

3. Configure your credentials
   
   Edit the `config.py` file with your DhanHQ credentials:
   ```python
   DHAN_CLIENT_ID = "your_client_id_here"
   DHAN_ACCESS_TOKEN = "your_access_token_here"
   DHAN_API_BASE_URL = "https://api.dhan.co/v2"
   ```

4. Make sure your `stocks.json` file is populated with the stocks you want to trade

### Running the Tools

Each tool can be run independently using the MCP CLI:

```
# To run the order placement tool
python -m mcp.server.cli dev order_placement_tool.py

# To run the portfolio server
python -m mcp.server.cli dev portfolio_server.py

# To run other tools
python -m mcp.server.cli dev <tool_filename>.py
```

## Using the Assistant

Once a tool is running, you can interact with it using natural language. Here are some example commands:

- "Buy 10 shares of HDFC Bank at market price"
- "Place a super order to buy 5 shares of Reliance with 2% target and 1% stop-loss"
- "Create an after-market order to buy 15 shares of TCS at 3500 rupees"
- "What are my current holdings?"
- "Check my available balance"
- "Show me my open positions"

## Tool Descriptions

### order_placement_tool.py
Handles basic order placement (market and limit orders). Supports buying and selling stocks by name.

### super-order.py
Manages super orders with target and stop-loss limits that can be specified in absolute values or percentages.

### after_market_order_tool.py
Places orders outside market hours to be executed on the next trading day.

### fund_balance_tool.py
Retrieves account fund information and calculates margin requirements.

### holdings_positions_tool.py
Retrieves holdings and positions information, allows conversion between product types.

### margin_calculator_tool.py
Calculates margin requirements for potential trades.

### order_book_tool.py
Provides access to order history, trade book, and enables order cancellation.

### portfolio_server.py
Main interface for portfolio management.

## Stock Information

The project uses a `stocks.json` file to map stock names to their security IDs. The file follows this structure:

```json
{
  "companies": [
    {
      "stock_code": "1333",
      "company_name": "HDFC Bank Ltd.",
      "stock_name": "HDFCBANK",
      "description": "Description of the company..."
    }
  ]
}
```

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational purposes only. Use at your own risk. The creators are not responsible for any financial losses incurred through the use of this software. Always verify all trading actions before execution.