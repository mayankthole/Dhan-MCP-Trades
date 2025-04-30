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

📈 Expanded Example Trading Commands
🛒 Basic Order Placement
- "Buy 10 shares of Infosys at market price"

- "Sell 5 shares of TCS at limit price of ₹3500"

- "Place a GTT order to buy 20 shares of HDFC Bank at ₹1450"

🎯 Orders with Stop-Loss and Targets
- "Buy Reliance with 2% target and 1% stop-loss"

- "Place a trailing stop-loss buy order for Tata Motors"

- "Short sell Axis Bank with 5% target and 2% stop-loss"

🌙 After-Market & Scheduled Orders
- "Create an after-market order to buy 100 shares of ONGC at ₹180"

- "Schedule a buy order for Tech Mahindra tomorrow at 9:15 AM"

💼 Account Insights
- "What are my current holdings?"

- "Check my available balance and margin"

- "Show me my open positions and unrealized profits"

📊 Portfolio & P&L Analysis
- "Analyze my portfolio performance this month"

- "Give me a P&L report on all banking sector trades"

- "What was my best-performing stock in the last 30 days?"

🤖 Smart, Context-Aware Voice Commands
- "Buy all PSU bank stocks"

- "Short all private sector banks today"

- "Go long on top 5 Nifty IT companies"

- "Buy 2 shares of the company whose promoter's son just had a grand wedding"

- "Tail the stop-loss of all chemical sector stocks"

📌 Contextual & Thematic Trading
- "Buy all companies headquartered in Mumbai"

- "Buy companies where promoter stake is increasing quarter-on-quarter"

- "Short all companies dependent heavily on China for raw materials"

- "Buy the top 5 companies based on market cap in India"

📈 Technical Signal-Based Trading
- "Buy breakout stocks above 200-day moving average"

- "Short stocks that broke below lower Bollinger Band"

- "Buy stocks where RSI crossed above 70"

- "Enter trades in mean reversion stocks with tight stop-loss"

🔍 Advanced Filtering & Signal Scanning
- "Buy companies where profits grew more than 10% quarter-on-quarter"

- "Buy stocks down more than 20% from all-time highs with high volume"

- "Sell all stocks affected by global crude oil prices"

🔁 Pairs & Strategy-Based Trading
- "Buy 3 shares of Reliance and sell 2 shares of Bharti Airtel"

- "Do pair trading between ICICI Bank and Axis Bank"



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
