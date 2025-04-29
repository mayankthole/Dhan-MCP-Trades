# Dhan Trading MCP Server

A Model Context Protocol (MCP) server integration for the Dhan Trading API, allowing Claude to access your trading account information.

## Overview

This project creates an MCP server that connects the Dhan Trading API with Claude AI, enabling Claude to:

- Check your account balance
- View your holdings and positions
- Get live profit and loss information
- Fetch latest trading prices
- Place and manage orders

## Installation

### Prerequisites

- Python 3.8+ installed
- Claude Desktop application
- Dhan Trading account with API credentials

### Setup

1. Install required packages:

```bash
pip install "mcp[cli]" Dhan-Tradehull
```

2. Clone this repository:

```bash
git clone https://github.com/your-username/dhan-trading-mcp.git
cd dhan-trading-mcp
```

3. Configure your Dhan API credentials by creating `.claude-desktop.json` in your home directory:

```json
{
    "mcpServers": {
        "dhan-trading": {
            "command": "/path/to/your/python",
            "args": [
                "/path/to/your/simple_dhan_mcp.py"
            ],
            "env": {
                "DHAN_CLIENT_CODE": "your_client_code",
                "DHAN_TOKEN_ID": "your_token_id"
            }
        }
    }
}
```

Replace the paths and API credentials with your own.

## Files

- `simple_dhan_mcp.py` - The MCP server implementation
- `simple_echo.py` - A minimal example server for testing connectivity

## Usage

1. Start Claude Desktop
2. Your Dhan MCP server will automatically connect
3. Ask Claude questions about your trading account, such as:
   - "What's my current balance?"
   - "Show me my holdings"
   - "What's my current P&L?"
   - "Get the latest price for NIFTY"

## Testing

To test your MCP server before connecting to Claude Desktop:

```bash
python /path/to/your/simple_dhan_mcp.py
```

Or test with minimal examples:

```bash
python /path/to/your/simple_echo.py
```

## Troubleshooting

If you experience connectivity issues:

1. Check that MCP package is installed correctly
2. Verify your API credentials are valid
3. Ensure paths in your configuration are correct
4. Check Claude Desktop logs (Open MCP settings > "Open Logs Folder")
5. Try the simple echo server first to test basic connectivity

## How It Works

The MCP (Model Context Protocol) server acts as a bridge between Claude and your Dhan trading API by:

1. Exposing your Dhan account data as "resources" that Claude can read
2. Providing "tools" that Claude can use to perform actions like getting prices
3. Handling the JSON communication protocol between Claude and your Dhan account

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) for the MCP specification
